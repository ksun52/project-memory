# Data Model

**Product:** Project Memory  
**Version:** v0.1 (MVP)  
**Status:** Draft

---

## Overview

This document defines the database schema for Project Memory. The data model follows these principles:

- **NOT NULL by default** — all columns are required unless there's a strong reason for nullability
- **No schema-level defaults** — all default values are set explicitly in the SQLAlchemy model layer, not in the database schema; this keeps the data model doc focused on structure and constraints
- **Generic schema** — memory records use broad types, not domain-specific tables
- **Strong provenance** — every record traces back to its source(s)
- **Separation of concerns** — content, files, chunks, and embeddings are stored in dedicated tables
- **Future-proof** — designed for multi-user workspaces from day one

---

## Entity Relationship Diagram

```
users
  │
  └─< workspaces (owner_id)
        │
        └─< memory_spaces (workspace_id)
              │
              ├─< sources (memory_space_id)
              │     │
              │     ├── source_contents (source_id) [1:1]
              │     │
              │     ├── source_files (source_id) [1:1, only for documents]
              │     │
              │     ├─< source_chunks (source_id) [1:many, always exists]
              │     │     │
              │     │     └── embeddings (entity_type='source_chunk')
              │     │
              │     └─< record_source_links (source_id)
              │
              ├─< memory_records (memory_space_id)
              │     │
              │     ├─< record_source_links (record_id)
              │     │
              │     └── embeddings (entity_type='memory_record')
              │
              └─< generated_summaries (memory_space_id)

embeddings (polymorphic - references memory_records or source_chunks)
```

---

## Tables

### 1. `users`

Stores user identity. Authentication is handled by WorkOS; we store a reference to the external identity.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | UUID | NOT NULL | Primary key |
| `auth_provider` | VARCHAR(50) | NOT NULL | `workos` (extensible for future providers) |
| `auth_provider_id` | VARCHAR(255) | NOT NULL | User's ID in the auth provider |
| `email` | VARCHAR(255) | NOT NULL | Synced from auth provider |
| `display_name` | VARCHAR(255) | NOT NULL | User-facing name |
| `created_at` | TIMESTAMP | NOT NULL | |
| `updated_at` | TIMESTAMP | NOT NULL | |

**Constraints:**
- Primary key: `id`
- Unique: `(auth_provider, auth_provider_id)`
- Unique: `email`

**Indexes:**
- `idx_users_email` on `email`

---

### 2. `workspaces`

Top-level container for a user or team. All data is scoped within a workspace.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | UUID | NOT NULL | Primary key |
| `owner_id` | UUID | NOT NULL | FK → users.id |
| `name` | VARCHAR(255) | NOT NULL | Workspace name |
| `description` | TEXT | NOT NULL | |
| `created_at` | TIMESTAMP | NOT NULL | |
| `updated_at` | TIMESTAMP | NOT NULL | |
| `deleted_at` | TIMESTAMP | **NULLABLE** | Set on soft delete; NULL = active |

**Constraints:**
- Primary key: `id`
- Foreign key: `owner_id` → `users.id`

**Indexes:**
- `idx_workspaces_owner_id` on `owner_id`

**Future:** Add `workspace_members` join table for multi-user collaboration.

---

### 3. `memory_spaces`

A scoped container for a specific project, client, or topic within a workspace.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | UUID | NOT NULL | Primary key |
| `workspace_id` | UUID | NOT NULL | FK → workspaces.id |
| `name` | VARCHAR(255) | NOT NULL | Project/client name |
| `description` | TEXT | NOT NULL | |
| `status` | VARCHAR(50) | NOT NULL | `active`, `archived` |
| `created_at` | TIMESTAMP | NOT NULL | |
| `updated_at` | TIMESTAMP | NOT NULL | |
| `deleted_at` | TIMESTAMP | **NULLABLE** | Set on soft delete; NULL = active |

**Constraints:**
- Primary key: `id`
- Foreign key: `workspace_id` → `workspaces.id`
- Check: `status IN ('active', 'archived')`

**Indexes:**
- `idx_memory_spaces_workspace_id` on `workspace_id`
- `idx_memory_spaces_status` on `status`

---

### 4. `sources`

Metadata for a raw input (note, document, transcript). Content is stored separately.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | UUID | NOT NULL | Primary key |
| `memory_space_id` | UUID | NOT NULL | FK → memory_spaces.id |
| `source_type` | VARCHAR(50) | NOT NULL | `note`, `document`, `transcript` |
| `title` | VARCHAR(500) | NOT NULL | User-provided or AI-generated |
| `processing_status` | VARCHAR(50) | NOT NULL | `pending`, `processing`, `completed`, `failed` |
| `processing_error` | TEXT | **NULLABLE** | Error message if processing failed |
| `created_at` | TIMESTAMP | NOT NULL | |
| `updated_at` | TIMESTAMP | NOT NULL | |
| `deleted_at` | TIMESTAMP | **NULLABLE** | Set on soft delete; NULL = active |

