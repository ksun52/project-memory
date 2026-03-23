# Backend Testing Guide

## Prerequisites

1. Postgres running via Docker:
   ```
   docker compose up -d
   ```

2. Test database created with pgvector extension:
   ```
   docker compose exec db psql -U project_memory -d project_memory -c "CREATE DATABASE project_memory_test;"
   docker compose exec db psql -U project_memory -d project_memory_test -c "CREATE EXTENSION IF NOT EXISTS vector;"
   ```
   These only need to be run once.

3. Python venv activated with dependencies installed:
   ```
   cd backend
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

## Running Tests

From the `backend/` directory with the venv active:

```bash
# Run all tests
pytest tests/ -v

# Run a specific test file
pytest tests/domains/test_auth.py -v

# Run a single test
pytest tests/domains/test_auth.py::test_get_me_returns_dev_user -v
```

## How the Test Fixtures Work

`tests/conftest.py` provides two fixtures:

- **`db_session`** — Creates all tables in the test database before each test, yields a SQLAlchemy session, then drops all tables after. Each test gets a clean database.
- **`client`** — Overrides FastAPI's `get_db` dependency to use the test session, yields a `TestClient`. No real HTTP server is started.

Tests that need database access should accept `db_session`. Tests that hit API endpoints should accept `client` (which implicitly depends on `db_session`).

## Adding New Tests

1. Create test files under `tests/domains/` matching the pattern `test_<domain>.py`
2. Use the `client` fixture for endpoint tests and `db_session` for direct DB tests
3. Seed any required data in the test function itself (see `test_auth.py` for an example)
