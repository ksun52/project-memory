from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.domains.memory_space.models import MemorySpace
from app.domains.workspace.models import (
    Workspace,
    WorkspaceCreate,
    WorkspaceEntity,
    WorkspaceUpdate,
)


def create_workspace(
    db: Session, owner_id: UUID, data: WorkspaceCreate
) -> WorkspaceEntity:
    workspace = Workspace(
        owner_id=owner_id,
        name=data.name,
        description=data.description if data.description is not None else "",
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return WorkspaceEntity.from_orm(workspace)


def list_workspaces(
    db: Session, owner_id: UUID, page: int = 1, page_size: int = 20
) -> tuple[list[WorkspaceEntity], int]:
    query = db.query(Workspace).filter(
        Workspace.owner_id == owner_id,
        Workspace.deleted_at.is_(None),
    )
    total = query.count()
    offset = (page - 1) * page_size
    workspaces = query.offset(offset).limit(page_size).all()
    return [WorkspaceEntity.from_orm(w) for w in workspaces], total


def get_workspace(
    db: Session, workspace_id: UUID, owner_id: UUID
) -> WorkspaceEntity:
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.deleted_at.is_(None),
    ).first()
    if not workspace:
        raise NotFoundError("Workspace not found")
    if workspace.owner_id != owner_id:
        raise ForbiddenError("Not your workspace")
    return WorkspaceEntity.from_orm(workspace)


def update_workspace(
    db: Session, workspace_id: UUID, owner_id: UUID, data: WorkspaceUpdate
) -> WorkspaceEntity:
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.deleted_at.is_(None),
    ).first()
    if not workspace:
        raise NotFoundError("Workspace not found")
    if workspace.owner_id != owner_id:
        raise ForbiddenError("Not your workspace")

    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(workspace, field, value)

    db.commit()
    db.refresh(workspace)
    return WorkspaceEntity.from_orm(workspace)


def delete_workspace(
    db: Session, workspace_id: UUID, owner_id: UUID
) -> None:
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.deleted_at.is_(None),
    ).first()
    if not workspace:
        raise NotFoundError("Workspace not found")
    if workspace.owner_id != owner_id:
        raise ForbiddenError("Not your workspace")

    workspace.deleted_at = func.now()

    # Cascade soft-delete to child memory spaces
    db.query(MemorySpace).filter(
        MemorySpace.workspace_id == workspace_id,
        MemorySpace.deleted_at.is_(None),
    ).update({"deleted_at": func.now()})

    db.commit()
