"""
CareMate Backend - Test Suite
Test all components of the two-agent system
"""

import os
import json
import sys
from datetime import datetime

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test(name):
    print(f"\n{Colors.BLUE}[TEST]{Colors.END} {name}")

def print_success(message):
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_error(message):
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")

# ============================================================================
# TEST 1: Environment Configuration
# ============================================================================

def test_environment():
    print_test("Environment Configuration")
    
    required_vars = ["GEMINI_API_KEY", "SARVAM_API_KEY"]
    optional_vars = ["MONGODB_URI", "OTEL_SDK_DISABLED"]
    
    all_ok = True
    
    for var in required_vars:
        if os.getenv(var):
            print_success(f"{var} is set")
        else:
            print_error(f"{var} is NOT set")
            all_ok = False
    
    for var in optional_vars:
        if os.getenv(var):
            print_success(f"{var} is set (optional)")
        else:
            print_warning(f"{var} is not set (optional)")
    
    return all_ok

# ============================================================================
# TEST 2: Dependencies
# ============================================================================

def test_dependencies():
    print_test("Package Dependencies")
    
    dependencies = [
        ("crewai", "CrewAI Framework"),
        ("langchain", "LangChain"),
        ("langchain_google_genai", "Gemini Integration"),
        ("pymongo", "MongoDB Driver"),
        ("fastapi", "FastAPI Framework"),
        ("requests", "HTTP Requests"),
        ("pydantic", "Data Validation")
    ]
    
    all_ok = True
    
    for package, name in dependencies:
        try:
            __import__(package)
            print_success(f"{name} installed")
        except ImportError:
            print_error(f"{name} NOT installed")
            all_ok = False
    
    return all_ok

# ============================================================================
# TEST 3: MongoDB Connection
# ============================================================================

def test_mongodb():
    print_test("MongoDB Connection")
    
    try:
        from pymongo import MongoClient
        
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        
        # Test connection
        client.server_info()
        print_success("MongoDB connection successful")
        
        # Check database
        db = client["caremate_db"]
        collections = db.list_collection_names()
        print_success(f"Database accessible ({len(collections)} collections)")
        
        # Check patient data
        patient_count = db.patients.count_documents({})
        print_success(f"Patient records: {patient_count}")
        
        return True
        
    except Exception as e:
        print_error(f"MongoDB connection failed: {str(e)}")
        return False

# ============================================================================
# TEST 4: Gemini LLM Connection
# ============================================================================

def test_gemini():
    print_test("Google Gemini LLM")
    
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0.3
        )
        
        response = llm.invoke("Say 'test successful' in 2 words")
        print_success("Gemini LLM connection successful")
        print(f"   Response: {response.content}")
        
        return True
        
    except Exception as e:
        print_error(f"Gemini connection failed: {str(e)}")
        return False

# ============================================================================
# TEST 5: Sarvam AI Connection
# ============================================================================

def test_sarvam():
    print_test("Sarvam AI APIs")
    
    try:
        import requests
        
        api_key = os.getenv("SARVAM_API_KEY")
        
        # Test TTS endpoint
        url = "https://api.sarvam.ai/text-to-speech"
        headers = {
            "api-subscription-key": api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "inputs": ["Test"],
            "target_language_code": "hi-IN",
            "speaker": "meera",
            "model": "bulbul:v2"
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        
        print_success("Sarvam AI TTS connection successful")
        
        result = response.json()
        audio_length = len(result.get("audios", [""])[0])
        print_success(f"Audio generated: {audio_length} characters")
        
        return True
        
    except Exception as e:
        print_error(f"Sarvam AI connection failed: {str(e)}")
        return False

# ============================================================================
# TEST 6: CrewAI Agent Creation
# ============================================================================

def test_agent_creation():
    print_test("CrewAI Agent Creation")
    
    try:
        from crewai import Agent
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0.3
        )
        
        agent = Agent(
            role="Test Agent",
            goal="Test agent creation",
            backstory="I am a test agent.",
            llm=llm,
            verbose=False
        )
        
        print_success("Patient Intelligence Agent can be created")
        
        orchestrator = Agent(
            role="Test Orchestrator",
            goal="Test orchestration",
            backstory="I orchestrate tests.",
            llm=llm,
            verbose=False
        )
        
        print_success("Orchestrator Agent can be created")
        
        return True
        
    except Exception as e:
        print_error(f"Agent creation failed: {str(e)}")
        return False

# ============================================================================
# TEST 7: Custom Tools
# ============================================================================

def test_custom_tools():
    print_test("Custom CrewAI Tools")
    
    try:
        from crewai.tools import BaseTool
        from pydantic import Field
        
        class TestTool(BaseTool):
            name: str = "Test Tool"
            description: str = "A test tool"
            
            def _run(self, input_data: str) -> str:
                return json.dumps({"status": "success", "input": input_data})
        
        tool = TestTool()
        result = tool._run("test input")
        
        print_success("Custom tool creation works")
        print(f"   Tool output: {result}")
        
        return True
        
    except Exception as e:
        print_error(f"Tool creation failed: {str(e)}")
        return False

