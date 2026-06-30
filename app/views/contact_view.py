from flask import Blueprint, current_app, jsonify, request
from mysql.connector import Error as MySQLError

from app.controllers.contact_controller import ContactController


contact_blueprint = Blueprint("contact", __name__)


@contact_blueprint.post("/queries")
def submit_contact_query():
    """
    Submit a new contact query (Public - no authentication required)
    
    Request body:
    {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "subject": "Query Subject",
        "message": "Detailed message content"
    }
    
    Returns:
        - 201: Successfully created
        - 400: Invalid request
        - 500: Server error
    """
    payload = request.get_json(silent=True) or {}

    try:
        response, status_code = ContactController.submit_contact_query(
            payload=payload,
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


@contact_blueprint.get("/queries")
def get_all_contact_queries():
    """
    Get all contact queries (Admin only)
    
    Requires JWT token in Authorization header (Admin only)
    
    Query parameters:
        - status: Filter by status (Pending, Resolved)

    Every authenticated Admin can see every contact query; no other role
    has access to this endpoint.

    Returns:
        - 200: List of contact queries
        - 401: Missing or invalid JWT token
        - 403: User is not an Admin
        - 500: Server error
    """
    authorization_header = request.headers.get("Authorization")
    filters = {
        "status": request.args.get("status"),
    }

    try:
        response, status_code = ContactController.get_all_contact_queries(
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


@contact_blueprint.get("/queries/<int:query_id>")
def get_contact_query_details(query_id):
    """
    Get details of a specific contact query (Admin only)
    
    Requires JWT token in Authorization header (Admin only)
    
    Returns:
        - 200: Contact query details
        - 401: Missing or invalid JWT token
        - 403: User is not an Admin
        - 404: Query not found
        - 500: Server error
    """
    authorization_header = request.headers.get("Authorization")

    try:
        response, status_code = ContactController.get_contact_query_details(
            query_id=query_id,
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


@contact_blueprint.patch("/queries/<int:query_id>/status")
def update_contact_query_status(query_id):
    """
    Update contact query status (Admin only)
    
    Requires JWT token in Authorization header (Admin only)
    
    Request body:
    {
        "status": "Pending" | "Resolved"
    }
    
    Returns:
        - 200: Status updated successfully
        - 400: Invalid status
        - 401: Missing or invalid JWT token
        - 403: User is not an Admin
        - 404: Query not found
        - 500: Server error
    """
    payload = request.get_json(silent=True) or {}
    new_status = payload.get("status")
    authorization_header = request.headers.get("Authorization")

    try:
        response, status_code = ContactController.update_contact_query_status(
            query_id=query_id,
            new_status=new_status,
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
