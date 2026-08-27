from services import decide_status

def test_decide_status():
    print("Testing decide_status logic:\n")
    
    cases = [
        ("High", "Electrical", "Pending Approval"),
        ("Low", "Other", "Pending Approval"),
        ("Medium", "Plumbing", "Auto-Approved"),
        ("Low", "WiFi", "Auto-Approved")
    ]
    
    all_passed = True
    for urgency, category, expected in cases:
        result = decide_status(urgency, category)
        status = "PASSED" if result == expected else f"FAILED (Got {result})"
        print(f"Urgency: {urgency:6} | Category: {category:10} -> Expected: {expected:16} | Result: {status}")
        if result != expected:
            all_passed = False
            
    print(f"\nOverall Result: {'ALL PASSED' if all_passed else 'FAILED'}")

if __name__ == "__main__":
    test_decide_status()
