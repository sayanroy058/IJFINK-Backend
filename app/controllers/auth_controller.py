from datetime import timedelta

from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import check_password_hash

from app.models.user_model import UserModel


ROLE_ALIASES = {
    "author": "Author",
    "admin": "Admin",
    "editor": "Editor",
    "publication team": "Publication Team",
    "publication_team": "Publication Team",
    "publication-team": "Publication Team",
}

ROLE_DASHBOARD_MAP = {
    "Author": "/dashboard/author",
    "Admin": "/dashboard/admin",
    "Editor": "/dashboard/editor",
    "Publication Team": "/dashboard/publication-team",
}


class AuthController:
    @staticmethod
    def login(payload, secret_key):
        email = (payload.get("email") or "").strip().lower()
        password = payload.get("password") or ""
        selected_role = AuthController._normalize_role(payload.get("role"))
        remember_me = bool(payload.get("remember_me", False))

        if not email or not password or not selected_role:
            return {
                "success": False,
                "message": "Email, password, and role are required.",
            }, 400

        user = UserModel.find_by_email(email)
        if not user:
            return {
                "success": False,
                "message": "Invalid email or password.",
            }, 401

        if user["status"] != "Active":
            return {
                "success": False,
                "message": "This account is inactive. Please contact support.",
            }, 403

        if user["role"] != selected_role:
            return {
                "success": False,
                "message": f"This account is registered as {user['role']}, not {selected_role}.",
            }, 403

        if not check_password_hash(user["password_hash"], password):
            return {
                "success": False,
                "message": "Invalid email or password.",
            }, 401

        profile = UserModel.get_role_profile(user["user_id"], user["role"])
        token = AuthController._generate_token(
            secret_key=secret_key,
            user_id=user["user_id"],
            email=user["email"],
            role=user["role"],
            remember_me=remember_me,
        )

        return {
            "success": True,
            "message": "Login successful.",
            "data": {
                "access_token": token,
                "token_type": "Bearer",
                "expires_in_seconds": 2592000 if remember_me else 43200,
                "user": {
                    "user_id": user["user_id"],
                    "email": user["email"],
                    "role": user["role"],
                    "status": user["status"],
                    "display_name": (profile or {}).get("display_name"),
                    "profile_id": (profile or {}).get("profile_id"),
                    "redirect_to": ROLE_DASHBOARD_MAP[user["role"]],
                },
            },
        }, 200

    @staticmethod
    def _normalize_role(role_value):
        if not role_value:
            return None
        return ROLE_ALIASES.get(str(role_value).strip().lower())

    @staticmethod
    def _generate_token(secret_key, user_id, email, role, remember_me):
        serializer = URLSafeTimedSerializer(secret_key)
        expiry = timedelta(days=30) if remember_me else timedelta(hours=12)
        return serializer.dumps(
            {
                "sub": user_id,
                "email": email,
                "role": role,
                "remember_me": remember_me,
                "expires_in_seconds": int(expiry.total_seconds()),
            },
            salt="ijfink-auth",
        )