**Constraints:**
- Primary key: `id`
- Foreign key: `memory_space_id` → `memory_spaces.id`
- Check: `source_type IN ('note', 'document', 'transcript')`
- Check: `processing_status IN ('pending', 'processing', 'completed', 'failed')`

**Indexes:**
- `idx_sources_memory_space_id` on `memory_space_id`
- `idx_sources_processing_status` on `processing_status`

**Source Types:**
| Type | Description | Has file? |
|------|-------------|-----------|
| `note` | User-typed or pasted text | No |
| `document` | Uploaded file (PDF, DOCX, TXT, etc.) | Yes |
| `transcript` | Text from audio transcription (audio discarded after processing) | No |

---

### 5. `source_contents`

Stores the full extracted/transcribed text content. One record per source (1:1).

Used for display and as the source of truth for non-AI operations.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | UUID | NOT NULL | Primary key |
| `source_id` | UUID | NOT NULL | FK → sources.id (unique, 1:1) |
| `content_text` | TEXT | NOT NULL | Full extracted/transcribed text |
| `created_at` | TIMESTAMP | NOT NULL | |
| `deleted_at` | TIMESTAMP | **NULLABLE** | Set on soft delete; NULL = active |

**Constraints:**
- Primary key: `id`
- Foreign key + Unique: `source_id` → `sources.id` (enforces 1:1)

---

### 6. `source_files`

Stores file metadata for uploaded documents. Only exists for `document` type sources (1:1).

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | UUID | NOT NULL | Primary key |
| `source_id` | UUID | NOT NULL | FK → sources.id (unique, 1:1) |
| `file_path` | VARCHAR(1000) | NOT NULL | Path in blob storage |
| `mime_type` | VARCHAR(100) | NOT NULL | e.g., `application/pdf` |
| `size_bytes` | BIGINT | NOT NULL | File size in bytes |
| `original_filename` | VARCHAR(500) | NOT NULL | Original upload filename |
| `created_at` | TIMESTAMP | NOT NULL | |
| `deleted_at` | TIMESTAMP | **NULLABLE** | Set on soft delete; NULL = active |

**Constraints:**
- Primary key: `id`
- Foreign key + Unique: `source_id` → `sources.id` (enforces 1:1)

---

### 7. `source_chunks`

Stores chunked pieces of source content for embedding. Always created (at least 1 chunk per source).

This is the table that gets embedded and searched for RAG retrieval.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | UUID | NOT NULL | Primary key |
| `source_id` | UUID | NOT NULL | FK → sources.id |
| `chunk_index` | INT | NOT NULL | 0-based order within source |
| `content` | TEXT | NOT NULL | The chunk text |
| `start_offset` | INT | NOT NULL | Character offset start in source_contents.content_text |
| `end_offset` | INT | NOT NULL | Character offset end |
| `created_at` | TIMESTAMP | NOT NULL | |
| `deleted_at` | TIMESTAMP | **NULLABLE** | Set on soft delete; NULL = active |

**Constraints:**
- Primary key: `id`
- Foreign key: `source_id` → `sources.id`
- Unique: `(source_id, chunk_index)`

**Indexes:**
- `idx_source_chunks_source_id` on `source_id`

**Design Notes:**
- Chunks are always created, even for short content (simplifies retrieval logic)
- Chunks may overlap (typically 10-20%) to preserve context at boundaries
- `start_offset` and `end_offset` allow highlighting the chunk within the full source content

---

### 8. `memory_records`

A normalized, structured unit of context extracted from sources.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | UUID | NOT NULL | Primary key |
| `memory_space_id` | UUID | NOT NULL | FK → memory_spaces.id |
| `record_type` | VARCHAR(50) | NOT NULL | See record types below |
| `content` | TEXT | NOT NULL | The memory content (concise summary) |
| `origin` | VARCHAR(50) | NOT NULL | `extracted`, `manual` |
| `status` | VARCHAR(50) | NOT NULL | `active`, `tentative`, `outdated`, `archived` |
| `confidence` | DECIMAL(3,2) | NOT NULL | 0.00–1.00 (AI confidence score) |
| `importance` | VARCHAR(20) | NOT NULL | `low`, `medium`, `high` |
| `metadata` | JSONB | NOT NULL | Flexible key-value for additional structure |
| `created_at` | TIMESTAMP | NOT NULL | |
| `updated_at` | TIMESTAMP | NOT NULL | |
| `deleted_at` | TIMESTAMP | **NULLABLE** | Set on soft delete; NULL = active |

