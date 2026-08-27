import os
from dotenv import load_dotenv

load_dotenv()

from services import check_approvals

def test_approvals():
    notion_token = os.getenv("NOTION_TOKEN")
    complaints_db_id = os.getenv("COMPLAINTS_DATABASE_ID")
    
    print("Checking pending approvals...")
    
    approved_complaints = check_approvals(notion_token, complaints_db_id)
    
    if not approved_complaints:
        print("No approved complaints found.")
        return
        
    print(f"Found {len(approved_complaints)} approved complaints.")
    for c in approved_complaints:
        print(f"ID: {c['id']}")
        print(f"  Category: {c['category']}")
        print(f"  Status: {c['status']}")
        print(f"  Approved By: {c.get('approved_by')}")
        print("Vendor lookup starting (simulated)...")
        print("---")

if __name__ == "__main__":
    test_approvals()
