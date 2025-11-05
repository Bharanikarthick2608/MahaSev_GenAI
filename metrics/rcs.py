"""
Resource Contention Score (RCS) Calculator.
Audits worker utilization and availability against demand signals.
"""

from typing import Dict, List, Optional
from agents.tools.database_tool import execute_query_dataframe
import pandas as pd


def calculate_rcs(district: Optional[str] = None) -> Dict[str, float]:
    """
    Calculate Resource Contention Score for district(s).
    
    Formula: RCS = (Worker Utilization Rate / Available Workers) × (Escalated Requests / Total Requests)
    
    Args:
        district: Optional district name. If None, calculates for all districts.
    
    Returns:
        Dictionary mapping district names to RCS scores (0-10 scale)
    """
    # Query worker data and service requests
    query = """
    SELECT 
        w."District",
        w."Total_Workers",
        w."Available_Workers",
        w."Utilization_Rate_Percentage",
        w."On_Duty",
        w."Avg_Experience_Years",
        w."Avg_Response_Time_Minutes",
        w."Worker_Type"
    FROM public_workers_data w
    WHERE w."District" IS NOT NULL
    """
    
    if district:
        query += f" AND w.\"District\" = '{district}'"
    
    worker_df = execute_query_dataframe(query)
    
    if worker_df.empty:
        return {}
    
    # Query service request escalation data
    # Note: Escalated column is stored as text, so we compare as text strings
    escalation_query = """
    SELECT 
        "District",
        COUNT(*) as total_requests,
        SUM(CASE 
            WHEN LOWER(TRIM("Escalated"::text)) IN ('true', 't', '1', 'yes') 
            THEN 1 
            ELSE 0 
        END) as escalated_requests,
        COUNT(DISTINCT "Worker_Assigned") as assigned_workers_count
    FROM service_request_details
    WHERE "District" IS NOT NULL
    """
    
    if district:
        escalation_query += f" AND \"District\" = '{district}'"
    
    escalation_query += " GROUP BY \"District\""
    
    escalation_df = execute_query_dataframe(escalation_query)
    
    rcs_scores = {}
    
    # Aggregate worker data by district
    district_workers = {}
    for _, row in worker_df.iterrows():
        dist = row['District']
        if dist not in district_workers:
            district_workers[dist] = {
                'total_workers': 0,
                'available_workers': 0,
                'on_duty': 0,
                'utilization_rate': 0.0,
                'total_utilization': 0.0,
                'count': 0,
                'avg_experience': 0.0,
                'avg_response_time': 0.0
            }
        
        district_workers[dist]['total_workers'] += (row['Total_Workers'] or 0)
        district_workers[dist]['available_workers'] += (row['Available_Workers'] or 0)
        district_workers[dist]['on_duty'] += (row['On_Duty'] or 0)
        district_workers[dist]['total_utilization'] += (row['Utilization_Rate_Percentage'] or 0)
        district_workers[dist]['count'] += 1
        district_workers[dist]['avg_experience'] += (row['Avg_Experience_Years'] or 0)
        district_workers[dist]['avg_response_time'] += (row['Avg_Response_Time_Minutes'] or 0)
    
    # Calculate averages
    for dist in district_workers:
        count = district_workers[dist]['count']
        if count > 0:
            district_workers[dist]['utilization_rate'] = district_workers[dist]['total_utilization'] / count
            district_workers[dist]['avg_experience'] = district_workers[dist]['avg_experience'] / count
            district_workers[dist]['avg_response_time'] = district_workers[dist]['avg_response_time'] / count
    
    # Calculate RCS for each district
    for dist, worker_data in district_workers.items():
        utilization_rate = worker_data['utilization_rate']
        available_workers = max(worker_data['available_workers'], 1)  # Avoid division by zero
        total_workers = max(worker_data['total_workers'], 1)
        
        # Get escalation data for this district
        escalation_row = escalation_df[escalation_df['District'] == dist] if not escalation_df.empty else pd.DataFrame()
        
        if not escalation_row.empty:
            total_requests = escalation_row.iloc[0]['total_requests'] or 1
            escalated_requests = escalation_row.iloc[0]['escalated_requests'] or 0
            escalation_ratio = escalated_requests / total_requests
        else:
            escalation_ratio = 0.0
            # If no escalation data but workers exist, still calculate RCS
            if available_workers > 0:
                escalation_ratio = 0.1  # Default minimum
        
        # Availability ratio (inverse - fewer available = higher contention)
        availability_ratio = 1.0 - (available_workers / total_workers) if total_workers > 0 else 0.0
        
        # RCS formula: (Utilization Rate / Available Workers Ratio) × Escalation Ratio
        utilization_factor = utilization_rate / 100.0  # Normalize to 0-1
        availability_factor = availability_ratio  # Already 0-1
        
        rcs_raw = (utilization_factor * availability_factor) * (1 + escalation_ratio)
        
        # Scale to 0-10
        rcs_score = min(10.0, max(0.0, rcs_raw * 10))
        
        # Add minimum RCS if utilization is high but score is too low
        if utilization_rate > 50 and available_workers < total_workers * 0.5:
            rcs_score = max(rcs_score, 1.0)  # Minimum RCS if workers are strained
        
        # Additional penalties
        if utilization_rate > 90 and available_workers < total_workers * 0.1:
            rcs_score += 2.0  # Critical resource contention
        
        rcs_scores[dist] = min(10.0, rcs_score)
    
    return rcs_scores


