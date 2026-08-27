import os
from dotenv import load_dotenv

load_dotenv()

from services import create_complaint_row

def test_create():
    notion_token = os.getenv("NOTION_TOKEN")
    complaints_db_id = os.getenv("COMPLAINTS_DATABASE_ID")
    
    print("Testing create_complaint_row() against Complaints DB...")
    
    fake_data = {
        "room_block": "B-204",
        "raw_text": "TEST - fan not working room 204 block B",
        "category": "Electrical",
        "urgency": "High",
        "status": "Pending Approval",
        "vendor_assigned": "Unknown"
    }
    
    result = create_complaint_row(fake_data, notion_token, complaints_db_id)
    
    if result.get("status") == "success":
        print(f"SUCCESS! Row created in Notion with ID: {result['notion_id']}")
        print("Please check your Notion Complaints database to confirm.")
    else:
        print(f"FAILED to create row: {result}")

if __name__ == "__main__":
    test_create()
