from flask import Flask, jsonify

from app.views.auth_view import auth_blueprint
from config import DevelopmentConfig


def create_app(config_object=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_object)
    app.register_blueprint(auth_blueprint, url_prefix="/api/auth")

    @app.get("/health")
    def health_check():
        return jsonify({"success": True, "message": "IJFINK backend is running."}), 200

    return app
