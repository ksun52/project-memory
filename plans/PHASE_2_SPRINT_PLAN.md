# Phase 2 Sprint Plan

**Phase:** 2 — Data Domains + Ingestion
**Branch:** `phase-2`
**Depends on:** Phase 0 + Phase 1 (complete)

---

## Track F: Source Domain (Backend)

**Depends on:** Phase 1 backend (memory space service for scoping)

### Domain Entities & Schemas (source/models.py)

ORM models already exist. Need to add domain entities and Pydantic DTOs.

- [ ] Create `SourceEntity` dataclass with fields: id, memory_space_id, source_type, title, processing_status, processing_error, created_at, updated_at
- [ ] Create `SourceEntity.from_orm()` classmethod to convert Source ORM → SourceEntity
- [ ] Create `SourceContentEntity` dataclass with fields: source_id, content_text
- [ ] Create `SourceFileEntity` dataclass with fields: source_id, mime_type, size_bytes, original_filename
- [ ] Create `SourceChunkEntity` dataclass with fields: id, source_id, chunk_index, content, start_offset, end_offset
- [ ] Create `SourceCreateNote` Pydantic schema with fields: source_type (literal "note"), title, content — with validation
- [ ] Create `SourceCreateDocument` Pydantic schema with fields: source_type (literal "document"), title — for multipart upload
- [ ] Create `SourceResponse` Pydantic schema matching API contract (id, memory_space_id, source_type, title, processing_status, processing_error, created_at, updated_at)
- [ ] Create `SourceDetailResponse` Pydantic schema with nested content (SourceContentResponse) and file (SourceFileResponse) — nullable file field
- [ ] Create `SourceContentResponse` Pydantic schema with fields: source_id, content_text
- [ ] Create `SourceFileResponse` Pydantic schema with fields: mime_type, size_bytes, original_filename
- [ ] Create `SourceListResponse` paginated envelope schema (items, total, page, page_size)

### Source Service (source/service.py)

- [ ] Implement `_get_memory_space_for_source()` helper — verify memory space exists, is not deleted, and user owns parent workspace
- [ ] Implement `create_note_source(db, memory_space_id, owner_id, data: SourceCreateNote)` — create Source (status=pending) + SourceContent in one transaction, return SourceEntity
- [ ] Implement `create_document_source(db, memory_space_id, owner_id, title, file)` — save file via storage_client, create Source + SourceFile + SourceContent (after parsing), return SourceEntity
- [ ] Implement `parse_document(file_path, mime_type) -> str` — extract plain text from PDF (pdfplumber), DOCX (python-docx), TXT; raise ValidationError on unsupported type
- [ ] Implement `chunk_source_content(db, source_id, content_text)` — split text into embedding chunks (~500-1000 tokens, ~4000 chars target, 10-20% overlap), create SourceChunk rows with correct start_offset/end_offset
- [ ] Implement `list_sources(db, memory_space_id, owner_id, page, page_size, source_type?, processing_status?)` — paginated list with optional filters, return (list[SourceEntity], total)
- [ ] Implement `get_source(db, source_id, owner_id)` — return SourceEntity with ownership check via memory space → workspace chain
- [ ] Implement `get_source_detail(db, source_id, owner_id)` — return source + content + file metadata for the detail endpoint
- [ ] Implement `get_source_content(db, source_id, owner_id)` — return just content_text for the /content endpoint
- [ ] Implement `delete_source(db, source_id, owner_id)` — cascade soft-delete source + content + file + chunks + record_source_links + embeddings (query embeddings by entity_type='source_chunk' AND entity_id IN chunk_ids)

### Source Router (source/router.py)

- [ ] `POST /memory-spaces/{id}/sources` — single endpoint inspecting content-type header: JSON body for notes, multipart form data for documents
- [ ] `GET /memory-spaces/{id}/sources` — list with pagination + source_type/processing_status filters
- [ ] `GET /sources/{id}` — return SourceDetailResponse with nested content and file
- [ ] `GET /sources/{id}/content` — return SourceContentResponse
- [ ] `DELETE /sources/{id}` — soft delete, return 204
- [ ] Register source router in main.py

### Chunking Logic

- [ ] Implement sentence boundary detection for chunk splitting (split on `. `, `? `, `! ` etc. with fallback to character boundary)
- [ ] Implement overlap logic — carry over 2-3 sentences from previous chunk
- [ ] Handle edge case: content shorter than chunk size → single chunk equal to full content
- [ ] Make chunk target size configurable via settings (CHUNK_TARGET_CHARS, CHUNK_OVERLAP_CHARS)

### Tests

