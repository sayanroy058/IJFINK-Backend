from flask import Blueprint, current_app, jsonify, request
from mysql.connector import Error as MySQLError

from app.controllers.admin_controller import AdminController


admin_blueprint = Blueprint("admin", __name__)


@admin_blueprint.patch("/users/<int:user_id>/status")
def toggle_user_status(user_id):
    """
    Activate or deactivate a user account
    
    Requires JWT token in Authorization header (Admin only)
    
    Request body:
    {
        "status": "Active" | "Inactive"
    }
    
    Returns:
        - 200: Successfully updated
        - 400: Invalid request/status
        - 401: Missing or invalid JWT token
        - 403: User is not an Admin
        - 404: User not found
        - 500: Server error
    """
    payload = request.get_json(silent=True) or {}
    new_status = payload.get("status")
    authorization_header = request.headers.get("Authorization")

    try:
        response, status_code = AdminController.toggle_user_status(
            target_user_id=user_id,
            new_status=new_status,
            actor_user_id=None,  # Extracted from JWT in controller
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


@admin_blueprint.get("/users")
def get_all_users():
    """
    Get all users with optional filtering
    
    Requires JWT token in Authorization header (Admin only)
    
    Query parameters:
        - role: Filter by role (Author, Admin, Editor, Publication Team)
        - status: Filter by status (Active, Inactive)
    
    Returns:
        - 200: List of users
        - 401: Missing or invalid JWT token
        - 403: User is not an Admin
        - 500: Server error
    """
    authorization_header = request.headers.get("Authorization")
    filters = {
        "role": request.args.get("role"),
        "status": request.args.get("status"),
    }

    try:
        response, status_code = AdminController.get_all_users(
            actor_user_id=None,  # Extracted from JWT in controller
            secret_key=current_app.config["SECRET_KEY"],
            authorization_header=authorization_header,
            filters=filters,
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


@admin_blueprint.get("/users/<int:user_id>")
def get_user_details(user_id):
    """
    Get detailed information about a specific user
    
    Requires JWT token in Authorization header (Admin only)
    
    Returns:
        - 200: User details
        - 401: Missing or invalid JWT token
        - 403: User is not an Admin
        - 404: User not found
        - 500: Server error
    """
    authorization_header = request.headers.get("Authorization")

    try:
        response, status_code = AdminController.get_user_details(
            target_user_id=user_id,
            actor_user_id=None,  # Extracted from JWT in controller
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
