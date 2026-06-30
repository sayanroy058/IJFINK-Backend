from datetime import datetime
from mysql.connector import Error as MySQLError

from database import get_db_connection
from app.models.user_model import UserModel
from app.controllers.auth_controller import AuthController


class ContactController:
    """Contact form management controller (Admin only)"""

    @staticmethod
    def submit_contact_query(payload):
        """
        Submit a new contact query (Public - no authentication required)
        
        Args:
            payload: Request body with contact form data
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        
        # Validate required fields
        first_name = (payload.get("first_name") or "").strip()
        last_name = (payload.get("last_name") or "").strip()
        email = (payload.get("email") or "").strip().lower()
        subject = (payload.get("subject") or "").strip()
        message = (payload.get("message") or "").strip()
        
        if not all([first_name, last_name, email, subject, message]):
            return {
                "success": False,
                "message": "First name, last name, email, subject, and message are required.",
            }, 400
        
        # Validate email format
        if "@" not in email or "." not in email.split("@")[-1]:
            return {
                "success": False,
                "message": "Invalid email format.",
            }, 400
        
        # Insert contact query
        connection = None
        try:
            connection = get_db_connection()
            
            query = """
                INSERT INTO contact_queries (admin_id, first_name, last_name, email, subject, message, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            with connection.cursor() as cursor:
                
                cursor.execute(query, (
                    None,
                    first_name,
                    last_name,
                    email,
                    subject,
                    message,
                    "Pending"
                ))
                connection.commit()
                query_id = cursor.lastrowid
            
            return {
                "success": True,
                "message": "Contact query submitted successfully.",
                "data": {
                    "query_id": query_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "subject": subject,
                    "message": message,
                    "status": "Pending",
                    "created_at": datetime.now().isoformat(),
                }
            }, 201
            
        except MySQLError as exc:
            if connection:
                connection.rollback()
            return {
                "success": False,
                "message": f"Database error: {str(exc)}",
            }, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def get_all_contact_queries(secret_key, authorization_header, filters=None):
        """
        Get all contact queries with optional filtering (Admin only)
        
        Args:
            secret_key: Secret key for JWT validation
            authorization_header: Authorization header with JWT token
            filters: Dict with optional filters (status)

        Returns:
            Tuple of (response_dict, status_code)

        Any authenticated Admin can view every contact query. Non-admin
        callers are rejected with 403.
        """
        
        # Validate the requesting user is an authenticated admin
        actor = AuthController._get_authenticated_actor(secret_key, authorization_header)
        
        if not actor:
            return {
                "success": False,
                "message": "Authentication failed. Valid JWT token is required.",
            }, 401
        
        if actor["role"] != "Admin":
            return {
                "success": False,
                "message": "Only Admin users can view contact queries.",
            }, 403
        
        filters = filters or {}
        status_filter = filters.get("status")

        connection = None
        try:
            connection = get_db_connection()

            query = """
                SELECT
                    cq.query_id,
                    cq.first_name,
                    cq.last_name,
                    cq.email,
                    cq.subject,
                    cq.message,
                    cq.status,
                    cq.created_at,
                    cq.resolved_at,
                    cq.admin_id,
                    CASE
                        WHEN a.admin_id IS NOT NULL
                        THEN CONCAT(a.first_name, ' ', a.last_name)
                        ELSE NULL
                    END AS assigned_admin_name
                FROM contact_queries cq
                LEFT JOIN admins a ON a.admin_id = cq.admin_id
                WHERE 1=1
            """

            params = []

            if status_filter:
                query += " AND cq.status = %s"
                params.append(status_filter)

            query += " ORDER BY cq.created_at DESC"
            
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query, params)
                queries = cursor.fetchall()
            
            # Format results
            queries_data = []
            for q in queries:
                queries_data.append({
                    "query_id": q["query_id"],
                    "first_name": q["first_name"],
                    "last_name": q["last_name"],
                    "email": q["email"],
                    "subject": q["subject"],
                    "message": q["message"],
                    "status": q["status"],
                    "created_at": str(q["created_at"]),
                    "resolved_at": str(q["resolved_at"]) if q["resolved_at"] else None,
                    "assigned_admin": q["assigned_admin_name"],
                })
            
            return {
                "success": True,
                "message": f"Retrieved {len(queries_data)} contact query(ies).",
                "data": {
                    "queries": queries_data,
                    "total_count": len(queries_data),
                    "filters_applied": {
                        "status": status_filter,
                    }
                },
            }, 200
            
        except MySQLError as exc:
            return {
                "success": False,
                "message": f"Database error: {str(exc)}",
            }, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def get_contact_query_details(query_id, secret_key, authorization_header):
        """
        Get details of a specific contact query (Admin only)
        
        Args:
            query_id: ID of the contact query
            secret_key: Secret key for JWT validation
            authorization_header: Authorization header with JWT token
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        
        # Validate the requesting user is an authenticated admin
        actor = AuthController._get_authenticated_actor(secret_key, authorization_header)
        
        if not actor:
            return {
                "success": False,
                "message": "Authentication failed. Valid JWT token is required.",
            }, 401
        
        if actor["role"] != "Admin":
            return {
                "success": False,
                "message": "Only Admin users can view contact query details.",
            }, 403
        
        connection = None
        try:
            connection = get_db_connection()
            
            query = """
                SELECT 
                    cq.query_id,
                    cq.first_name,
                    cq.last_name,
                    cq.email,
                    cq.subject,
                    cq.message,
                    cq.status,
                    cq.created_at,
                    cq.resolved_at,
                    cq.admin_id,
                    CASE 
                        WHEN a.admin_id IS NOT NULL 
                        THEN CONCAT(a.first_name, ' ', a.last_name)
                        ELSE NULL
                    END AS assigned_admin_name
                FROM contact_queries cq
                LEFT JOIN admins a ON a.admin_id = cq.admin_id
                WHERE cq.query_id = %s
            """
            
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query, (query_id,))
                result = cursor.fetchone()
            
            if not result:
                return {
                    "success": False,
                    "message": f"Contact query with ID {query_id} not found.",
                }, 404
            
            return {
                "success": True,
                "message": "Contact query details retrieved successfully.",
                "data": {
                    "query": {
                        "query_id": result["query_id"],
                        "first_name": result["first_name"],
                        "last_name": result["last_name"],
                        "email": result["email"],
                        "subject": result["subject"],
                        "message": result["message"],
                        "status": result["status"],
                        "created_at": str(result["created_at"]),
                        "resolved_at": str(result["resolved_at"]) if result["resolved_at"] else None,
                        "assigned_admin": result["assigned_admin_name"],
                    }
                },
            }, 200
            
        except MySQLError as exc:
            return {
                "success": False,
                "message": f"Database error: {str(exc)}",
            }, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def update_contact_query_status(query_id, new_status, secret_key, authorization_header):
        """
        Update contact query status (Admin only)
        
        Args:
            query_id: ID of the contact query
            new_status: New status ('Pending' or 'Resolved')
            secret_key: Secret key for JWT validation
            authorization_header: Authorization header with JWT token
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        
        # Validate the requesting user is an authenticated admin
        actor = AuthController._get_authenticated_actor(secret_key, authorization_header)
        
        if not actor:
            return {
                "success": False,
                "message": "Authentication failed. Valid JWT token is required.",
            }, 401
        
        if actor["role"] != "Admin":
            return {
                "success": False,
                "message": "Only Admin users can update contact query status.",
            }, 403
        
        # Validate status
        if new_status not in ["Pending", "Resolved"]:
            return {
                "success": False,
                "message": "Invalid status. Must be 'Pending' or 'Resolved'.",
            }, 400
        
        connection = None
        try:
            connection = get_db_connection()
            
            # Get current status
            check_query = "SELECT status FROM contact_queries WHERE query_id = %s"
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(check_query, (query_id,))
                result = cursor.fetchone()
            
            if not result:
                return {
                    "success": False,
                    "message": f"Contact query with ID {query_id} not found.",
                }, 404
            
            current_status = result["status"]
            
            if current_status == new_status:
                return {
                    "success": False,
                    "message": f"Query is already {new_status.lower()}.",
                }, 400
            
            # Get admin_id
            admin_query = "SELECT admin_id FROM admins WHERE user_id = %s"
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(admin_query, (actor["user_id"],))
                admin_result = cursor.fetchone()
                admin_id = admin_result["admin_id"] if admin_result else None
            
            # Update status
            resolved_at = datetime.now() if new_status == "Resolved" else None
            
            update_query = """
                UPDATE contact_queries
                SET status = %s, admin_id = %s, resolved_at = %s
                WHERE query_id = %s
            """
            
            with connection.cursor() as cursor:
                cursor.execute(update_query, (new_status, admin_id, resolved_at, query_id))
                connection.commit()
            
            return {
                "success": True,
                "message": f"Contact query status updated to {new_status}.",
                "data": {
                    "query_id": query_id,
                    "status": new_status,
                    "updated_by": {
                        "user_id": actor["user_id"],
                        "email": actor["email"],
                        "role": actor["role"],
                    },
                    "resolved_at": resolved_at.isoformat() if resolved_at else None,
                }
            }, 200
            
        except MySQLError as exc:
            if connection:
                connection.rollback()
            return {
                "success": False,
                "message": f"Database error: {str(exc)}",
            }, 500
        finally:
            if connection:
                connection.close()
