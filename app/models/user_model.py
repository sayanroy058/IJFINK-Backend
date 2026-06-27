from database import get_db_connection


ROLE_TABLE_MAP = {
    "Author": {
        "table": "authors",
        "id_field": "author_id",
        "name_fields": ("first_name", "last_name"),
    },
    "Admin": {
        "table": "admins",
        "id_field": "admin_id",
        "name_fields": ("first_name", "last_name"),
    },
    "Editor": {
        "table": "editors",
        "id_field": "editor_id",
        "name_fields": ("first_name", "last_name"),
    },
    "Publication Team": {
        "table": "publication_team",
        "id_field": "publication_team_id",
        "name_fields": ("first_name", "last_name"),
    },
}


class UserModel:
    @staticmethod
    def find_by_email(email):
        query = """
            SELECT user_id, email, password_hash, role, status, created_at, updated_at
            FROM users
            WHERE email = %s
            LIMIT 1
        """

        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query, (email,))
                return cursor.fetchone()

    @staticmethod
    def get_role_profile(user_id, role):
        role_config = ROLE_TABLE_MAP.get(role)
        if not role_config:
            return None

        query = f"""
            SELECT *
            FROM {role_config["table"]}
            WHERE user_id = %s
            LIMIT 1
        """

        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query, (user_id,))
                profile = cursor.fetchone()

        if not profile:
            return None

        first_name, last_name = role_config["name_fields"]
        profile["display_name"] = " ".join(
            part for part in [profile.get(first_name), profile.get(last_name)] if part
        ).strip()
        profile["profile_id"] = profile.get(role_config["id_field"])
        return profile
