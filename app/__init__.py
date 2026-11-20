import os
import mimetypes
import secrets
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

mimetypes.add_type('application/manifest+json', '.webmanifest')
db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    db_url = os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url or 'sqlite:///patrol.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Debes iniciar sesión para acceder a esta página.'

    from app import models  # noqa: F401
    from app.routes import auth_bp, main_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()
        from app.tenancy import provision_legacy_company
        provision_legacy_company()

    return app
