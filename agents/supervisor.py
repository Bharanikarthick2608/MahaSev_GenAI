"""
Supervisor Agent using LangGraph.
Orchestrates specialist agents and synthesizes cross-sectoral intelligence.
"""

from typing import Dict, List, Any, Optional, Annotated
try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
# Commented out Gemini - using Groq instead
# from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
import os
import json

from agents.data_retrieval_agent import DataRetrievalAgent
from agents.health_agent import HealthAgent
from agents.infrastructure_agent import InfrastructureAgent
from agents.resource_agent import ResourceAgent
from metrics.p_score import get_comprehensive_p_score


class SupervisorState(TypedDict):
    """State passed between agent nodes in the graph."""
    query: str
    current_district: Optional[str]
    agent_results: Annotated[List[Dict], "List of results from specialist agents"]
    final_response: Optional[str]
    xai_log: Annotated[List[Dict], "Explainable AI log entries"]
    error: Optional[str]


class SupervisorAgent:
    """
    Supervisor Agent that coordinates specialist agents using LangGraph.
    Routes queries to appropriate agents and synthesizes final responses.
    """
    
    def __init__(self):
        self.name = "SupervisorAgent"
        self.description = "Coordinates specialist agents for cross-sectoral intelligence"
        
        # Initialize specialist agents
        self.data_agent = DataRetrievalAgent()
        self.health_agent = HealthAgent()
        self.infrastructure_agent = InfrastructureAgent()
        self.resource_agent = ResourceAgent()
        
        # Commented out Gemini - using Groq instead
        # api_key = os.getenv("GEMINI_API_KEY")
        # if api_key:
        #     self.gemini = ChatGoogleGenerativeAI(
        #         model="gemini-pro",
        #         google_api_key=api_key,
        #         temperature=0.3
        #     )
        # else:
        #     self.gemini = None
        
        # Initialize Groq for routing and synthesis
        groq_api_key = os.getenv("GROQ_API_KEY","")
        self.groq = ChatGroq(
            model="llama-3.3-70b-versatile",
            groq_api_key=groq_api_key,
            temperature=0.3
        )
        # Keep gemini attribute for backward compatibility
        self.gemini = self.groq
        
        # Build LangGraph workflow
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine."""
        workflow = StateGraph(SupervisorState)
        
        # Add nodes
        workflow.add_node("route", self._route_query)
        workflow.add_node("data_retrieval", self._data_retrieval_node)
        workflow.add_node("health_analysis", self._health_analysis_node)
        workflow.add_node("infrastructure_analysis", self._infrastructure_analysis_node)
        workflow.add_node("resource_analysis", self._resource_analysis_node)
        workflow.add_node("synthesize", self._synthesize_results)
        
        # Set entry point
        workflow.set_entry_point("route")
        
        # Add edges from route
        workflow.add_conditional_edges(
            "route",
            self._should_invoke_agent,
            {
                "data": "data_retrieval",
                "health": "health_analysis",
                "infrastructure": "infrastructure_analysis",
                "resource": "resource_analysis",
                "synthesize": "synthesize",
                "end": END
            }
        )
        
        # All specialist agents flow to synthesize
        workflow.add_edge("data_retrieval", "synthesize")
        workflow.add_edge("health_analysis", "synthesize")
        workflow.add_edge("infrastructure_analysis", "synthesize")
        workflow.add_edge("resource_analysis", "synthesize")
        
        # Synthesize flows to end
        workflow.add_edge("synthesize", END)
        
        return workflow.compile()
    
    def _route_query(self, state: SupervisorState) -> SupervisorState:
        """
        Route query to determine which agents to invoke.
        Uses Groq to analyze the query intent intelligently.
        """
        query = state.get("query", "")
        state["agent_results"] = []
        
        # Check for greetings first
        query_lower = query.lower().strip()
        greetings = ['hi', 'hello', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening', 'good night']
        if query_lower in greetings or any(query_lower.startswith(g) for g in greetings):
            state["final_response"] = "Hello! I'm the AI Admin Assistant. I can help you analyze districts, health infrastructure, resources, and service metrics. What would you like to know?"
            return state
        
        # Extract district names from query if not already set
        district = state.get("current_district")
        if not district:
            from agents.tools.database_tool import get_districts
            from agents.data_retrieval_agent import fuzzy_match_district
            available_districts = get_districts()
            
            # Try exact match first
            for dist in available_districts:
                if dist.lower() in query_lower:
                    district = dist
                    state["current_district"] = district
                    break
            
            # If no exact match, try fuzzy matching
            if not district:
                fuzzy_match = fuzzy_match_district(query, available_districts)
                if fuzzy_match:
                    district = fuzzy_match
                    state["current_district"] = district
        
        # Use Groq for intelligent routing with better context
        routing_prompt = f"""You are an intelligent query routing system for a cross-sectoral intelligence platform.

