from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domains.auth.models import UserEntity
from app.domains.auth.service import get_current_user
from app.domains.memory_space import service
from app.domains.memory_space.models import (
    CitationResponse,
    MemorySpaceCreate,
    MemorySpaceListResponse,
    MemorySpaceResponse,
    MemorySpaceUpdate,
    QueryRequest,
    QueryResponse,
    SummaryRequest,
    SummaryResponse,
)

router = APIRouter(tags=["memory-spaces"])


# --- Workspace-scoped routes ---


@router.post("/workspaces/{workspace_id}/memory-spaces", status_code=201)
def create_memory_space(
    workspace_id: UUID,
    data: MemorySpaceCreate,
    current_user: UserEntity = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MemorySpaceResponse:
    entity = service.create_memory_space(db, workspace_id, current_user.id, data)
    return MemorySpaceResponse.model_validate(entity, from_attributes=True)


@router.get("/workspaces/{workspace_id}/memory-spaces")
def list_memory_spaces(
    workspace_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    current_user: UserEntity = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MemorySpaceListResponse:
    entities, total = service.list_memory_spaces(
        db, workspace_id, current_user.id, page, page_size, status
    )
    return MemorySpaceListResponse(
        items=[MemorySpaceResponse.model_validate(e, from_attributes=True) for e in entities],
        total=total,
        page=page,
        page_size=page_size,
    )


# --- Direct memory space routes ---


@router.get("/memory-spaces/{memory_space_id}")
def get_memory_space(
    memory_space_id: UUID,
    current_user: UserEntity = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MemorySpaceResponse:
    entity = service.get_memory_space(db, memory_space_id, current_user.id)
    return MemorySpaceResponse.model_validate(entity, from_attributes=True)


@router.patch("/memory-spaces/{memory_space_id}")
def update_memory_space(
    memory_space_id: UUID,
    data: MemorySpaceUpdate,
    current_user: UserEntity = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MemorySpaceResponse:
    entity = service.update_memory_space(db, memory_space_id, current_user.id, data)
    return MemorySpaceResponse.model_validate(entity, from_attributes=True)


@router.delete("/memory-spaces/{memory_space_id}", status_code=204)
def delete_memory_space(
    memory_space_id: UUID,
    current_user: UserEntity = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    service.delete_memory_space(db, memory_space_id, current_user.id)
    return Response(status_code=204)


# --- AI-powered endpoints ---


@router.post("/memory-spaces/{memory_space_id}/summarize")
def summarize_memory_space(
    memory_space_id: UUID,
    data: SummaryRequest,
    current_user: UserEntity = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SummaryResponse:
    result = service.summarize_memory_space(
        db, memory_space_id, current_user.id, data.summary_type, data.regenerate
    )
    return SummaryResponse.model_validate(result, from_attributes=True)


@router.post("/memory-spaces/{memory_space_id}/query")
def query_memory_space(
    memory_space_id: UUID,
    data: QueryRequest,
    current_user: UserEntity = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QueryResponse:
    result = service.query_memory_space(
        db, memory_space_id, current_user.id, data.question
    )
    return QueryResponse(
        answer=result.answer,
        citations=[
            CitationResponse(
                record_id=c.record_id,
                source_id=c.source_id,
                chunk_id=c.chunk_id,
                excerpt=c.excerpt,
            )
            for c in result.citations
        ],
    )