**Constraints:**
- Primary key: `id`
- Foreign key: `memory_space_id` → `memory_spaces.id`
- Check: `record_type IN ('fact', 'event', 'decision', 'issue', 'question', 'preference', 'task', 'insight')`
- Check: `origin IN ('extracted', 'manual')`
- Check: `status IN ('active', 'tentative', 'outdated', 'archived')`
- Check: `importance IN ('low', 'medium', 'high')`
- Check: `confidence >= 0.00 AND confidence <= 1.00`

**Indexes:**
- `idx_memory_records_memory_space_id` on `memory_space_id`
- `idx_memory_records_status` on `status`
- `idx_memory_records_record_type` on `record_type`

**Record Types:**
| Type | Description |
|------|-------------|
| `fact` | A piece of factual information |
| `event` | Something that happened (past or scheduled) |
| `decision` | A choice that was made |
| `issue` | A problem or concern |
| `question` | An open question or uncertainty |
| `preference` | A stated preference or requirement |
| `task` | An action item or to-do |
| `insight` | An observation or inference |

**Origin Values:**
| Value | Description |
|-------|-------------|
| `extracted` | AI-generated from source content |
| `manual` | User-created directly |

**Status Values:**
| Value | Description |
|-------|-------------|
| `active` | Current and valid |
| `tentative` | Needs confirmation |
| `outdated` | Superseded by newer information |
| `archived` | Removed from active use |

---

### 9. `record_source_links`

Many-to-many join table linking memory records to their source(s) with optional evidence.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | UUID | NOT NULL | Primary key |
| `record_id` | UUID | NOT NULL | FK → memory_records.id |
| `source_id` | UUID | NOT NULL | FK → sources.id |
| `evidence_text` | TEXT | **NULLABLE** | Specific excerpt supporting this record |
| `evidence_start_offset` | INT | **NULLABLE** | Character offset start in source content |
| `evidence_end_offset` | INT | **NULLABLE** | Character offset end |
| `created_at` | TIMESTAMP | NOT NULL | |
| `deleted_at` | TIMESTAMP | **NULLABLE** | Set on soft delete; NULL = active |

**Constraints:**
- Primary key: `id`
- Foreign key: `record_id` → `memory_records.id`
- Foreign key: `source_id` → `sources.id`
- Unique: `(record_id, source_id)`

**Indexes:**
- `idx_record_source_links_record_id` on `record_id`
- `idx_record_source_links_source_id` on `source_id`

**Nullable Rationale:**
- `evidence_text` and offsets are nullable because manual records may not have specific evidence, and some extractions may be holistic (derived from entire source).

---

### 10. `embeddings`

Unified table for all vector embeddings (memory records and source chunks).

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | UUID | NOT NULL | Primary key |
| `entity_type` | VARCHAR(50) | NOT NULL | `memory_record`, `source_chunk` |
| `entity_id` | UUID | NOT NULL | ID of the embedded entity |
| `embedding` | VECTOR(1536) | NOT NULL | The vector (pgvector) |
| `model_id` | VARCHAR(100) | NOT NULL | e.g., `text-embedding-3-small` |
| `created_at` | TIMESTAMP | NOT NULL | |
| `deleted_at` | TIMESTAMP | **NULLABLE** | Set on soft delete; NULL = active |

**Constraints:**
- Primary key: `id`
- Unique: `(entity_type, entity_id, model_id)`
- Check: `entity_type IN ('memory_record', 'source_chunk')`

**Indexes:**
- `idx_embeddings_entity` on `(entity_type, entity_id)`
- HNSW index on `embedding` for fast similarity search:
  ```sql
  CREATE INDEX idx_embeddings_vector ON embeddings 
  USING hnsw (embedding vector_cosine_ops);
  ```

**Design Notes:**
- `entity_id` is not a formal FK since it references multiple tables (polymorphic)
- Application logic ensures referential integrity
- `model_id` allows re-embedding when upgrading models
- Only `source_chunks` are embedded (not `source_contents`)—this keeps retrieval logic simple

---

### 11. `generated_summaries`

Stores AI-generated summaries with optional user edits.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | UUID | NOT NULL | Primary key |
| `memory_space_id` | UUID | NOT NULL | FK → memory_spaces.id |
| `summary_type` | VARCHAR(50) | NOT NULL | `one_pager`, `recent_updates` |
| `title` | VARCHAR(500) | NOT NULL | Display title |
| `content` | TEXT | NOT NULL | Original AI-generated summary (markdown) |
| `is_edited` | BOOLEAN | NOT NULL | Whether user has modified |
| `edited_content` | TEXT | **NULLABLE** | User-modified version |
| `record_ids_used` | UUID[] | NOT NULL | Array of record IDs that contributed |
| `prompt_version` | VARCHAR(100) | NOT NULL | Which prompt template was used |
| `model_id` | VARCHAR(100) | NOT NULL | Which LLM generated it |
| `generated_at` | TIMESTAMP | NOT NULL | When LLM call completed |
| `created_at` | TIMESTAMP | NOT NULL | |
| `updated_at` | TIMESTAMP | NOT NULL | |
| `deleted_at` | TIMESTAMP | **NULLABLE** | Set on soft delete; NULL = active |

