import os
import requests
from dotenv import load_dotenv

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
COMPLAINTS_DATABASE_ID = os.getenv("COMPLAINTS_DATABASE_ID")

def debug():
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
                },
                {
                    "property": "Student Email",
                    "email": {
                        "is_not_empty": True
                    }
                }
            ]
        }
    }
    
    resp = requests.post(url, headers=headers, json=payload)
    print("Filter hits:", len(resp.json().get("results", [])))

debug()
