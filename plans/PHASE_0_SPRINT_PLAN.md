# Phase 0: Foundation — Detailed Sprint Plan

## Context

Project Memory exists as documentation only — zero implementation code. Phase 0 establishes all infrastructure, scaffolding, ORM models, and auth bypass needed before any domain logic can be built. Nothing in Phase 1+ can start until Phase 0 is complete.

Work is on the `phase-0/foundation` branch in a git worktree at `../project-memory-phase-0`.

---

## Sprint 0.1: Infrastructure — Docker Compose + Postgres/pgvector

**Tests needed?** No — manual verification via `docker compose up` + psql connection test.

### Tasks

- [ ] **0.1.1** Create `.env.example` with all required environment variables
  - `DATABASE_URL=postgresql://project_memory:project_memory@localhost:5432/project_memory`
  - `SECRET_KEY=dev-secret-key-change-in-production`
  - `CORS_ORIGINS=http://localhost:3000`
  - `AUTH_BYPASS=true`
  - `OPENAI_API_KEY=sk-...`
  - `STORAGE_PATH=./storage`
  - `LOG_LEVEL=debug`

- [ ] **0.1.2** Create `docker-compose.yml`
  - Postgres 16 service with pgvector extension (`pgvector/pgvector:pg16`)
  - Named volume for data persistence (`project_memory_pgdata`)
  - Port mapping `5432:5432`
  - Health check with `pg_isready`
  - Environment variables for `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
  - Init script mount for pgvector extension creation

- [ ] **0.1.3** Create `scripts/init-db.sql`
  - `CREATE EXTENSION IF NOT EXISTS vector;`
  - Mounted into Postgres container at `/docker-entrypoint-initdb.d/`

- [ ] **0.1.4** Create `.env` from `.env.example` (gitignored)

- [ ] **0.1.5** Create/update `.gitignore`
  - `.env`, `__pycache__`, `.venv`, `node_modules`, `storage/`, `.next`, etc.

**Verify:** `docker compose up -d` → Postgres starts. `psql -U project_memory -d project_memory -c "SELECT extname FROM pg_extension WHERE extname = 'vector'"` returns a row.

---

## Sprint 0.2: Backend Scaffolding

**Tests needed?** No formal tests — just verify `uvicorn app.main:app` starts and health check returns 200. The `conftest.py` is setup for future tests.

### Tasks

- [ ] **0.2.1** Create `backend/requirements.txt` — All Python dependencies
  - fastapi, uvicorn, sqlalchemy 2.0, alembic, psycopg2-binary, pydantic-settings
  - python-jose (JWT), pdfplumber, python-docx, httpx, openai
  - pytest, pytest-asyncio (dev)

- [ ] **0.2.2** Create `backend/app/__init__.py` (empty)

- [ ] **0.2.3** Create `backend/app/core/__init__.py` (empty)

- [ ] **0.2.4** Create `backend/app/core/config.py` — Pydantic Settings
  - `class Settings(BaseSettings)` with: `DATABASE_URL` (str), `SECRET_KEY` (str), `CORS_ORIGINS` (str, comma-separated → split to list), `AUTH_BYPASS` (bool, default True), `OPENAI_API_KEY` (Optional[str], default None), `STORAGE_PATH` (str, default `./storage`), `LOG_LEVEL` (str, default `info`)
  - `model_config = SettingsConfigDict(env_file=".env")`
  - Module-level `settings = Settings()` singleton
  - Property `cors_origin_list` that splits CORS_ORIGINS by comma

- [ ] **0.2.5** Create `backend/app/core/database.py` — SQLAlchemy 2.0 setup
  - `engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)`
  - `SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)`
  - `Base = declarative_base()`
  - `def get_db() -> Generator[Session, None, None]` — yields session, closes in finally

- [ ] **0.2.6** Create `backend/app/core/models.py` — Base mixins
  - `TimestampMixin` — `created_at` (TIMESTAMP, default `func.now()`), `updated_at` (TIMESTAMP, default `func.now()`, onupdate `func.now()`)
  - `SoftDeleteMixin` — `deleted_at` (TIMESTAMP, nullable) + `@hybrid_property is_deleted`
  - These are declared_attr mixins, not standalone Base classes

- [ ] **0.2.7** Create `backend/app/core/exceptions.py` — Exception hierarchy
  - `class AppException(Exception)` with `status_code: int`, `error_code: str`, `message: str`
  - `class NotFoundError(AppException)` — `status_code=404, error_code="not_found"`
  - `class ForbiddenError(AppException)` — `status_code=403, error_code="forbidden"`
  - `class ValidationError(AppException)` — `status_code=400, error_code="validation_error"`

- [ ] **0.2.8** Create `backend/app/core/middleware.py` — Middleware
  - `async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse` — returns `{"error": {"code": exc.error_code, "message": exc.message}}`
  - `class RequestLoggingMiddleware(BaseHTTPMiddleware)` — logs method, path, status code, duration in ms

- [ ] **0.2.9** Create `backend/app/main.py` — FastAPI application
  - `app = FastAPI(title="Project Memory", version="0.1.0")`
  - Add CORS middleware with `settings.cors_origin_list`
  - Register `app_exception_handler` for `AppException`
  - Add `RequestLoggingMiddleware`
  - Create `api_v1 = APIRouter(prefix="/api/v1")`
  - `GET /api/v1/health` → `{"status": "ok"}`
  - Include `api_v1` in app
  - Comment stubs for future domain router imports

- [ ] **0.2.10** Create all empty `__init__.py` files for domain directories
  - `backend/app/domains/__init__.py`
  - `backend/app/domains/auth/__init__.py`
  - `backend/app/domains/workspace/__init__.py`
  - `backend/app/domains/memory_space/__init__.py`
  - `backend/app/domains/source/__init__.py`
  - `backend/app/domains/memory/__init__.py`
  - `backend/app/domains/ai/__init__.py`
  - `backend/app/domains/ai/prompts/__init__.py`
  - `backend/app/processes/__init__.py`
  - `backend/app/integrations/__init__.py`

- [ ] **0.2.11** Create `backend/tests/__init__.py` and `backend/tests/domains/__init__.py` (empty)

- [ ] **0.2.12** Create `backend/tests/conftest.py` — Test fixtures
  - Override `DATABASE_URL` to `project_memory_test` database
  - Create `test_engine` and `TestingSessionLocal`
  - `db_session` fixture: creates all tables via `Base.metadata.create_all`, yields session, drops all tables
  - `client` fixture: overrides `get_db` dependency with test session, yields `TestClient(app)`

**Verify:** `cd backend && pip install -r requirements.txt && uvicorn app.main:app` → `curl localhost:8000/api/v1/health` returns `{"status":"ok"}`.

---

## Sprint 0.3: ORM Models + Alembic Initial Migration

**Tests needed?** Yes — manual verification that `alembic upgrade head` creates all 11 tables correctly. Optionally add a test that the migration round-trips (`upgrade head` → `downgrade base`).

### Tasks

- [ ] **0.3.1** Create `backend/app/domains/auth/models.py` — User model
  - Table `users`: `id` (UUID PK), `auth_provider` (VARCHAR 50, NOT NULL), `auth_provider_id` (VARCHAR 255, NOT NULL), `email` (VARCHAR 255, NOT NULL), `display_name` (VARCHAR 255, NOT NULL), `created_at` (TIMESTAMP, NOT NULL), `updated_at` (TIMESTAMP, NOT NULL)
  - Uses `TimestampMixin` only (NO `SoftDeleteMixin` — users table has no `deleted_at`)
  - `UniqueConstraint('auth_provider', 'auth_provider_id', name='uq_users_auth_provider')`
  - `UniqueConstraint('email', name='uq_users_email')`
  - `Index('idx_users_email', 'email')`

- [ ] **0.3.2** Create `backend/app/domains/workspace/models.py` — Workspace model
  - Table `workspaces`: `id` (UUID PK), `owner_id` (UUID FK → users.id, NOT NULL), `name` (VARCHAR 255, NOT NULL), `description` (TEXT, NOT NULL), + `TimestampMixin` + `SoftDeleteMixin`
  - `Index('idx_workspaces_owner_id', 'owner_id')`
  - `relationship('User', back_populates=...)` for `owner`

- [ ] **0.3.3** Create `backend/app/domains/memory_space/models.py` — MemorySpace model
  - Table `memory_spaces`: `id` (UUID PK), `workspace_id` (UUID FK → workspaces.id, NOT NULL), `name` (VARCHAR 255, NOT NULL), `description` (TEXT, NOT NULL), `status` (VARCHAR 50, NOT NULL), + `TimestampMixin` + `SoftDeleteMixin`
  - `CheckConstraint("status IN ('active', 'archived')", name='ck_memory_spaces_status')`
  - `Index('idx_memory_spaces_workspace_id', 'workspace_id')`
  - `Index('idx_memory_spaces_status', 'status')`

- [ ] **0.3.4** Create `backend/app/domains/source/models.py` — 4 models
  - **Source** table `sources`: `id`, `memory_space_id` (FK → memory_spaces.id), `source_type` (VARCHAR 50), `title` (VARCHAR 500), `processing_status` (VARCHAR 50), `processing_error` (TEXT, **nullable**), + timestamps + soft delete
    - `CheckConstraint("source_type IN ('note', 'document', 'transcript')")`
    - `CheckConstraint("processing_status IN ('pending', 'processing', 'completed', 'failed')")`
    - Indexes: `idx_sources_memory_space_id`, `idx_sources_processing_status`
  - **SourceContent** table `source_contents`: `id`, `source_id` (FK → sources.id, **unique** for 1:1), `content_text` (TEXT), `created_at`, `deleted_at` (nullable)
  - **SourceFile** table `source_files`: `id`, `source_id` (FK → sources.id, **unique** for 1:1), `file_path` (VARCHAR 1000), `mime_type` (VARCHAR 100), `size_bytes` (BIGINT), `original_filename` (VARCHAR 500), `created_at`, `deleted_at` (nullable)
  - **SourceChunk** table `source_chunks`: `id`, `source_id` (FK → sources.id), `chunk_index` (INT), `content` (TEXT), `start_offset` (INT), `end_offset` (INT), `created_at`, `deleted_at` (nullable)
    - `UniqueConstraint('source_id', 'chunk_index')`
    - `Index('idx_source_chunks_source_id', 'source_id')`

- [ ] **0.3.5** Create `backend/app/domains/memory/models.py` — 2 models
  - **MemoryRecord** table `memory_records`: `id`, `memory_space_id` (FK), `record_type` (VARCHAR 50), `content` (TEXT), `origin` (VARCHAR 50), `status` (VARCHAR 50), `confidence` (DECIMAL(3,2)), `importance` (VARCHAR 20), `metadata` (JSONB), + timestamps + soft delete
    - Check constraints for all enum columns + confidence range `(>= 0 AND <= 1)`
    - Indexes: `idx_memory_records_memory_space_id`, `idx_memory_records_status`, `idx_memory_records_record_type`
  - **RecordSourceLink** table `record_source_links`: `id`, `record_id` (FK → memory_records.id), `source_id` (FK → sources.id), `evidence_text` (TEXT, **nullable**), `evidence_start_offset` (INT, **nullable**), `evidence_end_offset` (INT, **nullable**), `created_at`, `deleted_at` (nullable)
    - `UniqueConstraint('record_id', 'source_id')`
    - Indexes: `idx_record_source_links_record_id`, `idx_record_source_links_source_id`

- [ ] **0.3.6** Create `backend/app/domains/ai/models.py` — 2 models
  - **Embedding** table `embeddings`: `id`, `entity_type` (VARCHAR 50), `entity_id` (UUID), `embedding` (Vector(1536) from pgvector), `model_id` (VARCHAR 100), `created_at`, `deleted_at` (nullable)
    - `UniqueConstraint('entity_type', 'entity_id', 'model_id')`
    - `CheckConstraint("entity_type IN ('memory_record', 'source_chunk')")`
    - `Index('idx_embeddings_entity', 'entity_type', 'entity_id')`
    - HNSW index: `Index('idx_embeddings_vector', 'embedding', postgresql_using='hnsw', postgresql_with={'m': 16, 'ef_construction': 64}, postgresql_ops={'embedding': 'vector_cosine_ops'})`
    - Requires `from pgvector.sqlalchemy import Vector`
  - **GeneratedSummary** table `generated_summaries`: `id`, `memory_space_id` (FK), `summary_type` (VARCHAR 50), `title` (VARCHAR 500), `content` (TEXT), `is_edited` (BOOLEAN), `edited_content` (TEXT, **nullable**), `record_ids_used` (ARRAY(UUID)), `prompt_version` (VARCHAR 100), `model_id` (VARCHAR 100), `generated_at` (TIMESTAMP), + timestamps + soft delete
    - `CheckConstraint("summary_type IN ('one_pager', 'recent_updates')")`
    - Indexes: `idx_generated_summaries_memory_space_id`, `idx_generated_summaries_summary_type`

- [ ] **0.3.7** Add `pgvector` to `backend/requirements.txt`
  - `pgvector==0.3.*` (SQLAlchemy integration for Vector type)

- [ ] **0.3.8** Initialize Alembic
  - Run `alembic init alembic` in `backend/`
  - Edit `alembic.ini`: comment out `sqlalchemy.url` (will come from env.py)
  - Edit `alembic/env.py`:
    - Import `settings` from `app.core.config`
    - Import `Base` from `app.core.database`
    - Import ALL domain models (auth, workspace, memory_space, source, memory, ai) so their tables register with Base.metadata
    - Set `target_metadata = Base.metadata`
    - Set `config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)`

- [ ] **0.3.9** Generate initial migration
  - `alembic revision --autogenerate -m "001_initial_schema"`
  - Review: check all 11 tables, constraints, indexes are present
  - Manually add `op.execute('CREATE EXTENSION IF NOT EXISTS vector')` at the top of `upgrade()` if not auto-generated
  - Manually add the HNSW index creation if Alembic doesn't auto-generate it correctly

- [ ] **0.3.10** Run migration and verify
  - `docker compose up -d` (ensure DB is running)
  - `alembic upgrade head`
  - Verify via psql: `\dt` shows all 11 tables, spot-check constraints and indexes

**Verify:** All 11 tables exist with correct columns, constraints, indexes. The `embeddings` table has a working vector column and HNSW index.

---

## Sprint 0.4: Frontend Scaffolding

**Tests needed?** No — verify dev server starts and page renders.

### Tasks

- [ ] **0.4.1** Create Next.js app with App Router
  - `npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"`
  - Verify `npm run dev` works

