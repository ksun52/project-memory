from fastapi import APIRouter, Depends, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domains.auth import service
from app.domains.auth.models import UserEntity, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
def login() -> dict:
    return service.login()


@router.get("/callback")
def callback(code: str, db: Session = Depends(get_db)) -> RedirectResponse:
    result = service.callback(code, db)
    return RedirectResponse(url=result["redirect_url"], status_code=302)


@router.post("/logout", status_code=204)
def logout() -> Response:
    service.logout()
    return Response(status_code=204)


@router.get("/me")
def me(current_user: UserEntity = Depends(service.get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user, from_attributes=True)
