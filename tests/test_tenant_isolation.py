import pytest
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import Company, CompanyMembership, User, PatrolEvidence


@pytest.fixture()
def app(monkeypatch):
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("SECRET_KEY", "test-only-secret-key-not-for-production")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.delenv("AUTO_CREATE_TABLES", raising=False)
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with app.app_context():
        db.create_all()
        company_a = Company(name="Empresa A", slug="empresa-a", status="trial")
        company_b = Company(name="Empresa B", slug="empresa-b", status="trial")
        db.session.add_all([company_a, company_b])
        db.session.flush()

        user_a = User(code="AGENTE-A", name="Agente A", role="guardia",
                      password_hash=generate_password_hash("clave-segura"))
        user_b = User(code="AGENTE-B", name="Agente B", role="guardia",
                      password_hash=generate_password_hash("clave-segura"))
        db.session.add_all([user_a, user_b])
        db.session.flush()
        db.session.add_all([
            CompanyMembership(company_id=company_a.id, legacy_user_id=user_a.id, role_key="guard"),
            CompanyMembership(company_id=company_b.id, legacy_user_id=user_b.id, role_key="guard"),
        ])
        db.session.add_all([
            PatrolEvidence(company_id=company_a.id, user_id=user_a.id, zona="Zona A",
                           descripcion="Evidencia privada A", photos=[]),
            PatrolEvidence(company_id=company_b.id, user_id=user_b.id, zona="Zona B",
                           descripcion="Evidencia privada B", photos=[]),
        ])
        db.session.commit()
        app.config["TEST_COMPANY_A_ID"] = company_a.id
        app.config["TEST_COMPANY_B_ID"] = company_b.id
        app.config["TEST_EVIDENCE_B_ID"] = PatrolEvidence.query.filter_by(company_id=company_b.id).first().id
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


def login(client, code):
    return client.post("/login", data={"code": code, "password": "clave-segura"}, follow_redirects=True)


def test_guard_only_sees_evidence_from_own_company(app):
    client = app.test_client()
    login(client, "AGENTE-A")
    response = client.get("/api/patrol-evidence")
    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload) == 1
    assert payload[0]["descripcion"] == "Evidencia privada A"


def test_user_cannot_update_another_company_evidence(app):
    client = app.test_client()
    login(client, "AGENTE-A")
    evidence_id = app.config["TEST_EVIDENCE_B_ID"]
    response = client.put(f"/api/patrol-evidence/{evidence_id}", json={"descripcion": "intrusion"})
    assert response.status_code == 404


def test_user_cannot_delete_another_company_evidence(app):
    client = app.test_client()
    login(client, "AGENTE-A")
    evidence_id = app.config["TEST_EVIDENCE_B_ID"]
    response = client.delete(f"/api/patrol-evidence/{evidence_id}")
    assert response.status_code == 404