**Constraints:**
- Primary key: `id`
- Foreign key: `memory_space_id` → `memory_spaces.id`
- Check: `summary_type IN ('one_pager', 'recent_updates')`

**Indexes:**
- `idx_generated_summaries_memory_space_id` on `memory_space_id`
- `idx_generated_summaries_summary_type` on `summary_type`

**Usage:**
- Display `edited_content` if `is_edited = true`, otherwise display `content`
- `content` is always preserved as the original AI output
- `record_ids_used` enables "regenerate" by comparing current records

---

## Nullable Fields Summary

| Table | Nullable Column | Reason |
|-------|-----------------|--------|
| `sources` | `processing_error` | Only populated on failure |
| `record_source_links` | `evidence_text` | Manual records or holistic extractions may lack specific evidence |
| `record_source_links` | `evidence_start_offset` | Same as above |
| `record_source_links` | `evidence_end_offset` | Same as above |
| `generated_summaries` | `edited_content` | Only populated if user edits |
| All tables (except `users`) | `deleted_at` | Soft delete — NULL means active, timestamp means deleted |

All other columns are NOT NULL. No schema-level defaults are defined — all defaults (UUID generation, timestamps, initial status values) are set in the SQLAlchemy model layer.

---

## Table Summary

| Table | Purpose | Relationship |
|-------|---------|--------------|
| `users` | User identity (auth via WorkOS) | — |
| `workspaces` | Top-level container | belongs to user |
| `memory_spaces` | Project/client container | belongs to workspace |
| `sources` | Source metadata | belongs to memory_space |
| `source_contents` | Full text content | 1:1 with source |
| `source_files` | File metadata | 1:1 with source (documents only) |
| `source_chunks` | Chunked content for embedding | 1:many with source |
| `memory_records` | Extracted knowledge | belongs to memory_space |
| `record_source_links` | Provenance links | many-to-many (records ↔ sources) |
| `embeddings` | Vector embeddings | polymorphic (chunks + records) |
| `generated_summaries` | Cached AI summaries | belongs to memory_space |

---

## Key Design Decisions

### Content vs Chunks

- **`source_contents`** — Full text, used for display and non-AI operations
- **`source_chunks`** — Chunked text, used for embedding and RAG retrieval
- Chunks are always created (even for short content) to simplify retrieval logic
- Only chunks get embedded; content is never embedded directly

### Embeddings Strategy

- Unified `embeddings` table for both memory records and source chunks
- Uses pgvector with HNSW index for fast similarity search
- `model_id` column supports re-embedding when upgrading models
- Polymorphic design (`entity_type` + `entity_id`) keeps queries simple

### Authentication

- WorkOS handles authentication
- `users` table stores reference to external identity
- Decouples data model from auth provider for future flexibility

### Processing Status

- Four statuses: `pending`, `processing`, `completed`, `failed`
- Supports both sync (MVP) and async (future) extraction
- `processing_error` captures failure details

### Soft Delete

- All entities (except `users`) have a nullable `deleted_at` timestamp column
- `deleted_at = NULL` means the record is active; a timestamp means it has been soft-deleted
- All queries filter `WHERE deleted_at IS NULL` by default (enforced via SQLAlchemy base model mixin)
- Soft-deleting a parent entity cascades to its children:
  - Workspace → memory spaces → sources, records, summaries
  - Source → content, file, chunks, record-source links, embeddings
  - Memory record → record-source links, embeddings
- `users` table does not use soft delete — account deactivation is an auth-layer concern
- Hard delete (permanent removal) is not exposed for MVP

---

## Future Considerations

| Feature | How to Extend |
|---------|---------------|
| Multi-user workspaces | Add `workspace_members` join table with `user_id`, `workspace_id`, `role` |
| Deduplication | Add `content_hash` to `memory_records`, query for duplicates |
| Contradiction detection | Use `status = 'tentative'` + `metadata` to flag conflicts |
| Freshness tracking | Add `last_validated_at` timestamp to `memory_records` |
| Tags/categories | Add `tags` table + `record_tags` join table |
| Audit logging | Add `record_history` table for change tracking |
| Cross-project insights | Query across memory_spaces within same workspace |
