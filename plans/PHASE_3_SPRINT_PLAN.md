# Phase 3 Sprint Plan: AI Features + Auth + Integration

## Overview

Phase 3 delivers the remaining AI-powered features (summarization, query/RAG), real authentication (WorkOS), and full frontend-backend integration. The AI service layer is already implemented — this phase wires it into HTTP endpoints and builds the UI.

### Key Context
- AI service (`ai/service.py`) already implements `summarize_memory_space()` and `query_memory_space()` — fully functional
- Two router endpoints (`/summarize`, `/query`) currently return 501 stubs
- Frontend Summary tab is a placeholder ("Coming in Phase 3")
- Auth is dev-bypass only; WorkOS client is a stub
- Frontend runs against MSW mocks; needs to be pointed at real backend
- **Citation schema decided:** canonical shape is `{record_id, source_id, chunk_id, excerpt}` — backend `Citation` dataclass and API_CONTRACT.md both need updating
- Summary endpoint returns cached summary by default; only regenerates on explicit user action
- Token persisted to localStorage for session survival across refreshes
- Query is its own tab (separate from Summary)
- Summary editing deferred to post-Phase 3

---

## Track J: Summarize + Query Backend Endpoints

**Depends on:** Phase 2 backend (complete)

### J.1 — Citation Schema Alignment + Response DTOs

