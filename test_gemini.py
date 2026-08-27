import sys
from dotenv import load_dotenv
from services import parse_complaint

def run_tests():
    load_dotenv()
    
    test_cases = [
        "fan not working in B block room 204 since morning",
        "wifi not working in room 210 block B",
        "water pipe burst in C block room 105",
        "some random text with no obvious location or category"
    ]
    
    print("========================================")
    print("GEMINI AI COMPLAINT PARSER TEST")
    print("========================================\n")
    
    all_passed = True
    
    for i, complaint in enumerate(test_cases, 1):
        print(f"Test {i}: '{complaint}'")
        try:
            result = parse_complaint(complaint)
            print(f"Result: {result}\n")
            
            # Simple validation to ensure it returns the expected dictionary structure
            if not isinstance(result, dict) or "category" not in result or "urgency" not in result:
                all_passed = False
                print("❌ FAIL: Invalid output structure.\n")
        except Exception as e:
            all_passed = False
            print(f"❌ FAIL: Exception occurred: {type(e).__name__}\n")
            
    if all_passed:
        print("✓ All tests completed successfully! The Gemini parser is returning properly structured data.")
    else:
        print("✗ Some tests failed. Please review the output above.")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
