# Mock Service Worker (MSW) Setup

This directory contains the frontend's mock API layer, powered by [MSW](https://mswjs.io/). It intercepts HTTP requests in the browser and returns realistic responses, enabling full frontend development without a running backend.

## How It Works

MSW is enabled when `NEXT_PUBLIC_ENABLE_MSW=true` in `.env.local`. On app mount, `msw-provider.tsx` initializes the service worker and blocks rendering until it's ready. All requests to `http://localhost:8000/api/v1/*` are intercepted; unmatched requests pass through to the real network.

**Key files:**
- `browser.ts` — Creates the MSW worker with all handlers
- `init.ts` — Async initialization (no-op on server or when MSW disabled)
- `msw-provider.tsx` — React component that gates rendering until MSW is ready
- `seed-data.ts` — Initial data and TypeScript interfaces for mock entities
- `handlers/` — Request handlers organized by domain

## Seed Data

All mock data is centered around a realistic **Acme Corp database migration** scenario.

### Entities & Relationships

```
Dev User (dev@projectmemory.local)
├── Acme Corp (workspace)
│   ├── Stakeholder Interviews (memory space, active)
│   │   ├── Sources (4):
│   │   │   ├── Kickoff meeting notes       [note, completed]
│   │   │   ├── Project charter v2          [document/PDF, completed]
│   │   │   ├── Follow-up with VP of Eng    [note, pending]
│   │   │   └── Org chart (corrupted file)  [document, failed]
│   │   │
│   │   ├── Memory Records (10):
│   │   │   ├── fact: timeline & budget (extracted, high)
│   │   │   ├── decision: Oracle → PostgreSQL (extracted, high)
│   │   │   ├── issue: PL/SQL conversion needed (extracted, high)
│   │   │   ├── fact: Sarah Chen is POC (extracted, medium)
│   │   │   ├── event: weekly syncs Thu 2pm (extracted, medium)
│   │   │   ├── task: assessment report due July 1 (extracted, high)
│   │   │   ├── insight: previous migration failed (extracted, high)
│   │   │   ├── issue: only 2 DBAs available (extracted, tentative, medium)
│   │   │   ├── preference: weekend cutover (extracted, medium)
│   │   │   └── question: zero downtime possible? (manual, high)
│   │   │
│   │   └── Record-Source Links (6):
│   │       Links extracted records back to source text with evidence excerpts
│   │
│   ├── Technical Architecture (memory space, active, empty)
│   └── Phase 1 Retro (memory space, archived, empty)
│
├── Internal Research (workspace)
│   └── Competitor Analysis (memory space, active, empty)
│
└── Product Launch Q3 (workspace, empty)
```

### What the seed data demonstrates
- **Multiple processing statuses**: completed, pending, and failed sources
- **Mixed record types**: all 8 types (fact, event, decision, issue, question, preference, task, insight)
- **Mixed origins**: 9 extracted records + 1 manual record
- **Mixed statuses**: 9 active + 1 tentative record
- **Confidence range**: 0.75 to 1.0
- **Provenance**: 6 record-source links with evidence text excerpts
- **File metadata**: one PDF source with mime type and file size
- **Failed processing**: one source with an error message

## Mock Behaviors by Feature

### Authentication

Static mock — always returns the dev user and token. No real auth logic.

| Action | Behavior |
|--------|----------|
| `GET /auth/me` | Returns `DEV_USER` |
| `GET /auth/login` | Returns a dummy redirect URL |
| `GET /auth/callback?code=...` | Returns `DEV_TOKEN` (validates code param exists) |
| `POST /auth/logout` | Returns 204 |

### Workspaces

Standard CRUD with in-memory store.

| Action | Behavior |
|--------|----------|
| Create | Validates name is non-empty. Generates UUID, sets timestamps. Returns 201. |
| List | Paginated, excludes soft-deleted workspaces. |
| Get | Returns 404 if deleted or missing. |
| Update | Partial update of name/description. Updates `updated_at`. |
| Delete | Soft delete — sets `deleted_at`, returns 204. Entity remains in memory but hidden from queries. |

### Memory Spaces

Standard CRUD scoped to a workspace.

