from database import get_db_connection


class ArticleModel:
    @staticmethod
    def get_author_by_user_id(user_id, connection=None):
        query = """
            SELECT author_id, user_id, first_name, last_name, institution, orcid, phone_number
            FROM authors
            WHERE user_id = %s
            LIMIT 1
        """

        if connection:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query, (user_id,))
                return cursor.fetchone()

        with get_db_connection() as standalone_connection:
            with standalone_connection.cursor(dictionary=True) as cursor:
                cursor.execute(query, (user_id,))
                return cursor.fetchone()

    @staticmethod
    def create_article(connection, author_id, title, abstract, keywords, article_type, subject_area):
        query = """
            INSERT INTO articles (author_id, title, abstract, keywords, article_type, subject_area, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'Submitted')
        """

        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (author_id, title, abstract, keywords, article_type, subject_area),
            )
            return cursor.lastrowid

    @staticmethod
    def create_co_author(connection, article_id, full_name, email, institution, orcid, author_order):
        query = """
            INSERT INTO co_authors (article_id, full_name, email, institution, orcid, author_order)
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (article_id, full_name, email, institution, orcid, author_order),
            )
            return cursor.lastrowid

    @staticmethod
    def get_next_file_version(connection, article_id, file_type):
        query = """
            SELECT COALESCE(MAX(version), 0) + 1 AS next_version
            FROM article_files
            WHERE article_id = %s AND file_type = %s
        """

        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (article_id, file_type))
            result = cursor.fetchone()
            return int(result["next_version"])

    @staticmethod
    def create_article_file(connection, article_id, file_name, file_type, file_path, version):
        query = """
            INSERT INTO article_files (article_id, file_name, file_type, file_path, version)
            VALUES (%s, %s, %s, %s, %s)
        """

        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (article_id, file_name, file_type, file_path, version),
            )
            return cursor.lastrowid

    @staticmethod
    def list_articles_by_author(author_id):
        query = """
            SELECT
                article_id,
                title,
                abstract,
                keywords,
                article_type,
                subject_area,
                status,
                submitted_at,
                updated_at
            FROM articles
            WHERE author_id = %s
            ORDER BY submitted_at DESC, article_id DESC
        """

        with get_db_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query, (author_id,))
                return cursor.fetchall()

    @staticmethod
    def get_article_by_id(article_id, author_id, connection=None):
        query = """
            SELECT
                article_id,
                author_id,
                title,
                abstract,
                keywords,
                article_type,
                subject_area,
                status,
                submitted_at,
                updated_at
            FROM articles
            WHERE article_id = %s AND author_id = %s
            LIMIT 1
        """

        if connection:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query, (article_id, author_id))
                return cursor.fetchone()

        with get_db_connection() as standalone_connection:
            with standalone_connection.cursor(dictionary=True) as cursor:
                cursor.execute(query, (article_id, author_id))
                return cursor.fetchone()

    @staticmethod
    def get_co_authors(article_id, connection=None):
        query = """
            SELECT co_author_id, full_name, email, institution, orcid, author_order
            FROM co_authors
            WHERE article_id = %s
            ORDER BY author_order ASC, co_author_id ASC
        """

        if connection:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query, (article_id,))
                return cursor.fetchall()

        with get_db_connection() as standalone_connection:
            with standalone_connection.cursor(dictionary=True) as cursor:
                cursor.execute(query, (article_id,))
                return cursor.fetchall()

    @staticmethod
    def get_article_files(article_id, connection=None):
        query = """
            SELECT file_id, file_name, file_type, file_path, version, uploaded_at
            FROM article_files
            WHERE article_id = %s
            ORDER BY file_type ASC, version ASC, file_id ASC
        """

        if connection:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query, (article_id,))
                return cursor.fetchall()

        with get_db_connection() as standalone_connection:
            with standalone_connection.cursor(dictionary=True) as cursor:
                cursor.execute(query, (article_id,))
                return cursor.fetchall()

    @staticmethod
    def get_revisions(article_id, connection=None):
        query = """
            SELECT revision_id, editorial_review_id, revision_number, response_letter, submitted_at
            FROM revisions
            WHERE article_id = %s
            ORDER BY revision_number ASC, revision_id ASC
        """

        if connection:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query, (article_id,))
                return cursor.fetchall()

        with get_db_connection() as standalone_connection:
            with standalone_connection.cursor(dictionary=True) as cursor:
                cursor.execute(query, (article_id,))
                return cursor.fetchall()

    @staticmethod
    def get_next_revision_number(connection, article_id):
        query = """
            SELECT COALESCE(MAX(revision_number), 0) + 1 AS next_revision_number
            FROM revisions
            WHERE article_id = %s
        """

        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (article_id,))
            result = cursor.fetchone()
            return int(result["next_revision_number"])

    @staticmethod
    def get_editorial_review_for_revision(connection, article_id, editorial_review_id):
        query = """
            SELECT
                er.editorial_review_id,
                er.decision,
                ea.article_id
            FROM editorial_review er
            JOIN editorial_assignment ea
                ON ea.assignment_id = er.assignment_id
            WHERE er.editorial_review_id = %s
              AND ea.article_id = %s
            LIMIT 1
        """

        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (editorial_review_id, article_id))
            return cursor.fetchone()

    @staticmethod
    def create_revision(connection, article_id, editorial_review_id, author_id, revision_number, response_letter):
        query = """
            INSERT INTO revisions (article_id, editorial_review_id, author_id, revision_number, response_letter)
            VALUES (%s, %s, %s, %s, %s)
        """

        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (article_id, editorial_review_id, author_id, revision_number, response_letter),
            )
            return cursor.lastrowid