- [ ] Test create_note_source — verify Source + SourceContent created with correct fields
- [ ] Test create_document_source — verify file stored, parsed, Source + SourceFile + SourceContent created
- [ ] Test parse_document — PDF, DOCX, TXT parsing, unsupported type error
- [ ] Test chunk_source_content — correct chunk count, offsets, overlap, single-chunk case
- [ ] Test list_sources — pagination, type filter, status filter
- [ ] Test get_source / get_source_detail — ownership check, 404 on missing
- [ ] Test delete_source — verify cascade soft-delete on all child entities
- [ ] Test source router endpoints — HTTP status codes, response shapes

---

## Track G: Memory Domain (Backend)

**Depends on:** Phase 1 backend (parallel with Track F)

### Domain Entities & Schemas (memory/models.py)

ORM models already exist. Need to add domain entities and Pydantic DTOs.

- [ ] Create `MemoryRecordEntity` dataclass with fields: id, memory_space_id, record_type, content, origin, status, confidence, importance, metadata, created_at, updated_at
- [ ] Create `MemoryRecordEntity.from_orm()` classmethod
- [ ] Create `RecordSourceLinkEntity` dataclass with fields: id, record_id, source_id, evidence_text, evidence_start_offset, evidence_end_offset, created_at
- [ ] Create `RecordSourceLinkEntity.from_orm()` classmethod
- [ ] Create `RecordCreate` Pydantic schema with fields: record_type, content, importance (optional, default "medium"), metadata (optional, default {}) — with enum validation
- [ ] Create `RecordUpdate` Pydantic schema with fields: content?, status?, importance?, metadata? — all optional, with enum validation
- [ ] Create `RecordResponse` Pydantic schema matching API contract (id, memory_space_id, record_type, content, origin, status, confidence, importance, metadata, created_at, updated_at)
- [ ] Create `RecordListResponse` paginated envelope schema
- [ ] Create `RecordSourceLinkResponse` Pydantic schema with fields: id, record_id, source_id, source_title, source_type, evidence_text, created_at — denormalized source fields

### Memory Service (memory/service.py)

- [ ] Implement `_get_memory_space_for_record()` helper — verify memory space ownership through workspace chain
- [ ] Implement `create_record(db, memory_space_id, owner_id, data: RecordCreate)` — create manual record with origin="manual", status="active", confidence=1.00, return RecordEntity
- [ ] Implement `bulk_create_records(db, memory_space_id, source_id, records: list[ExtractedRecord])` — persist multiple extracted records + record_source_links in one transaction; compute evidence offsets via string matching
- [ ] Implement `_compute_evidence_offsets(content_text, evidence_text)` — find evidence_text in source content, return (start_offset, end_offset) or (None, None) if not found
- [ ] Implement `list_records(db, memory_space_id, owner_id, page, page_size, record_type?, status?, importance?)` — paginated list with optional filters
- [ ] Implement `get_record(db, record_id, owner_id)` — return RecordEntity with ownership check via memory_space → workspace chain
- [ ] Implement `update_record(db, record_id, owner_id, data: RecordUpdate)` — partial update of content, status, importance, metadata; return updated RecordEntity (re-embedding deferred — accept stale embeddings for MVP)
- [ ] Implement `delete_record(db, record_id, owner_id)` — soft-delete record + record_source_links + embeddings
- [ ] Implement `get_record_sources(db, record_id, owner_id)` — return list of RecordSourceLinkResponse with denormalized source_title and source_type via join

### Memory Router (memory/router.py)

- [ ] `GET /memory-spaces/{id}/records` — list with pagination + record_type/status/importance filters
- [ ] `POST /memory-spaces/{id}/records` — create manual record, return 201
- [ ] `GET /records/{id}` — return RecordResponse
- [ ] `PATCH /records/{id}` — partial update, return RecordResponse
- [ ] `DELETE /records/{id}` — soft delete, return 204
- [ ] `GET /records/{id}/sources` — return provenance links with denormalized source info
- [ ] Register memory router in main.py

### Tests

- [ ] Test create_record — verify manual record created with origin="manual", confidence=1.00
- [ ] Test bulk_create_records — verify multiple records + links created, evidence offsets computed correctly
- [ ] Test _compute_evidence_offsets — exact match, substring match, not-found returns None
- [ ] Test list_records — pagination, each filter (type, status, importance), combined filters
- [ ] Test get_record — ownership check, 404 on missing/deleted
- [ ] Test update_record — partial update, status transition, importance change
- [ ] Test delete_record — verify cascade soft-delete on links + embeddings
- [ ] Test get_record_sources — correct denormalized fields, evidence text
- [ ] Test memory router endpoints — HTTP status codes, response shapes

