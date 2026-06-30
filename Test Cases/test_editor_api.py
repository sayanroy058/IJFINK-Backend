#!/usr/bin/env python3
"""
Editor API Testing Script

Verifies the editor workflow end-to-end:
- dashboard
- assigned articles
- article detail and files
- review submission for Accepted / Minor Revision / Major Revision / Rejected
- review update
- review history
- revision requests
- notifications
- authorization failures
"""

import json
import os
import random
import string
import sys
import time
import uuid
from datetime import datetime

import requests

from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import get_db_connection
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")
AUTH_ENDPOINT = f"{BASE_URL}/api/auth"
SCREENING_ENDPOINT = f"{BASE_URL}/api/screening"
EDITORIAL_ENDPOINT = f"{BASE_URL}/api/editorial"
USER_ENDPOINT = f"{BASE_URL}/api/user"
EDITOR_ENDPOINT = f"{BASE_URL}/api/editor"

ADMIN_CREDENTIALS = {"email": "trimplin@admin.com", "password": "Admin@123", "role": "Admin"}
RUN_ID = f"{int(time.time())}{uuid.uuid4().hex[:8]}"


def rand(n=6):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def unique_email(prefix):
    return f"{prefix}.{RUN_ID}@example.com"


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    END = "\033[0m"


def section(title):
    print(f"\n{Colors.BLUE}{'=' * 80}")
    print(f"{title:^80}")
    print(f"{'=' * 80}{Colors.END}\n")


def ok(msg):
    print(f"{Colors.GREEN}? {msg}{Colors.END}")


def fail(msg):
    print(f"{Colors.RED}? {msg}{Colors.END}")


def info(msg):
    print(f"{Colors.YELLOW}? {msg}{Colors.END}")


def dump(label, response):
    try:
        body = response.json()
    except Exception:
        body = response.text
    print(f"{Colors.CYAN}{label}{Colors.END} -> {response.status_code} {body}")


def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def login(email, password, role):
    response = requests.post(
        f"{AUTH_ENDPOINT}/login",
        json={"email": email, "password": password, "role": role},
        timeout=20,
    )
    dump(f"login:{role}", response)
    if response.status_code == 200 and response.json().get("success"):
        return response.json()["data"]["access_token"], response.json()["data"]["user"]
    return None, None


def register_user(admin_token, payload):
    response = requests.post(
        f"{AUTH_ENDPOINT}/register",
        json=payload,
        headers=auth_headers(admin_token),
        timeout=30,
    )
    dump("register", response)
    if response.status_code in (200, 201) and response.json().get("success"):
        return response.json()["data"]["user"]
    return None


def submit_article(author_token, title):
    data = {
        "title": title,
        "abstract": "Editor test abstract.",
        "keywords": "editor,workflow",
        "article_type": "Research Article",
        "subject_area": "Computer Science",
    }
    files = {
        "main_manuscript": ("manuscript.txt", b"manuscript content", "text/plain"),
    }
    response = requests.post(
        f"{USER_ENDPOINT}/articles",
        data=data,
        files=files,
        headers={"Authorization": f"Bearer {author_token}"},
        timeout=30,
    )
    dump("submit_article", response)
    return response


def approve_article(admin_token, article_id):
    response = requests.post(
        f"{SCREENING_ENDPOINT}/{article_id}/decision",
        json={"decision": "Approved", "remarks": "Approved for editor tests."},
        headers=auth_headers(admin_token),
        timeout=20,
    )
    dump("approve", response)
    return response


def assign_editor(admin_token, article_id, editor_id):
    response = requests.post(
        f"{EDITORIAL_ENDPOINT}/assignments",
        json={"article_id": article_id, "editor_id": editor_id},
        headers=auth_headers(admin_token),
        timeout=20,
    )
    dump("assign", response)
    return response


def db_fetch_one(query, params=()):
    connection = get_db_connection()
    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()
    finally:
        connection.close()


def db_fetch_all(query, params=()):
    connection = get_db_connection()
    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    finally:
        connection.close()


def assert_status(response, expected, label):
    if response.status_code == expected:
        ok(label)
        return True
    fail(f"{label} (expected {expected}, got {response.status_code})")
    return False


