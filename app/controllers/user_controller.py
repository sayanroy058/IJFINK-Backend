import json
import os
from pathlib import Path

from mysql.connector import Error as MySQLError
from werkzeug.utils import secure_filename

from database import get_db_connection
from app.controllers.auth_controller import AuthController
from app.models.article_model import ArticleModel


FILE_FIELD_MAP = {
    "main_manuscript": {"file_type": "Main Manuscript", "required": True, "multiple": False},
    "editable_manuscript": {"file_type": "Editable Manuscript", "required": False, "multiple": False},
    "cover_letter": {"file_type": "Cover Letter", "required": False, "multiple": False},
    "video_abstract": {"file_type": "Video Abstract", "required": False, "multiple": False},
    "copyright_form": {"file_type": "Copyright Form", "required": False, "multiple": False},
    "figures": {"file_type": "Figures", "required": False, "multiple": True},
    "supplementary_files": {"file_type": "Supplementary File", "required": False, "multiple": True},
}


class UserController:
    @staticmethod
    def submit_article(form_data, files_data, secret_key, authorization_header, upload_root):
        actor, author_profile, error_response = UserController._authenticate_author(
            secret_key,
            authorization_header,
        )
        if error_response:
            return error_response

        payload, error_response = UserController._parse_json_payload(
            form_data=form_data,
            primary_key="article_data",
            fallback_keys=("article", "payload"),
            allow_form_fallback=True,
        )
        if error_response:
            return error_response

        article_fields, co_authors, validation_error = UserController._validate_article_payload(payload)
        if validation_error:
            return validation_error

        prepared_files, file_error = UserController._collect_submission_files(files_data)
        if file_error:
            return file_error

        connection = None
        saved_file_paths = []

        try:
            connection = get_db_connection()
            connection.start_transaction()

            article_id = ArticleModel.create_article(
                connection=connection,
                author_id=author_profile["author_id"],
                title=article_fields["title"],
                abstract=article_fields["abstract"],
                keywords=article_fields["keywords"],
                article_type=article_fields["article_type"],
                subject_area=article_fields["subject_area"],
            )

            for co_author in co_authors:
                ArticleModel.create_co_author(
                    connection=connection,
                    article_id=article_id,
                    full_name=co_author["full_name"],
                    email=co_author["email"],
                    institution=co_author["institution"],
                    orcid=co_author["orcid"],
                    author_order=co_author["author_order"],
                )

            for prepared_file in prepared_files:
                version = ArticleModel.get_next_file_version(
                    connection=connection,
                    article_id=article_id,
                    file_type=prepared_file["file_type"],
                )
                file_name, relative_path, absolute_path = UserController._build_file_paths(
                    upload_root=upload_root,
                    user_id=actor["user_id"],
                    article_id=article_id,
                    file_type=prepared_file["file_type"],
                    original_filename=prepared_file["storage"].filename,
                )
                os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
                prepared_file["storage"].save(absolute_path)
                saved_file_paths.append(absolute_path)

                ArticleModel.create_article_file(
                    connection=connection,
                    article_id=article_id,
                    file_name=file_name,
                    file_type=prepared_file["file_type"],
                    file_path=relative_path,
                    version=version,
                )

            connection.commit()

            response, status_code = UserController.get_article_details(
                article_id=article_id,
                secret_key=secret_key,
                authorization_header=authorization_header,
                message="Article submitted successfully.",
            )
            return response, 201 if status_code == 200 else status_code
        except MySQLError as exc:
            if connection:
                connection.rollback()
            UserController._cleanup_saved_files(saved_file_paths, upload_root)
            return UserController._map_database_error(exc, "Unable to submit article.")
        except Exception:
            if connection:
                connection.rollback()
            UserController._cleanup_saved_files(saved_file_paths, upload_root)
            return {
                "success": False,
                "message": "Unexpected error while submitting article.",
            }, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def list_articles(secret_key, authorization_header):
        actor, author_profile, error_response = UserController._authenticate_author(
            secret_key,
            authorization_header,
        )
        if error_response:
            return error_response

        try:
            articles = ArticleModel.list_articles_by_author(author_profile["author_id"])
            response_articles = []
            for article in articles:
                response_articles.append(
                    {
                        "article_id": article["article_id"],
                        "title": article["title"],
                        "abstract": article["abstract"],
                        "keywords": UserController._split_keywords(article["keywords"]),
                        "article_type": article["article_type"],
                        "subject_area": article["subject_area"],
                        "status": article["status"],
                        "submitted_at": str(article["submitted_at"]),
                        "updated_at": str(article["updated_at"]),
                    }
                )

            return {
                "success": True,
                "message": f"Retrieved {len(response_articles)} article(s).",
                "data": {
                    "articles": response_articles,
                    "total_count": len(response_articles),
                    "author": {
                        "author_id": author_profile["author_id"],
                        "user_id": actor["user_id"],
                        "name": f"{author_profile['first_name']} {author_profile['last_name']}".strip(),
                    },
                },
            }, 200
        except MySQLError as exc:
            return {
                "success": False,
                "message": f"Database error: {str(exc)}",
            }, 500

    @staticmethod
    def get_article_details(article_id, secret_key, authorization_header, message="Article details retrieved successfully."):
        actor, author_profile, error_response = UserController._authenticate_author(
            secret_key,
            authorization_header,
        )
        if error_response:
            return error_response

        try:
            article = ArticleModel.get_article_by_id(article_id, author_profile["author_id"])
            if not article:
                return {
                    "success": False,
                    "message": f"Article with ID {article_id} not found.",
                }, 404

            return UserController._build_article_detail_response(article, author_profile, actor, message)
        except MySQLError as exc:
            return {
                "success": False,
                "message": f"Database error: {str(exc)}",
            }, 500

    @staticmethod
    def submit_revision(article_id, form_data, files_data, secret_key, authorization_header, upload_root):
        actor, author_profile, error_response = UserController._authenticate_author(
            secret_key,
            authorization_header,
        )
        if error_response:
            return error_response

        payload, error_response = UserController._parse_json_payload(
            form_data=form_data,
            primary_key="revision_data",
            fallback_keys=("revision", "payload"),
            allow_form_fallback=True,
        )
        if error_response:
            return error_response

        revision_fields, validation_error = UserController._validate_revision_payload(payload)
        if validation_error:
            return validation_error

        revision_file = files_data.get("revision_file")
        if not revision_file or not revision_file.filename:
            return {
                "success": False,
                "message": "Revision file is required.",
            }, 400

        connection = None
        saved_file_paths = []

        try:
            connection = get_db_connection()
            connection.start_transaction()

            article = ArticleModel.get_article_by_id(article_id, author_profile["author_id"], connection=connection)
            if not article:
                return {
                    "success": False,
                    "message": f"Article with ID {article_id} not found.",
                }, 404

            if article["status"] != "Revision Requested":
                return {
                    "success": False,
                    "message": "Revision can be submitted only when the article status is 'Revision Requested'.",
                }, 400

            editorial_review = ArticleModel.get_editorial_review_for_revision(
                connection=connection,
                article_id=article_id,
                editorial_review_id=revision_fields["editorial_review_id"],
            )
            if not editorial_review:
                return {
                    "success": False,
                    "message": "Editorial review not found for this article.",
                }, 404

            if editorial_review["decision"] not in {"Minor Revision", "Major Revision"}:
                return {
                    "success": False,
                    "message": "Revision is allowed only for Minor Revision or Major Revision decisions.",
                }, 400

            revision_number = ArticleModel.get_next_revision_number(connection, article_id)
            revision_id = ArticleModel.create_revision(
                connection=connection,
                article_id=article_id,
                editorial_review_id=revision_fields["editorial_review_id"],
                author_id=author_profile["author_id"],
                revision_number=revision_number,
                response_letter=revision_fields["response_letter"],
            )

            file_version = ArticleModel.get_next_file_version(connection, article_id, "Revision File")
            file_name, relative_path, absolute_path = UserController._build_file_paths(
                upload_root=upload_root,
                user_id=actor["user_id"],
                article_id=article_id,
                file_type="Revision File",
                original_filename=revision_file.filename,
            )
            os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
            revision_file.save(absolute_path)
            saved_file_paths.append(absolute_path)

            ArticleModel.create_article_file(
                connection=connection,
                article_id=article_id,
                file_name=file_name,
                file_type="Revision File",
                file_path=relative_path,
                version=file_version,
            )

            connection.commit()

            response, status_code = UserController.get_article_details(
                article_id=article_id,
                secret_key=secret_key,
                authorization_header=authorization_header,
                message="Revision submitted successfully.",
            )
            if status_code == 200:
                response["data"]["revision"] = {
                    "revision_id": revision_id,
                    "editorial_review_id": revision_fields["editorial_review_id"],
                    "revision_number": revision_number,
                    "response_letter": revision_fields["response_letter"],
                    "file_name": file_name,
                    "file_path": relative_path,
                    "file_version": file_version,
                }
            return response, 201 if status_code == 200 else status_code
        except MySQLError as exc:
            if connection:
                connection.rollback()
            UserController._cleanup_saved_files(saved_file_paths, upload_root)
            return UserController._map_database_error(exc, "Unable to submit revision.")
        except Exception:
            if connection:
                connection.rollback()
            UserController._cleanup_saved_files(saved_file_paths, upload_root)
            return {
                "success": False,
                "message": "Unexpected error while submitting revision.",
            }, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def _authenticate_author(secret_key, authorization_header):
        actor = AuthController._get_authenticated_actor(secret_key, authorization_header)
        if not actor:
            return None, None, ({
                "success": False,
                "message": "Authentication failed. Valid JWT token is required.",
            }, 401)

        if actor["role"] != "Author":
            return actor, None, ({
                "success": False,
                "message": "Only Author users can access this endpoint.",
            }, 403)

        author_profile = ArticleModel.get_author_by_user_id(actor["user_id"])
        if not author_profile:
            return actor, None, ({
                "success": False,
                "message": "Author profile not found for this account.",
            }, 404)

        return actor, author_profile, None

    @staticmethod
    def _parse_json_payload(form_data, primary_key, fallback_keys=(), allow_form_fallback=False):
        raw_payload = form_data.get(primary_key)
        if raw_payload is None:
            for key in fallback_keys:
                raw_payload = form_data.get(key)
                if raw_payload is not None:
                    break

        if raw_payload is None and allow_form_fallback:
            payload = {key: value for key, value in form_data.items()}
            if payload:
                return payload, None

        if raw_payload is None:
            return None, ({
                "success": False,
                "message": f"Form field '{primary_key}' with JSON payload is required.",
            }, 400)

        try:
            payload = json.loads(raw_payload)
        except (TypeError, json.JSONDecodeError):
            return None, ({
                "success": False,
                "message": f"Form field '{primary_key}' must contain valid JSON.",
            }, 400)

        if not isinstance(payload, dict):
            return None, ({
                "success": False,
                "message": f"Form field '{primary_key}' must contain a JSON object.",
            }, 400)

        return payload, None

    @staticmethod
    def _validate_article_payload(payload):
        title = UserController._clean_text(payload.get("title"))
        abstract = UserController._clean_text(payload.get("abstract"))
        keywords = payload.get("keywords")
        article_type = UserController._clean_text(payload.get("article_type") or payload.get("articleType"))
        subject_area = UserController._clean_text(payload.get("subject_area") or payload.get("subjectArea"))

        if not title or not abstract or not article_type or not subject_area:
            return None, None, ({
                "success": False,
                "message": "Title, abstract, article type, and subject area are required.",
            }, 400)

        formatted_keywords = UserController._normalize_keywords(keywords)
        co_authors_payload = payload.get("co_authors", payload.get("coAuthors", []))
        if isinstance(co_authors_payload, str):
            try:
                co_authors_payload = json.loads(co_authors_payload)
            except json.JSONDecodeError:
                return None, None, ({
                    "success": False,
                    "message": "co_authors must be valid JSON when sent as text.",
                }, 400)

        if co_authors_payload is None:
            co_authors_payload = []

        if not isinstance(co_authors_payload, list):
            return None, None, ({
                "success": False,
                "message": "co_authors must be an array.",
            }, 400)

        co_authors = []
        seen_orders = set()
        seen_emails = set()

        for index, item in enumerate(co_authors_payload, start=1):
            if not isinstance(item, dict):
                return None, None, ({
                    "success": False,
                    "message": f"Co-author #{index} must be an object.",
                }, 400)

            full_name = UserController._clean_text(item.get("full_name") or item.get("fullName"))
            email = UserController._clean_text(item.get("email"), lower=True)
            institution = UserController._clean_text(item.get("institution"))
            orcid = UserController._clean_text(item.get("orcid"))
            author_order = item.get("author_order", item.get("authorOrder"))

            if not full_name or not email or not institution or author_order is None:
                return None, None, ({
                    "success": False,
                    "message": f"Co-author #{index} requires full_name, email, institution, and author_order.",
                }, 400)

            if not UserController._is_valid_email(email):
                return None, None, ({
                    "success": False,
                    "message": f"Co-author #{index} has an invalid email address.",
                }, 400)

            try:
                author_order = int(author_order)
            except (TypeError, ValueError):
                return None, None, ({
                    "success": False,
                    "message": f"Co-author #{index} author_order must be an integer.",
                }, 400)

            if author_order < 1:
                return None, None, ({
                    "success": False,
                    "message": f"Co-author #{index} author_order must be at least 1.",
                }, 400)

            if author_order in seen_orders:
                return None, None, ({
                    "success": False,
                    "message": "Each co-author author_order must be unique per article.",
                }, 400)

            if email in seen_emails:
                return None, None, ({
                    "success": False,
                    "message": "Each co-author email must be unique per article.",
                }, 400)

            seen_orders.add(author_order)
            seen_emails.add(email)
            co_authors.append(
                {
                    "full_name": full_name,
                    "email": email,
                    "institution": institution,
                    "orcid": orcid,
                    "author_order": author_order,
                }
            )

        return {
            "title": title,
            "abstract": abstract,
            "keywords": formatted_keywords,
            "article_type": article_type,
            "subject_area": subject_area,
        }, co_authors, None

    @staticmethod
    def _collect_submission_files(files_data):
        prepared_files = []

        for field_name, config in FILE_FIELD_MAP.items():
            uploaded_files = files_data.getlist(field_name)
            valid_files = [file_storage for file_storage in uploaded_files if file_storage and file_storage.filename]

            if config["required"] and not valid_files:
                return None, ({
                    "success": False,
                    "message": f"{config['file_type']} is required.",
                }, 400)

            if not config["multiple"] and len(valid_files) > 1:
                return None, ({
                    "success": False,
                    "message": f"Only one file is allowed for {config['file_type']}.",
                }, 400)

            for file_storage in valid_files:
                prepared_files.append(
                    {
                        "file_type": config["file_type"],
                        "storage": file_storage,
                    }
                )

        return prepared_files, None

    @staticmethod
    def _validate_revision_payload(payload):
        editorial_review_id = payload.get("editorial_review_id", payload.get("editorialReviewId"))
        response_letter = UserController._clean_text(payload.get("response_letter") or payload.get("responseLetter"))

        if editorial_review_id is None or not response_letter:
            return None, ({
                "success": False,
                "message": "editorial_review_id and response_letter are required.",
            }, 400)

        try:
            editorial_review_id = int(editorial_review_id)
        except (TypeError, ValueError):
            return None, ({
                "success": False,
                "message": "editorial_review_id must be an integer.",
            }, 400)

        return {
            "editorial_review_id": editorial_review_id,
            "response_letter": response_letter,
        }, None

    @staticmethod
    def _build_article_detail_response(article, author_profile, actor, message):
        co_authors = ArticleModel.get_co_authors(article["article_id"])
        files = ArticleModel.get_article_files(article["article_id"])
        revisions = ArticleModel.get_revisions(article["article_id"])

        return {
            "success": True,
            "message": message,
            "data": {
                "article": {
                    "article_id": article["article_id"],
                    "title": article["title"],
                    "abstract": article["abstract"],
                    "keywords": UserController._split_keywords(article["keywords"]),
                    "article_type": article["article_type"],
                    "subject_area": article["subject_area"],
                    "status": article["status"],
                    "submitted_at": str(article["submitted_at"]),
                    "updated_at": str(article["updated_at"]),
                    "author": {
                        "author_id": author_profile["author_id"],
                        "user_id": actor["user_id"],
                        "first_name": author_profile["first_name"],
                        "last_name": author_profile["last_name"],
                        "institution": author_profile["institution"],
                        "orcid": author_profile["orcid"],
                        "phone_number": author_profile["phone_number"],
                    },
                    "co_authors": [
                        {
                            "co_author_id": co_author["co_author_id"],
                            "full_name": co_author["full_name"],
                            "email": co_author["email"],
                            "institution": co_author["institution"],
                            "orcid": co_author["orcid"],
                            "author_order": co_author["author_order"],
                        }
                        for co_author in co_authors
                    ],
                    "files": [
                        {
                            "file_id": article_file["file_id"],
                            "file_name": article_file["file_name"],
                            "file_type": article_file["file_type"],
                            "file_path": article_file["file_path"],
                            "version": article_file["version"],
                            "uploaded_at": str(article_file["uploaded_at"]),
                        }
                        for article_file in files
                    ],
                    "revisions": [
                        {
                            "revision_id": revision["revision_id"],
                            "editorial_review_id": revision["editorial_review_id"],
                            "revision_number": revision["revision_number"],
                            "response_letter": revision["response_letter"],
                            "submitted_at": str(revision["submitted_at"]),
                        }
                        for revision in revisions
                    ],
                }
            },
        }, 200

    @staticmethod
    def _build_file_paths(upload_root, user_id, article_id, file_type, original_filename):
        safe_filename = secure_filename(original_filename or "")
        if not safe_filename:
            safe_filename = "uploaded_file"

        safe_file_type = secure_filename(file_type).replace("_", " ")
        path_parts = [str(user_id), str(article_id), safe_file_type, safe_filename]
        relative_path = "/".join(path_parts)
        absolute_path = os.path.join(upload_root, *path_parts)
        return safe_filename, relative_path, absolute_path

    @staticmethod
    def _cleanup_saved_files(saved_file_paths, upload_root):
        upload_root_path = Path(upload_root).resolve()

        for file_path in saved_file_paths:
            try:
                file_path_obj = Path(file_path).resolve()
                if file_path_obj.exists() and upload_root_path in file_path_obj.parents:
                    file_path_obj.unlink()
            except OSError:
                continue

        for file_path in saved_file_paths:
            current_dir = Path(file_path).parent
            try:
                while current_dir != upload_root_path and current_dir.exists():
                    current_dir.rmdir()
                    current_dir = current_dir.parent
            except OSError:
                continue

    @staticmethod
    def _map_database_error(exc, default_message):
        error_message = str(exc)

        if getattr(exc, "errno", None) == 1062:
            if "uq_co_authors_order" in error_message:
                return {
                    "success": False,
                    "message": "Each co-author author_order must be unique per article.",
                }, 409
            if "uq_co_authors_email_per_article" in error_message:
                return {
                    "success": False,
                    "message": "Each co-author email must be unique per article.",
                }, 409
            if "uq_article_files_article_type_version" in error_message:
                return {
                    "success": False,
                    "message": "A conflicting article file version already exists.",
                }, 409
            if "uq_revisions_article_number" in error_message:
                return {
                    "success": False,
                    "message": "A revision with this revision number already exists.",
                }, 409

        if "A revision can be submitted only after" in error_message:
            return {
                "success": False,
                "message": error_message,
            }, 400

        if "Revision Article must match" in error_message:
            return {
                "success": False,
                "message": error_message,
            }, 400

        return {
            "success": False,
            "message": default_message,
        }, 400

    @staticmethod
    def _clean_text(value, lower=False):
        if value is None:
            return None
        cleaned = str(value).strip()
        if not cleaned:
            return None
        return cleaned.lower() if lower else cleaned

    @staticmethod
    def _normalize_keywords(keywords):
        if keywords is None:
            return None
        if isinstance(keywords, list):
            cleaned_keywords = []
            for keyword in keywords:
                cleaned_keyword = UserController._clean_text(keyword)
                if cleaned_keyword:
                    cleaned_keywords.append(cleaned_keyword)
            return ", ".join(cleaned_keywords) if cleaned_keywords else None

        if isinstance(keywords, str):
            parts = [part.strip() for part in keywords.split(",") if part.strip()]
            return ", ".join(parts) if parts else None

        return str(keywords)

    @staticmethod
    def _split_keywords(keywords):
        if not keywords:
            return []
        return [part.strip() for part in str(keywords).split(",") if part.strip()]

    @staticmethod
    def _is_valid_email(email):
        return bool(email and "@" in email and "." in email.split("@")[-1])