Available agents and their capabilities:
1. "data_retrieval" - Retrieves raw data from database tables. Use for:
   - Direct data queries ("show me", "list", "get", "how many")
   - Comparative queries across districts ("compare", "difference between")
   - Multi-district queries ("all districts", "across districts")
   - Specific metrics ("population", "roads", "workers count")

2. "health" - Analyzes health infrastructure and vulnerability (HVI). Use for:
   - Health vulnerability scores
   - ICU beds, emergency cases, bed occupancy
   - Health risk assessments
   - Health infrastructure capacity

3. "infrastructure" - Analyzes infrastructure strain and demand (ISS). Use for:
   - Infrastructure strain scores
   - Service request volumes
   - Road, water, electricity infrastructure
   - Infrastructure demand forecasts

4. "resource" - Analyzes worker utilization and resource contention (RCS). Use for:
   - Resource contention scores
   - Worker availability and utilization
   - Service request escalation rates
   - Worker response times

User Query: "{query}"

IMPORTANT ROUTING RULES:
- For queries asking "which district", "compare", "all districts", "across districts" → ALWAYS include "data_retrieval"
- For comparative queries mentioning multiple districts → include "data_retrieval" + relevant domain agents
- For queries asking specific metrics → include "data_retrieval" + relevant domain agent
- For general analysis queries → include all relevant agents

Analyze the query intent and determine which agent(s) should be invoked. Respond with valid JSON only:
{{
    "agents": ["agent1", "agent2"],
    "reasoning": "brief explanation of why these agents were chosen",
    "query_type": "comparative|multi_district|single_district|general"
}}

Agent names must be exactly: "data_retrieval", "health", "infrastructure", "resource"

