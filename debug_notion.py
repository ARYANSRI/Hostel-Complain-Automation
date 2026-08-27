import os
import requests
from dotenv import load_dotenv

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
COMPLAINTS_DATABASE_ID = os.getenv("COMPLAINTS_DATABASE_ID")

def debug_notion():
    url = f"https://api.notion.com/v1/databases/{COMPLAINTS_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    # Query ONLY by Status = Resolved to see what properties actually look like
    payload = {
        "filter": {
            "property": "Status",
            "select": {
                "equals": "Resolved"
            }
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    data = response.json()
    
    results = data.get("results", [])
    print(f"Found {len(results)} rows with Status = Resolved.")
    
    for row in results:
        print("\n--- Row Data ---")
        props = row["properties"]
        
        # Check Resolution Email Sent
        res_sent = props.get("Resolution Email Sent")
        print(f"Resolution Email Sent property exists: {res_sent is not None}")
        if res_sent:
            print(f"  Type: {res_sent.get('type')}")
            print(f"  Value: {res_sent.get('checkbox')}")
            
        # Check Student Email
        student_email = props.get("Student Email")
        print(f"Student Email property exists: {student_email is not None}")
        if student_email:
            print(f"  Type: {student_email.get('type')}")
            print(f"  Value: {student_email.get('email')}")

if __name__ == "__main__":
    debug_notion()
