import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app as fastapi_app

# Import all domain models so Base.metadata.create_all creates all tables
import app.domains.auth.models  # noqa: F401
import app.domains.workspace.models  # noqa: F401
import app.domains.memory_space.models  # noqa: F401
import app.domains.source.models  # noqa: F401
import app.domains.memory.models  # noqa: F401
import app.domains.ai.models  # noqa: F401

TEST_DATABASE_URL = settings.DATABASE_URL.rsplit("/", 1)[0] + "/project_memory_test"

test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    with TestClient(fastapi_app) as c:
        yield c
    fastapi_app.dependency_overrides.clear()
