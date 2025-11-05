"""
Database query executor tool.
Executes SQL queries using SQLAlchemy and returns structured results.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.engine import Result
import pandas as pd
from database.connection import get_db_session


def execute_query(sql_query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Execute SQL query and return results as list of dictionaries.
    
    Args:
        sql_query: SQL query string
        params: Optional query parameters for parameterized queries
    
    Returns:
        List of dictionaries, each representing a row
    """
    try:
        with get_db_session() as db:
            # Execute query
            if params:
                result: Result = db.execute(text(sql_query), params)
            else:
                result: Result = db.execute(text(sql_query))
            
            # Get column names
            columns = list(result.keys())
            
            # Fetch all rows
            rows = result.fetchall()
            
            # Convert to list of dictionaries
            results = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    # Convert datetime objects to strings if needed
                    if hasattr(value, 'isoformat'):
                        value = value.isoformat()
                    row_dict[col] = value
                results.append(row_dict)
            
            return results
    
    except Exception as e:
        raise Exception(f"Database query execution failed: {str(e)}")


def execute_query_dataframe(sql_query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """
    Execute SQL query and return results as pandas DataFrame.
    
    Args:
        sql_query: SQL query string
        params: Optional query parameters
    
    Returns:
        pandas DataFrame with query results
    """
    results = execute_query(sql_query, params)
    return pd.DataFrame(results)


def get_districts() -> List[str]:
    """Get list of all unique districts from database."""
    query = """
    SELECT DISTINCT "District" 
    FROM (
        SELECT "District" FROM health_infrastructure_data WHERE "District" IS NOT NULL
        UNION
        SELECT "District" FROM area_wise_demographics_infrastructure WHERE "District" IS NOT NULL
        UNION
        SELECT "District" FROM public_workers_data WHERE "District" IS NOT NULL
        UNION
        SELECT "District" FROM service_request_details WHERE "District" IS NOT NULL
    ) AS all_districts
    ORDER BY "District"
    """
    
    results = execute_query(query)
    return [row["District"] for row in results if row["District"]]


def validate_sql_query(sql_query: str) -> bool:
    """
    Basic validation of SQL query.
    Prevents dangerous operations.
    
    Args:
        sql_query: SQL query to validate
    
    Returns:
        True if query appears safe, False otherwise
    """
    sql_lower = sql_query.lower().strip()
    
    # Block dangerous operations
    dangerous_keywords = [
        'drop', 'delete', 'truncate', 'alter', 'create', 
        'insert', 'update', 'grant', 'revoke', 'exec', 'execute'
    ]
    
    # Allow SELECT queries
    if not sql_lower.startswith('select'):
        return False
    
    # Check for dangerous keywords
    for keyword in dangerous_keywords:
        if f' {keyword} ' in sql_lower or sql_lower.startswith(keyword):
            return False
    
    return True

