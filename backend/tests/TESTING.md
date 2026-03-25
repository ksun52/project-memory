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

---

## Manual AI Extraction Verification

End-to-end verification of the extraction pipeline using a real OpenAI API key. This hits the real LLM and embedding APIs — expect ~5-15s per source depending on content length.

### Prerequisites

1. Stack running:
   ```bash
   cd backend
   docker compose up -d
   source .venv/bin/activate
   alembic upgrade head
   python -m scripts.seed_dev_user
   ```

2. `.env` must have a valid OpenAI key:
   ```
   OPENAI_API_KEY=sk-...
   ```
   Confirm it's loaded:
   ```bash
   OPENAI_API_KEY=sk-... uvicorn app.main:app --reload --log-level debug
   ```

3. Create a workspace and memory space to use as the test target:
   ```bash
   WS_ID=$(curl -s -X POST http://localhost:8000/api/v1/workspaces \
     -H "Content-Type: application/json" \
     -d '{"name": "AI Test Workspace"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

   MS_ID=$(curl -s -X POST http://localhost:8000/api/v1/workspaces/$WS_ID/memory-spaces \
     -H "Content-Type: application/json" \
     -d '{"name": "AI Test Space"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

   echo "MS_ID=$MS_ID"
   ```

### DB helper

All verification queries below use psql. Open a second terminal:
```bash
docker compose exec db psql -U project_memory -d project_memory
```

### Test 1: Note Source Extraction

```bash
SOURCE_ID=$(curl -s -X POST http://localhost:8000/api/v1/memory-spaces/$MS_ID/sources \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "note",
    "title": "Q1 Planning Notes",
    "content": "We decided to migrate the auth service from session-based to JWT tokens. Timeline is 6 weeks starting March 1. Sarah owns the backend migration. Open question: do we also migrate the admin panel or keep it on sessions? Risk: the mobile app caches tokens aggressively and we had a bug last quarter with stale refresh tokens."
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "SOURCE_ID=$SOURCE_ID"
```

The response returns immediately with `"processing_status": "pending"`. Extraction runs in a background thread.

**Wait ~10s**, then poll the source to confirm completion:

```bash
curl -s http://localhost:8000/api/v1/sources/$SOURCE_ID | python3 -m json.tool
```

Expected: `"processing_status": "completed"`, `"processing_error": null`.

**Verify in DB:**

```sql
-- Source status
SELECT id, title, processing_status, processing_error FROM sources WHERE id = '<SOURCE_ID>';

-- Memory records created (expect 5-15 records with types like decision, event, task, question, issue)
SELECT id, record_type, importance, confidence, substring(content, 1, 80) AS content_preview
FROM memory_records
WHERE memory_space_id = '<MS_ID>' AND deleted_at IS NULL
ORDER BY importance, confidence DESC;

-- Record-source links
SELECT r.record_type, r.importance, rsl.evidence_start, rsl.evidence_end
FROM record_source_links rsl
JOIN memory_records r ON r.id = rsl.record_id
WHERE rsl.source_id = '<SOURCE_ID>' AND rsl.deleted_at IS NULL;

-- Source chunks (content gets chunked for embedding storage)
SELECT id, chunk_index, char_start, char_end, length(content) AS chars
FROM source_chunks
WHERE source_id = '<SOURCE_ID>' AND deleted_at IS NULL
ORDER BY chunk_index;

-- Embeddings (one per memory record + one per source chunk, all 1536-dim)
SELECT entity_type, entity_id, model_id, array_length(embedding::real[], 1) AS dims
FROM embeddings
WHERE deleted_at IS NULL
ORDER BY entity_type, created_at DESC;
```

What to check:
- `memory_records` has rows with varied `record_type` values (not all the same type)
- `confidence` values are between 0 and 1
- `importance` values are `low`, `medium`, or `high`
- Every record has a `record_source_links` row pointing back to this source
- Every record and chunk has an `embeddings` row with `array_length = 1536`
- `model_id` = `text-embedding-3-small`

### Test 2: Document Source Extraction

Create a small test file:
```bash
echo "Meeting notes from March 15 standup.
Jake reported the CI pipeline is broken on the staging branch — flaky Selenium tests.
Decision: we will disable the Selenium suite in CI and move to Playwright by end of sprint.
Action item: Maria to set up the Playwright test harness by Friday.
Blocker: the QA environment is down, DevOps ticket INFRA-442 is open." > /tmp/test_doc.txt
```

Upload it:
```bash
SOURCE_ID2=$(curl -s -X POST http://localhost:8000/api/v1/memory-spaces/$MS_ID/sources \
  -F "title=March 15 Standup Notes" \
  -F "file=@/tmp/test_doc.txt" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "SOURCE_ID2=$SOURCE_ID2"
```

