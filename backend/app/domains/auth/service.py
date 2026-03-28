import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Depends, Request
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import NotFoundError, UnauthorizedError
from app.domains.auth.models import User, UserEntity
from app.integrations.workos_client import workos_client

logger = logging.getLogger(__name__)

DEV_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


def create_access_token(user_id: UUID) -> str:
    """Create a JWT access token encoding the user_id and expiration."""
    expires = datetime.now(timezone.utc) + timedelta(
        hours=settings.JWT_EXPIRATION_HOURS
    )
    payload = {
        "sub": str(user_id),
        "exp": expires,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> UUID:
    """Decode and validate a JWT, returning the user_id.

    Raises UnauthorizedError on invalid or expired tokens.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise UnauthorizedError("Invalid token: missing subject")
        return UUID(user_id_str)
    except JWTError:
        raise UnauthorizedError("Invalid or expired token")


def _extract_bearer_token(request: Request) -> str:
    """Extract Bearer token from the Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise UnauthorizedError("Missing or invalid Authorization header")
    return auth_header[len("Bearer "):]


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> UserEntity:
    """Resolve the current user from JWT or dev bypass."""
    if settings.AUTH_BYPASS:
        user = db.query(User).filter(User.id == DEV_USER_ID).first()
        if not user:
            raise NotFoundError(
                "Dev user not found. Run: python -m scripts.seed_dev_user"
            )
        return UserEntity.from_orm(user)

    token = _extract_bearer_token(request)
    user_id = decode_access_token(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UnauthorizedError("User not found")
    return UserEntity.from_orm(user)


def login() -> dict:
    """Return the authorization URL for the frontend to redirect to."""
    if settings.AUTH_BYPASS:
        return {"redirect_url": "/api/v1/auth/callback?code=dev"}

    if not workos_client:
        raise UnauthorizedError("WorkOS not configured")

    url = workos_client.get_authorization_url()
    return {"redirect_url": url}


def callback(code: str, db: Session) -> dict:
    """Exchange auth code for user + JWT. Returns redirect info."""
    if settings.AUTH_BYPASS:
        token = create_access_token(DEV_USER_ID)
        return {
            "redirect_url": f"{settings.FRONTEND_URL}/auth/callback?token={token}",
            "token": token,
        }

    if not workos_client:
        raise UnauthorizedError("WorkOS not configured")

    profile = workos_client.authenticate_with_code(code)

    user = (
        db.query(User)
        .filter(
            User.auth_provider == "workos",
            User.auth_provider_id == profile["id"],
        )
        .first()
    )

    if not user:
        display = " ".join(
            filter(None, [profile.get("first_name"), profile.get("last_name")])
        ) or profile["email"]
        user = User(
            auth_provider="workos",
            auth_provider_id=profile["id"],
            email=profile["email"],
            display_name=display,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Created new user %s for %s", user.id, user.email)

    token = create_access_token(user.id)
    return {
        "redirect_url": f"{settings.FRONTEND_URL}/auth/callback?token={token}",
        "token": token,
    }


def logout() -> None:
    """MVP: logout is client-side only (discard token from localStorage)."""
    return
