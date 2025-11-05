"""
Cross-Sectoral Prioritization Score (P-Score) Calculator.
Combines HVI, ISS, and RCS into unified prioritization metric.
"""

from typing import Dict, List, Optional
from metrics.hvi import calculate_hvi
from metrics.iss import calculate_iss
from metrics.rcs import calculate_rcs
from metrics.sel import calculate_sel_index


def calculate_p_score(district: Optional[str] = None, weights: Optional[Dict[str, float]] = None) -> Dict[str, float]:
    """
    Calculate Cross-Sectoral Prioritization Score (P-Score).
    
    Formula: P-Score = (w1 × HVI + w2 × ISS + w3 × RCS) / (w1 + w2 + w3)
    
    Additional cross-sectoral metrics:
    - Health Crisis vs. Worker Capacity Gap: HVI × RCS
    - Service Equity Lag: SEL Index
    
    Args:
        district: Optional district name. If None, calculates for all districts.
        weights: Optional weights for HVI, ISS, RCS. Default: equal weights.
    
    Returns:
        Dictionary mapping district names to P-Scores (0-10 scale)
    """
    try:
        if weights is None:
            weights = {"hvi": 0.4, "iss": 0.3, "rcs": 0.3}
        
        # Get component scores with error handling
        try:
            hvi_scores = calculate_hvi(district)
        except Exception as e:
            print(f"Warning: Error calculating HVI: {str(e)}")
            hvi_scores = {}
        
        try:
            iss_scores = calculate_iss(district)
        except Exception as e:
            print(f"Warning: Error calculating ISS: {str(e)}")
            iss_scores = {}
        
        try:
            rcs_scores = calculate_rcs(district)
        except Exception as e:
            print(f"Warning: Error calculating RCS: {str(e)}")
            rcs_scores = {}
        
        # Validate scores are not empty
        if not hvi_scores and not iss_scores and not rcs_scores:
            print(f"Warning: No metric scores available for district: {district}")
            return {}
        
        # Get all unique districts
        all_districts = set(hvi_scores.keys()) | set(iss_scores.keys()) | set(rcs_scores.keys())
        
        if not all_districts:
            return {}
        
        p_scores = {}
        
        for dist in all_districts:
            try:
                hvi = hvi_scores.get(dist, 0.0)
                iss = iss_scores.get(dist, 0.0)
                rcs = rcs_scores.get(dist, 0.0)
                
                # Validate scores are numeric
                if not isinstance(hvi, (int, float)) or not isinstance(iss, (int, float)) or not isinstance(rcs, (int, float)):
                    print(f"Warning: Non-numeric score for district {dist}: HVI={hvi}, ISS={iss}, RCS={rcs}")
                    continue
                
                # Weighted average
                total_weight = weights.get("hvi", 0.4) + weights.get("iss", 0.3) + weights.get("rcs", 0.3)
                weighted_sum = (hvi * weights.get("hvi", 0.4) + 
                               iss * weights.get("iss", 0.3) + 
                               rcs * weights.get("rcs", 0.3))
                
                p_score = weighted_sum / total_weight if total_weight > 0 else 0.0
                
                # Apply cross-sectoral multiplier: Health Crisis vs. Worker Capacity Gap
                health_worker_gap = hvi * rcs / 10.0  # Normalize
                if health_worker_gap > 5.0:  # Critical gap
                    p_score *= 1.2  # Boost priority
                
                # Cap at 10
                p_scores[dist] = min(10.0, max(0.0, p_score))
            except Exception as e:
                print(f"Warning: Error calculating P-Score for district {dist}: {str(e)}")
                continue
        
        return p_scores
    
    except Exception as e:
        print(f"Error calculating P-Score: {str(e)}")
        import traceback
        traceback.print_exc()
        return {}


def get_comprehensive_p_score(district: Optional[str] = None) -> Dict[str, Dict]:
    """
    Get comprehensive P-Score with all component metrics and cross-sectoral analysis.
    
    Args:
        district: Optional district name
    
    Returns:
        Dictionary with detailed P-Score analysis per district
    """
    try:
        p_scores = calculate_p_score(district)
        
        if not p_scores:
            return {}
        
        # Get all component details
        from metrics.hvi import get_health_vulnerability_predictions
        from metrics.iss import get_infrastructure_demand_forecast
        from metrics.rcs import get_resource_utilization_metrics
        from metrics.sel import get_equity_analysis
        
        hvi_details = get_health_vulnerability_predictions(district)
        iss_details = get_infrastructure_demand_forecast(district)
        rcs_details = get_resource_utilization_metrics(district)
        sel_details = get_equity_analysis(district)
        
        comprehensive = {}
        
        for dist, p_score in p_scores.items():
            hvi_detail = hvi_details.get(dist, {})
            iss_detail = iss_details.get(dist, {})
            rcs_detail = rcs_details.get(dist, {})
            sel_detail = sel_details.get(dist, {})
            
            # Calculate cross-sectoral gaps
            hvi_score = hvi_detail.get("hvi_score", 0.0)
            rcs_score = rcs_detail.get("rcs_score", 0.0)
            health_worker_gap = (hvi_score * rcs_score) / 10.0
            
            # Compile all insights
            all_issues = []
            all_issues.extend(hvi_detail.get("risk_factors", []))
            all_issues.extend(iss_detail.get("demand_indicators", []))
            all_issues.extend(rcs_detail.get("issues", []))
            if sel_detail.get("has_equity_gap", False):
                all_issues.extend(sel_detail.get("equity_issues", []))
            
            # Generate recommendations
            recommendations = []
            if p_score > 8.0:
                recommendations.append("IMMEDIATE ACTION REQUIRED: Cross-sectoral intervention needed")
            if health_worker_gap > 6.0:
                recommendations.append("Health-Worker Capacity Gap: Consider resource reallocation")
            if sel_detail.get("sel_index", 1.0) > 1.3:
                recommendations.append("Equity Intervention: Address service delivery disparities")
            if hvi_score > 7.0:
                recommendations.append(f"Health Vulnerability: District needs {dist} health infrastructure support")
            if iss_detail.get("iss_score", 0.0) > 7.0:
                recommendations.append("Infrastructure Strain: Increase infrastructure capacity")
            if rcs_score > 7.0:
                recommendations.append("Resource Contention: Deploy additional workers or optimize allocation")
            
            comprehensive[dist] = {
                "p_score": p_score,
                "hvi_score": hvi_score,
                "iss_score": iss_detail.get("iss_score", 0.0),
                "rcs_score": rcs_score,
                "sel_index": sel_detail.get("sel_index", 1.0),
                "health_worker_capacity_gap": health_worker_gap,
                "priority_level": "CRITICAL" if p_score > 8.0 else "HIGH" if p_score > 6.0 else "MEDIUM" if p_score > 4.0 else "LOW",
                "all_issues": all_issues,
                "recommendations": recommendations,
                "component_details": {
                    "health": hvi_detail,
                    "infrastructure": iss_detail,
                    "resource": rcs_detail,
                    "equity": sel_detail
                }
            }
        
        return comprehensive
    
    except Exception as e:
        print(f"Error in get_comprehensive_p_score: {str(e)}")
        import traceback
        traceback.print_exc()
        return {}

