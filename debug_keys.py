import os
import requests
from dotenv import load_dotenv

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
COMPLAINTS_DATABASE_ID = os.getenv("COMPLAINTS_DATABASE_ID")

def debug_keys():
    url = f"https://api.notion.com/v1/databases/{COMPLAINTS_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    resp = requests.post(url, headers=headers, json={})
    data = resp.json()
    if data.get("results"):
        print("Property keys:", list(data["results"][0]["properties"].keys()))

if __name__ == "__main__":
    debug_keys()
