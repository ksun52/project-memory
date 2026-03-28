from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import UUID

from jose import jwt

from app.core.config import settings
from app.domains.auth.models import User
from app.domains.auth.service import (
    DEV_USER_ID,
    create_access_token,
    decode_access_token,
)
from app.core.exceptions import UnauthorizedError

import pytest


# ── Helpers ──────────────────────────────────────────────────────────


def _seed_dev_user(db_session) -> User:
    user = User(
        id=DEV_USER_ID,
        auth_provider="dev",
        auth_provider_id="dev-user-001",
        email="dev@projectmemory.local",
        display_name="Dev User",
    )
    db_session.add(user)
    db_session.commit()
    return user


def _seed_workos_user(db_session, workos_id="workos-user-001") -> User:
    user = User(
        auth_provider="workos",
        auth_provider_id=workos_id,
        email="real@example.com",
        display_name="Real User",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ── JWT: create_access_token ─────────────────────────────────────────


def test_create_access_token_produces_valid_jwt():
    user_id = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    token = create_access_token(user_id)

    payload = jwt.decode(
        token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
    assert payload["sub"] == str(user_id)
    assert "exp" in payload


def test_create_access_token_expiration_is_correct():
    token = create_access_token(DEV_USER_ID)
    payload = jwt.decode(
        token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    expected = datetime.now(timezone.utc) + timedelta(
        hours=settings.JWT_EXPIRATION_HOURS
    )
    # Allow 5 seconds of drift
    assert abs((exp - expected).total_seconds()) < 5


# ── JWT: decode_access_token ─────────────────────────────────────────


def test_decode_access_token_roundtrip():
    user_id = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    token = create_access_token(user_id)
    assert decode_access_token(token) == user_id


def test_decode_access_token_rejects_expired():
    payload = {
        "sub": str(DEV_USER_ID),
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    with pytest.raises(UnauthorizedError, match="Invalid or expired token"):
        decode_access_token(token)


def test_decode_access_token_rejects_tampered():
    token = create_access_token(DEV_USER_ID)
    tampered = token[:-4] + "XXXX"
    with pytest.raises(UnauthorizedError, match="Invalid or expired token"):
        decode_access_token(tampered)


def test_decode_access_token_rejects_wrong_secret():
    payload = {
        "sub": str(DEV_USER_ID),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    token = jwt.encode(payload, "wrong-secret", algorithm=settings.JWT_ALGORITHM)
    with pytest.raises(UnauthorizedError, match="Invalid or expired token"):
        decode_access_token(token)


def test_decode_access_token_rejects_missing_sub():
    payload = {"exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    with pytest.raises(UnauthorizedError, match="missing subject"):
        decode_access_token(token)


# ── callback: WorkOS flow (mocked) ──────────────────────────────────


def test_callback_creates_new_user_on_first_login(client, db_session):
    mock_profile = {
        "id": "workos-new-user",
        "email": "new@example.com",
        "first_name": "New",
        "last_name": "User",
    }
    with patch("app.domains.auth.service.workos_client") as mock_wos, \
         patch("app.domains.auth.service.settings") as mock_settings:
        mock_settings.AUTH_BYPASS = False
        mock_settings.SECRET_KEY = settings.SECRET_KEY
        mock_settings.JWT_ALGORITHM = settings.JWT_ALGORITHM
        mock_settings.JWT_EXPIRATION_HOURS = settings.JWT_EXPIRATION_HOURS
        mock_settings.FRONTEND_URL = settings.FRONTEND_URL
        mock_wos.authenticate_with_code.return_value = mock_profile

        response = client.get(
            "/api/v1/auth/callback", params={"code": "test-code"},
            follow_redirects=False,
        )

    assert response.status_code == 302
    assert "/auth/callback?token=" in response.headers["location"]

    user = (
        db_session.query(User)
        .filter(User.auth_provider == "workos", User.auth_provider_id == "workos-new-user")
        .first()
    )
    assert user is not None
    assert user.email == "new@example.com"
    assert user.display_name == "New User"


def test_callback_returns_existing_user_on_subsequent_login(client, db_session):
    existing = _seed_workos_user(db_session, workos_id="workos-existing")
    mock_profile = {
        "id": "workos-existing",
        "email": "real@example.com",
        "first_name": "Real",
        "last_name": "User",
    }
    with patch("app.domains.auth.service.workos_client") as mock_wos, \
         patch("app.domains.auth.service.settings") as mock_settings:
        mock_settings.AUTH_BYPASS = False
        mock_settings.SECRET_KEY = settings.SECRET_KEY
        mock_settings.JWT_ALGORITHM = settings.JWT_ALGORITHM
        mock_settings.JWT_EXPIRATION_HOURS = settings.JWT_EXPIRATION_HOURS
        mock_settings.FRONTEND_URL = settings.FRONTEND_URL
        mock_wos.authenticate_with_code.return_value = mock_profile

        response = client.get(
            "/api/v1/auth/callback", params={"code": "test-code"},
            follow_redirects=False,
        )

    assert response.status_code == 302

    # Verify the JWT references the existing user
    location = response.headers["location"]
    token = location.split("token=")[1]
    user_id = decode_access_token(token)
    assert user_id == existing.id

    # No duplicate users created
    count = (
        db_session.query(User)
        .filter(User.auth_provider_id == "workos-existing")
        .count()
    )
    assert count == 1


# ── get_current_user ─────────────────────────────────────────────────


def test_get_current_user_returns_dev_user_in_bypass(client, db_session):
    _seed_dev_user(db_session)
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(DEV_USER_ID)
    assert data["email"] == "dev@projectmemory.local"


def test_get_current_user_resolves_from_jwt(client, db_session):
    user = _seed_workos_user(db_session)
    token = create_access_token(user.id)

    with patch("app.domains.auth.service.settings") as mock_settings:
        mock_settings.AUTH_BYPASS = False
        mock_settings.SECRET_KEY = settings.SECRET_KEY
        mock_settings.JWT_ALGORITHM = settings.JWT_ALGORITHM

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(user.id)
    assert data["email"] == "real@example.com"


def test_get_current_user_rejects_missing_token(client, db_session):
    with patch("app.domains.auth.service.settings") as mock_settings:
        mock_settings.AUTH_BYPASS = False

        response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


# ── Existing endpoint tests (bypass mode) ────────────────────────────


def test_login_returns_redirect_url_bypass(client):
    response = client.get("/api/v1/auth/login")
    assert response.status_code == 200
    data = response.json()
    assert data["redirect_url"] == "/api/v1/auth/callback?code=dev"


def test_callback_redirects_in_bypass(client, db_session):
    response = client.get(
        "/api/v1/auth/callback", params={"code": "dev"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    location = response.headers["location"]
    assert "/auth/callback?token=" in location


def test_logout_returns_204(client):
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 204