# ============================================================================
# TEST 8: Complete Crew Workflow
# ============================================================================

def test_crew_workflow():
    print_test("Complete Crew Workflow")
    
    try:
        from crewai import Agent, Task, Crew, Process
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0.3,
            max_tokens=500
        )
        
        # Create agent
        agent = Agent(
            role="Medical Assistant",
            goal="Answer patient questions",
            backstory="I help patients with basic information.",
            llm=llm,
            verbose=False
        )
        
        # Create task
        task = Task(
            description="What are the visiting hours?",
            agent=agent,
            expected_output="Brief response about visiting hours"
        )
        
        # Create crew
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False
        )
        
        # Run crew
        print("   Running crew (this may take 10-15 seconds)...")
        result = crew.kickoff()
        
        print_success("Crew workflow executed successfully")
        print(f"   Result: {str(result)[:100]}...")
        
        return True
        
    except Exception as e:
        print_error(f"Crew workflow failed: {str(e)}")
        return False

# ============================================================================
# TEST 9: Database Operations
# ============================================================================

def test_database_operations():
    print_test("Database Operations")
    
    try:
        from pymongo import MongoClient
        
        client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017/"))
        db = client["caremate_db"]
        
        # Test patient retrieval
        patient = db.patients.find_one({"hospital_id": "PT001"})
        if patient:
            print_success("Patient record retrieval works")
        else:
            print_warning("No sample patient data found")
        
        # Test interaction logging
        test_interaction = {
            "interaction_id": f"TEST_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "patient_id": "PT001",
            "timestamp": datetime.now().isoformat(),
            "query_text": "Test query",
            "is_test": True
        }
        
        db.interactions.insert_one(test_interaction)
        print_success("Interaction logging works")
        
        # Clean up test data
        db.interactions.delete_one({"interaction_id": test_interaction["interaction_id"]})
        print_success("Database cleanup works")
        
        return True
        
    except Exception as e:
        print_error(f"Database operations failed: {str(e)}")
        return False

# ============================================================================
# TEST 10: API Server (if running)
# ============================================================================

def test_api_server():
    print_test("API Server (if running)")
    
    try:
        import requests
        
        # Test health endpoint
        response = requests.get("http://localhost:8000/api/v1/health", timeout=5)
        
        if response.status_code == 200:
            print_success("API server is running")
            print_success("Health check endpoint works")
            
            # Test patient endpoint
            response = requests.get("http://localhost:8000/api/v1/patient/PT001", timeout=5)
            if response.status_code == 200:
                print_success("Patient endpoint works")
            else:
                print_warning(f"Patient endpoint returned {response.status_code}")
            
            return True
        else:
            print_warning("API server returned unexpected status")
            return False
            
    except requests.exceptions.ConnectionError:
        print_warning("API server is not running (this is OK if not started yet)")
        return None
    except Exception as e:
        print_error(f"API test failed: {str(e)}")
        return False

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def run_all_tests():
    print("\n" + "="*70)
    print("  CareMate Backend - Comprehensive Test Suite")
    print("="*70)
    
    tests = [
        ("Environment Configuration", test_environment),
        ("Package Dependencies", test_dependencies),
        ("MongoDB Connection", test_mongodb),
        ("Google Gemini LLM", test_gemini),
        ("Sarvam AI APIs", test_sarvam),
        ("CrewAI Agent Creation", test_agent_creation),
        ("Custom Tools", test_custom_tools),
        ("Complete Crew Workflow", test_crew_workflow),
        ("Database Operations", test_database_operations),
        ("API Server", test_api_server)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print_error(f"Test crashed: {str(e)}")
            results[test_name] = False
    
    # Print summary
    print("\n" + "="*70)
    print("  TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for r in results.values() if r is True)
    failed = sum(1 for r in results.values() if r is False)
    skipped = sum(1 for r in results.values() if r is None)
    
    for test_name, result in results.items():
        if result is True:
            print(f"{Colors.GREEN}✅ PASS{Colors.END} - {test_name}")
        elif result is False:
            print(f"{Colors.RED}❌ FAIL{Colors.END} - {test_name}")
        else:
            print(f"{Colors.YELLOW}⊘  SKIP{Colors.END} - {test_name}")
    
    print("\n" + "-"*70)
    print(f"Total: {len(tests)} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
    print("-"*70)
    
    if failed == 0:
        print(f"\n{Colors.GREEN}🎉 All critical tests passed! System is ready.{Colors.END}")
        return 0
    else:
        print(f"\n{Colors.RED}⚠️  {failed} test(s) failed. Please fix issues before proceeding.{Colors.END}")
        return 1

if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
