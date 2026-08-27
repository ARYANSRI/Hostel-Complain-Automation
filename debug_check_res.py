import os
import requests
from dotenv import load_dotenv

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
COMPLAINTS_DATABASE_ID = os.getenv("COMPLAINTS_DATABASE_ID")

def check_res():
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
    
    response = requests.post(url, headers=headers, json=payload)
    data = response.json()
    
    print("Fetched", len(data.get("results", [])), "results")
    
    resolved_complaints = []
    for row in data.get("results", []):
        props = row["properties"]
        
        print("Row ID:", row["id"])
        
        res_email_sent_prop = props.get("Resolution Email Sent", {})
        print("Checkbox prop:", res_email_sent_prop.get("checkbox"))
        if res_email_sent_prop.get("checkbox") is True:
            print("Skipping because checkbox is True")
            continue
        
        cat_prop = props.get("Category", {}).get("select")
        category = cat_prop.get("name") if cat_prop else "Other"
        
        room_rt = props.get("Room/Block", {}).get("rich_text", [])
        room_block = room_rt[0]["plain_text"] if room_rt else ""
        
        text_rt = props.get("Raw Text", {}).get("rich_text", [])
        raw_text = text_rt[0]["plain_text"] if text_rt else ""
        
        student_email_prop = props.get("Student Email", {}).get("email")
        print("Appending email:", student_email_prop)
        
        resolved_complaints.append({
            "id": row["id"],
            "category": category,
            "room_block": room_block,
            "raw_text": raw_text,
            "status": "Resolved",
            "student_email": student_email_prop
        })
    print("Returning", len(resolved_complaints))
    
if __name__ == "__main__":
    check_res()