Response (JSON only):"""
        
        try:
            response = self.groq.invoke(routing_prompt)
            response_text = response.content.strip()
            
            # Clean JSON response (remove markdown if present)
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
                response_text = response_text.strip().strip("`").strip()
            
            # Try to extract JSON from response
            if "{" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                if json_end > json_start:
                    response_text = response_text[json_start:json_end]
            
            routing_decision = json.loads(response_text)
            agents = routing_decision.get("agents", [])
            
            # Ensure at least one agent is selected
            if not agents:
                agents = ["data_retrieval"]
            
            state["xai_log"] = [{
                "step": "route",
                "decision": agents,
                "reasoning": routing_decision.get("reasoning", ""),
                "query_type": routing_decision.get("query_type", "general")
            }]
            
        except Exception as e:
            # Intelligent fallback routing
            query_lower = query.lower()
            agents = []
            
            # Check for comparative/multi-district keywords
            if any(word in query_lower for word in ["compare", "comparison", "difference", "between", "versus", "vs"]):
                agents.append("data_retrieval")
            if any(word in query_lower for word in ["all districts", "across districts", "every district", "which district"]):
                agents.append("data_retrieval")
            
            # Domain-specific routing
            if any(word in query_lower for word in ["health", "hospital", "bed", "icu", "emergency", "disease", "vulnerability"]):
                agents.append("health")
            if any(word in query_lower for word in ["infrastructure", "road", "water", "electricity", "service request", "strain"]):
                agents.append("infrastructure")
            if any(word in query_lower for word in ["worker", "resource", "utilization", "availability", "staff", "contention"]):
                agents.append("resource")
            
            # If no specific agents found, use data_retrieval as default
            if not agents:
                agents = ["data_retrieval"]
            
            state["xai_log"] = [{
                "step": "route",
                "decision": agents,
                "reasoning": f"Fallback routing based on keywords. Error: {str(e)}",
                "query_type": "fallback"
            }]
        
        return state
    
    def _should_invoke_agent(self, state: SupervisorState) -> str:
        """
        Conditional edge function to determine next step.
        Intelligently routes to appropriate agents based on routing decision.
        """
        if state.get("final_response"):
            return "end"
        
        xai_log = state.get("xai_log", [])
        agent_results = state.get("agent_results", [])
        executed_agents = [r.get("agent") for r in agent_results]
        
        # Get routing decision from log
        decision = []
        if xai_log:
            for log_entry in xai_log:
                if log_entry.get("step") == "route":
                    decision = log_entry.get("decision", [])
                    break
        
        # If no decision found, default to data_retrieval
        if not decision:
            decision = ["data_retrieval"]
        
        # Ensure decision is a list
        if not isinstance(decision, list):
            decision = ["data_retrieval"]
        
        # Route to agents in priority order
        # Priority: data_retrieval first (for comparative/multi-district queries), then domain agents
        if "data_retrieval" in decision and "DataRetrievalAgent" not in executed_agents:
            return "data"
        elif "health" in decision and "HealthAgent" not in executed_agents:
            return "health"
        elif "infrastructure" in decision and "InfrastructureAgent" not in executed_agents:
            return "infrastructure"
        elif "resource" in decision and "ResourceAgent" not in executed_agents:
            return "resource"
        else:
            # All agents executed, synthesize
            return "synthesize"
    
    def _data_retrieval_node(self, state: SupervisorState) -> SupervisorState:
        """Invoke Data Retrieval Agent."""
        query = state.get("query", "")
        district = state.get("current_district")
        
        result = self.data_agent.execute(query, district)
        state["agent_results"] = state.get("agent_results", []) + [result]
        
        # Enhanced logging with SQL query and data details
        log_entry = {
            "step": "data_retrieval",
            "agent": "DataRetrievalAgent",
            "result_summary": f"Retrieved {result.get('row_count', 0)} rows",
            "success": result.get("success", False)
        }
        
        if result.get("sql_query"):
            log_entry["sql_query"] = result.get("sql_query")
        
        if not result.get("success"):
            log_entry["error"] = result.get("error", "Unknown error")
        
        if result.get("mentioned_districts"):
            log_entry["mentioned_districts"] = result.get("mentioned_districts")
        
        state["xai_log"].append(log_entry)
        
        return state
    
    def _health_analysis_node(self, state: SupervisorState) -> SupervisorState:
        """Invoke Health Agent."""
        district = state.get("current_district")
        
        result = self.health_agent.execute(district, "detailed_analysis")
        state["agent_results"] = state.get("agent_results", []) + [result]
        
        log_entry = {
            "step": "health_analysis",
            "agent": "HealthAgent",
            "metric": "HVI",
            "success": result.get("success", False)
        }
        
        if result.get("hvi_scores"):
            log_entry["hvi_scores_count"] = len(result.get("hvi_scores", {}))
        
        if not result.get("success"):
            log_entry["error"] = result.get("error", "Unknown error")
        
        state["xai_log"].append(log_entry)
        
        return state
    
    def _infrastructure_analysis_node(self, state: SupervisorState) -> SupervisorState:
        """Invoke Infrastructure Agent."""
        district = state.get("current_district")
        
        # Use calculate_iss instead of demand_forecast to avoid triggering Nixtla forecasting
        result = self.infrastructure_agent.execute(district, "calculate_iss")
        state["agent_results"] = state.get("agent_results", []) + [result]
        
        log_entry = {
            "step": "infrastructure_analysis",
            "agent": "InfrastructureAgent",
            "metric": "ISS",
            "success": result.get("success", False)
        }
        
        if result.get("iss_scores"):
            log_entry["iss_scores_count"] = len(result.get("iss_scores", {}))
        
        if not result.get("success"):
            log_entry["error"] = result.get("error", "Unknown error")
        
        state["xai_log"].append(log_entry)
        
        return state
    
    def _resource_analysis_node(self, state: SupervisorState) -> SupervisorState:
        """Invoke Resource Agent."""
        district = state.get("current_district")
        
        result = self.resource_agent.execute(district, "utilization_metrics")
        state["agent_results"] = state.get("agent_results", []) + [result]
        
        log_entry = {
            "step": "resource_analysis",
            "agent": "ResourceAgent",
            "metric": "RCS",
            "success": result.get("success", False)
        }
        
        if result.get("rcs_scores"):
            log_entry["rcs_scores_count"] = len(result.get("rcs_scores", {}))
        
        if not result.get("success"):
            log_entry["error"] = result.get("error", "Unknown error")
        
        state["xai_log"].append(log_entry)
        
        return state
    
    def _synthesize_results(self, state: SupervisorState) -> SupervisorState:
        """Synthesize results from all agents into final response."""
        query = state.get("query", "")
        agent_results = state.get("agent_results", [])
        
        if not self.groq:
            # Simple synthesis without Groq
            summary = self._simple_synthesis(query, agent_results)
            state["final_response"] = summary
            return state
        
        # Use Groq for intelligent synthesis
        results_summary = json.dumps(agent_results, indent=2, default=str)
        
        # Check if this is a comparative or multi-district query
        query_lower = query.lower()
        is_comparative = any(word in query_lower for word in ["compare", "comparison", "difference", "between", "versus", "vs"])
        is_multi_district = any(word in query_lower for word in ["all districts", "across districts", "which district", "every district", "top", "highest", "lowest"])
        is_district_info = any(phrase in query_lower for phrase in ["tell about", "tell me about", "show information about", "information about", "details about"])
        
        synthesis_prompt = f"""You are an administrative intelligence analyst. Synthesize the following agent results into a clear, actionable response for an administrator.

