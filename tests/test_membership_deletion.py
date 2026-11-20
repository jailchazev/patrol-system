import pytest
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import Company, CompanyMembership, User, PatrolEvidence


@pytest.fixture()
def app(monkeypatch):
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("SECRET_KEY", "membership-delete-test-secret")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with app.app_context():
        db.create_all()
        company_a = Company(name="Empresa A", slug="empresa-delete-a", status="active")
        company_b = Company(name="Empresa B", slug="empresa-delete-b", status="active")
        db.session.add_all([company_a, company_b])
        db.session.flush()
        admin = User(
            code="ADMIN-DEL",
            name="Admin A",
            role="admin",
            password_hash=generate_password_hash("clave-segura"),
        )
        worker = User(
            code="WORKER-DEL",
            name="Trabajador compartido",
            role="guardia",
            password_hash=generate_password_hash("clave-segura"),
        )
        db.session.add_all([admin, worker])
        db.session.flush()
        db.session.add_all([
            CompanyMembership(company_id=company_a.id, legacy_user_id=admin.id, role_key="company_admin"),
            CompanyMembership(company_id=company_a.id, legacy_user_id=worker.id, role_key="guard"),
            CompanyMembership(company_id=company_b.id, legacy_user_id=worker.id, role_key="guard"),
        ])
        db.session.add_all([
            PatrolEvidence(company_id=company_a.id, user_id=worker.id, zona="A", descripcion="Histórico A", photos=[]),
            PatrolEvidence(company_id=company_b.id, user_id=worker.id, zona="B", descripcion="Histórico B", photos=[]),
        ])
        db.session.commit()
        app.config["TEST_WORKER_ID"] = worker.id
        app.config["TEST_COMPANY_A_ID"] = company_a.id
        app.config["TEST_COMPANY_B_ID"] = company_b.id
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_removing_worker_revokes_only_current_company_membership(app):
    client = app.test_client()
    login = client.post(
        "/login",
        data={"code": "ADMIN-DEL", "password": "clave-segura"},
        follow_redirects=False,
    )
    assert login.status_code == 302

    response = client.delete(f"/api/users/{app.config['TEST_WORKER_ID']}")
    assert response.status_code == 200

    with app.app_context():
        worker = db.session.get(User, app.config["TEST_WORKER_ID"])
        assert worker is not None
        memberships = CompanyMembership.query.filter_by(
            legacy_user_id=app.config["TEST_WORKER_ID"]
        ).all()
        assert len(memberships) == 1
        assert memberships[0].company_id == app.config["TEST_COMPANY_B_ID"]

        evidence = PatrolEvidence.query.filter_by(
            user_id=app.config["TEST_WORKER_ID"]
        ).order_by(PatrolEvidence.zona).all()
        assert len(evidence) == 2
        assert {item.descripcion for item in evidence} == {"Histórico A", "Histórico B"}
