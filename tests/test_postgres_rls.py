"""PostgreSQL RLS integration tests.

Run only against a disposable PostgreSQL database:
  TEST_POSTGRES_ADMIN_URL=postgresql://.../postgres
  TEST_POSTGRES_APP_URL=postgresql://patrol_rls_app:.../postgres
  pytest -q tests/test_postgres_rls.py

The app role must be non-superuser, NOSUPERUSER, NOBYPASSRLS and must not own
the test table. The fixture creates and drops an isolated schema.
"""
import os
import uuid

import psycopg2
import pytest


ADMIN_URL = os.getenv("TEST_POSTGRES_ADMIN_URL")
APP_URL = os.getenv("TEST_POSTGRES_APP_URL")
pytestmark = pytest.mark.skipif(
    not ADMIN_URL or not APP_URL,
    reason="Configura TEST_POSTGRES_ADMIN_URL y TEST_POSTGRES_APP_URL para pruebas PostgreSQL",
)


@pytest.fixture
def rls_schema():
    schema = "rls_test_" + uuid.uuid4().hex
    admin = psycopg2.connect(ADMIN_URL)
    admin.autocommit = True
    try:
        with admin.cursor() as cur:
            cur.execute("CREATE SCHEMA " + schema)
            cur.execute(
                f"""
                CREATE TABLE {schema}.patrol_evidences (
                    id text PRIMARY KEY,
                    company_id text NOT NULL,
                    description text NOT NULL
                )
                """
            )
            cur.execute(
                f"""
                INSERT INTO {schema}.patrol_evidences (id, company_id, description)
                VALUES ('evidence-a', 'company-a', 'A'),
                       ('evidence-b', 'company-b', 'B')
                """
            )
            cur.execute(
                f"ALTER TABLE {schema}.patrol_evidences ENABLE ROW LEVEL SECURITY"
            )
            cur.execute(
                f"ALTER TABLE {schema}.patrol_evidences FORCE ROW LEVEL SECURITY"
            )
            cur.execute(
                f"""
                CREATE POLICY tenant_isolation ON {schema}.patrol_evidences
                USING (
                    company_id = NULLIF(current_setting('app.current_company_id', true), '')
                )
                WITH CHECK (
                    company_id = NULLIF(current_setting('app.current_company_id', true), '')
                )
                """
            )
            cur.execute(f"GRANT USAGE ON SCHEMA {schema} TO patrol_rls_app")
            cur.execute(
                f"""
                GRANT SELECT, INSERT, UPDATE, DELETE
                ON {schema}.patrol_evidences TO patrol_rls_app
                """
            )
            cur.execute(
                """
                SELECT rolsuper, rolbypassrls
                FROM pg_roles WHERE rolname = 'patrol_rls_app'
                """
            )
            role_flags = cur.fetchone()
            assert role_flags is not None, "Falta crear el rol patrol_rls_app"
            assert role_flags == (False, False), (
                "patrol_rls_app no puede ser superuser ni tener BYPASSRLS"
            )
        yield schema
    finally:
        with admin.cursor() as cur:
            cur.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        admin.close()


def _app_connection():
    return psycopg2.connect(APP_URL)


def test_rls_blocks_cross_company_reads_and_writes_and_context_does_not_leak(rls_schema):
    schema = rls_schema
    conn = _app_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
                role = cur.fetchone()
                assert role == ("patrol_rls_app", False, False)

                # Without tenant context, default-deny: no company rows are visible.
                cur.execute(f"SELECT id FROM {schema}.patrol_evidences ORDER BY id")
                assert cur.fetchall() == []

                # Tenant A sees only its own evidence.
                cur.execute(
                    "SELECT set_config('app.current_company_id', %s, true)",
                    ("company-a",),
                )
                cur.execute(f"SELECT id FROM {schema}.patrol_evidences ORDER BY id")
                assert cur.fetchall() == [("evidence-a",)]

                # USING hides tenant B from UPDATE and DELETE.
                cur.execute(
                    f"UPDATE {schema}.patrol_evidences SET description = 'hacked' WHERE id = 'evidence-b'"
                )
                assert cur.rowcount == 0
                cur.execute(
                    f"DELETE FROM {schema}.patrol_evidences WHERE id = 'evidence-b'"
                )
                assert cur.rowcount == 0

                # WITH CHECK rejects inserting a row into another tenant.
                with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                    cur.execute(
                        f"""
                        INSERT INTO {schema}.patrol_evidences (id, company_id, description)
                        VALUES ('evidence-forged', 'company-b', 'forged')
                        """
                    )
                # A rejected statement aborts the transaction; roll it back before reuse.
                conn.rollback()

        # The transaction ended: the transaction-local setting must not survive.
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT NULLIF(current_setting('app.current_company_id', true), '')"
                )
                assert cur.fetchone()[0] is None
                cur.execute(f"SELECT id FROM {schema}.patrol_evidences ORDER BY id")
                assert cur.fetchall() == []
    finally:
        conn.close()