def build_env():
    info(f"Base URL: {BASE_URL}")
    info(f"Started: {datetime.now().isoformat(timespec='seconds')}")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            fail("Server health check failed")
            return False
    except Exception as exc:
        fail(f"Server not reachable: {exc}")
        return False
    ok("Server reachable")
    return True


def provision_article(admin_token, author_token, editor_id, title_prefix):
    article_title = f"{title_prefix} {rand()}"
    article_resp = submit_article(author_token, article_title)
    if not assert_status(article_resp, 201, f"Article submitted: {article_title}"):
        return None, None

    article_id = article_resp.json()["data"]["article"]["article_id"]

    if not assert_status(approve_article(admin_token, article_id), 201, f"Article approved: {article_title}"):
        return None, None

    assign_resp = assign_editor(admin_token, article_id, editor_id)
    if not assert_status(assign_resp, 201, f"Editor assigned: {article_title}"):
        return None, None

    assignment_id = assign_resp.json()["data"]["assignment_id"]
    return article_id, assignment_id


def verify_article_state(article_id, expected_article_status=None, expected_assignment_status=None):
    row = db_fetch_one(
        """
        SELECT a.status AS article_status, ea.status AS assignment_status
        FROM articles a
        JOIN editorial_assignment ea ON ea.article_id = a.article_id
        WHERE a.article_id = %s
        ORDER BY ea.assignment_id DESC
        LIMIT 1
        """,
        (article_id,),
    )
    if not row:
        return False, f"Article {article_id} not found in database"
    if expected_article_status and row["article_status"] != expected_article_status:
        return False, f"Expected article status {expected_article_status}, got {row['article_status']}"
    if expected_assignment_status and row["assignment_status"] != expected_assignment_status:
        return False, f"Expected assignment status {expected_assignment_status}, got {row['assignment_status']}"
    return True, row


def submit_review(editor_token, assignment_id, decision, comments):
    response = requests.post(
        f"{EDITOR_ENDPOINT}/review",
        json={"assignment_id": assignment_id, "decision": decision, "comments": comments},
        headers=auth_headers(editor_token),
        timeout=20,
    )
    dump(f"review-{decision.lower().replace(' ', '-')}", response)
    return response


def verify_review_row(assignment_id, decision):
    row = db_fetch_one(
        """
        SELECT editorial_review_id, assignment_id, decision, comments
        FROM editorial_review
        WHERE assignment_id = %s
        ORDER BY editorial_review_id DESC
        LIMIT 1
        """,
        (assignment_id,),
    )
    if not row:
        return False, "No review row found"
    if row["decision"] != decision:
        return False, f"Expected review decision {decision}, got {row['decision']}"
    return True, row


