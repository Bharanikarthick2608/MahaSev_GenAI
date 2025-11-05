"""
Natural Language to SQL query generator using Groq.
Converts admin queries into optimized PostgreSQL queries.
"""

import os
from typing import Dict, Optional
# Commented out Gemini - using Groq instead
# from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from database.models import TABLE_SCHEMAS

# Commented out Gemini model for SQL generation
# gemini_model = None
# 
# 
# def get_gemini_model():
#     """Get or create Gemini model instance."""
#     global gemini_model
#     if gemini_model is None:
#         api_key = os.getenv("GEMINI_API_KEY")
#         if not api_key:
#             raise ValueError("GEMINI_API_KEY environment variable is required")
#         gemini_model = ChatGoogleGenerativeAI(
#             model="gemini-pro",
#             google_api_key=api_key,
#             temperature=0.1  # Low temperature for consistent SQL generation
#         )
#     return gemini_model

# Initialize Groq model for SQL generation
groq_model = None


def get_groq_model():
    """Get or create Groq model instance."""
    global groq_model
    if groq_model is None:
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")
        groq_model = ChatGroq(
            model="llama-3.1-8b-instant",
            groq_api_key=groq_api_key,
            temperature=0.1  # Low temperature for consistent SQL generation
        )
    return groq_model

# Keep backward compatibility alias
def get_gemini_model():
    """Backward compatibility alias - returns Groq model."""
    return get_groq_model()


