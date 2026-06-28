import mysql.connector
from flask import current_app, has_app_context

from config import DevelopmentConfig


def get_db_connection():
    if has_app_context():
        config = current_app.config
        host = config["MYSQL_HOST"]
        port = int(config["MYSQL_PORT"])
        user = config["MYSQL_USER"]
        password = config["MYSQL_PASSWORD"]
        database = config["MYSQL_DATABASE"]
    else:
        host = DevelopmentConfig.MYSQL_HOST
        port = int(DevelopmentConfig.MYSQL_PORT)
        user = DevelopmentConfig.MYSQL_USER
        password = DevelopmentConfig.MYSQL_PASSWORD
        database = DevelopmentConfig.MYSQL_DATABASE

    return mysql.connector.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
    )
