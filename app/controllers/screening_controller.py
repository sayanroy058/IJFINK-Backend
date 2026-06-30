from datetime import datetime
from mysql.connector import Error as MySQLError

from database import get_db_connection
from app.controllers.auth_controller import AuthController


class ScreeningController:
    """Admin manuscript screening management controller"""

    @staticmethod
    def get_pending_articles(secret_key, authorization_header):
        """
        Get all articles pending admin screening
        
        Args:
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
                "message": "Only Admin users can access screening.",
            }, 403
        
        # Get pending articles
        connection = None
        try:
            connection = get_db_connection()
            
            query = """
                SELECT 
                    a.article_id,
                    a.title,
                    a.abstract,
                    a.keywords,
                    a.article_type,
                    a.subject_area,
                    a.status,
                    a.submitted_at,
                    au.first_name,
                    au.last_name,
                    u.email,
                    au.institution,
                    CASE WHEN a_s.screening_id IS NOT NULL THEN 'Screened' ELSE 'Pending' END as screening_status
                FROM articles a
                JOIN authors au ON a.author_id = au.author_id
                JOIN users u ON au.user_id = u.user_id
                LEFT JOIN admin_screening a_s ON a.article_id = a_s.article_id
                WHERE a.status = 'Submitted' AND a_s.screening_id IS NULL
                ORDER BY a.submitted_at ASC
            """
            
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query)
                articles = cursor.fetchall()
            
            return {
                "success": True,
                "message": f"Retrieved {len(articles)} pending article(s) for screening.",
                "data": {
                    "articles": articles,
                    "total_count": len(articles)
                }
            }, 200
            
        except MySQLError as e:
            return {
                "success": False,
                "message": f"Database error: {str(e)}",
            }, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def get_article_details(article_id, secret_key, authorization_header):
        """
        Get detailed information about a specific article for screening
        
        Args:
            article_id: ID of the article
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
                "message": "Only Admin users can access screening.",
            }, 403
        
        # Get article details
        connection = None
        try:
            connection = get_db_connection()
            
            # Get main article info
            query = """
                SELECT 
                    a.article_id,
                    a.title,
                    a.abstract,
                    a.keywords,
                    a.article_type,
                    a.subject_area,
                    a.status,
                    a.submitted_at,
                    au.first_name,
                    au.last_name,
                    u.email,
                    au.institution,
                    au.phone_number,
                    au.orcid
                FROM articles a
                JOIN authors au ON a.author_id = au.author_id
                JOIN users u ON au.user_id = u.user_id
                WHERE a.article_id = %s
            """
            
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query, (article_id,))
                article = cursor.fetchone()
                
                if not article:
                    return {
                        "success": False,
                        "message": "Article not found.",
                    }, 404
                
                # Get co-authors
                co_authors_query = """
                    SELECT full_name, email, institution, orcid, author_order
                    FROM co_authors
                    WHERE article_id = %s
                    ORDER BY author_order ASC
                """
                cursor.execute(co_authors_query, (article_id,))
                co_authors = cursor.fetchall()
                
                # Get uploaded files
                files_query = """
                    SELECT file_id, file_name, file_type, file_path, version, uploaded_at
                    FROM article_files
                    WHERE article_id = %s
                    ORDER BY uploaded_at DESC
                """
                cursor.execute(files_query, (article_id,))
                files = cursor.fetchall()
                
                # Get existing screening if any
                screening_query = """
                    SELECT screening_id, decision, remarks, screened_at, 
                           CONCAT(admin.first_name, ' ', admin.last_name) as screened_by
                    FROM admin_screening a_s
                    JOIN admins admin ON a_s.admin_id = admin.admin_id
                    WHERE article_id = %s
                """
                cursor.execute(screening_query, (article_id,))
                screening = cursor.fetchone()
            
            article["co_authors"] = co_authors
            article["files"] = files
            article["screening"] = screening
            
            return {
                "success": True,
                "message": "Article details retrieved successfully.",
                "data": {
                    "article": article
                }
            }, 200
            
        except MySQLError as e:
            return {
                "success": False,
                "message": f"Database error: {str(e)}",
            }, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def submit_screening_decision(article_id, payload, secret_key, authorization_header):
        """
        Submit admin screening decision (Approved or Rejected)
        
        Args:
            article_id: ID of the article being screened
            payload: Request body with decision and remarks
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
                "message": "Only Admin users can submit screening decisions.",
            }, 403
        
        # Validate decision
        decision = (payload.get("decision") or "").strip().capitalize()
        if decision not in ["Approved", "Rejected"]:
            return {
                "success": False,
                "message": "Decision must be either 'Approved' or 'Rejected'.",
            }, 400
        
        # Validate remarks
        remarks = (payload.get("remarks") or "").strip()
        
        # Submit screening decision
        connection = None
        try:
            connection = get_db_connection()
            
            with connection.cursor(dictionary=True) as cursor:
                # Check if article exists
                cursor.execute("SELECT article_id, status FROM articles WHERE article_id = %s", (article_id,))
                article = cursor.fetchone()
                
                if not article:
                    return {
                        "success": False,
                        "message": "Article not found.",
                    }, 404
                
                if article["status"] != "Submitted":
                    return {
                        "success": False,
                        "message": "Only articles in 'Submitted' status can be screened.",
                    }, 400
                
                # Check if already screened
                cursor.execute(
                    "SELECT screening_id FROM admin_screening WHERE article_id = %s",
                    (article_id,)
                )
                existing_screening = cursor.fetchone()
                
                if existing_screening:
                    return {
                        "success": False,
                        "message": "This article has already been screened.",
                    }, 400
                
                # Get admin profile ID
                admin_query = "SELECT admin_id FROM admins WHERE user_id = %s"
                cursor.execute(admin_query, (actor["user_id"],))
                admin_result = cursor.fetchone()
                admin_id = admin_result["admin_id"] if admin_result else None
                
                if not admin_id:
                    return {
                        "success": False,
                        "message": "Admin profile not found.",
                    }, 500
                
                # Insert screening record
                insert_query = """
                    INSERT INTO admin_screening (article_id, admin_id, decision, remarks)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(insert_query, (article_id, admin_id, decision, remarks if remarks else None))
                
                # Update article status based on decision
                new_status = "Admin Approved" if decision == "Approved" else "Admin Rejected"
                update_query = "UPDATE articles SET status = %s WHERE article_id = %s"
                cursor.execute(update_query, (new_status, article_id))
                
                connection.commit()
                screening_id = cursor.lastrowid
            
            return {
                "success": True,
                "message": f"Screening decision '{decision}' submitted successfully.",
                "data": {
                    "screening_id": screening_id,
                    "article_id": article_id,
                    "decision": decision,
                    "remarks": remarks,
                    "screened_at": datetime.now().isoformat(),
                    "new_article_status": new_status
                }
            }, 201
            
        except MySQLError as e:
            if connection:
                connection.rollback()
            return {
                "success": False,
                "message": f"Database error: {str(e)}",
            }, 500
        finally:
            if connection:
                connection.close()

    @staticmethod
    def get_screening_history(secret_key, authorization_header, filters=None):
        """
        Get admin screening history with optional filtering
        
        Args:
            secret_key: Secret key for JWT validation
            authorization_header: Authorization header with JWT token
            filters: Optional dictionary with filters (decision, admin_id, date_from, date_to)
            
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
                "message": "Only Admin users can access screening history.",
            }, 403
        
        filters = filters or {}
        
        # Get screening history
        connection = None
        try:
            connection = get_db_connection()
            
            query = """
                SELECT 
                    a_s.screening_id,
                    a_s.article_id,
                    a_s.decision,
                    a_s.remarks,
                    a_s.screened_at,
                    CONCAT(admin.first_name, ' ', admin.last_name) as screened_by,
                    a.title,
                    a.status,
                    CONCAT(au.first_name, ' ', au.last_name) as author_name
                FROM admin_screening a_s
                JOIN admins admin ON a_s.admin_id = admin.admin_id
                JOIN articles a ON a_s.article_id = a.article_id
                JOIN authors au ON a.author_id = au.author_id
                WHERE 1=1
            """
            
            params = []
            
            # Apply filters
            if filters.get("decision"):
                query += " AND a_s.decision = %s"
                params.append(filters["decision"])
            
            if filters.get("screened_by_me"):
                query += " AND a_s.admin_id = (SELECT admin_id FROM admins WHERE user_id = %s)"
                params.append(actor["user_id"])
            
            if filters.get("date_from"):
                query += " AND DATE(a_s.screened_at) >= %s"
                params.append(filters["date_from"])
            
            if filters.get("date_to"):
                query += " AND DATE(a_s.screened_at) <= %s"
                params.append(filters["date_to"])
            
            query += " ORDER BY a_s.screened_at DESC"
            
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query, params)
                screenings = cursor.fetchall()
            
            return {
                "success": True,
                "message": f"Retrieved {len(screenings)} screening record(s).",
                "data": {
                    "screenings": screenings,
                    "total_count": len(screenings)
                }
            }, 200
            
        except MySQLError as e:
            return {
                "success": False,
                "message": f"Database error: {str(e)}",
            }, 500
        finally:
            if connection:
                connection.close()
