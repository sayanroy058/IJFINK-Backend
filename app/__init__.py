from flask import Flask, jsonify
from flask_cors import CORS

from app.views.auth_view import auth_blueprint
from app.views.admin_view import admin_blueprint
from app.views.contact_view import contact_blueprint
from app.views.user_view import user_blueprint
from app.views.screening_view import screening_blueprint
from app.views.editorial_view import editorial_blueprint
from app.views.publication_view import publication_blueprint
from app.views.editor_view import editor_blueprint
from app.views.chief_editor_view import chief_editor_blueprint
from config import DevelopmentConfig


def create_app(config_object=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_object)
    CORS(app)
    app.register_blueprint(auth_blueprint, url_prefix="/api/auth")
    app.register_blueprint(admin_blueprint, url_prefix="/api/admin")
    app.register_blueprint(contact_blueprint, url_prefix="/api/contact")
    app.register_blueprint(user_blueprint, url_prefix="/api/user")
    app.register_blueprint(screening_blueprint, url_prefix="/api/screening")
    app.register_blueprint(editorial_blueprint, url_prefix="/api/editorial")
    app.register_blueprint(publication_blueprint, url_prefix="/api/publication")

    @app.get("/health")
    def health_check():
        return jsonify({"success": True, "message": "IJFINK backend is running."}), 200

    return app
