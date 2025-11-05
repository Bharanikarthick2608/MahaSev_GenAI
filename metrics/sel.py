"""
Service Equity Lag Index (SEL) Calculator.
Identifies systemic bias by comparing resolution times across demographic segments.
"""

from typing import Dict, List, Optional
from agents.tools.database_tool import execute_query_dataframe
import pandas as pd


def calculate_sel_index(district: Optional[str] = None) -> Dict[str, float]:
    """
    Calculate Service Equity Lag Index for district(s).
    
    Formula: SEL = Average Resolution Time (Low Literacy Areas) / Average Resolution Time (High Literacy Areas)
    
    Args:
        district: Optional district name. If None, calculates for all districts.
    
    Returns:
        Dictionary mapping district names to SEL Index (ratio, >1.2 indicates equity gap)
    """
    # Query combining service requests with demographics
    query = """
    SELECT 
        s."District",
        s."Resolution_Time_Hours",
        d."Literacy_Rate",
        d."Avg_Income_INR",
        s."Service_Category",
        s."Status"
    FROM service_request_details s
    JOIN area_wise_demographics_infrastructure d ON s."District" = d."District"
    WHERE s."Resolution_Time_Hours" IS NOT NULL
        AND s."Status" IN ('Resolved', 'Closed')
        AND d."Literacy_Rate" IS NOT NULL
    """
    
    if district:
        query += f" AND s.\"District\" = '{district}'"
    
    df = execute_query_dataframe(query)
    
    if df.empty:
        return {}
    
    sel_scores = {}
    districts = df['District'].unique()
    
    for dist in districts:
        district_data = df[df['District'] == dist]
        
        # Define thresholds
        literacy_threshold = district_data['Literacy_Rate'].median() or 75.0
        income_threshold = district_data['Avg_Income_INR'].median() or 50000.0
        
        # Low literacy/income areas
        low_equity = district_data[
            (district_data['Literacy_Rate'] < literacy_threshold) | 
            (district_data['Avg_Income_INR'] < income_threshold)
        ]
        
        # High literacy/income areas
        high_equity = district_data[
            (district_data['Literacy_Rate'] >= literacy_threshold) & 
            (district_data['Avg_Income_INR'] >= income_threshold)
        ]
        
        if low_equity.empty or high_equity.empty:
            # Not enough data for comparison
            sel_scores[dist] = 1.0
            continue
        
        avg_resolution_low = low_equity['Resolution_Time_Hours'].mean()
        avg_resolution_high = high_equity['Resolution_Time_Hours'].mean()
        
        if avg_resolution_high == 0 or avg_resolution_high is None:
            sel_scores[dist] = 1.0
            continue
        
        # SEL Index: Ratio of low to high equity resolution times
        sel_ratio = avg_resolution_low / avg_resolution_high
        
        sel_scores[dist] = sel_ratio
    
    return sel_scores


def get_equity_analysis(district: Optional[str] = None) -> Dict[str, Dict]:
    """
    Get detailed equity analysis including resolution time comparisons.
    
    Args:
        district: Optional district name
    
    Returns:
        Dictionary with district equity analysis
    """
    sel_indices = calculate_sel_index(district)
    
    query = """
    SELECT 
        s."District",
        s."Resolution_Time_Hours",
        d."Literacy_Rate",
        d."Avg_Income_INR",
        s."Service_Category",
        s."Status"
    FROM service_request_details s
    JOIN area_wise_demographics_infrastructure d ON s."District" = d."District"
    WHERE s."Resolution_Time_Hours" IS NOT NULL
        AND s."Status" IN ('Resolved', 'Closed')
        AND d."Literacy_Rate" IS NOT NULL
    """
    
    if district:
        query += f" AND s.\"District\" = '{district}'"
    
    df = execute_query_dataframe(query)
    
    analyses = {}
    
    for dist, sel in sel_indices.items():
        district_data = df[df['District'] == dist]
        
        if district_data.empty:
            continue
        
        literacy_threshold = district_data['Literacy_Rate'].median() or 75.0
        income_threshold = district_data['Avg_Income_INR'].median() or 50000.0
        
        low_equity = district_data[
            (district_data['Literacy_Rate'] < literacy_threshold) | 
            (district_data['Avg_Income_INR'] < income_threshold)
        ]
        
        high_equity = district_data[
            (district_data['Literacy_Rate'] >= literacy_threshold) & 
            (district_data['Avg_Income_INR'] >= income_threshold)
        ]
        
        avg_resolution_low = float(low_equity['Resolution_Time_Hours'].mean() or 0)
        avg_resolution_high = float(high_equity['Resolution_Time_Hours'].mean() or 0)
        
        # Equity issues
        issues = []
        if sel > 1.2:
            issues.append(f"Significant equity gap detected (SEL: {sel:.2f})")
        if avg_resolution_low > avg_resolution_high * 1.5:
            issues.append("Resolution time is >50% longer in underserved areas")
        if low_equity.shape[0] > 0 and high_equity.shape[0] > 0:
            if low_equity['Resolution_Time_Hours'].median() > high_equity['Resolution_Time_Hours'].median() * 1.3:
                issues.append("Median resolution time gap exceeds 30%")
        
        analyses[dist] = {
            "sel_index": sel,
            "avg_resolution_low_equity_hours": avg_resolution_low,
            "avg_resolution_high_equity_hours": avg_resolution_high,
            "low_equity_sample_size": int(low_equity.shape[0]),
            "high_equity_sample_size": int(high_equity.shape[0]),
            "literacy_threshold": float(literacy_threshold),
            "income_threshold": float(income_threshold),
            "equity_issues": issues,
            "has_equity_gap": sel > 1.2,
            "severity": "CRITICAL" if sel > 1.5 else "WARNING" if sel > 1.2 else "INFO"
        }
    
    return analyses

