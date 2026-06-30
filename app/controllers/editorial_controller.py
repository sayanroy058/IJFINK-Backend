from mysql.connector import Error as MySQLError

from database import get_db_connection
from app.controllers.auth_controller import AuthController


class EditorialController:
    """
    Editorial assignment management.

    Flow:
      - Admin lists admin-approved articles awaiting editor assignment.
      - Admin assigns one of those articles to a specific editor.
      - The assigned editor (and the chief editor) can view the assignment.
      - No other editor can see the assignment or article details through this module.
    """

    # ---------------- Admin operations ----------------

    @staticmethod
    def get_assignable_articles(secret_key, authorization_header):
        """List articles that passed admin screening and have no active editor assignment."""
        actor, error = EditorialController._require_admin(secret_key, authorization_header)
        if error:
            return error

        connection = None
        try:
            connection = get_db_connection()

            query = """
                SELECT
                    a.article_id,
                    a.title,
                    a.article_type,
                    a.subject_area,
                    a.status,
                    a.submitted_at,
                    a.updated_at,
                    CONCAT(au.first_name, ' ', au.last_name) AS author_name,
                    u.email AS author_email,
                    s.screening_id,
                    s.screened_at,
                    s.remarks AS screening_remarks
                FROM articles a
                JOIN authors au ON au.author_id = a.author_id
                JOIN users u ON u.user_id = au.user_id
                JOIN admin_screening s ON s.article_id = a.article_id
                LEFT JOIN editorial_assignment ea
                    ON ea.article_id = a.article_id
                   AND ea.status = 'Active'
                WHERE a.status = 'Admin Approved'
                  AND s.decision = 'Approved'
                  AND ea.assignment_id IS NULL
                ORDER BY s.screened_at ASC
            """

            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query)
                articles = cursor.fetchall()

            return {
                "success": True,
                "message": f"Retrieved {len(articles)} article(s) awaiting editor assignment.",
                "data": {
                    "articles": articles,
                    "total_count": len(articles),
                },
            }, 200
        except MySQLError as exc:
            return {
                "success": False,
                "message": f"Database error: {str(exc)}",
            }, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def get_assignable_editors(secret_key, authorization_header):
        """List active editors who can receive an assignment (chief editor excluded)."""
        actor, error = EditorialController._require_admin(secret_key, authorization_header)
        if error:
            return error

        connection = None
        try:
            connection = get_db_connection()

            query = """
                SELECT
                    e.editor_id,
                    e.first_name,
                    e.last_name,
                    e.institution,
                    e.is_chief_editor,
                    u.user_id,
                    u.email,
                    u.status
                FROM editors e
                JOIN users u ON u.user_id = e.user_id
                WHERE u.status = 'Active'
                  AND e.is_chief_editor = FALSE
                ORDER BY e.first_name ASC, e.last_name ASC
            """

            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query)
                editors = cursor.fetchall()

            return {
                "success": True,
                "message": f"Retrieved {len(editors)} assignable editor(s).",
                "data": {
                    "editors": editors,
                    "total_count": len(editors),
                },
            }, 200
        except MySQLError as exc:
            return {
                "success": False,
                "message": f"Database error: {str(exc)}",
            }, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def assign_editor(payload, secret_key, authorization_header):
        """
        Assign an editor to an admin-approved article.

        Requirements enforced here (and at the DB trigger level):
          - Caller is an active Admin
          - Article exists, has admin_screening.decision = 'Approved',
            and articles.status = 'Admin Approved'
          - Editor exists, is Active, and is not the chief editor
          - No existing Active editorial_assignment for this article
        """
        actor, error = EditorialController._require_admin(secret_key, authorization_header)
        if error:
            return error

        article_id = payload.get("article_id")
        editor_id = payload.get("editor_id")

        try:
            article_id = int(article_id)
            editor_id = int(editor_id)
        except (TypeError, ValueError):
            return {
                "success": False,
                "message": "article_id and editor_id are required and must be integers.",
            }, 400

        connection = None
        try:
            connection = get_db_connection()
            connection.start_transaction()

            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    "SELECT article_id, status FROM articles WHERE article_id = %s",
                    (article_id,),
                )
                article = cursor.fetchone()
                if not article:
                    connection.rollback()
                    return {
                        "success": False,
                        "message": "Article not found.",
                    }, 404

                cursor.execute(
                    "SELECT decision FROM admin_screening WHERE article_id = %s",
                    (article_id,),
                )
                screening = cursor.fetchone()
                if not screening:
                    connection.rollback()
                    return {
                        "success": False,
                        "message": "Article has not been screened by an admin yet.",
                    }, 400

                if screening["decision"] != "Approved":
                    connection.rollback()
                    return {
                        "success": False,
                        "message": (
                            "Editor can be assigned only when the admin screening "
                            "decision is 'Approved'."
                        ),
                    }, 403

                cursor.execute(
                    """
                    SELECT assignment_id
                    FROM editorial_assignment
                    WHERE article_id = %s AND status = 'Active'
                    """,
                    (article_id,),
                )
                if cursor.fetchone():
                    connection.rollback()
                    return {
                        "success": False,
                        "message": "An active editorial assignment already exists for this article.",
                    }, 409

                if article["status"] != "Admin Approved":
                    connection.rollback()
                    return {
                        "success": False,
                        "message": (
                            "Editor assignment is allowed only when the article is in "
                            "'Admin Approved' status."
                        ),
                    }, 400

                cursor.execute(
                    """
                    SELECT e.editor_id, e.is_chief_editor, u.status
                    FROM editors e
                    JOIN users u ON u.user_id = e.user_id
                    WHERE e.editor_id = %s
                    """,
                    (editor_id,),
                )
                editor = cursor.fetchone()
                if not editor:
                    connection.rollback()
                    return {
                        "success": False,
                        "message": "Editor not found.",
                    }, 404

                if editor["status"] != "Active":
                    connection.rollback()
                    return {
                        "success": False,
                        "message": "Editor account is inactive.",
                    }, 400

                if editor["is_chief_editor"]:
                    connection.rollback()
                    return {
                        "success": False,
                        "message": "Chief editor cannot be assigned as the reviewing editor.",
                    }, 400

                cursor.execute(
                    "SELECT admin_id FROM admins WHERE user_id = %s",
                    (actor["user_id"],),
                )
                admin_row = cursor.fetchone()
                if not admin_row:
                    connection.rollback()
                    return {
                        "success": False,
                        "message": "Admin profile not found.",
                    }, 500
                admin_id = admin_row["admin_id"]

                cursor.execute(
                    """
                    INSERT INTO editorial_assignment (article_id, admin_id, editor_id, status)
                    VALUES (%s, %s, %s, 'Active')
                    """,
                    (article_id, admin_id, editor_id),
                )
                assignment_id = cursor.lastrowid

                cursor.execute(
                    """
                    UPDATE articles
                    SET status = 'Editorial Review'
                    WHERE article_id = %s
                    """,
                    (article_id,),
                )


                cursor.execute(
                    "SELECT assigned_at FROM editorial_assignment WHERE assignment_id = %s",
                    (assignment_id,),
                )
                assigned_row = cursor.fetchone()
                assigned_at = assigned_row["assigned_at"] if assigned_row else None

            connection.commit()

            return {
                "success": True,
                "message": "Editor assigned successfully.",
                "data": {
                    "assignment_id": assignment_id,
                    "article_id": article_id,
                    "editor_id": editor_id,
                    "admin_id": admin_id,
                    "status": "Active",
                    "assigned_at": assigned_at.isoformat() if assigned_at else None,
                },
            }, 201

        except MySQLError as exc:
            if connection:
                connection.rollback()
            message = str(exc)
            if "Only one active editorial assignment" in message:
                return {
                    "success": False,
                    "message": "An active editorial assignment already exists for this article.",
                }, 409
            if "after admin approval" in message:
                return {
                    "success": False,
                    "message": "Editor can be assigned only after admin approval.",
                }, 403
            return {
                "success": False,
                "message": f"Database error: {message}",
            }, 500
        finally:
            if connection:
                connection.close()

    # ---------------- Editor-side reads ----------------

    @staticmethod
    def get_assignments(secret_key, authorization_header):
        """
        List assignments visible to the calling editor.

        Chief editor: every assignment.
        Regular editor: only assignments where editor_id matches their profile.
        """
        actor, editor_profile, error = EditorialController._require_editor(
            secret_key, authorization_header
        )
        if error:
            return error

        connection = None
        try:
            connection = get_db_connection()

            base_query = """
                SELECT
                    ea.assignment_id,
                    ea.article_id,
                    ea.editor_id,
                    ea.admin_id,
                    ea.status AS assignment_status,
                    ea.assigned_at,
                    a.title,
                    a.article_type,
                    a.subject_area,
                    a.status AS article_status,
                    a.submitted_at,
                    CONCAT(au.first_name, ' ', au.last_name) AS author_name,
                    CONCAT(e.first_name, ' ', e.last_name) AS editor_name,
                    e.is_chief_editor AS editor_is_chief
                FROM editorial_assignment ea
                JOIN articles a ON a.article_id = ea.article_id
                JOIN authors au ON au.author_id = a.author_id
                JOIN editors e ON e.editor_id = ea.editor_id
            """

            params = []
            if editor_profile["is_chief_editor"]:
                query = base_query + " ORDER BY ea.assigned_at DESC"
            else:
                query = base_query + " WHERE ea.editor_id = %s ORDER BY ea.assigned_at DESC"
                params.append(editor_profile["editor_id"])

            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()

            return {
                "success": True,
                "message": f"Retrieved {len(rows)} assignment(s).",
                "data": {
                    "assignments": rows,
                    "total_count": len(rows),
                    "viewer": {
                        "editor_id": editor_profile["editor_id"],
                        "is_chief_editor": bool(editor_profile["is_chief_editor"]),
                    },
                },
            }, 200
        except MySQLError as exc:
            return {
                "success": False,
                "message": f"Database error: {str(exc)}",
            }, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def get_assignment_details(assignment_id, secret_key, authorization_header):
        """
        Return the full assignment details, including article, co-authors, and files.

        Only the assigned editor or the chief editor may access this resource.
        """
        actor, editor_profile, error = EditorialController._require_editor(
            secret_key, authorization_header
        )
        if error:
            return error

        connection = None
        try:
            connection = get_db_connection()

            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT
                        ea.assignment_id,
                        ea.article_id,
                        ea.editor_id,
                        ea.admin_id,
                        ea.status AS assignment_status,
                        ea.assigned_at
                    FROM editorial_assignment ea
                    WHERE ea.assignment_id = %s
                    """,
                    (assignment_id,),
                )
                assignment = cursor.fetchone()

                if not assignment:
                    return {
                        "success": False,
                        "message": "Assignment not found.",
                    }, 404

                is_chief = bool(editor_profile["is_chief_editor"])
                is_assignee = assignment["editor_id"] == editor_profile["editor_id"]

                if not is_chief and not is_assignee:
                    return {
                        "success": False,
                        "message": "You are not authorized to view this assignment.",
                    }, 403

                cursor.execute(
                    """
                    SELECT
                        a.article_id,
                        a.title,
                        a.abstract,
                        a.keywords,
                        a.article_type,
                        a.subject_area,
                        a.status,
                        a.submitted_at,
                        a.updated_at,
                        au.author_id,
                        au.first_name AS author_first_name,
                        au.last_name AS author_last_name,
                        au.institution AS author_institution,
                        au.orcid AS author_orcid,
                        au.phone_number AS author_phone,
                        u.email AS author_email
                    FROM articles a
                    JOIN authors au ON au.author_id = a.author_id
                    JOIN users u ON u.user_id = au.user_id
                    WHERE a.article_id = %s
                    """,
                    (assignment["article_id"],),
                )
                article = cursor.fetchone()

                cursor.execute(
                    """
                    SELECT co_author_id, full_name, email, institution, orcid, author_order
                    FROM co_authors
                    WHERE article_id = %s
                    ORDER BY author_order ASC
                    """,
                    (assignment["article_id"],),
                )
                co_authors = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT file_id, file_name, file_type, file_path, version, uploaded_at
                    FROM article_files
                    WHERE article_id = %s
                    ORDER BY file_type ASC, version ASC
                    """,
                    (assignment["article_id"],),
                )
                files = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT
                        s.screening_id,
                        s.decision,
                        s.remarks,
                        s.screened_at,
                        CONCAT(ad.first_name, ' ', ad.last_name) AS screened_by
                    FROM admin_screening s
                    JOIN admins ad ON ad.admin_id = s.admin_id
                    WHERE s.article_id = %s
                    """,
                    (assignment["article_id"],),
                )
                screening = cursor.fetchone()

                cursor.execute(
                    """
                    SELECT
                        e.editor_id,
                        e.first_name,
                        e.last_name,
                        e.institution,
                        e.is_chief_editor,
                        u.email
                    FROM editors e
                    JOIN users u ON u.user_id = e.user_id
                    WHERE e.editor_id = %s
                    """,
                    (assignment["editor_id"],),
                )
                assigned_editor = cursor.fetchone()

            return {
                "success": True,
                "message": "Assignment retrieved successfully.",
                "data": {
                    "assignment": assignment,
                    "article": article,
                    "co_authors": co_authors,
                    "files": files,
                    "admin_screening": screening,
                    "assigned_editor": assigned_editor,
                    "viewer": {
                        "editor_id": editor_profile["editor_id"],
                        "is_chief_editor": is_chief,
                        "is_assignee": is_assignee,
                    },
                },
            }, 200
        except MySQLError as exc:
            return {
                "success": False,
                "message": f"Database error: {str(exc)}",
            }, 500
        finally:
            if connection:
                connection.close()

    # ---------------- Helpers ----------------

    @staticmethod
    def _require_admin(secret_key, authorization_header):
        actor = AuthController._get_authenticated_actor(secret_key, authorization_header)
        if not actor:
            return None, ({
                "success": False,
                "message": "Authentication failed. Valid JWT token is required.",
            }, 401)
        if actor["role"] != "Admin":
            return None, ({
                "success": False,
                "message": "Only Admin users can perform this action.",
            }, 403)
        return actor, None

    @staticmethod
    def _require_editor(secret_key, authorization_header):
        """
        Validate the caller is an authenticated Editor and return their editor profile row.
        Returns (actor, editor_profile, error_tuple_or_None).
        """
        actor = AuthController._get_authenticated_actor(secret_key, authorization_header)
        if not actor:
            return None, None, ({
                "success": False,
                "message": "Authentication failed. Valid JWT token is required.",
            }, 401)

        if actor["role"] != "Editor":
            return None, None, ({
                "success": False,
                "message": "Only Editor users can access editorial assignments.",
            }, 403)

        connection = None
        try:
            connection = get_db_connection()
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT editor_id, user_id, first_name, last_name, institution, is_chief_editor
                    FROM editors
                    WHERE user_id = %s
                    """,
                    (actor["user_id"],),
                )
                profile = cursor.fetchone()
        finally:
            if connection:
                connection.close()

        if not profile:
            return None, None, ({
                "success": False,
                "message": "Editor profile not found for this account.",
            }, 404)

        return actor, profile, None

