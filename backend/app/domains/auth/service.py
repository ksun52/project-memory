from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.domains.auth.models import TokenResponse, User, UserEntity

DEV_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


def get_current_user(db: Session = Depends(get_db)) -> UserEntity:
    if settings.AUTH_BYPASS:
        user = db.query(User).filter(User.id == DEV_USER_ID).first()
        if not user:
            raise NotFoundError("Dev user not found. Run: python -m scripts.seed_dev_user")
        return UserEntity.from_orm(user)

    raise NotImplementedError("Real auth not yet implemented")


def login() -> dict:
    if settings.AUTH_BYPASS:
        return {"redirect_url": "/api/v1/auth/callback?code=dev"}

    raise NotImplementedError("Real auth not yet implemented")


def callback(code: str) -> TokenResponse:
    if settings.AUTH_BYPASS:
        return TokenResponse(access_token="dev-token-bypass")

    raise NotImplementedError("Real auth not yet implemented")


def logout() -> None:
    if settings.AUTH_BYPASS:
        return

    raise NotImplementedError("Real auth not yet implemented")
