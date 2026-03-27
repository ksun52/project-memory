# API Contract

**Product:** Project Memory  
**Version:** v0.1 (MVP)  
**Status:** Draft  
**Source of Truth:** [`docs/api/openapi.yaml`](./api/openapi.yaml)

This document is a human-readable companion to the OpenAPI spec. Both sides (frontend and backend) develop against this contract. Changes require explicit agreement.

---

## Conventions

### Base URL

All endpoints are prefixed with `/api/v1`.

### Authentication

All endpoints (except `/auth/login` and `/auth/callback`) require a valid JWT in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

### Pagination

All list endpoints accept these query parameters:

| Parameter | Type | Required | Max | Notes |
|-----------|------|----------|-----|-------|
| `page` | integer | No | — | 1-indexed |
| `page_size` | integer | No | 100 | Items per page |

All list endpoints return this envelope:

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20
}
```

### Error Format

All errors return this shape:

```json
{
  "error": {
    "code": "not_found",
    "message": "Memory space not found"
  }
}
```

Standard HTTP status codes:
- `401` — unauthenticated
- `403` — forbidden (no access)
- `404` — resource not found
- `422` — validation error / unprocessable entity (FastAPI convention for malformed or invalid request bodies)
- `500` — internal server error

### Soft Delete

`DELETE` endpoints perform soft deletes (set `deleted_at`). They return `204 No Content` on success. Soft-deleted resources are excluded from all list/get responses.

### Timestamps

All timestamps are ISO 8601 strings in UTC: `"2025-01-15T09:30:00Z"`

---

## Shared Enums

These enum values are referenced across multiple endpoints.

### Source Type

```
"note" | "document" | "transcript"
```

### Processing Status

```
"pending" | "processing" | "completed" | "failed"
```

### Record Type

```
"fact" | "event" | "decision" | "issue" | "question" | "preference" | "task" | "insight"
```

### Record Origin

```
"extracted" | "manual"
```

### Record Status

```
"active" | "tentative" | "outdated" | "archived"
```

### Record Importance

```
"low" | "medium" | "high"
```

### Memory Space Status

```
"active" | "archived"
```

### Summary Type

```
"one_pager" | "recent_updates"
```

---

## Auth

### `GET /auth/login`

Initiate WorkOS SSO. Redirects the browser to the WorkOS login page.

**Response:** `302 Redirect` to WorkOS

---

### `GET /auth/callback?code={code}`

Handle WorkOS callback after successful authentication.

**Query Parameters:**

| Parameter | Type | Required |
|-----------|------|----------|
| `code` | string | Yes |

**Response:** `200 OK`

```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

### `POST /auth/logout`

Invalidate the current session.

**Response:** `204 No Content`

---

### `GET /auth/me`

Return the currently authenticated user.

**Response:** `200 OK`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "display_name": "Jane Doe",
  "created_at": "2025-01-15T09:30:00Z"
}
```

---

## Workspace

### `POST /workspaces`

Create a new workspace.

**Request Body:**

```json
{
  "name": "Acme Corp",
  "description": "Client engagement workspace"
}
```

| Field | Type | Required |
|-------|------|----------|
| `name` | string | Yes |
| `description` | string | No |

**Response:** `201 Created`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "owner_id": "660e8400-e29b-41d4-a716-446655440000",
  "name": "Acme Corp",
  "description": "Client engagement workspace",
  "created_at": "2025-01-15T09:30:00Z",
  "updated_at": "2025-01-15T09:30:00Z"
}
```

---

### `GET /workspaces`

List the current user's workspaces.

**Query Parameters:** Pagination (`page`, `page_size`)

**Response:** `200 OK` — `PaginatedResponse<Workspace>`

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "owner_id": "660e8400-e29b-41d4-a716-446655440000",
      "name": "Acme Corp",
      "description": "Client engagement workspace",
      "created_at": "2025-01-15T09:30:00Z",
      "updated_at": "2025-01-15T09:30:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

---

### `GET /workspaces/{id}`

Get a single workspace.

**Response:** `200 OK` — `Workspace`

Same shape as individual item in the list response.

---

### `PATCH /workspaces/{id}`

Update a workspace. Only provided fields are updated.

**Request Body:**

```json
{
  "name": "Acme Corp (Updated)",
  "description": "Updated description"
}
```

| Field | Type | Required |
|-------|------|----------|
| `name` | string | No |
| `description` | string | No |

**Response:** `200 OK` — `Workspace`

---

### `DELETE /workspaces/{id}`

Soft delete a workspace and all its children (memory spaces, sources, records, summaries).

**Response:** `204 No Content`

---

## Memory Space

### `POST /workspaces/{workspace_id}/memory-spaces`

Create a new memory space within a workspace.

**Request Body:**

```json
{
  "name": "Project X",
  "description": "Strategic initiative for Q1"
}
```

| Field | Type | Required |
|-------|------|----------|
| `name` | string | Yes |
| `description` | string | No |