---

## Track H: AI Service + Extraction Process (Backend)

**Depends on:** Tracks F + G (needs their service interfaces) + Track C (LLM client stubs from Phase 1)

### AI Domain Entities (ai/models.py)

ORM models (Embedding, GeneratedSummary) already exist. Need to add domain entities for AI outputs.

- [ ] Create `ExtractedRecord` dataclass with fields: record_type (str), content (str), confidence (float), importance (str), evidence_text (Optional[str])
- [ ] Create `ExtractionOutput` dataclass with field: records (list[ExtractedRecord])
- [ ] Create `SummaryResult` dataclass with fields: summary_type (str), title (str), content (str), record_ids_used (list[UUID])
- [ ] Create `Citation` dataclass with fields: record_id (Optional[UUID]), source_id (Optional[UUID]), excerpt (str)
- [ ] Create `QueryResult` dataclass with fields: answer (str), citations (list[Citation])
- [ ] Create `EmbeddingResult` dataclass with fields: entity_type (str), entity_id (UUID), embedding (list[float])

### LLM Client Implementation (integrations/llm_client.py)

- [ ] Initialize OpenAI client in `__init__` using `openai` SDK with stored api_key
- [ ] Implement `generate_embeddings(texts: list[str]) -> list[list[float]]` — call OpenAI `text-embedding-3-small`, batch at 100 texts per API call, return 1536-dim vectors
- [ ] Implement `extract(content: str, source_type: str, chunk_position: Optional[str] = None) -> dict` — call OpenAI chat completion with JSON response format, return parsed dict
- [ ] Implement `summarize(records: list[dict], summary_type: str) -> dict` — call OpenAI chat completion, return dict with title + content
- [ ] Implement `query(question: str, context: list[dict]) -> dict` — call OpenAI chat completion, return dict with answer + citations
- [ ] Add error handling: retry once on malformed JSON response, raise on timeout/API error
- [ ] Add `OPENAI_MODEL` to config settings (default: `gpt-4o-mini` or similar)
- [ ] Add `EMBEDDING_MODEL` to config settings (default: `text-embedding-3-small`)

### Extraction Prompt (ai/prompts/extraction.py)

