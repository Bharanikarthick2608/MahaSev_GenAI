"""
Test script to verify the multi-agent system works in console.
Run this before integrating with FastAPI.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test imports
print("=" * 60)
print("Testing Multi-Agent Cross-Sectoral Intelligence Platform")
print("=" * 60)

print("\n1. Testing database connection...")
try:
    from database.connection import test_connection, get_db_session
    
    if test_connection():
        print("✓ Database connection successful")
    else:
        print("✗ Database connection failed")
        print("  Make sure DATABASE_URL and DATABASE_PASSWORD are set in .env")
        sys.exit(1)
except Exception as e:
    print(f"✗ Database connection error: {e}")
    sys.exit(1)

print("\n2. Testing data retrieval...")
try:
    from agents.tools.database_tool import get_districts
    
    districts = get_districts()
    print(f"✓ Retrieved {len(districts)} districts from database")
    if districts:
        print(f"  Sample districts: {districts[:3]}")
except Exception as e:
    print(f"✗ Data retrieval error: {e}")

print("\n3. Testing metric calculations...")
try:
    from metrics.hvi import calculate_hvi
    from metrics.iss import calculate_iss
    from metrics.rcs import calculate_rcs
    
    # Test with first district if available
    if districts:
        test_district = districts[0]
        print(f"  Testing with district: {test_district}")
        
        hvi_scores = calculate_hvi(test_district)
        print(f"✓ HVI calculation successful: {hvi_scores.get(test_district, 'N/A')}")
        
        iss_scores = calculate_iss(test_district)
        print(f"✓ ISS calculation successful: {iss_scores.get(test_district, 'N/A')}")
        
        rcs_scores = calculate_rcs(test_district)
        print(f"✓ RCS calculation successful: {rcs_scores.get(test_district, 'N/A')}")
    else:
        print("  Skipping - no districts found")
except Exception as e:
    print(f"✗ Metric calculation error: {e}")

print("\n4. Testing P-Score calculation...")
try:
    from metrics.p_score import calculate_p_score, get_comprehensive_p_score
    
    if districts:
        p_scores = calculate_p_score(test_district)
        print(f"✓ P-Score calculation successful: {p_scores.get(test_district, 'N/A')}")
        
        comprehensive = get_comprehensive_p_score(test_district)
        if comprehensive:
            dist_data = comprehensive.get(test_district, {})
            print(f"  P-Score: {dist_data.get('p_score', 'N/A')}")
            print(f"  Priority: {dist_data.get('priority_level', 'N/A')}")
except Exception as e:
    print(f"✗ P-Score calculation error: {e}")

print("\n5. Testing specialist agents...")
try:
    from agents.health_agent import HealthAgent
    from agents.infrastructure_agent import InfrastructureAgent
    from agents.resource_agent import ResourceAgent
    
    health_agent = HealthAgent()
    print(f"✓ HealthAgent initialized: {health_agent.name}")
    
    infra_agent = InfrastructureAgent()
    print(f"✓ InfrastructureAgent initialized: {infra_agent.name}")
    
    resource_agent = ResourceAgent()
    print(f"✓ ResourceAgent initialized: {resource_agent.name}")
    
    # Test agent execution if district available
    if districts:
        health_result = health_agent.execute(test_district)
        if health_result.get("success"):
            print(f"✓ HealthAgent execution successful")
        else:
            print(f"  HealthAgent warning: {health_result.get('error', 'Unknown error')}")
except Exception as e:
    print(f"✗ Agent initialization error: {e}")

print("\n6. Testing Supervisor Agent...")
try:
    # Check for Gemini API key
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("  ⚠ GEMINI_API_KEY not set - Supervisor will use fallback routing")
    else:
        print("  ✓ GEMINI_API_KEY found")
    
    from agents.supervisor import SupervisorAgent
    
    supervisor = SupervisorAgent()
    print(f"✓ SupervisorAgent initialized: {supervisor.name}")
    
    # Test with a simple query
    if districts:
        test_query = f"What is the health vulnerability in {test_district}?"
        print(f"\n  Testing query: '{test_query}'")
        
        result = supervisor.execute(test_query, test_district)
        if result.get("success"):
            print(f"✓ Supervisor execution successful")
            print(f"  Response length: {len(result.get('response', ''))} characters")
            print(f"  XAI log entries: {len(result.get('xai_log', []))}")
        else:
            print(f"  Supervisor warning: {result.get('error', 'Unknown error')}")
except Exception as e:
    print(f"✗ Supervisor Agent error: {e}")
    import traceback
    traceback.print_exc()

print("\n7. Testing Chatbot Service...")
try:
    from services.chatbot_service import ChatbotService
    
    chatbot = ChatbotService()
    print("✓ ChatbotService initialized")
    
    if districts:
        test_query = f"Which district has the highest P-Score?"
        print(f"\n  Testing chatbot query: '{test_query}'")
        
        response = chatbot.process_query(test_query)
        if response.get("success"):
            print(f"✓ Chatbot query successful")
            print(f"  Response preview: {response.get('response', '')[:100]}...")
        else:
            print(f"  Chatbot warning: {response.get('error', 'Unknown error')}")
except Exception as e:
    print(f"✗ Chatbot Service error: {e}")

print("\n" + "=" * 60)
print("Test Summary")
print("=" * 60)
print("\nIf all tests passed (✓), the system is ready for FastAPI integration.")
print("If any tests failed (✗), check:")
print("  1. Database connection settings in .env")
print("  2. GEMINI_API_KEY in .env (optional but recommended)")
print("  3. All dependencies installed: pip install -r requirements.txt")
print("\n" + "=" * 60)

