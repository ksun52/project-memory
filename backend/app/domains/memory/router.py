"""Memory domain router — HTTP endpoints for memory record CRUD."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domains.auth.models import UserEntity
from app.domains.auth.service import get_current_user
from app.domains.memory import service
from app.domains.memory.models import (
    RecordCreate,
    RecordListResponse,
    RecordResponse,
    RecordSourceLinkResponse,
    RecordUpdate,
)

router = APIRouter(tags=["records"])


# --- Memory-space-scoped routes ---


@router.post("/memory-spaces/{memory_space_id}/records", status_code=201)
def create_record(
    memory_space_id: UUID,
    data: RecordCreate,
    current_user: UserEntity = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecordResponse:
    entity = service.create_record(db, memory_space_id, current_user.id, data)
    return RecordResponse.model_validate(entity, from_attributes=True)


@router.get("/memory-spaces/{memory_space_id}/records")
def list_records(
    memory_space_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    record_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    importance: Optional[str] = Query(None),
    current_user: UserEntity = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecordListResponse:
    entities, total = service.list_records(
        db, memory_space_id, current_user.id, page, page_size,
        record_type, status, importance,
    )
    return RecordListResponse(
        items=[RecordResponse.model_validate(e, from_attributes=True) for e in entities],
        total=total,
        page=page,
        page_size=page_size,
    )


# --- Direct record routes ---


@router.get("/records/{record_id}")
def get_record(
    record_id: UUID,
    current_user: UserEntity = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecordResponse:
    entity = service.get_record(db, record_id, current_user.id)
    return RecordResponse.model_validate(entity, from_attributes=True)


@router.patch("/records/{record_id}")
def update_record(
    record_id: UUID,
    data: RecordUpdate,
    current_user: UserEntity = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecordResponse:
    entity = service.update_record(db, record_id, current_user.id, data)
    return RecordResponse.model_validate(entity, from_attributes=True)


@router.delete("/records/{record_id}", status_code=204)
def delete_record(
    record_id: UUID,
    current_user: UserEntity = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    service.delete_record(db, record_id, current_user.id)
    return Response(status_code=204)


@router.get("/records/{record_id}/sources")
def get_record_sources(
    record_id: UUID,
    current_user: UserEntity = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RecordSourceLinkResponse]:
    return service.get_record_sources(db, record_id, current_user.id)
