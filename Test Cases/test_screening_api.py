#!/usr/bin/env python3
"""
Admin Screening API Testing Script
Tests the manuscript screening endpoints with JWT authentication (Admin only)

Usage:
    python test_screening_api.py
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"
AUTH_ENDPOINT = f"{BASE_URL}/api/auth"
SCREENING_ENDPOINT = f"{BASE_URL}/api/screening"

# Test data
ADMIN_CREDENTIALS = {
    "email": "trimplin@admin.com",
    "password": "Admin@123",
    "role": "Admin"
}


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'


def print_section(title):
    """Print a formatted section title"""
    print(f"\n{Colors.BLUE}{'='*80}")
    print(f"{title:^80}")
    print(f"{'='*80}{Colors.END}\n")


def print_success(message):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_error(message):
    """Print error message"""
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_info(message):
    """Print info message"""
    print(f"{Colors.YELLOW}ℹ {message}{Colors.END}")


def print_test(message):
    """Print test message"""
    print(f"{Colors.CYAN}▶ {message}{Colors.END}")


def print_request(method, url, headers=None, body=None):
    """Print request details"""
    print(f"\n{Colors.BLUE}Request:{Colors.END}")
    print(f"  {method} {url}")
    if headers:
        print(f"  Headers: {json.dumps(headers, indent=4)}")
    if body:
        print(f"  Body: {json.dumps(body, indent=4)}")


def print_response(response):
    """Print response details"""
    print(f"\n{Colors.BLUE}Response:{Colors.END}")
    print(f"  Status: {response.status_code}")
    try:
        print(f"  Body: {json.dumps(response.json(), indent=4)}")
    except:
        print(f"  Body: {response.text}")


def login(credentials):
    """Login and return JWT token"""
    print_section(f"LOGGING IN AS {credentials['role'].upper()}")
    
    payload = {
        "email": credentials["email"],
        "password": credentials["password"],
        "role": credentials["role"]
    }
    
    print_request("POST", f"{AUTH_ENDPOINT}/login", body=payload)
    
    response = requests.post(
        f"{AUTH_ENDPOINT}/login",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            token = data["data"]["access_token"]
            user = data["data"]["user"]
            print_success(f"Login successful!")
            return token, user
        else:
            print_error(f"Login failed: {data.get('message')}")
            return None, None
    else:
        print_error(f"Login failed with status {response.status_code}")
        return None, None


def get_pending_articles(token):
    """Get all articles pending screening"""
    print_section("GET PENDING ARTICLES FOR SCREENING")
    print_test("Retrieving all articles pending admin screening")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"{SCREENING_ENDPOINT}/pending"
    
    print_request("GET", url, headers=headers)
    
    response = requests.get(url, headers=headers)
    
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            articles = data["data"]["articles"]
            print_success(f"Retrieved {len(articles)} pending article(s)")
            return articles
        else:
            print_error(f"Failed to get pending articles: {data.get('message')}")
            return []
    else:
        print_error(f"Request failed with status {response.status_code}")
        return []


def get_article_details(token, article_id):
    """Get details of a specific article for screening"""
    print_section(f"GET ARTICLE DETAILS (ID: {article_id})")
    print_test(f"Retrieving details for article {article_id}")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"{SCREENING_ENDPOINT}/{article_id}"
    
    print_request("GET", url, headers=headers)
    
    response = requests.get(url, headers=headers)
    
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            article = data["data"]["article"]
            print_success(f"Retrieved article: {article['title']}")
            return article
        else:
            print_error(f"Failed to get article: {data.get('message')}")
            return None
    else:
        print_error(f"Request failed with status {response.status_code}")
        return None


def submit_screening_decision(token, article_id, decision, remarks=""):
    """Submit screening decision for an article"""
    print_section(f"SUBMIT SCREENING DECISION (ID: {article_id})")
    print_test(f"Submitting decision: {decision}")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "decision": decision,
        "remarks": remarks
    }
    
    url = f"{SCREENING_ENDPOINT}/{article_id}/decision"
    
    print_request("POST", url, headers=headers, body=payload)
    
    response = requests.post(url, json=payload, headers=headers)
    
    print_response(response)
    
    if response.status_code == 201:
        data = response.json()
        if data.get("success"):
            screening_id = data["data"]["screening_id"]
            print_success(f"Screening decision submitted! Screening ID: {screening_id}")
            return screening_id
        else:
            print_error(f"Failed to submit decision: {data.get('message')}")
            return None
    else:
        print_error(f"Request failed with status {response.status_code}")
        return None


def get_screening_history(token, filters=None):
    """Get screening history"""
    print_section("GET SCREENING HISTORY")
    print_test("Retrieving screening history")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"{SCREENING_ENDPOINT}/history"
    if filters:
        query_params = "&".join(f"{k}={v}" for k, v in filters.items() if v)
        if query_params:
            url += f"?{query_params}"
    
    print_request("GET", url, headers=headers)
    
    response = requests.get(url, headers=headers)
    
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            screenings = data["data"]["screenings"]
            print_success(f"Retrieved {len(screenings)} screening record(s)")
            return screenings
        else:
            print_error(f"Failed to get history: {data.get('message')}")
            return []
    else:
        print_error(f"Request failed with status {response.status_code}")
        return []


def test_unauthorized_access():
    """Test accessing endpoints without token"""
    print_section("TEST: UNAUTHORIZED ACCESS (NO TOKEN)")
    print_test("Attempting to access screening endpoints without authentication")
    
    headers = {"Content-Type": "application/json"}
    url = f"{SCREENING_ENDPOINT}/pending"
    
    print_request("GET", url, headers=headers)
    
    response = requests.get(url, headers=headers)
    
    print_response(response)
    
    if response.status_code == 401:
        print_success("Correctly rejected request without token")
    else:
        print_error("Security issue: Request should have been rejected")


def test_invalid_token():
    """Test with invalid JWT token"""
    print_section("TEST: INVALID TOKEN")
    print_test("Attempting to access with invalid JWT token")
    
    headers = {
        "Authorization": "Bearer invalid.token.here",
        "Content-Type": "application/json"
    }
    
    url = f"{SCREENING_ENDPOINT}/pending"
    
    print_request("GET", url, headers=headers)
    
    response = requests.get(url, headers=headers)
    
    print_response(response)
    
    if response.status_code == 401:
        print_success("Correctly rejected invalid token")
    else:
        print_error("Security issue: Invalid token should be rejected")


def test_invalid_decision(token, article_id):
    """Test with invalid decision value"""
    print_section("TEST: INVALID DECISION VALUE")
    print_test("Attempting to submit invalid decision")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "decision": "InvalidDecision",
        "remarks": "Test"
    }
    
    url = f"{SCREENING_ENDPOINT}/{article_id}/decision"
    
    print_request("POST", url, headers=headers, body=payload)
    
    response = requests.post(url, json=payload, headers=headers)
    
    print_response(response)
    
    if response.status_code == 400:
        print_success("Correctly rejected invalid decision")
    else:
        print_error("Invalid decision should have been rejected")


def test_nonexistent_article(token):
    """Test accessing non-existent article"""
    print_section("TEST: NON-EXISTENT ARTICLE")
    print_test("Attempting to access non-existent article")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"{SCREENING_ENDPOINT}/99999"
    
    print_request("GET", url, headers=headers)
    
    response = requests.get(url, headers=headers)
    
    print_response(response)
    
    if response.status_code == 404:
        print_success("Correctly returned 404 for non-existent article")
    else:
        print_error("Should return 404 for non-existent article")


def test_filter_history(token):
    """Test filtering screening history"""
    print_section("TEST: FILTER SCREENING HISTORY")
    print_test("Testing screening history filtering")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test 1: Filter by decision=Approved
    print_info("Test 1: Filter by decision=Approved")
    url = f"{SCREENING_ENDPOINT}/history?decision=Approved"
    print_request("GET", url, headers=headers)
    response = requests.get(url, headers=headers)
    print_response(response)
    
    # Test 2: Filter by screened_by_me=true
    print_info("Test 2: Filter by screened_by_me=true")
    url = f"{SCREENING_ENDPOINT}/history?screened_by_me=true"
    print_request("GET", url, headers=headers)
    response = requests.get(url, headers=headers)
    print_response(response)


def main():
    """Run all tests"""
    print(f"\n{Colors.BLUE}")
    print("╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "IJFINK BACKEND - ADMIN SCREENING API TEST SUITE".center(78) + "║")
    print("║" + " "*78 + "║")
    print("║" + "Testing Manuscript Screening Endpoints (Admin Only)".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")
    print(f"{Colors.END}")
    
    print_info(f"Base URL: {BASE_URL}")
    print_info(f"Testing started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code == 200:
            print_success("Server is running")
        else:
            print_error("Server is not responding correctly")
            return
    except requests.exceptions.ConnectionError:
        print_error(f"Cannot connect to server at {BASE_URL}")
        print_info("Please ensure the Flask server is running on http://localhost:5000")
        return
    except Exception as e:
        print_error(f"Error connecting to server: {e}")
        return
    
    # Step 1: Login as Admin
    admin_token, admin_user = login(ADMIN_CREDENTIALS)
    if not admin_token:
        print_error("Cannot proceed without admin token")
        return
    
    # Step 2: Get pending articles for screening
    pending_articles = get_pending_articles(admin_token)
    
    if not pending_articles:
        print_info("No pending articles to screen. Skipping to history and security tests...")
    else:
        # Step 3: Get details of first pending article
        first_article_id = pending_articles[0]["article_id"]
        article_details = get_article_details(admin_token, first_article_id)
        
        # Step 4: Submit approved decision
        approval_id = submit_screening_decision(admin_token, first_article_id, "Approved", "This manuscript meets all criteria.")
        
        # Step 5: Attempt to screen already screened article
        print_section("TEST: ALREADY SCREENED ARTICLE")
        print_test("Attempting to screen an already screened article")
        
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "decision": "Rejected",
            "remarks": "This should fail"
        }
        
        url = f"{SCREENING_ENDPOINT}/{first_article_id}/decision"
        
        print_request("POST", url, headers=headers, body=payload)
        
        response = requests.post(url, json=payload, headers=headers)
        
        print_response(response)
        
        if response.status_code == 400:
            print_success("Correctly rejected attempt to re-screen article")
        else:
            print_error("Should have rejected re-screening attempt")
    
    # Step 6: Get screening history
    history = get_screening_history(admin_token)
    
    # Step 7: Security tests
    test_unauthorized_access()
    test_invalid_token()
    
    if pending_articles:
        test_invalid_decision(admin_token, pending_articles[0]["article_id"])
    
    test_nonexistent_article(admin_token)
    
    # Step 8: Test filtering
    test_filter_history(admin_token)
    
    # Summary
    print_section("TEST SUMMARY")
    print_success("All tests completed!")
    print_info(f"Testing finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


if __name__ == "__main__":
    main()
