#!/usr/bin/env python3
"""
Article Submission API Testing Script
Tests author submission endpoints with multipart uploads and JWT authentication.

Usage:
    python test_article_submission_api.py
"""

import io
import json
import os
import sys
import secrets
import time
import uuid
from datetime import datetime
from urllib import error as urllib_error
from urllib import request as urllib_request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")
AUTH_ENDPOINT = f"{BASE_URL}/api/auth"
USER_ENDPOINT = f"{BASE_URL}/api/user"


RUN_ID = f"{int(time.time())}{uuid.uuid4().hex[:8]}"


def generate_unique_email(prefix):
    return f"{prefix}.{RUN_ID}@example.com"


def generate_unique_orcid():
    digits = [secrets.randbelow(10) for _ in range(15)]
    total = 0

    for digit in digits:
        total = (total + digit) * 2

    remainder = total % 11
    check_digit = (12 - remainder) % 11
    check_character = "X" if check_digit == 10 else str(check_digit)
    orcid_digits = "".join(str(digit) for digit in digits) + check_character
    return "-".join(orcid_digits[index : index + 4] for index in range(0, 16, 4))


TEST_AUTHOR_REGISTRATION = {
    "first_name": "Article",
    "last_name": "Author",
    "email": generate_unique_email("article.author"),
    "password": "ArticleAuthor@123",
    "confirm_password": "ArticleAuthor@123",
    "institution": "IJFINK Test Institute",
    "role": "Author",
    "orcid": generate_unique_orcid(),
}


ARTICLE_PAYLOAD = {
    "title": "End-to-End API Submission Test",
    "abstract": "This is a backend integration test for article submission.",
    "keywords": ["testing", "submission", "api"],
    "article_type": "Research Article",
    "subject_area": "Computer Science",
    "co_authors": [
        {
            "full_name": "Co Author One",
            "email": generate_unique_email("coauthor.one"),
            "institution": "Institute One",
            "orcid": generate_unique_orcid(),
            "author_order": 1,
        },
        {
            "full_name": "Co Author Two",
            "email": generate_unique_email("coauthor.two"),
            "institution": "Institute Two",
            "orcid": generate_unique_orcid(),
            "author_order": 2,
        },
    ],
}


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    END = "\033[0m"


def print_section(title):
    print(f"\n{Colors.BLUE}{'=' * 80}")
    print(f"{title:^80}")
    print(f"{'=' * 80}{Colors.END}\n")


def print_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_error(message):
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_info(message):
    print(f"{Colors.YELLOW}ℹ {message}{Colors.END}")


def print_test(message):
    print(f"{Colors.CYAN}▶ {message}{Colors.END}")


def print_request(method, url, headers=None, body=None, files=None):
    print(f"\n{Colors.BLUE}Request:{Colors.END}")
    print(f"  {method} {url}")
    if headers:
        safe_headers = dict(headers)
        if "Authorization" in safe_headers:
            safe_headers["Authorization"] = "Bearer ***"
        print(f"  Headers: {json.dumps(safe_headers, indent=4)}")
    if body:
        print(f"  Body: {json.dumps(body, indent=4)}")
    if files:
        print(f"  Files: {json.dumps(files, indent=4)}")


def print_response(response):
    print(f"\n{Colors.BLUE}Response:{Colors.END}")
    print(f"  Status: {response['status_code']}")
    try:
        print(f"  Body: {json.dumps(response['json'], indent=4)}")
    except Exception:
        print(f"  Body: {response['text']}")


def build_multipart_body(fields, files):
    boundary = f"----IJFINKBoundary{uuid.uuid4().hex}"
    buffer = io.BytesIO()

    for field_name, field_value in (fields or {}).items():
        buffer.write(f"--{boundary}\r\n".encode("utf-8"))
        buffer.write(f'Content-Disposition: form-data; name="{field_name}"\r\n\r\n'.encode("utf-8"))
        buffer.write(str(field_value).encode("utf-8"))
        buffer.write(b"\r\n")

    for field_name, file_info in (files or []):
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


