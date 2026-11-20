import uuid
from datetime import datetime
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint, Index
from app import db, login_manager


def generate_uuid():
    return str(uuid.uuid4())


class Company(db.Model):
    """Tenant de la plataforma. Los datos operativos pertenecen a una empresa."""
    __tablename__ = 'companies'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(180), nullable=False)
    slug = db.Column(db.String(100), nullable=False, unique=True, index=True)
    tax_id = db.Column(db.String(30), nullable=True, index=True)
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    memberships = db.relationship('CompanyMembership', back_populates='company', cascade='all, delete-orphan')


class PlatformUser(db.Model):
    """Identidad global; puede pertenecer a varias empresas."""
    __tablename__ = 'platform_users'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    full_name = db.Column(db.String(180), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_superadmin = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class CompanyMembership(db.Model):
    """Vincula una identidad de plataforma o usuario heredado con un tenant."""
    __tablename__ = 'company_memberships'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    company_id = db.Column(db.String(36), db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    platform_user_id = db.Column(db.String(36), db.ForeignKey('platform_users.id', ondelete='CASCADE'), nullable=True, index=True)
    legacy_user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    role_key = db.Column(db.String(60), nullable=False, default='guard')
    status = db.Column(db.String(20), nullable=False, default='active')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    company = db.relationship('Company', back_populates='memberships')
    platform_user = db.relationship('PlatformUser')
    legacy_user = db.relationship('User')

    __table_args__ = (
        UniqueConstraint('company_id', 'platform_user_id', name='uq_membership_company_platform_user'),
        UniqueConstraint('company_id', 'legacy_user_id', name='uq_membership_company_legacy_user'),
    )

    def is_active(self):
        return self.status == 'active' and self.company.status in ('trial', 'active')


class CompanyRegistrationRequest(db.Model):
    __tablename__ = 'company_registration_requests'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    company_name = db.Column(db.String(180), nullable=False)
    requester_name = db.Column(db.String(180), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    phone = db.Column(db.String(40), nullable=True)
    tax_id = db.Column(db.String(30), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)
    reviewed_by = db.Column(db.String(36), db.ForeignKey('platform_users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Permission(db.Model):
    __tablename__ = 'permissions'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    key = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=False, default='')


class CompanyRole(db.Model):
    __tablename__ = 'company_roles'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    company_id = db.Column(db.String(36), db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    key = db.Column(db.String(60), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_system = db.Column(db.Boolean, nullable=False, default=False)
    __table_args__ = (UniqueConstraint('company_id', 'key', name='uq_company_role_key'),)


class RolePermission(db.Model):
    __tablename__ = 'role_permissions'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    role_id = db.Column(db.String(36), db.ForeignKey('company_roles.id', ondelete='CASCADE'), nullable=False, index=True)
    permission_id = db.Column(db.String(36), db.ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False, index=True)
    __table_args__ = (UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),)


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    company_id = db.Column(db.String(36), db.ForeignKey('companies.id', ondelete='SET NULL'), nullable=True, index=True)
    actor_platform_user_id = db.Column(db.String(36), db.ForeignKey('platform_users.id'), nullable=True)
    actor_legacy_user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(100), nullable=False)
    resource_id = db.Column(db.String(100), nullable=True)
    details = db.Column(db.JSON, nullable=False, default=dict)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)


class User(UserMixin, db.Model):
    """Modelo heredado de usuarios (se conserva durante la migración)."""
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    unit = db.Column(db.String(100), nullable=True)
    post = db.Column(db.String(100), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='guardia')
    password_hash = db.Column(db.String(255), nullable=False)
    shift = db.Column(db.String(10), default='dia')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    evidences = db.relationship('PatrolEvidence', backref='user', lazy=True, cascade='all, delete-orphan')
    memberships = db.relationship('CompanyMembership', back_populates='legacy_user', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id, 'code': self.code, 'name': self.name,
            'unit': self.unit or '', 'post': self.post or '',
            'role': self.role, 'shift': self.shift,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class PatrolEvidence(db.Model):
    """Evidencia heredada; se conserva sin alterar durante la migración."""
    __tablename__ = 'patrol_evidences'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    patrol_num = db.Column(db.String(10))
    paquete = db.Column(db.String(100))
    progresiva = db.Column(db.String(100))
    margen = db.Column(db.String(20))
    zona = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    photos = db.Column(db.JSON, default=list)
    location = db.Column(db.JSON)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        user = User.query.get(self.user_id)
        return {
            'id': self.id, 'user_id': self.user_id,
            'user_name': user.name if user else 'Desconocido',
            'user_role': user.role if user else '',
            'user_unit': user.unit if user else '',
            'patrol_num': self.patrol_num or '', 'paquete': self.paquete or '',
            'progresiva': self.progresiva or '', 'margen': self.margen or '',
            'zona': self.zona or '', 'descripcion': self.descripcion or '',
            'photos': self.photos or [], 'location': self.location,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)
