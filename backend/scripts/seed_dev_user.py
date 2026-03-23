"""Seed the development user for auth bypass mode.

Usage:
    cd backend && python -m scripts.seed_dev_user
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine
from app.domains.auth.models import User

# Import all models so SQLAlchemy can resolve relationships
import app.domains.workspace.models  # noqa: F401
import app.domains.memory_space.models  # noqa: F401
import app.domains.source.models  # noqa: F401
import app.domains.memory.models  # noqa: F401
import app.domains.ai.models  # noqa: F401

DEV_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


def seed() -> None:
    db: Session = SessionLocal()
    try:
        existing = db.query(User).filter(User.id == DEV_USER_ID).first()
        if existing:
            print(f"Dev user already exists: {existing.email}")
            return

        user = User(
            id=DEV_USER_ID,
            auth_provider="dev",
            auth_provider_id="dev-user-001",
            email="dev@projectmemory.local",
            display_name="Dev User",
        )
        db.add(user)
        db.commit()
        print(f"Created dev user: {user.email} ({user.id})")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
