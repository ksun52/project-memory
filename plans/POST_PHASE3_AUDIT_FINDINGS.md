# Documentation & Implementation Audit

**Date:** 2026-03-28
**Branch:** phase-3
**Scope:** All docs in `docs/` compared against actual codebase implementation

---

## 1. Discrepancies & Contradictions Between Documents

### 1.1 QueryCitation Schema Mismatch (API_CONTRACT.md vs openapi.yaml)

**Severity: HIGH**

The query citation schema is fundamentally different between the two API documents:

| Field | API_CONTRACT.md | openapi.yaml |
|-------|----------------|--------------|
| `record_id` | Yes | Yes |
| `source_id` | Yes | **No** |
| `chunk_id` | Yes (nullable) | **No** |
| `excerpt` | Yes | **No** |
| `content` | **No** | Yes |
| `record_type` | **No** | Yes |

**API_CONTRACT.md** defines citations as:
```json
{
  "record_id": "...",
  "source_id": "...",
  "chunk_id": null,
  "excerpt": "We decided to go with vendor A..."
}
```

**openapi.yaml** defines `QueryCitation` as:
```json
{
  "record_id": "...",
  "content": "...",
  "record_type": "decision"
}
```

These are completely incompatible schemas. The frontend types follow a third variant closer to the openapi.yaml version but with its own field names.

---

### 1.2 SummaryRequest `regenerate` Field Missing from openapi.yaml

**Severity: MEDIUM**

- **API_CONTRACT.md** documents `regenerate` as an optional boolean (default `false`) on `SummaryRequest`
- **openapi.yaml** `SummaryRequest` only has `summary_type` — no `regenerate` field
- **Frontend** types.ts includes `regenerate?: boolean` and the SummaryPanel uses it
- **AI_LAYER.md** describes caching behavior that depends on `regenerate: true`

The frontend implementation and API_CONTRACT.md agree, but openapi.yaml (the stated "source of truth") is missing this field.

---

### 1.3 Auth Callback Flow: Token Delivery Mechanism

**Severity: MEDIUM**

- **API_CONTRACT.md** says `GET /auth/callback?code={code}` returns a JSON body:
  ```json
  { "access_token": "...", "token_type": "bearer", "expires_in": 3600 }
  ```
- **openapi.yaml** agrees — returns `TokenResponse` with 200 OK
- **Frontend implementation** (`auth/callback/page.tsx`) reads the token from a **query parameter** (`?token=...`), not from a JSON response body
- The callback page never calls the backend API — it just reads `searchParams.get("token")`

This means the backend likely redirects with the token in the URL, which is a fundamentally different flow from what both API docs describe.

---

### 1.4 Memory Space Detail Layout: Tabs vs Query Bar

**Severity: LOW** — *Resolved*

- **FRONTEND.md** previously described a persistent query bar above 3 tabs with a slide-over panel
- **Implementation** has 4 tabs (Sources, Records, Summary, Ask) with query as its own tab
- FRONTEND.md has been updated to match the implementation

---

## 2. Documented But Not Yet Implemented

### 2.1 Frontend Components Listed in FRONTEND.md But Missing

| Component | Documented In | Status |
|-----------|--------------|--------|
| `SourceDetail` | FRONTEND.md §6 | **Missing** — no source detail slide-over or expandable panel exists |
| `WorkspaceCard` | FRONTEND.md §6 | **Missing** as standalone — card UI is inline within WorkspaceList |

*Resolved:* `MemorySpaceDetail`, `QueryBar`, `QueryResultPanel`, `GenerateSummaryButton`, and `SummaryDisplay` were removed from FRONTEND.md and replaced with the actual component names (`SummaryPanel`, `QueryPanel`).

### 2.2 Frontend Tests

- **FRONTEND.md §11** describes contract-first workflow with MSW for parallel development
- **FRONTEND.md §12** mentions E2E testing with Playwright as a future consideration
- **Actual state:** Zero test files exist in the frontend. No unit tests, integration tests, or E2E tests.