- [ ] **0.4.2** Initialize shadcn/ui + install core components
  - `npx shadcn@latest init` (default style, CSS variables)
  - `npx shadcn@latest add button dialog form input tabs toast badge card skeleton sheet dropdown-menu`

- [ ] **0.4.3** Install TanStack Query
  - `npm install @tanstack/react-query`

- [ ] **0.4.4** Create `frontend/src/shared/types/api.ts` — Shared API types
  - `PaginatedResponse<T>` interface: `items: T[]`, `total: number`, `page: number`, `page_size: number`
  - `ApiError` interface: `error: { code: string; message: string }`
  - `PaginationParams` interface: `page?: number`, `page_size?: number`

- [ ] **0.4.5** Create `frontend/src/shared/api/client.ts` — Typed fetch wrapper
  - Class or object with `get<T>`, `post<T>`, `patch<T>`, `del` methods
  - `NEXT_PUBLIC_API_URL` env var for base URL
  - Auto-attach `Authorization: Bearer` header from a token getter function
  - Parse JSON responses, throw `ApiError` on non-2xx
  - Handle `FormData` for file uploads (skip JSON content-type)

- [ ] **0.4.6** Create `frontend/src/shared/components/providers.tsx`
  - `'use client'` directive
  - `QueryClient` instance with `defaultOptions` (staleTime: 60s, retry: 1)
  - `QueryClientProvider` wrapping children
  - Export `Providers` component

