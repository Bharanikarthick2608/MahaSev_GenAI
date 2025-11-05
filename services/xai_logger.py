"""
Explainable AI (XAI) Logger.
Tracks agent decisions and provides transparency logs for administrative trust.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json


class XAILogger:
    """
    Logs all agent decisions and provides explainable AI transparency.
    """
    
    def __init__(self):
        self.logs: List[Dict[str, Any]] = []
    
    def log_agent_decision(self, 
                          agent_name: str,
                          decision: str,
                          reasoning: str,
                          input_data: Optional[Dict] = None,
                          output_data: Optional[Dict] = None) -> str:
        """
        Log an agent decision with full context.
        
        Args:
            agent_name: Name of the agent making the decision
            decision: The decision made
            reasoning: Why this decision was made
            input_data: Input data to the agent
            output_data: Output data from the agent
        
        Returns:
            Log entry ID
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "decision": decision,
            "reasoning": reasoning,
            "input": input_data,
            "output": output_data
        }
        
        self.logs.append(log_entry)
        return log_entry["timestamp"]
    
    def log_p_score_calculation(self,
                               district: str,
                               p_score: float,
                               components: Dict[str, float],
                               weights: Dict[str, float],
                               recommendations: List[str]) -> str:
        """
        Log P-Score calculation with full breakdown.
        
        Args:
            district: District name
            p_score: Final P-Score
            components: Component scores (HVI, ISS, RCS)
            weights: Weights used in calculation
            recommendations: Generated recommendations
        
        Returns:
            Log entry ID
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "p_score_calculation",
            "district": district,
            "p_score": p_score,
            "components": components,
            "weights": weights,
            "recommendations": recommendations,
            "explanation": self._explain_p_score(p_score, components, weights)
        }
        
        self.logs.append(log_entry)
        return log_entry["timestamp"]
    
    def _explain_p_score(self, p_score: float, components: Dict[str, float], weights: Dict[str, float]) -> str:
        """Generate human-readable explanation of P-Score calculation."""
        explanations = [f"P-Score: {p_score:.2f}/10"]
        
        # Explain components
        for metric, score in components.items():
            weight = weights.get(metric.lower(), 0.0)
            contribution = score * weight
            explanations.append(f"{metric.upper()}: {score:.2f} (weight: {weight:.1%}, contribution: {contribution:.2f})")
        
        # Explain severity
        if p_score > 8.0:
            explanations.append("Priority Level: CRITICAL - Immediate cross-sectoral intervention required")
        elif p_score > 6.0:
            explanations.append("Priority Level: HIGH - Significant multi-sector attention needed")
        elif p_score > 4.0:
            explanations.append("Priority Level: MEDIUM - Monitor closely and plan interventions")
        else:
            explanations.append("Priority Level: LOW - Stable conditions")
        
        return "\n".join(explanations)
    
    def get_logs_for_query(self, query: str, limit: int = 10) -> List[Dict]:
        """Get logs related to a specific query."""
        # Simple implementation - in production, would use proper filtering
        return self.logs[-limit:]
    
    def get_logs_by_agent(self, agent_name: str, limit: int = 20) -> List[Dict]:
        """Get logs for a specific agent."""
        agent_logs = [log for log in self.logs if log.get("agent") == agent_name]
        return agent_logs[-limit:]
    
    def export_logs(self, format: str = "json") -> str:
        """
        Export all logs in specified format.
        
        Args:
            format: Export format ("json" or "text")
        
        Returns:
            Exported logs as string
        """
        if format == "json":
            return json.dumps(self.logs, indent=2, default=str)
        else:
            lines = []
            for log in self.logs:
                lines.append(f"[{log['timestamp']}] {log.get('agent', 'System')}: {log.get('decision', '')}")
                if log.get('reasoning'):
                    lines.append(f"  Reasoning: {log['reasoning']}")
            return "\n".join(lines)
    
    def clear_logs(self):
        """Clear all logs."""
        self.logs = []


# Global XAI logger instance
xai_logger = XAILogger()

