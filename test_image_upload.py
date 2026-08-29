import os
import base64
from dotenv import load_dotenv
load_dotenv()

from services import describe_image_issue
from fastapi.testclient import TestClient
from main import app

SAMPLE_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)

def test_describe_image():
    print("Testing describe_image_issue function...")
    image_bytes = base64.b64decode(SAMPLE_PNG_BASE64)
    result = describe_image_issue(image_bytes, "image/png")
    print(f"Result from describe_image_issue: {result}")
    assert isinstance(result, dict)
    assert "success" in result

def test_analyze_image_endpoint():
    print("\nTesting /analyze-image endpoint via TestClient...")
    client = TestClient(app)
    response = client.post("/analyze-image", json={
        "image": f"data:image/png;base64,{SAMPLE_PNG_BASE64}",
        "mime_type": "image/png"
    })
    print(f"Endpoint status code: {response.status_code}")
    data = response.json()
    print(f"Endpoint response json: {data}")
    assert response.status_code == 200
    assert "success" in data

if __name__ == "__main__":
    try:
        test_describe_image()
        test_analyze_image_endpoint()
        print("\n[SUCCESS] Image analysis tests passed successfully!")
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