def ensure_editor_notification(editor_user_id, title, message):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO notifications (user_id, article_id, title, message)
                VALUES (%s, NULL, %s, %s)
                """,
                (editor_user_id, title, message),
            )
            notification_id = cursor.lastrowid
        connection.commit()
        return notification_id
    finally:
        connection.close()


def main():
    section("EDITOR API TEST SUITE")
    if not build_env():
        return 1

    admin_token, _ = login(ADMIN_CREDENTIALS["email"], ADMIN_CREDENTIALS["password"], "Admin")
    if not admin_token:
        fail("Cannot continue without admin token")
        return 1

    editor_payload = {
        "first_name": "Editor",
        "last_name": "One",
        "email": unique_email("editor.one"),
        "password": "Editor@123",
        "confirm_password": "Editor@123",
        "role": "Editor",
        "institution": "IJFINK Institute",
    }
    editor_two_payload = {
        "first_name": "Editor",
        "last_name": "Two",
        "email": unique_email("editor.two"),
        "password": "Editor@123",
        "confirm_password": "Editor@123",
        "role": "Editor",
        "institution": "IJFINK Institute",
    }
    author_payload = {
        "first_name": "Author",
        "last_name": "One",
        "email": unique_email("author.one"),
        "password": "Author@123",
        "confirm_password": "Author@123",
        "role": "Author",
        "institution": "IJFINK Institute",
    }

    editor_user = register_user(admin_token, editor_payload)
    editor_two_user = register_user(admin_token, editor_two_payload)
    author_user = register_user(admin_token, author_payload)
    if not editor_user or not editor_two_user or not author_user:
        fail("Failed to provision test users")
        return 1

    editor_token, _ = login(editor_payload["email"], editor_payload["password"], "Editor")
    editor_two_token, _ = login(editor_two_payload["email"], editor_two_payload["password"], "Editor")
    author_token, _ = login(author_payload["email"], author_payload["password"], "Author")
    if not editor_token or not editor_two_token or not author_token:
        fail("Failed to login test users")
        return 1

    editor_id = editor_user["profile_id"]
    editor_two_id = editor_two_user["profile_id"]

    accepted_article_id, accepted_assignment_id = provision_article(admin_token, author_token, editor_id, "Accepted Flow")
    minor_article_id, minor_assignment_id = provision_article(admin_token, author_token, editor_id, "Minor Revision Flow")
    major_article_id, major_assignment_id = provision_article(admin_token, author_token, editor_id, "Major Revision Flow")
    rejected_article_id, rejected_assignment_id = provision_article(admin_token, author_token, editor_id, "Rejected Flow")
    update_article_id, update_assignment_id = provision_article(admin_token, author_token, editor_id, "Update Flow")
    other_editor_article_id, other_editor_assignment_id = provision_article(admin_token, author_token, editor_two_id, "Other Editor Flow")

    if not all([accepted_article_id, minor_article_id, major_article_id, rejected_article_id, update_article_id, other_editor_article_id]):
        fail("Failed to provision the article workflow")
        return 1

    section("EDITOR DASHBOARD")
    resp = requests.get(f"{EDITOR_ENDPOINT}/dashboard", headers=auth_headers(editor_token), timeout=20)
    dump("editor-dashboard", resp)
    if not assert_status(resp, 200, "Editor dashboard available"):
        return 1
    dashboard = resp.json()["data"]
    if dashboard["assigned_articles"] < 5:
        fail(f"Dashboard assigned_articles should be at least 5, got {dashboard['assigned_articles']}")
        return 1
    ok("Dashboard counts returned")

    section("EDITOR ARTICLES")
    resp = requests.get(f"{EDITOR_ENDPOINT}/articles", headers=auth_headers(editor_token), timeout=20)
    dump("editor-articles", resp)
    if not assert_status(resp, 200, "Editor articles listed"):
        return 1
    rows = resp.json()["data"]["articles"]
    assigned_ids = {row["article_id"] for row in rows}
    for article_id in [accepted_article_id, minor_article_id, major_article_id, rejected_article_id, update_article_id]:
        if article_id not in assigned_ids:
            fail(f"Assigned article missing from editor list: {article_id}")
            return 1
    ok("Assigned articles visible to editor")

    resp = requests.get(
        f"{EDITOR_ENDPOINT}/articles?page=1&per_page=2&sort_by=ea.assigned_at&sort_order=DESC",
        headers=auth_headers(editor_token),
        timeout=20,
    )
    dump("editor-articles-paginated", resp)
    if not assert_status(resp, 200, "Pagination works"):
        return 1
    if resp.json()["data"]["pagination"]["per_page"] != 2:
        fail("Pagination per_page should be 2")
        return 1

    resp = requests.get(
        f"{EDITOR_ENDPOINT}/articles?search=Accepted%20Flow",
        headers=auth_headers(editor_token),
        timeout=20,
    )
    dump("editor-search", resp)
    if not assert_status(resp, 200, "Editor search works"):
        return 1
    if not resp.json()["data"]["articles"]:
        fail("Search should return at least one article")
        return 1

    resp = requests.get(
        f"{EDITOR_ENDPOINT}/articles?status=Editorial%20Review",
        headers=auth_headers(editor_token),
        timeout=20,
    )
    dump("editor-filter-status", resp)
    assert_status(resp, 200, "Status filter works")

    section("EDITOR ARTICLE DETAIL")
    resp = requests.get(f"{EDITOR_ENDPOINT}/articles/{accepted_article_id}", headers=auth_headers(editor_token), timeout=20)
    dump("editor-article", resp)
    if not assert_status(resp, 200, "Editor can view own article"):
        return 1
    article_detail = resp.json()["data"]
    if article_detail["current_status"] != "Editorial Review":
        fail(f"Article must be in 'Editorial Review' after assignment, got '{article_detail['current_status']}'")
        return 1

    resp = requests.get(f"{EDITOR_ENDPOINT}/articles/{accepted_article_id}/files", headers=auth_headers(editor_token), timeout=20)
    dump("editor-files", resp)
    assert_status(resp, 200, "Editor can view files")

    section("EDITOR REVIEW - ACCEPTED")
    resp = submit_review(editor_token, accepted_assignment_id, "Accepted", "Accepted after review.")
    if not assert_status(resp, 201, "Accepted review submitted"):
        return 1
    ok_state, state = verify_article_state(accepted_article_id, expected_article_status="Accepted", expected_assignment_status="Completed")
    if not ok_state:
        fail(state)
        return 1
    ok("Accepted article state verified in database")
    ok_review, review_row = verify_review_row(accepted_assignment_id, "Accepted")
    if not ok_review:
        fail(review_row)
        return 1
    ok("Accepted review row verified")
    author_notification = db_fetch_one(
        """
        SELECT n.notification_id, n.user_id, n.title, n.message
        FROM notifications n
        JOIN articles a ON a.article_id = n.article_id
        JOIN authors au ON au.author_id = a.author_id
        WHERE a.article_id = %s AND n.user_id = au.user_id
        ORDER BY n.notification_id DESC
        LIMIT 1
        """,
        (accepted_article_id,),
    )
    if not author_notification:
        fail("Author notification missing for accepted article")
        return 1
    ok("Author notification created for accepted article")
    publication_team_exists = db_fetch_one("SELECT 1 AS ok FROM publication_team LIMIT 1")
    if publication_team_exists:
        pub_notification = db_fetch_one(
            """
            SELECT n.notification_id
            FROM notifications n
            JOIN users u ON u.user_id = n.user_id
            WHERE n.article_id = %s AND u.role = 'Publication Team'
            ORDER BY n.notification_id DESC
            LIMIT 1
            """,
            (accepted_article_id,),
        )
        if not pub_notification:
            fail("Publication team notification missing for accepted article")
            return 1
        ok("Publication team notification created")
    else:
        info("No publication team row found; skipped publication notification assertion")

    section("EDITOR REVIEW - MINOR REVISION")
    resp = submit_review(editor_token, minor_assignment_id, "Minor Revision", "Please fix minor issues.")
    if not assert_status(resp, 201, "Minor revision submitted"):
        return 1
    ok_state, state = verify_article_state(minor_article_id, expected_article_status="Revision Requested", expected_assignment_status="Active")
    if not ok_state:
        fail(state)
        return 1
    ok("Minor revision state verified in database")

    section("EDITOR REVIEW - MAJOR REVISION")
    resp = submit_review(editor_token, major_assignment_id, "Major Revision", "Please fix major issues.")
    if not assert_status(resp, 201, "Major revision submitted"):
        return 1
    ok_state, state = verify_article_state(major_article_id, expected_article_status="Revision Requested", expected_assignment_status="Active")
    if not ok_state:
        fail(state)
        return 1
    ok("Major revision state verified in database")

    section("EDITOR REVIEW - REJECTED")
    resp = submit_review(editor_token, rejected_assignment_id, "Rejected", "Rejected after review.")
    if not assert_status(resp, 201, "Rejected review submitted"):
        return 1
    ok_state, state = verify_article_state(rejected_article_id, expected_article_status="Rejected", expected_assignment_status="Completed")
    if not ok_state:
        fail(state)
        return 1
    ok("Rejected article state verified in database")

    section("EDITOR REVIEW - UPDATE REVIEW")
    resp = submit_review(editor_token, update_assignment_id, "Minor Revision", "Initial comments for update test.")
    if not assert_status(resp, 201, "Initial review for update test submitted"):
        return 1
    update_resp = requests.put(
        f"{EDITOR_ENDPOINT}/review/{resp.json()['data']['review_id']}",
        json={"decision": "Major Revision", "comments": "Updated comments after re-check."},
        headers=auth_headers(editor_token),
        timeout=20,
    )
    dump("update-review", update_resp)
    if not assert_status(update_resp, 200, "Review update works"):
        return 1
    updated_row = db_fetch_one(
        """
        SELECT decision, comments
        FROM editorial_review
        WHERE assignment_id = %s
        ORDER BY editorial_review_id DESC
        LIMIT 1
        """,
        (update_assignment_id,),
    )
    if not updated_row or updated_row["decision"] != "Major Revision":
        fail("Updated review decision not saved in database")
        return 1
    ok("Updated review verified in database")

    section("REVIEW HISTORY / REVISION REQUESTS")
    resp = requests.get(f"{EDITOR_ENDPOINT}/reviews", headers=auth_headers(editor_token), timeout=20)
    dump("editor-reviews", resp)
    if not assert_status(resp, 200, "Review history available"):
        return 1
    if len(resp.json()["data"]["reviews"]) < 5:
        fail("Expected at least 5 reviews in history")
        return 1
    ok("Review history contains editor reviews")

    resp = requests.get(f"{EDITOR_ENDPOINT}/revision-requests", headers=auth_headers(editor_token), timeout=20)
    dump("editor-revision-requests", resp)
    if not assert_status(resp, 200, "Revision requests available"):
        return 1
    revision_articles = {row["article_id"] for row in resp.json()["data"]["articles"]}
    if minor_article_id not in revision_articles or major_article_id not in revision_articles:
        fail("Revision requests did not return expected articles")
        return 1
    ok("Revision request list verified")

    section("NOTIFICATIONS")
    editor_notifications_resp = requests.get(f"{EDITOR_ENDPOINT}/notifications", headers=auth_headers(editor_token), timeout=20)
    dump("editor-notifications", editor_notifications_resp)
    if not assert_status(editor_notifications_resp, 200, "Notifications endpoint available"):
        return 1

    editor_notification_id = ensure_editor_notification(
        editor_user["user_id"],
        "Editor Test Notification",
        "This notification was created by the test to verify mark-as-read.",
    )
    if not editor_notification_id:
        fail("Failed to create editor notification for read test")
        return 1

    read_resp = requests.put(
        f"{EDITOR_ENDPOINT}/notifications/{editor_notification_id}/read",
        headers=auth_headers(editor_token),
        timeout=20,
    )
    dump("editor-notification-read", read_resp)
    if not assert_status(read_resp, 200, "Mark notification as read works"):
        return 1
    read_row = db_fetch_one(
        "SELECT is_read FROM notifications WHERE notification_id = %s",
        (editor_notification_id,),
    )
    if not read_row or int(read_row["is_read"]) != 1:
        fail("Notification read state was not saved in database")
        return 1
    ok("Notification read state verified in database")

    section("NEGATIVE ACCESS CONTROL")
    resp = requests.get(f"{EDITOR_ENDPOINT}/dashboard", headers=auth_headers(admin_token), timeout=20)
    dump("admin-view-editor-endpoint", resp)
    assert_status(resp, 403, "Admin blocked from editor endpoint")

    resp = requests.get(f"{EDITOR_ENDPOINT}/dashboard", timeout=20)
    dump("no-token", resp)
    assert_status(resp, 401, "Editor endpoint requires auth")

    resp = requests.get(f"{EDITOR_ENDPOINT}/articles/{other_editor_article_id}", headers=auth_headers(editor_token), timeout=20)
    dump("other-editor-article", resp)
    assert_status(resp, 403, "Editor blocked from another editor's article")

    resp = submit_review(editor_token, 999999, "Accepted", "Invalid assignment test.")
    dump("invalid-assignment", resp)
    assert_status(resp, 404, "Invalid assignment rejected")

    resp = submit_review(editor_token, accepted_assignment_id, "Not A Decision", "Invalid decision test.")
    dump("invalid-decision", resp)
    assert_status(resp, 400, "Invalid decision rejected")

    section("SUMMARY")
    ok("Editor API tests completed")
    info(f"Finished: {datetime.now().isoformat(timespec='seconds')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())



