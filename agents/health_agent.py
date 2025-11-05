"""
Health & Vulnerability Agent.
Calculates Health Vulnerability Index (HVI) and predicts health capacity shortfalls.
"""

from typing import Dict, List, Any, Optional
from metrics.hvi import calculate_hvi, get_health_vulnerability_predictions


class HealthAgent:
    """Agent focused on health infrastructure and vulnerability analysis."""
    
    def __init__(self):
        self.name = "HealthAgent"
        self.description = "Analyzes health infrastructure capacity and predicts vulnerability"
    
    def execute(self, district: Optional[str] = None, action: str = "calculate_hvi") -> Dict[str, Any]:
        """
        Execute health vulnerability analysis.
        
        Args:
            district: Optional district name. If None, analyzes all districts.
            action: Action to perform ("calculate_hvi" or "detailed_analysis")
        
        Returns:
            Dictionary with HVI scores and analysis
        """
        try:
            if action == "calculate_hvi":
                hvi_scores = calculate_hvi(district)
                
                return {
                    "success": True,
                    "hvi_scores": hvi_scores,
                    "agent": self.name,
                    "metric": "HVI"
                }
            
            elif action == "detailed_analysis":
                predictions = get_health_vulnerability_predictions(district)
                
                return {
                    "success": True,
                    "predictions": predictions,
                    "agent": self.name,
                    "metric": "HVI"
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
    
    def identify_health_crises(self, threshold: float = 7.0) -> List[Dict[str, Any]]:
        """
        Identify districts with critical health vulnerability.
        
        Args:
            threshold: HVI threshold for critical status
        
        Returns:
            List of districts with critical health issues
        """
        predictions = get_health_vulnerability_predictions()
        crises = []
        
        for district, data in predictions.items():
            if data.get("hvi_score", 0) > threshold:
                crises.append({
                    "district": district,
                    "hvi_score": data.get("hvi_score"),
                    "severity": data.get("severity"),
                    "risk_factors": data.get("risk_factors", []),
                    "recommendations": self._generate_health_recommendations(data)
                })
        
        return sorted(crises, key=lambda x: x["hvi_score"], reverse=True)
    
    def _generate_health_recommendations(self, health_data: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on health data."""
        recommendations = []
        hvi = health_data.get("hvi_score", 0)
        
        if hvi > 8.0:
            recommendations.append("IMMEDIATE: Deploy emergency medical resources")
        if health_data.get("bed_occupancy", 0) > 85:
            recommendations.append("Increase hospital bed capacity immediately")
        if health_data.get("icu_beds", 0) < 20:
            recommendations.append("Deploy temporary ICU facilities")
        if health_data.get("emergency_cases", 0) > 500:
            recommendations.append("Activate emergency response protocols")
        
        return recommendations

