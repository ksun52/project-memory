import uuid
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.models import TimestampMixin


# --- ORM Model ---


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    auth_provider = Column(String(50), nullable=False)
    auth_provider_id = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)

    workspaces = relationship("Workspace", back_populates="owner")

    __table_args__ = (
        UniqueConstraint("auth_provider", "auth_provider_id", name="uq_users_auth_provider"),
        UniqueConstraint("email", name="uq_users_email"),
        Index("idx_users_email", "email"),
    )


# --- Domain Entity ---


@dataclass
class UserEntity:
    id: uuid.UUID
    auth_provider: str
    auth_provider_id: str
    email: str
    display_name: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm(cls, user: User) -> "UserEntity":
        return cls(
            id=user.id,
            auth_provider=user.auth_provider,
            auth_provider_id=user.auth_provider_id,
            email=user.email,
            display_name=user.display_name,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


# --- Pydantic Schemas ---


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
