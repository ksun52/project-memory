# Backend Architecture

**Product:** Project Memory  
**Version:** v0.1 (MVP)  
**Status:** Draft

---

## 1. Overview

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Runtime | Python 3.12+ |
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Database | PostgreSQL + pgvector |
| Auth | WorkOS |
| File Storage | S3-compatible (local filesystem for dev) |
| LLM | TBD (OpenAI or Anthropic) |
| Embeddings | OpenAI text-embedding-3-small (tentative) |

### Architecture Principles

- **Domain-Driven Design** — code organized by business domain, not technical layer
- **Clean separation of concerns** — routers handle HTTP, services handle business logic, models handle persistence
- **ORM → Entity transformation** — ORM models map to database tables; data is immediately transformed into domain entities for all business logic
- **Services as domain interfaces** — cross-domain communication happens through service function calls; no repository layer for MVP
- **API versioning** — all routes prefixed with `/api/v1`
- **Offset-based pagination** — `page` (1-indexed) + `page_size` (default 20, max 100) for all list endpoints
- **Soft delete** — nullable `deleted_at` timestamp on all entities except `users`

---

## 2. Domains

| Domain | Has Router? | Purpose |
|--------|-------------|---------|
| **Auth** | Yes | User identity, WorkOS SSO, session/token management |
| **Workspace** | Yes | Workspace CRUD, ownership validation |
| **Memory Space** | Yes | Memory space CRUD, status lifecycle, summarize + query endpoints |
| **Source** | Yes | Source ingestion (note/document), file storage, parsing, chunking |
| **Memory** | Yes | Memory record CRUD, provenance links, status transitions |
| **AI** | **No** | Extraction, embedding, summarization, query/RAG (service layer only) |

### Domain Dependencies

```
Auth ← all domains depend on Auth for user resolution and access checks

Workspace → Auth
Memory Space → Auth, Workspace, AI (summarization, query)
Source → Auth, Workspace, Memory Space
Memory → Auth, Workspace, Memory Space
AI → Source (read content/chunks), Memory (write records), Integrations (LLM, embeddings)
```

Extraction is triggered implicitly on source creation. The source service kicks off the extraction process, which orchestrates AI service functions.

---

## 3. API Surface

All routes are prefixed with `/api/v1`.

### Auth

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/auth/login` | Initiate WorkOS SSO redirect |
| GET | `/auth/callback` | Handle WorkOS callback, issue token |
| POST | `/auth/logout` | Invalidate session |
| GET | `/auth/me` | Return current authenticated user |

### Workspace

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/workspaces` | Create workspace |
| GET | `/workspaces` | List user's workspaces |
| GET | `/workspaces/{id}` | Get workspace detail |
| PATCH | `/workspaces/{id}` | Update workspace |
| DELETE | `/workspaces/{id}` | Soft delete workspace |

### Memory Space

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/workspaces/{workspace_id}/memory-spaces` | Create memory space |
| GET | `/workspaces/{workspace_id}/memory-spaces` | List memory spaces (with status filter) |
| GET | `/memory-spaces/{id}` | Get memory space detail |
| PATCH | `/memory-spaces/{id}` | Update memory space |
| DELETE | `/memory-spaces/{id}` | Soft delete / archive |
| POST | `/memory-spaces/{id}/summarize` | Generate one-pager or recent updates summary |
| POST | `/memory-spaces/{id}/query` | Natural language question → answer with citations |

### Source

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/memory-spaces/{id}/sources` | Create source (note text or file upload) |
| GET | `/memory-spaces/{id}/sources` | List sources (with type/status filters) |
| GET | `/sources/{id}` | Get source detail |
| GET | `/sources/{id}/content` | Get full source text content |
| DELETE | `/sources/{id}` | Soft delete source + cascade |

