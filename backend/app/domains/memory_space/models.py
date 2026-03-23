import uuid

from sqlalchemy import CheckConstraint, Column, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.models import SoftDeleteMixin, TimestampMixin


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
