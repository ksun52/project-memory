# Phase 1: Core CRUD Domains — Detailed Sprint Plan

## Context

Phase 0 is complete. Infrastructure, ORM models, Alembic migration, frontend scaffolding, and auth bypass are all in place. Phase 1 builds the first layer of domain logic: Workspace and Memory Space CRUD on the backend, plus MSW mocking, auth UI, and workspace/memory space browsing on the frontend.

Two developers work in parallel:
- **Backend Developer** — Tracks A, B, C (Workspace → Memory Space → Integration Clients)
- **Frontend Developer** — Tracks D, E (MSW + Auth + Shared → Workspace + Memory Space UI)

### Prerequisites
- Docker Compose running with Postgres + pgvector
- `alembic upgrade head` applied
- Dev user seeded (`python -m scripts.seed_dev_user`)
- Backend: `uvicorn app.main:app --reload` starts with health check at 200
- Frontend: `npm run dev` starts, root page loads

---

## Design Decisions

> **Resolved before starting Phase 1:**

1. **Single `models.py` per domain**: ORM models, domain entities (dataclasses), and Pydantic schemas all live in one `models.py` file per domain. The app is small with only 1-2 ORM models per domain, so separate `entities.py`/`schemas.py` files would add friction without benefit. Auth already follows this pattern. BACKEND.md has been updated accordingly.

2. **Workspace.description stays NOT NULL**: The ORM column stays `nullable=False`. The API contract allows `description` to be optional on create/update — the backend service layer handles this by defaulting to `""` when the client omits it. The DB is explicit about what it stores.

3. **MemorySpace.description stays NOT NULL**: Same approach as Workspace — column stays `nullable=False`, service defaults to `""` when not provided by the client.

4. **API client needs query param support**: The frontend `apiClient` currently doesn't support query parameters (needed for pagination and filters). Track D adds this.

5. **Providers missing AuthProvider**: `providers.tsx` only wraps `QueryClientProvider`. Track D will add `AuthProvider`.

---

# Backend Developer

## Track A: Workspace Domain

**Depends on:** Phase 0 complete
**Goal:** Full CRUD for workspaces with ownership enforcement. 5 API endpoints operational.

### Tasks

#### A.1 — Workspace entities + schemas (add to models.py)
- [ ] **A.1.1** Update `backend/app/domains/workspace/models.py` — add domain entity and Pydantic DTOs alongside the existing ORM model:

  **Domain Entity (dataclass):**
  - `WorkspaceEntity` with fields: `id` (UUID), `owner_id` (UUID), `name` (str), `description` (str), `created_at` (datetime), `updated_at` (datetime)
  - `from_orm(cls, workspace: Workspace) -> WorkspaceEntity` classmethod

  **Pydantic DTOs:**
  - `WorkspaceCreate(BaseModel)` — `name: str` (required), `description: Optional[str] = None`
  - `WorkspaceUpdate(BaseModel)` — `name: Optional[str] = None`, `description: Optional[str] = None`
  - `WorkspaceResponse(BaseModel)` — `id: UUID`, `owner_id: UUID`, `name: str`, `description: str`, `created_at: datetime`, `updated_at: datetime`. Config: `from_attributes = True`
  - `WorkspaceListResponse(BaseModel)` — wraps `PaginatedResponse` pattern: `items: list[WorkspaceResponse]`, `total: int`, `page: int`, `page_size: int`

#### A.2 — Workspace service
- [ ] **A.2.1** Create `backend/app/domains/workspace/service.py` with these functions:

  **`create_workspace(db: Session, owner_id: UUID, data: WorkspaceCreate) -> WorkspaceEntity`**
  - Create ORM instance, set `owner_id`, default `description` to `""` if not provided
  - Commit, refresh, return entity

  **`list_workspaces(db: Session, owner_id: UUID, page: int = 1, page_size: int = 20) -> tuple[list[WorkspaceEntity], int]`**
  - Query workspaces WHERE `owner_id = owner_id` AND `deleted_at IS NULL`
  - Apply pagination (offset = (page - 1) * page_size, limit = page_size)
  - Return (entities, total_count)

  **`get_workspace(db: Session, workspace_id: UUID, owner_id: UUID) -> WorkspaceEntity`**
  - Query by id WHERE `deleted_at IS NULL`
  - If not found: raise `NotFoundError("Workspace not found")`
  - If `workspace.owner_id != owner_id`: raise `ForbiddenError("Not your workspace")`
  - Return entity

  **`update_workspace(db: Session, workspace_id: UUID, owner_id: UUID, data: WorkspaceUpdate) -> WorkspaceEntity`**
  - Call `get_workspace` first (ownership check)
  - Apply only non-None fields from `data` using `data.model_dump(exclude_unset=True)`
  - Description stays unchanged if not provided (column is NOT NULL, so never set it to None)
  - Commit, refresh, return entity

  **`delete_workspace(db: Session, workspace_id: UUID, owner_id: UUID) -> None`**
  - Call `get_workspace` first (ownership check)
  - Set `deleted_at = func.now()` on the workspace
  - Also soft-delete all child memory spaces (cascade)
  - Commit

