import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.models import SoftDeleteMixin, TimestampMixin


class MemoryRecord(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "memory_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memory_space_id = Column(UUID(as_uuid=True), ForeignKey("memory_spaces.id"), nullable=False)
    record_type = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    origin = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    confidence = Column(Numeric(3, 2), nullable=False)
    importance = Column(String(20), nullable=False)
    record_metadata = Column("metadata", JSONB, nullable=False)

    memory_space = relationship("MemorySpace", back_populates="memory_records")
    source_links = relationship("RecordSourceLink", back_populates="record")

    __table_args__ = (
        CheckConstraint(
            "record_type IN ('fact', 'event', 'decision', 'issue', 'question', 'preference', 'task', 'insight')",
            name="ck_memory_records_record_type",
        ),
        CheckConstraint(
            "origin IN ('extracted', 'manual')",
            name="ck_memory_records_origin",
        ),
        CheckConstraint(
            "status IN ('active', 'tentative', 'outdated', 'archived')",
            name="ck_memory_records_status",
        ),
        CheckConstraint(
            "importance IN ('low', 'medium', 'high')",
            name="ck_memory_records_importance",
        ),
        CheckConstraint(
            "confidence >= 0.00 AND confidence <= 1.00",
            name="ck_memory_records_confidence",
        ),
        Index("idx_memory_records_memory_space_id", "memory_space_id"),
        Index("idx_memory_records_status", "status"),
        Index("idx_memory_records_record_type", "record_type"),
    )


class RecordSourceLink(Base):
    __tablename__ = "record_source_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id = Column(UUID(as_uuid=True), ForeignKey("memory_records.id"), nullable=False)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    evidence_text = Column(Text, nullable=True)
    evidence_start_offset = Column(Integer, nullable=True)
    evidence_end_offset = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now(), server_default=func.now())
    deleted_at = Column(DateTime, nullable=True)

    record = relationship("MemoryRecord", back_populates="source_links")
    source = relationship("Source", back_populates="record_links")

    __table_args__ = (
        UniqueConstraint("record_id", "source_id", name="uq_record_source_links_record_source"),
        Index("idx_record_source_links_record_id", "record_id"),
        Index("idx_record_source_links_source_id", "source_id"),
    )
