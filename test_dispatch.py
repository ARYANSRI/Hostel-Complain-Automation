import asyncio
import os
from dotenv import load_dotenv

# Load env vars before importing main
load_dotenv()

from main import run_dispatch

async def test_dispatch_pipeline():
    print("========================================")
    print("PIPELINE DISPATCH TEST")
    print("========================================")
    print("Triggering the dispatch pipeline manually...\n")
    
    result = await run_dispatch()
    print("RESULT:")
    print(result)

if __name__ == "__main__":
    asyncio.run(test_dispatch_pipeline())
