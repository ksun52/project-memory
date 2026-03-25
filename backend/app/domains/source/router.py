"""Source domain router — HTTP endpoints for source CRUD."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domains.auth.models import UserEntity
from app.domains.auth.service import get_current_user
from app.domains.source import service
from app.domains.source.models import (
    SourceContentResponse,
    SourceCreateNote,
    SourceDetailResponse,
    SourceFileResponse,
    SourceListResponse,
    SourceResponse,
)

router = APIRouter(tags=["sources"])


# --- Memory-space-scoped routes ---


@router.post("/memory-spaces/{memory_space_id}/sources", status_code=201)
async def create_source(
    memory_space_id: UUID,
    request: Request,
    current_user: UserEntity = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SourceResponse:
    """Create a source. JSON body for notes, multipart form data for documents."""
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        # Document upload
        form = await request.form()
        title = form.get("title", "")
        file = form.get("file")
        if not title:
            from app.core.exceptions import ValidationError

            raise ValidationError("title is required")
        if not file:
            from app.core.exceptions import ValidationError

            raise ValidationError("file is required")

        entity = service.create_document_source(
            db, memory_space_id, current_user.id, str(title), file
        )
    else:
        # JSON note
        body = await request.json()
        try:
            data = SourceCreateNote(**body)
        except Exception:
            from fastapi import HTTPException

            raise HTTPException(status_code=422, detail="Invalid request body for note source")
        entity = service.create_note_source(db, memory_space_id, current_user.id, data)

    return SourceResponse.model_validate(entity, from_attributes=True)


@router.get("/memory-spaces/{memory_space_id}/sources")
def list_sources(
    memory_space_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source_type: Optional[str] = Query(None),
    processing_status: Optional[str] = Query(None),
    current_user: UserEntity = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SourceListResponse:
    entities, total = service.list_sources(
        db, memory_space_id, current_user.id, page, page_size, source_type, processing_status
    )
    return SourceListResponse(
        items=[SourceResponse.model_validate(e, from_attributes=True) for e in entities],
        total=total,
        page=page,
        page_size=page_size,
    )


# --- Direct source routes ---


@router.get("/sources/{source_id}")
def get_source_detail(
    source_id: UUID,
    current_user: UserEntity = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SourceDetailResponse:
    detail = service.get_source_detail(db, source_id, current_user.id)
    source_entity = detail["source"]
    content_entity = detail["content"]
    file_entity = detail["file"]

    content_resp = None
    if content_entity:
        content_resp = SourceContentResponse(
            source_id=content_entity.source_id,
            content_text=content_entity.content_text,
        )

    file_resp = None
    if file_entity:
        file_resp = SourceFileResponse(
            mime_type=file_entity.mime_type,
            size_bytes=file_entity.size_bytes,
            original_filename=file_entity.original_filename,
        )

    return SourceDetailResponse(
        id=source_entity.id,
        memory_space_id=source_entity.memory_space_id,
        source_type=source_entity.source_type,
        title=source_entity.title,
        processing_status=source_entity.processing_status,
        processing_error=source_entity.processing_error,
        created_at=source_entity.created_at,
        updated_at=source_entity.updated_at,
        content=content_resp,
        file=file_resp,
    )


@router.get("/sources/{source_id}/content")
def get_source_content(
    source_id: UUID,
    current_user: UserEntity = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SourceContentResponse:
    content = service.get_source_content(db, source_id, current_user.id)
    return SourceContentResponse(
        source_id=content.source_id,
        content_text=content.content_text,
    )


@router.delete("/sources/{source_id}", status_code=204)
def delete_source(
    source_id: UUID,
    current_user: UserEntity = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    service.delete_source(db, source_id, current_user.id)
    return Response(status_code=204)
