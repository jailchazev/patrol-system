"""Resolución segura de empresa desde las membresías del usuario autenticado."""
from flask import session
from flask_login import current_user
from sqlalchemy import select

from app import db
from app.models import CompanyMembership


class TenantAccessError(PermissionError):
    pass


def available_memberships():
    """Devuelve solo membresías activas del usuario autenticado."""
    if not current_user.is_authenticated:
        return []
    memberships = db.session.execute(
        select(CompanyMembership).where(
            CompanyMembership.legacy_user_id == current_user.id,
            CompanyMembership.status == "active",
        )
    ).scalars().all()
    return [membership for membership in memberships if membership.is_active()]


def current_membership(*, required=True):
    if not current_user.is_authenticated:
        if required:
            raise TenantAccessError("Se requiere autenticación")
        return None

    memberships = available_memberships()
    if not memberships:
        if required:
            raise TenantAccessError("El usuario no tiene una empresa activa")
        session.pop("active_company_id", None)
        return None

    selected_company_id = session.get("active_company_id")
    if selected_company_id:
        selected = next(
            (m for m in memberships if m.company_id == selected_company_id),
            None,
        )
        if selected:
            return selected
        # La membresía pudo ser revocada o la empresa suspendida.
        session.pop("active_company_id", None)

    if len(memberships) == 1:
        return memberships[0]

    if required:
        raise TenantAccessError("Selecciona una empresa para continuar")
    return None


def current_company(*, required=True):
    membership = current_membership(required=required)
    return membership.company if membership else None


def current_company_id(*, required=True):
    company = current_company(required=required)
    return company.id if company else None


def tenant_query(model, company_id=None):
    """Consulta segura solo para modelos que exponen company_id."""
    company_id = company_id or current_company_id()
    column = getattr(model, "company_id", None)
    if column is None:
        raise TypeError(f"{model.__name__} no tiene company_id")
    return db.session.query(model).filter(column == company_id)


def provision_legacy_company():
    """Asocia los usuarios históricos al tenant inicial; no altera evidencias."""
    from app.models import Company, User, PatrolEvidence

    company = Company.query.filter_by(slug="legacy-migration").first()
    if company is None:
        company = Company(
            name="Empresa migrada (pendiente de configuración)",
            slug="legacy-migration",
            status="trial",
        )
        db.session.add(company)
        db.session.flush()

    for user in User.query.all():
        membership = CompanyMembership.query.filter_by(
            company_id=company.id, legacy_user_id=user.id
        ).first()
        if membership is None:
            role_key = "company_admin" if user.role == "admin" else (
                "supervisor" if user.role == "supervisor" else "guard"
            )
            db.session.add(CompanyMembership(
                company_id=company.id, legacy_user_id=user.id, role_key=role_key
            ))

    for evidence in PatrolEvidence.query.filter(PatrolEvidence.company_id.is_(None)).all():
        evidence.company_id = company.id
    db.session.commit()
    return company
