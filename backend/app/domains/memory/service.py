"""Memory domain service — business logic for memory records."""

from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.domains.memory.models import (
    MemoryRecord,
    MemoryRecordEntity,
    RecordCreate,
    RecordSourceLink,
    RecordSourceLinkResponse,
    RecordUpdate,
)
from app.domains.memory_space.models import MemorySpace
from app.domains.source.models import Source, SourceContent
from app.domains.workspace.models import Workspace


def _get_memory_space_for_record(
    db: Session, memory_space_id: UUID, owner_id: UUID
) -> MemorySpace:
    """Verify memory space exists, is not deleted, and user owns the parent workspace."""
    ms = db.query(MemorySpace).filter(
        MemorySpace.id == memory_space_id,
        MemorySpace.deleted_at.is_(None),
    ).first()
    if not ms:
        raise NotFoundError("Memory space not found")

    workspace = db.query(Workspace).filter(
        Workspace.id == ms.workspace_id,
        Workspace.deleted_at.is_(None),
    ).first()
    if not workspace or workspace.owner_id != owner_id:
        raise ForbiddenError("Not your memory space")
    return ms


def _get_record_with_ownership(
    db: Session, record_id: UUID, owner_id: UUID
) -> MemoryRecord:
    """Fetch a record by ID and verify ownership through workspace chain."""
    record = db.query(MemoryRecord).filter(
        MemoryRecord.id == record_id,
        MemoryRecord.deleted_at.is_(None),
    ).first()
    if not record:
        raise NotFoundError("Record not found")

    ms = db.query(MemorySpace).filter(
        MemorySpace.id == record.memory_space_id,
        MemorySpace.deleted_at.is_(None),
    ).first()
    if not ms:
        raise NotFoundError("Record not found")

    workspace = db.query(Workspace).filter(
        Workspace.id == ms.workspace_id,
        Workspace.deleted_at.is_(None),
    ).first()
    if not workspace or workspace.owner_id != owner_id:
        raise ForbiddenError("Not your record")

    return record


def _compute_evidence_offsets(
    content_text: str, evidence_text: str
) -> tuple[Optional[int], Optional[int]]:
    """Find evidence_text in content_text using simple string matching.

    Returns (start_offset, end_offset) or (None, None) if not found.
    """
    if not evidence_text:
        return None, None

    pos = content_text.find(evidence_text)
    if pos == -1:
        return None, None
    return pos, pos + len(evidence_text)


# --- Create ---


