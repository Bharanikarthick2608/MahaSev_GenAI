"""
Infrastructure & Demand Agent.
Calculates Infrastructure Strain Score (ISS) and forecasts service request volume.
"""

from typing import Dict, List, Any, Optional
from metrics.iss import calculate_iss, get_infrastructure_demand_forecast


class InfrastructureAgent:
    """Agent focused on infrastructure capacity and demand forecasting."""
    
    def __init__(self):
        self.name = "InfrastructureAgent"
        self.description = "Analyzes infrastructure strain and forecasts demand"
    
    def execute(self, district: Optional[str] = None, action: str = "calculate_iss") -> Dict[str, Any]:
        """
        Execute infrastructure strain analysis.
        
        Args:
            district: Optional district name. If None, analyzes all districts.
            action: Action to perform ("calculate_iss" or "demand_forecast")
        
        Returns:
            Dictionary with ISS scores and analysis
        """
        try:
            if action == "calculate_iss":
                iss_scores = calculate_iss(district)
                
                return {
                    "success": True,
                    "iss_scores": iss_scores,
                    "agent": self.name,
                    "metric": "ISS"
                }
            
            elif action == "demand_forecast":
                forecasts = get_infrastructure_demand_forecast(district)
                
                return {
                    "success": True,
                    "forecasts": forecasts,
                    "agent": self.name,
                    "metric": "ISS"
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "agent": self.name
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "agent": self.name
            }
    
    def identify_infrastructure_strain(self, threshold: float = 7.0) -> List[Dict[str, Any]]:
        """
        Identify districts with critical infrastructure strain.
        
        Args:
            threshold: ISS threshold for critical status
        
        Returns:
            List of districts with critical infrastructure issues
        """
        forecasts = get_infrastructure_demand_forecast()
        strained_districts = []
        
        for district, data in forecasts.items():
            if data.get("iss_score", 0) > threshold:
                strained_districts.append({
                    "district": district,
                    "iss_score": data.get("iss_score"),
                    "severity": data.get("severity"),
                    "demand_indicators": data.get("demand_indicators", []),
                    "recommendations": self._generate_infrastructure_recommendations(data)
                })
        
        return sorted(strained_districts, key=lambda x: x["iss_score"], reverse=True)
    
    def _generate_infrastructure_recommendations(self, infra_data: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on infrastructure data."""
        recommendations = []
        iss = infra_data.get("iss_score", 0)
        
        if iss > 8.0:
            recommendations.append("IMMEDIATE: Deploy emergency infrastructure resources")
        if infra_data.get("roads_km", 0) < 100:
            recommendations.append("Urgent road infrastructure expansion needed")
        if infra_data.get("infrastructure_requests", 0) > 50:
            recommendations.append("Increase infrastructure maintenance workforce")
        if infra_data.get("avg_resolution_time", 0) > 72:
            recommendations.append("Optimize service request triage and routing")
        
        return recommendations