- [ ] Update backend `Citation` dataclass in `ai/models.py` to use fields: `record_id` (Optional[UUID]), `source_id` (Optional[UUID]), `chunk_id` (Optional[UUID]), `excerpt` (str) — add `source_id` field so frontend can link to the source detail page
- [ ] Update `ai/service.py` `query_memory_space()` to populate `source_id` on citations (look up `source_id` from `SourceChunk` when `chunk_id` is present, or from `MemoryRecord` → `RecordSourceLink` when `record_id` is present)
- [ ] Update `ai/prompts/query.py` to instruct LLM to return `record_id` and `chunk_id` (not `source_id` — that's derived server-side)
- [ ] Add `SummaryResponse` Pydantic schema to `memory_space/models.py` with fields: `id`, `memory_space_id`, `summary_type`, `title`, `content`, `is_edited`, `edited_content`, `record_ids_used`, `generated_at`, `created_at`, `updated_at`
- [ ] Add `CitationResponse` Pydantic schema to `memory_space/models.py` with fields: `record_id` (Optional[UUID]), `source_id` (Optional[UUID]), `chunk_id` (Optional[UUID]), `excerpt` (str)
- [ ] Add `QueryResponse` Pydantic schema to `memory_space/models.py` with fields: `answer` (str), `citations` (list[CitationResponse])
- [ ] Update API_CONTRACT.md `/query` response to use canonical citation shape: `{record_id, source_id, chunk_id, excerpt}` — remove old `content`/`record_type` fields from contract
- [ ] Update AI_LAYER.md `Citation` definition to match: `{record_id, source_id, chunk_id, excerpt}`

### J.2 — Memory Space Service: Summarize (with caching)

- [ ] Add `get_cached_summary(db, memory_space_id, summary_type) -> Optional[SummaryResponse]` to `memory_space/service.py` — query `generated_summaries` for most recent row matching `memory_space_id` + `summary_type` where `deleted_at IS NULL`
- [ ] Add `summarize_memory_space(db, memory_space_id, owner_id, summary_type, regenerate: bool)` to `memory_space/service.py`
- [ ] Verify ownership via `_get_memory_space_orm()`
- [ ] If `regenerate=False`: check cache via `get_cached_summary()`, return cached summary if one exists
- [ ] If `regenerate=True` or no cache: call `ai_service.summarize_memory_space(db, memory_space_id, summary_type)`
- [ ] Convert `GeneratedSummary` ORM to `SummaryResponse` DTO before returning (never return ORM objects)
- [ ] Handle case where memory space has zero active records — return meaningful error message instead of calling LLM
- [ ] Add `regenerate` boolean field to `SummaryRequest` in `memory_space/models.py` (default `False`)

### J.3 — Memory Space Service: Query

- [ ] Add `query_memory_space(db, memory_space_id, owner_id, question)` to `memory_space/service.py`
- [ ] Verify ownership via `_get_memory_space_orm()`
- [ ] Call `ai_service.query_memory_space(db, memory_space_id, question)`
- [ ] Map `QueryResult` domain entity to `QueryResponse` DTO (citations already enriched with `source_id` in J.1)
- [ ] Handle case where memory space has zero records/embeddings — return helpful "no context available" answer

### J.4 — Router: Replace 501 Stubs

- [ ] Replace `/memory-spaces/{memory_space_id}/summarize` stub with real handler: inject `db` dependency, call `service.summarize_memory_space()`, return `SummaryResponse`
- [ ] Replace `/memory-spaces/{memory_space_id}/query` stub with real handler: inject `db` dependency, call `service.query_memory_space()`, return `QueryResponse`
- [ ] Add error handling for AI service failures (LLM timeout, empty results) — return 502 with descriptive error

### J.5 — Doc Updates

- [ ] Update AI_LAYER.md §4 to note: no `time_window` filtering for MVP — both `one_pager` and `recent_updates` summarize all active records, ordered by importance/recency
- [ ] Update AI_LAYER.md §4 Key Decisions to document caching behavior: return cached summary by default, regenerate only on explicit user request
- [ ] Update API_CONTRACT.md `/summarize` request to include `regenerate` (bool, optional, default false)

### J.6 — Tests

- [ ] Test `/summarize` endpoint returns valid `SummaryResponse` with mocked AI service
- [ ] Test `/summarize` returns cached summary on second call without `regenerate=true`
- [ ] Test `/summarize` with `regenerate=true` calls AI service even when cache exists
- [ ] Test `/summarize` with empty memory space returns appropriate error
- [ ] Test `/query` endpoint returns valid `QueryResponse` with citations (including `source_id`) using mocked AI service
- [ ] Test `/query` with empty memory space returns "no context" response
- [ ] Test ownership enforcement on both endpoints (403 for wrong user)
- [ ] Integration test: create source → wait for extraction → call `/summarize` → verify summary references extracted records
- [ ] Integration test: create source → wait for extraction → call `/query` → verify answer and citations with `source_id` populated

---

## Track K: Real Auth (WorkOS)

**Depends on:** Phase 0 auth bypass (parallel with Track J)

### K.0 — Human Tasks (must be done manually before K.2)

- [ ] Create a WorkOS account at https://workos.com
- [ ] Create a new WorkOS project/environment for Project Memory
- [ ] Configure an authentication method in WorkOS dashboard (e.g., Email + Password, Google OAuth, or SSO)
- [ ] Set the redirect URI in WorkOS dashboard to `http://localhost:8000/api/v1/auth/callback`
- [ ] Copy the API key and Client ID from the WorkOS dashboard
- [ ] Add `WORKOS_API_KEY` and `WORKOS_CLIENT_ID` values to your local `.env` file

### K.1 — Configuration

- [ ] Add `WORKOS_API_KEY` to `Settings` in `core/config.py` (Optional[str], default None)
- [ ] Add `WORKOS_CLIENT_ID` to `Settings` in `core/config.py` (Optional[str], default None)
- [ ] Add `WORKOS_REDIRECT_URI` to `Settings` in `core/config.py` (default `http://localhost:8000/api/v1/auth/callback`)
- [ ] Add these env vars to `.env.example` with placeholder values and comments

### K.2 — WorkOS Client Implementation

- [ ] Install `workos` Python SDK — add to `requirements.txt`
- [ ] Implement `WorkOSClient.get_authorization_url()` in `workos_client.py` — generate authorization URL using WorkOS SDK with `client_id` and `redirect_uri`
- [ ] Implement `WorkOSClient.authenticate_with_code(code)` — exchange authorization code for user profile via WorkOS SDK, return dict with `{id, email, first_name, last_name}`
- [ ] Implement `WorkOSClient.get_user_profile(access_token)` — retrieve user profile from WorkOS using access token
- [ ] Initialize `workos_client` singleton with settings values (lazy init, skip if keys not set)

### K.3 — JWT Token Management

- [ ] Add `JWT_ALGORITHM` constant (HS256) and `JWT_EXPIRATION_HOURS` (default 24) to `core/config.py`
- [ ] Create `create_access_token(user_id: UUID) -> str` function in `auth/service.py` — encode user_id + expiration into JWT using `python-jose` with `SECRET_KEY`
- [ ] Create `decode_access_token(token: str) -> UUID` function in `auth/service.py` — decode and validate JWT, return user_id; raise `ForbiddenError` on invalid/expired token
- [ ] Add `Authorization: Bearer <token>` header extraction to `get_current_user()` — parse token from request header when `AUTH_BYPASS=false` (keep using dependency injection pattern, not middleware)

### K.4 — Auth Service: Real Login Flow

- [ ] Implement real `login()` — call `workos_client.get_authorization_url()`, return `{"redirect_url": url}` (JSON response — frontend navigates via `window.location`)
- [ ] Implement real `callback(code)` — call `workos_client.authenticate_with_code(code)`, get-or-create User in DB (match on `auth_provider='workos'` + `auth_provider_id`), create JWT, redirect to frontend callback URL with token as query param (e.g., `http://localhost:3000/auth/callback?token=...`)
- [ ] Implement real `get_current_user(db, token)` — decode JWT, query User by id, return `UserEntity`; fall back to dev user when `AUTH_BYPASS=true`
- [ ] Implement real `logout()` — MVP: client-side only (discard token from localStorage); no server-side token invalidation
- [ ] Keep `AUTH_BYPASS=true` as default so dev mode continues working without WorkOS keys

### K.5 — Auth Router Updates

- [ ] Update `GET /auth/login` to return JSON `{"redirect_url": url}` pointing to WorkOS authorization URL
- [ ] Update `GET /auth/callback` to handle the WorkOS redirect with `code` query param, issue JWT, return HTTP 302 redirect to frontend with token in query param
- [ ] Ensure `POST /auth/logout` works in both bypass and real mode
- [ ] Ensure `GET /auth/me` validates JWT from `Authorization` header and returns user profile in real mode

### K.6 — Frontend: Token Persistence (localStorage)

- [ ] Update `AuthProvider` to initialize `token` state from `localStorage.getItem("auth_token")` on mount
- [ ] Update `setToken()` to persist to `localStorage.setItem("auth_token", token)` alongside React state
- [ ] Update `clearAuth()` to call `localStorage.removeItem("auth_token")`
- [ ] Update the frontend `/auth/callback` page to read token from URL query params (for real WorkOS flow) and call `setToken()`
- [ ] Remove the MSW-only auto-token logic (`if NEXT_PUBLIC_ENABLE_MSW`) — replace with localStorage check

### K.7 — Tests

- [ ] Test `create_access_token()` produces valid JWT with correct claims
- [ ] Test `decode_access_token()` rejects expired tokens
- [ ] Test `decode_access_token()` rejects tampered tokens
- [ ] Test `callback()` with mocked WorkOS client — creates new user on first login
- [ ] Test `callback()` with mocked WorkOS client — returns existing user on subsequent login
- [ ] Test `get_current_user()` resolves user from JWT when `AUTH_BYPASS=false`
- [ ] Test `get_current_user()` still returns dev user when `AUTH_BYPASS=true`

---

## Track L: Summary + Query Frontend UI

**Depends on:** Frontend Track I (Phase 2)

### L.0 — Dependencies

- [ ] Install `react-markdown` — add to frontend `package.json`

### L.1 — Types

- [ ] Add `GeneratedSummary` interface to `memory-space/types.ts` with fields: `id`, `memory_space_id`, `summary_type`, `title`, `content`, `is_edited`, `edited_content`, `record_ids_used`, `generated_at`, `created_at`, `updated_at`
- [ ] Add `SummaryRequest` interface: `{ summary_type: "one_pager" | "recent_updates", regenerate?: boolean }`
- [ ] Add `Citation` interface: `{ record_id: string | null, source_id: string | null, chunk_id: string | null, excerpt: string }`
- [ ] Add `QueryResponse` interface: `{ answer: string, citations: Citation[] }`
- [ ] Add `QueryRequest` interface: `{ question: string }`

### L.2 — API Functions

- [ ] Add `summarizeMemorySpace(id: string, data: SummaryRequest): Promise<GeneratedSummary>` to `memory-space/api.ts` — POST to `/memory-spaces/${id}/summarize`
- [ ] Add `queryMemorySpace(id: string, data: QueryRequest): Promise<QueryResponse>` to `memory-space/api.ts` — POST to `/memory-spaces/${id}/query`

### L.3 — Hooks

- [ ] Add `useSummarize()` mutation hook to `memory-space/hooks.ts` — calls `summarizeMemorySpace`, shows toast on success/error
- [ ] Add `useQuery()` mutation hook to `memory-space/hooks.ts` (name carefully to avoid clash with react-query's `useQuery`) — e.g. `useMemorySpaceQuery()` — calls `queryMemorySpace`

### L.4 — Summary Tab Components

- [ ] Create `SummaryPanel` component in `domains/memory-space/components/summary-panel.tsx` — container for the full summary experience
- [ ] Add summary type selector (dropdown or segmented control) with options "One-Pager" and "Recent Updates"
- [ ] On tab load, call `useSummarize()` with `regenerate=false` to fetch cached summary (if one exists)
- [ ] Add "Regenerate" button that calls `useSummarize()` with `regenerate=true` — disabled while loading
- [ ] Add loading state — skeleton or spinner while LLM generates summary
- [ ] Add `SummaryDisplay` component — renders `title` as heading and `content` as markdown via `react-markdown`
- [ ] Show metadata below summary: `generated_at` timestamp, count of records used
- [ ] Add empty state when no summary has been generated yet — prompt user to generate one
- [ ] Add error state — show error message if summarization fails (e.g., no records yet)

### L.5 — Query Tab Components

- [ ] Create `QueryPanel` component in `domains/memory-space/components/query-panel.tsx`
- [ ] Add text input for natural language question with submit button (Enter key submits)
- [ ] Add loading state while query is processing
- [ ] Create `QueryResultDisplay` component — renders `answer` as markdown via `react-markdown`
- [ ] Create `CitationList` component — renders each citation as a compact card showing `excerpt`
- [ ] Make citation cards link to the source detail page using `source_id` (if present)
- [ ] Add empty state when no query has been made yet — prompt user to ask a question
- [ ] Add error state for failed queries
- [ ] Keep scrollable history of Q&A pairs within the session (in React state — not persisted past hard refresh)

### L.6 — Wire into Memory Space Detail Page

- [ ] Replace "Coming in Phase 3" placeholder in Summary tab with `SummaryPanel` component
- [ ] Add new "Ask" tab with `Brain` icon — renders `QueryPanel` component
- [ ] Update `VALID_TABS` to `["sources", "records", "summary", "ask"]`
- [ ] Ensure tab state persists in URL query params

### L.7 — MSW Handlers

- [ ] Add MSW handler for `POST /memory-spaces/:id/summarize` in `mocks/handlers/memory-space.ts` — return mock `GeneratedSummary` with sample markdown content
- [ ] Add MSW handler for `POST /memory-spaces/:id/query` in `mocks/handlers/memory-space.ts` — return mock `QueryResponse` with sample answer and citations
- [ ] Test Summary tab renders correctly with mock data
- [ ] Test Query panel renders correctly with mock data

---

## Track M: Frontend-Backend Integration

**Depends on:** Tracks J + L complete

### M.1 — Connect Frontend to Real Backend

- [ ] Add environment variable `NEXT_PUBLIC_API_URL` pointing to `http://localhost:8000/api/v1`
- [ ] Ensure `shared/api/client.ts` uses `NEXT_PUBLIC_API_URL` as base URL (verify it's not hardcoded to MSW)
- [ ] Disable MSW when `NEXT_PUBLIC_ENABLE_MSW` is `false` or unset
- [ ] Update auth flow for dev mode: frontend should call real `/auth/callback?code=dev` to get token, store it, and use for subsequent requests

### M.2 — End-to-End Flow Testing

- [ ] Test: Login (dev bypass) → navigate to workspaces → see workspace list
- [ ] Test: Create workspace → create memory space → navigate to detail page
- [ ] Test: Upload note source → see processing status update → see extracted records appear
- [ ] Test: Upload document (PDF/DOCX) → verify parsing + extraction works
- [ ] Test: Browse Records tab → filter by type → filter by importance
- [ ] Test: Create manual record → verify it appears in list
- [ ] Test: Edit record → verify update persists
- [ ] Test: Delete record → verify soft delete
- [ ] Test: Generate one-pager summary → verify markdown renders correctly
- [ ] Test: Generate recent-updates summary → verify it focuses on recent records
- [ ] Test: Ask a natural language question → verify answer with citations
- [ ] Test: Click citation → navigates to source record
- [ ] Test: Delete source → verify cascade (records, chunks, embeddings cleaned up)
- [ ] Test: Archive memory space → verify status change

### M.3 — Contract Mismatch Fixes

- [ ] Compare every frontend type definition against actual backend response shapes
- [ ] Fix any field naming mismatches (e.g., `snake_case` vs `camelCase`)
- [ ] Fix any missing or extra fields in frontend types
- [ ] Verify pagination response shape matches (`items`, `total`, `page`, `page_size`)
- [ ] Verify error response shape matches (`{ error: { code, message } }`)

### M.4 — Polish & Edge Cases

- [ ] Handle long-running summarization gracefully (loading indicator, disable Regenerate button during generation)
- [ ] Handle query timeout — show retry option
- [ ] Summary and query work with whatever records exist (no blocking on extraction status) — but show a note if sources are still processing ("Some sources are still being processed — results may be incomplete")
- [ ] Verify CORS configuration allows frontend origin
- [ ] Verify API client properly sends auth token on all requests (reads from localStorage)

---

## Dependency Graph

```
Track J (Summarize/Query BE)  ─────────────────┐
                                                ├──→ Track M (Integration)
Track L (Summary/Query FE)    ─────────────────┤
                                                │
Track K (Real Auth / WorkOS)  ── parallel ──────┘
```

- J and K can run in parallel (no dependencies on each other)
- L can start immediately (builds against MSW mocks)
- M requires J + L complete; K can be integrated during or after M

## Suggested Execution Order (Solo Developer)

1. **Track J** first — small scope, unblocks integration testing
2. **Track L** next — build UI against MSW, verify independently
3. **Track M** — connect frontend to backend, fix mismatches
4. **Track K** — real auth last (dev bypass works for all testing)

---

## Resolved Decisions

Decisions made for ambiguities found in the docs. Tasks above already reflect these.

| # | Topic | Decision |
|---|-------|----------|
| 1 | Citation schema | Canonical shape: `{record_id, source_id, chunk_id, excerpt}`. Update backend `Citation` dataclass, API_CONTRACT.md, and AI_LAYER.md. |
| 2 | `source_id` vs `chunk_id` | Expose both. `source_id` lets frontend link to source page; `chunk_id` identifies the specific excerpt. |
| 3 | Summary caching | Check cache first. Only user-initiated regeneration (`regenerate=true`) refreshes the cache. |
| 4 | Summarize default behavior | Return most recent cached summary. "Regenerate" button triggers fresh LLM call. |
| 5 | ORM vs DTO return | Never return ORM objects. Memory space service converts `GeneratedSummary` ORM → `SummaryResponse` DTO. |
| 6 | `recent_updates` time window | No time filter for MVP. Both summary types use all active records, ordered by importance/recency. |
| 7 | Login endpoint format | Return JSON `{"redirect_url": url}`. Frontend navigates via `window.location`. |
| 8 | Token delivery after OAuth | Callback redirects to frontend URL with token in query param (`/auth/callback?token=...`). |
| 9 | Auth middleware vs DI | Keep dependency injection pattern (`get_current_user` per-route). No middleware change. |
| 10 | Token storage | Persist to `localStorage`. Sessions survive page refresh. |
| 11 | Query conversation history | Scrollable Q&A history in React state. Not persisted past hard refresh. |
| 12 | Query tab layout | Separate "Ask" tab alongside Sources / Records / Summary. |
| 13 | Summary editing | **Deferred** to post-Phase 3. Model fields (`is_edited`, `edited_content`) exist but no UI or endpoint built. |
| 14 | Markdown rendering | Add `react-markdown` as a frontend dependency. |
| 15 | Summary/query during extraction | Work with whatever records exist. Show informational note when sources are still processing. |

---

## Deferred to Post-Phase 3

- [ ] **Summary editing UI + endpoint** — `PATCH /generated-summaries/{id}` to save `edited_content` and set `is_edited=true`. Frontend inline editing component. Model already supports it.
- [ ] **`recent_updates` time window** — add `time_window` param to `SummaryRequest`, filter records by `created_at` in AI service
- [ ] **Query conversation context** — send prior Q&A pairs to LLM for follow-up questions
- [ ] **Summary auto-invalidation** — detect when records have changed since last cached summary, show "stale" indicator
