import os
import glob
from config import (
    NOTION_TOKEN, COMPLAINTS_DATABASE_ID, VENDORS_DATABASE_ID, 
    GEMINI_API_KEY, MAILTRAP_HOST, MAILTRAP_PORT, MAILTRAP_USERNAME, 
    MAILTRAP_PASSWORD, MAIL_FROM
)

def run_test():
    print("========================================")
    print("CONFIGURATION TEST")
    print("========================================\n")
    
    # 1. Test Variables
    variables = {
        "NOTION_TOKEN": NOTION_TOKEN,
        "COMPLAINTS_DATABASE_ID": COMPLAINTS_DATABASE_ID,
        "VENDORS_DATABASE_ID": VENDORS_DATABASE_ID,
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "MAILTRAP configuration": all([MAILTRAP_HOST, MAILTRAP_PORT, MAILTRAP_USERNAME, MAILTRAP_PASSWORD, MAIL_FROM])
    }
    
    all_configured = True
    for name, value in variables.items():
        if value:
            print(f"{name}: configured")
        else:
            print(f"{name}: not configured")
            all_configured = False
            
    print("\n========================================")
    print("DEPENDENCY CHECK")
    print("========================================\n")
    
    # 2. Check for leftover 'DATABASE_ID' references in code
    files_to_check = glob.glob("**/*.py", recursive=True)
    found_generic_database_id = False
    
    for file_path in files_to_check:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                # Search for the exact env var lookup string
                target_str = 'os.getenv("DATABASE_' + 'ID")'
                target_str2 = 'os.environ["DATABASE_' + 'ID"]'
                target_str3 = "os.environ.get('DATABASE_" + "ID')"
                
                if target_str in line or target_str2 in line or target_str3 in line:
                    print(f"ERROR: Found legacy DATABASE_ID dependency in {file_path} on line {i+1}")
                    found_generic_database_id = True
                    
    if not found_generic_database_id:
        print("DATABASE_ID dependency check passed: No runtime code depends on 'DATABASE_ID'.")
        
    print("\nTest completed.")

if __name__ == "__main__":
    run_test()