### 2.3 Summary Editing (User Edits to Summaries)

- **DATA_MODEL.md** defines `generated_summaries.is_edited` and `edited_content` fields
- **API_CONTRACT.md** SummaryResponse includes `is_edited` and `edited_content`
- **openapi.yaml** SummaryResponse includes these fields
- **Frontend:** SummaryPanel can generate and regenerate summaries, but there is **no UI for editing summary content**. The `is_edited` / `edited_content` fields go unused on the frontend.

### 2.4 Memory Record Date Range Filtering

- **BACKEND.md §5** mentions "Filtering + pagination — query records by type, status, importance, **date range**"
- **API_CONTRACT.md** and **openapi.yaml** do not include date range parameters on `GET /memory-spaces/{id}/records`
- No date range filtering exists in the implementation

### 2.5 `usePagination` Shared Hook

- **FRONTEND.md §9** documents a shared `usePagination` hook in `shared/hooks/`
- Need to verify if it's actually used by components or if pagination is handled inline

---

## 3. Implemented Differently Than Documented

### 3.1 Token Storage: Memory vs localStorage

**Severity: HIGH (Security)** — *Resolved (docs updated to match implementation)*

- **FRONTEND.md** updated to reflect localStorage usage
- localStorage chosen for MVP to persist sessions across page refreshes
- Trade-off: localStorage is accessible to any JS on the page (XSS risk), but in-memory storage would force re-login on every refresh without a silent refresh token flow
- See TODO at end of this document for planned migration to HttpOnly cookies

### 3.2 Next.js Version

**Severity: MEDIUM** — *Resolved (docs updated)*

- ARCHITECTURE.md and FRONTEND.md updated from "Next.js 14+" to "Next.js 16"
- Implementation uses Next.js 16.2.1 with React 19

### 3.3 Tailwind CSS Version

**Severity: MEDIUM** — *Resolved (docs updated)*

- FRONTEND.md updated to "Tailwind CSS v4" with note about CSS-based config
- ARCHITECTURE.md updated to "Tailwind CSS v4"
- Removed `tailwind.config.ts` from folder structure diagram (Tailwind v4 uses CSS-based config in `globals.css`)

### 3.4 shadcn/ui Component Location

**Severity: LOW** — *Resolved (docs updated)*

- FRONTEND.md folder structure updated: `src/components/ui/` (not `src/lib/components/ui/`)
- `src/lib/` only contains `utils.ts` (the `cn()` helper)

### 3.5 OpenAI Model Default

**Severity: MEDIUM** — *Resolved (docs updated)*

- ARCHITECTURE.md updated from "TBD (OpenAI or Anthropic)" to "OpenAI (`gpt-4o-mini`)"
- Embedding model updated from "tentative" to confirmed `text-embedding-3-small`

### 3.6 Auth Provider File Location

**Severity: LOW** — *Resolved (verified correct)*

- `auth-provider.tsx` is at `domains/auth/auth-provider.tsx` — matches docs
- `Providers` component is at `shared/components/providers.tsx` — matches docs

### 3.7 Zod Version

**Severity: LOW** — *Resolved (docs updated)*

- FRONTEND.md updated from "Zod" to "Zod v4"
- ARCHITECTURE.md updated from "Zod" to "Zod v4"

---

## 4. Implemented Features Not Described in Documentation

### 4.1 Auth Bypass Mode

*Resolved* — Documented in BACKEND.md §8 (Auth Bypass subsection under Cross-Cutting Concerns)

### 4.2 Smart Source Polling

*Resolved* — Documented in FRONTEND.md §9 (Smart Source Polling subsection under Cross-Cutting Concerns)

### 4.3 Dark Mode Support

*Resolved* — Documented in FRONTEND.md §9 (Theming subsection); updated §12 Future Considerations to reference adding a user-facing toggle

