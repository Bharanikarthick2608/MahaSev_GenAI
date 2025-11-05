"""
Resource Allocation Agent.
Calculates Resource Contention Score (RCS) and audits worker utilization.
"""

from typing import Dict, List, Any, Optional
from metrics.rcs import calculate_rcs, get_resource_utilization_metrics



class ResourceAgent:
    """Agent focused on worker resource utilization and availability."""
    
    def __init__(self):
        self.name = "ResourceAgent"
        self.description = "Analyzes worker utilization and resource contention"
    
    def execute(self, district: Optional[str] = None, action: str = "calculate_rcs") -> Dict[str, Any]:
        """
        Execute resource contention analysis.
        
        Args:
            district: Optional district name. If None, analyzes all districts.
            action: Action to perform ("calculate_rcs" or "utilization_metrics")
        
        Returns:
            Dictionary with RCS scores and analysis
        """
        try:
            if action == "calculate_rcs":
                rcs_scores = calculate_rcs(district)
                
                return {
                    "success": True,
                    "rcs_scores": rcs_scores,
                    "agent": self.name,
                    "metric": "RCS"
                }
            
            elif action == "utilization_metrics":
                metrics = get_resource_utilization_metrics(district)
                
                return {
                    "success": True,
                    "metrics": metrics,
                    "agent": self.name,
                    "metric": "RCS"
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
    
    def identify_resource_contention(self, threshold: float = 7.0) -> List[Dict[str, Any]]:
        """
        Identify districts with critical resource contention.
        
        Args:
            threshold: RCS threshold for critical status
        
        Returns:
            List of districts with critical resource issues
        """
        metrics = get_resource_utilization_metrics()
        contended_districts = []
        
        for district, data in metrics.items():
            if data.get("rcs_score", 0) > threshold:
                contended_districts.append({
                    "district": district,
                    "rcs_score": data.get("rcs_score"),
                    "severity": data.get("severity"),
                    "issues": data.get("issues", []),
                    "recommendations": self._generate_resource_recommendations(data)
                })
        
        return sorted(contended_districts, key=lambda x: x["rcs_score"], reverse=True)
    
    def _generate_resource_recommendations(self, resource_data: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on resource data."""
        recommendations = []
        rcs = resource_data.get("rcs_score", 0)
        
        if rcs > 8.0:
            recommendations.append("IMMEDIATE: Deploy additional workers or reassign from other districts")
        if resource_data.get("utilization_rate", 0) > 90:
            recommendations.append("Reduce worker workload to prevent burnout")
        if resource_data.get("available_workers", 0) < resource_data.get("total_workers", 1) * 0.15:
            recommendations.append("Activate reserve worker pool or hire temporary staff")
        if resource_data.get("escalated_requests", 0) > resource_data.get("total_requests", 1) * 0.2:
            recommendations.append("Improve worker assignment based on experience and workload")
        
        return recommendations

