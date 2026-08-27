import os
import requests
from dotenv import load_dotenv

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
COMPLAINTS_DATABASE_ID = os.getenv("COMPLAINTS_DATABASE_ID")

def debug_query():
    url = f"https://api.notion.com/v1/databases/{COMPLAINTS_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    payload = {
        "filter": {
            "and": [
                {
                    "property": "Status",
                    "select": {
                        "equals": "Resolved"
                    }
                }
            ]
        }
    }
    
    # Try different combinations
    resp = requests.post(url, headers=headers, json=payload)
    print("Status=Resolved count:", len(resp.json().get("results", [])))
    
    payload["filter"]["and"].append({
        "property": "Resolution Email Sent",
        "checkbox": {
            "equals": False
        }
    })
    resp = requests.post(url, headers=headers, json=payload)
    print("Status=Resolved AND Checkbox=False count:", len(resp.json().get("results", [])))
    
    payload["filter"]["and"][1] = {
        "property": "Resolution Email Sent",
        "checkbox": {
            "does_not_equal": True
        }
    }
    resp = requests.post(url, headers=headers, json=payload)
    print("Status=Resolved AND Checkbox!=True count:", len(resp.json().get("results", [])))

if __name__ == "__main__":
    debug_query()
