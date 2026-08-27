"""
Diagnostic: Test parse_complaint() with sample inputs.
Shows model used, success/failure, and parsed result.
Does NOT print API keys or credentials.
"""
import os
import time
from dotenv import load_dotenv
load_dotenv()

from services import parse_complaint

model = os.getenv("GEMINI_MODEL", "(not set)")
print(f"Model configured: {model}")
print(f"API key loaded: {'Yes (hidden)' if os.getenv('GEMINI_API_KEY') else 'NO'}")
print()

test_cases = [
    "Bulb low light in room X-265",
    "wifi not working room 210 block B",
    "water pipe burst in room 105 block C",
]

for i, text in enumerate(test_cases):
    print(f"--- Test {i+1} ---")
    print(f"Input: {text}")
    try:
        result = parse_complaint(text)
        print(f"Result: {result}")
        
        # Check if it fell back to defaults (meaning Gemini failed)
        if result == {"category": "Other", "urgency": "Medium", "room_block": None}:
            print("NOTE: Got default fallback values. Gemini may have failed (check logs above).")
        else:
            print("SUCCESS: Gemini parsed the complaint correctly.")
    except Exception as e:
        print(f"EXCEPTION: {type(e).__name__}: {e}")
    
    print()
    
    # Small delay between requests to avoid hitting rate limits
    if i < len(test_cases) - 1:
        print("(Waiting 10 seconds to respect rate limits...)")
        time.sleep(10)

print("Test complete.")