**Wait ~10s**, then:

```bash
curl -s http://localhost:8000/api/v1/sources/$SOURCE_ID2 | python3 -m json.tool
```

Expected: `"processing_status": "completed"`. Verify the same DB queries as Test 1 substituting `SOURCE_ID2`. The document pipeline goes through `_parse_document` (txt → raw text) before hitting the same extraction path.

Additionally verify the file metadata was stored:
```sql
SELECT source_id, mime_type, size_bytes, original_filename
FROM source_files
WHERE source_id = '<SOURCE_ID2>';
```

### Test 3: Failure Verification

**3a — Empty content (should fail with zero-records guard):**

```bash
FAIL_ID=$(curl -s -X POST http://localhost:8000/api/v1/memory-spaces/$MS_ID/sources \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "note",
    "title": "Empty Note",
    "content": "   "
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
```

Wait ~5s, then:
```bash
curl -s http://localhost:8000/api/v1/sources/$FAIL_ID | python3 -m json.tool
```

Expected: `"processing_status": "failed"`, `"processing_error"` contains `"Extraction produced zero records from non-empty content"`.

Note: if content is truly whitespace-only, the zero-records guard skips (line 74 of `extraction.py` checks `content_text.strip()`), so status may end up `"completed"` with 0 records. To reliably trigger the failure, use content that has text but is gibberish the LLM can't extract from:

```bash
FAIL_ID2=$(curl -s -X POST http://localhost:8000/api/v1/memory-spaces/$MS_ID/sources \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "note",
    "title": "Gibberish Note",
    "content": "asdf jkl; qwerty zxcvbn 12345 !!@@## lorem ipsum random noise blah"
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
```

The LLM may still extract something from gibberish — the zero-records guard only fires when the LLM returns literally 0 records from non-empty content. If it returns records, they'll just have low confidence.

**3b — Invalid source (DB-level failure):**

Force an extraction error by creating a source then deleting its content row before extraction completes. This is hard to race manually, so the easier check is the DB state after the automated tests:

```sql
-- Check for any failed sources
SELECT id, title, processing_status, processing_error
FROM sources
WHERE processing_status = 'failed';
```

### Test 4: Log Verification

With `--log-level debug`, the uvicorn output shows the extraction thread lifecycle. Look for these log lines after creating a source:

```
INFO:     app.domains.source.service - Triggering extraction for source <UUID>
```

On success:
```
INFO:     app.processes.extraction - Extraction completed for source <UUID>: N records, M chunks
```

On failure:
```
ERROR:    app.processes.extraction - Extraction failed for source <UUID>
```

The background thread runs as a daemon thread — if you kill the server mid-extraction, the thread dies silently. No cleanup needed.

### Cleanup

```bash
# Delete the test workspace (cascades to memory spaces, sources, etc.)
curl -s -o /dev/null -w "Status: %{http_code}\n" \
  -X DELETE http://localhost:8000/api/v1/workspaces/$WS_ID
```

Note: soft-delete cascade covers sources and memory spaces. Embeddings and chunks are orphaned (no cascade from source soft-delete to embeddings table). This is a known limitation — embeddings reference entity IDs but have no FK cascade.

---

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

### Integration Clients (Track C)

No server needed — these run directly in the Python shell. From the `backend/` directory with the venv active:

```bash
python -c "
from app.integrations.storage_client import storage_client
from app.integrations.llm_client import llm_client
from app.integrations.workos_client import workos_client
print('All imports OK')
"
```

#### LocalStorageClient — write, read, delete

```bash
python -c "
from app.integrations.storage_client import LocalStorageClient
import tempfile

client = LocalStorageClient(tempfile.mkdtemp())
key = 'space-1/source-1/test.txt'

# Save
path = client.save_file(key, b'hello world')
print(f'Saved to: {path}')

# Read
print(f'Read back: {client.read_file(key)}')

# Exists
print(f'Exists: {client.file_exists(key)}')

# Delete
client.delete_file(key)
print(f'Exists after delete: {client.file_exists(key)}')
"
```

#### LLM & WorkOS stubs — confirm NotImplementedError

```bash
python -c "
import asyncio
from app.integrations.llm_client import llm_client
try:
    asyncio.run(llm_client.extract('test', 'note'))
except NotImplementedError as e:
    print(f'LLM stub OK: {e}')
"

python -c "
from app.integrations.workos_client import workos_client
try:
    workos_client.get_authorization_url()
except NotImplementedError as e:
    print(f'WorkOS stub OK: {e}')
"
```
