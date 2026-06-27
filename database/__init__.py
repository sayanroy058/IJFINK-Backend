import mysql.connector
from flask import current_app, has_app_context

from config import DevelopmentConfig


def get_db_connection():
    config = current_app.config if has_app_context() else DevelopmentConfig
    return mysql.connector.connect(
        host=config["MYSQL_HOST"],
        port=int(config["MYSQL_PORT"]),
        user=config["MYSQL_USER"],
        password=config["MYSQL_PASSWORD"],
        database=config["MYSQL_DATABASE"],
    )