### Memory

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/memory-spaces/{id}/records` | List/filter records (type, status, importance) |
| POST | `/memory-spaces/{id}/records` | Create manual record |
| GET | `/records/{id}` | Get record detail |
| PATCH | `/records/{id}` | Edit record (content, status, importance) |
| DELETE | `/records/{id}` | Soft delete record |
| GET | `/records/{id}/sources` | Get linked sources (provenance) |

---

## 4. Types Per Domain

Each domain has three type categories, all consolidated into a single `models.py` file per domain:

- **ORM Models** — SQLAlchemy models mapped directly to database tables
- **Domain Entities** — Business logic representations (dataclasses); ORM data is transformed into entities immediately after querying
- **DTOs (Schemas)** — Pydantic models for request validation and response serialization

All three categories live in `models.py` to keep things simple — each domain has only 1-2 ORM models and a small number of entities/DTOs, so separate files would add friction without meaningful organization benefit.

| Domain | ORM Models | Domain Entities | DTOs |
|--------|-----------|----------------|------|
| **Auth** | `User` | `UserEntity` | `AuthCallbackParams`, `UserResponse`, `TokenResponse` |
| **Workspace** | `Workspace` | `WorkspaceEntity` | `WorkspaceCreate`, `WorkspaceUpdate`, `WorkspaceResponse` |
| **Memory Space** | `MemorySpace` | `MemorySpaceEntity` | `MemorySpaceCreate`, `MemorySpaceUpdate`, `MemorySpaceResponse`, `SummaryRequest`, `SummaryResponse`, `QueryRequest`, `QueryResponse` |
| **Source** | `Source`, `SourceContent`, `SourceFile`, `SourceChunk` | `SourceEntity`, `SourceContentEntity`, `SourceFileEntity`, `SourceChunkEntity` | `SourceCreateNote`, `SourceCreateDocument`, `SourceResponse`, `SourceDetailResponse`, `SourceContentResponse` |
| **Memory** | `MemoryRecord`, `RecordSourceLink` | `MemoryRecordEntity`, `RecordSourceLinkEntity` | `RecordCreate`, `RecordUpdate`, `RecordResponse`, `RecordListResponse`, `RecordSourceLinkResponse` |
| **AI** | `Embedding`, `GeneratedSummary` | `ExtractionOutput`, `ExtractedRecord`, `EmbeddingResult`, `SummaryResult`, `QueryResult` | — (no router, no request/response DTOs) |

AI domain entities represent intermediate structured output from LLM calls (e.g., a list of extracted records with types, content, and confidence scores) before those results are persisted through the Memory domain's service. Modeling these as domain entities rather than ORM models keeps the AI layer decoupled from persistence.

---

## 5. Services Per Domain

### Auth Service

- **WorkOS SSO flow** — initiate login redirect, handle callback, exchange code for user profile
- **Token management** — issue JWT, validate on each request
- **User resolution** — get-or-create user from WorkOS profile; resolve current user from request token
- **Access validation** — verify user has access to a workspace or memory space (called by other domains as a service function)

### Workspace Service

- **CRUD operations** — create, list (for user), get, update, soft delete
- **Ownership enforcement** — verify requesting user is workspace owner

### Memory Space Service

- **CRUD operations** — create, list (with status filter), get, update, soft delete/archive
- **Status lifecycle** — active ↔ archived transitions
- **Workspace scoping** — ensure memory space belongs to user's workspace
- **Summarization orchestration** — call AI summarization service, return/cache result
- **Query orchestration** — call AI query service, return answer with citations

### Source Service

- **Source creation** — handle note (text input) vs document (file upload) flows
- **File storage** — upload document to S3-compatible storage, store metadata
- **Document parsing** — extract plain text from PDF, DOCX, TXT into source content
- **Chunking** — split source content into overlapping chunks
- **Trigger extraction** — after source + content storage commits, kick off extraction process
- **Cascade soft delete** — soft delete source + content + file + chunks + links + embeddings

### Memory Service

- **Record CRUD** — create (manual), read, update, soft delete
- **Bulk record creation** — persist multiple records from extraction output in one transaction
- **Status transitions** — active / tentative / outdated / archived lifecycle
- **Provenance management** — create and read record-source links with evidence text
- **Filtering + pagination** — query records by type, status, importance, date range

### AI Service (no router)

- **Extraction** — take source content → build prompt → call LLM → parse structured output → return `ExtractionOutput` domain entity
- **Embedding generation** — generate vector embeddings for source chunks and memory records via embedding model
- **Summarization** — collect relevant records → build prompt → call LLM → return `SummaryResult` domain entity
- **Query / RAG** — take NL question → retrieve relevant records + chunks (vector similarity) → build prompt → call LLM → return `QueryResult` with citations
- **Prompt management** — select and version prompt templates for each AI task

---

## 6. Async Processes

Async processes live in the `processes/` folder, separate from domain services. Each process orchestrates a multi-step workflow by calling functions from domain services.

### Extraction Process (`processes/extraction.py`)

Triggered implicitly after source creation. Orchestrates:

1. Read source content (via Source service)
2. Parse document if needed (via Source service)
3. Chunk content (via Source service)
4. Call LLM extraction (via AI service) → returns `ExtractionOutput`
5. Persist extracted records (via Memory service — bulk creation)
6. Generate embeddings for chunks and records (via AI service)
7. Update source `processing_status` to `completed` or `failed`

**MVP:** Called synchronously inline during source creation.
**Future:** Enqueued as a background job via DB-backed job queue.

The extraction process is a standalone function that can be called either inline or by a worker — no code changes needed for the async transition.

---

## 7. External Integrations

All external service clients live in `integrations/` and are injected into domain services.

| Integration | Client | Used By | Purpose |
|-------------|--------|---------|---------|
| **WorkOS** | `workos_client.py` | Auth service | SSO authentication, user profile sync |
| **LLM Provider** | `llm_client.py` | AI service | Extraction, summarization, query answering |
| **Embedding Model** | `llm_client.py` | AI service | Vector generation (text-embedding-3-small) |
| **File Storage** | `storage_client.py` | Source service | Document upload/download (S3 or local for dev) |

**Document parsing** is handled by Python libraries (not external services):

- `pdfplumber` or `PyMuPDF` — PDF → text
- `python-docx` — DOCX → text
- Built-in — TXT

---

## 8. Cross-Cutting Concerns

### Authentication & Authorization

- FastAPI middleware validates JWT on every request (except auth routes)
- `get_current_user` dependency lives in Auth service — resolves user from token
- Workspace and memory space access checks also live in Auth service — called by other domain services as needed
- Access chain: user → workspace ownership → memory space scoping

### Auth Bypass (Local Development)

For local development, set `AUTH_BYPASS=True` (the default) in configuration. This skips WorkOS SSO entirely and authenticates all requests as a hardcoded dev user:

- **Dev user ID:** `00000000-0000-0000-0000-000000000001`
- **Seeding:** Run `python -m scripts.seed_dev_user` to create the dev user in the database
- **Login flow:** `GET /auth/login` returns a redirect URL pointing to `/api/v1/auth/callback?code=dev`, which generates a real JWT for the dev user
- **Request auth:** `get_current_user` dependency returns the dev user directly without checking the JWT

Set `AUTH_BYPASS=False` and provide `WORKOS_API_KEY` / `WORKOS_CLIENT_ID` to enable real SSO.

### Error Handling

- Domain-specific exceptions defined in each domain (e.g., `SourceNotFoundError`, `ExtractionFailedError`)
- Global exception handler in `core/middleware.py` maps domain exceptions to HTTP status codes
- Consistent error response format: `{ "error": { "code": "...", "message": "..." } }`

### Logging

- Structured logging configured in `core/middleware.py`
- Request/response logging middleware for all endpoints
- Domain services log business-level events (source created, extraction started/completed/failed)

### Soft Delete

- All entities (except `users`) have a nullable `deleted_at` timestamp
- Base model mixin in `core/models.py` provides soft delete behavior
- All queries filter `WHERE deleted_at IS NULL` by default
- Soft-deleting a parent cascades to children

### Pagination

- Offset-based: `page` (1-indexed) + `page_size` (default 20, max 100)
- All list endpoints return: `{ "items": [...], "total": N, "page": N, "page_size": N }`

### Database

- Alembic for migrations (version-controlled schema changes)
- SQLAlchemy 2.0
- Connection pooling via SQLAlchemy engine defaults

---

## 9. Project Folder Structure

```
backend/
├── alembic/
│   └── versions/                  # Migration files
├── alembic.ini
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, router registration, middleware setup
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # Pydantic Settings (DB URL, API keys, env vars)
│   │   ├── database.py            # SQLAlchemy engine, session factory, Base
│   │   ├── exceptions.py          # Base exception classes, global handler
│   │   ├── middleware.py          # CORS, logging, error handling middleware
│   │   └── models.py             # Base model mixin (timestamps, soft delete)
│   │
│   ├── domains/
│   │   ├── __init__.py
│   │   │
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── router.py          # Login, callback, logout, me
│   │   │   ├── service.py         # WorkOS flow, token mgmt, user resolution, access checks
│   │   │   └── models.py          # User ORM + UserEntity + auth DTOs
│   │   │
│   │   ├── workspace/
│   │   │   ├── __init__.py
│   │   │   ├── router.py
│   │   │   ├── service.py
│   │   │   └── models.py          # Workspace ORM + WorkspaceEntity + DTOs
│   │   │
│   │   ├── memory_space/
│   │   │   ├── __init__.py
│   │   │   ├── router.py          # CRUD + summarize + query
│   │   │   ├── service.py
│   │   │   └── models.py          # MemorySpace ORM + entity + DTOs (incl. Summary/Query)
│   │   │
│   │   ├── source/
│   │   │   ├── __init__.py
│   │   │   ├── router.py
│   │   │   ├── service.py         # Creation, parsing, chunking, file storage
│   │   │   └── models.py          # Source/SourceContent/SourceFile/SourceChunk ORM + entities + DTOs
│   │   │
│   │   ├── memory/
│   │   │   ├── __init__.py
│   │   │   ├── router.py
│   │   │   ├── service.py         # CRUD, bulk creation, provenance, filtering
│   │   │   └── models.py          # MemoryRecord/RecordSourceLink ORM + entities + DTOs
│   │   │
│   │   └── ai/
│   │       ├── __init__.py
│   │       ├── service.py         # Extraction, embedding, summarization, query/RAG
│   │       ├── models.py          # Embedding/GeneratedSummary ORM + AI domain entities
│   │       └── prompts/
│   │           ├── __init__.py
│   │           ├── extraction.py
│   │           ├── summarization.py
│   │           └── query.py
│   │
│   ├── processes/
│   │   ├── __init__.py
│   │   └── extraction.py          # Multi-step extraction orchestration
│   │
│   └── integrations/
│       ├── __init__.py
│       ├── workos_client.py       # WorkOS SDK wrapper
│       ├── llm_client.py          # LLM + embedding API wrapper
│       └── storage_client.py      # S3 / local file storage wrapper
│
├── tests/
│   ├── conftest.py                # Fixtures, test DB setup
│   └── domains/
│       ├── test_auth.py
│       ├── test_workspace.py
│       ├── test_memory_space.py
│       ├── test_source.py
│       ├── test_memory.py
│       └── test_ai.py
│
├── requirements.txt
├── .env.example
├── Dockerfile
└── docker-compose.yml             # Postgres + pgvector for local dev
```

---

## 10. Future Considerations

| Feature | Approach |
|---------|----------|
| Semantic search endpoint | Add `GET /memory-spaces/{id}/search` to Memory Space domain with semantic + structured filtering |
| Async extraction | Replace inline call with DB-backed job queue; extraction process function unchanged |
| Re-extraction | Add explicit `POST /sources/{id}/extract` endpoint; handle replacing old records |
| Background job queue | DB-backed queue with polling worker; `processes/` functions as job handlers |
| Rate limiting | FastAPI middleware or reverse proxy |
| WebSocket updates | Real-time extraction progress notifications |
