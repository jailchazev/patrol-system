import os
import mimetypes
import secrets
from datetime import timedelta
from flask import Flask, jsonify, redirect, request, url_for
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

    db_url = os.environ.get("DATABASE_URL")
    if production and not db_url:
        raise RuntimeError("DATABASE_URL debe configurarse en producción; SQLite no está permitido.")
    if production and db_url and db_url.startswith("sqlite:"):
        raise RuntimeError("SQLite no está permitido en producción. Configura PostgreSQL.")
    # Render puede entregar postgres:// o postgresql://. Fijamos el driver
    # psycopg2, instalado en requirements.txt.
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif db_url and db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    app.config.update(
        SECRET_KEY=secret or secrets.token_hex(32),
        SQLALCHEMY_DATABASE_URI=db_url or "sqlite:///patrol.db",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,
        SESSION_COOKIE_SECURE=production,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    )

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

    @app.get("/health")
    def health_check():
        # Render solo recibe un estado genérico; nunca se exponen credenciales
        # ni detalles internos de la conexión.
        try:
            db.session.execute(text("SELECT 1"))
            return jsonify({"status": "ok", "database": "connected"}), 200
        except Exception:
            app.logger.exception("Health check: database connection failed")
            db.session.rollback()
            return jsonify({"status": "unavailable", "database": "disconnected"}), 503

    from app.tenancy import TenantAccessError

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
                    "health_check",
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
        from app.tenancy import available_memberships, current_membership
        memberships = available_memberships()
        active_membership = current_membership(required=False)
        return {
            "available_company_count": len(memberships),
            "active_membership": active_membership,
            "active_company": active_membership.company if active_membership else None,
        }

    # No crear tablas ni migrar datos automáticamente durante el despliegue.
    if os.environ.get("AUTO_CREATE_TABLES", "").lower() == "true":
        with app.app_context():
            db.create_all()
    if os.environ.get("AUTO_PROVISION_LEGACY_COMPANY", "").lower() == "true":
        with app.app_context():
            from app.tenancy import provision_legacy_company
            provision_legacy_company()
    return app
