"""Helpers para resolver el tenant desde la sesión validada, nunca desde el request."""
from flask_login import current_user
from sqlalchemy import select
from app import db
from app.models import Company, CompanyMembership


class TenantAccessError(PermissionError):
    pass


def current_membership(*, required=True):
    """Devuelve la membresía activa del usuario heredado autenticado."""
    if not current_user.is_authenticated:
        if required:
            raise TenantAccessError("Se requiere autenticación")
        return None
    membership = db.session.execute(
        select(CompanyMembership).where(
            CompanyMembership.legacy_user_id == current_user.id,
            CompanyMembership.status == 'active'
        )
    ).scalar_one_or_none()
    if membership is None or not membership.is_active():
        if required:
            raise TenantAccessError("El usuario no tiene una empresa activa")
        return None
    return membership


def current_company(*, required=True):
    membership = current_membership(required=required)
    return membership.company if membership else None


def tenant_query(model, company_id, company_column=None):
    """Plantilla para consultas tenant-scoped; requiere columna company_id en el modelo."""
    column = company_column or getattr(model, 'company_id', None)
    if column is None:
        raise TypeError(f"{model.__name__} todavía no tiene company_id; no usar consulta sin aislamiento")
    return db.session.query(model).filter(column == company_id)


def provision_legacy_company():
    """Asocia usuarios existentes al tenant de transición sin tocar sus evidencias."""
    company = Company.query.filter_by(slug='legacy-migration').first()
    users = db.session.query(__import__('app.models', fromlist=['User']).User).all()
    if not users:
        return None
    if company is None:
        company = Company(
            name='Empresa migrada (pendiente de configuración)',
            slug='legacy-migration',
            status='trial'
        )
        db.session.add(company)
        db.session.flush()
    for user in users:
        exists = CompanyMembership.query.filter_by(
            company_id=company.id, legacy_user_id=user.id
        ).first()
        if not exists:
            role_key = 'company_admin' if user.role == 'admin' else (
                'supervisor' if user.role == 'supervisor' else 'guard'
            )
            db.session.add(CompanyMembership(
                company_id=company.id, legacy_user_id=user.id, role_key=role_key
            ))
    db.session.commit()
    return company
