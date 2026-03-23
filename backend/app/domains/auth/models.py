import uuid

from sqlalchemy import Column, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.models import TimestampMixin


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
