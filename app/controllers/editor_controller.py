from datetime import datetime
from mysql.connector import Error as MySQLError

from database import get_db_connection
from app.controllers.auth_controller import AuthController


class EditorController:
    @staticmethod
    def dashboard(secret_key, authorization_header):
        actor, editor_profile, error = EditorController._require_editor(secret_key, authorization_header)
        if error:
            return error

        connection = None
        try:
            connection = get_db_connection()
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM editorial_assignment
                    WHERE editor_id = %s
                    """,
                    (editor_profile["editor_id"],),
                )
                assigned_articles = cursor.fetchone()["total"]

                cursor.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM editorial_assignment ea
                    JOIN articles a ON a.article_id = ea.article_id
                    WHERE ea.editor_id = %s AND ea.status = 'Active' AND a.status IN ('Editorial Review', 'Revision Requested')
                    """,
                    (editor_profile["editor_id"],),
                )
                pending_reviews = cursor.fetchone()["total"]

                cursor.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM editorial_review
                    WHERE editor_id = %s
                    """,
                    (editor_profile["editor_id"],),
                )
                completed_reviews = cursor.fetchone()["total"]

                cursor.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM editorial_review er
                    JOIN editorial_assignment ea ON ea.assignment_id = er.assignment_id
                    JOIN articles a ON a.article_id = ea.article_id
                    WHERE er.editor_id = %s AND er.decision IN ('Minor Revision', 'Major Revision')
                    """,
                    (editor_profile["editor_id"],),
                )
                revision_requests = cursor.fetchone()["total"]

                cursor.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM editorial_review
                    WHERE editor_id = %s AND decision = 'Accepted'
                    """,
                    (editor_profile["editor_id"],),
                )
                accepted_articles = cursor.fetchone()["total"]

                cursor.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM editorial_review
                    WHERE editor_id = %s AND decision = 'Rejected'
                    """,
                    (editor_profile["editor_id"],),
                )
                rejected_articles = cursor.fetchone()["total"]

            return {
                "success": True,
                "message": "Dashboard data retrieved successfully.",
                "data": {
                    "assigned_articles": assigned_articles,
                    "pending_reviews": pending_reviews,
                    "completed_reviews": completed_reviews,
                    "revision_requests": revision_requests,
                    "accepted_articles": accepted_articles,
                    "rejected_articles": rejected_articles,
                },
            }, 200
        except MySQLError as exc:
            return {"success": False, "message": f"Database error: {str(exc)}"}, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def list_articles(secret_key, authorization_header, filters=None):
        actor, editor_profile, error = EditorController._require_editor(secret_key, authorization_header)
        if error:
            return error

        filters = filters or {}
        status_filter = filters.get("status")
        search = (filters.get("search") or "").strip()
        sort_by = filters.get("sort_by") or "ea.assigned_at"
        sort_order = (filters.get("sort_order") or "DESC").upper()
        try:
            page = max(int(filters.get("page", 1)), 1)
            per_page = min(max(int(filters.get("per_page", 10)), 1), 100)
        except (TypeError, ValueError):
            return {"success": False, "message": "page and per_page must be integers."}, 400

        allowed_sort_fields = {"ea.assigned_at", "a.title", "a.status", "ea.status"}
        if sort_by not in allowed_sort_fields:
            sort_by = "ea.assigned_at"
        if sort_order not in {"ASC", "DESC"}:
            sort_order = "DESC"

        connection = None
        try:
            connection = get_db_connection()
            params = [editor_profile["editor_id"]]
            where = ["ea.editor_id = %s"]
            if status_filter:
                where.append("a.status = %s")
                params.append(status_filter)
            if search:
                where.append("(a.title LIKE %s OR a.subject_area LIKE %s OR a.article_type LIKE %s)")
                like = f"%{search}%"
                params.extend([like, like, like])

            count_query = f"""
                SELECT COUNT(*) AS total
                FROM editorial_assignment ea
                JOIN articles a ON a.article_id = ea.article_id
                WHERE {' AND '.join(where)}
            """
            query = f"""
                SELECT
                    ea.assignment_id,
                    ea.article_id,
                    ea.editor_id,
                    ea.admin_id,
                    ea.status AS assignment_status,
                    ea.assigned_at,
                    a.title,
                    a.abstract,
                    a.article_type,
                    a.subject_area,
                    a.status AS article_status,
                    a.submitted_at,
                    a.updated_at,
                    CONCAT(au.first_name, ' ', au.last_name) AS author_name
                FROM editorial_assignment ea
                JOIN articles a ON a.article_id = ea.article_id
                JOIN authors au ON au.author_id = a.author_id
                WHERE {' AND '.join(where)}
                ORDER BY {sort_by} {sort_order}, ea.assignment_id DESC
                LIMIT %s OFFSET %s
            """
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()["total"]
                cursor.execute(query, params + [per_page, (page - 1) * per_page])
                articles = cursor.fetchall()

            return {
                "success": True,
                "message": f"Retrieved {len(articles)} article(s).",
                "data": {
                    "articles": articles,
                    "pagination": {"page": page, "per_page": per_page, "total_count": total_count},
                },
            }, 200
        except MySQLError as exc:
            return {"success": False, "message": f"Database error: {str(exc)}"}, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def get_article(article_id, secret_key, authorization_header):
        actor, editor_profile, error = EditorController._require_editor(secret_key, authorization_header)
        if error:
            return error

        connection = None
        try:
            connection = get_db_connection()
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT ea.assignment_id, ea.article_id, ea.editor_id, ea.admin_id, ea.status AS assignment_status, ea.assigned_at,
                           a.title, a.abstract, a.keywords, a.article_type, a.subject_area, a.status AS article_status, a.submitted_at, a.updated_at,
                           CONCAT(au.first_name, ' ', au.last_name) AS author_name, au.first_name AS author_first_name, au.last_name AS author_last_name,
                           au.institution AS author_institution, au.orcid AS author_orcid, au.phone_number AS author_phone, u.email AS author_email
                    FROM editorial_assignment ea
                    JOIN articles a ON a.article_id = ea.article_id
                    JOIN authors au ON au.author_id = a.author_id
                    JOIN users u ON u.user_id = au.user_id
                    WHERE a.article_id = %s
                    """,
                    (article_id,),
                )
                article = cursor.fetchone()
                if not article:
                    return {"success": False, "message": "Article not found."}, 404

                if not editor_profile["is_chief_editor"] and article["editor_id"] != editor_profile["editor_id"]:
                    return {"success": False, "message": "You are not authorized to view this article."}, 403

                cursor.execute(
                    """
                    SELECT file_id, file_name, file_type, file_path, version, uploaded_at
                    FROM article_files
                    WHERE article_id = %s
                    ORDER BY file_type ASC, version ASC
                    """,
                    (article_id,),
                )
                files = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT editorial_review_id, assignment_id, editor_id, decision, comments, reviewed_at
                    FROM editorial_review
                    WHERE assignment_id = %s
                    ORDER BY reviewed_at ASC, editorial_review_id ASC
                    """,
                    (article["assignment_id"],),
                )
                review_history = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT revision_id, editorial_review_id, revision_number, response_letter, submitted_at
                    FROM revisions
                    WHERE article_id = %s
                    ORDER BY revision_number ASC, revision_id ASC
                    """,
                    (article_id,),
                )
                revision_history = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT
                        ea.assignment_id,
                        ea.status AS assignment_status,
                        ea.assigned_at,
                        CONCAT(ad.first_name, ' ', ad.last_name) AS assigned_by
                    FROM editorial_assignment ea
                    JOIN admins ad ON ad.admin_id = ea.admin_id
                    WHERE ea.article_id = %s
                    """,
                    (article_id,),
                )
                assignment_rows = cursor.fetchall()

            return {
                "success": True,
                "message": "Article retrieved successfully.",
                "data": {
                    "article": article,
                    "files": files,
                    "review_history": review_history,
                    "revision_history": revision_history,
                    "assignment_history": assignment_rows,
                    "current_status": article["article_status"],
                },
            }, 200
        except MySQLError as exc:
            return {"success": False, "message": f"Database error: {str(exc)}"}, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def get_files(article_id, secret_key, authorization_header):
        actor, editor_profile, error = EditorController._require_editor(secret_key, authorization_header)
        if error:
            return error
        detail, status = EditorController.get_article(article_id, secret_key, authorization_header)
        if status != 200:
            return detail, status
        return {
            "success": True,
            "message": "Files retrieved successfully.",
            "data": {"files": detail["data"]["files"]},
        }, 200

    @staticmethod
    def submit_review(payload, secret_key, authorization_header):
        actor, editor_profile, error = EditorController._require_editor(secret_key, authorization_header)
        if error:
            return error

        assignment_id = payload.get("assignment_id")
        decision = EditorController._normalize_decision(payload.get("decision"))
        comments = (payload.get("comments") or "").strip()
        if assignment_id is None or not decision:
            return {"success": False, "message": "assignment_id and decision are required."}, 400
        try:
            assignment_id = int(assignment_id)
        except (TypeError, ValueError):
            return {"success": False, "message": "assignment_id must be an integer."}, 400
        if decision not in {"Accepted", "Minor Revision", "Major Revision", "Rejected"}:
            return {"success": False, "message": "Invalid decision."}, 422

        connection = None
        try:
            connection = get_db_connection()
            connection.start_transaction()
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT ea.assignment_id, ea.article_id, ea.editor_id, ea.status AS assignment_status, a.status AS article_status
                    FROM editorial_assignment ea
                    JOIN articles a ON a.article_id = ea.article_id
                    WHERE ea.assignment_id = %s
                    """,
                    (assignment_id,),
                )
                assignment = cursor.fetchone()
                if not assignment:
                    connection.rollback()
                    return {"success": False, "message": "Assignment not found."}, 404
                if not editor_profile["is_chief_editor"] and assignment["editor_id"] != editor_profile["editor_id"]:
                    connection.rollback()
                    return {"success": False, "message": "Assignment belongs to another editor."}, 403
                if assignment["assignment_status"] != "Active":
                    connection.rollback()
                    return {"success": False, "message": "Assignment must be active."}, 409
                if assignment["article_status"] not in {"Editorial Review", "Revision Requested"}:
                    connection.rollback()
                    return {"success": False, "message": "Article is not in a valid review state."}, 409

                cursor.execute(
                    "SELECT editorial_review_id FROM editorial_review WHERE assignment_id = %s ORDER BY reviewed_at DESC, editorial_review_id DESC LIMIT 1",
                    (assignment_id,),
                )
                latest_review = cursor.fetchone()
                if latest_review:
                    cursor.execute(
                        "SELECT editorial_review_id FROM editorial_review WHERE assignment_id = %s AND editorial_review_id > %s",
                        (assignment_id, latest_review["editorial_review_id"]),
                    )

                cursor.execute(
                    """
                    INSERT INTO editorial_review (assignment_id, editor_id, decision, comments)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (assignment_id, editor_profile["editor_id"], decision, comments or None),
                )
                review_id = cursor.lastrowid

                article_id = assignment["article_id"]
                if decision == "Accepted":
                    cursor.execute("UPDATE articles SET status = 'Accepted' WHERE article_id = %s", (article_id,))
                    cursor.execute("UPDATE editorial_assignment SET status = 'Completed' WHERE assignment_id = %s", (assignment_id,))
                    notification_title = "Accepted"
                    notification_message = "Your Article has been accepted for publication."
                elif decision in {"Minor Revision", "Major Revision"}:
                    cursor.execute("UPDATE articles SET status = 'Revision Requested' WHERE article_id = %s", (article_id,))
                    notification_title = "Revision Requested"
                    notification_message = f"Your Article requires {decision}."
                else:
                    cursor.execute("UPDATE articles SET status = 'Rejected' WHERE article_id = %s", (article_id,))
                    cursor.execute("UPDATE editorial_assignment SET status = 'Completed' WHERE assignment_id = %s", (assignment_id,))
                    notification_title = "Rejected"
                    notification_message = "Your Article was rejected after editorial review."

                cursor.execute(
                    """
                    INSERT INTO notifications (user_id, article_id, title, message)
                    SELECT a.user_id, %s, %s, %s
                    FROM articles ar
                    JOIN authors a ON a.author_id = ar.author_id
                    WHERE ar.article_id = %s
                    """,
                    (article_id, notification_title, notification_message, article_id),
                )

                if decision == "Accepted":
                    cursor.execute(
                        """
                        INSERT INTO notifications (user_id, article_id, title, message)
                        SELECT u.user_id, %s, %s, %s
                        FROM users u
                        JOIN publication_team pt ON pt.user_id = u.user_id
                        WHERE u.role = 'Publication Team'
                          AND u.status = 'Active'
                        """,
                        (
                            article_id,
                            "Accepted Article Ready",
                            "An article has been accepted and is ready for publication.",
                        ),
                    )
            connection.commit()
            return {
                "success": True,
                "message": "Editorial review submitted successfully.",
                "data": {"review_id": review_id, "assignment_id": assignment_id, "decision": decision},
            }, 201
        except MySQLError as exc:
            if connection:
                connection.rollback()
            return {"success": False, "message": f"Database error: {str(exc)}"}, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def update_review(review_id, payload, secret_key, authorization_header):
        actor, editor_profile, error = EditorController._require_editor(secret_key, authorization_header)
        if error:
            return error
        comments = payload.get("comments")
        decision = payload.get("decision")
        connection = None
        try:
            connection = get_db_connection()
            connection.start_transaction()
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT er.editorial_review_id, er.assignment_id, er.editor_id, er.decision, ea.article_id, ea.status AS assignment_status, a.status AS article_status
                    FROM editorial_review er
                    JOIN editorial_assignment ea ON ea.assignment_id = er.assignment_id
                    JOIN articles a ON a.article_id = ea.article_id
                    WHERE er.editorial_review_id = %s
                    """,
                    (review_id,),
                )
                review = cursor.fetchone()
                if not review:
                    connection.rollback()
                    return {"success": False, "message": "Review not found."}, 404
                if not editor_profile["is_chief_editor"] and review["editor_id"] != editor_profile["editor_id"]:
                    connection.rollback()
                    return {"success": False, "message": "Review belongs to another editor."}, 403
                if review["assignment_status"] != "Active":
                    connection.rollback()
                    return {"success": False, "message": "Assignment must be active."}, 409
                if review["article_status"] == "Published":
                    connection.rollback()
                    return {"success": False, "message": "Published articles cannot be updated."}, 409
                cursor.execute(
                    "SELECT MAX(editorial_review_id) AS latest_id FROM editorial_review WHERE assignment_id = %s",
                    (review["assignment_id"],),
                )
                latest_id = cursor.fetchone()["latest_id"]
                if latest_id != review_id:
                    connection.rollback()
                    return {"success": False, "message": "A newer review already exists."}, 409
                updates = []
                params = []
                if decision:
                    normalized = EditorController._normalize_decision(decision)
                    if normalized not in {"Accepted", "Minor Revision", "Major Revision", "Rejected"}:
                        connection.rollback()
                        return {"success": False, "message": "Invalid decision."}, 422
                    updates.append("decision = %s")
                    params.append(normalized)
                if comments is not None:
                    updates.append("comments = %s")
                    params.append((comments or "").strip() or None)
                if not updates:
                    connection.rollback()
                    return {"success": False, "message": "No update fields provided."}, 400
                params.append(review_id)
                cursor.execute(f"UPDATE editorial_review SET {', '.join(updates)} WHERE editorial_review_id = %s", params)
            connection.commit()
            return {"success": True, "message": "Review updated successfully.", "data": {"review_id": review_id}}, 200
        except MySQLError as exc:
            if connection:
                connection.rollback()
            return {"success": False, "message": f"Database error: {str(exc)}"}, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def review_history(secret_key, authorization_header):
        actor, editor_profile, error = EditorController._require_editor(secret_key, authorization_header)
        if error:
            return error
        connection = None
        try:
            connection = get_db_connection()
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT er.editorial_review_id, er.assignment_id, er.editor_id, er.decision, er.comments, er.reviewed_at,
                           ea.article_id, a.title, a.status AS article_status
                    FROM editorial_review er
                    JOIN editorial_assignment ea ON ea.assignment_id = er.assignment_id
                    JOIN articles a ON a.article_id = ea.article_id
                    WHERE er.editor_id = %s
                    ORDER BY er.reviewed_at DESC, er.editorial_review_id DESC
                    """,
                    (editor_profile["editor_id"],),
                )
                reviews = cursor.fetchall()
            return {"success": True, "message": f"Retrieved {len(reviews)} review(s).", "data": {"reviews": reviews}}, 200
        except MySQLError as exc:
            return {"success": False, "message": f"Database error: {str(exc)}"}, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def revision_requests(secret_key, authorization_header):
        actor, editor_profile, error = EditorController._require_editor(secret_key, authorization_header)
        if error:
            return error
        connection = None
        try:
            connection = get_db_connection()
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT a.article_id, a.title, a.status AS article_status, er.editorial_review_id, er.decision, er.reviewed_at,
                           CONCAT(au.first_name, ' ', au.last_name) AS author_name
                    FROM articles a
                    JOIN authors au ON au.author_id = a.author_id
                    JOIN editorial_assignment ea ON ea.article_id = a.article_id
                    JOIN editorial_review er ON er.assignment_id = ea.assignment_id
                    WHERE ea.editor_id = %s AND a.status = 'Revision Requested' AND er.decision IN ('Minor Revision', 'Major Revision')
                    ORDER BY er.reviewed_at DESC
                    """,
                    (editor_profile["editor_id"],),
                )
                rows = cursor.fetchall()
            return {"success": True, "message": f"Retrieved {len(rows)} article(s).", "data": {"articles": rows}}, 200
        except MySQLError as exc:
            return {"success": False, "message": f"Database error: {str(exc)}"}, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def notifications(secret_key, authorization_header):
        actor, editor_profile, error = EditorController._require_editor(secret_key, authorization_header)
        if error:
            return error
        connection = None
        try:
            connection = get_db_connection()
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT notification_id, user_id, article_id, title, message, is_read, created_at
                    FROM notifications
                    WHERE user_id = %s
                    ORDER BY created_at DESC, notification_id DESC
                    """,
                    (actor["user_id"],),
                )
                notifications = cursor.fetchall()
            return {"success": True, "message": f"Retrieved {len(notifications)} notification(s).", "data": {"notifications": notifications}}, 200
        except MySQLError as exc:
            return {"success": False, "message": f"Database error: {str(exc)}"}, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def mark_notification_read(notification_id, secret_key, authorization_header):
        actor, editor_profile, error = EditorController._require_editor(secret_key, authorization_header)
        if error:
            return error
        connection = None
        try:
            connection = get_db_connection()
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT notification_id, user_id, is_read FROM notifications WHERE notification_id = %s", (notification_id,))
                notification = cursor.fetchone()
                if not notification:
                    return {"success": False, "message": "Notification not found."}, 404
                if notification["user_id"] != actor["user_id"]:
                    return {"success": False, "message": "Notification belongs to another user."}, 403
                cursor.execute("UPDATE notifications SET is_read = TRUE WHERE notification_id = %s", (notification_id,))
                connection.commit()
            return {"success": True, "message": "Notification marked as read.", "data": {"notification_id": notification_id, "is_read": True}}, 200
        except MySQLError as exc:
            if connection:
                connection.rollback()
            return {"success": False, "message": f"Database error: {str(exc)}"}, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def _require_editor(secret_key, authorization_header):
        actor = AuthController._get_authenticated_actor(secret_key, authorization_header)
        if not actor:
            return None, None, ({"success": False, "message": "Authentication failed. Valid JWT token is required."}, 401)
        if actor["role"] != "Editor":
            return None, None, ({"success": False, "message": "Only Editor users can access this endpoint."}, 403)
        connection = None
        try:
            connection = get_db_connection()
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT editor_id, user_id, first_name, last_name, institution, is_chief_editor FROM editors WHERE user_id = %s", (actor["user_id"],))
                profile = cursor.fetchone()
        finally:
            if connection:
                connection.close()
        if not profile:
            return None, None, ({"success": False, "message": "Editor profile not found for this account."}, 404)
        return actor, profile, None

    @staticmethod
    def _normalize_decision(value):
        if value is None:
            return None
        cleaned = str(value).strip().lower()
        mapping = {
            "accepted": "Accepted",
            "minor revision": "Minor Revision",
            "major revision": "Major Revision",
            "rejected": "Rejected",
        }
        return mapping.get(cleaned)

