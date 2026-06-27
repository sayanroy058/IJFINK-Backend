#!/usr/bin/env python3
"""
Contact Form API Testing Script
Tests the contact form endpoints with JWT authentication (Admin only)

Usage:
    python test_contact_form_api.py
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"
AUTH_ENDPOINT = f"{BASE_URL}/api/auth"
CONTACT_ENDPOINT = f"{BASE_URL}/api/contact"

# Test data
ADMIN_CREDENTIALS = {
    "email": "trimplin@admin.com",
    "password": "Admin@123",
    "role": "Admin"
}

CONTACT_QUERY_DATA = {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "subject": "Issue with manuscript submission",
    "message": "I'm having trouble submitting my manuscript through the portal. Can you help?"
}

INVALID_CONTACT_DATA = {
    "first_name": "Jane",
    "last_name": "Smith",
    "email": "invalid-email",  # Invalid email format
    "subject": "Test Query"
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


def submit_contact_query(contact_data):
    """Submit a contact query (Public - no auth required)"""
    print_section("SUBMIT CONTACT QUERY (PUBLIC - NO AUTH REQUIRED)")
    print_test(f"Submitting contact query")
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print_request("POST", f"{CONTACT_ENDPOINT}/queries", headers=headers, body=contact_data)
    
    response = requests.post(
        f"{CONTACT_ENDPOINT}/queries",
        json=contact_data,
        headers=headers
    )
    
    print_response(response)
    
    if response.status_code == 201:
        data = response.json()
        if data.get("success"):
            query_id = data["data"]["query_id"]
            print_success(f"Contact query submitted successfully! ID: {query_id}")
            return query_id
        else:
            print_error(f"Failed to submit query: {data.get('message')}")
            return None
    else:
        print_error(f"Request failed with status {response.status_code}")
        return None


def get_all_contact_queries(token, filters=None):
    """Get all contact queries"""
    print_section("GET ALL CONTACT QUERIES")
    print_test("Retrieving all contact queries")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"{CONTACT_ENDPOINT}/queries"
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
            queries = data["data"]["queries"]
            print_success(f"Retrieved {len(queries)} contact query(ies)")
            return queries
        else:
            print_error(f"Failed to get queries: {data.get('message')}")
            return []
    else:
        print_error(f"Request failed with status {response.status_code}")
        return []


def get_contact_query_details(token, query_id):
    """Get details of a specific contact query"""
    print_section(f"GET CONTACT QUERY DETAILS (ID: {query_id})")
    print_test(f"Retrieving details for query {query_id}")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"{CONTACT_ENDPOINT}/queries/{query_id}"
    
    print_request("GET", url, headers=headers)
    
    response = requests.get(url, headers=headers)
    
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            query = data["data"]["query"]
            print_success(f"Retrieved query details: Subject: {query['subject']}")
            return query
        else:
            print_error(f"Failed to get query: {data.get('message')}")
            return None
    else:
        print_error(f"Request failed with status {response.status_code}")
        return None


def update_contact_query_status(token, query_id, new_status):
    """Update contact query status"""
    print_section(f"UPDATE CONTACT QUERY STATUS (ID: {query_id})")
    print_test(f"Setting status to: {new_status}")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "status": new_status
    }
    
    url = f"{CONTACT_ENDPOINT}/queries/{query_id}/status"
    
    print_request("PATCH", url, headers=headers, body=payload)
    
    response = requests.patch(url, json=payload, headers=headers)
    
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            print_success(f"Query status updated to {new_status}")
            return True
        else:
            print_error(f"Failed to update status: {data.get('message')}")
            return False
    else:
        print_error(f"Request failed with status {response.status_code}")
        return False


def test_unauthorized_access(query_id):
    """Test accessing endpoints without token"""
    print_section("TEST: UNAUTHORIZED ACCESS (NO TOKEN)")
    print_test("Attempting to access contact queries without authentication")
    
    headers = {"Content-Type": "application/json"}
    url = f"{CONTACT_ENDPOINT}/queries"
    
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
    
    url = f"{CONTACT_ENDPOINT}/queries"
    
    print_request("GET", url, headers=headers)
    
    response = requests.get(url, headers=headers)
    
    print_response(response)
    
    if response.status_code == 401:
        print_success("Correctly rejected invalid token")
    else:
        print_error("Security issue: Invalid token should be rejected")


def test_invalid_email():
    """Test with invalid email format"""
    print_section("TEST: INVALID EMAIL FORMAT (PUBLIC)")
    print_test("Attempting to submit query with invalid email (no auth required)")
    
    headers = {
        "Content-Type": "application/json"
    }
    
    invalid_data = {
        "first_name": "Test",
        "last_name": "User",
        "email": "invalid-email-format",
        "subject": "Test",
        "message": "Test message"
    }
    
    url = f"{CONTACT_ENDPOINT}/queries"
    
    print_request("POST", url, headers=headers, body=invalid_data)
    
    response = requests.post(url, json=invalid_data, headers=headers)
    
    print_response(response)
    
    if response.status_code == 400:
        print_success("Correctly rejected invalid email format")
    else:
        print_error("Invalid email should have been rejected")


def test_missing_fields():
    """Test with missing required fields"""
    print_section("TEST: MISSING REQUIRED FIELDS (PUBLIC)")
    print_test("Attempting to submit query with missing fields (no auth required)")
    
    headers = {
        "Content-Type": "application/json"
    }
    
    incomplete_data = {
        "first_name": "Test",
        "last_name": "User"
        # Missing: email, subject, message
    }
    
    url = f"{CONTACT_ENDPOINT}/queries"
    
    print_request("POST", url, headers=headers, body=incomplete_data)
    
    response = requests.post(url, json=incomplete_data, headers=headers)
    
    print_response(response)
    
    if response.status_code == 400:
        print_success("Correctly rejected incomplete data")
    else:
        print_error("Missing fields should have been rejected")


def test_invalid_status(token, query_id):
    """Test with invalid status value"""
    print_section("TEST: INVALID STATUS VALUE")
    print_test("Attempting to set invalid status")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    invalid_payload = {
        "status": "InvalidStatus"
    }
    
    url = f"{CONTACT_ENDPOINT}/queries/{query_id}/status"
    
    print_request("PATCH", url, headers=headers, body=invalid_payload)
    
    response = requests.patch(url, json=invalid_payload, headers=headers)
    
    print_response(response)
    
    if response.status_code == 400:
        print_success("Correctly rejected invalid status")
    else:
        print_error("Invalid status should have been rejected")


def test_nonexistent_query(token):
    """Test accessing non-existent query"""
    print_section("TEST: NON-EXISTENT QUERY")
    print_test("Attempting to access non-existent query")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"{CONTACT_ENDPOINT}/queries/99999"
    
    print_request("GET", url, headers=headers)
    
    response = requests.get(url, headers=headers)
    
    print_response(response)
    
    if response.status_code == 404:
        print_success("Correctly returned 404 for non-existent query")
    else:
        print_error("Should return 404 for non-existent query")


def test_filter_queries(token):
    """Test filtering queries"""
    print_section("TEST: FILTER QUERIES")
    print_test("Testing query filtering functionality")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test 1: Filter by status
    print_info("Test 1: Filter by status=Pending")
    url = f"{CONTACT_ENDPOINT}/queries?status=Pending"
    print_request("GET", url, headers=headers)
    response = requests.get(url, headers=headers)
    print_response(response)
    
    # Test 2: Filter assigned to me
    print_info("Test 2: Filter by assigned_to_me=true")
    url = f"{CONTACT_ENDPOINT}/queries?assigned_to_me=true"
    print_request("GET", url, headers=headers)
    response = requests.get(url, headers=headers)
    print_response(response)


def test_public_submission():
    """Test that public users can submit queries without authentication"""
    print_section("TEST: PUBLIC SUBMISSION (NO AUTH REQUIRED)")
    print_test("Submitting contact query without any authentication")
    
    headers = {"Content-Type": "application/json"}
    
    public_data = {
        "first_name": "Jane",
        "last_name": "Public",
        "email": "jane.public@example.com",
        "subject": "Public Query",
        "message": "This is a query submitted by a public user"
    }
    
    url = f"{CONTACT_ENDPOINT}/queries"
    
    print_request("POST", url, headers=headers, body=public_data)
    
    response = requests.post(url, json=public_data, headers=headers)
    
    print_response(response)
    
    if response.status_code == 201:
        print_success("Public users can submit contact queries without authentication")
    else:
        print_error("Public submission should be allowed")


def test_get_without_auth():
    """Test that GET endpoints require authentication"""
    print_section("TEST: GET WITHOUT AUTHENTICATION")
    print_test("Attempting to GET queries without JWT token")
    
    headers = {"Content-Type": "application/json"}
    
    url = f"{CONTACT_ENDPOINT}/queries"
    
    print_request("GET", url, headers=headers)
    
    response = requests.get(url, headers=headers)
    
    print_response(response)
    
    if response.status_code == 401:
        print_success("GET endpoint correctly requires authentication")
    else:
        print_error("GET endpoint should require authentication (401)")


def main():
    """Run all tests"""
    print(f"\n{Colors.BLUE}")
    print("╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "IJFINK BACKEND - CONTACT FORM API TEST SUITE".center(78) + "║")
    print("║" + " "*78 + "║")
    print("║" + "Testing Contact Form Endpoints (Public POST, Admin-only GET/PATCH)".center(78) + "║")
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
    
    # Step 2: Submit a contact query (PUBLIC - no auth required)
    query_id = submit_contact_query(CONTACT_QUERY_DATA)
    if not query_id:
        print_error("Cannot proceed without contact query")
        return
    
    # Step 3: Get all contact queries
    all_queries = get_all_contact_queries(admin_token)
    
    # Step 4: Get specific query details
    query_details = get_contact_query_details(admin_token, query_id)
    
    # Step 5: Update query status to Resolved
    update_contact_query_status(admin_token, query_id, "Resolved")
    
    # Step 6: Verify status update
    updated_query = get_contact_query_details(admin_token, query_id)
    if updated_query and updated_query["status"] == "Resolved":
        print_success("Query status update verified")
    
    # Step 7: Revert status back to Pending
    update_contact_query_status(admin_token, query_id, "Pending")
    
    # Step 8: Test public submission and authentication requirements
    test_public_submission()
    test_get_without_auth()
    
    # Step 9: Security tests
    test_unauthorized_access(query_id)
    test_invalid_token()
    test_invalid_email()
    test_missing_fields()
    test_invalid_status(admin_token, query_id)
    test_nonexistent_query(admin_token)
    
    # Step 10: Test filtering
    test_filter_queries(admin_token)
    
    # Summary
    print_section("TEST SUMMARY")
    print_success("All tests completed!")
    print_info(f"Testing finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


if __name__ == "__main__":
    main()
