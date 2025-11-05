"""
Health Vulnerability Index (HVI) Calculator.
Predicts disease spikes and identifies capacity shortfalls.
"""

from typing import Dict, List, Optional
from agents.tools.database_tool import execute_query_dataframe
import pandas as pd
import numpy as np


def calculate_hvi(district: Optional[str] = None) -> Dict[str, float]:
    """
    Calculate Health Vulnerability Index for district(s).
    
    Formula: HVI = (Predicted Emergency Cases / ICU Beds) × (Bed Occupancy Rate / Capacity)
    
    Args:
        district: Optional district name. If None, calculates for all districts.
    
    Returns:
        Dictionary mapping district names to HVI scores (0-10 scale)
    """
    # Query health infrastructure data
    query = """
    SELECT 
        h."District",
        h."ICU_Beds",
        h."Avg_Bed_Occupancy_Rate",
        h."Emergency_Cases_Per_Month",
        h."Total_Beds",
        a."Population",
        a."Hospitals",
        a."Primary_Health_Centers"
    FROM health_infrastructure_data h
    LEFT JOIN area_wise_demographics_infrastructure a 
        ON h."District" = a."District"
    WHERE h."District" IS NOT NULL
    """
    
    if district:
        query += f" AND h.\"District\" = '{district}'"
    
    df = execute_query_dataframe(query)
    
    if df.empty:
        return {}
    
    hvi_scores = {}
    
    for _, row in df.iterrows():
        dist = row['District']
        
        # Get base values
        icu_beds = row['ICU_Beds'] or 1  # Avoid division by zero
        emergency_cases = row['Emergency_Cases_Per_Month'] or 0
        bed_occupancy = row['Avg_Bed_Occupancy_Rate'] or 0
        total_beds = row['Total_Beds'] or 1
        population = row['Population'] or 1
        
        # Predict emergency cases (simple trend: assume 10% monthly increase if occupancy high)
        predicted_emergency = emergency_cases
        if bed_occupancy > 80:
            # High occupancy suggests increasing demand
            predicted_emergency = emergency_cases * 1.15  # 15% predicted increase
        
        # Calculate components
        emergency_ratio = predicted_emergency / icu_beds if icu_beds > 0 else 10.0
        occupancy_ratio = bed_occupancy / 100.0  # Normalize to 0-1
        
        # HVI formula: (Predicted Emergency Cases / ICU Beds) × (Bed Occupancy Rate)
        hvi_raw = emergency_ratio * occupancy_ratio
        
        # Normalize to 0-10 scale (cap at 10)
        hvi_score = min(10.0, max(0.0, hvi_raw))
        
        # Adjust based on capacity shortfall
        if icu_beds < 10 and population > 100000:
            hvi_score += 2.0  # Significant capacity shortfall
        
        hvi_scores[dist] = min(10.0, hvi_score)
    
    return hvi_scores


def get_health_vulnerability_predictions(district: Optional[str] = None) -> Dict[str, Dict]:
    """
    Get detailed health vulnerability predictions including risk factors.
    
    Args:
        district: Optional district name
    
    Returns:
        Dictionary with district predictions
    """
    hvi_scores = calculate_hvi(district)
    
    query = """
    SELECT 
        "District",
        "ICU_Beds",
        "Emergency_Cases_Per_Month",
        "Avg_Bed_Occupancy_Rate",
        "Doctors",
        "Nurses",
        "Ambulances"
    FROM health_infrastructure_data
    WHERE "District" IS NOT NULL
    """
    
    if district:
        query += f" AND \"District\" = '{district}'"
    
    df = execute_query_dataframe(query)
    
    predictions = {}
    
    for dist, hvi in hvi_scores.items():
        district_data = df[df['District'] == dist]
        if district_data.empty:
            continue
        
        row = district_data.iloc[0]
        
        # Risk indicators
        risks = []
        if row['Avg_Bed_Occupancy_Rate'] > 85:
            risks.append("High bed occupancy (>85%)")
        if (row['ICU_Beds'] or 0) < 20:
            risks.append("Low ICU bed capacity")
        if (row['Emergency_Cases_Per_Month'] or 0) > 500:
            risks.append("High emergency case volume")
        
        predictions[dist] = {
            "hvi_score": hvi,
            "icu_beds": int(row['ICU_Beds'] or 0),
            "emergency_cases": int(row['Emergency_Cases_Per_Month'] or 0),
            "bed_occupancy": float(row['Avg_Bed_Occupancy_Rate'] or 0),
            "doctors": int(row['Doctors'] or 0),
            "nurses": int(row['Nurses'] or 0),
            "ambulances": int(row['Ambulances'] or 0),
            "risk_factors": risks,
            "severity": "CRITICAL" if hvi > 7 else "WARNING" if hvi > 5 else "INFO"
        }
    
    return predictions

