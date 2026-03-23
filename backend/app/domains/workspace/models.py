import uuid

from sqlalchemy import Column, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.models import SoftDeleteMixin, TimestampMixin


class Workspace(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    owner = relationship("User", back_populates="workspaces")
    memory_spaces = relationship("MemorySpace", back_populates="workspace")

    __table_args__ = (
        Index("idx_workspaces_owner_id", "owner_id"),
    )
