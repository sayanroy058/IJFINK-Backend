#!/usr/bin/env python3
"""
Publication API Testing Script

Covers:
  - Publication Team account creation/login
  - Accepted article listing
  - Return-to-editor rule:
      publisher can return the paper only to the latest assigned editor
  - Optional publish happy path if a second accepted article is available

Usage:
    python "Test Cases/test_publication_api.py"

Optional:
    $env:RETURN_TEST_ARTICLE_ID="123"
    $env:PUBLISH_TEST_ARTICLE_ID="124"
"""

import io
import json
import os
import random
import string
import sys
import time
import uuid
from datetime import date, datetime
from urllib import error as urllib_error
from urllib import request as urllib_request

from mysql.connector import Error as MySQLError

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db_connection


BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")
AUTH_ENDPOINT = f"{BASE_URL}/api/auth"
PUBLICATION_ENDPOINT = f"{BASE_URL}/api/publication"

ADMIN_CREDENTIALS = {
    "email": "trimplin@admin.com",
    "password": "Admin@123",
    "role": "Admin",
}

RUN_ID = f"{int(time.time())}{uuid.uuid4().hex[:8]}"
ACCEPTED_ARTICLE_ID = os.getenv("ACCEPTED_ARTICLE_ID")
RETURN_TEST_ARTICLE_ID = os.getenv("RETURN_TEST_ARTICLE_ID") or ACCEPTED_ARTICLE_ID
PUBLISH_TEST_ARTICLE_ID = os.getenv("PUBLISH_TEST_ARTICLE_ID")


def _rand(n=6):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def _print_section(title):
    print(f"\n{'=' * 80}\n{title:^80}\n{'=' * 80}")