Original Query: "{query}"

Agent Results:
{results_summary}

IMPORTANT INSTRUCTIONS:
{"- This is a COMPARATIVE query. Focus on comparing districts, highlighting differences, and providing clear comparisons." if is_comparative else ""}
{"- This is a MULTI-DISTRICT query. Present data for all districts mentioned, rank/compare them, and identify patterns across districts." if is_multi_district else ""}
{"- This is a DISTRICT INFORMATION query. Provide comprehensive information about the district including: (1) Key demographics (population, area), (2) Health infrastructure (hospitals, ICU beds, PHCs, emergency cases), (3) Infrastructure (roads, water treatment plants, electricity substations), (4) Worker resources (total workers, available workers, utilization rate), (5) Key metrics (HVI, ISS, RCS, P-Score if available), and (6) Overall assessment and recommendations." if is_district_info else ""}
- If agent_results contain data with multiple districts, organize the response by district for easy comparison
- If data is missing for some districts, clearly state what data is available and what is missing
- Use tables or structured format when comparing multiple districts
- For district information queries, provide a structured overview with all available metrics

Provide:
1. Direct answer to the query (if comparing, show clear comparison; if asking "which", name the district; if asking "tell about", provide comprehensive district overview)
2. Key insights and cross-sectoral connections
3. Specific recommendations (if applicable)
4. Priority level and urgency (if applicable)

