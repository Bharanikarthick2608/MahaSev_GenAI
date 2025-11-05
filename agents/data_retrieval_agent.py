"""

Data Retrieval Agent.
Translates natural language queries into optimized SQL and executes them.
"""

from typing import Dict, List, Any, Optional
from agents.tools.sql_generator import generate_sql_query
from agents.tools.database_tool import execute_query, validate_sql_query


def fuzzy_match_district(query: str, available_districts: List[str]) -> Optional[str]:
    """
    Fuzzy match district name from query using exact match first, then fuzzy matching.
    
    Args:
        query: Query string
        available_districts: List of available district names
        
    Returns:
        Matched district name or None
    """
    from difflib import get_close_matches
    query_lower = query.lower()
    
    # First try exact substring match
    for dist in available_districts:
        if dist.lower() in query_lower:
            return dist
    
    # Extract words from query (longer than 4 characters)
    query_words = [w for w in query_lower.split() if len(w) > 4]
    
    # Try fuzzy matching on each word
    for word in query_words:
        district_lower = [d.lower() for d in available_districts]
        matches = get_close_matches(word, district_lower, n=1, cutoff=0.75)
        if matches:
            # Find original district name (case-sensitive)
            for dist in available_districts:
                if dist.lower() == matches[0]:
                    return dist
    
    # Try fuzzy matching on entire query if it's a single word
    if len(query_lower.split()) == 1 and len(query_lower) > 4:
        district_lower = [d.lower() for d in available_districts]
        matches = get_close_matches(query_lower, district_lower, n=1, cutoff=0.7)
        if matches:
            for dist in available_districts:
                if dist.lower() == matches[0]:
                    return dist
    
    return None


class DataRetrievalAgent:
    """Agent responsible for all database queries."""
    
    def __init__(self):
        self.name = "DataRetrievalAgent"
        self.description = "Retrieves data from all database tables using SQL queries"
    
    def execute(self, query: str, table_hint: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute natural language query by converting to SQL and fetching results.
        
        Args:
            query: Natural language query
            table_hint: Optional hint about which table to focus on
        
        Returns:
            Dictionary with query results and metadata
        """
        try:
            # Extract district names from query for better context
            from agents.tools.database_tool import get_districts
            available_districts = get_districts()
            query_lower = query.lower()
            
            # Check if query mentions specific districts (exact match first)
            mentioned_districts = [d for d in available_districts if d.lower() in query_lower]
            
            # If no exact match, try fuzzy matching
            if not mentioned_districts:
                fuzzy_match = fuzzy_match_district(query, available_districts)
                if fuzzy_match:
                    mentioned_districts = [fuzzy_match]
            
            # Generate SQL from natural language
            sql_query = generate_sql_query(query, table_hint)
            
            # Validate SQL query
            if not validate_sql_query(sql_query):
                return {
                    "success": False,
                    "error": "Generated SQL query failed validation (unsafe operation detected)",
                    "sql_query": sql_query
                }
            
            # Execute query
            results = execute_query(sql_query)
            
            # If no results and query mentions districts, try to provide helpful info
            if not results and mentioned_districts:
                return {
                    "success": True,
                    "sql_query": sql_query,
                    "results": results,
                    "row_count": 0,
                    "agent": self.name,
                    "note": f"Query executed but returned no results for districts: {', '.join(mentioned_districts)}"
                }
            
            return {
                "success": True,
                "sql_query": sql_query,
                "results": results,
                "row_count": len(results),
                "agent": self.name,
                "mentioned_districts": mentioned_districts if mentioned_districts else None
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "agent": self.name
            }
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get schema information for a specific table."""
        from database.models import TABLE_SCHEMAS
        return TABLE_SCHEMAS.get(table_name, {})

