import json
import os
from datetime import datetime
from pathlib import Path

from mysql.connector import Error as MySQLError
from werkzeug.utils import secure_filename

from database import get_db_connection
from app.controllers.auth_controller import AuthController


class PublicationController:
    """Publication team workflow for accepted articles and final publication records."""

    @staticmethod
    def get_accepted_articles(secret_key, authorization_header):
        actor, profile, error = PublicationController._require_publication_team(
            secret_key,
            authorization_header,
        )
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
                    u.email AS author_email
                FROM articles a
                JOIN authors au ON au.author_id = a.author_id
                JOIN users u ON u.user_id = au.user_id
                WHERE a.status = 'Accepted'
                ORDER BY a.updated_at ASC, a.article_id ASC
            """
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query)
                articles = cursor.fetchall()

            return {
                "success": True,
                "message": f"Retrieved {len(articles)} accepted article(s).",
                "data": {
                    "articles": articles,
                    "total_count": len(articles),
                    "viewer": PublicationController._viewer(profile),
                },
            }, 200
        except MySQLError as exc:
            return PublicationController._db_error(exc)
        finally:
            if connection:
                connection.close()

    @staticmethod
    def get_article_details(article_id, secret_key, authorization_header):
        actor, profile, error = PublicationController._require_publication_team(
            secret_key,
            authorization_header,
        )
        if error:
            return error

        connection = None
        try:
            connection = get_db_connection()
            with connection.cursor(dictionary=True) as cursor:
                article = PublicationController._fetch_article(cursor, article_id)
                if not article:
                    return {
                        "success": False,
                        "message": "Article not found.",
                    }, 404

                cursor.execute(
                    """
                    SELECT co_author_id, full_name, email, institution, orcid, author_order
                    FROM co_authors
                    WHERE article_id = %s
                    ORDER BY author_order ASC, co_author_id ASC
                    """,
                    (article_id,),
                )
                co_authors = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT file_id, file_name, file_type, file_path, version, uploaded_at
                    FROM article_files
                    WHERE article_id = %s
                    ORDER BY file_type ASC, version ASC, file_id ASC
                    """,
                    (article_id,),
                )
                files = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT
                        ea.assignment_id,
                        ea.editor_id,
                        ea.status AS assignment_status,
                        ea.assigned_at,
                        CONCAT(e.first_name, ' ', e.last_name) AS editor_name,
                        eu.email AS editor_email
                    FROM editorial_assignment ea
                    JOIN editors e ON e.editor_id = ea.editor_id
                    JOIN users eu ON eu.user_id = e.user_id
                    WHERE ea.article_id = %s
                    ORDER BY ea.assigned_at DESC, ea.assignment_id DESC
                    """,
                    (article_id,),
                )
                assignments = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT
                        er.editorial_review_id,
                        er.assignment_id,
                        er.editor_id,
                        er.decision,
                        er.comments,
                        er.reviewed_at,
                        CONCAT(e.first_name, ' ', e.last_name) AS editor_name
                    FROM editorial_review er
                    JOIN editorial_assignment ea ON ea.assignment_id = er.assignment_id
                    JOIN editors e ON e.editor_id = er.editor_id
                    WHERE ea.article_id = %s
                    ORDER BY er.reviewed_at DESC, er.editorial_review_id DESC
                    """,
                    (article_id,),
                )
                editorial_reviews = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT
                        publication_id,
                        publication_team_id,
                        organization_name,
                        doi,
                        article_url,
                        volume,
                        issue,
                        pages,
                        publication_date,
                        published_file_name,
                        published_file_path,
                        published_file_type
                    FROM publications
                    WHERE article_id = %s
                    LIMIT 1
                    """,
                    (article_id,),
                )
                publication = cursor.fetchone()

            return {
                "success": True,
                "message": "Article details retrieved successfully.",
                "data": {
                    "article": article,
                    "co_authors": co_authors,
                    "files": files,
                    "editorial_assignments": assignments,
                    "editorial_reviews": editorial_reviews,
                    "publication": publication,
                    "viewer": PublicationController._viewer(profile),
                },
            }, 200
        except MySQLError as exc:
            return PublicationController._db_error(exc)
        finally:
            if connection:
                connection.close()

    @staticmethod
    def start_review(article_id, secret_key, authorization_header):
        actor, profile, error = PublicationController._require_publication_team(
            secret_key,
            authorization_header,
        )
        if error:
            return error

        connection = None
        try:
            connection = get_db_connection()
            connection.start_transaction()
            with connection.cursor(dictionary=True) as cursor:
                article = PublicationController._fetch_article(cursor, article_id)
                if not article:
                    connection.rollback()
                    return {"success": False, "message": "Article not found."}, 404
                if article["status"] != "Accepted":
                    connection.rollback()
                    return {
                        "success": False,
                        "message": "Publication review can start only for articles in 'Accepted' status.",
                    }, 400

                cursor.execute(
                    "UPDATE articles SET status = 'Publication Review' WHERE article_id = %s",
                    (article_id,),
                )
                PublicationController._notify_author(
                    cursor,
                    article_id,
                    "Publication Review Started",
                    "Your article is now under publication team review.",
                )

            connection.commit()
            return {
                "success": True,
                "message": "Publication review started successfully.",
                "data": {
                    "article_id": article_id,
                    "new_article_status": "Publication Review",
                },
            }, 200
        except MySQLError as exc:
            if connection:
                connection.rollback()
            return PublicationController._db_error(exc)
        finally:
            if connection:
                connection.close()

    @staticmethod
    def return_to_editor(article_id, payload, secret_key, authorization_header):
        actor, profile, error = PublicationController._require_publication_team(
            secret_key,
            authorization_header,
        )
        if error:
            return error

        feedback = PublicationController._clean_text(payload.get("feedback") or payload.get("remarks"))
        requested_editor_id = payload.get("editor_id", payload.get("editorId"))
        if not feedback:
            return {
                "success": False,
                "message": "feedback is required when returning an article to the editor.",
            }, 400
        if requested_editor_id is not None:
            try:
                requested_editor_id = int(requested_editor_id)
            except (TypeError, ValueError):
                return {"success": False, "message": "editor_id must be an integer."}, 400

        connection = None
        try:
            connection = get_db_connection()
            connection.start_transaction()
            with connection.cursor(dictionary=True) as cursor:
                article = PublicationController._fetch_article(cursor, article_id)
                if not article:
                    connection.rollback()
                    return {"success": False, "message": "Article not found."}, 404
                if article["status"] != "Publication Review":
                    connection.rollback()
                    return {
                        "success": False,
                        "message": "Article can be returned to editor only from 'Publication Review' status.",
                    }, 400

                assignment = PublicationController._fetch_latest_assignment(cursor, article_id)
                if not assignment:
                    connection.rollback()
                    return {
                        "success": False,
                        "message": "No editorial assignment exists for this article.",
                    }, 400
                if requested_editor_id is not None and requested_editor_id != assignment["editor_id"]:
                    connection.rollback()
                    return {
                        "success": False,
                        "message": "editor_id must match the article's latest assigned editor.",
                    }, 400

                cursor.execute(
                    """
                    UPDATE editorial_assignment
                    SET status = 'Active'
                    WHERE assignment_id = %s
                    """,
                    (assignment["assignment_id"],),
                )
                cursor.execute(
                    "UPDATE articles SET status = 'Editorial Review' WHERE article_id = %s",
                    (article_id,),
                )
                cursor.execute(
                    """
                    INSERT INTO notifications (user_id, article_id, title, message)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        assignment["editor_user_id"],
                        article_id,
                        "Publication Team Feedback",
                        feedback,
                    ),
                )

            connection.commit()
            return {
                "success": True,
                "message": "Article returned to editor successfully.",
                "data": {
                    "article_id": article_id,
                    "assignment_id": assignment["assignment_id"],
                    "editor_id": assignment["editor_id"],
                    "feedback": feedback,
                    "new_article_status": "Editorial Review",
                    "assignment_status": "Active",
                },
            }, 200
        except MySQLError as exc:
            if connection:
                connection.rollback()
            return PublicationController._db_error(exc)
        finally:
            if connection:
                connection.close()

    @staticmethod
    def submit_to_organization(article_id, payload, secret_key, authorization_header):
        actor, profile, error = PublicationController._require_publication_team(
            secret_key,
            authorization_header,
        )
        if error:
            return error

        organization_name = PublicationController._clean_text(
            payload.get("organization_name") or payload.get("organizationName")
        )
        remarks = PublicationController._clean_text(payload.get("remarks"))
        if not organization_name:
            return {"success": False, "message": "organization_name is required."}, 400

        connection = None
        try:
            connection = get_db_connection()
            connection.start_transaction()
            with connection.cursor(dictionary=True) as cursor:
                article = PublicationController._fetch_article(cursor, article_id)
                if not article:
                    connection.rollback()
                    return {"success": False, "message": "Article not found."}, 404
                if article["status"] != "Publication Review":
                    connection.rollback()
                    return {
                        "success": False,
                        "message": "Article can be submitted to an organization only from 'Publication Review' status.",
                    }, 400

                cursor.execute(
                    "UPDATE articles SET status = 'Submitted To Organization' WHERE article_id = %s",
                    (article_id,),
                )
                message = f'Your article has been submitted to {organization_name} for publication.'
                if remarks:
                    message = f"{message} Remarks: {remarks}"
                PublicationController._notify_author(
                    cursor,
                    article_id,
                    "Submitted To Organization",
                    message,
                )

            connection.commit()
            return {
                "success": True,
                "message": "Article submitted to organization successfully.",
                "data": {
                    "article_id": article_id,
                    "organization_name": organization_name,
                    "remarks": remarks,
                    "new_article_status": "Submitted To Organization",
                },
            }, 200
        except MySQLError as exc:
            if connection:
                connection.rollback()
            return PublicationController._db_error(exc)
        finally:
            if connection:
                connection.close()

    @staticmethod
    def reject_article(article_id, payload, secret_key, authorization_header):
        actor, profile, error = PublicationController._require_publication_team(
            secret_key,
            authorization_header,
        )
        if error:
            return error

        remarks = PublicationController._clean_text(payload.get("remarks") or payload.get("reason"))

        connection = None
        try:
            connection = get_db_connection()
            connection.start_transaction()
            with connection.cursor(dictionary=True) as cursor:
                article = PublicationController._fetch_article(cursor, article_id)
                if not article:
                    connection.rollback()
                    return {"success": False, "message": "Article not found."}, 404
                if article["status"] != "Submitted To Organization":
                    connection.rollback()
                    return {
                        "success": False,
                        "message": "Article can be rejected by publication only from 'Submitted To Organization' status.",
                    }, 400

                cursor.execute(
                    "UPDATE articles SET status = 'Rejected' WHERE article_id = %s",
                    (article_id,),
                )
                message = "Your article was rejected by the external publication organization."
                if remarks:
                    message = f"{message} Remarks: {remarks}"
                PublicationController._notify_author(cursor, article_id, "Rejected", message)

            connection.commit()
            return {
                "success": True,
                "message": "Article marked as rejected successfully.",
                "data": {
                    "article_id": article_id,
                    "remarks": remarks,
                    "new_article_status": "Rejected",
                },
            }, 200
        except MySQLError as exc:
            if connection:
                connection.rollback()
            return PublicationController._db_error(exc)
        finally:
            if connection:
                connection.close()

    @staticmethod
    def publish_article(article_id, form_data, files_data, secret_key, authorization_header, published_root):
        actor, profile, error = PublicationController._require_publication_team(
            secret_key,
            authorization_header,
        )
        if error:
            return error

        payload, parse_error = PublicationController._parse_publication_payload(form_data)
        if parse_error:
            return parse_error

        publication_fields, validation_error = PublicationController._validate_publication_payload(payload)
        if validation_error:
            return validation_error

        published_file = files_data.get("published_file")
        if not published_file or not published_file.filename:
            return {
                "success": False,
                "message": "published_file is required.",
            }, 400

        saved_file_path = None
        connection = None
        try:
            connection = get_db_connection()
            connection.start_transaction()
            with connection.cursor(dictionary=True) as cursor:
                article = PublicationController._fetch_article(cursor, article_id)
                if not article:
                    connection.rollback()
                    return {"success": False, "message": "Article not found."}, 404
                if article["status"] != "Submitted To Organization":
                    connection.rollback()
                    return {
                        "success": False,
                        "message": "Article can be published only from 'Submitted To Organization' status.",
                    }, 400

                cursor.execute(
                    "SELECT publication_id FROM publications WHERE article_id = %s",
                    (article_id,),
                )
                if cursor.fetchone():
                    connection.rollback()
                    return {
                        "success": False,
                        "message": "This article already has a publication record.",
                    }, 409

                file_name, relative_path, absolute_path = PublicationController._build_published_file_paths(
                    published_root,
                    article_id,
                    published_file.filename,
                )
                os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
                published_file.save(absolute_path)
                saved_file_path = absolute_path

                cursor.execute(
                    """
                    INSERT INTO publications (
                        article_id,
                        publication_team_id,
                        organization_name,
                        doi,
                        article_url,
                        volume,
                        issue,
                        pages,
                        publication_date,
                        published_file_name,
                        published_file_path,
                        published_file_type
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        article_id,
                        profile["publication_team_id"],
                        publication_fields["organization_name"],
                        publication_fields["doi"],
                        publication_fields["article_url"],
                        publication_fields["volume"],
                        publication_fields["issue"],
                        publication_fields["pages"],
                        publication_fields["publication_date"],
                        file_name,
                        relative_path,
                        published_file.mimetype or None,
                    ),
                )
                publication_id = cursor.lastrowid

            connection.commit()
            return {
                "success": True,
                "message": "Article published successfully.",
                "data": {
                    "publication_id": publication_id,
                    "article_id": article_id,
                    "organization_name": publication_fields["organization_name"],
                    "doi": publication_fields["doi"],
                    "article_url": publication_fields["article_url"],
                    "published_file_name": file_name,
                    "published_file_path": relative_path,
                    "new_article_status": "Published",
                },
            }, 201
        except MySQLError as exc:
            if connection:
                connection.rollback()
            PublicationController._cleanup_file(saved_file_path, published_root)
            return PublicationController._map_publication_db_error(exc)
        except Exception:
            if connection:
                connection.rollback()
            PublicationController._cleanup_file(saved_file_path, published_root)
            return {
                "success": False,
                "message": "Unexpected error while publishing article.",
            }, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def get_published_articles(secret_key, authorization_header):
        actor, profile, error = PublicationController._require_publication_team(
            secret_key,
            authorization_header,
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
                        p.publication_id,
                        p.article_id,
                        a.title,
                        p.organization_name,
                        p.doi,
                        p.article_url,
                        p.volume,
                        p.issue,
                        p.pages,
                        p.publication_date,
                        p.published_file_name,
                        p.published_file_path,
                        p.published_file_type,
                        CONCAT(au.first_name, ' ', au.last_name) AS author_name
                    FROM publications p
                    JOIN articles a ON a.article_id = p.article_id
                    JOIN authors au ON au.author_id = a.author_id
                    ORDER BY p.publication_date DESC, p.publication_id DESC
                    """
                )
                publications = cursor.fetchall()

            return {
                "success": True,
                "message": f"Retrieved {len(publications)} published article(s).",
                "data": {
                    "publications": publications,
                    "total_count": len(publications),
                    "viewer": PublicationController._viewer(profile),
                },
            }, 200
        except MySQLError as exc:
            return PublicationController._db_error(exc)
        finally:
            if connection:
                connection.close()

    @staticmethod
    def get_published_article(article_id, secret_key, authorization_header):
        actor, profile, error = PublicationController._require_publication_team(
            secret_key,
            authorization_header,
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
                        p.publication_id,
                        p.article_id,
                        a.title,
                        a.abstract,
                        a.keywords,
                        a.article_type,
                        a.subject_area,
                        a.status,
                        p.organization_name,
                        p.doi,
                        p.article_url,
                        p.volume,
                        p.issue,
                        p.pages,
                        p.publication_date,
                        p.published_file_name,
                        p.published_file_path,
                        p.published_file_type,
                        CONCAT(au.first_name, ' ', au.last_name) AS author_name,
                        u.email AS author_email
                    FROM publications p
                    JOIN articles a ON a.article_id = p.article_id
                    JOIN authors au ON au.author_id = a.author_id
                    JOIN users u ON u.user_id = au.user_id
                    WHERE p.article_id = %s
                    LIMIT 1
                    """,
                    (article_id,),
                )
                publication = cursor.fetchone()

            if not publication:
                return {
                    "success": False,
                    "message": "Published article not found.",
                }, 404

            return {
                "success": True,
                "message": "Published article retrieved successfully.",
                "data": {
                    "publication": publication,
                    "viewer": PublicationController._viewer(profile),
                },
            }, 200
        except MySQLError as exc:
            return PublicationController._db_error(exc)
        finally:
            if connection:
                connection.close()

    @staticmethod
    def _require_publication_team(secret_key, authorization_header):
        actor = AuthController._get_authenticated_actor(secret_key, authorization_header)
        if not actor:
            return None, None, ({
                "success": False,
                "message": "Authentication failed. Valid JWT token is required.",
            }, 401)
        if actor["role"] != "Publication Team":
            return actor, None, ({
                "success": False,
                "message": "Only Publication Team users can access publication endpoints.",
            }, 403)

        connection = None
        try:
            connection = get_db_connection()
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """
                    SELECT publication_team_id, user_id, first_name, last_name
                    FROM publication_team
                    WHERE user_id = %s
                    LIMIT 1
                    """,
                    (actor["user_id"],),
                )
                profile = cursor.fetchone()
        finally:
            if connection:
                connection.close()

        if not profile:
            return actor, None, ({
                "success": False,
                "message": "Publication Team profile not found for this account.",
            }, 404)

        return actor, profile, None

    @staticmethod
    def _fetch_article(cursor, article_id):
        cursor.execute(
            """
            SELECT
                a.article_id,
                a.author_id,
                a.title,
                a.abstract,
                a.keywords,
                a.article_type,
                a.subject_area,
                a.status,
                a.submitted_at,
                a.updated_at,
                au.first_name AS author_first_name,
                au.last_name AS author_last_name,
                au.institution AS author_institution,
                u.email AS author_email
            FROM articles a
            JOIN authors au ON au.author_id = a.author_id
            JOIN users u ON u.user_id = au.user_id
            WHERE a.article_id = %s
            LIMIT 1
            """,
            (article_id,),
        )
        return cursor.fetchone()

    @staticmethod
    def _fetch_latest_assignment(cursor, article_id):
        cursor.execute(
            """
            SELECT
                ea.assignment_id,
                ea.editor_id,
                ea.status,
                e.user_id AS editor_user_id
            FROM editorial_assignment ea
            JOIN editors e ON e.editor_id = ea.editor_id
            WHERE ea.article_id = %s
            ORDER BY ea.assigned_at DESC, ea.assignment_id DESC
            LIMIT 1
            """,
            (article_id,),
        )
        return cursor.fetchone()

    @staticmethod
    def _notify_author(cursor, article_id, title, message):
        cursor.execute(
            """
            INSERT INTO notifications (user_id, article_id, title, message)
            SELECT au.user_id, a.article_id, %s, %s
            FROM articles a
            JOIN authors au ON au.author_id = a.author_id
            WHERE a.article_id = %s
            """,
            (title, message, article_id),
        )

    @staticmethod
    def _parse_publication_payload(form_data):
        raw_payload = form_data.get("publication_data")
        if raw_payload is None:
            raw_payload = form_data.get("publication") or form_data.get("payload")

        if raw_payload is None:
            payload = {key: value for key, value in form_data.items()}
            if payload:
                return payload, None
            return None, ({
                "success": False,
                "message": "publication_data form field with JSON payload is required.",
            }, 400)

        try:
            payload = json.loads(raw_payload)
        except (TypeError, json.JSONDecodeError):
            return None, ({
                "success": False,
                "message": "publication_data must contain valid JSON.",
            }, 400)

        if not isinstance(payload, dict):
            return None, ({
                "success": False,
                "message": "publication_data must contain a JSON object.",
            }, 400)
        return payload, None

    @staticmethod
    def _validate_publication_payload(payload):
        fields = {
            "organization_name": PublicationController._clean_text(
                payload.get("organization_name") or payload.get("organizationName")
            ),
            "doi": PublicationController._clean_text(payload.get("doi")),
            "article_url": PublicationController._clean_text(payload.get("article_url") or payload.get("articleUrl")),
            "volume": PublicationController._clean_text(payload.get("volume")),
            "issue": PublicationController._clean_text(payload.get("issue")),
            "pages": PublicationController._clean_text(payload.get("pages")),
            "publication_date": PublicationController._clean_text(
                payload.get("publication_date") or payload.get("publicationDate")
            ),
        }

        missing = [key for key, value in fields.items() if not value]
        if missing:
            return None, ({
                "success": False,
                "message": f"Missing required publication field(s): {', '.join(missing)}.",
            }, 400)

        if not fields["doi"].startswith("10.") or "/" not in fields["doi"]:
            return None, ({
                "success": False,
                "message": "doi must follow the expected DOI format, for example '10.xxxx/yyyy'.",
            }, 400)

        try:
            datetime.strptime(fields["publication_date"], "%Y-%m-%d")
        except ValueError:
            return None, ({
                "success": False,
                "message": "publication_date must be in YYYY-MM-DD format.",
            }, 400)

        return fields, None

    @staticmethod
    def _build_published_file_paths(published_root, article_id, original_filename):
        safe_filename = secure_filename(original_filename or "")
        if not safe_filename:
            safe_filename = "published_file"

        path_parts = [str(article_id), safe_filename]
        relative_path = "/".join(path_parts)
        absolute_path = os.path.join(published_root, *path_parts)
        return safe_filename, relative_path, absolute_path

    @staticmethod
    def _cleanup_file(file_path, published_root):
        if not file_path:
            return
        try:
            root_path = Path(published_root).resolve()
            file_path_obj = Path(file_path).resolve()
            if file_path_obj.exists() and root_path in file_path_obj.parents:
                file_path_obj.unlink()
        except OSError:
            return

    @staticmethod
    def _map_publication_db_error(exc):
        message = str(exc)
        if getattr(exc, "errno", None) == 1062:
            if "uq_publications_article" in message:
                return {"success": False, "message": "This article already has a publication record."}, 409
            if "uq_publications_doi" in message:
                return {"success": False, "message": "This DOI is already used."}, 409
            if "uq_publications_article_url" in message:
                return {"success": False, "message": "This article URL is already used."}, 409
        if "Only articles submitted to an organization can be published" in message:
            return {"success": False, "message": "Only articles submitted to an organization can be published."}, 400
        return PublicationController._db_error(exc)

    @staticmethod
    def _db_error(exc):
        return {
            "success": False,
            "message": f"Database error: {str(exc)}",
        }, 500

    @staticmethod
    def _viewer(profile):
        return {
            "publication_team_id": profile["publication_team_id"],
            "name": f"{profile['first_name']} {profile['last_name']}".strip(),
        }

    @staticmethod
    def _clean_text(value):
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None
