#!/usr/bin/env python3
"""
Quick Screening Test - Test Approval/Rejection and Verify Status Updates
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:5000"
AUTH_ENDPOINT = f"{BASE_URL}/api/auth"
SCREENING_ENDPOINT = f"{BASE_URL}/api/screening"

ADMIN_CREDENTIALS = {
    "email": "trimplin@admin.com",
    "password": "Admin@123",
    "role": "Admin"
}

# Test articles
ARTICLE_12_ID = 12  # Will be approved
ARTICLE_13_ID = 13  # Will be rejected
ARTICLE_14_ID = 14  # Control - remains unchanged

def login():
    """Login as admin"""
    print("🔐 Logging in as admin...\n")
    
    response = requests.post(
        f"{AUTH_ENDPOINT}/login",
        json=ADMIN_CREDENTIALS,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        data = response.json()
        token = data["data"]["access_token"]
        print(f"✓ Login successful")
        return token
    else:
        print(f"❌ Login failed")
        return None

def test_article(token, article_id, decision, remarks):
    """Test screening decision"""
    print(f"\n{'='*70}")
    print(f"Testing Article {article_id} - Decision: {decision}")
    print(f"{'='*70}")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "decision": decision,
        "remarks": remarks
    }
    
    url = f"{SCREENING_ENDPOINT}/{article_id}/decision"
    
    print(f"\nRequest: POST {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(url, json=payload, headers=headers)
    
    print(f"\nResponse Status: {response.status_code}")
    
    if response.status_code == 201:
        data = response.json()
        print(f"✓ Decision submitted successfully")
        print(f"  - Article Status: {data['data']['new_article_status']}")
        print(f"  - Decision: {data['data']['decision']}")
        print(f"  - Screening ID: {data['data']['screening_id']}")
        return True
    else:
        print(f"❌ Failed: {response.json()['message']}")
        return False

def main():
    """Run all tests"""
    print(f"\n{'╔' + '='*68 + '╗'}")
    print(f"║ {'DIRECT DATABASE UPDATE & STATUS VERIFICATION TEST'.center(68)} ║")
    print(f"║ {'Testing Article Approval/Rejection with Status Updates'.center(68)} ║")
    print(f"{'╚' + '='*68 + '╝'}\n")
    
    print(f"Base URL: {BASE_URL}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Check server
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code == 200:
            print("✓ Server is running\n")
        else:
            print("❌ Server not responding correctly")
            return
    except:
        print("❌ Cannot connect to server")
        return
    
    # Login
    token = login()
    if not token:
        return
    
    # Test 1: Approve Article 12
    test_article(
        token, 
        ARTICLE_12_ID, 
        "Approved", 
        "Article meets all criteria. Excellent research methodology."
    )
    
    # Test 2: Reject Article 13
    test_article(
        token, 
        ARTICLE_13_ID, 
        "Rejected", 
        "The methodology is not rigorous enough for publication."
    )
    
    # Article 14 remains as control (unchanged)
    print(f"\n{'='*70}")
    print(f"Article {ARTICLE_14_ID} - CONTROL (NO CHANGE)")
    print(f"{'='*70}")
    print(f"\nThis article remains unscreened to verify no unintended updates occur.")
    
    # Summary
    print(f"\n{'='*70}")
    print(f"TEST SUMMARY")
    print(f"{'='*70}")
    print(f"\n✓ Article {ARTICLE_12_ID}: Should be 'Admin Approved'")
    print(f"✓ Article {ARTICLE_13_ID}: Should be 'Admin Rejected'")
    print(f"✓ Article {ARTICLE_14_ID}: Should remain 'Submitted'")
    print(f"\n📌 Next: Run verify_database_updates.py again to confirm status changes")
    print(f"\n{'='*70}\n")

if __name__ == "__main__":
    main()