def _request(method, url, headers=None, json_body=None, form_fields=None, multipart_files=None, timeout=20):
    request_headers = dict(headers or {})
    body = None

    if json_body is not None:
        body = json.dumps(json_body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    elif multipart_files is not None:
        boundary, body = _build_multipart_body(form_fields or {}, multipart_files)
        request_headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"

    req = urllib_request.Request(url, data=body, headers=request_headers, method=method)
    try:
        with urllib_request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return _response(response.status, raw)
    except urllib_error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        return _response(exc.code, raw)


def _response(status_code, raw):
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = None
    return {"status_code": status_code, "json": parsed, "text": raw}


def _build_multipart_body(fields, files):
    boundary = f"----IJFINKBoundary{uuid.uuid4().hex}"
    buffer = io.BytesIO()

    for field_name, field_value in fields.items():
        buffer.write(f"--{boundary}\r\n".encode("utf-8"))
        buffer.write(f'Content-Disposition: form-data; name="{field_name}"\r\n\r\n'.encode("utf-8"))
        buffer.write(str(field_value).encode("utf-8"))
        buffer.write(b"\r\n")

    for field_name, file_info in files:
        filename, file_bytes, content_type = file_info
        buffer.write(f"--{boundary}\r\n".encode("utf-8"))
        buffer.write(
            (
                f'Content-Disposition: form-data; name="{field_name}"; '
                f'filename="{filename}"\r\n'
            ).encode("utf-8")
        )
        buffer.write(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        buffer.write(file_bytes)
        buffer.write(b"\r\n")

    buffer.write(f"--{boundary}--\r\n".encode("utf-8"))
    return boundary, buffer.getvalue()


def _dump(label, response):
    print(f"\n{label}: {response['status_code']}")
    try:
        print(json.dumps(response["json"], indent=2, default=str))
    except Exception:
        print(response["text"])
    message = ((response.get("json") or {}).get("message") or "")
    if "Data truncated for column 'status'" in message:
        print("\nDatabase schema is missing the new publication status enum values.")
        print("Run SQL_Scripts_&_ERD/migration_publication_api.sql once, then rerun this test.")


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _fetch_accepted_articles(limit=5):
    try:
        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT article_id, title
                    FROM articles
                    WHERE status = 'Accepted'
                    ORDER BY updated_at ASC, article_id ASC
                    LIMIT %s
                    """,
                    (limit,),
                )
                return cursor.fetchall()
    except MySQLError as exc:
        print(f"Could not auto-detect accepted articles: {exc}")
        return []


def _resolve_article_ids():
    if RETURN_TEST_ARTICLE_ID:
        return_article_id = int(RETURN_TEST_ARTICLE_ID)
    else:
        accepted_articles = _fetch_accepted_articles(limit=5)
        if not accepted_articles:
            print("No article in 'Accepted' status was found.")
            print("Create or update one first, then rerun with:")
            print('$env:RETURN_TEST_ARTICLE_ID="123"')
            print('python "Test Cases/test_publication_api.py"')
            return None, None
        return_article_id = int(accepted_articles[0]["article_id"])
        print(
            "Using accepted article "
            f"{accepted_articles[0]['article_id']} ({accepted_articles[0]['title']}) "
            "for return-to-editor validation."
        )

    if PUBLISH_TEST_ARTICLE_ID:
        publish_article_id = int(PUBLISH_TEST_ARTICLE_ID)
    else:
        publish_article_id = None
        for article in _fetch_accepted_articles(limit=10):
            if int(article["article_id"]) != return_article_id:
                publish_article_id = int(article["article_id"])
                print(
                    "Using accepted article "
                    f"{article['article_id']} ({article['title']}) "
                    "for publish flow."
                )
                break

    if publish_article_id is None:
        print("No second accepted article found; publish happy path will be skipped.")

    return return_article_id, publish_article_id


def _fetch_latest_assignment(article_id):
    with get_db_connection() as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                """
                SELECT
                    ea.assignment_id,
                    ea.editor_id,
                    ea.status AS assignment_status,
                    e.user_id AS editor_user_id,
                    CONCAT(e.first_name, ' ', e.last_name) AS editor_name
                FROM editorial_assignment ea
                JOIN editors e ON e.editor_id = ea.editor_id
                WHERE ea.article_id = %s
                ORDER BY ea.assigned_at DESC, ea.assignment_id DESC
                LIMIT 1
                """,
                (article_id,),
            )
            return cursor.fetchone()


def _fetch_article_status(article_id):
    with get_db_connection() as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                "SELECT status FROM articles WHERE article_id = %s",
                (article_id,),
            )
            article = cursor.fetchone()
            return article["status"] if article else None


def _fetch_notification(user_id, article_id, title):
    with get_db_connection() as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                """
                SELECT notification_id, user_id, article_id, title, message, created_at
                FROM notifications
                WHERE user_id = %s
                  AND article_id = %s
                  AND title = %s
                ORDER BY created_at DESC, notification_id DESC
                LIMIT 1
                """,
                (user_id, article_id, title),
            )
            return cursor.fetchone()


def _register_editor(admin_token, label):
    payload = {
        "first_name": "Wrong",
        "last_name": f"Editor{label}",
        "email": f"wrong_editor_{RUN_ID}_{_rand()}@test.local",
        "password": "Editor@123",
        "confirm_password": "Editor@123",
        "role": "Editor",
        "institution": "Publication Test Institute",
    }
    response = _request(
        "POST",
        f"{AUTH_ENDPOINT}/register",
        headers=_auth(admin_token),
        json_body=payload,
    )
    _dump("register wrong editor", response)
    if response["status_code"] != 201:
        return None
    return response["json"]["data"]["user"]["profile_id"]


def _assert_response(condition, success_message, failure_message):
    if condition:
        print(f"[PASS] {success_message}")
        return True
    print(f"[FAIL] {failure_message}")
    return False


def _run_return_to_editor_test(article_id, headers, wrong_editor_id):
    _print_section("Return-To-Original-Editor Rule")

    original_assignment = _fetch_latest_assignment(article_id)
    if not original_assignment:
        print("This article has no editorial assignment, so return-to-editor cannot be tested.")
        return False

    print(
        "Original editor assignment: "
        f"assignment_id={original_assignment['assignment_id']}, "
        f"editor_id={original_assignment['editor_id']}, "
        f"editor={original_assignment['editor_name']}"
    )

    response = _request(
        "POST",
        f"{PUBLICATION_ENDPOINT}/articles/{article_id}/start-review",
        headers=headers,
    )
    _dump("start review for return test", response)
    if response["status_code"] != 200:
        return False

    response = _request(
        "POST",
        f"{PUBLICATION_ENDPOINT}/articles/{article_id}/return-to-editor",
        headers=headers,
        json_body={
            "editor_id": wrong_editor_id,
            "feedback": "This should fail because it targets the wrong editor.",
        },
    )
    _dump("return to wrong editor", response)
    wrong_editor_rejected = _assert_response(
        response["status_code"] == 400,
        "Publisher cannot return the paper to a different editor.",
        "Publisher was able to target a different editor.",
    )

    feedback = "Please correct publication formatting and references."
    response = _request(
        "POST",
        f"{PUBLICATION_ENDPOINT}/articles/{article_id}/return-to-editor",
        headers=headers,
        json_body={
            "editor_id": original_assignment["editor_id"],
            "feedback": feedback,
        },
    )
    _dump("return to original editor", response)
    if response["status_code"] != 200:
        return False

    updated_assignment = _fetch_latest_assignment(article_id)
    article_status = _fetch_article_status(article_id)
    notification = _fetch_notification(
        original_assignment["editor_user_id"],
        article_id,
        "Publication Team Feedback",
    )

    same_editor = _assert_response(
        updated_assignment and updated_assignment["editor_id"] == original_assignment["editor_id"],
        "Paper is still attached to the original editor.",
        "Paper is not attached to the original editor.",
    )
    active_assignment = _assert_response(
        updated_assignment and updated_assignment["assignment_status"] == "Active",
        "Original editor assignment is active again.",
        "Original editor assignment was not reactivated.",
    )
    status_ok = _assert_response(
        article_status == "Editorial Review",
        "Article status returned to Editorial Review.",
        f"Article status should be Editorial Review, got {article_status}.",
    )
    notification_ok = _assert_response(
        notification and notification["message"] == feedback,
        "Original editor received the publisher feedback notification.",
        "Feedback notification was not found for the original editor.",
    )

    return all([wrong_editor_rejected, same_editor, active_assignment, status_ok, notification_ok])


def _run_publish_flow(article_id, headers):
    _print_section("Publish Happy Path")

    response = _request(
        "POST",
        f"{PUBLICATION_ENDPOINT}/articles/{article_id}/start-review",
        headers=headers,
    )
    _dump("start review for publish test", response)
    if response["status_code"] != 200:
        return False

    organization_name = f"IJFINK Test Publisher {_rand()}"
    response = _request(
        "POST",
        f"{PUBLICATION_ENDPOINT}/articles/{article_id}/submit-organization",
        headers=headers,
        json_body={
            "organization_name": organization_name,
            "remarks": "Submitted through publication API test.",
        },
    )
    _dump("submit organization", response)
    if response["status_code"] != 200:
        return False

    publication_data = {
        "organization_name": organization_name,
        "doi": f"10.5555/{RUN_ID}",
        "article_url": f"https://example.org/articles/{RUN_ID}",
        "volume": "1",
        "issue": "1",
        "pages": "1-10",
        "publication_date": date.today().isoformat(),
    }
    response = _request(
        "POST",
        f"{PUBLICATION_ENDPOINT}/articles/{article_id}/publish",
        headers=headers,
        form_fields={"publication_data": json.dumps(publication_data)},
        multipart_files=[
            ("published_file", ("published-paper.pdf", b"%PDF-1.4 test file", "application/pdf")),
        ],
    )
    _dump("publish", response)
    if response["status_code"] != 201:
        return False

    response = _request("GET", f"{PUBLICATION_ENDPOINT}/published/{article_id}", headers=headers)
    _dump("published detail", response)
    return _assert_response(
        response["status_code"] == 200,
        "Published article detail is retrievable.",
        "Published article detail was not retrievable.",
    )


def _login(email, password, role):
    response = _request(
        "POST",
        f"{AUTH_ENDPOINT}/login",
        json_body={"email": email, "password": password, "role": role},
    )
    _dump(f"login {role}", response)
    if response["status_code"] == 200 and response["json"] and response["json"].get("success"):
        return response["json"]["data"]["access_token"]
    return None


def _register_publication_team(admin_token):
    payload = {
        "first_name": "Publication",
        "last_name": "Tester",
        "email": f"publication_{RUN_ID}_{_rand()}@test.local",
        "password": "Publication@123",
        "confirm_password": "Publication@123",
        "role": "Publication Team",
    }
    response = _request(
        "POST",
        f"{AUTH_ENDPOINT}/register",
        headers=_auth(admin_token),
        json_body=payload,
    )
    _dump("register publication team", response)
    if response["status_code"] != 201:
        return None
    return payload


def run():
    _print_section("PUBLICATION API TEST SUITE")
    print(f"Base URL: {BASE_URL}")
    print(f"Started: {datetime.now().isoformat(timespec='seconds')}")

    return_article_id, publish_article_id = _resolve_article_ids()
    if return_article_id is None:
        return 1

    health = _request("GET", f"{BASE_URL}/health", timeout=5)
    if health["status_code"] != 200:
        _dump("health", health)
        return 1

    admin_token = _login(
        ADMIN_CREDENTIALS["email"],
        ADMIN_CREDENTIALS["password"],
        ADMIN_CREDENTIALS["role"],
    )
    if not admin_token:
        return 1

    wrong_editor_id = _register_editor(admin_token, "ForPublicationReturn")
    if not wrong_editor_id:
        return 1

    publication_payload = _register_publication_team(admin_token)
    if not publication_payload:
        return 1

    publication_token = _login(
        publication_payload["email"],
        publication_payload["password"],
        "Publication Team",
    )
    if not publication_token:
        return 1

    headers = _auth(publication_token)

    _print_section("List Accepted Articles")
    response = _request("GET", f"{PUBLICATION_ENDPOINT}/accepted-articles", headers=headers)
    _dump("accepted articles", response)

    return_test_ok = _run_return_to_editor_test(return_article_id, headers, wrong_editor_id)

    publish_test_ok = True
    if publish_article_id is not None:
        publish_test_ok = _run_publish_flow(publish_article_id, headers)
        response = _request("GET", f"{PUBLICATION_ENDPOINT}/published", headers=headers)
        _dump("published list", response)

    _print_section("SUMMARY")
    if return_test_ok:
        print("[PASS] Return-to-original-editor rule verified.")
    else:
        print("[FAIL] Return-to-original-editor rule failed.")

    if publish_article_id is None:
        print("[SKIP] Publish happy path skipped because only one accepted article was available.")
    elif publish_test_ok:
        print("[PASS] Publish happy path verified.")
    else:
        print("[FAIL] Publish happy path failed.")

    return 0 if return_test_ok and publish_test_ok else 2


if __name__ == "__main__":
    sys.exit(run())