### 4.4 "Ask" Tab (Query as Full Tab)

*Resolved (earlier)* — FRONTEND.md updated to describe 4-tab layout with dedicated Ask tab

### 4.5 Source Processing Status Visual Feedback

*Resolved* — Documented in FRONTEND.md §6 Source component table (SourceCard description updated with animated spinner and status badge details)

### 4.6 Memory Space Status Toggle

*Resolved (earlier)* — Already documented in FRONTEND.md §6 MemorySpaceCard description ("inline archive/activate toggle, edit, and delete")

### 4.7 Workspace/Memory Space Edit & Delete

*Resolved* — Documented in FRONTEND.md §6 (WorkspaceCard and WorkspaceList descriptions updated with dropdown menu and delete confirmation); shared `ConfirmDialog` documented in §9

---

## 5. Summary of Action Items

### Critical (Should Fix Before Moving Forward)

| # | Finding | Action |
|---|---------|--------|
| 1 | QueryCitation schema mismatch across 3 sources | Align openapi.yaml, API_CONTRACT.md, and frontend types to a single schema |
| 2 | SummaryRequest missing `regenerate` in openapi.yaml | Add `regenerate` field to openapi.yaml SummaryRequest |
| 3 | Auth callback flow undocumented | Document actual token-via-redirect flow; update API_CONTRACT.md and openapi.yaml |
| 4 | Token in localStorage vs documented in-memory | ~~Either update docs to reflect localStorage choice, or migrate to in-memory storage per original security design~~ Resolved — docs updated to match localStorage implementation |

### Medium (Should Update Documentation)

| # | Finding | Action |
|---|---------|--------|
| 5 | Next.js 16 / React 19 / Tailwind v4 / Zod 4 | ~~Update ARCHITECTURE.md and FRONTEND.md version references~~ Resolved |
| 6 | 4-tab layout vs documented 3-tab + query bar | ~~Update FRONTEND.md to reflect actual tab-based layout~~ Resolved (earlier) |
| 7 | Missing component names in FRONTEND.md | ~~Update component table (QueryPanel, SummaryPanel replace documented names)~~ Resolved (earlier) |
| 8 | shadcn/ui path | ~~Update folder structure in FRONTEND.md~~ Resolved |
| 9 | OpenAI model decision | ~~Update ARCHITECTURE.md to reflect `gpt-4o-mini` decision~~ Resolved |
| 10 | Auth bypass mode | ~~Document in BACKEND.md under dev workflow~~ Resolved |
| 11 | Date range filtering | Remove from BACKEND.md or add to API contract |

### Low (Track for Later)

| # | Finding | Action |
|---|---------|--------|
| 12 | No frontend tests | Track as tech debt |
| 13 | No summary editing UI | Track as future feature or remove from data model |
| 14 | Smart polling, dark mode, status toggle | ~~Document as implemented features in FRONTEND.md~~ Resolved |

---

## 6. Future Security TODOs

### 6.1 Migrate Token Storage from localStorage to HttpOnly Cookies

**Priority: LOW** (post-MVP)

The JWT is currently stored in `localStorage` for simplicity. This is vulnerable to XSS — any JavaScript running on the page can read the token. The recommended migration path:

1. Backend sets an `HttpOnly`, `Secure`, `SameSite=Strict` cookie on the `/auth/callback` redirect instead of passing the token as a query parameter
2. Frontend API client stops sending `Authorization: Bearer` headers — the browser sends the cookie automatically
3. Backend auth middleware reads the token from the cookie instead of the `Authorization` header
4. Add CSRF protection (SameSite=Strict covers most cases, but consider a CSRF token for non-GET mutations)
5. Remove `localStorage` token management from `AuthProvider`

This eliminates both the XSS token theft risk and the token-in-URL leakage concern (see TODO in `backend/app/domains/auth/service.py`).
