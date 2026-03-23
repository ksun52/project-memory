# Project Memory — Build Timeline

## Context

Project Memory exists as documentation only (PRD, architecture, data model, API contract, frontend/backend plans, AI layer design). Zero implementation code exists. This timeline identifies what to build, in what order, and what can be parallelized — getting from docs to a working MVP.

AI layer uses real OpenAI API calls (GPT for extraction/summarization/query, text-embedding-3-small for embeddings). Single provider for simplicity. The AI domain is isolated as a service-only layer with no router, keeping LLM concerns cleanly separated.

---

## Phase 0: Foundation (Sequential — Must Complete First)

Everything depends on this. No parallel work until Phase 0 is done.

### 0.1 Infrastructure — Docker Compose + Postgres/pgvector
- `docker-compose.yml` — Postgres 16 with pgvector extension, persistent volume
- `.env.example` — DATABASE_URL, SECRET_KEY, CORS_ORIGINS, etc.
- **Verify:** `docker compose up` → running Postgres with `CREATE EXTENSION vector` working

### 0.2 Backend Scaffolding
- `backend/requirements.txt` — fastapi, uvicorn, sqlalchemy, alembic, psycopg2-binary, pydantic-settings, python-jose, pdfplumber, python-docx, httpx, pytest, openai
- `backend/app/main.py` — FastAPI app, CORS, health check (`GET /api/v1/health`), router registration stubs
- `backend/app/core/config.py` — Pydantic Settings
- `backend/app/core/database.py` — SQLAlchemy 2.0 engine, session factory, Base, `get_db` dependency
- `backend/app/core/models.py` — `TimestampMixin`, `SoftDeleteMixin`, base query filtering
- `backend/app/core/exceptions.py` — `AppException`, `NotFoundError`, `ForbiddenError`, `ValidationError`
- `backend/app/core/middleware.py` — global exception handler, request logging
- Empty `__init__.py` files for all domain/process/integration directories
- `backend/tests/conftest.py` — test DB setup, fixtures
- **Verify:** `uvicorn app.main:app` starts, health check returns 200

### 0.3 All ORM Models + Alembic Initial Migration
All 11 tables defined upfront (data model is fully specified and stable):
- `auth/models.py` — User
- `workspace/models.py` — Workspace
- `memory_space/models.py` — MemorySpace
- `source/models.py` — Source, SourceContent, SourceFile, SourceChunk
- `memory/models.py` — MemoryRecord, RecordSourceLink
- `ai/models.py` — Embedding, GeneratedSummary
- Alembic setup + `001_initial_schema.py` migration
- **Verify:** `alembic upgrade head` creates all tables with correct constraints/indexes

### 0.4 Frontend Scaffolding
- `frontend/` — Next.js 14+ App Router via `create-next-app`
- Tailwind, shadcn/ui initialized with core components (button, dialog, form, input, tabs, toast, badge, card, skeleton, sheet)
- `shared/types/api.ts` — `PaginatedResponse<T>`, `ApiError`, `PaginationParams`
- `shared/api/client.ts` — typed fetch wrapper
- `shared/components/providers.tsx` — QueryClientProvider stub
- Root layout + root redirect page
- **Verify:** `npm run dev` starts, page loads

### 0.5 Auth Bypass for Development
- `auth/entities.py`, `auth/schemas.py`, `auth/service.py` with `AUTH_BYPASS=true` mode returning a hardcoded dev user
- `auth/router.py` — stub routes for login, callback, logout, me
- Seed script inserting one dev user
- **Verify:** Auth-protected endpoints callable without real JWT in bypass mode

---

## Phase 1: Core CRUD Domains (Parallel Tracks)

### Backend Track A: Workspace Domain
**Depends on:** Phase 0
- entities.py, schemas.py, service.py (CRUD + ownership enforcement), router.py
- Register in main.py
- Tests
- **Verify:** All 5 workspace endpoints work, ownership checks pass

### Backend Track B: Memory Space Domain (CRUD only)
**Depends on:** Track A (workspace service for scoping)
- entities.py, schemas.py, service.py (CRUD + workspace scoping + status lifecycle)
- router.py — CRUD endpoints only; `/summarize` and `/query` return 501 for now
- Tests
- **Verify:** Memory space CRUD works, workspace scoping enforced

