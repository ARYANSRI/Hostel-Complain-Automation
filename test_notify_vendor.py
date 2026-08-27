import sys
from dotenv import load_dotenv
from dispatch.email import notify_vendor

def run_test():
    # 2. Load all required environment variables from the existing .env securely
    load_dotenv()
    
    print("========================================")
    print("HOSTEL MAINTENANCE EMAIL TEST")
    print("========================================\n")
    
    # 4. Use a realistic fake hostel complaint for testing via Mailtrap
    vendor_email = "test@mailtrap.io"
    complaint_details = {
        "category": "Electrical",
        "urgency": "High",
        "room_block": "Block B - Room 204",
        "raw_text": "Fan not working in B block room 204 since morning"
    }
    
    print("Sending test complaint notification...\n")
    
    try:
        # 5. Call the actual implementation from dispatch.email
        result = notify_vendor(vendor_email, complaint_details)
        
        # 6. Print clear result safely
        if result["success"]:
            print("SUCCESS: Test email sent successfully!")
            print(f"Check your Mailtrap inbox for: {vendor_email}")
            print("\nResponse details:")
            print(result)
        else:
            print("FAILED: Email test failed.")
            print(f"Error Message: {result.get('message', 'Unknown error.')}")
            
    except Exception as e:
        # Failsafe in case an unexpected error bubbles up outside the try/except block in email.py
        print("FAILED: Email test failed.")
        print(f"Error Details: {type(e).__name__}")
        sys.exit(1)

if __name__ == "__main__":
    run_test()
