from flask import Blueprint, current_app, jsonify, request
from mysql.connector import Error as MySQLError

from app.controllers.screening_controller import ScreeningController


screening_blueprint = Blueprint("screening", __name__)


@screening_blueprint.get("/pending")
def get_pending_articles():
    """
    Get all articles pending admin screening
    
    Requires JWT token in Authorization header (Admin only)
    
    Returns:
        - 200: List of pending articles
        - 401: Missing or invalid JWT token
        - 403: User is not an Admin
        - 500: Server error
    """
    authorization_header = request.headers.get("Authorization")

    try:
        response, status_code = ScreeningController.get_pending_articles(
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


@screening_blueprint.get("/<int:article_id>")
def get_article_details(article_id):
    """
    Get detailed information about a specific article for screening
    
    Requires JWT token in Authorization header (Admin only)
    
    URL parameters:
        article_id: ID of the article
    
    Returns:
        - 200: Article details
        - 401: Missing or invalid JWT token
        - 403: User is not an Admin
        - 404: Article not found
        - 500: Server error
    """
    authorization_header = request.headers.get("Authorization")

    try:
        response, status_code = ScreeningController.get_article_details(
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


@screening_blueprint.post("/<int:article_id>/decision")
def submit_screening_decision(article_id):
    """
    Submit admin screening decision (Approved or Rejected)
    
    Requires JWT token in Authorization header (Admin only)
    
    URL parameters:
        article_id: ID of the article being screened
    
    Request body:
    {
        "decision": "Approved" or "Rejected",
        "remarks": "Optional remarks about the screening decision"
    }
    
    Returns:
        - 201: Decision submitted successfully
        - 400: Invalid decision or article already screened
        - 401: Missing or invalid JWT token
        - 403: User is not an Admin
        - 404: Article not found
        - 500: Server error
    """
    payload = request.get_json(silent=True) or {}
    authorization_header = request.headers.get("Authorization")

    try:
        response, status_code = ScreeningController.submit_screening_decision(
            article_id=article_id,
            payload=payload,
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


@screening_blueprint.get("/history")
def get_screening_history():
    """
    Get admin screening history with optional filtering
    
    Requires JWT token in Authorization header (Admin only)
    
    Query parameters (optional):
        decision: Filter by 'Approved' or 'Rejected'
        screened_by_me: Set to 'true' to show only your screenings
        date_from: Filter from date (YYYY-MM-DD)
        date_to: Filter to date (YYYY-MM-DD)
    
    Returns:
        - 200: Screening history records
        - 401: Missing or invalid JWT token
        - 403: User is not an Admin
        - 500: Server error
    """
    authorization_header = request.headers.get("Authorization")
    
    filters = {}
    if request.args.get("decision"):
        filters["decision"] = request.args.get("decision").capitalize()
    if request.args.get("screened_by_me") == "true":
        filters["screened_by_me"] = True
    if request.args.get("date_from"):
        filters["date_from"] = request.args.get("date_from")
    if request.args.get("date_to"):
        filters["date_to"] = request.args.get("date_to")

    try:
        response, status_code = ScreeningController.get_screening_history(
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