def get_resource_utilization_metrics(district: Optional[str] = None) -> Dict[str, Dict]:
    """
    Get detailed resource utilization metrics.
    
    Args:
        district: Optional district name
    
    Returns:
        Dictionary with district utilization details
    """
    rcs_scores = calculate_rcs(district)
    
    query = """
    SELECT 
        "District",
        SUM("Total_Workers") as total_workers,
        SUM("Available_Workers") as available_workers,
        SUM("On_Duty") as on_duty,
        AVG("Utilization_Rate_Percentage") as avg_utilization,
        AVG("Avg_Experience_Years") as avg_experience,
        AVG("Avg_Response_Time_Minutes") as avg_response_time,
        COUNT(DISTINCT "Worker_Type") as worker_types
    FROM public_workers_data
    WHERE "District" IS NOT NULL
    """
    
    if district:
        query += f" AND \"District\" = '{district}'"
    
    query += " GROUP BY \"District\""
    
    worker_df = execute_query_dataframe(query)
    
    # Note: Escalated column is stored as text, so we compare as text strings
    escalation_query = """
    SELECT 
        "District",
        COUNT(*) as total_requests,
        SUM(CASE 
            WHEN LOWER(TRIM("Escalated"::text)) IN ('true', 't', '1', 'yes') 
            THEN 1 
            ELSE 0 
        END) as escalated_count,
        AVG("Resolution_Time_Hours") as avg_resolution_time
    FROM service_request_details
    WHERE "District" IS NOT NULL
    """
    
    if district:
        escalation_query += f" AND \"District\" = '{district}'"
    
    escalation_query += " GROUP BY \"District\""
    
    escalation_df = execute_query_dataframe(escalation_query)
    
    metrics = {}
    
    for dist, rcs in rcs_scores.items():
        worker_row = worker_df[worker_df['District'] == dist]
        escalation_row = escalation_df[escalation_df['District'] == dist] if not escalation_df.empty else pd.DataFrame()
        
        if worker_row.empty:
            continue
        
        wr = worker_row.iloc[0]
        
        utilization = float(wr['avg_utilization'] or 0)
        total_workers = int(wr['total_workers'] or 0)
        available_workers = int(wr['available_workers'] or 0)
        
        # Issues identified
        issues = []
        if utilization > 90:
            issues.append("Very high worker utilization (>90%)")
        if available_workers < total_workers * 0.15:
            issues.append("Low worker availability (<15%)")
        if not escalation_row.empty:
            escalated_count = escalation_row.iloc[0]['escalated_count'] or 0
            total_requests = escalation_row.iloc[0]['total_requests'] or 1
            if escalated_count / total_requests > 0.2:
                issues.append("High escalation rate (>20%)")
        
        metrics[dist] = {
            "rcs_score": rcs,
            "total_workers": total_workers,
            "available_workers": available_workers,
            "on_duty": int(wr['on_duty'] or 0),
            "utilization_rate": utilization,
            "avg_experience_years": float(wr['avg_experience'] or 0),
            "avg_response_time_minutes": float(wr['avg_response_time'] or 0),
            "worker_types": int(wr['worker_types'] or 0),
            "issues": issues,
            "severity": "CRITICAL" if rcs > 7 else "WARNING" if rcs > 5 else "INFO"
        }
        
        if not escalation_row.empty:
            metrics[dist]["total_requests"] = int(escalation_row.iloc[0]['total_requests'] or 0)
            metrics[dist]["escalated_requests"] = int(escalation_row.iloc[0]['escalated_count'] or 0)
            metrics[dist]["avg_resolution_time_hours"] = float(escalation_row.iloc[0]['avg_resolution_time'] or 0)
    
    return metrics