#### A.3 — Workspace router
- [ ] **A.3.1** Create `backend/app/domains/workspace/router.py`:

  **`POST /workspaces`** → 201 Created
  - Depends: `current_user` (from auth service), `db` (from get_db)
  - Body: `WorkspaceCreate`
  - Calls `service.create_workspace(db, current_user.id, data)`
  - Returns `WorkspaceResponse`

  **`GET /workspaces`** → 200 OK
  - Query params: `page: int = 1`, `page_size: int = 20`
  - Calls `service.list_workspaces(db, current_user.id, page, page_size)`
  - Returns `WorkspaceListResponse`

  **`GET /workspaces/{workspace_id}`** → 200 OK
  - Calls `service.get_workspace(db, workspace_id, current_user.id)`
  - Returns `WorkspaceResponse`

  **`PATCH /workspaces/{workspace_id}`** → 200 OK
  - Body: `WorkspaceUpdate`
  - Calls `service.update_workspace(db, workspace_id, current_user.id, data)`
  - Returns `WorkspaceResponse`

  **`DELETE /workspaces/{workspace_id}`** → 204 No Content
  - Calls `service.delete_workspace(db, workspace_id, current_user.id)`
  - Returns `Response(status_code=204)`

- [ ] **A.3.2** Register workspace router in `backend/app/main.py`:
  - `from app.domains.workspace.router import router as workspace_router`
  - `api_v1.include_router(workspace_router)`

#### A.4 — Workspace tests
- [ ] **A.4.1** Create `backend/tests/domains/test_workspace.py`:

  **Test cases:**
  - `test_create_workspace` — POST /workspaces with valid body → 201, verify response fields
  - `test_create_workspace_with_description` — include optional description → 201, description matches
  - `test_create_workspace_no_description` — omit description → 201, description defaults to `""`
  - `test_create_workspace_missing_name` — omit name → 422
  - `test_list_workspaces_empty` — no workspaces → 200, items=[], total=0
  - `test_list_workspaces` — create 3, list → 200, items has 3, total=3
  - `test_list_workspaces_pagination` — create 5, request page_size=2 → 2 items, total=5
  - `test_get_workspace` — create then get by id → 200, matches
  - `test_get_workspace_not_found` — random UUID → 404
  - `test_update_workspace_name` — PATCH with name only → 200, name changed, description unchanged
  - `test_update_workspace_description` — PATCH with description → 200
  - `test_update_workspace_not_found` — random UUID → 404
  - `test_delete_workspace` — DELETE → 204, subsequent GET → 404
  - `test_delete_workspace_cascades_memory_spaces` — create workspace with memory spaces, delete workspace → memory spaces also gone from list

- [ ] **A.4.2** Run tests, verify all pass: `pytest tests/domains/test_workspace.py -v`

#### A.5 — Verify Track A
- [ ] **A.5.1** Manual verification:
  - Start server, call all 5 endpoints via curl or httpie
  - Confirm response shapes match API_CONTRACT.md
  - Confirm deleted workspaces excluded from list/get
  - Confirm ownership check returns 403 for wrong user (not testable in bypass mode with single user — just confirm the code path exists)

---

## Track B: Memory Space Domain (CRUD Only)

**Depends on:** Track A complete (needs workspace service for scoping)
**Goal:** Full CRUD for memory spaces with workspace scoping and status lifecycle. `/summarize` and `/query` return 501 for now.

### Tasks

#### B.1 — Memory Space entities + schemas (add to models.py)
- [ ] **B.1.1** Update `backend/app/domains/memory_space/models.py` — add domain entity and Pydantic DTOs alongside the existing ORM model:

  **Domain Entity (dataclass):**
  - `MemorySpaceEntity` with fields: `id` (UUID), `workspace_id` (UUID), `name` (str), `description` (str), `status` (str), `created_at` (datetime), `updated_at` (datetime)
  - `from_orm(cls, ms: MemorySpace) -> MemorySpaceEntity` classmethod

  **Pydantic DTOs:**
  - `MemorySpaceCreate(BaseModel)` — `name: str`, `description: Optional[str] = None`
  - `MemorySpaceUpdate(BaseModel)` — `name: Optional[str] = None`, `description: Optional[str] = None`, `status: Optional[str] = None` (validate status is "active" or "archived" if provided)
  - `MemorySpaceResponse(BaseModel)` — `id: UUID`, `workspace_id: UUID`, `name: str`, `description: str`, `status: str`, `created_at: datetime`, `updated_at: datetime`. Config: `from_attributes = True`
  - `MemorySpaceListResponse(BaseModel)` — `items: list[MemorySpaceResponse]`, `total: int`, `page: int`, `page_size: int`
  - `SummaryRequest(BaseModel)` — `summary_type: str` (validate: "one_pager" or "recent_updates") — used by stub endpoint
  - `QueryRequest(BaseModel)` — `question: str` — used by stub endpoint

