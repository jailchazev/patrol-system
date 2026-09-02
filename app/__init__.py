import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from werkzeug.security import generate_password_hash

# Inicializar extensiones
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

    # Configuración
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'patrol-secret-key-change-me-2026')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///patrol.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB para fotos base64

    # Inicializar extensiones
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Debes iniciar sesión para acceder a esta página.'

    # Importar modelos y registrar rutas
    from app import models  # noqa
    from app.routes import auth_bp, main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    # Crear tablas y usuario admin por defecto
    with app.app_context():
        db.create_all()
        _create_default_admin()

    return app


def _create_default_admin():
    """Crea un usuario admin por defecto si no existe ninguno."""
    from app.models import User
    if not User.query.filter_by(role='admin').first():
        admin = User(
            code='ADMIN',
            name='Administrador del Sistema',
            unit='SISTEMAS',
            post='Administrador',
            role='admin',
            shift='dia',
            password_hash=generate_password_hash('admin123')
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Usuario admin creado: code=ADMIN / password=admin123")