| Action | Behavior |
|--------|----------|
| Create | Validates name. Defaults `status: "active"`. Returns 201. |
| List | Paginated, filtered by workspace ID. Optional `status` filter (active/archived). |
| Get | Returns 404 if deleted. |
| Update | Partial update. Validates status enum if provided. |
| Delete | Soft delete. |
| Summarize | Returns **501 Not Implemented** (stub). |
| Query | Returns **501 Not Implemented** (stub). |

### Sources — Creating Notes

When a user creates a note source (JSON request):

1. Validates `title` and `content` are present
2. Creates the source with `processing_status: "pending"`
3. Stores the content text in the content store
4. Returns the source immediately (201)
5. **After 5 seconds**, a `setTimeout` callback transitions the source to `processing_status: "completed"` — simulating backend AI extraction

The frontend polls every 3 seconds and will pick up the status change on the next refetch.

### Sources — Uploading Documents

When a user uploads a document (multipart form data):

1. Validates `title` and `file` are present
2. Creates the source with `source_type: "document"` and `processing_status: "pending"`
3. Reads the file content via `file.text()` and stores it
4. Stores file metadata (mime type, size, original filename)
5. Returns the source immediately (201)
6. **After 5 seconds**, same async processing simulation as notes

### Sources — Listing & Filtering

- Paginated, scoped to a memory space
- Optional filters: `source_type` (note/document/transcript) and `processing_status` (pending/processing/completed/failed)
- Excludes soft-deleted sources

### Sources — Detail View

`GET /sources/:id` returns an enriched response with:
- Base source fields
- `content` — full text content (null for failed sources)
- `file` — file metadata if it's a document (null for notes)
- `linked_records_count` — number of memory records linked to this source (computed from record-source links)

### Sources — Deletion

Soft delete. Sets `deleted_at`, returns 204. Source is excluded from all subsequent queries.

### Memory Records — Manual Creation

When a user creates a record manually:

1. Validates `record_type` (must be one of 8 valid types) and `content`
2. Creates with `origin: "manual"`, `status: "active"`, `confidence: 1.0`
3. `importance` defaults to `"medium"` if not provided or invalid
4. Returns 201

Note: the mock does **not** simulate AI extraction creating records. Extracted records only exist as seed data.

### Memory Records — Editing

`PATCH /records/:id` supports partial updates:
- `content` — free text
- `status` — validated against: active, tentative, outdated, archived
- `importance` — validated against: low, medium, high

Returns 422 on invalid enum values.

### Memory Records — Provenance

`GET /records/:id/sources` returns an array of record-source links with:
- `source_title` and `source_type` (denormalized from the source)
- `evidence_text` — the exact excerpt from the source that supports this record

Only seed data has provenance links. Manually created records will have no linked sources.

### Memory Records — Deletion

Soft delete, same as other entities.

## Cross-Cutting Patterns

### Soft Deletes
All entities use a `deleted_at` field. `DELETE` endpoints set this timestamp rather than removing the object. All `GET` endpoints filter out deleted entities. A `GET` for a specific deleted entity returns 404.

### Pagination
All list endpoints use offset-based pagination:
- Query params: `page` (default: 1), `page_size` (default: 20)
- Response: `{ items: [...], total, page, page_size }`
- Filters are applied **before** pagination

### Validation & Errors
- Required fields → 422 with `{ error: { code: "validation_error", message: "..." } }`
- Invalid enums → 422 with specific message
- Not found → 404 with `{ error: { code: "not_found", message: "..." } }`
- Stubs → 501 with `{ error: { code: "not_implemented", message: "..." } }`

### State Isolation
Each handler file maintains its own in-memory arrays. Each exports a `reset*()` function that restores seed state (useful for test isolation, not currently called automatically).

## Limitations

- **No cross-entity cascading**: Deleting a source does not delete its linked records or record-source links
- **No AI extraction simulation for new sources**: The mock transitions status to "completed" but does not generate new memory records or record-source links for user-created sources
- **No ownership validation**: All requests are treated as coming from DEV_USER; no actual token validation occurs
- **No workspace scoping on sources/records**: The mock doesn't validate that a memory space belongs to the correct workspace
- **Static provenance data**: Record-source links only exist as seed data and are not created when new records are added
