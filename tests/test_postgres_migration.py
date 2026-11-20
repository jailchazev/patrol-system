"""End-to-end legacy migration and rollback test on disposable PostgreSQL.

SAFETY: this test refuses to run unless TEST_POSTGRES_MIGRATION_URL points to
a database named exactly patrol_migration_test. It drops/recreates public schema.
"""
import os

import psycopg2
import pytest

from app import create_app


MIGRATION_URL = os.getenv("TEST_POSTGRES_MIGRATION_URL")
APP_URL = os.getenv("TEST_POSTGRES_MIGRATION_APP_URL")
pytestmark = pytest.mark.skipif(
    not MIGRATION_URL or not APP_URL,
    reason="Configura TEST_POSTGRES_MIGRATION_URL y TEST_POSTGRES_MIGRATION_APP_URL",
)


def _connect():
    conn = psycopg2.connect(MIGRATION_URL)
    if conn.get_dsn_parameters().get("dbname") != "patrol_migration_test":
        conn.close()
        raise RuntimeError(
            "Bloqueado: TEST_POSTGRES_MIGRATION_URL debe apuntar a "
            "la base desechable patrol_migration_test"
        )
    return conn


def test_postgres_upgrade_and_downgrade_preserve_legacy_data(monkeypatch):
    conn = _connect()
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            # Esta base es exclusiva de CI. Se limpia solo su esquema público.
            cur.execute("DROP SCHEMA public CASCADE")
            cur.execute("CREATE SCHEMA public")
            cur.execute("GRANT ALL ON SCHEMA public TO postgres")
            cur.execute("GRANT ALL ON SCHEMA public TO public")
            cur.execute("""
                CREATE TABLE users (
                    id VARCHAR(36) PRIMARY KEY,
                    code VARCHAR(50) NOT NULL UNIQUE,
                    name VARCHAR(150) NOT NULL,
                    unit VARCHAR(100),
                    post VARCHAR(100),
                    role VARCHAR(20) NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    shift VARCHAR(10),
                    created_at TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE patrol_evidences (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
                    patrol_num VARCHAR(10),
                    paquete VARCHAR(100),
                    progresiva VARCHAR(100),
                    margen VARCHAR(20),
                    zona VARCHAR(150) NOT NULL,
                    descripcion TEXT NOT NULL,
                    photos JSON,
                    location JSON,
                    timestamp TIMESTAMP,
                    created_at TIMESTAMP
                )
            """)
            cur.execute("""
                INSERT INTO users
                    (id, code, name, role, password_hash, shift)
                VALUES
                    ('legacy-user-pg', 'PG-LEGACY-01', 'Administrador histórico',
                     'admin', 'hash-original', 'dia')
            """)
            cur.execute("""
                INSERT INTO patrol_evidences
                    (id, user_id, patrol_num, zona, descripcion, photos, location)
                VALUES
                    ('legacy-evidence-pg', 'legacy-user-pg', 'P-77',
                     'Zona original', 'Evidencia PostgreSQL que debe conservarse',
                     '["https://res.cloudinary.com/demo/image/upload/photo.jpg"]',
                     '{"lat":-8.11,"lng":-79.02}')
            """)

        monkeypatch.setenv("APP_ENV", "testing")
        monkeypatch.setenv("SECRET_KEY", "postgres-migration-test-only")
        monkeypatch.setenv("ALLOW_LEGACY_TENANT_MIGRATION", "true")
        monkeypatch.setenv("DATABASE_URL", MIGRATION_URL)
        monkeypatch.delenv("AUTO_CREATE_TABLES", raising=False)
        monkeypatch.delenv("AUTO_PROVISION_LEGACY_COMPANY", raising=False)
        app = create_app()
        app.config.update(TESTING=True)

        upgraded = app.test_cli_runner().invoke(args=["db", "upgrade"])
        assert upgraded.exit_code == 0, upgraded.output

        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*), MIN(company_id), MAX(company_id)
                FROM patrol_evidences
            """)
            evidence_count, min_company, max_company = cur.fetchone()
            assert evidence_count == 1
            assert min_company == max_company
            assert min_company == "f5a0f35a-6c5b-4c9d-9c70-9f5d84e90a10"

            cur.execute("""
                SELECT photos::text, location::text, descripcion, user_id
                FROM patrol_evidences WHERE id = 'legacy-evidence-pg'
            """)
            photos, location, description, user_id = cur.fetchone()
            assert "cloudinary.com" in photos
            assert "-8.11" in location
            assert description == "Evidencia PostgreSQL que debe conservarse"
            assert user_id == "legacy-user-pg"

            cur.execute("""
                SELECT role_key, status
                FROM company_memberships
                WHERE legacy_user_id = 'legacy-user-pg'
            """)
            assert cur.fetchone() == ("company_admin", "active")

            cur.execute("""
                SELECT COUNT(*) FROM pg_policies
                WHERE schemaname = 'public'
                  AND tablename IN (
                    'patrol_evidences', 'company_memberships',
                    'company_roles', 'audit_logs'
                  )
            """)
            assert cur.fetchone()[0] >= 4

            # Crea una segunda empresa y una evidencia que el rol de aplicación no debe ver.
            cur.execute("""
                INSERT INTO companies (id, name, slug, status, created_at, updated_at)
                VALUES ('company-b-pg', 'Empresa B', 'empresa-b-pg', 'active', NOW(), NOW())
            """)
            cur.execute("""
                INSERT INTO company_memberships
                    (id, company_id, legacy_user_id, role_key, status, created_at)
                VALUES
                    ('membership-company-b', 'company-b-pg', 'legacy-user-pg',
                     'guard', 'active', NOW())
            """)
            cur.execute("""
                INSERT INTO patrol_evidences
                    (id, company_id, user_id, zona, descripcion)
                VALUES
                    ('evidence-company-b', 'company-b-pg', 'legacy-user-pg',
                     'Zona B', 'No debe ser visible desde empresa A')
            """)
            cur.execute("""
                GRANT USAGE ON SCHEMA public TO patrol_rls_app
            """)
            cur.execute("""
                GRANT SELECT, INSERT, UPDATE, DELETE
                ON patrol_evidences, company_memberships, companies
                TO patrol_rls_app
            """)

        # Valida las políticas creadas por la migración usando el rol real restringido.
        app_conn = psycopg2.connect(APP_URL)
        try:
            with app_conn:
                with app_conn.cursor() as cur:
                    cur.execute("""
                        SELECT r.rolname, r.rolsuper, r.rolbypassrls,
                               pg_get_userbyid(t.relowner) = current_user
                        FROM pg_roles r
                        CROSS JOIN pg_class t
                        JOIN pg_namespace n ON n.oid = t.relnamespace
                        WHERE r.rolname = current_user
                          AND n.nspname = 'public'
                          AND t.relname = 'patrol_evidences'
                    """)
                    assert cur.fetchone() == ("patrol_rls_app", False, False, False)

                    # La membresía propia puede leerse antes de seleccionar empresa.
                    cur.execute(
                        "SELECT set_config('app.current_user_id', %s, true)",
                        ('legacy-user-pg',),
                    )
                    cur.execute("""
                        SELECT company_id, role_key FROM company_memberships
                        WHERE legacy_user_id = 'legacy-user-pg'
                    """)
                    assert set(cur.fetchall()) == {
                        ('f5a0f35a-6c5b-4c9d-9c70-9f5d84e90a10', 'company_admin'),
                        ('company-b-pg', 'guard'),
                    }

                    cur.execute(
                        "SELECT set_config('app.current_company_id', %s, true)",
                        ('f5a0f35a-6c5b-4c9d-9c70-9f5d84e90a10',),
                    )
                    cur.execute("""
                        SELECT id FROM patrol_evidences ORDER BY id
                    """)
                    assert cur.fetchall() == [('legacy-evidence-pg',)]

                    cur.execute(
                        "SELECT set_config('app.current_company_id', %s, true)",
                        ('company-b-pg',),
                    )
                    cur.execute("SELECT id FROM patrol_evidences ORDER BY id")
                    assert cur.fetchall() == [('evidence-company-b',)]

                    cur.execute(
                        "SELECT set_config('app.current_company_id', %s, true)",
                        ('f5a0f35a-6c5b-4c9d-9c70-9f5d84e90a10',),
                    )
                    cur.execute("""
                        UPDATE patrol_evidences SET descripcion = 'ataque'
                        WHERE id = 'evidence-company-b'
                    """)
                    assert cur.rowcount == 0
                    cur.execute("""
                        DELETE FROM patrol_evidences WHERE id = 'evidence-company-b'
                    """)
                    assert cur.rowcount == 0

                    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                        cur.execute("""
                            INSERT INTO patrol_evidences
                                (id, company_id, user_id, zona, descripcion)
                            VALUES
                                ('forged-company-evidence', 'company-b-pg',
                                 'legacy-user-pg', 'Zona B', 'Inserción no permitida')
                        """)
                    app_conn.rollback()
        finally:
            app_conn.close()

        downgraded = app.test_cli_runner().invoke(args=["db", "downgrade", "base"])
        assert downgraded.exit_code == 0, downgraded.output

        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'patrol_evidences'
            """)
            columns = {row[0] for row in cur.fetchall()}
            assert "company_id" not in columns
            assert {"id", "user_id", "descripcion", "photos", "location"} <= columns

            cur.execute("""
                SELECT descripcion, photos::text, location::text, user_id
                FROM patrol_evidences WHERE id = 'legacy-evidence-pg'
            """)
            row = cur.fetchone()
            assert row is not None
            assert row[0] == "Evidencia PostgreSQL que debe conservarse"
            assert "cloudinary.com" in row[1]
            assert "-8.11" in row[2]
            assert row[3] == "legacy-user-pg"

            cur.execute("SELECT name, password_hash FROM users WHERE id = 'legacy-user-pg'")
            assert cur.fetchone() == ("Administrador histórico", "hash-original")

            cur.execute("SELECT COUNT(*) FROM patrol_evidences")
            assert cur.fetchone()[0] == 2
            cur.execute("""
                SELECT descripcion FROM patrol_evidences
                WHERE id = 'evidence-company-b'
            """)
            assert cur.fetchone() == ("No debe ser visible desde empresa A",)

            cur.execute("""
                SELECT to_regclass('public.companies'),
                       to_regclass('public.company_memberships'),
                       to_regclass('public.audit_logs')
            """)
            assert cur.fetchone() == (None, None, None)
    finally:
        conn.close()
