from mysql.connector import Error as MySQLError

from database import get_db_connection
from app.models.user_model import UserModel
from app.controllers.auth_controller import AuthController


class AdminController:
    """Admin operations controller for managing user accounts"""

    @staticmethod
    def toggle_user_status(target_user_id, new_status, actor_user_id, secret_key, authorization_header):
        """
        Activate or deactivate a user account
        
        Args:
            target_user_id: ID of the user to activate/deactivate
            new_status: 'Active' or 'Inactive'
            actor_user_id: ID of the admin performing the action
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
                "message": "Only Admin users can manage user status.",
            }, 403
        
        # Validate new_status parameter
        if new_status not in ["Active", "Inactive"]:
            return {
                "success": False,
                "message": "Invalid status. Must be 'Active' or 'Inactive'.",
            }, 400
        
        # Prevent self-deactivation
        if actor["user_id"] == target_user_id and new_status == "Inactive":
            return {
                "success": False,
                "message": "Cannot deactivate your own account.",
            }, 400
        
        # Get target user information
        target_user = UserModel.find_by_id(target_user_id)
        
        if not target_user:
            return {
                "success": False,
                "message": f"User with ID {target_user_id} not found.",
            }, 404
        
        # Check if user is already in the requested status
        if target_user["status"] == new_status:
            return {
                "success": False,
                "message": f"User is already {new_status.lower()}.",
            }, 400
        
        # Update user status in database
        connection = None
        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                query = """
                    UPDATE users
                    SET status = %s
                    WHERE user_id = %s
                """
                cursor.execute(query, (new_status, target_user_id))
                connection.commit()
                
                if cursor.rowcount == 0:
                    return {
                        "success": False,
                        "message": "Failed to update user status.",
                    }, 500
                    
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
        
        # Get updated user information
        updated_user = UserModel.find_by_id(target_user_id)
        role_profile = UserModel.get_role_profile(target_user_id, target_user["role"])
        
        action = "activated" if new_status == "Active" else "deactivated"
        return {
            "success": True,
            "message": f"User successfully {action}.",
            "data": {
                "user": {
                    "user_id": updated_user["user_id"],
                    "email": updated_user["email"],
                    "role": updated_user["role"],
                    "status": updated_user["status"],
                    "display_name": (role_profile or {}).get("display_name"),
                    "profile_id": (role_profile or {}).get("profile_id"),
                    "created_at": str(updated_user["created_at"]),
                    "updated_at": str(updated_user["updated_at"]),
                },
                "action_by": {
                    "user_id": actor["user_id"],
                    "email": actor["email"],
                    "role": actor["role"],
                }
            },
        }, 200

    @staticmethod
    def get_all_users(actor_user_id, secret_key, authorization_header, filters=None):
        """
        Get all users with optional filtering (Admin only)
        
        Args:
            actor_user_id: ID of the requesting admin
            secret_key: Secret key for JWT validation
            authorization_header: Authorization header with JWT token
            filters: Dict with optional filters (role, status)
            
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
                "message": "Only Admin users can view all users.",
            }, 403
        
        filters = filters or {}
        role_filter = filters.get("role")
        status_filter = filters.get("status")
        
        connection = None
        try:
            connection = get_db_connection()
            
            query = "SELECT user_id, email, role, status, created_at, updated_at FROM users WHERE 1=1"
            params = []
            
            if role_filter:
                query += " AND role = %s"
                params.append(role_filter)
            
            if status_filter:
                query += " AND status = %s"
                params.append(status_filter)
            
            query += " ORDER BY created_at DESC"
            
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query, params)
                users = cursor.fetchall()
            
            # Enrich with profile data
            users_data = []
            for user in users:
                profile = UserModel.get_role_profile(user["user_id"], user["role"])
                users_data.append({
                    "user_id": user["user_id"],
                    "email": user["email"],
                    "role": user["role"],
                    "status": user["status"],
                    "display_name": (profile or {}).get("display_name"),
                    "profile_id": (profile or {}).get("profile_id"),
                    "created_at": str(user["created_at"]),
                    "updated_at": str(user["updated_at"]),
                })
            
            return {
                "success": True,
                "message": f"Retrieved {len(users_data)} user(s).",
                "data": {
                    "users": users_data,
                    "total_count": len(users_data),
                    "filters_applied": {
                        "role": role_filter,
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
    def get_user_details(target_user_id, actor_user_id, secret_key, authorization_header):
        """
        Get detailed information about a specific user (Admin only)
        
        Args:
            target_user_id: ID of the user to retrieve
            actor_user_id: ID of the requesting admin
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
                "message": "Only Admin users can view user details.",
            }, 403
        
        user = UserModel.find_by_id(target_user_id)
        
        if not user:
            return {
                "success": False,
                "message": f"User with ID {target_user_id} not found.",
            }, 404
        
        role_profile = UserModel.get_role_profile(target_user_id, user["role"])
        
        return {
            "success": True,
            "message": "User details retrieved successfully.",
            "data": {
                "user": {
                    "user_id": user["user_id"],
                    "email": user["email"],
                    "role": user["role"],
                    "status": user["status"],
                    "display_name": (role_profile or {}).get("display_name"),
                    "profile_id": (role_profile or {}).get("profile_id"),
                    "created_at": str(user["created_at"]),
                    "updated_at": str(user["updated_at"]),
                    "full_profile": role_profile or {},
                }
            },
        }, 200
