import os
import mimetypes
import secrets
from datetime import timedelta
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

mimetypes.add_type("application/manifest+json", ".webmanifest")
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    production = os.environ.get("APP_ENV", "").lower() == "production"
    secret = os.environ.get("SECRET_KEY")
    if production and not secret:
        raise RuntimeError("SECRET_KEY debe configurarse en producción.")
    app.config.update(
        SECRET_KEY=secret or secrets.token_hex(32),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,
        SESSION_COOKIE_SECURE=production,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    )
    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url or "sqlite:///patrol.db"

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Debes iniciar sesión para acceder a esta página."

    from app import models  # noqa: F401
    from app.routes import auth_bp, main_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    if os.environ.get("AUTO_CREATE_TABLES", "").lower() == "true":
        with app.app_context():
            db.create_all()
    if os.environ.get("AUTO_PROVISION_LEGACY_COMPANY", "").lower() == "true":
        with app.app_context():
            from app.tenancy import provision_legacy_company
            provision_legacy_company()
    return app
