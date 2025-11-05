"""
Chatbot Testing Script
Tests the chatbot with various queries and scenarios to verify accuracy and capabilities.
"""

import sys
from services.chatbot_service import ChatbotService
from agents.tools.database_tool import get_districts

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """Print formatted header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(80)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}\n")

def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_info(text):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")

def print_warning(text):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def test_query(chatbot, query, district=None, expected_keywords=None):
    """
    Test a single query and display results.
    
    Args:
        chatbot: ChatbotService instance
        query: Query string to test
        district: Optional district name
        expected_keywords: List of keywords that should appear in response
    """
    print(f"\n{Colors.BOLD}Query:{Colors.RESET} {query}")
    if district:
        print(f"{Colors.BOLD}District:{Colors.RESET} {district}")
    print(f"{Colors.BOLD}{'-'*80}{Colors.RESET}")
    
    try:
        result = chatbot.process_query(query, district)
        
        if result.get("success"):
            response = result.get("response", "")
            xai_log = result.get("xai_log", [])
            
            print_success("Query processed successfully")
            print(f"\n{Colors.BOLD}Response:{Colors.RESET}")
            print(f"{response[:500]}{'...' if len(response) > 500 else ''}")
            
            # Check for expected keywords
            if expected_keywords:
                found_keywords = [kw for kw in expected_keywords if kw.lower() in response.lower()]
                if found_keywords:
                    print_success(f"Found expected keywords: {', '.join(found_keywords)}")
                else:
                    print_warning(f"Expected keywords not found: {', '.join(expected_keywords)}")
            
            # Show XAI log
            if xai_log:
                print(f"\n{Colors.BOLD}XAI Log ({len(xai_log)} entries):{Colors.RESET}")
                for i, log_entry in enumerate(xai_log[:3], 1):  # Show first 3
                    print(f"  {i}. {log_entry.get('step', 'N/A')}: {log_entry.get('decision', log_entry.get('action', 'N/A'))}")
            
            print_info(f"Response length: {len(response)} characters")
            return True
        else:
            error = result.get("error", "Unknown error")
            print_error(f"Query failed: {error}")
            return False
            
    except Exception as e:
        print_error(f"Exception occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def custom_query_mode(chatbot):
    """Interactive custom query mode."""
    print_header("Custom Query Mode")
    print_info("Enter your queries to test the chatbot interactively.")
    print_info("Type 'exit' to quit, 'clear' to clear history, 'help' for commands")
    print_info("Type 'district <name>' to set district context")
    
    current_district = None
    
    while True:
        try:
            print(f"\n{Colors.CYAN}{'='*80}{Colors.RESET}")
            user_input = input(f"{Colors.CYAN}You: {Colors.RESET}").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'exit':
                print_info("Exiting custom query mode...")
                break
            
            if user_input.lower() == 'clear':
                chatbot.clear_history()
                current_district = None
                print_success("Conversation history cleared")
                continue
            
            if user_input.lower() == 'help':
                print_info("Commands:")
                print("  exit - Exit custom query mode")
                print("  clear - Clear conversation history")
                print("  district <name> - Set district context")
                print("  Any other text - Ask a question to the chatbot")
                continue
            
            if user_input.lower().startswith('district '):
                from agents.tools.database_tool import get_districts
                districts = get_districts()
                district_name = user_input[9:].strip()
                if district_name in districts:
                    current_district = district_name
                    print_success(f"District context set to: {district_name}")
                else:
                    print_warning(f"District '{district_name}' not found. Available districts: {', '.join(districts[:5])}...")
                continue
            
            # Process query
            print(f"\n{Colors.BLUE}Processing query...{Colors.RESET}")
            print(f"{Colors.BLUE}{'-'*80}{Colors.RESET}")
            
            result = chatbot.process_query(user_input, current_district)
            
            # DEBUG: Show detailed information
            print(f"\n{Colors.YELLOW}{Colors.BOLD}=== DEBUG INFORMATION ==={Colors.RESET}")
            
            # Show routing information first
            xai_log = result.get("xai_log", [])
            routing_info = None
            for log_entry in xai_log:
                if log_entry.get('step') == 'route':
                    routing_info = log_entry
                    break
            
            if routing_info:
                print(f"\n{Colors.CYAN}{Colors.BOLD}Routing Decision:{Colors.RESET}")
                decision = routing_info.get('decision', [])
                if isinstance(decision, list):
                    print(f"  Agents to invoke: {', '.join(decision)}")
                else:
                    print(f"  Decision: {decision}")
                if routing_info.get('reasoning'):
                    print(f"  Reasoning: {routing_info.get('reasoning')}")
                if routing_info.get('query_type'):
                    print(f"  Query Type: {routing_info.get('query_type')}")
                if routing_info.get('error'):
                    print(f"  {Colors.RED}Routing Error: {routing_info.get('error')}{Colors.RESET}")
            
            # Show agent results
            agent_results = result.get("agent_results", [])
            if agent_results:
                print(f"\n{Colors.CYAN}{Colors.BOLD}Agent Results ({len(agent_results)} agents invoked):{Colors.RESET}")
                for i, agent_result in enumerate(agent_results, 1):
                    agent_name = agent_result.get("agent", "Unknown")
                    success = agent_result.get("success", False)
                    print(f"\n  {i}. {Colors.BOLD}{agent_name}{Colors.RESET}: {'✓ Success' if success else '✗ Failed'}")
                    
                    if success:
                        # Show SQL query if available (FULL QUERY for debugging)
                        sql_query = agent_result.get("sql_query")
                        if sql_query:
                            print(f"     {Colors.BLUE}SQL Query:{Colors.RESET}")
                            # Show full SQL query, formatted nicely
                            sql_lines = sql_query.split('\n')
                            for sql_line in sql_lines:
                                print(f"     {sql_line}")
                        
                        # Show data fetched
                        row_count = agent_result.get("row_count", 0)
                        results = agent_result.get("results", [])
                        print(f"     {Colors.GREEN}Rows fetched: {row_count}{Colors.RESET}")
                        
                        # Show sample data (first 3 rows) - FULL DATA for debugging
                        if results and len(results) > 0:
                            print(f"     {Colors.CYAN}Sample data (first {min(3, len(results))} rows):{Colors.RESET}")
                            for j, row in enumerate(results[:3], 1):
                                # Show full row data
                                import json
                                row_str = json.dumps(row, indent=6, default=str)
                                print(f"       Row {j}:")
                                for line in row_str.split('\n'):
                                    print(f"         {line}")
                            if len(results) > 3:
                                print(f"       ... and {len(results) - 3} more rows")
                        
                        # Show other metadata
                        if agent_result.get("mentioned_districts"):
                            print(f"     {Colors.CYAN}Mentioned districts: {agent_result.get('mentioned_districts')}{Colors.RESET}")
                        if agent_result.get("note"):
                            print(f"     {Colors.YELLOW}Note: {agent_result.get('note')}{Colors.RESET}")
                    else:
                        error = agent_result.get("error", "Unknown error")
                        print(f"     {Colors.RED}Error: {error}{Colors.RESET}")
                        if agent_result.get("sql_query"):
                            print(f"     {Colors.RED}SQL Query (that failed):{Colors.RESET}")
                            sql_query = agent_result.get("sql_query")
                            sql_lines = sql_query.split('\n')
                            for sql_line in sql_lines:
                                print(f"     {Colors.RED}{sql_line}{Colors.RESET}")
            else:
                print_warning("No agent results found")
            
            # Show XAI log with more details (skip route as we already showed it)
            if xai_log:
                print(f"\n{Colors.CYAN}{Colors.BOLD}XAI Log ({len(xai_log)} entries):{Colors.RESET}")
                for i, log_entry in enumerate(xai_log, 1):
                    step = log_entry.get('step', 'N/A')
                    decision = log_entry.get('decision', log_entry.get('action', 'N/A'))
                    reasoning = log_entry.get('reasoning', '')
                    query_type = log_entry.get('query_type', '')
                    result_summary = log_entry.get('result_summary', '')
                    
                    print(f"  {i}. {Colors.BOLD}{step}{Colors.RESET}:")
                    if isinstance(decision, list):
                        print(f"       Agents: {', '.join(decision)}")
                    else:
                        print(f"       Decision: {decision}")
                    if reasoning:
                        print(f"       Reasoning: {reasoning}")
                    if query_type:
                        print(f"       Query Type: {query_type}")
                    if result_summary:
                        print(f"       Result: {result_summary}")
                    
                    # Show SQL query if available in log (FULL QUERY)
                    if log_entry.get('sql_query'):
                        sql_query = log_entry.get('sql_query')
                        print(f"       {Colors.BLUE}SQL Query:{Colors.RESET}")
                        # Show full SQL query
                        sql_lines = sql_query.split('\n')
                        for sql_line in sql_lines:
                            print(f"       {sql_line}")
                    
                    # Show other metrics
                    if log_entry.get('hvi_scores_count'):
                        print(f"       HVI scores calculated: {log_entry.get('hvi_scores_count')}")
                    if log_entry.get('iss_scores_count'):
                        print(f"       ISS scores calculated: {log_entry.get('iss_scores_count')}")
                    if log_entry.get('rcs_scores_count'):
                        print(f"       RCS scores calculated: {log_entry.get('rcs_scores_count')}")
                    if log_entry.get('mentioned_districts'):
                        print(f"       Districts mentioned: {log_entry.get('mentioned_districts')}")
                    
                    if log_entry.get('error'):
                        print(f"       {Colors.RED}Error: {log_entry.get('error')}{Colors.RESET}")
                    if log_entry.get('success') is False:
                        print(f"       {Colors.RED}Status: Failed{Colors.RESET}")
                    elif log_entry.get('success') is True:
                        print(f"       {Colors.GREEN}Status: Success{Colors.RESET}")
            
            print(f"\n{Colors.YELLOW}{'='*80}{Colors.RESET}\n")
            
            if result.get("success"):
                response = result.get("response", "")
                
                # Display full response
                print(f"\n{Colors.GREEN}{Colors.BOLD}Chatbot Response:{Colors.RESET}")
                print(f"{Colors.GREEN}{'='*80}{Colors.RESET}")
                print(f"{response}")
                print(f"{Colors.GREEN}{'='*80}{Colors.RESET}")
                
                print_info(f"Response length: {len(response)} characters")
            else:
                error = result.get("error", "Unknown error")
                print_error(f"Error: {error}")
                
        except KeyboardInterrupt:
            print("\n\n" + Colors.YELLOW + "Interrupted by user" + Colors.RESET)
            break
        except Exception as e:
            print_error(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()

def main():
    """Main testing function."""
    print_header("Chatbot Testing Suite")
    
    # Initialize chatbot
    print_info("Initializing ChatbotService...")
    try:
        chatbot = ChatbotService()
        print_success("ChatbotService initialized successfully")
    except Exception as e:
        print_error(f"Failed to initialize chatbot: {e}")
        sys.exit(1)
    
    # Get available districts
    try:
        districts = get_districts()
        print_success(f"Retrieved {len(districts)} districts from database")
        sample_district = districts[0] if districts else None
    except Exception as e:
        print_warning(f"Could not retrieve districts: {e}")
        districts = []
        sample_district = None
    
    # Ask user to choose mode
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}Choose Testing Mode:{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.BLUE}1.{Colors.RESET} Run built-in test queries (31 predefined tests)")
    print(f"{Colors.BLUE}2.{Colors.RESET} Custom query mode (enter your own queries)")
    print(f"{Colors.BLUE}3.{Colors.RESET} Both (run tests first, then custom mode)")
    
    while True:
        choice = input(f"\n{Colors.CYAN}Enter your choice (1/2/3): {Colors.RESET}").strip()
        
        if choice == '1':
            run_builtin_tests = True
            run_custom_mode = False
            break
        elif choice == '2':
            run_builtin_tests = False
            run_custom_mode = True
            break
        elif choice == '3':
            run_builtin_tests = True
            run_custom_mode = True
            break
        else:
            print_error("Invalid choice. Please enter 1, 2, or 3.")
    
    # Run built-in tests if selected
    if run_builtin_tests:
        # Test Categories
        test_categories = {
            "Health Queries": [
                {
                    "query": "What is the health vulnerability in Ahmednagar?",
                    "district": "Ahmednagar",
                    "keywords": ["health", "vulnerability", "HVI", "Ahmednagar"]
                },
                {
                    "query": "Which district has the highest health vulnerability?",
                    "keywords": ["health", "vulnerability", "district"]
                },
                {
                    "query": "How many ICU beds are available in Amravati?",
                    "district": "Amravati",
                    "keywords": ["ICU", "bed", "Amravati"]
                },
                {
                    "query": "Show me the emergency cases per month for all districts",
                    "keywords": ["emergency", "cases", "district"]
                },
                {
                    "query": "What is the bed occupancy rate in Aurangabad?",
                    "district": "Aurangabad",
                    "keywords": ["bed", "occupancy", "Aurangabad"]
                }
            ],
            
            "Infrastructure Queries": [
                {
                    "query": "What is the infrastructure strain in Ahmednagar?",
                    "district": "Ahmednagar",
                    "keywords": ["infrastructure", "strain", "ISS"]
                },
                {
                    "query": "Which district has the most infrastructure service requests?",
                    "keywords": ["infrastructure", "service", "request", "district"]
                },
                {
                    "query": "How many kilometers of roads are there in Amravati?",
                    "district": "Amravati",
                    "keywords": ["road", "kilometer", "Amravati"]
                },
                {
                    "query": "What is the water treatment plant capacity across districts?",
                    "keywords": ["water", "treatment", "plant"]
                },
                {
                    "query": "Show me districts with high infrastructure demand",
                    "keywords": ["infrastructure", "demand", "district"]
                }
            ],
            
            "Resource & Worker Queries": [
                {
                    "query": "What is the resource contention score in Ahmednagar?",
                    "district": "Ahmednagar",
                    "keywords": ["resource", "contention", "RCS"]
                },
                {
                    "query": "How many workers are available in Amravati?",
                    "district": "Amravati",
                    "keywords": ["worker", "available", "Amravati"]
                },
                {
                    "query": "Which district has the highest worker utilization rate?",
                    "keywords": ["worker", "utilization", "district"]
                },
                {
                    "query": "Show me the escalation rate for service requests",
                    "keywords": ["escalation", "service", "request"]
                },
                {
                    "query": "What is the average response time for workers in different districts?",
                    "keywords": ["response", "time", "worker", "district"]
                }
            ],
            
            "P-Score & Priority Queries": [
                {
                    "query": "Which district has the highest P-Score?",
                    "keywords": ["P-Score", "district", "highest"]
                },
                {
                    "query": "What is the P-Score for Ahmednagar?",
                    "district": "Ahmednagar",
                    "keywords": ["P-Score", "Ahmednagar"]
                },
                {
                    "query": "Show me districts ranked by priority level",
                    "keywords": ["priority", "district", "rank"]
                },
                {
                    "query": "Which districts need immediate attention?",
                    "keywords": ["attention", "district", "priority"]
                },
                {
                    "query": "What are the top 5 districts by P-Score?",
                    "keywords": ["P-Score", "top", "district"]
                }
            ],
            
            "Comparative & Analysis Queries": [
                {
                    "query": "Compare health infrastructure between Ahmednagar and Amravati",
                    "keywords": ["compare", "health", "infrastructure"]
                },
                {
                    "query": "Show me a comprehensive analysis of Aurangabad district",
                    "district": "Aurangabad",
                    "keywords": ["analysis", "Aurangabad", "comprehensive"]
                },
                {
                    "query": "What are the key challenges in districts with high P-Scores?",
                    "keywords": ["challenge", "P-Score", "district"]
                },
                {
                    "query": "Which district has the best overall infrastructure?",
                    "keywords": ["district", "infrastructure", "best"]
                }
            ],
            
            "Data Retrieval Queries": [
                {
                    "query": "How many service requests are there in Ahmednagar?",
                    "district": "Ahmednagar",
                    "keywords": ["service", "request", "Ahmednagar"]
                },
                {
                    "query": "Show me all districts in the database",
                    "keywords": ["district", "database"]
                },
                {
                    "query": "What is the population of Amravati?",
                    "district": "Amravati",
                    "keywords": ["population", "Amravati"]
                },
                {
                    "query": "List all hospitals in Aurangabad",
                    "district": "Aurangabad",
                    "keywords": ["hospital", "Aurangabad"]
                }
            ],
            
            "General & Exploratory Queries": [
                {
                    "query": "Give me an overview of the system",
                    "keywords": ["overview", "system"]
                },
                {
                    "query": "What can you help me with?",
                    "keywords": ["help"]
                },
                {
                    "query": "What insights can you provide about district management?",
                    "keywords": ["insight", "district", "management"]
                }
            ]
        }
        
        # Run tests
        total_tests = 0
        passed_tests = 0
        
        for category, queries in test_categories.items():
            print_header(f"Testing: {category}")
            
            for i, test_case in enumerate(queries, 1):
                total_tests += 1
                print(f"\n{Colors.BOLD}[{category} - Test {i}/{len(queries)}]{Colors.RESET}")
                
                result = test_query(
                    chatbot,
                    test_case["query"],
                    test_case.get("district", sample_district),
                    test_case.get("keywords")
                )
                
                if result:
                    passed_tests += 1
                
                # Small delay to avoid rate limiting
                import time
                time.sleep(0.5)
        
        # Summary
        print_header("Test Summary")
        print(f"Total Tests: {total_tests}")
        print_success(f"Passed: {passed_tests}")
        if total_tests - passed_tests > 0:
            print_error(f"Failed: {total_tests - passed_tests}")
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"\n{Colors.BOLD}Success Rate: {success_rate:.1f}%{Colors.RESET}")
    
    # Run custom query mode if selected
    if run_custom_mode:
        custom_query_mode(chatbot)

if __name__ == "__main__":
    main()

