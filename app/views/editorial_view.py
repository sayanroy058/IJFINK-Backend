from flask import Blueprint, current_app, jsonify, request
from mysql.connector import Error as MySQLError

from app.controllers.editorial_controller import EditorialController


editorial_blueprint = Blueprint("editorial", __name__)


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


# ---------------- Admin-side endpoints ----------------

@editorial_blueprint.get("/assignable-articles")
def list_assignable_articles():
    """
    Articles approved by admin screening that still need an editor.

    Requires: Admin JWT.
    """
    return _handle(lambda: EditorialController.get_assignable_articles(
        secret_key=current_app.config["SECRET_KEY"],
        authorization_header=request.headers.get("Authorization"),
    ))


@editorial_blueprint.get("/assignable-editors")
def list_assignable_editors():
    """
    Active editors who can be assigned (chief editor excluded).

    Requires: Admin JWT.
    """
    return _handle(lambda: EditorialController.get_assignable_editors(
        secret_key=current_app.config["SECRET_KEY"],
        authorization_header=request.headers.get("Authorization"),
    ))


@editorial_blueprint.post("/assignments")
def create_assignment():
    """
    Assign an editor to an admin-approved article.

    Body: {"article_id": int, "editor_id": int}
    Requires: Admin JWT.

    Only works when the article's admin_screening.decision = 'Approved'
    and articles.status = 'Admin Approved'.
    """
    payload = request.get_json(silent=True) or {}
    return _handle(lambda: EditorialController.assign_editor(
        payload=payload,
        secret_key=current_app.config["SECRET_KEY"],
        authorization_header=request.headers.get("Authorization"),
    ))


# ---------------- Editor-side endpoints ----------------

@editorial_blueprint.get("/assignments")
def list_assignments():
    """
    List editorial assignments visible to the current editor.

    Chief editor sees all assignments. Regular editors see only theirs.
    Requires: Editor JWT.
    """
    return _handle(lambda: EditorialController.get_assignments(
        secret_key=current_app.config["SECRET_KEY"],
        authorization_header=request.headers.get("Authorization"),
    ))


@editorial_blueprint.get("/assignments/<int:assignment_id>")
def get_assignment_details(assignment_id):
    """
    Detailed view of an assignment.

    Only the assigned editor or the chief editor may view it.
    Requires: Editor JWT.
    """
    return _handle(lambda: EditorialController.get_assignment_details(
        assignment_id=assignment_id,
        secret_key=current_app.config["SECRET_KEY"],
        authorization_header=request.headers.get("Authorization"),
    ))
