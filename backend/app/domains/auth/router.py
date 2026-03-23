from fastapi import APIRouter, Depends, Response

from app.domains.auth import service
from app.domains.auth.entities import UserEntity
from app.domains.auth.schemas import TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
def login() -> dict:
    return service.login()


@router.get("/callback")
def callback(code: str) -> TokenResponse:
    return service.callback(code)


@router.post("/logout", status_code=204)
def logout() -> Response:
    service.logout()
    return Response(status_code=204)


@router.get("/me")
def me(current_user: UserEntity = Depends(service.get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user, from_attributes=True)
