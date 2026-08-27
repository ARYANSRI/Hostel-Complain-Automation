from dispatch.email import notify_student_resolved

def test_student_email():
    print("========================================")
    print("STUDENT RESOLUTION EMAIL TEST")
    print("========================================\n")
    
    fake_complaint = {
        "room_block": "B-204",
        "category": "Electrical",
        "raw_text": "Fan not working since morning",
        "status": "Resolved"
    }
    student_email = "test@mailtrap.io"
    
    print(f"Sending resolution email to {student_email}...\n")
    
    result = notify_student_resolved(student_email, fake_complaint)
    
    if result.get("success"):
        print("SUCCESS: Resolution email sent.")
        print("Check your Mailtrap inbox!")
    else:
        print(f"FAILED: {result.get('message')}")

if __name__ == "__main__":
    test_student_email()
