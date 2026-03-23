import uuid

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.models import SoftDeleteMixin, TimestampMixin


class Source(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memory_space_id = Column(UUID(as_uuid=True), ForeignKey("memory_spaces.id"), nullable=False)
    source_type = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    processing_status = Column(String(50), nullable=False)
    processing_error = Column(Text, nullable=True)

    memory_space = relationship("MemorySpace", back_populates="sources")
    content = relationship("SourceContent", back_populates="source", uselist=False)
    file = relationship("SourceFile", back_populates="source", uselist=False)
    chunks = relationship("SourceChunk", back_populates="source")
    record_links = relationship("RecordSourceLink", back_populates="source")

    __table_args__ = (
        CheckConstraint(
            "source_type IN ('note', 'document', 'transcript')",
            name="ck_sources_source_type",
        ),
        CheckConstraint(
            "processing_status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_sources_processing_status",
        ),
        Index("idx_sources_memory_space_id", "memory_space_id"),
        Index("idx_sources_processing_status", "processing_status"),
    )


class SourceContent(Base):
    __tablename__ = "source_contents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False, unique=True)
    content_text = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now(), server_default=func.now())
    deleted_at = Column(DateTime, nullable=True)

    source = relationship("Source", back_populates="content")


class SourceFile(Base):
    __tablename__ = "source_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False, unique=True)
    file_path = Column(String(1000), nullable=False)
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    original_filename = Column(String(500), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now(), server_default=func.now())
    deleted_at = Column(DateTime, nullable=True)

    source = relationship("Source", back_populates="file")


class SourceChunk(Base):
    __tablename__ = "source_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    start_offset = Column(Integer, nullable=False)
    end_offset = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now(), server_default=func.now())
    deleted_at = Column(DateTime, nullable=True)

    source = relationship("Source", back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("source_id", "chunk_index", name="uq_source_chunks_source_chunk_index"),
        Index("idx_source_chunks_source_id", "source_id"),
    )