### Backend Track C: Integration Clients
**Depends on:** Phase 0 (parallel with A & B)
- `integrations/storage_client.py` — `LocalStorageClient` (read/write to local filesystem)
- `integrations/llm_client.py` — OpenAI API wrapper for both LLM calls (extraction, summarization, query) and embeddings (`text-embedding-3-small`). Single provider, single SDK.
- `integrations/workos_client.py` — stub raising NotImplementedError

### Frontend Track D: MSW + Auth + Shared Layer
**Depends on:** Phase 0.4
- MSW setup: browser worker, handlers for all domains with in-memory seed data
- Auth domain: types, api, hooks, AuthProvider, LoginForm, AuthGuard
- Shared components: app-sidebar, breadcrumbs, page-header, empty-state, loading-skeleton, error-boundary
- Shared hooks: use-pagination
- App shell: (auth) routes + (dashboard) layout with sidebar/auth guard
- **Verify:** MSW intercepts calls, login flow works, dashboard layout renders

### Frontend Track E: Workspace + Memory Space UI
**Depends on:** Track D
- Workspace domain: types, api, hooks, WorkspaceList, WorkspaceCard, WorkspaceCreateDialog
- Memory Space domain: types, api, hooks, MemorySpaceList, MemorySpaceCard, MemorySpaceCreateDialog
- Route pages: /workspaces, /workspaces/[workspaceId]
- **Verify:** Navigate workspace list → memory space list, CRUD works against MSW

### Phase 1 Milestone
- Backend: Workspace + Memory Space CRUD functional with auth bypass
- Frontend: Login → workspace list → memory space list navigation working against MSW

---

## Phase 2: Data Domains + Ingestion (Parallel Tracks)

### Backend Track F: Source Domain
**Depends on:** Phase 1 backend
- entities.py, schemas.py
- service.py: create_note_source, create_document_source (with file storage + parsing), chunk_source_content, list/get/delete with cascade
- router.py, tests
- **Verify:** Note creation, document upload + parsing, chunking produces correct offsets

### Backend Track G: Memory Domain
**Depends on:** Phase 1 backend (parallel with Track F)
- entities.py, schemas.py
- service.py: create_record (manual), bulk_create_records (from extraction), list with filters, get, update, delete, get_record_sources (provenance)
- router.py, tests
- **Verify:** Manual record CRUD, bulk creation, filtering, provenance links

### Backend Track H: AI Service + Extraction Process
**Depends on:** Tracks F + G (needs their service interfaces), Track C (LLM + embedding clients)
- `ai/entities.py` — ExtractedRecord, ExtractionOutput, SummaryResult, QueryResult, Citation
- `ai/prompts/extraction.py` — extraction prompt template with source-type variations, output schema, record type definitions
- `ai/prompts/summarization.py` — summarization prompt templates (one_pager, recent_updates)
- `ai/prompts/query.py` — RAG query prompt template with citation instructions
- `ai/service.py` — real implementations using OpenAI API via `llm_client.py` for both LLM and embeddings
- `processes/extraction.py` — orchestrates: read content → extract via OpenAI → persist records → chunk → embed via OpenAI → update status
- Wire extraction into Source service (called synchronously after source creation)
- Integration tests: create source → verify records + chunks + embeddings created
- **Verify:** Source creation triggers full extraction pipeline with real LLM calls, records are meaningful

### Frontend Track I: Memory Space Detail Page
**Depends on:** Frontend Track E
- Source domain: types, api, hooks, SourceList, SourceCard, UploadDialog (note + document modes), SourceDetail
- Memory domain: types, api, hooks, RecordList (with filters), RecordCard, RecordEditDialog, RecordCreateDialog, RecordProvenance
- MemorySpaceDetail component (tabbed: Sources, Records, Summary stub)
- Route: /workspaces/[wId]/memory-spaces/[msId]
- **Verify:** Full tabbed detail page, upload works, record filtering + CRUD works against MSW

### Phase 2 Milestone
- Backend: End-to-end pipeline: create source → LLM extraction (OpenAI) → records + chunks + embeddings (OpenAI)
- Frontend: Complete Memory Space Detail with Sources and Records tabs

---

## Phase 3: AI Features + Auth + Integration