def generate_sql_query(natural_language_query: str, table_context: Optional[str] = None) -> str:
    """
    Generate SQL query from natural language.
    
    Args:
        natural_language_query: User's question in natural language
        table_context: Optional hint about which table to focus on
    
    Returns:
        SQL query string
    """
    model = get_groq_model()
    
    # Build schema context with detailed column-to-table mapping
    schema_context = "Available tables and columns:\n\n"
    column_to_table = {}  # Map columns to their tables
    
    for table_name, schema_info in TABLE_SCHEMAS.items():
        schema_context += f"Table: {schema_info['table_name']}\n"
        schema_context += f"Description: {schema_info['description']}\n"
        schema_context += f"Columns: {', '.join(schema_info['columns'])}\n\n"
        
        # Build column-to-table mapping
        for col in schema_info['columns']:
            if col not in column_to_table:
                column_to_table[col] = []
            column_to_table[col].append(schema_info['table_name'])
    
    # Add column-to-table mapping for reference
    schema_context += "\nIMPORTANT COLUMN LOCATIONS:\n"
    schema_context += "- 'Population' is ONLY in 'area_wise_demographics_infrastructure' (NOT in health_infrastructure_data)\n"
    schema_context += "- Health infrastructure columns (Total_Beds, ICU_Beds, Doctors, Nurses, etc.) are in 'health_infrastructure_data'\n"
    schema_context += "- Worker columns (Total_Workers, Available_Workers, Utilization_Rate_Percentage) are in 'public_workers_data'\n"
    schema_context += "- Service request columns (Request_ID, Escalated, Resolution_Time_Hours) are in 'service_request_details'\n"
    schema_context += "- Demographic columns (Population, Literacy_Rate, Avg_Income_INR) are in 'area_wise_demographics_infrastructure'\n"
    schema_context += "- All tables have 'District' column for joining\n\n"
    
    prompt = f"""You are a SQL expert. Convert the following natural language query into a PostgreSQL query.

{schema_context}

Natural Language Query: {natural_language_query}
{f'Focus on table: {table_context}' if table_context else ''}

CRITICAL DATABASE RULES:
1. All column names are case-sensitive and MUST be quoted with double quotes (e.g., "District", "Escalated")

2. COLUMN LOCATION - JOIN REQUIRED when columns are in different tables:
   - "Population" is ONLY in area_wise_demographics_infrastructure (NOT in health_infrastructure_data)
   - If you need "Population" with health_infrastructure_data, you MUST JOIN:
     FROM health_infrastructure_data h
     JOIN area_wise_demographics_infrastructure a ON h."District" = a."District"
   - If you need columns from multiple tables, JOIN them on "District"
   - Always use table aliases (h, a, w, s) when joining multiple tables

3. The "Escalated" column in service_request_details is stored as TEXT, not boolean. When comparing:
   - Use: CASE WHEN LOWER(TRIM("Escalated"::text)) IN ('true', 't', '1', 'yes') THEN 1 ELSE 0 END
   - Do NOT use: "Escalated" = true (this will cause an error: operator does not exist: text = boolean)

4. CRITICAL: For public_workers_data table, "District" is NOT unique. The primary key is "Worker_Type_District".
   - ALWAYS use aggregation when querying by district: GROUP BY "District"
   - Use aggregate functions: SUM("Total_Workers"), SUM("Available_Workers"), AVG("Utilization_Rate_Percentage"), etc.
   - When JOINING public_workers_data with other tables:
     * First aggregate public_workers_data by District: 
       SELECT "District", SUM("Total_Workers") as total_workers, AVG("Utilization_Rate_Percentage") as avg_utilization
       FROM public_workers_data GROUP BY "District"
     * Then JOIN this aggregated result with other tables
   - Example with JOIN:
     SELECT h."District", a."Population", w.total_workers
     FROM health_infrastructure_data h
     JOIN area_wise_demographics_infrastructure a ON h."District" = a."District"
     JOIN (
       SELECT "District", SUM("Total_Workers") as total_workers 
       FROM public_workers_data 
       GROUP BY "District"
     ) w ON h."District" = w."District"

5. For queries asking "all districts", "across districts", "which district", "compare districts":
   - DO NOT filter by single district
   - Use GROUP BY "District" to aggregate data per district
   - Return all districts or use ORDER BY to rank/compare

6. For comparative queries ("compare X and Y"):
   - Use WHERE "District" IN ('District1', 'District2')
   - Group by district to show comparison
   - Use ORDER BY to rank districts

Requirements:
1. Generate valid PostgreSQL syntax
2. Use appropriate WHERE clauses for filtering (but don't filter districts unless query specifies)
3. Include only necessary columns
4. Use aggregate functions (COUNT, SUM, AVG, MAX, MIN) when appropriate
5. For public_workers_data, ALWAYS aggregate by "District" using GROUP BY before joining with other tables
6. JOIN tables when columns are needed from different tables:
   - Use JOIN on "District" column (always quoted: "District")
   - Use table aliases (h=health_infrastructure_data, a=area_wise_demographics_infrastructure, w=public_workers_data, s=service_request_details)
   - When joining with public_workers_data, use subquery with GROUP BY first
7. All column names must be quoted with double quotes
8. All table names must be quoted if they contain special characters
9. For multi-district queries, ensure results show data for all relevant districts
10. Before writing SQL, identify which tables contain the columns you need:
    - If columns are in different tables, you MUST use JOIN
    - If "Population" is needed, it MUST come from area_wise_demographics_infrastructure
11. Return only the SQL query, no explanations

SQL Query:"""

    try:
        response = model.invoke(prompt)
        sql_query = response.content.strip()
        
        # Clean up the response (remove markdown code blocks if present)
        if sql_query.startswith("```"):
            lines = sql_query.split("\n")
            sql_query = "\n".join(lines[1:-1]) if len(lines) > 2 else sql_query
            sql_query = sql_query.strip().strip("`").strip()
        
        return sql_query
    except Exception as e:
        raise Exception(f"Failed to generate SQL query: {str(e)}")


def get_table_schema_string() -> str:
    """Get formatted schema information for prompts."""
    schema_str = ""
    for table_name, schema_info in TABLE_SCHEMAS.items():
        schema_str += f"\n{table_name.upper()}:\n"
        schema_str += f"  Description: {schema_info['description']}\n"
        schema_str += f"  Columns: {', '.join(schema_info['columns'])}\n"
    return schema_str