#### B.2 — Memory Space service
- [ ] **B.2.1** Create `backend/app/domains/memory_space/service.py`:

  **`create_memory_space(db: Session, workspace_id: UUID, owner_id: UUID, data: MemorySpaceCreate) -> MemorySpaceEntity`**
  - Call `workspace_service.get_workspace(db, workspace_id, owner_id)` to verify access
  - Create MemorySpace with `status="active"`, default `description` to `""` if not provided
  - Commit, refresh, return entity

  **`list_memory_spaces(db: Session, workspace_id: UUID, owner_id: UUID, page: int = 1, page_size: int = 20, status: Optional[str] = None) -> tuple[list[MemorySpaceEntity], int]`**
  - Verify workspace access first
  - Query WHERE `workspace_id` matches AND `deleted_at IS NULL`
  - Apply optional `status` filter
  - Apply pagination
  - Return (entities, total_count)

  **`get_memory_space(db: Session, memory_space_id: UUID, owner_id: UUID) -> MemorySpaceEntity`**
  - Query by id WHERE `deleted_at IS NULL`
  - If not found: raise `NotFoundError("Memory space not found")`
  - Look up the parent workspace, verify `owner_id` matches → raise `ForbiddenError` if not
  - Return entity

  **`update_memory_space(db: Session, memory_space_id: UUID, owner_id: UUID, data: MemorySpaceUpdate) -> MemorySpaceEntity`**
  - Call `get_memory_space` first (access check)
  - Apply only non-None fields from `data` using `data.model_dump(exclude_unset=True)`
  - Description stays unchanged if not provided (column is NOT NULL, so never set it to None)
  - Validate status transitions if status is being changed
  - Commit, refresh, return entity

  **`delete_memory_space(db: Session, memory_space_id: UUID, owner_id: UUID) -> None`**
  - Call `get_memory_space` first
  - Set `deleted_at` on the memory space
  - Also soft-delete child sources, records (cascade) — note: for Phase 1, there won't be children yet, but write the cascade logic now
  - Commit

#### B.3 — Memory Space router
- [ ] **B.3.1** Create `backend/app/domains/memory_space/router.py`:

  **`POST /workspaces/{workspace_id}/memory-spaces`** → 201 Created
  - Body: `MemorySpaceCreate`
  - Calls `service.create_memory_space(db, workspace_id, current_user.id, data)`
  - Returns `MemorySpaceResponse`

  **`GET /workspaces/{workspace_id}/memory-spaces`** → 200 OK
  - Query params: `page`, `page_size`, `status` (optional filter)
  - Calls `service.list_memory_spaces(...)`
  - Returns `MemorySpaceListResponse`

  **`GET /memory-spaces/{memory_space_id}`** → 200 OK
  - Calls `service.get_memory_space(db, memory_space_id, current_user.id)`
  - Returns `MemorySpaceResponse`

  **`PATCH /memory-spaces/{memory_space_id}`** → 200 OK
  - Body: `MemorySpaceUpdate`
  - Calls `service.update_memory_space(...)`
  - Returns `MemorySpaceResponse`

  **`DELETE /memory-spaces/{memory_space_id}`** → 204 No Content
  - Calls `service.delete_memory_space(...)`
  - Returns `Response(status_code=204)`

  **`POST /memory-spaces/{memory_space_id}/summarize`** → 501
  - Body: `SummaryRequest`
  - Returns 501 with `{"error": {"code": "not_implemented", "message": "Summarization not yet available"}}`

  **`POST /memory-spaces/{memory_space_id}/query`** → 501
  - Body: `QueryRequest`
  - Returns 501 with same pattern

- [ ] **B.3.2** Register memory space router in `backend/app/main.py`:
  - `from app.domains.memory_space.router import router as memory_space_router`
  - `api_v1.include_router(memory_space_router)`

