from mysql.connector import Error as MySQLError

from database import get_db_connection
from app.controllers.auth_controller import AuthController


class ChiefEditorController:
    @staticmethod
    def dashboard(secret_key, authorization_header):
        actor, profile, error = ChiefEditorController._require_chief_editor(secret_key, authorization_header)
        if error:
            return error
        connection = None
        try:
            connection = get_db_connection()
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT COUNT(*) AS total FROM editorial_assignment")
                total_assigned_articles = cursor.fetchone()["total"]
                cursor.execute("SELECT COUNT(*) AS total FROM editorial_assignment ea JOIN articles a ON a.article_id = ea.article_id WHERE ea.status = 'Active' AND a.status = 'Editorial Review'")
                pending_editorial_reviews = cursor.fetchone()["total"]
                cursor.execute("SELECT COUNT(*) AS total FROM articles WHERE status = 'Revision Requested'")
                revision_requested = cursor.fetchone()["total"]
                cursor.execute("SELECT COUNT(*) AS total FROM articles WHERE status = 'Accepted'")
                accepted = cursor.fetchone()["total"]
                cursor.execute("SELECT COUNT(*) AS total FROM articles WHERE status = 'Rejected'")
                rejected = cursor.fetchone()["total"]
                cursor.execute("SELECT COUNT(*) AS total FROM articles WHERE status = 'Published'")
                published = cursor.fetchone()["total"]
                cursor.execute("SELECT COUNT(*) AS total FROM editors e JOIN users u ON u.user_id = e.user_id WHERE u.status = 'Active' AND e.is_chief_editor = FALSE")
                active_editors = cursor.fetchone()["total"]
                cursor.execute("""
                    SELECT COALESCE(AVG(TIMESTAMPDIFF(MINUTE, ea.assigned_at, er.reviewed_at)), 0) AS avg_minutes
                    FROM editorial_assignment ea
                    JOIN editorial_review er ON er.assignment_id = ea.assignment_id
                """)
                average_review_time = cursor.fetchone()["avg_minutes"]
            return {"success": True, "message": "Dashboard data retrieved successfully.", "data": {
                "total_assigned_articles": total_assigned_articles,
                "pending_editorial_reviews": pending_editorial_reviews,
                "revision_requested": revision_requested,
                "accepted": accepted,
                "rejected": rejected,
                "published": published,
                "active_editors": active_editors,
                "average_review_time": float(average_review_time or 0),
            }}, 200
        except MySQLError as exc:
            return {"success": False, "message": f"Database error: {str(exc)}"}, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def list_articles(secret_key, authorization_header, filters=None):
        actor, profile, error = ChiefEditorController._require_chief_editor(secret_key, authorization_header)
        if error:
            return error
        filters = filters or {}
        search = (filters.get("search") or "").strip()
        status_filter = filters.get("status")
        editor_filter = filters.get("editor_id")
        try:
            page = max(int(filters.get("page", 1)), 1)
            per_page = min(max(int(filters.get("per_page", 10)), 1), 100)
        except (TypeError, ValueError):
            return {"success": False, "message": "page and per_page must be integers."}, 400
        connection = None
        try:
            connection = get_db_connection()
            where = ["1=1"]
            params = []
            if search:
                where.append("(a.title LIKE %s OR a.subject_area LIKE %s OR a.article_type LIKE %s)")
                like = f"%{search}%"
                params.extend([like, like, like])
            if status_filter:
                where.append("a.status = %s")
                params.append(status_filter)
            if editor_filter:
                where.append("ea.editor_id = %s")
                params.append(int(editor_filter))
            count_query = f"SELECT COUNT(*) AS total FROM editorial_assignment ea JOIN articles a ON a.article_id = ea.article_id WHERE {' AND '.join(where)}"
            query = f"""
                SELECT ea.assignment_id, ea.article_id, ea.editor_id, ea.admin_id, ea.status AS assignment_status, ea.assigned_at,
                       a.title, a.article_type, a.subject_area, a.status AS article_status, a.submitted_at, a.updated_at,
                       CONCAT(au.first_name, ' ', au.last_name) AS author_name,
                       CONCAT(ed.first_name, ' ', ed.last_name) AS editor_name, ed.is_chief_editor
                FROM editorial_assignment ea
                JOIN articles a ON a.article_id = ea.article_id
                JOIN authors au ON au.author_id = a.author_id
                JOIN editors ed ON ed.editor_id = ea.editor_id
                WHERE {' AND '.join(where)}
                ORDER BY ea.assigned_at DESC, ea.assignment_id DESC
                LIMIT %s OFFSET %s
            """
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()["total"]
                cursor.execute(query, params + [per_page, (page - 1) * per_page])
                articles = cursor.fetchall()
            return {"success": True, "message": f"Retrieved {len(articles)} article(s).", "data": {"articles": articles, "pagination": {"page": page, "per_page": per_page, "total_count": total_count}}}, 200
        except (MySQLError, ValueError) as exc:
            return {"success": False, "message": f"Database error: {str(exc)}"}, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def get_article(article_id, secret_key, authorization_header):
        actor, profile, error = ChiefEditorController._require_chief_editor(secret_key, authorization_header)
        if error:
            return error
        connection = None
        try:
            connection = get_db_connection()
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute("""
                    SELECT ea.assignment_id, ea.article_id, ea.editor_id, ea.admin_id, ea.status AS assignment_status, ea.assigned_at,
                           a.title, a.abstract, a.keywords, a.article_type, a.subject_area, a.status AS article_status, a.submitted_at, a.updated_at,
                           CONCAT(au.first_name, ' ', au.last_name) AS author_name, au.first_name AS author_first_name, au.last_name AS author_last_name,
                           au.institution AS author_institution, au.orcid AS author_orcid, au.phone_number AS author_phone, u.email AS author_email,
                           CONCAT(ed.first_name, ' ', ed.last_name) AS editor_name, ed.is_chief_editor
                    FROM editorial_assignment ea
                    JOIN articles a ON a.article_id = ea.article_id
                    JOIN authors au ON au.author_id = a.author_id
                    JOIN users u ON u.user_id = au.user_id
                    JOIN editors ed ON ed.editor_id = ea.editor_id
                    WHERE a.article_id = %s
                """, (article_id,))
                article = cursor.fetchone()
                if not article:
                    return {"success": False, "message": "Article not found."}, 404
                cursor.execute("SELECT file_id, file_name, file_type, file_path, version, uploaded_at FROM article_files WHERE article_id = %s ORDER BY file_type ASC, version ASC", (article_id,))
                files = cursor.fetchall()
                cursor.execute("SELECT editorial_review_id, assignment_id, editor_id, decision, comments, reviewed_at FROM editorial_review WHERE assignment_id = %s ORDER BY reviewed_at ASC, editorial_review_id ASC", (article["assignment_id"],))
                review_history = cursor.fetchall()
                cursor.execute("SELECT revision_id, editorial_review_id, revision_number, response_letter, submitted_at FROM revisions WHERE article_id = %s ORDER BY revision_number ASC, revision_id ASC", (article_id,))
                revision_history = cursor.fetchall()
                cursor.execute("SELECT notification_id, title, message, is_read, created_at FROM notifications WHERE article_id = %s ORDER BY created_at DESC, notification_id DESC", (article_id,))
                notifications = cursor.fetchall()
            return {"success": True, "message": "Article retrieved successfully.", "data": {"article": article, "files": files, "review_history": review_history, "revision_history": revision_history, "notifications": notifications, "article_timeline": ChiefEditorController._build_timeline(article, review_history, revision_history)}} , 200
        except MySQLError as exc:
            return {"success": False, "message": f"Database error: {str(exc)}"}, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def list_editors(secret_key, authorization_header):
        actor, profile, error = ChiefEditorController._require_chief_editor(secret_key, authorization_header)
        if error:
            return error
        connection = None
        try:
            connection = get_db_connection()
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute("""
                    SELECT e.editor_id, e.user_id, e.first_name, e.last_name, e.institution, e.is_chief_editor, u.email, u.status
                    FROM editors e JOIN users u ON u.user_id = e.user_id
                    ORDER BY e.is_chief_editor DESC, e.first_name ASC, e.last_name ASC
                """)
                editors = cursor.fetchall()
                for editor in editors:
                    cursor.execute("SELECT COUNT(*) AS total FROM editorial_assignment WHERE editor_id = %s", (editor["editor_id"],))
                    editor["assigned_articles"] = cursor.fetchone()["total"]
                    cursor.execute("SELECT COUNT(*) AS total FROM editorial_review WHERE editor_id = %s", (editor["editor_id"],))
                    editor["completed_reviews"] = cursor.fetchone()["total"]
                    cursor.execute("SELECT COUNT(*) AS total FROM editorial_review WHERE editor_id = %s AND decision = 'Accepted'", (editor["editor_id"],))
                    editor["accepted"] = cursor.fetchone()["total"]
                    cursor.execute("SELECT COUNT(*) AS total FROM editorial_review WHERE editor_id = %s AND decision = 'Rejected'", (editor["editor_id"],))
                    editor["rejected"] = cursor.fetchone()["total"]
                    cursor.execute("SELECT COALESCE(AVG(TIMESTAMPDIFF(MINUTE, ea.assigned_at, er.reviewed_at)), 0) AS avg_minutes FROM editorial_assignment ea JOIN editorial_review er ON er.assignment_id = ea.assignment_id WHERE ea.editor_id = %s", (editor["editor_id"],))
                    editor["average_completion_time"] = float(cursor.fetchone()["avg_minutes"] or 0)
            return {"success": True, "message": f"Retrieved {len(editors)} editor(s).", "data": {"editors": editors}}, 200
        except MySQLError as exc:
            return {"success": False, "message": f"Database error: {str(exc)}"}, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def get_editor(editor_id, secret_key, authorization_header):
        actor, profile, error = ChiefEditorController._require_chief_editor(secret_key, authorization_header)
        if error:
            return error
        connection = None
        try:
            connection = get_db_connection()
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT e.editor_id, e.user_id, e.first_name, e.last_name, e.institution, e.is_chief_editor, u.email, u.status FROM editors e JOIN users u ON u.user_id = e.user_id WHERE e.editor_id = %s", (editor_id,))
                editor = cursor.fetchone()
                if not editor:
                    return {"success": False, "message": "Editor not found."}, 404
                cursor.execute("SELECT COUNT(*) AS total FROM editorial_assignment WHERE editor_id = %s", (editor_id,))
                editor["assigned_articles"] = cursor.fetchone()["total"]
                cursor.execute("SELECT COUNT(*) AS total FROM editorial_review WHERE editor_id = %s", (editor_id,))
                editor["completed_reviews"] = cursor.fetchone()["total"]
                cursor.execute("SELECT COUNT(*) AS total FROM editorial_review WHERE editor_id = %s AND decision = 'Accepted'", (editor_id,))
                editor["accepted"] = cursor.fetchone()["total"]
                cursor.execute("SELECT COUNT(*) AS total FROM editorial_review WHERE editor_id = %s AND decision = 'Rejected'", (editor_id,))
                editor["rejected"] = cursor.fetchone()["total"]
                cursor.execute("SELECT COALESCE(AVG(TIMESTAMPDIFF(MINUTE, ea.assigned_at, er.reviewed_at)), 0) AS avg_minutes FROM editorial_assignment ea JOIN editorial_review er ON er.assignment_id = ea.assignment_id WHERE ea.editor_id = %s", (editor_id,))
                editor["average_completion_time"] = float(cursor.fetchone()["avg_minutes"] or 0)
            return {"success": True, "message": "Editor details retrieved successfully.", "data": {"editor": editor}}, 200
        except MySQLError as exc:
            return {"success": False, "message": f"Database error: {str(exc)}"}, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def pending_reviews(secret_key, authorization_header):
        actor, profile, error = ChiefEditorController._require_chief_editor(secret_key, authorization_header)
        if error:
            return error
        connection = None
        try:
            connection = get_db_connection()
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute("""
                    SELECT ea.assignment_id, ea.article_id, ea.editor_id, ea.status AS assignment_status, ea.assigned_at,
                           a.title, a.status AS article_status, CONCAT(ed.first_name, ' ', ed.last_name) AS editor_name
                    FROM editorial_assignment ea
                    JOIN articles a ON a.article_id = ea.article_id
                    JOIN editors ed ON ed.editor_id = ea.editor_id
                    WHERE ea.status = 'Active' AND a.status = 'Editorial Review'
                    ORDER BY ea.assigned_at ASC
                """)
                rows = cursor.fetchall()
            return {"success": True, "message": f"Retrieved {len(rows)} assignment(s).", "data": {"assignments": rows}}, 200
        except MySQLError as exc:
            return {"success": False, "message": f"Database error: {str(exc)}"}, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def revisions(secret_key, authorization_header):
        actor, profile, error = ChiefEditorController._require_chief_editor(secret_key, authorization_header)
        if error:
            return error
        connection = None
        try:
            connection = get_db_connection()
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute("""
                    SELECT a.article_id, a.title, a.status AS article_status, er.editorial_review_id, er.decision, er.reviewed_at,
                           CONCAT(au.first_name, ' ', au.last_name) AS author_name
                    FROM articles a
                    JOIN authors au ON au.author_id = a.author_id
                    JOIN editorial_assignment ea ON ea.article_id = a.article_id
                    JOIN editorial_review er ON er.assignment_id = ea.assignment_id
                    WHERE a.status = 'Revision Requested' AND er.decision IN ('Minor Revision', 'Major Revision')
                    ORDER BY er.reviewed_at DESC
                """)
                rows = cursor.fetchall()
            return {"success": True, "message": f"Retrieved {len(rows)} article(s).", "data": {"articles": rows}}, 200
        except MySQLError as exc:
            return {"success": False, "message": f"Database error: {str(exc)}"}, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def statistics(secret_key, authorization_header):
        actor, profile, error = ChiefEditorController._require_chief_editor(secret_key, authorization_header)
        if error:
            return error
        connection = None
        try:
            connection = get_db_connection()
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT COUNT(*) AS total FROM editorial_review WHERE decision = 'Accepted'")
                accepted = cursor.fetchone()["total"]
                cursor.execute("SELECT COUNT(*) AS total FROM editorial_review WHERE decision = 'Rejected'")
                rejected = cursor.fetchone()["total"]
                cursor.execute("SELECT COUNT(*) AS total FROM editorial_review WHERE decision IN ('Minor Revision', 'Major Revision')")
                revisions = cursor.fetchone()["total"]
                cursor.execute("SELECT COUNT(*) AS total FROM editorial_review")
                total_reviews = cursor.fetchone()["total"]
                cursor.execute("SELECT COALESCE(AVG(TIMESTAMPDIFF(MINUTE, ea.assigned_at, er.reviewed_at)), 0) AS avg_minutes FROM editorial_assignment ea JOIN editorial_review er ON er.assignment_id = ea.assignment_id")
                average_review_time = float(cursor.fetchone()["avg_minutes"] or 0)
                cursor.execute("""
                    SELECT
                        e.editor_id,
                        e.first_name,
                        e.last_name,
                        e.is_chief_editor,
                        COUNT(DISTINCT ea.assignment_id) AS assigned_articles,
                        SUM(CASE WHEN ea.status = 'Active' THEN 1 ELSE 0 END) AS active_assignments,
                        SUM(CASE WHEN er.editorial_review_id IS NOT NULL THEN 1 ELSE 0 END) AS completed_reviews
                    FROM editors e
                    LEFT JOIN editorial_assignment ea ON ea.editor_id = e.editor_id
                    LEFT JOIN editorial_review er ON er.editor_id = e.editor_id
                    GROUP BY e.editor_id, e.first_name, e.last_name, e.is_chief_editor
                    ORDER BY e.is_chief_editor DESC, e.first_name ASC, e.last_name ASC
                """)
                editor_workload = cursor.fetchall()
            total_reviews = max(total_reviews, 1)
            return {"success": True, "message": "Statistics retrieved successfully.", "data": {
                "acceptance_rate": round((accepted / total_reviews) * 100, 2),
                "rejection_rate": round((rejected / total_reviews) * 100, 2),
                "revision_rate": round((revisions / total_reviews) * 100, 2),
                "average_review_time": average_review_time,
                "editor_workload": editor_workload,
            }}, 200
        except MySQLError as exc:
            return {"success": False, "message": f"Database error: {str(exc)}"}, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def notifications(secret_key, authorization_header):
        actor, profile, error = ChiefEditorController._require_chief_editor(secret_key, authorization_header)
        if error:
            return error
        connection = None
        try:
            connection = get_db_connection()
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT notification_id, user_id, article_id, title, message, is_read, created_at FROM notifications WHERE user_id = %s ORDER BY created_at DESC, notification_id DESC", (actor["user_id"],))
                notifications = cursor.fetchall()
            return {"success": True, "message": f"Retrieved {len(notifications)} notification(s).", "data": {"notifications": notifications}}, 200
        except MySQLError as exc:
            return {"success": False, "message": f"Database error: {str(exc)}"}, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def mark_notification_read(notification_id, secret_key, authorization_header):
        actor, profile, error = ChiefEditorController._require_chief_editor(secret_key, authorization_header)
        if error:
            return error
        connection = None
        try:
            connection = get_db_connection()
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT notification_id, user_id FROM notifications WHERE notification_id = %s", (notification_id,))
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
    def _require_chief_editor(secret_key, authorization_header):
        actor = AuthController._get_authenticated_actor(secret_key, authorization_header)
        if not actor:
            return None, None, ({"success": False, "message": "Authentication failed. Valid JWT token is required."}, 401)
        if actor["role"] != "Editor":
            return None, None, ({"success": False, "message": "Only Chief Editor users can access this endpoint."}, 403)
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
            return None, None, ({"success": False, "message": "Chief editor profile not found for this account."}, 404)
        if not profile["is_chief_editor"]:
            return None, None, ({"success": False, "message": "Only Chief Editor users can access this endpoint."}, 403)
        return actor, profile, None

    @staticmethod
    def _build_timeline(article, reviews, revisions):
        events = [{"event": "Submitted", "at": str(article["submitted_at"])}]
        for review in reviews:
            events.append({"event": f"Review: {review['decision']}", "at": str(review["reviewed_at"])})
        for revision in revisions:
            events.append({"event": f"Revision {revision['revision_number']}", "at": str(revision["submitted_at"])})
        return events

