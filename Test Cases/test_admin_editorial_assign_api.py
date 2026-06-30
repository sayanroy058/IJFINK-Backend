#!/usr/bin/env python3
"""
Editorial Assignment API Testing Script

Covers:
  - Admin: list assignable articles, list assignable editors, assign editor
  - Editor: list own assignments, view assignment details
  - Chief editor: see all assignments and any assignment details
  - Negative cases: unauthorized roles, foreign editors, invalid state,
    invalid token, assignment not found, double assignment

Usage:
    python "Test Cases/test_admin_editorial_assign_api.py"
"""

import json
import random
import string
import sys
from datetime import datetime

import requests


BASE_URL = "http://localhost:5000"
AUTH_ENDPOINT = f"{BASE_URL}/api/auth"
SCREENING_ENDPOINT = f"{BASE_URL}/api/screening"
EDITORIAL_ENDPOINT = f"{BASE_URL}/api/editorial"
USER_ENDPOINT = f"{BASE_URL}/api/user"

ADMIN_CREDENTIALS = {
    "email": "trimplin@admin.com",
    "password": "Admin@123",
    "role": "Admin",
}


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    END = "\033[0m"


PASSED = 0
FAILED = 0


def _print_section(title):
    print(f"\n{Colors.BLUE}{'='*80}\n{title:^80}\n{'='*80}{Colors.END}")


def _ok(msg):
    global PASSED
    PASSED += 1
    print(f"{Colors.GREEN}[PASS]{Colors.END} {msg}")


def _fail(msg):
    global FAILED
    FAILED += 1
    print(f"{Colors.RED}[FAIL]{Colors.END} {msg}")


def _info(msg):
    print(f"{Colors.YELLOW}[INFO]{Colors.END} {msg}")


def _dump(label, response):
    try:
        body = response.json()
    except Exception:
        body = response.text
    print(f"{Colors.CYAN}{label}{Colors.END} -> {response.status_code} {body}")


