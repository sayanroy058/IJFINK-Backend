from flask import Blueprint, current_app, jsonify, request
from mysql.connector import Error as MySQLError

from app.controllers.publication_controller import PublicationController


publication_blueprint = Blueprint("publication", __name__)


def _handle(call):
    try:
        response, status_code = call()
        return jsonify(response), status_code
    except MySQLError:
        return jsonify({
            "success": False,
            "message": "Database connection failed.",
        }), 500
    except Exception as exc:
        return jsonify({
            "success": False,
            "message": f"Unexpected server error: {str(exc)}",
        }), 500


@publication_blueprint.get("/accepted-articles")
def list_accepted_articles():
    """List articles accepted by editorial review and ready for publication review."""
    return _handle(lambda: PublicationController.get_accepted_articles(
        secret_key=current_app.config["SECRET_KEY"],
        authorization_header=request.headers.get("Authorization"),
    ))


@publication_blueprint.get("/articles/<int:article_id>")
def get_article_details(article_id):
    """Detailed article view for publication team checks."""
    return _handle(lambda: PublicationController.get_article_details(
        article_id=article_id,
        secret_key=current_app.config["SECRET_KEY"],
        authorization_header=request.headers.get("Authorization"),
    ))


@publication_blueprint.post("/articles/<int:article_id>/start-review")
def start_publication_review(article_id):
    """Move an accepted article into publication team review."""
    return _handle(lambda: PublicationController.start_review(
        article_id=article_id,
        secret_key=current_app.config["SECRET_KEY"],
        authorization_header=request.headers.get("Authorization"),
    ))


@publication_blueprint.post("/articles/<int:article_id>/return-to-editor")
def return_to_editor(article_id):
    """Return an article to its latest assigned editor with publisher feedback."""
    payload = request.get_json(silent=True) or {}
    return _handle(lambda: PublicationController.return_to_editor(
        article_id=article_id,
        payload=payload,
        secret_key=current_app.config["SECRET_KEY"],
        authorization_header=request.headers.get("Authorization"),
    ))


@publication_blueprint.post("/articles/<int:article_id>/submit-organization")
def submit_to_organization(article_id):
    """Mark an article as submitted to an external publication organization."""
    payload = request.get_json(silent=True) or {}
    return _handle(lambda: PublicationController.submit_to_organization(
        article_id=article_id,
        payload=payload,
        secret_key=current_app.config["SECRET_KEY"],
        authorization_header=request.headers.get("Authorization"),
    ))


@publication_blueprint.post("/articles/<int:article_id>/reject")
def reject_article(article_id):
    """Mark an externally rejected article as rejected."""
    payload = request.get_json(silent=True) or {}
    return _handle(lambda: PublicationController.reject_article(
        article_id=article_id,
        payload=payload,
        secret_key=current_app.config["SECRET_KEY"],
        authorization_header=request.headers.get("Authorization"),
    ))


@publication_blueprint.post("/articles/<int:article_id>/publish")
def publish_article(article_id):
    """
    Create the final publication record and store the final PDF/DOC file.

    Multipart fields:
      - publication_data: JSON object with organization_name, doi, article_url,
        volume, issue, pages, publication_date
      - published_file: final published file
    """
    return _handle(lambda: PublicationController.publish_article(
        article_id=article_id,
        form_data=request.form,
        files_data=request.files,
        secret_key=current_app.config["SECRET_KEY"],
        authorization_header=request.headers.get("Authorization"),
        published_root=current_app.config["PUBLISHED_ROOT"],
    ))


@publication_blueprint.get("/published")
def list_published_articles():
    """List final publication records."""
    return _handle(lambda: PublicationController.get_published_articles(
        secret_key=current_app.config["SECRET_KEY"],
        authorization_header=request.headers.get("Authorization"),
    ))


@publication_blueprint.get("/published/<int:article_id>")
def get_published_article(article_id):
    """Get one final publication record by article id."""
    return _handle(lambda: PublicationController.get_published_article(
        article_id=article_id,
        secret_key=current_app.config["SECRET_KEY"],
        authorization_header=request.headers.get("Authorization"),
    ))
