from base64 import urlsafe_b64encode, urlsafe_b64decode
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json

from mysql.connector import Error as MySQLError
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_db_connection
from app.models.user_model import UserModel


ROLE_ALIASES = {
    "author": "Author",
    "admin": "Admin",
    "editor": "Editor",
    "chief editor": "Editor",
    "chief_editor": "Editor",
    "chief-editor": "Editor",
    "publication team": "Publication Team",
    "publication_team": "Publication Team",
    "publication-team": "Publication Team",
}

ROLE_DASHBOARD_MAP = {
    "Author": "/user/dashboard",
    "Admin": "/admin/dashboard",
    "Editor": "/editor/dashboard",
    "Chief Editor": "/chief-editor/dashboard",
    "Publication Team": "/publication-team/dashboard",
}


class AuthController:
    @staticmethod
    def login(payload, secret_key):
        email = (payload.get("email") or "").strip().lower()
        password = payload.get("password") or ""
        selected_role = AuthController._normalize_role(payload.get("role"))
        remember_me = bool(payload.get("remember_me", False))

        if not email or not password:
            return {
                "success": False,
                "message": "Email and password are required.",
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

        if selected_role and user["role"] != selected_role:
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
        redirect_to = AuthController._resolve_dashboard_route(user["role"], profile)
        token = AuthController._generate_jwt(
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
                    "redirect_to": redirect_to,
                },
            },
        }, 200

    @staticmethod
    def register(payload, secret_key, authorization_header=None):
        actor = AuthController._get_authenticated_actor(secret_key, authorization_header)
        requested_role = AuthController._normalize_role(payload.get("role"))

        first_name = AuthController._clean_text(payload.get("first_name"))
        last_name = AuthController._clean_text(payload.get("last_name"))
        email = AuthController._clean_text(payload.get("email"), lower=True)
        password = payload.get("password") or ""
        confirm_password = payload.get("confirm_password") or payload.get("confirmPassword") or ""
        institution = AuthController._clean_text(payload.get("institution"))
        orcid = AuthController._clean_text(payload.get("orcid"))
        phone_number = AuthController._clean_text(payload.get("phone_number") or payload.get("phoneNumber"))
        is_chief_editor = AuthController._parse_bool(
            payload.get("is_chief_editor", payload.get("isChiefEditor", False))
        )

        if not first_name or not last_name or not email or not password:
            return {
                "success": False,
                "message": "First name, last name, email, and password are required.",
            }, 400

        if confirm_password and password != confirm_password:
            return {
                "success": False,
                "message": "Password and confirm password do not match.",
            }, 400

        wants_admin_flow = requested_role in {"Admin", "Editor", "Publication Team"} or is_chief_editor
        is_admin_actor = bool(actor and actor["role"] == "Admin")

        if wants_admin_flow:
            if not actor:
                return {
                    "success": False,
                    "message": "Admin token is required to create Admin, Editor, or Publication Team accounts.",
                }, 401

            if not is_admin_actor:
                return {
                    "success": False,
                    "message": "Only Admin users can create Admin, Editor, or Publication Team accounts.",
                }, 403

            if not requested_role:
                return {
                    "success": False,
                    "message": "Role is required when an admin creates a user.",
                }, 400

            if actor["user_id"] == 1:
                if requested_role not in {"Admin", "Editor", "Publication Team"}:
                    return {
                        "success": False,
                        "message": "Admin 1 can create only Admin, Editor, or Publication Team accounts.",
                    }, 400
                effective_role = requested_role
            else:
                if requested_role == "Admin":
                    return {
                        "success": False,
                        "message": "Only Admin 1 can create Admin accounts.",
                    }, 403
                if requested_role not in {"Editor", "Publication Team"}:
                    return {
                        "success": False,
                        "message": "Admins can create only Editor or Publication Team accounts.",
                    }, 403
                effective_role = requested_role

            if effective_role == "Editor" and is_chief_editor and actor["user_id"] != 1:
                return {
                    "success": False,
                    "message": "Only Admin 1 can create the chief editor.",
                }, 403
        else:
            if actor and actor["role"] == "Admin" and requested_role is None:
                return {
                    "success": False,
                    "message": "Role is required when an admin creates a user.",
                }, 400
            effective_role = "Author"

        if effective_role == "Author":
            if not institution:
                return {
                    "success": False,
                    "message": "Institution is required for author registration.",
                }, 400
        elif effective_role == "Editor":
            if not institution:
                return {
                    "success": False,
                    "message": "Institution is required for editor registration.",
                }, 400

        existing_user = UserModel.find_by_email(email)
        if existing_user:
            return {
                "success": False,
                "message": "An account with this email already exists.",
            }, 409

        connection = None
        try:
            connection = get_db_connection()
            connection.start_transaction()
            password_hash = generate_password_hash(password)
            user_id = UserModel.create_user(connection, email, password_hash, effective_role)

            if effective_role == "Author":
                UserModel.create_author_profile(
                    connection,
                    user_id,
                    first_name,
                    last_name,
                    institution,
                    orcid or None,
                    phone_number or None,
                )
            elif effective_role == "Admin":
                UserModel.create_admin_profile(
                    connection,
                    user_id,
                    first_name,
                    last_name,
                )
            elif effective_role == "Editor":
                UserModel.create_editor_profile(
                    connection,
                    user_id,
                    first_name,
                    last_name,
                    institution,
                    is_chief_editor,
                )
            elif effective_role == "Publication Team":
                UserModel.create_publication_team_profile(
                    connection,
                    user_id,
                    first_name,
                    last_name,
                )
            else:
                raise ValueError("Unsupported role requested.")

            connection.commit()
        except MySQLError as exc:
            if connection:
                connection.rollback()

            error_message = str(exc)
            if getattr(exc, "errno", None) == 1062:
                return {
                    "success": False,
                    "message": "An account with this email already exists.",
                }, 409

            if "Only one editor can be marked as chief editor" in error_message:
                return {
                    "success": False,
                    "message": "A chief editor already exists.",
                }, 409

            if "must reference a user with role" in error_message:
                return {
                    "success": False,
                    "message": error_message,
                }, 400

            return {
                "success": False,
                "message": "Unable to create the requested account.",
            }, 400
        except ValueError as exc:
            if connection:
                connection.rollback()
            return {
                "success": False,
                "message": str(exc),
            }, 400
        finally:
            if connection:
                connection.close()

        created_user = UserModel.find_by_id(user_id)
        profile = UserModel.get_role_profile(user_id, effective_role)
        return {
            "success": True,
            "message": f"{effective_role} account created successfully.",
            "data": {
                "user": {
                    "user_id": created_user["user_id"],
                    "email": created_user["email"],
                    "role": created_user["role"],
                    "status": created_user["status"],
                    "display_name": (profile or {}).get("display_name"),
                    "profile_id": (profile or {}).get("profile_id"),
                    "redirect_to": AuthController._resolve_dashboard_route(created_user["role"], profile),
                },
            },
        }, 201

    @staticmethod
    def _normalize_role(role_value):
        if not role_value:
            return None
        return ROLE_ALIASES.get(str(role_value).strip().lower())

    @staticmethod
    def _clean_text(value, lower=False):
        if value is None:
            return None
        cleaned = str(value).strip()
        if not cleaned:
            return None
        return cleaned.lower() if lower else cleaned

    @staticmethod
    def _parse_bool(value):
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, (int, float)):
            return bool(value)
        return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}

    @staticmethod
    def _generate_jwt(secret_key, user_id, email, role, remember_me):
        now = datetime.now(timezone.utc)
        expiry = timedelta(days=30) if remember_me else timedelta(hours=12)
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": str(user_id),
            "email": email,
            "role": role,
            "remember_me": remember_me,
            "iat": int(now.timestamp()),
            "exp": int((now + expiry).timestamp()),
        }
        return AuthController._jwt_encode(header, payload, secret_key)

    @staticmethod
    def _jwt_encode(header, payload, secret_key):
        header_bytes = json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
        payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        signing_input = f"{AuthController._b64url_encode(header_bytes)}.{AuthController._b64url_encode(payload_bytes)}"
        signature = hmac.new(
            AuthController._to_bytes(secret_key),
            signing_input.encode("ascii"),
            hashlib.sha256,
        ).digest()
        return f"{signing_input}.{AuthController._b64url_encode(signature)}"

    @staticmethod
    def _jwt_decode(token, secret_key):
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token format.")

        header_b64, payload_b64, signature_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_signature = hmac.new(
            AuthController._to_bytes(secret_key),
            signing_input,
            hashlib.sha256,
        ).digest()
        provided_signature = AuthController._b64url_decode(signature_b64)

        if not hmac.compare_digest(expected_signature, provided_signature):
            raise ValueError("Invalid token signature.")

        header = json.loads(AuthController._b64url_decode(header_b64).decode("utf-8"))
        payload = json.loads(AuthController._b64url_decode(payload_b64).decode("utf-8"))

        if header.get("alg") != "HS256":
            raise ValueError("Unsupported token algorithm.")

        exp = payload.get("exp")
        if exp is None or int(datetime.now(timezone.utc).timestamp()) > int(exp):
            raise ValueError("Token has expired.")

        return payload

    @staticmethod
    def _to_bytes(value):
        return value.encode("utf-8") if isinstance(value, str) else bytes(value)

    @staticmethod
    def _b64url_encode(raw_bytes):
        return urlsafe_b64encode(raw_bytes).rstrip(b"=").decode("ascii")

    @staticmethod
    def _b64url_decode(value):
        padded = value + "=" * (-len(value) % 4)
        return urlsafe_b64decode(padded.encode("ascii"))

    @staticmethod
    def _get_authenticated_actor(secret_key, authorization_header):
        token = AuthController._extract_bearer_token(authorization_header)
        if not token:
            return None

        try:
            payload = AuthController._jwt_decode(token, secret_key)
        except Exception:
            return None

        if not isinstance(payload, dict):
            return None

        try:
            user_id = int(payload.get("sub"))
        except (TypeError, ValueError):
            return None

        user = UserModel.find_by_id(user_id)
        if not user or user["status"] != "Active":
            return None

        if user["role"] != payload.get("role"):
            return None

        return user

    @staticmethod
    def _extract_bearer_token(authorization_header):
        if not authorization_header:
            return None

        header_value = str(authorization_header).strip()
        if not header_value:
            return None

        if header_value.lower().startswith("bearer "):
            return header_value.split(None, 1)[1].strip() or None
        return header_value

    @staticmethod
    def _resolve_dashboard_route(role, profile):
        if role == "Editor":
            is_chief_editor = bool((profile or {}).get("is_chief_editor"))
            return "/dashboard/chief-editor" if is_chief_editor else "/dashboard/editor"

        return ROLE_DASHBOARD_MAP.get(role, "/dashboard")
