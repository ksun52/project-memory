from uuid import UUID

from app.domains.auth.models import User

DEV_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


def _seed_dev_user(db_session) -> None:
    user = User(
        id=DEV_USER_ID,
        auth_provider="dev",
        auth_provider_id="dev-user-001",
        email="dev@projectmemory.local",
        display_name="Dev User",
    )
    db_session.add(user)
    db_session.commit()


def test_get_me_returns_dev_user(client, db_session):
    _seed_dev_user(db_session)
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(DEV_USER_ID)
    assert data["email"] == "dev@projectmemory.local"
    assert data["display_name"] == "Dev User"
    assert "created_at" in data


def test_callback_returns_token(client):
    response = client.get("/api/v1/auth/callback", params={"code": "test"})
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "dev-token-bypass"
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 3600


def test_logout_returns_204(client):
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 204


def test_login_returns_redirect_url(client):
    response = client.get("/api/v1/auth/login")
    assert response.status_code == 200
    data = response.json()
    assert data["redirect_url"] == "/api/v1/auth/callback?code=dev"
