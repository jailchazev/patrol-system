import uuid
from datetime import datetime
from flask_login import UserMixin
from app import db, login_manager


def generate_uuid():
    return str(uuid.uuid4())


class User(UserMixin, db.Model):
    """Modelo de usuarios (trabajadores)."""
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    unit = db.Column(db.String(100), nullable=True)
    post = db.Column(db.String(100), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='guardia')  # admin, supervisor, guardia
    password_hash = db.Column(db.String(255), nullable=False)
    shift = db.Column(db.String(10), default='dia')  # dia, noche
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    evidences = db.relationship('PatrolEvidence', backref='user', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'unit': self.unit or '',
            'post': self.post or '',
            'role': self.role,
            'shift': self.shift,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class PatrolEvidence(db.Model):
    """Modelo de evidencia de patrullas."""
    __tablename__ = 'patrol_evidences'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    patrol_num = db.Column(db.String(10))          # 01-05
    paquete = db.Column(db.String(100))
    progresiva = db.Column(db.String(100))
    margen = db.Column(db.String(20))              # Derecho / Izquierdo
    zona = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    photos = db.Column(db.JSON, default=list)      # Array de strings base64
    location = db.Column(db.JSON)                  # {lat, lng}
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        user = User.query.get(self.user_id)
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': user.name if user else 'Desconocido',
            'user_role': user.role if user else '',  # ← CAMBIO AGREGADO
            'user_unit': user.unit if user else '',
            'patrol_num': self.patrol_num or '',
            'paquete': self.paquete or '',
            'progresiva': self.progresiva or '',
            'margen': self.margen or '',
            'zona': self.zona or '',
            'descripcion': self.descripcion or '',
            'photos': self.photos or [],
            'location': self.location,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)