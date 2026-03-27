import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator
from sqlalchemy import CheckConstraint, Column, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.models import SoftDeleteMixin, TimestampMixin

VALID_STATUSES = {"active", "archived"}
VALID_SUMMARY_TYPES = {"one_pager", "recent_updates"}


# --- ORM Model ---


class MemorySpace(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "memory_spaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(50), nullable=False)

    workspace = relationship("Workspace", back_populates="memory_spaces")
    sources = relationship("Source", back_populates="memory_space")
    memory_records = relationship("MemoryRecord", back_populates="memory_space")
    generated_summaries = relationship("GeneratedSummary", back_populates="memory_space")

    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived')", name="ck_memory_spaces_status"),
        Index("idx_memory_spaces_workspace_id", "workspace_id"),
        Index("idx_memory_spaces_status", "status"),
    )


# --- Domain Entity ---


@dataclass
class MemorySpaceEntity:
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm(cls, ms: MemorySpace) -> "MemorySpaceEntity":
        return cls(
            id=ms.id,
            workspace_id=ms.workspace_id,
            name=ms.name,
            description=ms.description,
            status=ms.status,
            created_at=ms.created_at,
            updated_at=ms.updated_at,
        )


# --- Pydantic Schemas ---


class MemorySpaceCreate(BaseModel):
    name: str
    description: Optional[str] = None


class MemorySpaceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(VALID_STATUSES))}")
        return v


class MemorySpaceResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MemorySpaceListResponse(BaseModel):
    items: list[MemorySpaceResponse]
    total: int
    page: int
    page_size: int


class SummaryRequest(BaseModel):
    summary_type: str
    regenerate: bool = False

    @field_validator("summary_type")
    @classmethod
    def validate_summary_type(cls, v: str) -> str:
        if v not in VALID_SUMMARY_TYPES:
            raise ValueError(f"summary_type must be one of: {', '.join(sorted(VALID_SUMMARY_TYPES))}")
        return v


class SummaryResponse(BaseModel):
    id: uuid.UUID
    memory_space_id: uuid.UUID
    summary_type: str
    title: str
    content: str
    is_edited: bool
    edited_content: Optional[str]
    record_ids_used: list[uuid.UUID]
    generated_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QueryRequest(BaseModel):
    question: str


class CitationResponse(BaseModel):
    record_id: Optional[uuid.UUID] = None
    source_id: Optional[uuid.UUID] = None
    chunk_id: Optional[uuid.UUID] = None
    excerpt: str = ""


class QueryResponse(BaseModel):
    answer: str
    citations: list[CitationResponse]
