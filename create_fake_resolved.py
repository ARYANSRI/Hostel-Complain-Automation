import os
import requests
from dotenv import load_dotenv

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
COMPLAINTS_DATABASE_ID = os.getenv("COMPLAINTS_DATABASE_ID")

def create_fake_resolved():
    url = f"https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    payload = {
        "parent": {"database_id": COMPLAINTS_DATABASE_ID},
        "properties": {
            "Complaint": {
                "title": [{"text": {"content": "Test Resolution Email"}}]
            },
            "Raw Text": {
                "rich_text": [{"text": {"content": "Test issue"}}]
            },
            "Room/Block": {
                "rich_text": [{"text": {"content": "Z-999"}}]
            },
            "Status": {
                "select": {"name": "Resolved"}
            },
            "Student Email": {
                "email": "test-live@mailtrap.io"
            },
            "Resolution Email Sent": {
                "checkbox": False
            }
        }
    }
    
    resp = requests.post(url, headers=headers, json=payload)
    print(resp.status_code)
    print(resp.json())

if __name__ == "__main__":
    create_fake_resolved()