- [ ] Define `EXTRACTION_PROMPT_VERSION = "extraction-v1"` constant
- [ ] Write base system prompt instructing LLM to extract discrete, atomic memory records from source text
- [ ] Include output JSON schema definition in prompt (records array with record_type, content, confidence, importance, evidence_text)
- [ ] Write record type definitions section — one clear description per type: fact, event, decision, issue, question, preference, task, insight
- [ ] Write confidence scoring guidelines section (0.90-1.00 explicit, 0.70-0.89 implied, 0.50-0.69 inferred, below 0.50 don't extract)
- [ ] Write importance scoring guidelines section (high: decisions/blockers/critical, medium: supporting context/default, low: background/minor)
- [ ] Write evidence extraction instructions (quote exact passage, keep concise, direct excerpt not paraphrase)
- [ ] Write source-type-specific instruction blocks — note (tolerate informal/shorthand), document (respect structure), transcript (find decisions/action items, attribute to speakers)
- [ ] Implement `build_extraction_prompt(content: str, source_type: str, chunk_position: Optional[str] = None) -> list[dict]` — assemble system + user messages with appropriate source-type block
- [ ] Add chunk position context to prompt when processing chunked content (e.g., "You are reading section 2 of 4")

### Summarization Prompt (ai/prompts/summarization.py)

- [ ] Define `SUMMARIZATION_PROMPT_VERSION = "summarization-v1"` constant
- [ ] Write base system prompt instructing LLM to synthesize memory records into coherent narrative markdown (not a raw list)
- [ ] Write one_pager type-specific instructions — comprehensive overview: key facts, decisions, open issues, current status; use section headings
- [ ] Write recent_updates type-specific instructions — focus on what changed recently: new decisions, resolved issues, new questions
- [ ] Include instructions for handling volume — summarize/group rather than enumerate when many records exist
- [ ] Include instructions to prioritize high-importance records (decisions, issues, tasks)
- [ ] Implement `build_summarization_prompt(records: list[dict], summary_type: str) -> list[dict]` — assemble system + user messages, format records for context

### Query/RAG Prompt (ai/prompts/query.py)

- [ ] Define `QUERY_PROMPT_VERSION = "query-v1"` constant
- [ ] Write system prompt instructing LLM to answer based ONLY on provided context (no hallucination)
- [ ] Include citation instructions — reference specific record IDs in the answer
- [ ] Include instruction to say "insufficient information" if context doesn't answer the question
- [ ] Include instruction to distinguish between curated records and raw source chunks in the answer
- [ ] Define output schema for answer + citations array (record_id, content excerpt)
- [ ] Implement `build_query_prompt(question: str, records: list[dict], chunks: list[dict]) -> list[dict]` — assemble system + user messages with retrieved context

### AI Service (ai/service.py)

- [ ] Implement `extract_from_content(content: str, source_type: str) -> ExtractionOutput` — build extraction prompt → call llm_client.extract → validate JSON against ExtractionOutput schema → return domain entity
- [ ] Implement extraction response validation — check each record has valid record_type, confidence 0-1, importance enum, non-empty content; discard invalid records, keep valid ones
- [ ] Implement `generate_embeddings(texts: list[str], entity_type: str, entity_ids: list[UUID]) -> list[EmbeddingResult]` — call llm_client.generate_embeddings (batched at 100 texts) → wrap in domain entities
- [ ] Implement `store_embeddings(db, results: list[EmbeddingResult])` — persist embedding rows to the embeddings table, handle upsert for re-embedding
- [ ] Implement `summarize_memory_space(db, memory_space_id: UUID, summary_type: str) -> SummaryResult` — query active records, filter/rank by importance + recency, build prompt, call LLM, return result
- [ ] Implement `query_memory_space(db, memory_space_id: UUID, question: str) -> QueryResult` — embed question → vector search memory_records → fallback to source_chunks → build RAG prompt → call LLM → return answer with citations
- [ ] Implement `_vector_search(db, memory_space_id, query_embedding, entity_type, top_k=10)` — cosine similarity search on embeddings table scoped to memory space

### Extraction Process (processes/extraction.py)

- [ ] Implement `run_extraction(db, source_id)` — orchestrator function that runs the full pipeline:
- [ ] Step 1: Read source content from SourceContent table
- [ ] Step 2: Update source processing_status to "processing"
- [ ] Step 3: Check if `len(content) > 24000` chars (approx ~6K tokens); if so, split into extraction chunks (transient, not stored)
- [ ] Step 4: For each extraction unit, call `ai_service.extract_from_content()`
- [ ] Step 5: Validate extraction output — if zero valid records from non-empty source, mark as failed
- [ ] Step 6: Persist extracted records via `memory_service.bulk_create_records()`
- [ ] Step 7: Create embedding chunks via `source_service.chunk_source_content()`
- [ ] Step 8: Generate embeddings for source_chunks via `ai_service.generate_embeddings()`
- [ ] Step 9: Generate embeddings for new memory_records via `ai_service.generate_embeddings()`
- [ ] Step 10: Store all embeddings via `ai_service.store_embeddings()`
- [ ] Step 11: Update source processing_status to "completed"
- [ ] Implement error handling: catch exceptions at each step, mark source as "failed" with processing_error message on any failure
- [ ] Implement retry logic: retry once on malformed LLM JSON response before failing

### Wire Extraction into Source Creation

- [ ] Call `run_extraction()` in a background thread (via `threading.Thread`) after source creation in source service (both note and document flows)
- [ ] Return source to caller immediately with status="pending" — extraction runs in background thread with its own DB session
- [ ] Handle extraction failure gracefully — source should still exist with status="failed", not roll back the source creation
- [ ] Ensure background thread creates its own SQLAlchemy session (not shared with request session)

### Integration Tests

- [ ] Test full extraction pipeline: create note source → verify records + chunks + embeddings created
- [ ] Test full extraction pipeline: create document source (TXT) → verify file stored + parsed + records + chunks + embeddings
- [ ] Test extraction failure handling: mock LLM returning malformed JSON → verify source marked as failed
- [ ] Test extraction with empty result: mock LLM returning empty records → verify source marked as completed with 0 records
- [ ] Test embedding generation: verify correct vectors stored for both source_chunks and memory_records

---

## Track I: Frontend Detail Page

**Depends on:** Frontend Phase 1 (workspace + memory space UI)

### Source Domain Types & API

- [ ] Create `source/types.ts` — interfaces: Source, SourceDetail, SourceContent, SourceFile, SourceCreateNote, SourceCreateDocument (matching API contract)
- [ ] Create `source/api.ts` — functions: listSources(memorySpaceId, filters?, pagination?), getSource(id), getSourceContent(id), createNoteSource(memorySpaceId, data), uploadDocumentSource(memorySpaceId, title, file), deleteSource(id)
- [ ] Create `source/hooks.ts` — TanStack Query hooks: useSources, useSource, useSourceContent, useCreateNoteSource, useUploadDocumentSource, useDeleteSource; with proper cache invalidation; useSources polls every 3s for up to 60s when any source has status pending/processing

### Source Components

- [ ] Create `source/components/source-list.tsx` — table/list displaying sources with type icon, title, processing status badge, created_at; includes "Add Source" button
- [ ] Create `source/components/source-card.tsx` — individual source row component with type icon, title, status badge (pending/processing/completed/failed with appropriate colors), timestamp
- [ ] Create `source/components/upload-dialog.tsx` — two-mode dialog: "Quick Note" tab (title + textarea) and "Upload Document" tab (title + file drag-and-drop); calls appropriate create mutation on submit
- [ ] Create `source/components/source-detail.tsx` — slide-over or expandable panel showing full source content text and file metadata; shows linked records count

### Memory Domain Types & API

- [ ] Create `memory/types.ts` — interfaces: MemoryRecord, RecordCreate, RecordUpdate, RecordSourceLink (matching API contract)
- [ ] Create `memory/api.ts` — functions: listRecords(memorySpaceId, filters?, pagination?), getRecord(id), createRecord(memorySpaceId, data), updateRecord(id, data), deleteRecord(id), getRecordSources(recordId)
- [ ] Create `memory/hooks.ts` — TanStack Query hooks: useRecords, useRecord, useCreateRecord, useUpdateRecord, useDeleteRecord, useRecordSources; with proper cache invalidation

### Memory Components

- [ ] Create `memory/components/record-list.tsx` — filterable list with filter controls for record_type, status, importance; paginated; includes "Add Record" button
- [ ] Create `memory/components/record-card.tsx` — displays content, type badge (colored by type), confidence score, importance badge, origin badge (extracted vs manual), provenance link
- [ ] Create `memory/components/record-edit-dialog.tsx` — modal form to edit content (textarea), status (dropdown), importance (dropdown), metadata (JSON editor or omit for MVP)
- [ ] Create `memory/components/record-create-dialog.tsx` — modal form for manual record creation: record_type (dropdown), content (textarea), importance (dropdown)
- [ ] Create `memory/components/record-provenance.tsx` — displays linked sources with evidence_text excerpts, source title, source type; links to source detail

### Memory Space Detail Page (Tabbed Layout)

- [ ] Replace placeholder cards in memory space detail page with tabbed interface using shadcn Tabs component
- [ ] Implement Sources tab — renders SourceList component with upload dialog
- [ ] Implement Records tab — renders RecordList component with filter controls and create/edit dialogs
- [ ] Implement Summary tab — placeholder with "Coming in Phase 3" message (summary generation + query bar are Phase 3 frontend)
- [ ] Sync active tab to URL query parameter (`?tab=sources`) for shareability
- [ ] Add source and record counts to tab labels (e.g., "Sources (5)", "Records (12)")

### MSW Mock Handlers

- [ ] Add source mock handlers — POST create (note + document), GET list (with filters), GET detail, GET content, DELETE
- [ ] Add memory record mock handlers — GET list (with filters), POST create, GET detail, PATCH update, DELETE, GET sources (provenance)
- [ ] Add seed data — 3-4 mock sources (mix of note and document) with processing statuses, 8-10 mock memory records (mix of types), 5-6 mock record-source links with evidence text
- [ ] Verify all mock handlers return shapes matching API contract

---

## Resolved Decisions

1. **Extraction threading:** Return immediately with status="pending", run extraction in a background `threading.Thread` with its own DB session.
2. **Content-type routing:** Single endpoint inspecting content-type header (JSON for notes, multipart for documents).
3. **Extraction threshold:** `len(content) > 24000` chars. No tiktoken dependency.
4. **Embedding batch size:** Batch at 100 texts per API call.
5. **Source deletion cascade to embeddings:** Query by `entity_type='source_chunk' AND entity_id IN (chunk_ids)`.
6. **Record re-embedding on edit:** Deferred — accept stale embeddings for MVP.
7. **Frontend polling:** Poll every 3s for up to 60s when any source has pending/processing status.

---

## Future Notes / Known Limitations

- **TODO:** Record content edits do not re-generate embeddings. Embeddings become stale after PATCH updates to record content. Revisit in Phase 3 or post-MVP — options: re-embed on edit, batch re-embed job, or mark embedding as stale.
- **TODO:** Add `reportlab` to test dependencies before Phase 3 integration testing so PDF parsing tests can generate test PDFs and run without skipping.
- **TODO:** The `embeddings` table has no `updated_at` column. When upserting embeddings, we overwrite `created_at` as a workaround. Add an `updated_at` column to the embeddings table in a future migration.