def create_record(
    db: Session,
    memory_space_id: UUID,
    owner_id: UUID,
    data: RecordCreate,
) -> MemoryRecordEntity:
    """Create a manual memory record."""
    _get_memory_space_for_record(db, memory_space_id, owner_id)

    record = MemoryRecord(
        memory_space_id=memory_space_id,
        record_type=data.record_type,
        content=data.content,
        origin="manual",
        status="active",
        confidence=Decimal("1.00"),
        importance=data.importance,
        record_metadata=data.metadata,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return MemoryRecordEntity.from_orm(record)


def bulk_create_records(
    db: Session,
    memory_space_id: UUID,
    source_id: UUID,
    records: list[dict],
) -> list[MemoryRecordEntity]:
    """Persist multiple extracted records + record_source_links in one transaction.

    Each record dict should have: record_type, content, confidence, importance,
    evidence_text.
    """
    # Get source content for evidence offset computation
    source_content = db.query(SourceContent).filter(
        SourceContent.source_id == source_id,
        SourceContent.deleted_at.is_(None),
    ).first()
    content_text = source_content.content_text if source_content else ""

    entities = []
    for rec in records:
        record = MemoryRecord(
            memory_space_id=memory_space_id,
            record_type=rec["record_type"],
            content=rec["content"],
            origin="extracted",
            status="active",
            confidence=Decimal(str(rec.get("confidence", 0.50))),
            importance=rec.get("importance", "medium"),
            record_metadata=rec.get("metadata", {}),
        )
        db.add(record)
        db.flush()

        # Create the source link with evidence offsets
        evidence_text = rec.get("evidence_text")
        start_offset, end_offset = None, None
        if evidence_text and content_text:
            start_offset, end_offset = _compute_evidence_offsets(
                content_text, evidence_text
            )

        link = RecordSourceLink(
            record_id=record.id,
            source_id=source_id,
            evidence_text=evidence_text,
            evidence_start_offset=start_offset,
            evidence_end_offset=end_offset,
        )
        db.add(link)

        entities.append(MemoryRecordEntity.from_orm(record))

    db.commit()
    return entities


# --- Read ---


def list_records(
    db: Session,
    memory_space_id: UUID,
    owner_id: UUID,
    page: int = 1,
    page_size: int = 20,
    record_type: Optional[str] = None,
    status: Optional[str] = None,
    importance: Optional[str] = None,
) -> tuple[list[MemoryRecordEntity], int]:
    """Paginated list of records with optional filters."""
    _get_memory_space_for_record(db, memory_space_id, owner_id)

    query = db.query(MemoryRecord).filter(
        MemoryRecord.memory_space_id == memory_space_id,
        MemoryRecord.deleted_at.is_(None),
    )
    if record_type is not None:
        query = query.filter(MemoryRecord.record_type == record_type)
    if status is not None:
        query = query.filter(MemoryRecord.status == status)
    if importance is not None:
        query = query.filter(MemoryRecord.importance == importance)

    total = query.count()
    offset = (page - 1) * page_size
    records = query.offset(offset).limit(page_size).all()
    return [MemoryRecordEntity.from_orm(r) for r in records], total


def get_record(
    db: Session, record_id: UUID, owner_id: UUID
) -> MemoryRecordEntity:
    """Get a single record with ownership check."""
    record = _get_record_with_ownership(db, record_id, owner_id)
    return MemoryRecordEntity.from_orm(record)


# --- Update ---


def update_record(
    db: Session,
    record_id: UUID,
    owner_id: UUID,
    data: RecordUpdate,
) -> MemoryRecordEntity:
    """Partial update of a memory record."""
    record = _get_record_with_ownership(db, record_id, owner_id)

    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if field == "metadata":
            setattr(record, "record_metadata", value)
        else:
            setattr(record, field, value)

    db.commit()
    db.refresh(record)
    return MemoryRecordEntity.from_orm(record)


# --- Delete ---


def delete_record(
    db: Session, record_id: UUID, owner_id: UUID
) -> None:
    """Cascade soft-delete: record + record_source_links + embeddings."""
    record = _get_record_with_ownership(db, record_id, owner_id)

    now = func.now()
    record.deleted_at = now

    # Soft-delete record_source_links
    db.query(RecordSourceLink).filter(
        RecordSourceLink.record_id == record_id,
        RecordSourceLink.deleted_at.is_(None),
    ).update({"deleted_at": now})

    # Soft-delete embeddings for this record
    from app.domains.ai.models import Embedding

    db.query(Embedding).filter(
        Embedding.entity_type == "memory_record",
        Embedding.entity_id == record_id,
        Embedding.deleted_at.is_(None),
    ).update({"deleted_at": now})

    db.commit()


# --- Record Sources ---


def get_record_sources(
    db: Session, record_id: UUID, owner_id: UUID
) -> list[RecordSourceLinkResponse]:
    """Return provenance links with denormalized source info."""
    _get_record_with_ownership(db, record_id, owner_id)

    links = (
        db.query(RecordSourceLink, Source)
        .join(Source, RecordSourceLink.source_id == Source.id)
        .filter(
            RecordSourceLink.record_id == record_id,
            RecordSourceLink.deleted_at.is_(None),
            Source.deleted_at.is_(None),
        )
        .all()
    )

    return [
        RecordSourceLinkResponse(
            id=link.id,
            record_id=link.record_id,
            source_id=link.source_id,
            source_title=source.title,
            source_type=source.source_type,
            evidence_text=link.evidence_text,
            created_at=link.created_at,
        )
        for link, source in links
    ]
