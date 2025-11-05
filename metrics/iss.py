"""
Infrastructure Strain Score (ISS) Calculator.
Forecasts service request volume and correlates with infrastructure readiness.
"""

from typing import Dict, List, Optional
from agents.tools.database_tool import execute_query_dataframe
import pandas as pd
import numpy as np


def calculate_iss(district: Optional[str] = None) -> Dict[str, float]:
    """
    Calculate Infrastructure Strain Score for district(s).
    
    Formula: ISS = (Service Request Volume / Infrastructure Capacity) × Demand Forecast
    
    Args:
        district: Optional district name. If None, calculates for all districts.
    
    Returns:
        Dictionary mapping district names to ISS scores (0-10 scale)
    """
    # Query service requests and infrastructure data
    query = """
    SELECT 
        d."District",
        COUNT(DISTINCT s."Request_ID") as service_request_count,
        d."Roads_Km",
        d."Water_Treatment_Plants",
        d."Electricity_Substations",
        d."Population",
        d."Area_Sq_Km",
        AVG(CASE WHEN s."Service_Category" = 'Infrastructure' THEN 1 ELSE 0 END) as infrastructure_ratio
    FROM area_wise_demographics_infrastructure d
    LEFT JOIN service_request_details s ON d."District" = s."District"
    WHERE d."District" IS NOT NULL
    """
    
    if district:
        query += f" AND d.\"District\" = '{district}'"
    
    query += " GROUP BY d.\"District\", d.\"Roads_Km\", d.\"Water_Treatment_Plants\", d.\"Electricity_Substations\", d.\"Population\", d.\"Area_Sq_Km\""
    
    df = execute_query_dataframe(query)
    
    if df.empty:
        return {}
    
    # Get recent service requests for trend analysis (last 30 days equivalent)
    trend_query = """
    SELECT 
        "District",
        COUNT(*) as recent_requests,
        AVG("Resolution_Time_Hours") as avg_resolution_time
    FROM service_request_details
    WHERE "Service_Category" = 'Infrastructure'
        AND "District" IS NOT NULL
    """
    
    if district:
        trend_query += f" AND \"District\" = '{district}'"
    
    trend_query += " GROUP BY \"District\""
    
    trend_df = execute_query_dataframe(trend_query)
    
    iss_scores = {}
    
    for _, row in df.iterrows():
        dist = row['District']
        
        service_count = row['service_request_count'] or 0
        roads_km = row['Roads_Km'] or 0
        water_plants = row['Water_Treatment_Plants'] or 1  # Avoid division by zero
        population = row['Population'] or 1
        
        # Calculate infrastructure capacity index
        # Normalize different infrastructure types
        road_capacity = roads_km / max(population / 1000, 1)  # Km per 1000 people
        water_capacity = (water_plants * 1000) / max(population / 10000, 1)  # Capacity per 10k people
        
        # Infrastructure capacity score (inverse - higher capacity = lower strain)
        total_capacity = (road_capacity * 0.6) + (water_capacity * 0.4)
        capacity_factor = 1.0 / max(total_capacity, 0.1)  # Inverse relationship
        
        # Service request volume per capita
        request_density = service_count / max(population / 1000, 1)
        
        # Demand forecast: Check trend from recent requests
        trend_row = trend_df[trend_df['District'] == dist] if not trend_df.empty else pd.DataFrame()
        if not trend_row.empty:
            recent_requests = trend_row.iloc[0]['recent_requests'] or 0
            # Forecast: if recent requests high, predict increasing demand
            forecast_multiplier = 1.2 if recent_requests > service_count * 0.3 else 1.0
        else:
            forecast_multiplier = 1.0
        
        # ISS formula: (Request Volume / Capacity) × Forecast
        iss_raw = (request_density * capacity_factor) * forecast_multiplier
        
        # Normalize to 0-10 scale - improved scaling factor
        iss_score = min(10.0, max(0.0, iss_raw * 2.0))  # Better scaling factor
        
        # If no service requests, ISS should be low (good), not 0
        if service_count == 0:
            iss_score = 0.5  # Minimal strain when no requests
        
        # Additional factors
        if service_count > 100 and roads_km < 100:
            iss_score += 1.5  # High demand, low capacity
        
        iss_scores[dist] = min(10.0, iss_score)
    
    return iss_scores


def get_infrastructure_demand_forecast(district: Optional[str] = None) -> Dict[str, Dict]:
    """
    Get detailed infrastructure demand forecast.
    
    Args:
        district: Optional district name
    
    Returns:
        Dictionary with district forecasts
    """
    iss_scores = calculate_iss(district)
    
    query = """
    SELECT 
        d."District",
        d."Roads_Km",
        d."Water_Treatment_Plants",
        COUNT(DISTINCT s."Request_ID") as total_requests,
        COUNT(DISTINCT CASE WHEN s."Service_Category" = 'Infrastructure' THEN s."Request_ID" END) as infrastructure_requests,
        AVG(s."Resolution_Time_Hours") as avg_resolution_time
    FROM area_wise_demographics_infrastructure d
    LEFT JOIN service_request_details s ON d."District" = s."District"
    WHERE d."District" IS NOT NULL
    """
    
    if district:
        query += f" AND d.\"District\" = '{district}'"
    
    query += " GROUP BY d.\"District\", d.\"Roads_Km\", d.\"Water_Treatment_Plants\""
    
    df = execute_query_dataframe(query)
    
    forecasts = {}
    
    for dist, iss in iss_scores.items():
        district_data = df[df['District'] == dist]
        if district_data.empty:
            continue
        
        row = district_data.iloc[0]
        
        # Demand indicators
        indicators = []
        if (row['infrastructure_requests'] or 0) > 50:
            indicators.append("High infrastructure request volume")
        if (row['avg_resolution_time'] or 0) > 72:
            indicators.append("Slow resolution times (>72 hours)")
        if (row['Roads_Km'] or 0) < 100 and (row['infrastructure_requests'] or 0) > 20:
            indicators.append("Insufficient road infrastructure")
        
        forecasts[dist] = {
            "iss_score": iss,
            "roads_km": float(row['Roads_Km'] or 0),
            "water_plants": int(row['Water_Treatment_Plants'] or 0),
            "total_requests": int(row['total_requests'] or 0),
            "infrastructure_requests": int(row['infrastructure_requests'] or 0),
            "avg_resolution_time": float(row['avg_resolution_time'] or 0),
            "demand_indicators": indicators,
            "severity": "CRITICAL" if iss > 7 else "WARNING" if iss > 5 else "INFO"
        }
    
    return forecasts

