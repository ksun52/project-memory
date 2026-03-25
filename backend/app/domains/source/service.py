"""Source domain service — business logic for creating, reading, and deleting sources."""

import re
from typing import Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.domains.memory.models import RecordSourceLink
from app.domains.memory_space.models import MemorySpace
from app.domains.source.models import (
    Source,
    SourceChunk,
    SourceChunkEntity,
    SourceContent,
    SourceContentEntity,
    SourceEntity,
    SourceFile,
    SourceFileEntity,
)
from app.domains.workspace.models import Workspace
from app.integrations.storage_client import storage_client


def _get_memory_space_for_source(
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


def _get_source_with_ownership(
    db: Session, source_id: UUID, owner_id: UUID
) -> Source:
    """Fetch a source by ID and verify ownership through workspace chain."""
    source = db.query(Source).filter(
        Source.id == source_id,
        Source.deleted_at.is_(None),
    ).first()
    if not source:
        raise NotFoundError("Source not found")

    ms = db.query(MemorySpace).filter(
        MemorySpace.id == source.memory_space_id,
        MemorySpace.deleted_at.is_(None),
    ).first()
    if not ms:
        raise NotFoundError("Source not found")

    workspace = db.query(Workspace).filter(
        Workspace.id == ms.workspace_id,
        Workspace.deleted_at.is_(None),
    ).first()
    if not workspace or workspace.owner_id != owner_id:
        raise ForbiddenError("Not your source")

    return source


# --- Create ---


def create_note_source(
    db: Session,
    memory_space_id: UUID,
    owner_id: UUID,
    data,
) -> SourceEntity:
    """Create a note source with its content in one transaction."""
    _get_memory_space_for_source(db, memory_space_id, owner_id)

    source = Source(
        memory_space_id=memory_space_id,
        source_type="note",
        title=data.title,
        processing_status="pending",
    )
    db.add(source)
    db.flush()

    content = SourceContent(
        source_id=source.id,
        content_text=data.content,
    )
    db.add(content)
    db.commit()
    db.refresh(source)
    return SourceEntity.from_orm(source)


def create_document_source(
    db: Session,
    memory_space_id: UUID,
    owner_id: UUID,
    title: str,
    file,
) -> SourceEntity:
    """Create a document source: save file, parse text, create Source + SourceFile + SourceContent."""
    _get_memory_space_for_source(db, memory_space_id, owner_id)

    # Read file data
    file_data = file.file.read()
    file_size = len(file_data)
    mime_type = file.content_type or "application/octet-stream"
    original_filename = file.filename or "unknown"

    # Create the source ORM first to get the ID for the file key
    source = Source(
        memory_space_id=memory_space_id,
        source_type="document",
        title=title,
        processing_status="pending",
    )
    db.add(source)
    db.flush()

    # Save file via storage client
    file_key = f"{memory_space_id}/{source.id}/{original_filename}"
    file_path = storage_client.save_file(file_key, file_data)

    # Parse the document to extract text
    content_text = parse_document(file_path, mime_type)

    # Create SourceFile
    source_file = SourceFile(
        source_id=source.id,
        file_path=file_path,
        mime_type=mime_type,
        size_bytes=file_size,
        original_filename=original_filename,
    )
    db.add(source_file)

    # Create SourceContent
    content = SourceContent(
        source_id=source.id,
        content_text=content_text,
    )
    db.add(content)

    db.commit()
    db.refresh(source)
    return SourceEntity.from_orm(source)


# --- Parse ---


def parse_document(file_path: str, mime_type: str) -> str:
    """Extract plain text from a document file.

    Supports PDF (pdfplumber), DOCX (python-docx), and plain text.
    Raises ValidationError for unsupported types.
    """
    if mime_type == "text/plain":
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    if mime_type == "application/pdf":
        import pdfplumber

        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)

    if mime_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ):
        import docx

        doc = docx.Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs if p.text)

    raise ValidationError(f"Unsupported document type: {mime_type}")


