import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.models import SoftDeleteMixin, TimestampMixin


# --- ORM Model ---


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


# --- Domain Entity ---


@dataclass
class WorkspaceEntity:
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    description: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm(cls, workspace: Workspace) -> "WorkspaceEntity":
        return cls(
            id=workspace.id,
            owner_id=workspace.owner_id,
            name=workspace.name,
            description=workspace.description,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )


# --- Pydantic Schemas ---


class WorkspaceCreate(BaseModel):
    name: str
    description: Optional[str] = None


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    description: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceListResponse(BaseModel):
    items: list[WorkspaceResponse]
    total: int
    page: int
    page_size: int