Format your response as a clear, professional administrative briefing with proper structure."""

        try:
            response = self.groq.invoke(synthesis_prompt)
            state["final_response"] = response.content
            
            # Calculate P-Score if we have enough data
            district = state.get("current_district")
            if not district:
                # Try to extract district from results
                for result in agent_results:
                    if "district" in str(result):
                        # Extract district from results
                        break
            
            if district:
                p_score_data = get_comprehensive_p_score(district)
                if p_score_data:
                    state["xai_log"].append({
                        "step": "synthesize",
                        "p_score": p_score_data.get(district, {}),
                        "action": "calculated_p_score"
                    })
        
        except Exception as e:
            state["final_response"] = self._simple_synthesis(query, agent_results)
            state["xai_log"].append({"step": "synthesize", "error": str(e), "fallback": "simple_synthesis"})
        
        return state
    
    def _simple_synthesis(self, query: str, agent_results: List[Dict]) -> str:
        """Simple synthesis without LLM."""
        summary_parts = []
        
        # Extract actual data from agent results
        for result in agent_results:
            agent_name = result.get("agent", "Unknown")
            if result.get("success"):
                # For DataRetrievalAgent - show actual data
                if "results" in result and result["results"]:
                    data = result["results"]
                    if isinstance(data, list) and len(data) > 0:
                        # Format the data
                        if len(data) == 1:
                            # Single row result
                            row = data[0]
                            for key, value in row.items():
                                if value is not None:
                                    summary_parts.append(f"{key}: {value}")
                        else:
                            # Multiple rows
                            summary_parts.append(f"Found {len(data)} records:")
                            for i, row in enumerate(data[:5], 1):  # Show first 5
                                summary_parts.append(f"\n{i}. {', '.join(f'{k}: {v}' for k, v in row.items() if v is not None)}")
                            if len(data) > 5:
                                summary_parts.append(f"\n... and {len(data) - 5} more")
                
                # For metric agents - show scores
                if "hvi_scores" in result or "iss_scores" in result or "rcs_scores" in result:
                    if "hvi_scores" in result:
                        for district, score in result["hvi_scores"].items():
                            summary_parts.append(f"Health Vulnerability Index (HVI) for {district}: {score:.2f}/10")
                    if "iss_scores" in result:
                        for district, score in result["iss_scores"].items():
                            summary_parts.append(f"Infrastructure Strain Score (ISS) for {district}: {score:.2f}/10")
                    if "rcs_scores" in result:
                        for district, score in result["rcs_scores"].items():
                            summary_parts.append(f"Resource Contention Score (RCS) for {district}: {score:.2f}/10")
                
                # Show metrics if present
                if "metrics" in result:
                    for key, value in result["metrics"].items():
                        summary_parts.append(f"{key}: {value}")
            else:
                summary_parts.append(f"Error: {result.get('error', 'Unknown error')}")
        
        if not summary_parts:
            return "I couldn't find the requested information. Please try rephrasing your query."
        
        return "\n".join(summary_parts)
    
    def execute(self, query: str, district: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute supervisor agent workflow.
        
        Args:
            query: Natural language query from admin
            district: Optional district to focus on
        
        Returns:
            Complete response with synthesis and XAI log
        """
        initial_state: SupervisorState = {
            "query": query,
            "current_district": district,
            "agent_results": [],
            "final_response": None,
            "xai_log": [],
            "error": None
        }
        
        try:
            final_state = self.graph.invoke(initial_state)
            
            return {
                "success": True,
                "query": query,
                "response": final_state.get("final_response", "No response generated"),
                "xai_log": final_state.get("xai_log", []),
                "agent_results": final_state.get("agent_results", []),
                "district": district
            }
        
        except Exception as e:
            return {
                "success": False,
                "query": query,
                "error": str(e),
                "xai_log": initial_state.get("xai_log", [])
            }

