from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domains.auth.models import User


@dataclass
class UserEntity:
    id: UUID
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