def send_request(method, url, headers=None, json_body=None, form_fields=None, multipart_files=None, timeout=10):
    request_headers = dict(headers or {})
    body = None

    if json_body is not None:
        body = json.dumps(json_body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    elif multipart_files is not None:
        boundary, body = build_multipart_body(form_fields or {}, multipart_files)
        request_headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"

    request = urllib_request.Request(url, data=body, headers=request_headers, method=method)

    try:
        with urllib_request.urlopen(request, timeout=timeout) as response:
            raw_text = response.read().decode("utf-8")
            try:
                json_data = json.loads(raw_text)
            except json.JSONDecodeError:
                json_data = None
            return {
                "status_code": response.status,
                "text": raw_text,
                "json": json_data,
            }
    except urllib_error.HTTPError as exc:
        raw_text = exc.read().decode("utf-8")
        try:
            json_data = json.loads(raw_text)
        except json.JSONDecodeError:
            json_data = None
        return {
            "status_code": exc.code,
            "text": raw_text,
            "json": json_data,
        }


def login(credentials):
    payload = {
        "email": credentials["email"],
        "password": credentials["password"],
        "role": credentials["role"],
    }

    print_section(f"LOGGING IN AS {credentials['role'].upper()}")
    print_request("POST", f"{AUTH_ENDPOINT}/login", body=payload)
    response = send_request("POST", f"{AUTH_ENDPOINT}/login", json_body=payload)
    print_response(response)

    if response["status_code"] == 200 and response["json"] and response["json"].get("success"):
        data = response["json"]["data"]
        print_success("Login successful.")
        return data["access_token"], data["user"]

    print_error("Login failed.")
    return None, None


def register_author(registration_data):
    print_section("REGISTER AUTHOR")
    print_request("POST", f"{AUTH_ENDPOINT}/register", body=registration_data)
    response = send_request("POST", f"{AUTH_ENDPOINT}/register", json_body=registration_data)
    print_response(response)

    if response["status_code"] == 201 and response["json"] and response["json"].get("success"):
        print_success("Author registration successful.")
        return response["json"]["data"]["user"]

    print_error("Author registration failed.")
    return None


def build_submission_files():
    return [
        ("main_manuscript", ("main-manuscript.txt", b"Main manuscript content", "text/plain")),
        ("editable_manuscript", ("editable-manuscript.docx", b"Editable manuscript content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
        ("cover_letter", ("cover-letter.txt", b"Cover letter content", "text/plain")),
        ("figures", ("figure-1.png", b"fake-figure-one", "image/png")),
        ("figures", ("figure-2.png", b"fake-figure-two", "image/png")),
        ("supplementary_files", ("supplementary.zip", b"fake-supplementary", "application/zip")),
    ]


def submit_article(token):
    print_section("SUBMIT ARTICLE")
    headers = {"Authorization": f"Bearer {token}"}
    data = {"article_data": json.dumps(ARTICLE_PAYLOAD)}
    files = build_submission_files()

    print_request(
        "POST",
        f"{USER_ENDPOINT}/articles",
        headers=headers,
        body={"article_data": ARTICLE_PAYLOAD},
        files=[name for name, _ in files],
    )
    response = send_request(
        "POST",
        f"{USER_ENDPOINT}/articles",
        headers=headers,
        form_fields=data,
        multipart_files=files,
    )
    print_response(response)

    if response["status_code"] == 201 and response["json"] and response["json"].get("success"):
        article = response["json"]["data"]["article"]
        print_success(f"Article submitted successfully. ID: {article['article_id']}")
        return article

    print_error("Article submission failed.")
    return None


def list_articles(token):
    print_section("LIST ARTICLES")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    print_request("GET", f"{USER_ENDPOINT}/articles", headers=headers)
    response = send_request("GET", f"{USER_ENDPOINT}/articles", headers=headers)
    print_response(response)

    if response["status_code"] == 200 and response["json"] and response["json"].get("success"):
        print_success("Fetched article list successfully.")
        return response["json"]["data"]["articles"]

    print_error("Fetching article list failed.")
    return []


def get_article_details(token, article_id):
    print_section(f"GET ARTICLE DETAILS ({article_id})")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    print_request("GET", f"{USER_ENDPOINT}/articles/{article_id}", headers=headers)
    response = send_request("GET", f"{USER_ENDPOINT}/articles/{article_id}", headers=headers)
    print_response(response)

    if response["status_code"] == 200 and response["json"] and response["json"].get("success"):
        print_success("Fetched article details successfully.")
        return response["json"]["data"]["article"]

    print_error("Fetching article details failed.")
    return None


def test_submission_requires_main_manuscript(token):
    print_section("TEST: MAIN MANUSCRIPT REQUIRED")
    print_test("Submitting without main manuscript")
    headers = {"Authorization": f"Bearer {token}"}
    data = {"article_data": json.dumps(ARTICLE_PAYLOAD)}
    files = [("cover_letter", ("cover-letter.txt", b"Cover", "text/plain"))]

    response = send_request(
        "POST",
        f"{USER_ENDPOINT}/articles",
        headers=headers,
        form_fields=data,
        multipart_files=files,
    )
    print_response(response)

    if response["status_code"] == 400:
        print_success("Endpoint correctly requires Main Manuscript.")
    else:
        print_error("Endpoint should reject submission without Main Manuscript.")


def test_author_auth_required():
    print_section("TEST: AUTHENTICATION REQUIRED")
    response = send_request("GET", f"{USER_ENDPOINT}/articles", headers={"Content-Type": "application/json"})
    print_response(response)

    if response["status_code"] == 401:
        print_success("Endpoint correctly requires authentication.")
    else:
        print_error("Endpoint should reject unauthenticated access.")


def main():
    print(f"\n{Colors.BLUE}")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "IJFINK BACKEND - ARTICLE SUBMISSION API TEST SUITE".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("║" + "Testing Author Article Submission Endpoints".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")
    print(f"{Colors.END}")

    print_info(f"Base URL: {BASE_URL}")
    print_info(f"Testing started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        response = send_request("GET", f"{BASE_URL}/health", timeout=2)
        if response["status_code"] == 200:
            print_success("Server is running")
        else:
            print_error("Server is not responding correctly")
            return
    except Exception:
        print_error(f"Cannot connect to server at {BASE_URL}")
        print_info("Please ensure the Flask server is running on http://localhost:5000")
        return

    registered_user = register_author(TEST_AUTHOR_REGISTRATION)
    if not registered_user:
        return

    token, user = login(
        {
            "email": TEST_AUTHOR_REGISTRATION["email"],
            "password": TEST_AUTHOR_REGISTRATION["password"],
            "role": "Author",
        }
    )
    if not token:
        return

    article = submit_article(token)
    if not article:
        return

    articles = list_articles(token)
    article_details = get_article_details(token, article["article_id"])

    if article_details:
        files = article_details.get("files", [])
        co_authors = article_details.get("co_authors", [])

        if article_details["status"] == "Submitted":
            print_success("Article status is Submitted.")
        else:
            print_error("Article status should be Submitted after creation.")

        if len(co_authors) == 2:
            print_success("Co-author records created correctly.")
        else:
            print_error("Co-author count mismatch.")

        main_manuscript_paths = [
            entry["file_path"]
            for entry in files
            if entry["file_type"] == "Main Manuscript"
        ]
        if main_manuscript_paths and main_manuscript_paths[0].startswith(f"{user['user_id']}/{article['article_id']}/"):
            print_success("File path format matches UserID/ArticleID/FileType/Filename.")
        else:
            print_error("File path format does not match the required structure.")

    if any(item["article_id"] == article["article_id"] for item in articles):
        print_success("Submitted article appears in author article list.")
    else:
        print_error("Submitted article is missing from author article list.")

    test_submission_requires_main_manuscript(token)
    test_author_auth_required()

    print_section("TEST SUMMARY")
    print_success("Article submission tests completed.")
    print_info(f"Testing finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
