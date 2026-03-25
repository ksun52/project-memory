"""AI service — extraction, embedding, summarization, and query/RAG logic.

This is a service-only domain (no router). All functions are called by other
domain services or the extraction process.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domains.ai.models import (
    Citation,
    Embedding,
    EmbeddingResult,
    ExtractionOutput,
    ExtractedRecord,
    GeneratedSummary,
    QueryResult,
    SummaryResult,
)
from app.domains.ai.prompts.extraction import (
    EXTRACTION_PROMPT_VERSION,
    build_extraction_prompt,
)
from app.domains.ai.prompts.query import (
    QUERY_PROMPT_VERSION,
    build_query_prompt,
)
from app.domains.ai.prompts.summarization import (
    SUMMARIZATION_PROMPT_VERSION,
    build_summarization_prompt,
)
from app.integrations.llm_client import llm_client

logger = logging.getLogger(__name__)

VALID_RECORD_TYPES = {
    "fact", "event", "decision", "issue",
    "question", "preference", "task", "insight",
}
VALID_IMPORTANCE = {"low", "medium", "high"}
EXTRACTION_CHAR_THRESHOLD = 24000


# --- Extraction ---


def extract_from_content(
    content: str,
    source_type: str,
    chunk_position: Optional[str] = None,
) -> ExtractionOutput:
    """Extract structured memory records from source content via LLM.

    Builds the extraction prompt, calls the LLM, validates the response,
    and returns an ExtractionOutput with valid records only.

    Args:
        content: Raw source text to extract from.
        source_type: One of "note", "document", "transcript".
        chunk_position: Optional position like "section 2 of 4" for chunked content.

    Returns:
        ExtractionOutput with validated records. Invalid records are discarded.
    """
    messages = build_extraction_prompt(content, source_type, chunk_position)
    raw = llm_client.extract(messages)
    return _validate_extraction_output(raw)


def _validate_extraction_output(raw: dict) -> ExtractionOutput:
    """Validate and filter LLM extraction output.

    Keeps records with valid record_type, confidence in [0, 1], valid
    importance, and non-empty content. Discards invalid records with warnings.
    """
    raw_records = raw.get("records", [])
    if not isinstance(raw_records, list):
        logger.warning("Extraction output 'records' is not a list")
        return ExtractionOutput(records=[])

    valid_records: list[ExtractedRecord] = []
    for i, rec in enumerate(raw_records):
        if not isinstance(rec, dict):
            logger.warning("Record %d is not a dict, skipping", i)
            continue

        record_type = rec.get("record_type", "")
        content = rec.get("content", "")
        confidence = rec.get("confidence", 0.0)
        importance = rec.get("importance", "medium")
        evidence_text = rec.get("evidence_text")

        # Validate required fields
        if not content or not content.strip():
            logger.warning("Record %d has empty content, skipping", i)
            continue

        if record_type not in VALID_RECORD_TYPES:
            logger.warning(
                "Record %d has invalid type '%s', skipping", i, record_type
            )
            continue

        # Coerce and validate confidence
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            logger.warning("Record %d has invalid confidence, skipping", i)
            continue
        confidence = max(0.0, min(1.0, confidence))

        # Validate importance
        if importance not in VALID_IMPORTANCE:
            importance = "medium"

        valid_records.append(
            ExtractedRecord(
                record_type=record_type,
                content=content.strip(),
                confidence=confidence,
                importance=importance,
                evidence_text=evidence_text if evidence_text else None,
            )
        )

    return ExtractionOutput(records=valid_records)


# --- Embeddings ---


def generate_embeddings(
    texts: list[str],
    entity_type: str,
    entity_ids: list[UUID],
) -> list[EmbeddingResult]:
    """Generate vector embeddings for a list of texts.

    Args:
        texts: Text strings to embed.
        entity_type: "memory_record" or "source_chunk".
        entity_ids: Corresponding entity IDs (same order as texts).

    Returns:
        List of EmbeddingResult with entity metadata and vectors.
    """
    if not texts:
        return []

    vectors = llm_client.generate_embeddings(texts)

    results = []
    for entity_id, vector in zip(entity_ids, vectors):
        results.append(
            EmbeddingResult(
                entity_type=entity_type,
                entity_id=entity_id,
                embedding=vector,
            )
        )
    return results


def store_embeddings(db: Session, results: list[EmbeddingResult]) -> None:
    """Persist embedding results to the database.

    Uses upsert logic: if an embedding for the same (entity_type, entity_id, model_id)
    already exists, replace it.
    """
    model_id = settings.EMBEDDING_MODEL

    for result in results:
        # Check for existing embedding
        existing = db.query(Embedding).filter(
            Embedding.entity_type == result.entity_type,
            Embedding.entity_id == result.entity_id,
            Embedding.model_id == model_id,
            Embedding.deleted_at.is_(None),
        ).first()

        if existing:
            existing.embedding = result.embedding
            existing.created_at = func.now()
        else:
            embedding = Embedding(
                entity_type=result.entity_type,
                entity_id=result.entity_id,
                embedding=result.embedding,
                model_id=model_id,
            )
            db.add(embedding)

    db.commit()


# --- Summarization ---


def summarize_memory_space(
    db: Session,
    memory_space_id: UUID,
    summary_type: str,
) -> SummaryResult:
    """Generate a summary from active memory records in a memory space.

    Queries active records, ranks by importance and recency, builds a
    summarization prompt, calls the LLM, and returns the result.
    Also persists the result to generated_summaries.

    Args:
        db: Database session.
        memory_space_id: Which memory space to summarize.
        summary_type: "one_pager" or "recent_updates".

    Returns:
        SummaryResult with title, content, and record IDs used.
    """
    from app.domains.memory.models import MemoryRecord

    # Query active records, ordered by importance (high first) then recency
    importance_order = text(
        "CASE importance WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END"
    )
    query = (
        db.query(MemoryRecord)
        .filter(
            MemoryRecord.memory_space_id == memory_space_id,
            MemoryRecord.status == "active",
            MemoryRecord.deleted_at.is_(None),
        )
        .order_by(importance_order, MemoryRecord.created_at.desc())
    )

    records = query.all()

    if not records:
        return SummaryResult(
            summary_type=summary_type,
            title="No Records Available",
            content="There are no active memory records to summarize.",
            record_ids_used=[],
        )

    # Convert to dicts for the prompt
    record_dicts = [
        {
            "id": str(r.id),
            "record_type": r.record_type,
            "content": r.content,
            "importance": r.importance,
            "confidence": float(r.confidence),
        }
        for r in records
    ]
    record_ids = [r.id for r in records]

    messages = build_summarization_prompt(record_dicts, summary_type)
    raw = llm_client.summarize(messages)

    title = raw.get("title", f"{summary_type} summary")
    content = raw.get("content", "")

    result = SummaryResult(
        summary_type=summary_type,
        title=title,
        content=content,
        record_ids_used=record_ids,
    )

    # Persist to generated_summaries
    summary = GeneratedSummary(
        memory_space_id=memory_space_id,
        summary_type=summary_type,
        title=title,
        content=content,
        is_edited=False,
        record_ids_used=record_ids,
        prompt_version=SUMMARIZATION_PROMPT_VERSION,
        model_id=settings.OPENAI_MODEL,
        generated_at=datetime.now(timezone.utc),
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)

    return result


# --- Query / RAG ---


def query_memory_space(
    db: Session,
    memory_space_id: UUID,
    question: str,
) -> QueryResult:
    """Answer a natural language question using memory records and source chunks.

    Pipeline:
    1. Embed the question
    2. Vector search memory_records (primary)
    3. Vector search source_chunks (fallback)
    4. Build RAG prompt with retrieved context
    5. Call LLM and return answer with citations

    Args:
        db: Database session.
        memory_space_id: Scope retrieval to this memory space.
        question: The user's natural language question.

    Returns:
        QueryResult with answer and citations.
    """
    from app.domains.memory.models import MemoryRecord
    from app.domains.source.models import SourceChunk

    # Step 1: Embed the question
    question_vectors = llm_client.generate_embeddings([question])
    if not question_vectors:
        return QueryResult(
            answer="Unable to process the question.",
            citations=[],
        )
    query_embedding = question_vectors[0]

    # Step 2: Search memory records
    record_results = _vector_search(
        db, memory_space_id, query_embedding, "memory_record", top_k=10
    )

    # Build record context dicts
    record_dicts = []
    if record_results:
        record_ids = [r[0] for r in record_results]
        records = (
            db.query(MemoryRecord)
            .filter(
                MemoryRecord.id.in_(record_ids),
                MemoryRecord.deleted_at.is_(None),
            )
            .all()
        )
        # Maintain similarity order
        record_map = {r.id: r for r in records}
        for entity_id, _score in record_results:
            rec = record_map.get(entity_id)
            if rec:
                record_dicts.append({
                    "id": str(rec.id),
                    "record_type": rec.record_type,
                    "content": rec.content,
                    "importance": rec.importance,
                })

    # Step 3: Search source chunks (fallback / supplementary)
    chunk_results = _vector_search(
        db, memory_space_id, query_embedding, "source_chunk", top_k=5
    )

    chunk_dicts = []
    if chunk_results:
        chunk_ids = [r[0] for r in chunk_results]
        chunks = (
            db.query(SourceChunk)
            .filter(
                SourceChunk.id.in_(chunk_ids),
                SourceChunk.deleted_at.is_(None),
            )
            .all()
        )
        chunk_map = {c.id: c for c in chunks}
        for entity_id, _score in chunk_results:
            chunk = chunk_map.get(entity_id)
            if chunk:
                chunk_dicts.append({
                    "id": str(chunk.id),
                    "content": chunk.content,
                    "source_id": str(chunk.source_id),
                })

    # Step 4: Build prompt and call LLM
    messages = build_query_prompt(question, record_dicts, chunk_dicts)
    raw = llm_client.query(messages)

    # Step 5: Parse response
    answer = raw.get("answer", "")
    raw_citations = raw.get("citations", [])

    citations = []
    for cit in raw_citations:
        if not isinstance(cit, dict):
            continue

        record_id = _parse_uuid(cit.get("record_id"))
        chunk_id = _parse_uuid(cit.get("chunk_id"))
        excerpt = cit.get("excerpt", "")

        citations.append(
            Citation(
                record_id=record_id,
                chunk_id=chunk_id,
                excerpt=excerpt,
            )
        )

    return QueryResult(answer=answer, citations=citations)


def _vector_search(
    db: Session,
    memory_space_id: UUID,
    query_embedding: list[float],
    entity_type: str,
    top_k: int = 10,
) -> list[tuple[UUID, float]]:
    """Cosine similarity search on the embeddings table.

    Scopes results to a specific memory space by joining through the
    appropriate entity table.

    Args:
        db: Database session.
        memory_space_id: Scope to this memory space.
        query_embedding: The query vector (1536-dim).
        entity_type: "memory_record" or "source_chunk".
        top_k: Number of results to return.

    Returns:
        List of (entity_id, distance) tuples ordered by similarity.
    """
    from app.domains.memory.models import MemoryRecord
    from app.domains.source.models import Source, SourceChunk

    # Build the distance expression
    embedding_vector = str(query_embedding)

    if entity_type == "memory_record":
        # Join embeddings → memory_records to scope by memory_space_id
        results = (
            db.query(
                Embedding.entity_id,
                Embedding.embedding.cosine_distance(query_embedding).label("distance"),
            )
            .join(
                MemoryRecord,
                (Embedding.entity_id == MemoryRecord.id),
            )
            .filter(
                Embedding.entity_type == "memory_record",
                Embedding.deleted_at.is_(None),
                MemoryRecord.memory_space_id == memory_space_id,
                MemoryRecord.deleted_at.is_(None),
                MemoryRecord.status == "active",
            )
            .order_by("distance")
            .limit(top_k)
            .all()
        )

    elif entity_type == "source_chunk":
        # Join embeddings → source_chunks → sources to scope by memory_space_id
        results = (
            db.query(
                Embedding.entity_id,
                Embedding.embedding.cosine_distance(query_embedding).label("distance"),
            )
            .join(
                SourceChunk,
                (Embedding.entity_id == SourceChunk.id),
            )
            .join(
                Source,
                (SourceChunk.source_id == Source.id),
            )
            .filter(
                Embedding.entity_type == "source_chunk",
                Embedding.deleted_at.is_(None),
                Source.memory_space_id == memory_space_id,
                Source.deleted_at.is_(None),
                SourceChunk.deleted_at.is_(None),
            )
            .order_by("distance")
            .limit(top_k)
            .all()
        )
    else:
        return []

    return [(row[0], row[1]) for row in results]


def _parse_uuid(value: Optional[str]) -> Optional[UUID]:
    """Safely parse a UUID string, returning None on failure."""
    if not value or value == "null":
        return None
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        return None