#### B.4 — Memory Space tests
- [ ] **B.4.1** Create `backend/tests/domains/test_memory_space.py`:

  **Test cases:**
  - `test_create_memory_space` — POST with valid body → 201, status="active"
  - `test_create_memory_space_no_description` — omit description → 201, description defaults to `""`
  - `test_create_memory_space_invalid_workspace` — random workspace UUID → 404
  - `test_list_memory_spaces_empty` — no spaces → 200, items=[], total=0
  - `test_list_memory_spaces` — create 3 → 200, total=3
  - `test_list_memory_spaces_filter_by_status` — create 2 active + 1 archived → filter by active returns 2
  - `test_list_memory_spaces_pagination` — create 5, page_size=2 → 2 items, total=5
  - `test_get_memory_space` — create then get → 200, fields match
  - `test_get_memory_space_not_found` — random UUID → 404
  - `test_update_memory_space_name` — PATCH name → 200, name changed
  - `test_update_memory_space_status` — PATCH status to "archived" → 200, status changed
  - `test_update_memory_space_invalid_status` — PATCH status to "invalid" → 400/422
  - `test_delete_memory_space` — DELETE → 204, subsequent GET → 404
  - `test_delete_memory_space_not_found` — random UUID → 404
  - `test_summarize_returns_501` — POST /summarize → 501
  - `test_query_returns_501` — POST /query → 501

- [ ] **B.4.2** Run tests: `pytest tests/domains/test_memory_space.py -v`

