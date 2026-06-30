from flask import Blueprint, current_app, jsonify, request
from mysql.connector import Error as MySQLError

from app.controllers.editor_controller import EditorController


editor_blueprint = Blueprint("editor", __name__)


def _handle(call):
    try:
        response, status_code = call()
        return jsonify(response), status_code
    except MySQLError:
        return jsonify({"success": False, "message": "Database connection failed."}), 500
    except Exception as exc:
        return jsonify({"success": False, "message": f"Unexpected server error: {str(exc)}"}), 500


@editor_blueprint.get("/dashboard")
def dashboard():
    return _handle(lambda: EditorController.dashboard(current_app.config["SECRET_KEY"], request.headers.get("Authorization")))


@editor_blueprint.get("/articles")
def list_articles():
    return _handle(lambda: EditorController.list_articles(current_app.config["SECRET_KEY"], request.headers.get("Authorization"), {
        "page": request.args.get("page", 1),
        "per_page": request.args.get("per_page", 10),
        "sort_by": request.args.get("sort_by"),
        "sort_order": request.args.get("sort_order"),
        "search": request.args.get("search"),
        "status": request.args.get("status"),
    }))


@editor_blueprint.get("/articles/<int:article_id>")
def get_article(article_id):
    return _handle(lambda: EditorController.get_article(article_id, current_app.config["SECRET_KEY"], request.headers.get("Authorization")))


@editor_blueprint.get("/articles/<int:article_id>/files")
def get_files(article_id):
    return _handle(lambda: EditorController.get_files(article_id, current_app.config["SECRET_KEY"], request.headers.get("Authorization")))


@editor_blueprint.post("/review")
def submit_review():
    payload = request.get_json(silent=True) or {}
    return _handle(lambda: EditorController.submit_review(payload, current_app.config["SECRET_KEY"], request.headers.get("Authorization")))


@editor_blueprint.put("/review/<int:review_id>")
def update_review(review_id):
    payload = request.get_json(silent=True) or {}
    return _handle(lambda: EditorController.update_review(review_id, payload, current_app.config["SECRET_KEY"], request.headers.get("Authorization")))


@editor_blueprint.get("/reviews")
def review_history():
    return _handle(lambda: EditorController.review_history(current_app.config["SECRET_KEY"], request.headers.get("Authorization")))


@editor_blueprint.get("/revision-requests")
def revision_requests():
    return _handle(lambda: EditorController.revision_requests(current_app.config["SECRET_KEY"], request.headers.get("Authorization")))


@editor_blueprint.get("/notifications")
def notifications():
    return _handle(lambda: EditorController.notifications(current_app.config["SECRET_KEY"], request.headers.get("Authorization")))


@editor_blueprint.put("/notifications/<int:notification_id>/read")
def mark_notification_read(notification_id):
    return _handle(lambda: EditorController.mark_notification_read(notification_id, current_app.config["SECRET_KEY"], request.headers.get("Authorization")))
