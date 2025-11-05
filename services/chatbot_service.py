"""
Chatbot Service using Groq.
Interfaces with Supervisor Agent to provide natural language responses.
"""

from typing import Dict, List, Optional, Any
from agents.supervisor import SupervisorAgent
# Commented out Gemini - using Groq instead
# from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
import os


class ChatbotService:
    """
    Chatbot service that processes admin queries and routes to Supervisor Agent.
    """
    
    def __init__(self):
        self.supervisor = SupervisorAgent()
        self.conversation_history: List[Dict] = []
        
        # Commented out Gemini - using Groq instead
        # api_key = os.getenv("GEMINI_API_KEY")
        # if api_key:
        #     self.gemini = ChatGoogleGenerativeAI(
        #         model="gemini-pro",
        #         google_api_key=api_key,
        #         temperature=0.5  # Higher temperature for more conversational responses
        #     )
        # else:
        #     self.gemini = None
        
        # Initialize Groq for chat interface
        groq_api_key = os.getenv("GROQ_API_KEY","")
        self.groq = ChatGroq(
            model="llama-3.3-70b-versatile",

            groq_api_key=groq_api_key,
            temperature=0.5  # Higher temperature for more conversational responses
        )
        # Keep gemini attribute for backward compatibility
        self.gemini = self.groq
    
    def process_query(self, query: str, district: Optional[str] = None, context: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Process admin query and return response.
        
        Args:
            query: Natural language query
            district: Optional district to focus on
            context: Optional conversation context
        
        Returns:
            Dictionary with response, XAI log, and metadata
        """
        try:
            # Add to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": query,
                "district": district
            })
            
            # Execute supervisor agent
            supervisor_result = self.supervisor.execute(query, district)
            
            # Format response for chatbot
            if supervisor_result.get("success"):
                response = supervisor_result.get("response", "No response generated")
                
                # Enhance response with chatbot formatting if Groq available
                if self.groq and len(response) > 0:
                    try:
                        formatted_response = self._format_chatbot_response(query, response, supervisor_result)
                    except Exception as e:
                        # If formatting fails, use raw response
                        print(f"Warning: Response formatting failed: {str(e)}")
                        formatted_response = response
                else:
                    formatted_response = response
                
                # Add to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": formatted_response,
                    "xai_log": supervisor_result.get("xai_log", [])
                })
                
                return {
                    "success": True,
                    "response": formatted_response,
                    "xai_log": supervisor_result.get("xai_log", []),
                    "agent_results": supervisor_result.get("agent_results", []),
                    "conversation_id": len(self.conversation_history) // 2
                }
            else:
                error_msg = supervisor_result.get("error", "Unknown error occurred")
                return {
                    "success": False,
                    "response": f"I encountered an error: {error_msg}",
                    "error": error_msg,
                    "xai_log": supervisor_result.get("xai_log", []),
                    "agent_results": supervisor_result.get("agent_results", [])
                }
        except Exception as e:
            # Catch any exceptions during processing
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error in ChatbotService.process_query: {error_trace}")
            
            error_msg = str(e)
            return {
                "success": False,
                "response": f"I encountered an error processing your query: {error_msg}",
                "error": error_msg,
                "xai_log": [],
                "agent_results": []
            }
    
    def _format_chatbot_response(self, query: str, raw_response: str, supervisor_result: Dict) -> str:
        """Format response for more conversational chatbot interaction."""
        if not self.groq:
            return raw_response
        
        formatting_prompt = f"""You are an administrative assistant chatbot. Convert this technical analysis into a clear, conversational response for an administrator.

User Query: {query}

Technical Response:
{raw_response}

Convert this into a friendly, professional chatbot response that:
1. Directly answers the question
2. Uses clear, non-technical language when possible
3. Highlights key insights and recommendations
4. Maintains a professional but approachable tone

Response:"""
        
        try:
            response = self.groq.invoke(formatting_prompt)
            return response.content
        except Exception:
            return raw_response
    
    def get_conversation_history(self, limit: int = 10) -> List[Dict]:
        """Get recent conversation history."""
        return self.conversation_history[-limit:]
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []

