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

## Manual Endpoint Testing

Start the server, run migrations, and seed the dev user:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
python -m scripts.seed_dev_user
uvicorn app.main:app --reload
```

### Workspace Endpoints

```bash
# Create a workspace
curl -s -X POST http://localhost:8000/api/v1/workspaces \
  -H "Content-Type: application/json" \
  -d '{"name": "My Workspace", "description": "Optional description"}' | python3 -m json.tool

# List workspaces (with optional pagination)
curl -s "http://localhost:8000/api/v1/workspaces?page=1&page_size=20" | python3 -m json.tool

# Get a single workspace
curl -s http://localhost:8000/api/v1/workspaces/{workspace_id} | python3 -m json.tool

# Update a workspace (partial update — only send fields to change)
curl -s -X PATCH http://localhost:8000/api/v1/workspaces/{workspace_id} \
  -H "Content-Type: application/json" \
  -d '{"name": "New Name"}' | python3 -m json.tool

# Delete a workspace (soft delete, returns 204)
curl -s -o /dev/null -w "Status: %{http_code}\n" \
  -X DELETE http://localhost:8000/api/v1/workspaces/{workspace_id}
```

Replace `{workspace_id}` with the `id` from the create response.

### Memory Space Endpoints

Memory spaces are scoped to a workspace. Create/list use the workspace path; get/update/delete use the memory space id directly.

```bash
# Create a memory space within a workspace
curl -s -X POST http://localhost:8000/api/v1/workspaces/{workspace_id}/memory-spaces \
  -H "Content-Type: application/json" \
  -d '{"name": "My Space", "description": "Optional description"}' | python3 -m json.tool

# List memory spaces (with optional status filter and pagination)
curl -s "http://localhost:8000/api/v1/workspaces/{workspace_id}/memory-spaces?status=active&page=1&page_size=20" | python3 -m json.tool

# Get a single memory space
curl -s http://localhost:8000/api/v1/memory-spaces/{memory_space_id} | python3 -m json.tool

# Update a memory space (partial update — name, description, and/or status)
curl -s -X PATCH http://localhost:8000/api/v1/memory-spaces/{memory_space_id} \
  -H "Content-Type: application/json" \
  -d '{"status": "archived"}' | python3 -m json.tool

# Delete a memory space (soft delete, returns 204)
curl -s -o /dev/null -w "Status: %{http_code}\n" \
  -X DELETE http://localhost:8000/api/v1/memory-spaces/{memory_space_id}

# Summarize (stub — returns 501)
curl -s -X POST http://localhost:8000/api/v1/memory-spaces/{memory_space_id}/summarize \
  -H "Content-Type: application/json" \
  -d '{"summary_type": "one_pager"}' | python3 -m json.tool

# Query (stub — returns 501)
curl -s -X POST http://localhost:8000/api/v1/memory-spaces/{memory_space_id}/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this project about?"}' | python3 -m json.tool
```

Replace `{workspace_id}` and `{memory_space_id}` with ids from create responses. Valid status values: `active`, `archived`. Valid summary types: `one_pager`, `recent_updates`.