- [ ] **0.4.7** Update `frontend/src/app/layout.tsx` — Root layout
  - Wrap children in `<Providers>`
  - Set metadata: title "Project Memory", description

- [ ] **0.4.8** Update `frontend/src/app/page.tsx` — Root redirect
  - `import { redirect } from 'next/navigation'`
  - `redirect('/workspaces')`

- [ ] **0.4.9** Create `frontend/.env.example`
  - `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`

- [ ] **0.4.10** Create empty domain directory structure with `.gitkeep` files
  - `src/domains/auth/components/.gitkeep`
  - `src/domains/workspace/components/.gitkeep`
  - `src/domains/memory-space/components/.gitkeep`
  - `src/domains/source/components/.gitkeep`
  - `src/domains/memory/components/.gitkeep`
  - `src/shared/hooks/.gitkeep`
  - `src/shared/utils/.gitkeep`

**Verify:** `cd frontend && npm run dev` starts. Page at `localhost:3000` redirects to `/workspaces` (which will 404 but that's expected — no page there yet).

---

## Sprint 0.5: Auth Bypass for Development

**Tests needed?** Yes — test auth endpoints return correct responses in bypass mode.

### Tasks

- [ ] **0.5.1** Create `backend/app/domains/auth/entities.py` — UserEntity
  - `@dataclass class UserEntity` with fields: `id` (UUID), `auth_provider` (str), `auth_provider_id` (str), `email` (str), `display_name` (str), `created_at` (datetime), `updated_at` (datetime)
  - `@classmethod from_orm(cls, user: User) -> UserEntity` factory method

- [ ] **0.5.2** Create `backend/app/domains/auth/schemas.py` — Pydantic DTOs
  - `class UserResponse(BaseModel)`: `id` (UUID), `email` (str), `display_name` (str), `created_at` (datetime). Config: `from_attributes = True`
  - `class TokenResponse(BaseModel)`: `access_token` (str), `token_type` (str, default "bearer"), `expires_in` (int, default 3600)

- [ ] **0.5.3** Create `backend/app/domains/auth/service.py` — Auth service
  - `DEV_USER_ID = UUID("00000000-0000-0000-0000-000000000001")`
  - `def get_current_user(db: Session = Depends(get_db)) -> UserEntity`:
    - If `settings.AUTH_BYPASS`: query User by `DEV_USER_ID`, convert to UserEntity, return
    - Else: raise `NotImplementedError("Real auth not yet implemented")`
  - `def login() -> dict`: returns `{"redirect_url": "/api/v1/auth/callback?code=dev"}` in bypass mode
  - `def callback(code: str) -> TokenResponse`: returns `TokenResponse(access_token="dev-token-bypass")` in bypass mode
  - `def logout() -> None`: no-op in bypass mode

- [ ] **0.5.4** Create `backend/app/domains/auth/router.py` — Auth routes
  - `router = APIRouter(prefix="/auth", tags=["auth"])`
  - `GET /login` → calls `service.login()`
  - `GET /callback` → calls `service.callback(code)`, accepts `code` query param
  - `POST /logout` → calls `service.logout()`, returns 204
  - `GET /me` → uses `Depends(get_current_user)`, returns `UserResponse`

- [ ] **0.5.5** Create `backend/scripts/seed_dev_user.py`
  - Imports engine, SessionLocal, User model
  - Creates dev user if not exists:
    - `id = UUID("00000000-0000-0000-0000-000000000001")`
    - `auth_provider = "dev"`
    - `auth_provider_id = "dev-user-001"`
    - `email = "dev@projectmemory.local"`
    - `display_name = "Dev User"`
  - Runnable as `cd backend && python -m scripts.seed_dev_user`

- [ ] **0.5.6** Register auth router in `backend/app/main.py`
  - `from app.domains.auth.router import router as auth_router`
  - `api_v1.include_router(auth_router)`

- [ ] **0.5.7** Create `backend/tests/domains/test_auth.py`
  - Test `GET /api/v1/auth/me` returns 200 with dev user fields (id, email, display_name)
  - Test `GET /api/v1/auth/callback?code=test` returns 200 with access_token
  - Test `POST /api/v1/auth/logout` returns 204
  - Tests use the `client` fixture from conftest which has auth bypass enabled

**Verify:** Run seed script → `GET /api/v1/auth/me` returns dev user. All auth tests pass.

### Sprint 0.5 Manual Verification

With Postgres running (`docker compose up -d`) and venv active:

```bash
# 1. Run migrations and seed dev user
alembic upgrade head
python -m scripts.seed_dev_user

# 2. Start server
uvicorn app.main:app --reload

# 3. Test each endpoint (in another terminal)
curl localhost:8000/api/v1/auth/me
# → {"id":"00000000-0000-0000-0000-000000000001","email":"dev@projectmemory.local","display_name":"Dev User","created_at":"..."}

curl localhost:8000/api/v1/auth/login
# → {"redirect_url":"/api/v1/auth/callback?code=dev"}

curl "localhost:8000/api/v1/auth/callback?code=dev"
# → {"access_token":"dev-token-bypass","token_type":"bearer","expires_in":3600}

curl -X POST localhost:8000/api/v1/auth/logout -w "\n%{http_code}"
# → 204

# 4. Run automated tests
pytest tests/ -v
# → 4 passed
```

---

## End-of-Phase Verification Checklist

1. `docker compose up -d` — Postgres running with pgvector
2. `cd backend && alembic upgrade head` — all 11 tables created
3. `cd backend && python -m scripts.seed_dev_user` — dev user seeded
4. `cd backend && uvicorn app.main:app --reload` — backend starts
5. `curl localhost:8000/api/v1/health` → `{"status": "ok"}`
6. `curl localhost:8000/api/v1/auth/me` → dev user JSON
7. `cd frontend && npm run dev` — frontend starts at localhost:3000
8. `cd backend && pytest` — all tests pass

---

## Commit Strategy

One commit per sprint:
1. `feat: add docker-compose infrastructure with postgres/pgvector`
2. `feat: scaffold fastapi backend with core modules`
3. `feat: define all 11 ORM models and initial alembic migration`
4. `feat: scaffold next.js frontend with shadcn/ui and shared types`
5. `feat: implement auth bypass for development mode`
