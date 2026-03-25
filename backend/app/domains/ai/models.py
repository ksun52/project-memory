import uuid
from dataclasses import dataclass, field
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.models import SoftDeleteMixin, TimestampMixin


class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    embedding = Column(Vector(1536), nullable=False)
    model_id = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now(), server_default=func.now())
    deleted_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "model_id", name="uq_embeddings_entity_model"),
        CheckConstraint(
            "entity_type IN ('memory_record', 'source_chunk')",
            name="ck_embeddings_entity_type",
        ),
        Index("idx_embeddings_entity", "entity_type", "entity_id"),
        Index(
            "idx_embeddings_vector",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class GeneratedSummary(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "generated_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memory_space_id = Column(UUID(as_uuid=True), ForeignKey("memory_spaces.id"), nullable=False)
    summary_type = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    is_edited = Column(Boolean, nullable=False)
    edited_content = Column(Text, nullable=True)
    record_ids_used = Column(ARRAY(UUID(as_uuid=True)), nullable=False)
    prompt_version = Column(String(100), nullable=False)
    model_id = Column(String(100), nullable=False)
    generated_at = Column(DateTime, nullable=False)

    memory_space = relationship("MemorySpace", back_populates="generated_summaries")

    __table_args__ = (
        CheckConstraint(
            "summary_type IN ('one_pager', 'recent_updates')",
            name="ck_generated_summaries_summary_type",
        ),
        Index("idx_generated_summaries_memory_space_id", "memory_space_id"),
        Index("idx_generated_summaries_summary_type", "summary_type"),
    )


# --- Domain Entities ---


@dataclass
class ExtractedRecord:
    """A single memory record extracted from source content by the LLM."""

    record_type: str
    content: str
    confidence: float
    importance: str
    evidence_text: Optional[str] = None


@dataclass
class ExtractionOutput:
    """Result of running extraction on source content."""

    records: list[ExtractedRecord] = field(default_factory=list)


@dataclass
class SummaryResult:
    """Result of generating a summary from memory records."""

    summary_type: str
    title: str
    content: str
    record_ids_used: list[uuid.UUID] = field(default_factory=list)


@dataclass
class Citation:
    """A citation linking an answer to a specific record or source chunk."""

    record_id: Optional[uuid.UUID] = None
    chunk_id: Optional[uuid.UUID] = None
    excerpt: str = ""


@dataclass
class QueryResult:
    """Result of a RAG query against a memory space."""

    answer: str
    citations: list[Citation] = field(default_factory=list)


@dataclass
class EmbeddingResult:
    """A generated embedding for a single entity."""

    entity_type: str
    entity_id: uuid.UUID
    embedding: list[float] = field(default_factory=list)
