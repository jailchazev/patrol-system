import pytest
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import Company, CompanyMembership, User, PatrolEvidence


@pytest.fixture()
def app(monkeypatch):
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("SECRET_KEY", "company-selection-test-secret")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.delenv("AUTO_CREATE_TABLES", raising=False)
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with app.app_context():
        db.create_all()
        company_a = Company(name="Empresa A", slug="empresa-a", status="active")
        company_b = Company(name="Empresa B", slug="empresa-b", status="active")
        db.session.add_all([company_a, company_b])
        db.session.flush()
        user = User(
            code="MULTI-01",
            name="Usuario multiempresa",
            role="guardia",
            password_hash=generate_password_hash("clave-segura"),
        )
        db.session.add(user)
        db.session.flush()
        db.session.add_all([
            CompanyMembership(company_id=company_a.id, legacy_user_id=user.id, role_key="guard"),
            CompanyMembership(company_id=company_b.id, legacy_user_id=user.id, role_key="guard"),
        ])
        db.session.add_all([
            PatrolEvidence(company_id=company_a.id, user_id=user.id, zona="A", descripcion="Solo A", photos=[]),
            PatrolEvidence(company_id=company_b.id, user_id=user.id, zona="B", descripcion="Solo B", photos=[]),
        ])
        db.session.commit()
        app.config["TEST_COMPANY_A_ID"] = company_a.id
        app.config["TEST_COMPANY_B_ID"] = company_b.id
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_multiple_memberships_require_selection_and_scope_queries(app):
    client = app.test_client()

    login_response = client.post(
        "/login",
        data={"code": "MULTI-01", "password": "clave-segura"},
        follow_redirects=False,
    )
    assert login_response.status_code == 302
    assert login_response.headers["Location"].endswith("/companies/select")

    # Una URL directa tampoco permite entrar al módulo sin contexto seleccionado.
    page_response = client.get("/evidencia", follow_redirects=False)
    assert page_response.status_code == 302
    assert page_response.headers["Location"].endswith("/companies/select")

    companies_response = client.get("/api/companies")
    assert companies_response.status_code == 200
    companies = companies_response.get_json()
    assert {item["id"] for item in companies} == {
        app.config["TEST_COMPANY_A_ID"],
        app.config["TEST_COMPANY_B_ID"],
    }

    # El servidor solo acepta empresas en las que el usuario tiene membresía activa.
    denied = client.post("/api/companies/select", json={"company_id": "company-not-owned"})
    assert denied.status_code == 403

    selected = client.post(
        "/api/companies/select",
        json={"company_id": app.config["TEST_COMPANY_B_ID"]},
    )
    assert selected.status_code == 200
    assert selected.get_json()["success"] is True

    evidence_response = client.get("/api/patrol-evidence")
    assert evidence_response.status_code == 200
    evidence = evidence_response.get_json()
    assert len(evidence) == 1
    assert evidence[0]["descripcion"] == "Solo B"

    # La selección se puede cambiar, pero siempre se valida contra membresías.
    switched = client.post(
        "/api/companies/select",
        json={"company_id": app.config["TEST_COMPANY_A_ID"]},
    )
    assert switched.status_code == 200
    evidence_a = client.get("/api/patrol-evidence").get_json()
    assert len(evidence_a) == 1
    assert evidence_a[0]["descripcion"] == "Solo A"