**Response:** `201 Created`

```json
{
  "id": "770e8400-e29b-41d4-a716-446655440000",
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Project X",
  "description": "Strategic initiative for Q1",
  "status": "active",
  "created_at": "2025-01-15T09:30:00Z",
  "updated_at": "2025-01-15T09:30:00Z"
}
```

---

### `GET /workspaces/{workspace_id}/memory-spaces`

List memory spaces within a workspace.

**Query Parameters:**

| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| `page` | integer | No | 1-indexed |
| `page_size` | integer | No | Max 100 |
| `status` | string | No | Filter by `"active"` or `"archived"` |

**Response:** `200 OK` — `PaginatedResponse<MemorySpace>`

---

### `GET /memory-spaces/{id}`

Get a single memory space.

**Response:** `200 OK` — `MemorySpace`

---

### `PATCH /memory-spaces/{id}`

Update a memory space. Only provided fields are updated.

**Request Body:**

```json
{
  "name": "Project X (Renamed)",
  "description": "Updated description",
  "status": "archived"
}
```

| Field | Type | Required |
|-------|------|----------|
| `name` | string | No |
| `description` | string | No |
| `status` | string | No |

**Response:** `200 OK` — `MemorySpace`

---

### `DELETE /memory-spaces/{id}`

Soft delete a memory space and all its children.

**Response:** `204 No Content`

---

### `POST /memory-spaces/{id}/summarize`

Generate a summary from current memory records.

**Request Body:**

```json
{
  "summary_type": "one_pager",
  "regenerate": false
}
```

| Field | Type | Required | Values |
|-------|------|----------|--------|
| `summary_type` | string | Yes | `"one_pager"`, `"recent_updates"` |
| `regenerate` | boolean | No (default `false`) | `true` to force regeneration, `false` to return cached if available |

**Response:** `200 OK`

```json
{
  "id": "880e8400-e29b-41d4-a716-446655440000",
  "memory_space_id": "770e8400-e29b-41d4-a716-446655440000",
  "summary_type": "one_pager",
  "title": "Project X — One-Pager",
  "content": "## Overview\n\nProject X is a strategic initiative...",
  "is_edited": false,
  "edited_content": null,
  "record_ids_used": [
    "990e8400-e29b-41d4-a716-446655440000",
    "aa0e8400-e29b-41d4-a716-446655440000"
  ],
  "generated_at": "2025-01-15T10:00:00Z",
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T10:00:00Z"
}
```

---

### `POST /memory-spaces/{id}/query`

Ask a natural language question about the memory space.

**Request Body:**

```json
{
  "question": "What are the key decisions made so far?"
}
```

| Field | Type | Required |
|-------|------|----------|
| `question` | string | Yes |

**Response:** `200 OK`

```json
{
  "answer": "Three key decisions have been made: (1) ..., (2) ..., (3) ...",
  "citations": [
    {
      "record_id": "990e8400-e29b-41d4-a716-446655440000",
      "source_id": "bb0e8400-e29b-41d4-a716-446655440000",
      "chunk_id": null,
      "excerpt": "We decided to go with vendor A for all infrastructure needs"
    },
    {
      "record_id": "aa0e8400-e29b-41d4-a716-446655440000",
      "source_id": "bb0e8400-e29b-41d4-a716-446655440000",
      "chunk_id": null,
      "excerpt": "Team agreed on bi-weekly sprint cadence going forward"
    }
  ]
}
```

---

## Source

### `POST /memory-spaces/{id}/sources` — Note

Create a text note source. Uses JSON body.

**Content-Type:** `application/json`

**Request Body:**

```json
{
  "source_type": "note",
  "title": "Meeting notes — Jan 15",
  "content": "Discussed roadmap priorities. Agreed on Q1 focus areas..."
}
```

| Field | Type | Required |
|-------|------|----------|
| `source_type` | string | Yes |
| `title` | string | Yes |
| `content` | string | Yes |

**Response:** `201 Created` — `Source`

```json
{
  "id": "bb0e8400-e29b-41d4-a716-446655440000",
  "memory_space_id": "770e8400-e29b-41d4-a716-446655440000",
  "source_type": "note",
  "title": "Meeting notes — Jan 15",
  "processing_status": "pending",
  "processing_error": null,
  "created_at": "2025-01-15T09:30:00Z",
  "updated_at": "2025-01-15T09:30:00Z"
}
```

---

### `POST /memory-spaces/{id}/sources` — Document

Upload a document. Uses multipart form data.

**Content-Type:** `multipart/form-data`

**Form Fields:**

| Field | Type | Required |
|-------|------|----------|
| `source_type` | string | Yes |
| `title` | string | Yes |
| `file` | binary | Yes |

**Response:** `201 Created` — `Source` (same shape as note response, with `source_type: "document"`)

---

### `GET /memory-spaces/{id}/sources`

