"""Extraction process — orchestrates the full pipeline from source content to
memory records, chunks, and embeddings.

Called in a background thread after source creation. Uses its own DB session.
"""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.domains.ai import service as ai_service
from app.domains.ai.models import ExtractionOutput
from app.domains.memory import service as memory_service
from app.domains.source import service as source_service

logger = logging.getLogger(__name__)

EXTRACTION_CHAR_THRESHOLD = 24000


def run_extraction(source_id: UUID) -> None:
    """Run the full extraction pipeline for a source.

    Creates its own DB session so it can run in a background thread
    independently of the request session.

    Steps:
    1. Read source content
    2. Update status to "processing"
    3. Extract memory records via LLM (chunk if content is large)
    4. Persist extracted records + source links
    5. Create embedding chunks
    6. Generate + store embeddings for chunks and records
    7. Update status to "completed"

    On any failure, marks the source as "failed" with the error message.
    """
    db: Session = SessionLocal()
    try:
        _run_extraction_pipeline(db, source_id)
    except Exception as e:
        logger.exception("Extraction failed for source %s", source_id)
        try:
            # Use a fresh session in case the previous one is in a bad state
            db.rollback()
            source_service.update_source_status(
                db, source_id, "failed", str(e)
            )
        except Exception:
            logger.exception(
                "Failed to update source status after extraction error"
            )
    finally:
        db.close()


def _run_extraction_pipeline(db: Session, source_id: UUID) -> None:
    """Inner pipeline logic, separated for cleaner error handling."""

    # Step 1: Read source metadata and content
    source = source_service.get_source_internal(db, source_id)
    content_text = source_service.get_source_content_internal(db, source_id)
    memory_space_id = source.memory_space_id

    # Step 2: Mark as processing
    source_service.update_source_status(db, source_id, "processing")

    # Step 3: Extract memory records via LLM
    extraction_output = _extract_with_chunking(content_text, source.source_type)

    # Step 4: Validate — zero records from non-empty content is a failure
    if not extraction_output.records and content_text.strip():
        source_service.update_source_status(
            db, source_id, "failed",
            "Extraction produced zero records from non-empty content"
        )
        return

    # Step 5: Persist extracted records (if any)
    record_entities = []
    if extraction_output.records:
        record_dicts = [
            {
                "record_type": r.record_type,
                "content": r.content,
                "confidence": r.confidence,
                "importance": r.importance,
                "evidence_text": r.evidence_text,
            }
            for r in extraction_output.records
        ]
        record_entities = memory_service.bulk_create_records(
            db, memory_space_id, source_id, record_dicts
        )

    # Step 6: Create embedding chunks from source content
    chunk_entities = source_service.chunk_source_content(
        db, source_id, content_text
    )

    # Step 7: Generate embeddings for source chunks
    if chunk_entities:
        chunk_texts = [c.content for c in chunk_entities]
        chunk_ids = [c.id for c in chunk_entities]
        chunk_embeddings = ai_service.generate_embeddings(
            chunk_texts, "source_chunk", chunk_ids
        )
        ai_service.store_embeddings(db, chunk_embeddings)

    # Step 8: Generate embeddings for memory records
    if record_entities:
        record_texts = [r.content for r in record_entities]
        record_ids = [r.id for r in record_entities]
        record_embeddings = ai_service.generate_embeddings(
            record_texts, "memory_record", record_ids
        )
        ai_service.store_embeddings(db, record_embeddings)

    # Step 9: Mark as completed
    source_service.update_source_status(db, source_id, "completed")

    logger.info(
        "Extraction completed for source %s: %d records, %d chunks",
        source_id,
        len(record_entities),
        len(chunk_entities),
    )


def _extract_with_chunking(
    content_text: str, source_type: str
) -> ExtractionOutput:
    """Run extraction, chunking the content if it exceeds the threshold.

    For content under 24K chars, extracts from full text.
    For longer content, splits into transient extraction chunks and
    combines results.
    """
    if len(content_text) <= EXTRACTION_CHAR_THRESHOLD:
        return ai_service.extract_from_content(content_text, source_type)

    # Split into extraction chunks (transient, not stored in DB)
    # Use ~16K char chunks with ~2K overlap for extraction
    extraction_chunk_size = 16000
    extraction_overlap = 2000
    chunks: list[str] = []
    start = 0
    while start < len(content_text):
        end = min(start + extraction_chunk_size, len(content_text))
        chunks.append(content_text[start:end])
        start = end - extraction_overlap
        if start + extraction_overlap >= len(content_text):
            break

    all_records = []
    total_chunks = len(chunks)
    for i, chunk in enumerate(chunks):
        position = f"section {i + 1} of {total_chunks}"
        output = ai_service.extract_from_content(
            chunk, source_type, chunk_position=position
        )
        all_records.extend(output.records)

    return ExtractionOutput(records=all_records)
