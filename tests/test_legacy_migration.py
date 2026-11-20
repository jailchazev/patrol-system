import importlib.util
from pathlib import Path

import pytest

from app import create_app, db
from app.models import Company, CompanyMembership, PatrolEvidence


def test_legacy_database_migration_preserves_and_assigns_records(monkeypatch):
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("SECRET_KEY", "migration-test-only-secret")
    monkeypatch.setenv("ALLOW_LEGACY_TENANT_MIGRATION", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.delenv("AUTO_CREATE_TABLES", raising=False)
    app = create_app()
    app.config.update(TESTING=True)

    # Simula exactamente las dos tablas heredadas antes de Alembic.
    with app.app_context():
        with db.engine.begin() as connection:
            connection.exec_driver_sql("""
                CREATE TABLE users (
                    id VARCHAR(36) PRIMARY KEY,
                    code VARCHAR(50) NOT NULL UNIQUE,
                    name VARCHAR(150) NOT NULL,
                    unit VARCHAR(100),
                    post VARCHAR(100),
                    role VARCHAR(20) NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    shift VARCHAR(10),
                    created_at DATETIME
                )
            """)
            connection.exec_driver_sql("""
                CREATE TABLE patrol_evidences (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    patrol_num VARCHAR(10),
                    paquete VARCHAR(100),
                    progresiva VARCHAR(100),
                    margen VARCHAR(20),
                    zona VARCHAR(150) NOT NULL,
                    descripcion TEXT NOT NULL,
                    photos JSON,
                    location JSON,
                    timestamp DATETIME,
                    created_at DATETIME,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """)
            connection.exec_driver_sql("""
                INSERT INTO users (id, code, name, role, password_hash)
                VALUES ('legacy-user-1', 'LEGACY-01', 'Agente histórico', 'guardia', 'hash-preservado')
            """)
            connection.exec_driver_sql("""
                INSERT INTO patrol_evidences (id, user_id, zona, descripcion, photos)
                VALUES ('legacy-evidence-1', 'legacy-user-1', 'Zona histórica', 'Registro que no se debe perder', '[]')
            """)

    result = app.test_cli_runner().invoke(args=["db", "upgrade"])
    assert result.exit_code == 0, result.output

    with app.app_context():
        company = Company.query.filter_by(slug="legacy-migration").one()
        membership = CompanyMembership.query.filter_by(
            company_id=company.id, legacy_user_id="legacy-user-1"
        ).one()
        evidence = PatrolEvidence.query.filter_by(id="legacy-evidence-1").one()
        assert membership.role_key == "guard"
        assert evidence.company_id == company.id
        assert evidence.descripcion == "Registro que no se debe perder"
        assert evidence.photos == []


def test_tenant_migration_requires_explicit_approval(monkeypatch):
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "20261120_0001_tenant_foundation.py"
    )
    spec = importlib.util.spec_from_file_location("tenant_foundation_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    monkeypatch.delenv("ALLOW_LEGACY_TENANT_MIGRATION", raising=False)
    with pytest.raises(RuntimeError, match="Migración multiempresa bloqueada"):
        migration._require_explicit_approval()