# --- Chunk ---


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences using simple boundary detection."""
    # Split on sentence-ending punctuation followed by whitespace
    parts = re.split(r'(?<=[.!?])\s+', text)
    return [p for p in parts if p.strip()]


def chunk_source_content(
    db: Session, source_id: UUID, content_text: str
) -> list[SourceChunkEntity]:
    """Split text into overlapping chunks and persist as SourceChunk rows.

    Uses sentence boundary detection. Target chunk size and overlap are
    configurable via settings.CHUNK_TARGET_CHARS and settings.CHUNK_OVERLAP_CHARS.
    """
    target_chars = settings.CHUNK_TARGET_CHARS
    overlap_chars = settings.CHUNK_OVERLAP_CHARS

    # If content fits in a single chunk, just return it
    if len(content_text) <= target_chars:
        chunk = SourceChunk(
            source_id=source_id,
            chunk_index=0,
            content=content_text,
            start_offset=0,
            end_offset=len(content_text),
        )
        db.add(chunk)
        db.commit()
        db.refresh(chunk)
        return [
            SourceChunkEntity(
                id=chunk.id,
                source_id=chunk.source_id,
                chunk_index=0,
                content=content_text,
                start_offset=0,
                end_offset=len(content_text),
            )
        ]

    sentences = _split_sentences(content_text)
    chunks: list[SourceChunkEntity] = []
    chunk_index = 0

    # Track position in the original text
    # We need to find each sentence's position in the original text
    sentence_positions: list[tuple[int, int]] = []
    search_start = 0
    for sentence in sentences:
        pos = content_text.find(sentence, search_start)
        if pos == -1:
            pos = search_start
        sentence_positions.append((pos, pos + len(sentence)))
        search_start = pos + len(sentence)

    current_sentence_idx = 0

    while current_sentence_idx < len(sentences):
        # Build a chunk starting from current_sentence_idx
        chunk_start = sentence_positions[current_sentence_idx][0]
        chunk_end = chunk_start
        end_sentence_idx = current_sentence_idx

        # Add sentences until we hit the target size
        for i in range(current_sentence_idx, len(sentences)):
            candidate_end = sentence_positions[i][1]
            if candidate_end - chunk_start > target_chars and i > current_sentence_idx:
                break
            end_sentence_idx = i
            chunk_end = candidate_end

        chunk_text = content_text[chunk_start:chunk_end]

        chunk_orm = SourceChunk(
            source_id=source_id,
            chunk_index=chunk_index,
            content=chunk_text,
            start_offset=chunk_start,
            end_offset=chunk_end,
        )
        db.add(chunk_orm)

        chunks.append(
            SourceChunkEntity(
                id=chunk_orm.id,
                source_id=source_id,
                chunk_index=chunk_index,
                content=chunk_text,
                start_offset=chunk_start,
                end_offset=chunk_end,
            )
        )

        chunk_index += 1

        if end_sentence_idx >= len(sentences) - 1:
            # Ensure the last chunk covers any trailing whitespace
            if chunks and chunks[-1].end_offset < len(content_text):
                chunks[-1] = SourceChunkEntity(
                    id=chunks[-1].id,
                    source_id=chunks[-1].source_id,
                    chunk_index=chunks[-1].chunk_index,
                    content=content_text[chunks[-1].start_offset:],
                    start_offset=chunks[-1].start_offset,
                    end_offset=len(content_text),
                )
                chunk_orm.content = content_text[chunks[-1].start_offset:]
                chunk_orm.end_offset = len(content_text)
            break

        # Calculate overlap: walk backwards from end_sentence_idx to find
        # sentences that fall within the overlap window
        overlap_start_idx = end_sentence_idx + 1
        overlap_text_len = 0
        for i in range(end_sentence_idx, current_sentence_idx - 1, -1):
            sent_len = sentence_positions[i][1] - sentence_positions[i][0]
            if overlap_text_len + sent_len > overlap_chars and i < end_sentence_idx:
                break
            overlap_text_len += sent_len
            overlap_start_idx = i

        # Ensure we carry over at least 2 sentences (if available)
        min_overlap_sentences = min(2, end_sentence_idx - current_sentence_idx + 1)
        max_overlap_start = end_sentence_idx - min_overlap_sentences + 1
        if overlap_start_idx > max_overlap_start:
            overlap_start_idx = max(current_sentence_idx + 1, max_overlap_start)

        current_sentence_idx = overlap_start_idx

    db.commit()

    # Refresh to get DB-generated IDs
    for chunk_entity in chunks:
        db_chunk = db.query(SourceChunk).filter(
            SourceChunk.source_id == source_id,
            SourceChunk.chunk_index == chunk_entity.chunk_index,
        ).first()
        if db_chunk:
            chunk_entity.id = db_chunk.id

    return chunks


# --- Read ---


def list_sources(
    db: Session,
    memory_space_id: UUID,
    owner_id: UUID,
    page: int = 1,
    page_size: int = 20,
    source_type: Optional[str] = None,
    processing_status: Optional[str] = None,
) -> tuple[list[SourceEntity], int]:
    """Paginated list of sources with optional filters."""
    _get_memory_space_for_source(db, memory_space_id, owner_id)

    query = db.query(Source).filter(
        Source.memory_space_id == memory_space_id,
        Source.deleted_at.is_(None),
    )
    if source_type is not None:
        query = query.filter(Source.source_type == source_type)
    if processing_status is not None:
        query = query.filter(Source.processing_status == processing_status)

    total = query.count()
    offset = (page - 1) * page_size
    sources = query.offset(offset).limit(page_size).all()
    return [SourceEntity.from_orm(s) for s in sources], total


def get_source(
    db: Session, source_id: UUID, owner_id: UUID
) -> SourceEntity:
    """Get a single source with ownership check."""
    source = _get_source_with_ownership(db, source_id, owner_id)
    return SourceEntity.from_orm(source)


def get_source_detail(
    db: Session, source_id: UUID, owner_id: UUID
) -> dict:
    """Get source with content and file metadata."""
    source = _get_source_with_ownership(db, source_id, owner_id)
    entity = SourceEntity.from_orm(source)

    content_orm = db.query(SourceContent).filter(
        SourceContent.source_id == source_id,
        SourceContent.deleted_at.is_(None),
    ).first()
    content_entity = None
    if content_orm:
        content_entity = SourceContentEntity(
            source_id=content_orm.source_id,
            content_text=content_orm.content_text,
        )

    file_orm = db.query(SourceFile).filter(
        SourceFile.source_id == source_id,
        SourceFile.deleted_at.is_(None),
    ).first()
    file_entity = None
    if file_orm:
        file_entity = SourceFileEntity(
            source_id=file_orm.source_id,
            mime_type=file_orm.mime_type,
            size_bytes=file_orm.size_bytes,
            original_filename=file_orm.original_filename,
        )

    return {
        "source": entity,
        "content": content_entity,
        "file": file_entity,
    }


def get_source_content(
    db: Session, source_id: UUID, owner_id: UUID
) -> SourceContentEntity:
    """Get just the content text for a source."""
    _get_source_with_ownership(db, source_id, owner_id)

    content_orm = db.query(SourceContent).filter(
        SourceContent.source_id == source_id,
        SourceContent.deleted_at.is_(None),
    ).first()
    if not content_orm:
        raise NotFoundError("Source content not found")

    return SourceContentEntity(
        source_id=content_orm.source_id,
        content_text=content_orm.content_text,
    )


# --- Delete ---


def delete_source(
    db: Session, source_id: UUID, owner_id: UUID
) -> None:
    """Cascade soft-delete: source + content + file + chunks + record_source_links + embeddings."""
    source = _get_source_with_ownership(db, source_id, owner_id)

    now = func.now()
    source.deleted_at = now

    # Soft-delete content
    db.query(SourceContent).filter(
        SourceContent.source_id == source_id,
        SourceContent.deleted_at.is_(None),
    ).update({"deleted_at": now})

    # Soft-delete file
    db.query(SourceFile).filter(
        SourceFile.source_id == source_id,
        SourceFile.deleted_at.is_(None),
    ).update({"deleted_at": now})

    # Get chunk IDs before soft-deleting them (for embedding cascade)
    chunk_ids = [
        row[0]
        for row in db.query(SourceChunk.id).filter(
            SourceChunk.source_id == source_id,
            SourceChunk.deleted_at.is_(None),
        ).all()
    ]

    # Soft-delete chunks
    db.query(SourceChunk).filter(
        SourceChunk.source_id == source_id,
        SourceChunk.deleted_at.is_(None),
    ).update({"deleted_at": now})

    # Soft-delete record_source_links
    db.query(RecordSourceLink).filter(
        RecordSourceLink.source_id == source_id,
        RecordSourceLink.deleted_at.is_(None),
    ).update({"deleted_at": now})

    # Soft-delete embeddings for these chunks
    if chunk_ids:
        from app.domains.ai.models import Embedding

        db.query(Embedding).filter(
            Embedding.entity_type == "source_chunk",
            Embedding.entity_id.in_(chunk_ids),
            Embedding.deleted_at.is_(None),
        ).update({"deleted_at": now}, synchronize_session="fetch")

    db.commit()
