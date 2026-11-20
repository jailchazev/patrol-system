import os
import mimetypes
import secrets
from datetime import timedelta
from flask import Flask, redirect, request, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from sqlalchemy import text

mimetypes.add_type("application/manifest+json", ".webmanifest")
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()


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
    # El proyecto instala psycopg2-binary; seleccionar el driver explícitamente
    # evita que SQLAlchemy 2.1 intente importar psycopg (psycopg3).
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif db_url and db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url or "sqlite:///patrol.db"

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Debes iniciar sesión para acceder a esta página."

    from app import models  # noqa: F401
    from app.routes import auth_bp, main_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    from app.tenancy import TenantAccessError
    from flask import jsonify

    @app.errorhandler(TenantAccessError)
    def tenant_access_error(error):
        return jsonify({"error": str(error)}), 403

    @app.before_request
    def establish_tenant_database_context():
        from flask_login import current_user
        if not current_user.is_authenticated:
            return None
        from app.tenancy import current_company_id
        if db.engine.dialect.name == "postgresql":
            db.session.execute(
                text("SELECT set_config('app.current_user_id', :user_id, true)"),
                {"user_id": str(current_user.id)},
            )
            company_id = current_company_id(required=False)
            if company_id:
                db.session.execute(
                    text("SELECT set_config('app.current_company_id', :company_id, true)"),
                    {"company_id": company_id},
                )
        else:
            company_id = current_company_id(required=False)

        # Evita que una cuenta multiempresa entre por una URL guardada sin elegir tenant.
        if not company_id:
            from app.tenancy import available_memberships
            if len(available_memberships()) > 1:
                allowed_endpoints = {
                    "auth.company_selector",
                    "auth.list_available_companies",
                    "auth.select_company",
                    "auth.logout",
                    "main.service_worker",
                    "main.manifest_file",
                    "static",
                }
                if request.endpoint not in allowed_endpoints and not request.path.startswith("/api/"):
                    return redirect(url_for("auth.company_selector"))
        return None

    @app.context_processor
    def inject_company_context():
        from flask_login import current_user
        if not current_user.is_authenticated:
            return {"available_company_count": 0, "active_company": None}
        from app.tenancy import available_memberships, current_company
        memberships = available_memberships()
        return {
            "available_company_count": len(memberships),
            "active_company": current_company(required=False),
        }

    if os.environ.get("AUTO_CREATE_TABLES", "").lower() == "true":
        with app.app_context():
            db.create_all()
    if os.environ.get("AUTO_PROVISION_LEGACY_COMPANY", "").lower() == "true":
        with app.app_context():
            from app.tenancy import provision_legacy_company
            provision_legacy_company()
    return app
