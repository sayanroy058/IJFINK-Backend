"""Application configuration"""

import os
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _env_bool(name, default=False):
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ('1', 'true', 'yes', 'on')


class Config:
    """Base configuration"""

    # Redis
    REDIS_URI = os.getenv('REDIS_URI')
    REDIS_HOST = os.getenv('REDIS_HOST')
    REDIS_PORT = os.getenv('REDIS_PORT', 16190)
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')

    # MySQL
    MYSQL_HOST = os.getenv('MYSQL_HOST', '127.0.0.1')
    MYSQL_PORT = os.getenv('MYSQL_PORT', 3306)
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'journaldb')

    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY')
    DEBUG = _env_bool('DEBUG', False)
    UPLOAD_ROOT = os.getenv('UPLOAD_ROOT', os.path.join(BASE_DIR, 'uploads'))
    PUBLISHED_ROOT = os.getenv('PUBLISHED_ROOT', os.path.join(BASE_DIR, 'Published'))


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SECRET_KEY = os.getenv('SECRET_KEY')


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