List sources within a memory space.

**Query Parameters:**

| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| `page` | integer | No | 1-indexed |
| `page_size` | integer | No | Max 100 |
| `source_type` | string | No | Filter by source type |
| `processing_status` | string | No | Filter by processing status |

**Response:** `200 OK` — `PaginatedResponse<Source>`

---

### `GET /sources/{id}`

Get source detail including content and file metadata.

**Response:** `200 OK`

```json
{
  "id": "bb0e8400-e29b-41d4-a716-446655440000",
  "memory_space_id": "770e8400-e29b-41d4-a716-446655440000",
  "source_type": "document",
  "title": "Q1 Strategy Deck",
  "processing_status": "completed",
  "processing_error": null,
  "content": {
    "content_text": "Full extracted text content of the document..."
  },
  "file": {
    "mime_type": "application/pdf",
    "size_bytes": 245760,
    "original_filename": "q1-strategy.pdf"
  },
  "created_at": "2025-01-15T09:30:00Z",
  "updated_at": "2025-01-15T09:35:00Z"
}
```

For note sources, `file` is `null`. For document sources, `content` is populated after parsing completes.

---

### `GET /sources/{id}/content`

Get just the full text content of a source.

**Response:** `200 OK`

```json
{
  "source_id": "bb0e8400-e29b-41d4-a716-446655440000",
  "content_text": "Full text content..."
}
```

---

### `DELETE /sources/{id}`

Soft delete a source and all its children (content, file, chunks, links, embeddings).

**Response:** `204 No Content`

---

## Memory Record

### `GET /memory-spaces/{id}/records`

List and filter memory records within a memory space.

**Query Parameters:**

| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| `page` | integer | No | 1-indexed |
| `page_size` | integer | No | Max 100 |
| `record_type` | string | No | Filter by record type |
| `status` | string | No | Filter by status |
| `importance` | string | No | Filter by importance |

**Response:** `200 OK` — `PaginatedResponse<MemoryRecord>`

```json
{
  "items": [
    {
      "id": "990e8400-e29b-41d4-a716-446655440000",
      "memory_space_id": "770e8400-e29b-41d4-a716-446655440000",
      "record_type": "decision",
      "content": "Decided to use vendor A for cloud infrastructure",
      "origin": "extracted",
      "status": "active",
      "confidence": 0.92,
      "importance": "high",
      "metadata": {},
      "created_at": "2025-01-15T09:35:00Z",
      "updated_at": "2025-01-15T09:35:00Z"
    }
  ],
  "total": 24,
  "page": 1,
  "page_size": 20
}
```

---

### `POST /memory-spaces/{id}/records`

Create a manual memory record.

**Request Body:**

```json
{
  "record_type": "fact",
  "content": "Budget approved at $500K for Q1",
  "importance": "high",
  "metadata": {}
}
```

| Field | Type | Required |
|-------|------|----------|
| `record_type` | string | Yes |
| `content` | string | Yes |
| `importance` | string | No |
| `metadata` | object | No |

**Response:** `201 Created` — `MemoryRecord`

Manual records have `origin: "manual"`, `status: "active"`, `confidence: 1.00`.

---

### `GET /records/{id}`

Get a single memory record.

**Response:** `200 OK` — `MemoryRecord`

---

### `PATCH /records/{id}`

Update a memory record. Only provided fields are updated.

**Request Body:**

```json
{
  "content": "Updated content text",
  "status": "outdated",
  "importance": "low",
  "metadata": { "note": "superseded by newer info" }
}
```

| Field | Type | Required |
|-------|------|----------|
| `content` | string | No |
| `status` | string | No |
| `importance` | string | No |
| `metadata` | object | No |

**Response:** `200 OK` — `MemoryRecord`

---

### `DELETE /records/{id}`

Soft delete a memory record.

**Response:** `204 No Content`

---

### `GET /records/{id}/sources`

Get the sources linked to a memory record (provenance).

**Response:** `200 OK`

```json
{
  "items": [
    {
      "id": "cc0e8400-e29b-41d4-a716-446655440000",
      "record_id": "990e8400-e29b-41d4-a716-446655440000",
      "source_id": "bb0e8400-e29b-41d4-a716-446655440000",
      "source_title": "Meeting notes — Jan 15",
      "source_type": "note",
      "evidence_text": "Team agreed to go with vendor A after evaluating three options",
      "created_at": "2025-01-15T09:35:00Z"
    }
  ]
}
```

| Field | Type | Nullable | Notes |
|-------|------|----------|-------|
| `id` | string (UUID) | No | Link ID |
| `record_id` | string (UUID) | No | |
| `source_id` | string (UUID) | No | |
| `source_title` | string | No | Denormalized from source for display |
| `source_type` | string | No | Denormalized from source for display |
| `evidence_text` | string | Yes | Specific excerpt; null for holistic extractions |
| `created_at` | string | No | ISO 8601 |