#### B.5 — Verify Track B
- [ ] **B.5.1** Manual verification:
  - Create workspace → create memory spaces within it → list → filter → update status → delete
  - Confirm deleted memory spaces excluded from list
  - Confirm workspace scoping (memory space only accessible through its workspace's owner)
  - Confirm summarize/query return 501

---

## Track C: Integration Clients

**Depends on:** Phase 0 only (parallel with A & B)
**Goal:** Stub integration clients for storage, LLM, and WorkOS. These are shells that will be filled in Phase 2 (LLM/storage) and Phase 3 (WorkOS).

### Tasks

#### C.1 — Local Storage Client
- [ ] **C.1.1** Create `backend/app/integrations/storage_client.py`:
  - `class LocalStorageClient`:
    - `__init__(self, base_path: str)` — creates directory if not exists
    - `save_file(self, file_key: str, data: bytes) -> str` — writes bytes to `{base_path}/{file_key}`, returns the file path
    - `read_file(self, file_key: str) -> bytes` — reads and returns bytes
    - `delete_file(self, file_key: str) -> None` — removes file if exists
    - `file_exists(self, file_key: str) -> bool` — checks existence
  - Module-level `storage_client = LocalStorageClient(settings.STORAGE_PATH)` singleton
  - File keys use `{memory_space_id}/{source_id}/{filename}` pattern

#### C.2 — LLM Client (stub)
- [ ] **C.2.1** Create `backend/app/integrations/llm_client.py`:
  - `class LLMClient`:
    - `__init__(self, api_key: Optional[str] = None)` — stores key, does NOT initialize OpenAI client yet
    - `async def extract(self, content: str, source_type: str) -> dict` — raises `NotImplementedError("LLM extraction not yet implemented")`
    - `async def summarize(self, records: list[dict], summary_type: str) -> dict` — raises `NotImplementedError`
    - `async def query(self, question: str, context: list[dict]) -> dict` — raises `NotImplementedError`
    - `async def generate_embeddings(self, texts: list[str]) -> list[list[float]]` — raises `NotImplementedError`
  - Module-level `llm_client = LLMClient(settings.OPENAI_API_KEY)` singleton
  - Include docstrings describing what each method will do in Phase 2

#### C.3 — WorkOS Client (stub)
- [ ] **C.3.1** Create `backend/app/integrations/workos_client.py`:
  - `class WorkOSClient`:
    - `get_authorization_url(self) -> str` — raises `NotImplementedError("WorkOS auth not yet implemented")`
    - `authenticate_with_code(self, code: str) -> dict` — raises `NotImplementedError`
    - `get_user_profile(self, access_token: str) -> dict` — raises `NotImplementedError`
  - Module-level `workos_client = WorkOSClient()` singleton

#### C.4 — Integration `__init__.py`
- [ ] **C.4.1** Create `backend/app/integrations/__init__.py` (if not exists) — empty or with convenience imports

#### C.5 — Verify Track C
- [ ] **C.5.1** Verify imports work:
  - `from app.integrations.storage_client import storage_client`
  - `from app.integrations.llm_client import llm_client`
  - `from app.integrations.workos_client import workos_client`
- [ ] **C.5.2** Test LocalStorageClient manually: write a file, read it back, delete it
- [ ] **C.5.3** Confirm LLM and WorkOS stubs raise `NotImplementedError` when called

---

## Backend — Phase 1 Milestone Verification

- [ ] All 5 workspace endpoints functional and tested
- [ ] All 7 memory space endpoints functional (5 CRUD + 2 stubs) and tested
- [ ] Integration client stubs importable and LocalStorageClient functional
- [ ] All tests pass: `pytest tests/ -v`
- [ ] Response shapes match `docs/API_CONTRACT.md` exactly
- [ ] Soft delete working correctly with cascade
- [ ] Pagination working correctly (1-indexed, default 20, max 100)

---

# Frontend Developer

## Track D: MSW + Auth + Shared Layer

**Depends on:** Phase 0.4 complete (frontend scaffold exists)
**Goal:** Mock Service Worker intercepting API calls, auth domain working, shared UI components in place, dashboard layout shell functional.

### Tasks

#### D.1 — MSW Setup
- [ ] **D.1.1** Install MSW:
  - `npm install msw --save-dev`
  - `npx msw init public/ --save` (generates service worker file in `public/`)

- [ ] **D.1.2** Create `frontend/src/mocks/browser.ts`:
  - `import { setupWorker } from 'msw/browser'`
  - `import { handlers } from './handlers'`
  - `export const worker = setupWorker(...handlers)`

- [ ] **D.1.3** Create `frontend/src/mocks/handlers/index.ts`:
  - Barrel file that re-exports and combines all domain handlers
  - `export const handlers = [...authHandlers, ...workspaceHandlers, ...memorySpaceHandlers]`

- [ ] **D.1.4** Create `frontend/src/mocks/handlers/auth.ts`:
  - Mock data: dev user object matching `UserResponse` shape
  - `GET /api/v1/auth/me` → returns dev user (200)
  - `GET /api/v1/auth/login` → returns `{ redirect_url: "/auth/callback?code=dev" }`
  - `GET /api/v1/auth/callback` → returns `TokenResponse` with dev token
  - `POST /api/v1/auth/logout` → returns 204

- [ ] **D.1.5** Create `frontend/src/mocks/handlers/workspace.ts`:
  - In-memory array of mock workspaces (seed with 2-3 examples)
  - `POST /api/v1/workspaces` → create and return (201)
  - `GET /api/v1/workspaces` → return paginated list (200)
  - `GET /api/v1/workspaces/:id` → return single workspace (200) or 404
  - `PATCH /api/v1/workspaces/:id` → update and return (200)
  - `DELETE /api/v1/workspaces/:id` → soft-delete and return 204

- [ ] **D.1.6** Create `frontend/src/mocks/handlers/memory-space.ts`:
  - In-memory array of mock memory spaces (seed with 3-4 examples across workspaces)
  - `POST /api/v1/workspaces/:wId/memory-spaces` → create (201)
  - `GET /api/v1/workspaces/:wId/memory-spaces` → list with status filter (200)
  - `GET /api/v1/memory-spaces/:id` → single (200) or 404
  - `PATCH /api/v1/memory-spaces/:id` → update (200)
  - `DELETE /api/v1/memory-spaces/:id` → 204
  - `POST /api/v1/memory-spaces/:id/summarize` → 501
  - `POST /api/v1/memory-spaces/:id/query` → 501

- [ ] **D.1.7** Create `frontend/src/mocks/seed-data.ts`:
  - Centralized mock data: users, workspaces, memory spaces with realistic names and UUIDs
  - Export typed arrays that handlers reference

- [ ] **D.1.8** Wire MSW into the app (dev only):
  - Create `frontend/src/mocks/init.ts` — conditionally starts MSW worker in development
  - Integrate into root layout or a client component that runs on mount
  - Use environment variable `NEXT_PUBLIC_ENABLE_MSW=true` to toggle
  - Add to `.env.local`

#### D.2 — Auth Domain Types, API, Hooks
- [ ] **D.2.1** Create `frontend/src/domains/auth/types.ts`:
  - `User` interface: `id: string`, `email: string`, `display_name: string`, `created_at: string`
  - `TokenResponse` interface: `access_token: string`, `token_type: string`, `expires_in: number`
  - `AuthState` type: `"loading" | "authenticated" | "unauthenticated"`

- [ ] **D.2.2** Create `frontend/src/domains/auth/api.ts`:
  - `getMe(): Promise<User>` — `apiClient.get('/auth/me')`
  - `login(): Promise<{ redirect_url: string }>` — `apiClient.get('/auth/login')`
  - `callback(code: string): Promise<TokenResponse>` — `apiClient.get('/auth/callback?code=' + code)`
  - `logout(): Promise<void>` — `apiClient.post('/auth/logout')`

- [ ] **D.2.3** Create `frontend/src/domains/auth/hooks.ts`:
  - `useCurrentUser()` — `useQuery` wrapping `getMe()`, query key: `['auth', 'me']`
  - `useLogout()` — `useMutation` wrapping `logout()`, on success: clear token + redirect to `/login`

#### D.3 — Auth Provider & Components
- [ ] **D.3.1** Create `frontend/src/domains/auth/auth-provider.tsx`:
  - React Context providing: `user: User | null`, `token: string | null`, `authState: AuthState`, `setToken: (token: string) => void`, `clearAuth: () => void`
  - On mount: check for stored token, call `getMe()` to validate
  - Wire into `setTokenGetter` from API client so requests include the token
  - For dev/MSW mode: auto-set a dev token on mount

- [ ] **D.3.2** Create `frontend/src/domains/auth/components/login-form.tsx`:
  - "Sign in" button
  - On click: call `login()` API → redirect to the returned URL
  - In bypass mode: redirect directly to callback with `code=dev`
  - Minimal styling with shadcn Button component

- [ ] **D.3.3** Create `frontend/src/domains/auth/components/auth-guard.tsx`:
  - Wraps children; checks auth state from context
  - If `loading`: show loading skeleton
  - If `unauthenticated`: redirect to `/login`
  - If `authenticated`: render children

- [ ] **D.3.4** Update `frontend/src/shared/components/providers.tsx`:
  - Wrap children in `AuthProvider` inside `QueryClientProvider`
  - `<QueryClientProvider><AuthProvider>{children}</AuthProvider></QueryClientProvider>`

#### D.4 — API Client Enhancement
- [ ] **D.4.1** Update `frontend/src/shared/api/client.ts`:
  - Add query parameter support: `get<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T>`
  - Build URL with query string, filtering out undefined values
  - Used by list hooks for pagination and filtering

#### D.5 — Shared Components
- [ ] **D.5.1** Create `frontend/src/shared/components/app-sidebar.tsx`:
  - Uses shadcn Sheet/sidebar pattern
  - Shows app name/logo at top
  - Navigation links: Workspaces (main nav item)
  - Current user display at bottom (email or display name)
  - Logout button
  - Responsive: drawer on mobile, fixed sidebar on desktop

- [ ] **D.5.2** Create `frontend/src/shared/components/breadcrumbs.tsx`:
  - Props: `items: Array<{ label: string, href?: string }>`
  - Renders breadcrumb trail with links (all but last are clickable)
  - Uses shadcn styling

- [ ] **D.5.3** Create `frontend/src/shared/components/page-header.tsx`:
  - Props: `title: string`, `description?: string`, `actions?: ReactNode`
  - Renders page title + optional description + right-aligned action buttons
  - Consistent spacing/typography across all pages

- [ ] **D.5.4** Create `frontend/src/shared/components/empty-state.tsx`:
  - Props: `icon?: ReactNode`, `title: string`, `description: string`, `action?: ReactNode`
  - Centered content for empty lists (no workspaces yet, no memory spaces, etc.)
  - Used across multiple domains

- [ ] **D.5.5** Create `frontend/src/shared/components/loading-skeleton.tsx`:
  - Reusable loading skeletons: `CardSkeleton`, `ListSkeleton`, `PageSkeleton`
  - Uses shadcn Skeleton component
  - Configurable count for list skeletons

- [ ] **D.5.6** Create `frontend/src/shared/components/error-boundary.tsx`:
  - React error boundary wrapping dashboard routes
  - Shows user-friendly error message with retry option
  - Logs error details to console

#### D.6 — Shared Hooks
- [ ] **D.6.1** Create `frontend/src/shared/hooks/use-pagination.ts`:
  - `usePagination(initialPage?: number, initialPageSize?: number)`
  - Returns: `{ page, pageSize, setPage, setPageSize, nextPage, prevPage, resetPage }`
  - Manages pagination state for list views

#### D.7 — Dashboard Layout
- [ ] **D.7.1** Create `frontend/src/app/(auth)/login/page.tsx`:
  - Centered login form
  - Minimal layout (no sidebar)

- [ ] **D.7.2** Create `frontend/src/app/(auth)/auth/callback/page.tsx`:
  - Client component
  - Reads `code` from URL params
  - Calls `callback(code)` → stores token in AuthProvider → redirects to `/workspaces`
  - Shows loading spinner during exchange

- [ ] **D.7.3** Create `frontend/src/app/(dashboard)/layout.tsx`:
  - Wraps all authenticated pages
  - Includes `AuthGuard`, `AppSidebar`
  - Provides the app shell (sidebar + main content area)

- [ ] **D.7.4** Update `frontend/src/app/page.tsx`:
  - Redirect to `/workspaces` (or `/login` if unauthenticated)

#### D.8 — Verify Track D
- [ ] **D.8.1** MSW is intercepting requests (check browser Network tab — requests go to MSW)
- [ ] **D.8.2** Login flow works: `/login` → click sign in → callback → redirected to dashboard
- [ ] **D.8.3** Auth guard works: unauthenticated access to `/workspaces` redirects to `/login`
- [ ] **D.8.4** Dashboard layout renders: sidebar visible, user info shown, logout works
- [ ] **D.8.5** Shared components render correctly in isolation

---

## Track E: Workspace + Memory Space UI

**Depends on:** Track D complete
**Goal:** Workspace list/CRUD and memory space list/CRUD pages fully functional against MSW mocks.

### Tasks

#### E.1 — Workspace Domain (Frontend)
- [ ] **E.1.1** Create `frontend/src/domains/workspace/types.ts`:
  - `Workspace` interface matching API contract: `id`, `owner_id`, `name`, `description`, `created_at`, `updated_at`
  - `WorkspaceCreate`: `name: string`, `description?: string`
  - `WorkspaceUpdate`: `name?: string`, `description?: string`

- [ ] **E.1.2** Create `frontend/src/domains/workspace/api.ts`:
  - `listWorkspaces(params?: PaginationParams): Promise<PaginatedResponse<Workspace>>`
  - `getWorkspace(id: string): Promise<Workspace>`
  - `createWorkspace(data: WorkspaceCreate): Promise<Workspace>`
  - `updateWorkspace(id: string, data: WorkspaceUpdate): Promise<Workspace>`
  - `deleteWorkspace(id: string): Promise<void>`

- [ ] **E.1.3** Create `frontend/src/domains/workspace/hooks.ts`:
  - `useWorkspaces(params?)` — `useQuery` with key `['workspaces', params]`
  - `useWorkspace(id)` — `useQuery` with key `['workspaces', id]`
  - `useCreateWorkspace()` — `useMutation`, invalidates `['workspaces']` on success, shows success toast
  - `useUpdateWorkspace()` — `useMutation`, invalidates `['workspaces']` and `['workspaces', id]`
  - `useDeleteWorkspace()` — `useMutation`, invalidates `['workspaces']`, shows success toast

- [ ] **E.1.4** Create `frontend/src/domains/workspace/components/workspace-card.tsx`:
  - Displays: workspace name, description (truncated), created date
  - Click navigates to `/workspaces/[id]`
  - Dropdown menu (three dots) with: Edit, Delete options
  - Uses shadcn Card component

- [ ] **E.1.5** Create `frontend/src/domains/workspace/components/workspace-create-dialog.tsx`:
  - Modal dialog with form: name (required), description (optional)
  - Uses React Hook Form + Zod validation
  - Calls `useCreateWorkspace()` on submit
  - Shows loading state on submit button
  - Closes dialog and shows toast on success

- [ ] **E.1.6** Create `frontend/src/domains/workspace/components/workspace-list.tsx`:
  - Grid of `WorkspaceCard` components
  - "Create Workspace" button in page header (opens `WorkspaceCreateDialog`)
  - Loading skeleton while fetching
  - Empty state when no workspaces exist ("Create your first workspace to get started")
  - Pagination controls if total > page_size

#### E.2 — Workspace Page
- [ ] **E.2.1** Create `frontend/src/app/(dashboard)/workspaces/page.tsx`:
  - Page header with title "Workspaces" and create button
  - Renders `WorkspaceList` component
  - Breadcrumbs: `Workspaces`

#### E.3 — Memory Space Domain (Frontend)
- [ ] **E.3.1** Create `frontend/src/domains/memory-space/types.ts`:
  - `MemorySpace` interface: `id`, `workspace_id`, `name`, `description`, `status`, `created_at`, `updated_at`
  - `MemorySpaceCreate`: `name: string`, `description?: string`
  - `MemorySpaceUpdate`: `name?: string`, `description?: string`, `status?: "active" | "archived"`

- [ ] **E.3.2** Create `frontend/src/domains/memory-space/api.ts`:
  - `listMemorySpaces(workspaceId: string, params?): Promise<PaginatedResponse<MemorySpace>>`
  - `getMemorySpace(id: string): Promise<MemorySpace>`
  - `createMemorySpace(workspaceId: string, data: MemorySpaceCreate): Promise<MemorySpace>`
  - `updateMemorySpace(id: string, data: MemorySpaceUpdate): Promise<MemorySpace>`
  - `deleteMemorySpace(id: string): Promise<void>`

- [ ] **E.3.3** Create `frontend/src/domains/memory-space/hooks.ts`:
  - `useMemorySpaces(workspaceId, params?)` — `useQuery` with key `['memory-spaces', workspaceId, params]`
  - `useMemorySpace(id)` — `useQuery` with key `['memory-spaces', id]`
  - `useCreateMemorySpace()` — `useMutation`, invalidates `['memory-spaces']`
  - `useUpdateMemorySpace()` — `useMutation`, invalidates list + detail
  - `useDeleteMemorySpace()` — `useMutation`, invalidates list

- [ ] **E.3.4** Create `frontend/src/domains/memory-space/components/memory-space-card.tsx`:
  - Displays: name, description (truncated), status badge (active=green, archived=gray)
  - Click navigates to `/workspaces/[wId]/memory-spaces/[msId]` (detail page — stubbed for Phase 1)
  - Dropdown with Edit, Archive/Activate, Delete options
  - Uses shadcn Card + Badge components

- [ ] **E.3.5** Create `frontend/src/domains/memory-space/components/memory-space-create-dialog.tsx`:
  - Modal form: name (required), description (optional)
  - React Hook Form + Zod
  - Calls `useCreateMemorySpace()` with workspace ID from route
  - Toast on success, close dialog

- [ ] **E.3.6** Create `frontend/src/domains/memory-space/components/memory-space-list.tsx`:
  - Grid of `MemorySpaceCard` components
  - "Create Memory Space" button
  - Status filter tabs or dropdown (All, Active, Archived)
  - Loading skeleton, empty state
  - Pagination controls

#### E.4 — Memory Space List Page (within workspace)
- [ ] **E.4.1** Create `frontend/src/app/(dashboard)/workspaces/[workspaceId]/page.tsx`:
  - Fetches workspace detail to show name in header
  - Page header: workspace name + "Create Memory Space" button
  - Renders `MemorySpaceList` with `workspaceId` from params
  - Breadcrumbs: `Workspaces > {Workspace Name}`

#### E.5 — Memory Space Detail Placeholder
- [ ] **E.5.1** Create `frontend/src/app/(dashboard)/workspaces/[workspaceId]/memory-spaces/[memorySpaceId]/page.tsx`:
  - Fetches memory space detail
  - Renders: name, description, status badge
  - Placeholder content: "Sources, Records, and Summary tabs coming in Phase 2"
  - Breadcrumbs: `Workspaces > {Workspace Name} > {Memory Space Name}`
  - This is a stub that will become the full tabbed detail page in Phase 2

#### E.6 — Delete Confirmation
- [ ] **E.6.1** Create `frontend/src/shared/components/confirm-dialog.tsx`:
  - Reusable confirmation dialog: title, description, confirm button (destructive variant), cancel button
  - Used by workspace and memory space delete actions
  - Uses shadcn AlertDialog

#### E.7 — Verify Track E
- [ ] **E.7.1** Navigation flow works: Login → Workspace list → click workspace → Memory space list → click memory space → detail stub
- [ ] **E.7.2** Workspace CRUD: create, view in list, edit (via dropdown), delete (with confirmation)
- [ ] **E.7.3** Memory Space CRUD: create, view in list, edit, archive/activate, delete
- [ ] **E.7.4** Status filter works on memory space list
- [ ] **E.7.5** Pagination works when mock data exceeds page_size
- [ ] **E.7.6** Empty states display correctly
- [ ] **E.7.7** Loading skeletons show during data fetch
- [ ] **E.7.8** Toast notifications show for create/update/delete actions
- [ ] **E.7.9** Breadcrumbs update correctly at each level
- [ ] **E.7.10** Responsive layout: sidebar collapses on mobile, cards stack properly

---

## Frontend — Phase 1 Milestone Verification

- [ ] MSW intercepts all API calls (no real backend needed)
- [ ] Login → workspace list → memory space list → memory space detail navigation works
- [ ] Workspace CRUD fully functional against mocks
- [ ] Memory Space CRUD fully functional against mocks
- [ ] Auth guard protects dashboard routes
- [ ] Sidebar navigation, breadcrumbs, page headers consistent
- [ ] Loading, error, and empty states all render correctly
- [ ] Responsive on mobile and desktop

---

## Integration Readiness (End of Phase 1)

At the end of Phase 1, both sides are ready but not yet connected:

| Concern | Backend | Frontend |
|---------|---------|----------|
| Workspace CRUD | Real endpoints on Postgres | Mock handlers in MSW |
| Memory Space CRUD | Real endpoints on Postgres | Mock handlers in MSW |
| Auth | Bypass mode (dev token) | AuthProvider with dev token |
| Data shapes | Pydantic schemas match API contract | TypeScript types match API contract |

**To connect (Phase 2+):** Turn off MSW, point frontend `NEXT_PUBLIC_API_URL` at backend, ensure CORS allows frontend origin. All flows should work because both sides developed against the same API contract.
