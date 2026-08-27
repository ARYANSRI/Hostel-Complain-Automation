"""
Test which models work with structured JSON output (response_schema) for complaint parsing.
"""
import os, json
from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

class ComplaintSchema(BaseModel):
    category: str = Field(description="Must be exactly one of: Electrical, Plumbing, WiFi, Furniture, Other")
    urgency: str = Field(description="Must be exactly one of: Low, Medium, High")
    room_block: str | None = Field(description="Use null when room/block cannot be identified", default=None)

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

test_text = "Bulb low light in room X-265"
system_instruction = (
    "Analyze the student's hostel complaint. Extract category, urgency, and room/block. "
    "Category: Electrical, Plumbing, WiFi, Furniture, Other. "
    "Urgency: Low, Medium, High. "
    "Return ONLY valid JSON."
)

models_to_test = [
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
]

for model in models_to_test:
    print(f"\n--- Testing: {model} ---")
    
    # Test 1: With structured schema
    try:
        response = client.models.generate_content(
            model=model,
            contents=test_text,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=ComplaintSchema
            )
        )
        result = json.loads(response.text)
        print(f"  Structured output: SUCCESS -> {result}")
    except Exception as e:
        err_str = str(e)
        if "429" in err_str:
            print(f"  Structured output: QUOTA EXHAUSTED (429)")
        elif "404" in err_str:
            print(f"  Structured output: NOT AVAILABLE (404)")
        else:
            print(f"  Structured output: FAILED ({type(e).__name__})")
            # Try without structured schema as fallback
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=test_text,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                    )
                )
                result = json.loads(response.text)
                print(f"  Plain JSON mode:   SUCCESS -> {result}")
            except Exception as e2:
                err2 = str(e2)
                if "429" in err2:
                    print(f"  Plain JSON mode:   QUOTA EXHAUSTED (429)")
                else:
                    print(f"  Plain JSON mode:   FAILED ({type(e2).__name__})")