def _rand(n=6):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def _login(email, password, role):
    response = requests.post(
        f"{AUTH_ENDPOINT}/login",
        json={"email": email, "password": password, "role": role},
        timeout=10,
    )
    if response.status_code != 200:
        _fail(f"Login failed for {email} ({role}): {response.status_code} {response.text}")
        return None
    return response.json()["data"]["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _register_editor(admin_token, suffix, is_chief_editor=False):
    payload = {
        "first_name": f"Edit{suffix}",
        "last_name": "Tester",
        "email": f"editor_{suffix}_{_rand()}@test.local",
        "password": "Editor@123",
        "confirm_password": "Editor@123",
        "role": "Editor",
        "institution": "Test University",
        "is_chief_editor": is_chief_editor,
    }
    response = requests.post(
        f"{AUTH_ENDPOINT}/register",
        json=payload,
        headers=_auth(admin_token),
        timeout=10,
    )
    if response.status_code != 201:
        return None, payload
    return response.json(), payload


def _register_author(suffix):
    payload = {
        "first_name": f"Auth{suffix}",
        "last_name": "Tester",
        "email": f"author_{suffix}_{_rand()}@test.local",
        "password": "Author@123",
        "confirm_password": "Author@123",
        "institution": "Test University",
    }
    response = requests.post(
        f"{AUTH_ENDPOINT}/register",
        json=payload,
        timeout=10,
    )
    if response.status_code != 201:
        return None, payload
    return response.json(), payload


def _submit_article(author_token, title):
    data = {
        "title": title,
        "abstract": "Editorial flow test abstract.",
        "keywords": "editorial,test",
        "article_type": "Research",
        "subject_area": "Computer Science",
    }
    headers = {"Authorization": f"Bearer {author_token}"}
    files = {
        "main_manuscript": (
            "manuscript.txt",
            b"Dummy manuscript content for editorial flow tests.",
            "text/plain",
        ),
    }
    response = requests.post(
        f"{USER_ENDPOINT}/articles",
        data=data,
        files=files,
        headers=headers,
        timeout=30,
    )
    return response


def _approve_article(admin_token, article_id):
    response = requests.post(
        f"{SCREENING_ENDPOINT}/{article_id}/decision",
        json={"decision": "Approved", "remarks": "OK for editor flow."},
        headers=_auth(admin_token),
        timeout=10,
    )
    return response


def _ensure_chief_editor(admin_token):
    """Return (chief_token, chief_editor_id_in_users) or (None, None) if already exists."""
    result, payload = _register_editor(admin_token, "chief", is_chief_editor=True)
    if result is None:
        _info("Chief editor already exists or could not be created — skipping chief-editor login flow.")
        return None
    token = _login(payload["email"], payload["password"], "Editor")
    return token


def _server_running():
    try:
        return requests.get(f"{BASE_URL}/health", timeout=5).status_code == 200
    except requests.exceptions.RequestException:
        return False


def run():
    _print_section("EDITORIAL ASSIGNMENT API TEST SUITE")
    _info(f"Base URL: {BASE_URL}")
    _info(f"Started: {datetime.now().isoformat(timespec='seconds')}")

    if not _server_running():
        _fail(f"Server not reachable at {BASE_URL}. Start it first.")
        return 1

    # 1. Admin login
    _print_section("Login: Admin")
    admin_token = _login(ADMIN_CREDENTIALS["email"], ADMIN_CREDENTIALS["password"], "Admin")
    if not admin_token:
        return 1
    _ok("Admin login")

    # 2. Provision two regular editors + one chief editor
    _print_section("Provisioning editors")
    suffix_a = _rand(4)
    suffix_b = _rand(4)
    editor_a_result, editor_a_payload = _register_editor(admin_token, f"a{suffix_a}")
    editor_b_result, editor_b_payload = _register_editor(admin_token, f"b{suffix_b}")
    if not editor_a_result or not editor_b_result:
        _fail("Could not create test editors")
        return 1
    editor_a_id = editor_a_result["data"]["user"]["profile_id"]
    editor_b_id = editor_b_result["data"]["user"]["profile_id"]
    _ok(f"Editor A created (editor_id={editor_a_id})")
    _ok(f"Editor B created (editor_id={editor_b_id})")

    chief_token = _ensure_chief_editor(admin_token)
    if chief_token:
        _ok("Chief editor created and logged in")
    else:
        _info("Continuing without a freshly-created chief editor")

    editor_a_token = _login(editor_a_payload["email"], editor_a_payload["password"], "Editor")
    editor_b_token = _login(editor_b_payload["email"], editor_b_payload["password"], "Editor")
    if not editor_a_token or not editor_b_token:
        _fail("Editor login failed")
        return 1
    _ok("Editor A logged in")
    _ok("Editor B logged in")

    # 3. Provision an author and submit an article
    _print_section("Provisioning author and submitting article")
    author_result, author_payload = _register_author(_rand(4))
    if not author_result:
        _fail("Could not create test author")
        return 1
    author_token = _login(author_payload["email"], author_payload["password"], "Author")
    if not author_token:
        return 1
    article_response = _submit_article(author_token, f"Editorial Flow Test {_rand()}")
    if article_response.status_code != 201:
        _dump("submit_article", article_response)
        _fail("Article submission failed; cannot continue")
        return 1
    article_id = article_response.json()["data"]["article"]["article_id"]
    _ok(f"Article submitted (article_id={article_id})")

    # 4. Try to assign an editor BEFORE admin approval -> 400/403
    _print_section("Negative: assign before admin approval")
    response = requests.post(
        f"{EDITORIAL_ENDPOINT}/assignments",
        json={"article_id": article_id, "editor_id": editor_a_id},
        headers=_auth(admin_token),
        timeout=10,
    )
    _dump("assign-before-approval", response)
    if response.status_code in (400, 403):
        _ok("Pre-approval assignment correctly rejected")
    else:
        _fail("Pre-approval assignment should be rejected")

    # 5. Admin approves the article
    _print_section("Admin approves article")
    approval = _approve_article(admin_token, article_id)
    _dump("approve", approval)
    if approval.status_code == 201:
        _ok("Article approved by admin")
    else:
        _fail("Admin approval failed")
        return 1

    # 6. GET /assignable-articles should now include this article
    _print_section("GET /api/editorial/assignable-articles (Admin)")
    response = requests.get(
        f"{EDITORIAL_ENDPOINT}/assignable-articles",
        headers=_auth(admin_token),
        timeout=10,
    )
    _dump("assignable-articles", response)
    if response.status_code == 200:
        ids = [a["article_id"] for a in response.json()["data"]["articles"]]
        if article_id in ids:
            _ok("New article is in the assignable list")
        else:
            _fail("New article missing from assignable list")
    else:
        _fail("assignable-articles request failed")

    # 7. Non-admin (editor) should be blocked
    _print_section("Negative: editor calls admin-only endpoints")
    response = requests.get(
        f"{EDITORIAL_ENDPOINT}/assignable-articles",
        headers=_auth(editor_a_token),
        timeout=10,
    )
    _dump("editor->assignable-articles", response)
    if response.status_code == 403:
        _ok("Editor correctly forbidden from admin-only endpoint")
    else:
        _fail("Editor should be 403 on admin-only endpoint")

    # 8. Missing/invalid token
    _print_section("Negative: missing/invalid token")
    response = requests.get(f"{EDITORIAL_ENDPOINT}/assignable-articles", timeout=10)
    _dump("no-token", response)
    if response.status_code == 401:
        _ok("No token -> 401")
    else:
        _fail("No token should be 401")

    response = requests.get(
        f"{EDITORIAL_ENDPOINT}/assignable-articles",
        headers={"Authorization": "Bearer not.a.real.token"},
        timeout=10,
    )
    _dump("invalid-token", response)
    if response.status_code == 401:
        _ok("Invalid token -> 401")
    else:
        _fail("Invalid token should be 401")

    # 9. GET /assignable-editors
    _print_section("GET /api/editorial/assignable-editors (Admin)")
    response = requests.get(
        f"{EDITORIAL_ENDPOINT}/assignable-editors",
        headers=_auth(admin_token),
        timeout=10,
    )
    _dump("assignable-editors", response)
    if response.status_code == 200:
        editor_ids = [e["editor_id"] for e in response.json()["data"]["editors"]]
        if editor_a_id in editor_ids and editor_b_id in editor_ids:
            _ok("Both test editors present in assignable-editors")
        else:
            _fail("Expected editors missing from list")
        chief_present = any(e["is_chief_editor"] for e in response.json()["data"]["editors"])
        if not chief_present:
            _ok("Chief editor excluded from assignable list")
        else:
            _fail("Chief editor should be excluded")
    else:
        _fail("assignable-editors request failed")

    # 10. Assign Editor A to the article
    _print_section("POST /api/editorial/assignments (assign Editor A)")
    response = requests.post(
        f"{EDITORIAL_ENDPOINT}/assignments",
        json={"article_id": article_id, "editor_id": editor_a_id},
        headers=_auth(admin_token),
        timeout=10,
    )
    _dump("assign", response)
    if response.status_code == 201:
        assignment_id = response.json()["data"]["assignment_id"]
        _ok(f"Editor A assigned (assignment_id={assignment_id})")
    else:
        _fail("Editor assignment failed")
        return 1

    # 11. Duplicate active assignment -> 409
    _print_section("Negative: duplicate active assignment")
    response = requests.post(
        f"{EDITORIAL_ENDPOINT}/assignments",
        json={"article_id": article_id, "editor_id": editor_b_id},
        headers=_auth(admin_token),
        timeout=10,
    )
    _dump("duplicate-assign", response)
    if response.status_code == 409:
        _ok("Duplicate assignment correctly returned 409")
    else:
        _fail("Duplicate assignment should be 409")

    # 12. Editor A sees the assignment
    _print_section("GET /api/editorial/assignments (Editor A — assignee)")
    response = requests.get(
        f"{EDITORIAL_ENDPOINT}/assignments",
        headers=_auth(editor_a_token),
        timeout=10,
    )
    _dump("editor-a-list", response)
    if response.status_code == 200:
        ids = [a["assignment_id"] for a in response.json()["data"]["assignments"]]
        if assignment_id in ids:
            _ok("Editor A can see their assignment in the list")
        else:
            _fail("Editor A cannot see their own assignment")
    else:
        _fail("Editor A list request failed")

    # 13. Editor B does NOT see the assignment
    _print_section("GET /api/editorial/assignments (Editor B — not assignee)")
    response = requests.get(
        f"{EDITORIAL_ENDPOINT}/assignments",
        headers=_auth(editor_b_token),
        timeout=10,
    )
    _dump("editor-b-list", response)
    if response.status_code == 200:
        ids = [a["assignment_id"] for a in response.json()["data"]["assignments"]]
        if assignment_id not in ids:
            _ok("Editor B correctly cannot see Editor A's assignment")
        else:
            _fail("Editor B should not see Editor A's assignment")
    else:
        _fail("Editor B list request failed")

    # 14. Editor A details view
    _print_section("GET /api/editorial/assignments/<id> (Editor A — assignee)")
    response = requests.get(
        f"{EDITORIAL_ENDPOINT}/assignments/{assignment_id}",
        headers=_auth(editor_a_token),
        timeout=10,
    )
    _dump("editor-a-detail", response)
    if response.status_code == 200:
        _ok("Editor A can view assignment details")
    else:
        _fail("Editor A should be able to view details")

    # 15. Editor B details view -> 403
    _print_section("GET /api/editorial/assignments/<id> (Editor B — forbidden)")
    response = requests.get(
        f"{EDITORIAL_ENDPOINT}/assignments/{assignment_id}",
        headers=_auth(editor_b_token),
        timeout=10,
    )
    _dump("editor-b-detail", response)
    if response.status_code == 403:
        _ok("Editor B correctly forbidden from details view")
    else:
        _fail("Editor B should get 403")

    # 16. Chief editor visibility (if available)
    if chief_token:
        _print_section("GET /api/editorial/assignments (Chief Editor)")
        response = requests.get(
            f"{EDITORIAL_ENDPOINT}/assignments",
            headers=_auth(chief_token),
            timeout=10,
        )
        _dump("chief-list", response)
        if response.status_code == 200:
            ids = [a["assignment_id"] for a in response.json()["data"]["assignments"]]
            if assignment_id in ids:
                _ok("Chief editor sees the assignment in their list")
            else:
                _fail("Chief editor should see all assignments")
        else:
            _fail("Chief editor list request failed")

        _print_section("GET /api/editorial/assignments/<id> (Chief Editor)")
        response = requests.get(
            f"{EDITORIAL_ENDPOINT}/assignments/{assignment_id}",
            headers=_auth(chief_token),
            timeout=10,
        )
        _dump("chief-detail", response)
        if response.status_code == 200:
            _ok("Chief editor can view any assignment details")
        else:
            _fail("Chief editor should be able to view details")
    else:
        _info("Skipping chief-editor checks (no chief token)")

    # 17. Author cannot use editorial endpoints
    _print_section("Negative: author calls editorial endpoints")
    response = requests.get(
        f"{EDITORIAL_ENDPOINT}/assignments",
        headers=_auth(author_token),
        timeout=10,
    )
    _dump("author-list", response)
    if response.status_code == 403:
        _ok("Author correctly forbidden from editor endpoints")
    else:
        _fail("Author should be 403 on editor endpoints")

    # 18. Assignment not found
    _print_section("Negative: assignment not found")
    response = requests.get(
        f"{EDITORIAL_ENDPOINT}/assignments/9999999",
        headers=_auth(editor_a_token),
        timeout=10,
    )
    _dump("missing-assignment", response)
    if response.status_code == 404:
        _ok("Unknown assignment id -> 404")
    else:
        _fail("Unknown assignment id should be 404")

    # 19. Invalid payload on assignment
    _print_section("Negative: invalid assign payload")
    response = requests.post(
        f"{EDITORIAL_ENDPOINT}/assignments",
        json={"article_id": "abc", "editor_id": None},
        headers=_auth(admin_token),
        timeout=10,
    )
    _dump("bad-payload", response)
    if response.status_code == 400:
        _ok("Invalid assign payload -> 400")
    else:
        _fail("Invalid payload should be 400")

    # Summary
    _print_section("SUMMARY")
    print(f"{Colors.GREEN}Passed:{Colors.END} {PASSED}")
    print(f"{Colors.RED}Failed:{Colors.END} {FAILED}")
    print(f"Finished: {datetime.now().isoformat(timespec='seconds')}")
    return 0 if FAILED == 0 else 2


if __name__ == "__main__":
    sys.exit(run())
