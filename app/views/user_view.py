from flask import Blueprint, current_app, jsonify, request
from mysql.connector import Error as MySQLError

from app.controllers.user_controller import UserController


user_blueprint = Blueprint("user", __name__)


@user_blueprint.post("/articles")
def submit_article():
    authorization_header = request.headers.get("Authorization")

    try:
        response, status_code = UserController.submit_article(
            form_data=request.form,
            files_data=request.files,
            secret_key=current_app.config["SECRET_KEY"],
            authorization_header=authorization_header,
            upload_root=current_app.config["UPLOAD_ROOT"],
        )
        return jsonify(response), status_code
    except MySQLError:
        return jsonify(
            {
                "success": False,
                "message": "Database connection failed.",
            }
        ), 500
    except Exception as exc:
        return jsonify(
            {
                "success": False,
                "message": f"Unexpected server error: {str(exc)}",
            }
        ), 500


@user_blueprint.get("/articles")
def list_articles():
    authorization_header = request.headers.get("Authorization")

    try:
        response, status_code = UserController.list_articles(
            secret_key=current_app.config["SECRET_KEY"],
            authorization_header=authorization_header,
        )
        return jsonify(response), status_code
    except MySQLError:
        return jsonify(
            {
                "success": False,
                "message": "Database connection failed.",
            }
        ), 500
    except Exception as exc:
        return jsonify(
            {
                "success": False,
                "message": f"Unexpected server error: {str(exc)}",
            }
        ), 500


@user_blueprint.get("/articles/<int:article_id>")
def get_article_details(article_id):
    authorization_header = request.headers.get("Authorization")

    try:
        response, status_code = UserController.get_article_details(
            article_id=article_id,
            secret_key=current_app.config["SECRET_KEY"],
            authorization_header=authorization_header,
        )
        return jsonify(response), status_code
    except MySQLError:
        return jsonify(
            {
                "success": False,
                "message": "Database connection failed.",
            }
        ), 500
    except Exception as exc:
        return jsonify(
            {
                "success": False,
                "message": f"Unexpected server error: {str(exc)}",
            }
        ), 500


@user_blueprint.post("/articles/<int:article_id>/revisions")
def submit_revision(article_id):
    authorization_header = request.headers.get("Authorization")

    try:
        response, status_code = UserController.submit_revision(
            article_id=article_id,
            form_data=request.form,
            files_data=request.files,
            secret_key=current_app.config["SECRET_KEY"],
            authorization_header=authorization_header,
            upload_root=current_app.config["UPLOAD_ROOT"],
        )
        return jsonify(response), status_code
    except MySQLError:
        return jsonify(
            {
                "success": False,
                "message": "Database connection failed.",
            }
        ), 500
    except Exception as exc:
        return jsonify(
            {
                "success": False,
                "message": f"Unexpected server error: {str(exc)}",
            }
        ), 500
