# IJFINK Backend — API Integration Guide

**Base URL:** `http://localhost:5000`  
**Content-Type:** `application/json` (unless noted as multipart/form-data)  
**Authentication:** Bearer JWT token in the `Authorization` header

```
Authorization: Bearer <access_token>
```

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [Admin — User Management](#2-admin--user-management)
3. [Contact Queries](#3-contact-queries)
4. [Author — Articles](#4-author--articles)
5. [Screening](#5-screening)
6. [Editorial — Admin Side](#6-editorial--admin-side)
7. [Editorial — Editor Side](#7-editorial--editor-side)
8. [Editor Dashboard & Workflow](#8-editor-dashboard--workflow)
9. [Chief Editor](#9-chief-editor)
10. [Publication Team](#10-publication-team)
11. [Health Check](#11-health-check)
12. [Article Status Flow](#12-article-status-flow)
13. [Error Reference](#13-error-reference)

---

## 1. Authentication

### 1.1 Login

**POST** `/api/auth/login`  
Public endpoint — no token required.

**Request Body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `email` | string | Yes | Case-insensitive |
| `password` | string | Yes | |
| `role` | string | No | Optional role check: `author`, `admin`, `editor`, `chief editor`, `publication team` |
| `remember_me` | boolean | No | `true` → 30-day token; `false` (default) → 12-hour token |

**Example — Author login**
```json
{
  "email": "author@example.com",
  "password": "SecurePass123",
  "remember_me": false
}
```

**Example — Admin login with role validation**
```json
{
  "email": "admin@example.com",
  "password": "AdminPass123",
  "role": "admin",
  "remember_me": true
}
```

**Success Response `200`**
```json
{
  "success": true,
  "message": "Login successful.",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in_seconds": 43200,
    "user": {
      "user_id": 7,
      "email": "author@example.com",
      "role": "Author",
      "status": "Active",
      "display_name": "Jane Doe",
      "profile_id": 3,
      "redirect_to": "/dashboard/author"
    }
  }
}
```

**Error Responses**

| Status | Scenario |
|---|---|
| `400` | Missing email or password |
| `401` | Wrong password or email not found |
| `403` | Account is inactive; or role mismatch |

---

### 1.2 Register

**POST** `/api/auth/register`  
- No token required when registering an **Author**.  
- **Admin JWT required** when registering Admin / Editor / Publication Team accounts.

**Request Body — Author (public, no token)**

| Field | Type | Required |
|---|---|---|
| `first_name` | string | Yes |
| `last_name` | string | Yes |
| `email` | string | Yes |
| `password` | string | Yes |
| `confirm_password` | string | No |
| `institution` | string | Yes |
| `orcid` | string | No |
| `phone_number` | string | No |

```json
{
  "first_name": "Jane",
  "last_name": "Doe",
  "email": "jane.doe@university.edu",
  "password": "SecurePass123",
  "confirm_password": "SecurePass123",
  "institution": "University of Science",
  "orcid": "0000-0002-1234-5678",
  "phone_number": "+1-555-0100"
}
```

**Request Body — Editor (Admin JWT required)**

```json
{
  "first_name": "Mark",
  "last_name": "Smith",
  "email": "mark.smith@journal.org",
  "password": "EditorPass123",
  "role": "editor",
  "institution": "Journal Institute",
  "is_chief_editor": false
}
```

**Request Body — Chief Editor (Admin 1 JWT required)**

```json
{
  "first_name": "Sarah",
  "last_name": "Chen",
  "email": "sarah.chen@journal.org",
  "password": "ChiefPass123",
  "role": "editor",
  "institution": "Journal Institute",
  "is_chief_editor": true
}
```

**Request Body — Admin (Admin 1 JWT required)**

```json
{
  "first_name": "Admin",
  "last_name": "User",
  "email": "admin2@journal.org",
  "password": "AdminPass123",
  "role": "admin"
}
```

**Request Body — Publication Team (Admin JWT required)**

```json
{
  "first_name": "Tom",
  "last_name": "Jones",
  "email": "tom.jones@journal.org",
  "password": "PubPass123",
  "role": "publication team"
}
```

**Role aliases accepted in the `role` field**

| Alias | Resolves to |
|---|---|
| `author` | Author |
| `admin` | Admin |
| `editor` | Editor |
| `chief editor` / `chief_editor` / `chief-editor` | Editor (chief) |
| `publication team` / `publication_team` / `publication-team` | Publication Team |

**Success Response `201`**
```json
{
  "success": true,
  "message": "Author account created successfully.",
  "data": {
    "user": {
      "user_id": 12,
      "email": "jane.doe@university.edu",
      "role": "Author",
      "status": "Active",
      "display_name": "Jane Doe",
      "profile_id": 5,
      "redirect_to": "/dashboard/author"
    }
  }
}
```

**Error Responses**

| Status | Scenario |
|---|---|
| `400` | Missing required fields; passwords mismatch; institution missing for Author/Editor |
| `401` | Admin token required but missing |
| `403` | Caller is not Admin; non-Admin 1 trying to create Admin; non-Admin 1 trying to set chief editor |
| `409` | Email already exists; chief editor already exists |

---

## 2. Admin — User Management

All endpoints require **Admin JWT**.

### 2.1 Get All Users

**GET** `/api/admin/users`

**Query Parameters (optional)**

| Parameter | Values |
|---|---|
| `role` | `Author`, `Admin`, `Editor`, `Publication Team` |
| `status` | `Active`, `Inactive` |

**Example Requests**
```
GET /api/admin/users
GET /api/admin/users?role=Author
GET /api/admin/users?status=Inactive
GET /api/admin/users?role=Editor&status=Active
```

**Success Response `200`**
```json
{
  "success": true,
  "message": "Retrieved 3 user(s).",
  "data": {
    "users": [
      {
        "user_id": 7,
        "email": "jane.doe@university.edu",
        "role": "Author",
        "status": "Active",
        "display_name": "Jane Doe",
        "profile_id": 3,
        "created_at": "2024-11-01 09:00:00",
        "updated_at": "2024-11-01 09:00:00"
      }
    ],
    "total_count": 3,
    "filters_applied": {
      "role": "Author",
      "status": null
    }
  }
}
```

---

### 2.2 Get User Details

**GET** `/api/admin/users/<user_id>`

**Success Response `200`**
```json
{
  "success": true,
  "message": "User details retrieved successfully.",
  "data": {
    "user": {
      "user_id": 7,
      "email": "jane.doe@university.edu",
      "role": "Author",
      "status": "Active",
      "display_name": "Jane Doe",
      "profile_id": 3,
      "created_at": "2024-11-01 09:00:00",
      "updated_at": "2024-11-01 09:00:00",
      "full_profile": {
        "author_id": 3,
        "first_name": "Jane",
        "last_name": "Doe",
        "institution": "University of Science",
        "orcid": "0000-0002-1234-5678",
        "phone_number": "+1-555-0100"
      }
    }
  }
}
```

**Error Responses**

| Status | Scenario |
|---|---|
| `404` | User ID not found |

---

### 2.3 Toggle User Status

**PATCH** `/api/admin/users/<user_id>/status`

**Request Body**

| Field | Type | Required | Values |
|---|---|---|---|
| `status` | string | Yes | `Active` or `Inactive` |

**Example — Deactivate user**
```json
{
  "status": "Inactive"
}
```

**Example — Reactivate user**
```json
{
  "status": "Active"
}
```

**Success Response `200`**
```json
{
  "success": true,
  "message": "User successfully deactivated.",
  "data": {
    "user": {
      "user_id": 7,
      "email": "jane.doe@university.edu",
      "role": "Author",
      "status": "Inactive",
      "display_name": "Jane Doe",
      "profile_id": 3,
      "created_at": "2024-11-01 09:00:00",
      "updated_at": "2024-11-15 14:30:00"
    },
    "action_by": {
      "user_id": 1,
      "email": "admin@journal.org",
      "role": "Admin"
    }
  }
}
```

**Error Responses**

| Status | Scenario |
|---|---|
| `400` | Invalid status value; user already in that status; admin trying to self-deactivate |
| `404` | User not found |

---

## 3. Contact Queries

### 3.1 Submit a Contact Query

**POST** `/api/contact/queries`  
Public — no token required.

**Request Body**

| Field | Type | Required |
|---|---|---|
| `first_name` | string | Yes |
| `last_name` | string | Yes |
| `email` | string | Yes |
| `subject` | string | Yes |
| `message` | string | Yes |

```json
{
  "first_name": "John",
  "last_name": "Researcher",
  "email": "john.researcher@uni.edu",
  "subject": "Article Submission Inquiry",
  "message": "I would like to know the formatting requirements for article submissions."
}
```

**Success Response `201`**
```json
{
  "success": true,
  "message": "Contact query submitted successfully.",
  "data": {
    "query_id": 14,
    "first_name": "John",
    "last_name": "Researcher",
    "email": "john.researcher@uni.edu",
    "subject": "Article Submission Inquiry",
    "message": "I would like to know the formatting requirements for article submissions.",
    "status": "Pending",
    "created_at": "2024-11-15T10:30:00.000000"
  }
}
```

---

### 3.2 Get All Contact Queries

**GET** `/api/contact/queries`  
Requires **Admin JWT**.

**Query Parameters (optional)**

| Parameter | Values |
|---|---|
| `status` | `Pending`, `Resolved` |

```
GET /api/contact/queries
GET /api/contact/queries?status=Pending
GET /api/contact/queries?status=Resolved
```

**Success Response `200`**
```json
{
  "success": true,
  "message": "Retrieved 2 contact query(ies).",
  "data": {
    "queries": [
      {
        "query_id": 14,
        "first_name": "John",
        "last_name": "Researcher",
        "email": "john.researcher@uni.edu",
        "subject": "Article Submission Inquiry",
        "message": "I would like to know the formatting requirements...",
        "status": "Pending",
        "created_at": "2024-11-15 10:30:00",
        "resolved_at": null,
        "assigned_admin": null
      }
    ],
    "total_count": 2,
    "filters_applied": {
      "status": "Pending"
    }
  }
}
```

---

### 3.3 Get Contact Query Details

**GET** `/api/contact/queries/<query_id>`  
Requires **Admin JWT**.

**Success Response `200`**
```json
{
  "success": true,
  "message": "Contact query details retrieved successfully.",
  "data": {
    "query": {
      "query_id": 14,
      "first_name": "John",
      "last_name": "Researcher",
      "email": "john.researcher@uni.edu",
      "subject": "Article Submission Inquiry",
      "message": "I would like to know the formatting requirements...",
      "status": "Resolved",
      "created_at": "2024-11-15 10:30:00",
      "resolved_at": "2024-11-16 11:00:00",
      "assigned_admin": "Alice Admin"
    }
  }
}
```

---

### 3.4 Update Contact Query Status

**PATCH** `/api/contact/queries/<query_id>/status`  
Requires **Admin JWT**.

**Request Body**

| Field | Type | Required | Values |
|---|---|---|---|
| `status` | string | Yes | `Pending` or `Resolved` |

**Example — Mark as resolved**
```json
{
  "status": "Resolved"
}
```

**Success Response `200`**
```json
{
  "success": true,
  "message": "Contact query status updated to Resolved.",
  "data": {
    "query_id": 14,
    "status": "Resolved",
    "updated_by": {
      "user_id": 1,
      "email": "admin@journal.org",
      "role": "Admin"
    },
    "resolved_at": "2024-11-16T11:00:00.000000"
  }
}
```

---

## 4. Author — Articles

All endpoints require an **Author JWT**.

### 4.1 Submit Article

**POST** `/api/user/articles`  
Content-Type: `multipart/form-data`

The article metadata is submitted as a JSON string in a form field. Files are sent as separate form fields.

**Form Fields**

| Field | Type | Required | Notes |
|---|---|---|---|
| `article_data` | JSON string | Yes | See structure below |
| `main_manuscript` | file | Yes | PDF/DOC of manuscript |
| `editable_manuscript` | file | No | Editable version |
| `cover_letter` | file | No | Cover letter document |
| `video_abstract` | file | No | Video file |
| `copyright_form` | file | No | Signed copyright form |
| `figures` | file(s) | No | Multiple allowed |
| `supplementary_files` | file(s) | No | Multiple allowed |

**`article_data` JSON structure**

```json
{
  "title": "Deep Learning Applications in Medical Imaging",
  "abstract": "This paper explores the use of convolutional neural networks in early disease detection...",
  "keywords": ["deep learning", "medical imaging", "CNN", "disease detection"],
  "article_type": "Research Article",
  "subject_area": "Computer Science",
  "co_authors": [
    {
      "full_name": "Dr. Robert Kim",
      "email": "robert.kim@hospital.org",
      "institution": "City Medical Center",
      "orcid": "0000-0001-9876-5432",
      "author_order": 2
    },
    {
      "full_name": "Prof. Maria Lopez",
      "email": "maria.lopez@tech.edu",
      "institution": "Tech University",
      "orcid": null,
      "author_order": 3
    }
  ]
}
```

> `keywords` can also be a comma-separated string: `"deep learning, medical imaging, CNN"`.  
> `co_authors` is optional — omit or pass an empty array `[]` if none.  
> Each co-author's `author_order` must be unique per article (minimum value: 1).

**Example — cURL**
```bash
curl -X POST http://localhost:5000/api/user/articles \
  -H "Authorization: Bearer <token>" \
  -F 'article_data={"title":"Deep Learning in Medical Imaging","abstract":"...","keywords":["deep learning"],"article_type":"Research Article","subject_area":"Computer Science","co_authors":[]}' \
  -F "main_manuscript=@/path/to/manuscript.pdf" \
  -F "cover_letter=@/path/to/cover_letter.pdf"
```

**Success Response `201`**
```json
{
  "success": true,
  "message": "Article submitted successfully.",
  "data": {
    "article": {
      "article_id": 42,
      "title": "Deep Learning Applications in Medical Imaging",
      "abstract": "This paper explores...",
      "keywords": ["deep learning", "medical imaging", "CNN", "disease detection"],
      "article_type": "Research Article",
      "subject_area": "Computer Science",
      "status": "Submitted",
      "submitted_at": "2024-11-15 12:00:00",
      "updated_at": "2024-11-15 12:00:00",
      "author": {
        "author_id": 3,
        "user_id": 7,
        "first_name": "Jane",
        "last_name": "Doe",
        "institution": "University of Science",
        "orcid": "0000-0002-1234-5678",
        "phone_number": "+1-555-0100"
      },
      "co_authors": [
        {
          "co_author_id": 1,
          "full_name": "Dr. Robert Kim",
          "email": "robert.kim@hospital.org",
          "institution": "City Medical Center",
          "orcid": "0000-0001-9876-5432",
          "author_order": 2
        }
      ],
      "files": [
        {
          "file_id": 101,
          "file_name": "manuscript.pdf",
          "file_type": "Main Manuscript",
          "file_path": "7/42/Main Manuscript/manuscript.pdf",
          "version": 1,
          "uploaded_at": "2024-11-15 12:00:00"
        }
      ],
      "revisions": []
    }
  }
}
```

---

### 4.2 List My Articles

**GET** `/api/user/articles`

**Success Response `200`**
```json
{
  "success": true,
  "message": "Retrieved 2 article(s).",
  "data": {
    "articles": [
      {
        "article_id": 42,
        "title": "Deep Learning Applications in Medical Imaging",
        "abstract": "This paper explores...",
        "keywords": ["deep learning", "medical imaging"],
        "article_type": "Research Article",
        "subject_area": "Computer Science",
        "status": "Submitted",
        "submitted_at": "2024-11-15 12:00:00",
        "updated_at": "2024-11-15 12:00:00"
      }
    ],
    "total_count": 2,
    "author": {
      "author_id": 3,
      "user_id": 7,
      "name": "Jane Doe"
    }
  }
}
```

---

### 4.3 Get Article Details

**GET** `/api/user/articles/<article_id>`

Returns the same detailed structure as the Submit Article response (article, author, co_authors, files, revisions).

**Error Responses**

| Status | Scenario |
|---|---|
| `404` | Article not found or belongs to another author |

---

### 4.4 Submit Revision

**POST** `/api/user/articles/<article_id>/revisions`  
Content-Type: `multipart/form-data`  
Only allowed when `article.status == "Revision Requested"`.

**Form Fields**

| Field | Type | Required |
|---|---|---|
| `revision_data` | JSON string | Yes |
| `revision_file` | file | Yes |

**`revision_data` JSON structure**

```json
{
  "editorial_review_id": 8,
  "response_letter": "We have addressed all reviewer comments. Section 3 has been rewritten to clarify the methodology..."
}
```

**Example — cURL**
```bash
curl -X POST http://localhost:5000/api/user/articles/42/revisions \
  -H "Authorization: Bearer <token>" \
  -F 'revision_data={"editorial_review_id":8,"response_letter":"Addressed all comments..."}' \
  -F "revision_file=@/path/to/revised_manuscript.pdf"
```

**Success Response `201`**
```json
{
  "success": true,
  "message": "Revision submitted successfully.",
  "data": {
    "article": { "...": "full article object as above" },
    "revision": {
      "revision_id": 5,
      "editorial_review_id": 8,
      "revision_number": 1,
      "response_letter": "Addressed all comments...",
      "file_name": "revised_manuscript.pdf",
      "file_path": "7/42/Revision File/revised_manuscript.pdf",
      "file_version": 1
    }
  }
}
```

**Error Responses**

| Status | Scenario |
|---|---|
| `400` | Article is not in `Revision Requested` status; editorial_review_id not found; decision is not Minor/Major Revision; missing revision_file |
| `404` | Article not found; editorial review not found |

---

## 5. Screening

All endpoints require **Admin JWT**.

### 5.1 Get Pending Articles

**GET** `/api/screening/pending`

Returns articles in `Submitted` status that have not yet been screened.

**Success Response `200`**
```json
{
  "success": true,
  "message": "Retrieved 3 pending article(s) for screening.",
  "data": {
    "articles": [
      {
        "article_id": 42,
        "title": "Deep Learning Applications in Medical Imaging",
        "abstract": "This paper explores...",
        "keywords": "deep learning, medical imaging",
        "article_type": "Research Article",
        "subject_area": "Computer Science",
        "status": "Submitted",
        "submitted_at": "2024-11-15 12:00:00",
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "jane.doe@university.edu",
        "institution": "University of Science",
        "screening_status": "Pending"
      }
    ],
    "total_count": 3
  }
}
```

---

### 5.2 Get Article Details for Screening

**GET** `/api/screening/<article_id>`

Returns article + co-authors + uploaded files + any existing screening record.

**Success Response `200`**
```json
{
  "success": true,
  "message": "Article details retrieved successfully.",
  "data": {
    "article": {
      "article_id": 42,
      "title": "Deep Learning Applications in Medical Imaging",
      "abstract": "...",
      "keywords": "deep learning, medical imaging",
      "article_type": "Research Article",
      "subject_area": "Computer Science",
      "status": "Submitted",
      "submitted_at": "2024-11-15 12:00:00",
      "first_name": "Jane",
      "last_name": "Doe",
      "email": "jane.doe@university.edu",
      "institution": "University of Science",
      "phone_number": "+1-555-0100",
      "orcid": "0000-0002-1234-5678",
      "co_authors": [
        {
          "full_name": "Dr. Robert Kim",
          "email": "robert.kim@hospital.org",
          "institution": "City Medical Center",
          "orcid": "0000-0001-9876-5432",
          "author_order": 2
        }
      ],
      "files": [
        {
          "file_id": 101,
          "file_name": "manuscript.pdf",
          "file_type": "Main Manuscript",
          "file_path": "7/42/Main Manuscript/manuscript.pdf",
          "version": 1,
          "uploaded_at": "2024-11-15 12:00:00"
        }
      ],
      "screening": null
    }
  }
}
```

---

### 5.3 Submit Screening Decision

**POST** `/api/screening/<article_id>/decision`

Can only be applied to articles with `status == "Submitted"` that have not been screened yet.

**Request Body**

| Field | Type | Required | Values |
|---|---|---|---|
| `decision` | string | Yes | `Approved` or `Rejected` |
| `remarks` | string | No | Free-text notes |

**Example — Approve**
```json
{
  "decision": "Approved",
  "remarks": "Article meets all submission guidelines."
}
```

**Example — Reject**
```json
{
  "decision": "Rejected",
  "remarks": "Abstract is too brief and does not describe the methodology."
}
```

**Success Response `201`**
```json
{
  "success": true,
  "message": "Screening decision 'Approved' submitted successfully.",
  "data": {
    "screening_id": 18,
    "article_id": 42,
    "decision": "Approved",
    "remarks": "Article meets all submission guidelines.",
    "screened_at": "2024-11-16T09:00:00.000000",
    "new_article_status": "Admin Approved"
  }
}
```

**Error Responses**

| Status | Scenario |
|---|---|
| `400` | Article not in `Submitted` status; decision value invalid |
| `400` | Article already screened |
| `404` | Article not found |

---

### 5.4 Get Screening History

**GET** `/api/screening/history`

**Query Parameters (optional)**

| Parameter | Values | Notes |
|---|---|---|
| `decision` | `Approved`, `Rejected` | Filter by outcome |
| `screened_by_me` | `true` | Only show your own decisions |
| `date_from` | `YYYY-MM-DD` | Start of date range |
| `date_to` | `YYYY-MM-DD` | End of date range |

```
GET /api/screening/history
GET /api/screening/history?decision=Approved
GET /api/screening/history?screened_by_me=true
GET /api/screening/history?date_from=2024-11-01&date_to=2024-11-30
```

**Success Response `200`**
```json
{
  "success": true,
  "message": "Retrieved 5 screening record(s).",
  "data": {
    "screenings": [
      {
        "screening_id": 18,
        "article_id": 42,
        "decision": "Approved",
        "remarks": "Article meets guidelines.",
        "screened_at": "2024-11-16 09:00:00",
        "screened_by": "Alice Admin",
        "title": "Deep Learning Applications in Medical Imaging",
        "status": "Admin Approved",
        "author_name": "Jane Doe"
      }
    ],
    "total_count": 5
  }
}
```

---

## 6. Editorial — Admin Side

All endpoints require **Admin JWT**.

### 6.1 List Assignable Articles

**GET** `/api/editorial/assignable-articles`

Returns articles in `Admin Approved` status with `admin_screening.decision = 'Approved'` that have no active editorial assignment.

**Success Response `200`**
```json
{
  "success": true,
  "message": "Retrieved 2 article(s) awaiting editor assignment.",
  "data": {
    "articles": [
      {
        "article_id": 42,
        "title": "Deep Learning Applications in Medical Imaging",
        "article_type": "Research Article",
        "subject_area": "Computer Science",
        "status": "Admin Approved",
        "submitted_at": "2024-11-15 12:00:00",
        "updated_at": "2024-11-16 09:00:00",
        "author_name": "Jane Doe",
        "author_email": "jane.doe@university.edu",
        "screening_id": 18,
        "screened_at": "2024-11-16 09:00:00",
        "screening_remarks": "Article meets all submission guidelines."
      }
    ],
    "total_count": 2
  }
}
```

---

### 6.2 List Assignable Editors

**GET** `/api/editorial/assignable-editors`

Returns active editors (chief editor excluded).

**Success Response `200`**
```json
{
  "success": true,
  "message": "Retrieved 4 assignable editor(s).",
  "data": {
    "editors": [
      {
        "editor_id": 2,
        "first_name": "Mark",
        "last_name": "Smith",
        "institution": "Journal Institute",
        "is_chief_editor": false,
        "user_id": 9,
        "email": "mark.smith@journal.org",
        "status": "Active"
      }
    ],
    "total_count": 4
  }
}
```

---

### 6.3 Assign Editor to Article

**POST** `/api/editorial/assignments`

**Request Body**

| Field | Type | Required |
|---|---|---|
| `article_id` | integer | Yes |
| `editor_id` | integer | Yes |

```json
{
  "article_id": 42,
  "editor_id": 2
}
```

**Success Response `201`**
```json
{
  "success": true,
  "message": "Editor assigned successfully.",
  "data": {
    "assignment_id": 11,
    "article_id": 42,
    "editor_id": 2,
    "admin_id": 1,
    "status": "Active",
    "assigned_at": "2024-11-16T10:00:00.000000"
  }
}
```

**Error Responses**

| Status | Scenario |
|---|---|
| `400` | Article not in `Admin Approved` status; editor inactive; chief editor selected |
| `403` | Admin screening decision is not `Approved` |
| `404` | Article or editor not found |
| `409` | Active editorial assignment already exists |

---

## 7. Editorial — Editor Side

All endpoints require an **Editor JWT** (regular or chief editor).

### 7.1 List My Assignments

**GET** `/api/editorial/assignments`

- **Chief editor:** sees all assignments.  
- **Regular editor:** sees only their own assignments.

**Success Response `200`**
```json
{
  "success": true,
  "message": "Retrieved 3 assignment(s).",
  "data": {
    "assignments": [
      {
        "assignment_id": 11,
        "article_id": 42,
        "editor_id": 2,
        "admin_id": 1,
        "assignment_status": "Active",
        "assigned_at": "2024-11-16 10:00:00",
        "title": "Deep Learning Applications in Medical Imaging",
        "article_type": "Research Article",
        "subject_area": "Computer Science",
        "article_status": "Editorial Review",
        "submitted_at": "2024-11-15 12:00:00",
        "author_name": "Jane Doe",
        "editor_name": "Mark Smith",
        "editor_is_chief": false
      }
    ],
    "total_count": 3,
    "viewer": {
      "editor_id": 2,
      "is_chief_editor": false
    }
  }
}
```

---

### 7.2 Get Assignment Details

**GET** `/api/editorial/assignments/<assignment_id>`

Only the assigned editor or the chief editor may call this.

**Success Response `200`**
```json
{
  "success": true,
  "message": "Assignment retrieved successfully.",
  "data": {
    "assignment": {
      "assignment_id": 11,
      "article_id": 42,
      "editor_id": 2,
      "admin_id": 1,
      "assignment_status": "Active",
      "assigned_at": "2024-11-16 10:00:00"
    },
    "article": {
      "article_id": 42,
      "title": "Deep Learning Applications in Medical Imaging",
      "abstract": "...",
      "keywords": "deep learning, medical imaging",
      "article_type": "Research Article",
      "subject_area": "Computer Science",
      "status": "Editorial Review",
      "submitted_at": "2024-11-15 12:00:00",
      "author_first_name": "Jane",
      "author_last_name": "Doe",
      "author_email": "jane.doe@university.edu"
    },
    "co_authors": [],
    "files": [
      {
        "file_id": 101,
        "file_name": "manuscript.pdf",
        "file_type": "Main Manuscript",
        "file_path": "7/42/Main Manuscript/manuscript.pdf",
        "version": 1,
        "uploaded_at": "2024-11-15 12:00:00"
      }
    ],
    "admin_screening": {
      "screening_id": 18,
      "decision": "Approved",
      "remarks": "Article meets all submission guidelines.",
      "screened_at": "2024-11-16 09:00:00",
      "screened_by": "Alice Admin"
    },
    "assigned_editor": {
      "editor_id": 2,
      "first_name": "Mark",
      "last_name": "Smith",
      "institution": "Journal Institute",
      "is_chief_editor": false,
      "email": "mark.smith@journal.org"
    },
    "viewer": {
      "editor_id": 2,
      "is_chief_editor": false,
      "is_assignee": true
    }
  }
}
```

---

## 8. Editor Dashboard & Workflow

All endpoints require **Editor JWT**.

### 8.1 Editor Dashboard

**GET** `/api/editor/dashboard`

**Success Response `200`**
```json
{
  "success": true,
  "message": "Dashboard data retrieved successfully.",
  "data": {
    "assigned_articles": 8,
    "pending_reviews": 3,
    "completed_reviews": 5,
    "revision_requests": 2,
    "accepted_articles": 2,
    "rejected_articles": 1
  }
}
```

---

### 8.2 List Editor's Articles

**GET** `/api/editor/articles`

**Query Parameters (optional)**

| Parameter | Type | Notes |
|---|---|---|
| `page` | integer | Default: `1` |
| `per_page` | integer | Default: `10`, max `100` |
| `sort_by` | string | `ea.assigned_at` (default), `a.title`, `a.status`, `ea.status` |
| `sort_order` | string | `ASC` or `DESC` (default) |
| `search` | string | Searches title, subject_area, article_type |
| `status` | string | Filter by article status |

```
GET /api/editor/articles
GET /api/editor/articles?page=2&per_page=5
GET /api/editor/articles?status=Editorial+Review
GET /api/editor/articles?search=deep+learning&sort_by=a.title&sort_order=ASC
```

**Success Response `200`**
```json
{
  "success": true,
  "message": "Retrieved 3 article(s).",
  "data": {
    "articles": [ { "...": "assignment + article fields" } ],
    "pagination": {
      "page": 1,
      "per_page": 10,
      "total_count": 3
    }
  }
}
```

---

### 8.3 Get Article Details (Editor View)

**GET** `/api/editor/articles/<article_id>`

Returns the article with its files, full review history, revision history, and assignment history.  
Only the assigned editor or chief editor can access.

**Success Response `200`**
```json
{
  "success": true,
  "message": "Article retrieved successfully.",
  "data": {
    "article": { "...": "full article + author fields" },
    "files": [],
    "review_history": [],
    "revision_history": [],
    "assignment_history": [],
    "current_status": "Editorial Review"
  }
}
```

---

### 8.4 Get Article Files

**GET** `/api/editor/articles/<article_id>/files`

**Success Response `200`**
```json
{
  "success": true,
  "message": "Files retrieved successfully.",
  "data": {
    "files": [
      {
        "file_id": 101,
        "file_name": "manuscript.pdf",
        "file_type": "Main Manuscript",
        "file_path": "7/42/Main Manuscript/manuscript.pdf",
        "version": 1,
        "uploaded_at": "2024-11-15 12:00:00"
      }
    ]
  }
}
```

---

### 8.5 Submit Editorial Review

**POST** `/api/editor/review`

**Request Body**

| Field | Type | Required | Values |
|---|---|---|---|
| `assignment_id` | integer | Yes | |
| `decision` | string | Yes | `Accepted`, `Minor Revision`, `Major Revision`, `Rejected` |
| `comments` | string | No | Reviewer comments |

**Example — Accept article**
```json
{
  "assignment_id": 11,
  "decision": "Accepted",
  "comments": "Excellent work with thorough methodology and clear conclusions."
}
```

**Example — Request minor revision**
```json
{
  "assignment_id": 11,
  "decision": "Minor Revision",
  "comments": "Please expand the related work section and add more recent references."
}
```

**Example — Reject article**
```json
{
  "assignment_id": 11,
  "decision": "Rejected",
  "comments": "The research methodology has fundamental flaws that cannot be addressed through revision."
}
```

Decision aliases (case-insensitive input accepted):
- `"accepted"` → `Accepted`
- `"minor revision"` → `Minor Revision`
- `"major revision"` → `Major Revision`
- `"rejected"` → `Rejected`

**Side effects by decision:**

| Decision | Article Status | Assignment Status | Notifications |
|---|---|---|---|
| `Accepted` | `Accepted` | `Completed` | Author notified; all Publication Team notified |
| `Minor Revision` | `Revision Requested` | `Active` | Author notified |
| `Major Revision` | `Revision Requested` | `Active` | Author notified |
| `Rejected` | `Rejected` | `Completed` | Author notified |

**Success Response `201`**
```json
{
  "success": true,
  "message": "Editorial review submitted successfully.",
  "data": {
    "review_id": 8,
    "assignment_id": 11,
    "decision": "Minor Revision"
  }
}
```

**Error Responses**

| Status | Scenario |
|---|---|
| `400` | Missing `assignment_id` or `decision` |
| `403` | Assignment belongs to another editor |
| `404` | Assignment not found |
| `409` | Assignment not active; article not in a valid review state |
| `422` | Invalid decision value |

---

### 8.6 Update Editorial Review

**PUT** `/api/editor/review/<review_id>`

Only the latest review for an assignment can be updated. Article must not be Published.

**Request Body (at least one field required)**

| Field | Type | Notes |
|---|---|---|
| `decision` | string | Same valid values as Submit Review |
| `comments` | string | Updated comments |

```json
{
  "decision": "Major Revision",
  "comments": "After re-reading, this requires more substantial changes."
}
```

**Success Response `200`**
```json
{
  "success": true,
  "message": "Review updated successfully.",
  "data": {
    "review_id": 8
  }
}
```

---

### 8.7 Review History

**GET** `/api/editor/reviews`

Returns all reviews submitted by the calling editor.

**Success Response `200`**
```json
{
  "success": true,
  "message": "Retrieved 5 review(s).",
  "data": {
    "reviews": [
      {
        "editorial_review_id": 8,
        "assignment_id": 11,
        "editor_id": 2,
        "decision": "Minor Revision",
        "comments": "Please expand the related work section.",
        "reviewed_at": "2024-11-17 14:00:00",
        "article_id": 42,
        "title": "Deep Learning Applications in Medical Imaging",
        "article_status": "Revision Requested"
      }
    ]
  }
}
```

---

### 8.8 Revision Requests

**GET** `/api/editor/revision-requests`

Returns articles assigned to this editor where the status is `Revision Requested`.

**Success Response `200`**
```json
{
  "success": true,
  "message": "Retrieved 1 article(s).",
  "data": {
    "articles": [
      {
        "article_id": 42,
        "title": "Deep Learning Applications in Medical Imaging",
        "article_status": "Revision Requested",
        "editorial_review_id": 8,
        "decision": "Minor Revision",
        "reviewed_at": "2024-11-17 14:00:00",
        "author_name": "Jane Doe"
      }
    ]
  }
}
```

---

### 8.9 Editor Notifications

**GET** `/api/editor/notifications`

**Success Response `200`**
```json
{
  "success": true,
  "message": "Retrieved 2 notification(s).",
  "data": {
    "notifications": [
      {
        "notification_id": 5,
        "user_id": 9,
        "article_id": 42,
        "title": "Publication Team Feedback",
        "message": "Please revise the formatting of Figure 3.",
        "is_read": false,
        "created_at": "2024-11-20 11:00:00"
      }
    ]
  }
}
```

---

### 8.10 Mark Notification as Read

**PUT** `/api/editor/notifications/<notification_id>/read`

No request body required.

**Success Response `200`**
```json
{
  "success": true,
  "message": "Notification marked as read.",
  "data": {
    "notification_id": 5,
    "is_read": true
  }
}
```

---

## 9. Chief Editor

All endpoints require a **Chief Editor JWT** (Editor role + `is_chief_editor = true`).

### 9.1 Chief Editor Dashboard

**GET** `/api/chief-editor/dashboard`

> Note: this blueprint is registered but not yet in `app/__init__.py`. Register it with `url_prefix="/api/chief-editor"` to activate.

**Success Response `200`**
```json
{
  "success": true,
  "message": "Dashboard data retrieved successfully.",
  "data": {
    "total_assigned_articles": 20,
    "pending_editorial_reviews": 5,
    "revision_requested": 3,
    "accepted": 8,
    "rejected": 2,
    "published": 6,
    "active_editors": 4,
    "average_review_time": 1440.5
  }
}
```

---

### 9.2 List All Articles (Chief Editor)

**GET** `/api/chief-editor/articles`

**Query Parameters (optional)**

| Parameter | Type | Notes |
|---|---|---|
| `page` | integer | Default `1` |
| `per_page` | integer | Default `10`, max `100` |
| `search` | string | Matches title, subject_area, article_type |
| `status` | string | Filter by article status |
| `editor_id` | integer | Filter by assigned editor |

```
GET /api/chief-editor/articles
GET /api/chief-editor/articles?status=Editorial+Review
GET /api/chief-editor/articles?editor_id=2&page=1&per_page=5
```

---

### 9.3 Get Article Details (Chief Editor)

**GET** `/api/chief-editor/articles/<article_id>`

Returns full article with files, review history, revision history, notifications, and a timeline.

**Success Response `200`**
```json
{
  "success": true,
  "message": "Article retrieved successfully.",
  "data": {
    "article": { "...": "full article fields" },
    "files": [],
    "review_history": [],
    "revision_history": [],
    "notifications": [],
    "article_timeline": [
      { "event": "Submitted", "at": "2024-11-15 12:00:00" },
      { "event": "Review: Minor Revision", "at": "2024-11-17 14:00:00" },
      { "event": "Revision 1", "at": "2024-11-19 09:00:00" }
    ]
  }
}
```

---

### 9.4 List All Editors (Chief Editor)

**GET** `/api/chief-editor/editors`

Returns all editors with performance stats.

**Success Response `200`**
```json
{
  "success": true,
  "message": "Retrieved 5 editor(s).",
  "data": {
    "editors": [
      {
        "editor_id": 2,
        "first_name": "Mark",
        "last_name": "Smith",
        "institution": "Journal Institute",
        "is_chief_editor": false,
        "email": "mark.smith@journal.org",
        "status": "Active",
        "assigned_articles": 6,
        "completed_reviews": 4,
        "accepted": 2,
        "rejected": 1,
        "average_completion_time": 980.0
      }
    ]
  }
}
```

---

### 9.5 Get Editor Details

**GET** `/api/chief-editor/editors/<editor_id>`

Returns one editor with full performance stats.

---

### 9.6 Pending Reviews

**GET** `/api/chief-editor/pending`

Returns all active assignments where the article is in `Editorial Review` status.

---

### 9.7 Revision Requests (Chief Editor)

**GET** `/api/chief-editor/revisions`

Returns all articles across all editors where status is `Revision Requested`.

---

### 9.8 Statistics

**GET** `/api/chief-editor/statistics`

**Success Response `200`**
```json
{
  "success": true,
  "message": "Statistics retrieved successfully.",
  "data": {
    "acceptance_rate": 40.0,
    "rejection_rate": 20.0,
    "revision_rate": 40.0,
    "average_review_time": 1440.5,
    "editor_workload": [
      {
        "editor_id": 2,
        "first_name": "Mark",
        "last_name": "Smith",
        "is_chief_editor": false,
        "assigned_articles": 6,
        "active_assignments": 2,
        "completed_reviews": 4
      }
    ]
  }
}
```

---

### 9.9 Chief Editor Notifications

**GET** `/api/chief-editor/notifications`

Same structure as editor notifications.

---

### 9.10 Mark Chief Editor Notification as Read

**PUT** `/api/chief-editor/notifications/<notification_id>/read`

Same behaviour as editor notifications.

---

## 10. Publication Team

All endpoints require a **Publication Team JWT**.

### 10.1 List Accepted Articles

**GET** `/api/publication/accepted-articles`

Returns articles in `Accepted` status, ready to begin publication review.

**Success Response `200`**
```json
{
  "success": true,
  "message": "Retrieved 2 accepted article(s).",
  "data": {
    "articles": [
      {
        "article_id": 42,
        "title": "Deep Learning Applications in Medical Imaging",
        "article_type": "Research Article",
        "subject_area": "Computer Science",
        "status": "Accepted",
        "submitted_at": "2024-11-15 12:00:00",
        "updated_at": "2024-11-18 15:00:00",
        "author_name": "Jane Doe",
        "author_email": "jane.doe@university.edu"
      }
    ],
    "total_count": 2,
    "viewer": {
      "publication_team_id": 1,
      "name": "Tom Jones"
    }
  }
}
```

---

### 10.2 Get Article Details (Publication Team)

**GET** `/api/publication/articles/<article_id>`

Returns full article details including co-authors, files, editorial assignments, editorial reviews, and existing publication record.

---

### 10.3 Start Publication Review

**POST** `/api/publication/articles/<article_id>/start-review`

Changes article status from `Accepted` → `Publication Review`. No request body required.

**Success Response `200`**
```json
{
  "success": true,
  "message": "Publication review started successfully.",
  "data": {
    "article_id": 42,
    "new_article_status": "Publication Review"
  }
}
```

---

### 10.4 Return Article to Editor

**POST** `/api/publication/articles/<article_id>/return-to-editor`

Article must be in `Publication Review` status.

**Request Body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `feedback` | string | Yes | Reason for returning (also accepted as `remarks`) |
| `editor_id` | integer | No | Must match the latest assigned editor if provided |

```json
{
  "feedback": "Figure 3 resolution is too low. Please provide high-resolution images (300 DPI minimum)."
}
```

**Success Response `200`**
```json
{
  "success": true,
  "message": "Article returned to editor successfully.",
  "data": {
    "article_id": 42,
    "assignment_id": 11,
    "editor_id": 2,
    "feedback": "Figure 3 resolution is too low...",
    "new_article_status": "Editorial Review",
    "assignment_status": "Active"
  }
}
```

---

### 10.5 Submit to Organization

**POST** `/api/publication/articles/<article_id>/submit-organization`

Article must be in `Publication Review` status. Changes status to `Submitted To Organization`.

**Request Body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `organization_name` | string | Yes | |
| `remarks` | string | No | Optional notes |

```json
{
  "organization_name": "IEEE Xplore Digital Library",
  "remarks": "Submitted under the Computer Science & AI track."
}
```

**Success Response `200`**
```json
{
  "success": true,
  "message": "Article submitted to organization successfully.",
  "data": {
    "article_id": 42,
    "organization_name": "IEEE Xplore Digital Library",
    "remarks": "Submitted under the Computer Science & AI track.",
    "new_article_status": "Submitted To Organization"
  }
}
```

---

### 10.6 Reject Article (Publication)

**POST** `/api/publication/articles/<article_id>/reject`

Article must be in `Submitted To Organization` status. Changes status to `Rejected`.

**Request Body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `remarks` | string | No | Rejection reason (also accepted as `reason`) |

```json
{
  "remarks": "Organization declined due to scope mismatch."
}
```

**Success Response `200`**
```json
{
  "success": true,
  "message": "Article marked as rejected successfully.",
  "data": {
    "article_id": 42,
    "remarks": "Organization declined due to scope mismatch.",
    "new_article_status": "Rejected"
  }
}
```

---

### 10.7 Publish Article

**POST** `/api/publication/articles/<article_id>/publish`  
Content-Type: `multipart/form-data`  
Article must be in `Submitted To Organization` status.

**Form Fields**

| Field | Type | Required | Notes |
|---|---|---|---|
| `publication_data` | JSON string | Yes | See structure below |
| `published_file` | file | Yes | Final published PDF/DOC |

**`publication_data` JSON structure**

| Field | Type | Required | Format |
|---|---|---|---|
| `organization_name` | string | Yes | |
| `doi` | string | Yes | Must start with `10.` and contain `/`, e.g. `10.1234/abc.2024.001` |
| `article_url` | string | Yes | URL to the published article |
| `volume` | string | Yes | e.g. `12` |
| `issue` | string | Yes | e.g. `3` |
| `pages` | string | Yes | e.g. `45-58` |
| `publication_date` | string | Yes | `YYYY-MM-DD` format |

```json
{
  "organization_name": "IEEE Xplore Digital Library",
  "doi": "10.1109/TPAMI.2024.001234",
  "article_url": "https://ieeexplore.ieee.org/document/1234567",
  "volume": "46",
  "issue": "3",
  "pages": "1024-1038",
  "publication_date": "2024-12-01"
}
```

**Example — cURL**
```bash
curl -X POST http://localhost:5000/api/publication/articles/42/publish \
  -H "Authorization: Bearer <token>" \
  -F 'publication_data={"organization_name":"IEEE Xplore","doi":"10.1109/TPAMI.2024.001234","article_url":"https://ieeexplore.ieee.org/document/1234567","volume":"46","issue":"3","pages":"1024-1038","publication_date":"2024-12-01"}' \
  -F "published_file=@/path/to/published_paper.pdf"
```

**Success Response `201`**
```json
{
  "success": true,
  "message": "Article published successfully.",
  "data": {
    "publication_id": 3,
    "article_id": 42,
    "organization_name": "IEEE Xplore Digital Library",
    "doi": "10.1109/TPAMI.2024.001234",
    "article_url": "https://ieeexplore.ieee.org/document/1234567",
    "published_file_name": "published_paper.pdf",
    "published_file_path": "42/published_paper.pdf",
    "new_article_status": "Published"
  }
}
```

**Error Responses**

| Status | Scenario |
|---|---|
| `400` | Article not in `Submitted To Organization` status; missing required fields; invalid DOI format; invalid date format |
| `400` | Missing `published_file` |
| `409` | Article already has a publication record; DOI already used; URL already used |

---

### 10.8 List Published Articles

**GET** `/api/publication/published`

**Success Response `200`**
```json
{
  "success": true,
  "message": "Retrieved 6 published article(s).",
  "data": {
    "publications": [
      {
        "publication_id": 3,
        "article_id": 42,
        "title": "Deep Learning Applications in Medical Imaging",
        "organization_name": "IEEE Xplore Digital Library",
        "doi": "10.1109/TPAMI.2024.001234",
        "article_url": "https://ieeexplore.ieee.org/document/1234567",
        "volume": "46",
        "issue": "3",
        "pages": "1024-1038",
        "publication_date": "2024-12-01",
        "published_file_name": "published_paper.pdf",
        "published_file_path": "42/published_paper.pdf",
        "published_file_type": "application/pdf",
        "author_name": "Jane Doe"
      }
    ],
    "total_count": 6,
    "viewer": {
      "publication_team_id": 1,
      "name": "Tom Jones"
    }
  }
}
```

---

### 10.9 Get Published Article

**GET** `/api/publication/published/<article_id>`

Returns full publication details including article metadata, author, and file path.

---

## 11. Health Check

**GET** `/health`  
Public — no authentication required.

**Success Response `200`**
```json
{
  "success": true,
  "message": "IJFINK backend is running."
}
```

---

## 12. Article Status Flow

```
Submitted
    │
    ├─[Admin Screening: Approved]──► Admin Approved
    │                                      │
    └─[Admin Screening: Rejected]──► Rejected        [Admin assigns editor]
                                           │
                                    Editorial Review
                                           │
                    ┌──────────────────────┤
                    │                      │                        │
             [Accepted]          [Minor/Major Revision]       [Rejected]
                    │                      │
                Accepted          Revision Requested
                    │                      │
        [Pub Team starts]        [Author submits revision]
                    │                      │
          Publication Review       Editorial Review (loop)
                    │
         ┌──────────┤
         │          │
   [Return to    [Submit to Org]
    Editor]            │
         │     Submitted To Organization
    Editorial          │
    Review      ┌──────┤
                │      │
           [Publish]  [Reject]
                │      │
           Published  Rejected
```

---

## 13. Error Reference

### Common HTTP Status Codes

| Code | Meaning |
|---|---|
| `200` | Success |
| `201` | Created |
| `400` | Bad request — validation error or business rule violation |
| `401` | Unauthenticated — missing or invalid JWT |
| `403` | Forbidden — authenticated but wrong role or insufficient permission |
| `404` | Resource not found |
| `409` | Conflict — duplicate entry or state conflict |
| `422` | Unprocessable entity — valid format but invalid value (e.g. unknown decision) |
| `500` | Server or database error |

### Common Error Response Shape

```json
{
  "success": false,
  "message": "Human-readable error description."
}
```

### Token Notes

- Tokens are custom HS256 JWTs.
- **12-hour expiry** by default; **30-day expiry** if `remember_me: true`.
- Pass the token as: `Authorization: Bearer <token>`
- A token becomes invalid if the user's account is deactivated, or if the role stored in the token no longer matches the database.
