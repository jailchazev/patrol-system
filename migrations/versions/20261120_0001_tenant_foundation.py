"""Create tenant foundation and attach legacy evidence to migration company.

Revision ID: 20261120_0001
Revises:
"""
import os
from datetime import datetime
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "20261120_0001"
down_revision = None
branch_labels = None
depends_on = None

LEGACY_COMPANY_ID = "f5a0f35a-6c5b-4c9d-9c70-9f5d84e90a10"


def _require_explicit_approval():
    if os.environ.get("ALLOW_LEGACY_TENANT_MIGRATION", "").lower() != "true":
        raise RuntimeError(
            "Migración multiempresa bloqueada. Revisa el backup y el destino; "
            "define ALLOW_LEGACY_TENANT_MIGRATION=true solo en una base aprobada."
        )


def upgrade():
    _require_explicit_approval()
    from app import db
    from app.models import (
        Company, PlatformUser, CompanyMembership, CompanyRegistrationRequest,
        Permission, CompanyRole, RolePermission, AuditLog,
    )
    bind = op.get_bind()

    # Solo crea tablas nuevas; no modifica ni recrea tablas operativas heredadas.
    db.metadata.create_all(bind=bind, tables=[
        Company.__table__, PlatformUser.__table__, CompanyRegistrationRequest.__table__,
        Permission.__table__, CompanyRole.__table__, CompanyMembership.__table__,
        RolePermission.__table__, AuditLog.__table__,
    ])

    with op.batch_alter_table("patrol_evidences") as batch:
        batch.add_column(sa.Column("company_id", sa.String(length=36), nullable=True))
        batch.create_foreign_key(
            "fk_patrol_evidences_company_id_companies",
            "companies", ["company_id"], ["id"], ondelete="RESTRICT",
        )
    op.create_index("ix_patrol_evidences_company_id", "patrol_evidences", ["company_id"])

    existing = bind.execute(
        sa.text("SELECT id FROM companies WHERE slug = :slug"),
        {"slug": "legacy-migration"},
    ).first()
    if existing:
        company_id = existing[0]
    else:
        company_id = LEGACY_COMPANY_ID
        bind.execute(
            sa.text("""
                INSERT INTO companies (id, name, slug, status, created_at, updated_at)
                VALUES (:id, :name, :slug, :status, :created_at, :updated_at)
            """),
            {
                "id": company_id,
                "name": "Empresa migrada (pendiente de configuración)",
                "slug": "legacy-migration",
                "status": "trial",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
        )

    users = bind.execute(sa.text("SELECT id, role FROM users")).fetchall()
    for user in users:
        exists = bind.execute(
            sa.text("""
                SELECT id FROM company_memberships
                WHERE company_id = :company_id AND legacy_user_id = :user_id
            """),
            {"company_id": company_id, "user_id": user.id},
        ).first()
        if not exists:
            bind.execute(
                sa.text("""
                    INSERT INTO company_memberships
                        (id, company_id, legacy_user_id, role_key, status, created_at)
                    VALUES
                        (:id, :company_id, :user_id, :role_key, 'active', :created_at)
                """),
                {
                    "id": str(uuid4()),
                    "company_id": company_id,
                    "user_id": user.id,
                    "role_key": "company_admin" if user.role == "admin" else (
                        "supervisor" if user.role == "supervisor" else "guard"
                    ),
                    "created_at": datetime.utcnow(),
                },
            )

    bind.execute(
        sa.text("UPDATE patrol_evidences SET company_id = :company_id WHERE company_id IS NULL"),
        {"company_id": company_id},
    )
    with op.batch_alter_table("patrol_evidences") as batch:
        batch.alter_column("company_id", existing_type=sa.String(length=36), nullable=False)

    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE patrol_evidences ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE patrol_evidences FORCE ROW LEVEL SECURITY")
        op.execute("""
            CREATE POLICY patrol_evidence_tenant_isolation ON patrol_evidences
            USING (company_id::text = NULLIF(current_setting('app.current_company_id', true), ''))
            WITH CHECK (company_id::text = NULLIF(current_setting('app.current_company_id', true), ''))
        """)
        op.execute("ALTER TABLE company_memberships ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE company_memberships FORCE ROW LEVEL SECURITY")
        op.execute("""
            CREATE POLICY company_membership_tenant_isolation ON company_memberships
            USING (
                legacy_user_id::text = NULLIF(current_setting('app.current_user_id', true), '')
                OR company_id::text = NULLIF(current_setting('app.current_company_id', true), '')
            )
            WITH CHECK (company_id::text = NULLIF(current_setting('app.current_company_id', true), ''))
        """)
        op.execute("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY")
        op.execute("""
            CREATE POLICY audit_log_tenant_isolation ON audit_logs
            USING (company_id::text = NULLIF(current_setting('app.current_company_id', true), ''))
            WITH CHECK (company_id::text = NULLIF(current_setting('app.current_company_id', true), ''))
        """)
        op.execute("ALTER TABLE company_roles ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE company_roles FORCE ROW LEVEL SECURITY")
        op.execute("""
            CREATE POLICY company_roles_tenant_isolation ON company_roles
            USING (company_id::text = NULLIF(current_setting('app.current_company_id', true), ''))
            WITH CHECK (company_id::text = NULLIF(current_setting('app.current_company_id', true), ''))
        """)


def downgrade():
    _require_explicit_approval()
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP POLICY IF EXISTS patrol_evidence_tenant_isolation ON patrol_evidences")
        op.execute("ALTER TABLE patrol_evidences NO FORCE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE patrol_evidences DISABLE ROW LEVEL SECURITY")
        op.execute("DROP POLICY IF EXISTS company_membership_tenant_isolation ON company_memberships")
        op.execute("ALTER TABLE company_memberships NO FORCE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE company_memberships DISABLE ROW LEVEL SECURITY")
        op.execute("DROP POLICY IF EXISTS audit_log_tenant_isolation ON audit_logs")
        op.execute("ALTER TABLE audit_logs NO FORCE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE audit_logs DISABLE ROW LEVEL SECURITY")
        op.execute("DROP POLICY IF EXISTS company_roles_tenant_isolation ON company_roles")
        op.execute("ALTER TABLE company_roles NO FORCE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE company_roles DISABLE ROW LEVEL SECURITY")

    op.drop_index("ix_patrol_evidences_company_id", table_name="patrol_evidences")
    with op.batch_alter_table("patrol_evidences") as batch:
        batch.drop_constraint("fk_patrol_evidences_company_id_companies", type_="foreignkey")
        batch.drop_column("company_id")

    from app import db
    from app.models import (
        AuditLog, RolePermission, CompanyMembership, CompanyRole,
        Permission, CompanyRegistrationRequest, PlatformUser, Company,
    )
    db.metadata.drop_all(bind=bind, tables=[
        AuditLog.__table__, RolePermission.__table__, CompanyMembership.__table__,
        CompanyRole.__table__, Permission.__table__, CompanyRegistrationRequest.__table__,
        PlatformUser.__table__, Company.__table__,
    ])
