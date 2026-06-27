from flask import Blueprint, current_app, jsonify, request
from mysql.connector import Error as MySQLError

from app.controllers.auth_controller import AuthController


auth_blueprint = Blueprint("auth", __name__)


@auth_blueprint.post("/login")
def login():
    payload = request.get_json(silent=True) or {}

    try:
        response, status_code = AuthController.login(
            payload=payload,
            secret_key=current_app.config["SECRET_KEY"],
        )
        return jsonify(response), status_code
    except MySQLError:
        return jsonify(
            {
                "success": False,
                "message": "Database connection failed during login.",
            }
        ), 500
    except Exception:
        return jsonify(
            {
                "success": False,
                "message": "Unexpected server error during login.",
            }
        ), 500
