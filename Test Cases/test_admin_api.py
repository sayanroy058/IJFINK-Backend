#!/usr/bin/env python3
"""
Admin API Testing Script
Tests the activate/deactivate user endpoints with JWT authentication

Usage:
    python test_admin_api.py
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"
AUTH_ENDPOINT = f"{BASE_URL}/api/auth"
ADMIN_ENDPOINT = f"{BASE_URL}/api/admin"

# Test data
ADMIN_CREDENTIALS = {
    "email": "trimplin@admin.com",
    "password": "Admin@123",
    "role": "Admin"
}

AUTHOR_CREDENTIALS = {
    "email": "author@ijfink.com",
    "password": "author123456",
    "role": "Author"
}

# Test user for registration
TEST_USER_REGISTRATION = {
    "first_name": "Test",
    "last_name": "User",
    "email": "testuser2@example.com",
    "password": "TestUser@123",
    "confirm_password": "TestUser@123",
    "institution": "Test Institution",
    "role": "Author"
}


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
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
            print_success(f"Login successful! Token: {token[:50]}...")
            return token, user
        else:
            print_error(f"Login failed: {data.get('message')}")
            return None, None
    else:
        print_error(f"Login failed with status {response.status_code}")
        return None, None


def register_user(registration_data, admin_token):
    """Register a new user account"""
    print_section("REGISTERING NEW TEST USER")
    
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }
    
    print_request("POST", f"{AUTH_ENDPOINT}/register", headers=headers, body=registration_data)
    
    response = requests.post(
        f"{AUTH_ENDPOINT}/register",
        json=registration_data,
        headers=headers
    )
    
    print_response(response)
    
    if response.status_code == 201:
        data = response.json()
        if data.get("success"):
            user = data["data"]["user"]
            print_success(f"User registered successfully! Email: {user['email']}")
            return user
        else:
            print_error(f"Registration failed: {data.get('message')}")
            return None
    else:
        print_error(f"Registration failed with status {response.status_code}")
        return None


def test_login_with_inactive_user(inactive_user_credentials):
    """Test that an inactive user cannot login"""
    print_section("TEST: LOGIN WITH INACTIVE USER")
    
    payload = {
        "email": inactive_user_credentials["email"],
        "password": inactive_user_credentials["password"],
        "role": "Author"
    }
    
    print_request("POST", f"{AUTH_ENDPOINT}/login", body=payload)
    print_info("Attempting to login with deactivated user account...")
    
    response = requests.post(
        f"{AUTH_ENDPOINT}/login",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print_response(response)
    
    if response.status_code == 403:
        data = response.json()
        if "inactive" in data.get("message", "").lower():
            print_success("Correctly rejected inactive user (account is suspended)")
            return True
        else:
            print_error(f"Got 403 but with unexpected message: {data.get('message')}")
            return False
    else:
        print_error(f"Expected 403 but got {response.status_code} - Inactive user should be rejected!")
        return False


def get_all_users(token, filters=None):
    """Get all users"""
    print_section("GET ALL USERS")
    
    params = {}
    if filters:
        params.update(filters)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"{ADMIN_ENDPOINT}/users"
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items() if v)
    
    print_request("GET", url, headers=headers)
    
    response = requests.get(url, headers=headers)
    
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            users = data["data"]["users"]
            print_success(f"Retrieved {len(users)} user(s)")
            return users
        else:
            print_error(f"Failed to get users: {data.get('message')}")
            return []
    else:
        print_error(f"Request failed with status {response.status_code}")
        return []


def get_user_details(token, user_id):
    """Get details of a specific user"""
    print_section(f"GET USER DETAILS (ID: {user_id})")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"{ADMIN_ENDPOINT}/users/{user_id}"
    
    print_request("GET", url, headers=headers)
    
    response = requests.get(url, headers=headers)
    
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            user = data["data"]["user"]
            print_success(f"Retrieved user: {user['email']}")
            return user
        else:
            print_error(f"Failed to get user: {data.get('message')}")
            return None
    else:
        print_error(f"Request failed with status {response.status_code}")
        return None


def toggle_user_status(token, user_id, new_status):
    """Toggle user status (Active/Inactive)"""
    print_section(f"TOGGLE USER STATUS (ID: {user_id})")
    print_info(f"Setting status to: {new_status}")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "status": new_status
    }
    
    url = f"{ADMIN_ENDPOINT}/users/{user_id}/status"
    
    print_request("PATCH", url, headers=headers, body=payload)
    
    response = requests.patch(url, json=payload, headers=headers)
    
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            print_success(f"User status updated: {data.get('message')}")
            return True
        else:
            print_error(f"Failed to update status: {data.get('message')}")
            return False
    else:
        print_error(f"Request failed with status {response.status_code}")
        return False


def test_unauthorized_access(user_id):
    """Test accessing admin endpoints without token"""
    print_section("TEST: UNAUTHORIZED ACCESS (NO TOKEN)")
    
    headers = {"Content-Type": "application/json"}
    url = f"{ADMIN_ENDPOINT}/users/{user_id}/status"
    payload = {"status": "Inactive"}
    
    print_request("PATCH", url, headers=headers, body=payload)
    
    response = requests.patch(url, json=payload, headers=headers)
    
    print_response(response)
    
    if response.status_code == 401:
        print_success("Correctly rejected request without token")
    else:
        print_error("Security issue: Request should have been rejected")


def test_non_admin_access(author_token, user_id):
    """Test accessing admin endpoints as non-admin user"""
    print_section("TEST: NON-ADMIN ACCESS")
    
    headers = {
        "Authorization": f"Bearer {author_token}",
        "Content-Type": "application/json"
    }
    
    url = f"{ADMIN_ENDPOINT}/users/{user_id}/status"
    payload = {"status": "Inactive"}
    
    print_request("PATCH", url, headers=headers, body=payload)
    
    response = requests.patch(url, json=payload, headers=headers)
    
    print_response(response)
    
    if response.status_code == 403:
        print_success("Correctly rejected non-admin user")
    else:
        print_error("Security issue: Non-admin should not have access")


def test_invalid_token():
    """Test with invalid JWT token"""
    print_section("TEST: INVALID TOKEN")
    
    headers = {
        "Authorization": "Bearer invalid.token.here",
        "Content-Type": "application/json"
    }
    
    url = f"{ADMIN_ENDPOINT}/users"
    
    print_request("GET", url, headers=headers)
    
    response = requests.get(url, headers=headers)
    
    print_response(response)
    
    if response.status_code == 401:
        print_success("Correctly rejected invalid token")
    else:
        print_error("Security issue: Invalid token should be rejected")


def test_invalid_status(admin_token, user_id):
    """Test with invalid status value"""
    print_section("TEST: INVALID STATUS VALUE")
    
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }
    
    url = f"{ADMIN_ENDPOINT}/users/{user_id}/status"
    payload = {"status": "InvalidStatus"}
    
    print_request("PATCH", url, headers=headers, body=payload)
    
    response = requests.patch(url, json=payload, headers=headers)
    
    print_response(response)
    
    if response.status_code == 400:
        print_success("Correctly rejected invalid status")
    else:
        print_error("Invalid status should have been rejected")


def test_nonexistent_user(admin_token):
    """Test accessing non-existent user"""
    print_section("TEST: NON-EXISTENT USER")
    
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }
    
    url = f"{ADMIN_ENDPOINT}/users/99999"
    
    print_request("GET", url, headers=headers)
    
    response = requests.get(url, headers=headers)
    
    print_response(response)
    
    if response.status_code == 404:
        print_success("Correctly returned 404 for non-existent user")
    else:
        print_error("Should return 404 for non-existent user")


def test_filter_users(admin_token):
    """Test filtering users by role and status"""
    print_section("TEST: FILTER USERS")
    
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }
    
    # Test 1: Filter by role
    print_info("Test 1: Filter by role=Author")
    url = f"{ADMIN_ENDPOINT}/users?role=Author"
    print_request("GET", url, headers=headers)
    response = requests.get(url, headers=headers)
    print_response(response)
    
    # Test 2: Filter by status
    print_info("Test 2: Filter by status=Active")
    url = f"{ADMIN_ENDPOINT}/users?status=Active"
    print_request("GET", url, headers=headers)
    response = requests.get(url, headers=headers)
    print_response(response)


def main():
    """Run all tests"""
    print(f"\n{Colors.BLUE}")
    print("╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "IJFINK BACKEND - ADMIN API TEST SUITE".center(78) + "║")
    print("║" + " "*78 + "║")
    print("║" + "Testing User Activation/Deactivation with JWT Authentication".center(78) + "║")
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
    
    print_section("WORKFLOW 1: REGISTER → LOGIN → DEACTIVATE → VERIFY BLOCKED")
    
    # Step 2: Register a new test user
    registered_user = register_user(TEST_USER_REGISTRATION, admin_token)
    if not registered_user:
        print_error("Cannot proceed without registered user")
        return
    
    test_user_id = registered_user["user_id"]
    test_user_email = TEST_USER_REGISTRATION["email"]
    test_user_password = TEST_USER_REGISTRATION["password"]
    
    # Step 3: Login as the newly registered user
    test_credentials = {
        "email": test_user_email,
        "password": test_user_password,
        "role": "Author"
    }
    
    test_user_token, test_user_data = login(test_credentials)
    if not test_user_token:
        print_error("Cannot proceed - registered user cannot login")
        return
    
    # Step 4: Get user details before deactivation
    print_section("USER DETAILS BEFORE DEACTIVATION")
    user_before = get_user_details(admin_token, test_user_id)
    
    # Step 5: Deactivate the user
    print_section("DEACTIVATING TEST USER")
    toggle_user_status(admin_token, test_user_id, "Inactive")
    
    # Step 6: Verify deactivation
    print_section("VERIFYING DEACTIVATION")
    user_after = get_user_details(admin_token, test_user_id)
    if user_after and user_after["status"] == "Inactive":
        print_success("Deactivation verified - User status is now Inactive")
    else:
        print_error("Deactivation verification failed")
    
    # Step 7: Try to login with deactivated user - SHOULD FAIL
    test_login_with_inactive_user({
        "email": test_user_email,
        "password": test_user_password
    })
    
    # Step 8: Reactivate the user
    print_section("REACTIVATING TEST USER")
    toggle_user_status(admin_token, test_user_id, "Active")
    
    # Step 9: Verify reactivation
    user_reactivated = get_user_details(admin_token, test_user_id)
    if user_reactivated and user_reactivated["status"] == "Active":
        print_success("Reactivation verified - User status is now Active")
    else:
        print_error("Reactivation verification failed")
    
    # Step 10: Try to login again with reactivated user - SHOULD SUCCEED
    print_section("LOGIN WITH REACTIVATED USER")
    reactivated_token, reactivated_user = login({
        "email": test_user_email,
        "password": test_user_password,
        "role": "Author"
    })
    if reactivated_token:
        print_success("Reactivated user can login again")
    else:
        print_error("Reactivated user cannot login - something is wrong")
    
    print_section("WORKFLOW 2: SECURITY & ACCESS CONTROL TESTS")
    
    # Step 11: Security tests
    test_unauthorized_access(test_user_id)
    test_invalid_token()
    test_invalid_status(admin_token, test_user_id)
    test_nonexistent_user(admin_token)
    
    # Step 12: Test filtering
    test_filter_users(admin_token)
    
    # Summary
    print_section("TEST SUMMARY")
    print_success("All tests completed!")
    print_info(f"Testing finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


if __name__ == "__main__":
    main()