### Backend Track J: Summarize + Query Endpoints
**Depends on:** Phase 2 backend
- Complete memory_space/schemas.py with SummaryRequest/Response, QueryRequest/Response
- Implement summarize + query in Memory Space service (calls AI service with real OpenAI API)
- Replace 501 stubs with real handlers
- Tests
- **Verify:** Summarize returns stored result, query returns answer with citations

### Backend Track K: Real Auth (WorkOS)
**Depends on:** Phase 0 auth bypass (parallel with Track J)
- Complete workos_client.py
- Real auth service: login redirect, callback flow, JWT issue/validate, get-or-create user
- Keep AUTH_BYPASS toggle for dev mode
- Tests with mocked WorkOS client
- **Verify:** Full SSO login flow works

### Frontend Track L: Summary + Query UI
**Depends on:** Frontend Track I
- SummaryDisplay, GenerateSummaryButton
- QueryBar, QueryResultPanel
- Wire into MemorySpaceDetail (Summary tab + persistent query bar)
- Update MSW handlers + hooks
- **Verify:** Summary tab shows content, query returns results with citation links

### Integration: Frontend ↔ Backend
**Depends on:** Tracks J + L complete
- Point frontend at real backend (disable MSW)
- Test all flows end-to-end: login → workspace → memory space → upload → records → summary → query → delete
- Fix contract mismatches
- **Verify:** Complete MVP works with real backend + Postgres + OpenAI

---

## AI Integration Strategy

### Single Provider: OpenAI (`integrations/llm_client.py`)
- Uses `openai` Python SDK for both LLM and embeddings — one API key, one provider
- LLM: GPT for extraction, summarization, query answering (structured JSON output)
- Embeddings: `text-embedding-3-small` (1536 dimensions) for semantic search
- Prompt templates versioned in `ai/prompts/` (extraction-v1, one-pager-v1, query-v1)
- Config: `OPENAI_API_KEY` in `.env`

### AI Service (`ai/service.py`)
| Function | Implementation |
|----------|---------------|
| `extract_from_content(text, type)` | Build extraction prompt with record type definitions + source-type instructions → OpenAI JSON output → validate → return ExtractionOutput |
| `generate_embeddings(texts)` | Batch embed via OpenAI `text-embedding-3-small` → return 1536-dim vectors |
| `summarize(records, type)` | Build summarization prompt with record contents → OpenAI → return markdown SummaryResult |
| `query(question, records, chunks)` | Build RAG prompt with retrieved context → OpenAI → return QueryResult with citations |

### Requirements
- `OPENAI_API_KEY` must be set in `.env` for AI features to work
- API costs are minimal for MVP-scale usage

---

## Parallel Work Summary

```
Phase 0 ─── sequential ─── ~1 day
  Infrastructure → Backend scaffold → ORM/Alembic → Frontend scaffold → Auth bypass

Phase 1 ─── parallel tracks ─── ~3-4 days
  BACKEND:  Track A (Workspace) → Track B (Memory Space) ←── Track C (Integrations, parallel)
  FRONTEND: Track D (MSW/Auth/Shared) → Track E (Workspace/MemSpace UI)

Phase 2 ─── parallel tracks ─── ~4-5 days
  BACKEND:  Track F (Source) ──┐
            Track G (Memory) ──┤→ Track H (AI Service + Extraction)
  FRONTEND: Track I (Detail Page)

Phase 3 ─── parallel tracks ─── ~3-4 days
  BACKEND:  Track J (Summarize/Query) ←── Track K (Real Auth, parallel)
  FRONTEND: Track L (Summary/Query UI)
  THEN:     Integration testing
```

**Solo developer: ~11-14 days focused work**
**Two developers (1 BE, 1 FE): ~8-10 days**

---

## Critical Files (Source of Truth)
- `docs/DATA_MODEL.md` — all 11 tables, every column, constraint, and index
- `docs/API_CONTRACT.md` — every endpoint, request/response shape
- `docs/api/openapi.yaml` — machine-readable API spec
- `docs/AI_LAYER.md` — extraction/summarization/query interfaces and prompt requirements
- `docs/BACKEND.md` — folder structure, domain responsibilities, service definitions
- `docs/FRONTEND.md` — folder structure, component inventory, hooks, MSW strategy
