from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domains.auth.models import UserEntity
from app.domains.auth.service import get_current_user
from app.domains.workspace import service
from app.domains.workspace.models import (
    WorkspaceCreate,
    WorkspaceListResponse,
    WorkspaceResponse,
    WorkspaceUpdate,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", status_code=201)
def create_workspace(
    data: WorkspaceCreate,
    current_user: UserEntity = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceResponse:
    entity = service.create_workspace(db, current_user.id, data)
    return WorkspaceResponse.model_validate(entity, from_attributes=True)


@router.get("")
def list_workspaces(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserEntity = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceListResponse:
    entities, total = service.list_workspaces(db, current_user.id, page, page_size)
    return WorkspaceListResponse(
        items=[WorkspaceResponse.model_validate(e, from_attributes=True) for e in entities],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{workspace_id}")
def get_workspace(
    workspace_id: UUID,
    current_user: UserEntity = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceResponse:
    entity = service.get_workspace(db, workspace_id, current_user.id)
    return WorkspaceResponse.model_validate(entity, from_attributes=True)


@router.patch("/{workspace_id}")
def update_workspace(
    workspace_id: UUID,
    data: WorkspaceUpdate,
    current_user: UserEntity = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceResponse:
    entity = service.update_workspace(db, workspace_id, current_user.id, data)
    return WorkspaceResponse.model_validate(entity, from_attributes=True)


@router.delete("/{workspace_id}", status_code=204)
def delete_workspace(
    workspace_id: UUID,
    current_user: UserEntity = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    service.delete_workspace(db, workspace_id, current_user.id)
    return Response(status_code=204)
