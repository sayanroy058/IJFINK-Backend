from flask import Blueprint, current_app, jsonify, request
from mysql.connector import Error as MySQLError

from app.controllers.chief_editor_controller import ChiefEditorController


chief_editor_blueprint = Blueprint("chief_editor", __name__)


def _handle(call):
    try:
        response, status_code = call()
        return jsonify(response), status_code
    except MySQLError:
        return jsonify({"success": False, "message": "Database connection failed."}), 500
    except Exception as exc:
        return jsonify({"success": False, "message": f"Unexpected server error: {str(exc)}"}), 500


@chief_editor_blueprint.get("/dashboard")
def dashboard():
    return _handle(lambda: ChiefEditorController.dashboard(current_app.config["SECRET_KEY"], request.headers.get("Authorization")))


@chief_editor_blueprint.get("/articles")
def list_articles():
    return _handle(lambda: ChiefEditorController.list_articles(current_app.config["SECRET_KEY"], request.headers.get("Authorization"), {
        "page": request.args.get("page", 1),
        "per_page": request.args.get("per_page", 10),
        "search": request.args.get("search"),
        "status": request.args.get("status"),
        "editor_id": request.args.get("editor_id"),
    }))


@chief_editor_blueprint.get("/articles/<int:article_id>")
def get_article(article_id):
    return _handle(lambda: ChiefEditorController.get_article(article_id, current_app.config["SECRET_KEY"], request.headers.get("Authorization")))


@chief_editor_blueprint.get("/editors")
def list_editors():
    return _handle(lambda: ChiefEditorController.list_editors(current_app.config["SECRET_KEY"], request.headers.get("Authorization")))


@chief_editor_blueprint.get("/editors/<int:editor_id>")
def get_editor(editor_id):
    return _handle(lambda: ChiefEditorController.get_editor(editor_id, current_app.config["SECRET_KEY"], request.headers.get("Authorization")))


@chief_editor_blueprint.get("/pending")
def pending_reviews():
    return _handle(lambda: ChiefEditorController.pending_reviews(current_app.config["SECRET_KEY"], request.headers.get("Authorization")))


@chief_editor_blueprint.get("/revisions")
def revisions():
    return _handle(lambda: ChiefEditorController.revisions(current_app.config["SECRET_KEY"], request.headers.get("Authorization")))


@chief_editor_blueprint.get("/statistics")
def statistics():
    return _handle(lambda: ChiefEditorController.statistics(current_app.config["SECRET_KEY"], request.headers.get("Authorization")))


@chief_editor_blueprint.get("/notifications")
def notifications():
    return _handle(lambda: ChiefEditorController.notifications(current_app.config["SECRET_KEY"], request.headers.get("Authorization")))


@chief_editor_blueprint.put("/notifications/<int:notification_id>/read")
def mark_notification_read(notification_id):
    return _handle(lambda: ChiefEditorController.mark_notification_read(notification_id, current_app.config["SECRET_KEY"], request.headers.get("Authorization")))
