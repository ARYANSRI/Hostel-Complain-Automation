"""
Diagnostic script: Lists available Gemini models for the configured API key.
Does NOT print the API key or any credentials.
"""
import os
from dotenv import load_dotenv
load_dotenv()

from google import genai

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("ERROR: GEMINI_API_KEY is not set in .env")
    exit(1)

print(f"API key loaded: {'Yes (hidden)' }")
print(f"Currently configured GEMINI_MODEL: {os.getenv('GEMINI_MODEL', '(not set)')}")
print()

client = genai.Client(api_key=api_key)

print("=" * 60)
print("AVAILABLE GEMINI MODELS (text generation capable)")
print("=" * 60)

try:
    models = client.models.list()
    flash_models = []
    pro_models = []
    other_models = []
    
    for model in models:
        name = model.name
        # Only show models that support generateContent
        supported = getattr(model, 'supported_generation_methods', None)
        
        # Filter for text generation models
        if 'flash' in name.lower():
            flash_models.append(name)
        elif 'pro' in name.lower():
            pro_models.append(name)
        else:
            other_models.append(name)
    
    if flash_models:
        print("\n--- Flash Models (fast, lightweight) ---")
        for m in sorted(flash_models):
            print(f"  {m}")
    
    if pro_models:
        print("\n--- Pro Models (higher capability) ---")
        for m in sorted(pro_models):
            print(f"  {m}")
    
    if other_models:
        print("\n--- Other Models ---")
        for m in sorted(other_models):
            print(f"  {m}")
    
    total = len(flash_models) + len(pro_models) + len(other_models)
    print(f"\nTotal models listed: {total}")
    
except Exception as e:
    print(f"ERROR listing models: {type(e).__name__}: {e}")
