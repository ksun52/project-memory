from typing import Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.domains.memory.models import MemoryRecord
from app.domains.memory_space.models import (
    MemorySpace,
    MemorySpaceCreate,
    MemorySpaceEntity,
    MemorySpaceUpdate,
)
from app.domains.source.models import Source
from app.domains.workspace.models import Workspace


def _get_workspace_orm(db: Session, workspace_id: UUID, owner_id: UUID) -> Workspace:
    """Verify workspace exists and belongs to owner. Returns ORM object."""
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.deleted_at.is_(None),
    ).first()
    if not workspace:
        raise NotFoundError("Workspace not found")
    if workspace.owner_id != owner_id:
        raise ForbiddenError("Not your workspace")
    return workspace


def _get_memory_space_orm(db: Session, memory_space_id: UUID, owner_id: UUID) -> MemorySpace:
    """Fetch memory space and verify ownership via parent workspace."""
    ms = db.query(MemorySpace).filter(
        MemorySpace.id == memory_space_id,
        MemorySpace.deleted_at.is_(None),
    ).first()
    if not ms:
        raise NotFoundError("Memory space not found")
    # Verify ownership through parent workspace
    workspace = db.query(Workspace).filter(
        Workspace.id == ms.workspace_id,
        Workspace.deleted_at.is_(None),
    ).first()
    if not workspace or workspace.owner_id != owner_id:
        raise ForbiddenError("Not your memory space")
    return ms


def create_memory_space(
    db: Session, workspace_id: UUID, owner_id: UUID, data: MemorySpaceCreate
) -> MemorySpaceEntity:
    _get_workspace_orm(db, workspace_id, owner_id)
    ms = MemorySpace(
        workspace_id=workspace_id,
        name=data.name,
        description=data.description if data.description is not None else "",
        status="active",
    )
    db.add(ms)
    db.commit()
    db.refresh(ms)
    return MemorySpaceEntity.from_orm(ms)


def list_memory_spaces(
    db: Session,
    workspace_id: UUID,
    owner_id: UUID,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
) -> tuple[list[MemorySpaceEntity], int]:
    _get_workspace_orm(db, workspace_id, owner_id)
    query = db.query(MemorySpace).filter(
        MemorySpace.workspace_id == workspace_id,
        MemorySpace.deleted_at.is_(None),
    )
    if status is not None:
        query = query.filter(MemorySpace.status == status)
    total = query.count()
    offset = (page - 1) * page_size
    spaces = query.offset(offset).limit(page_size).all()
    return [MemorySpaceEntity.from_orm(ms) for ms in spaces], total


def get_memory_space(
    db: Session, memory_space_id: UUID, owner_id: UUID
) -> MemorySpaceEntity:
    ms = _get_memory_space_orm(db, memory_space_id, owner_id)
    return MemorySpaceEntity.from_orm(ms)


def update_memory_space(
    db: Session, memory_space_id: UUID, owner_id: UUID, data: MemorySpaceUpdate
) -> MemorySpaceEntity:
    ms = _get_memory_space_orm(db, memory_space_id, owner_id)
    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(ms, field, value)
    db.commit()
    db.refresh(ms)
    return MemorySpaceEntity.from_orm(ms)


def delete_memory_space(
    db: Session, memory_space_id: UUID, owner_id: UUID
) -> None:
    ms = _get_memory_space_orm(db, memory_space_id, owner_id)
    ms.deleted_at = func.now()

    # Cascade soft-delete to child sources and memory records
    db.query(Source).filter(
        Source.memory_space_id == memory_space_id,
        Source.deleted_at.is_(None),
    ).update({"deleted_at": func.now()})

    db.query(MemoryRecord).filter(
        MemoryRecord.memory_space_id == memory_space_id,
        MemoryRecord.deleted_at.is_(None),
    ).update({"deleted_at": func.now()})

    db.commit()
