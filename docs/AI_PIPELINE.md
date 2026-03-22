# AI/LLM Pipeline Design

**Product:** Project Memory  
**Version:** v0.1 (MVP)  
**Status:** Draft

---

## 1. Overview

The AI layer provides four capabilities, all exposed as internal services with no API routes:

| Capability | Purpose |
|-----------|---------|
| **Extraction** | Convert raw source content into structured memory records |
| **Summarization** | Generate one-pagers and recent update summaries from memory records |
| **Query / RAG** | Answer natural language questions using memory records + source chunks |
| **Embedding** | Generate vector embeddings for retrieval |

---

## 2. Extraction

### Input

Source content text (from `source_contents.content_text`).

### Approach

- **Short content** (fits within context window): send full text as a single LLM call
- **Long content**: extract per-chunk, each chunk gets its own LLM call. Records from all chunks are collected into one `ExtractionOutput`
- LLM is instructed to return structured JSON — an array of extracted records
- Use JSON mode (OpenAI and Anthropic both support this). Validate response against a Pydantic schema.

### Output Entity

```python
@dataclass
class ExtractedRecord:
    record_type: str            # fact | event | decision | issue | question | preference | task | insight
    content: str                # concise summary of the memory
    confidence: float           # 0.0–1.0, LLM's self-assessed certainty
    importance: str             # low | medium | high
    evidence_text: str | None   # exact excerpt from source supporting this record

@dataclass
class ExtractionOutput:
    records: list[ExtractedRecord]
```

### Mapping to Data Model

| Entity field | Stored in | Notes |
|-------------|-----------|-------|
| `record_type` | `memory_records.record_type` | Direct map |
| `content` | `memory_records.content` | Direct map |
| `confidence` | `memory_records.confidence` | Direct map |
| `importance` | `memory_records.importance` | Direct map |
| `evidence_text` | `record_source_links.evidence_text` | Direct map |
| Evidence offsets | `record_source_links.evidence_start_offset`, `evidence_end_offset` | Computed by backend via string matching — not from LLM |
| Origin | `memory_records.origin` | Always `extracted` |
| Status | `memory_records.status` | Always `active` — confidence score conveys uncertainty |

### Key Decisions

- Extracted records start as `status = 'active'` — the confidence score is the uncertainty signal
- Evidence offset computation is backend logic, not LLM responsibility
- If validation fails on LLM response, retry once, then mark extraction as `failed`

---

## 3. Summarization

### Input

Active memory records from a memory space + a summary type (`one_pager` or `recent_updates`).

### Approach

- **One-pager**: query all active records in the memory space
- **Recent updates**: filter records created within a recent time window
- If too many records to fit in context, select by importance (high first) and recency
- Format records as structured context for the LLM
- LLM generates a markdown summary

### Output Entity

```python
@dataclass
class SummaryResult:
    summary_type: str            # one_pager | recent_updates
    title: str                   # generated title
    content: str                 # markdown body
    record_ids_used: list[UUID]  # which records contributed
```

### Mapping to Data Model

Directly persisted into `generated_summaries` table. `model_id` and `prompt_version` are added by the AI service at persistence time. `record_ids_used` enables the future "regenerate" feature (detect if records have changed since last summary).

### Key Decisions

- Summaries are always regenerated fresh from current records (not incremental)
- Cached in `generated_summaries` — re-serve cached version until the user explicitly requests regeneration or records have changed
- One-pager format: structured sections (key facts, decisions, open questions, recent updates) — prompt-guided, output is freeform markdown

---

## 4. Query / RAG

### Input

A natural language question + the memory space ID.

### Approach

1. Embed the question using the embedding model
2. Vector search against `memory_record` embeddings (primary) and `source_chunk` embeddings (fallback)
3. Retrieve top-K results (start with K=10)
4. Assemble retrieved records/chunks as context
5. Send question + context to LLM
6. LLM returns an answer with references to which records/sources it used

### Output Entity

```python
@dataclass
class Citation:
    record_id: UUID | None    # if citing a memory record
    source_id: UUID | None    # if citing a source chunk directly
    excerpt: str              # relevant snippet

@dataclass
class QueryResult:
    answer: str               # markdown
    citations: list[Citation]
```

### Mapping to Data Model

Query results are **not persisted** — they are returned directly via the API. Citations reference existing `record_id` and `source_id` values that the frontend can use for provenance links.

### Key Decisions

- Search memory records first (structured, distilled knowledge). Source chunks act as fallback for details not captured in records.
- If no relevant results found, the LLM should say so rather than hallucinate
- Citations are best-effort — LLM is asked to reference specific records, but strict citation accuracy is not enforced for MVP

---

## 5. Embedding Strategy

### What Gets Embedded

| Entity | When | Purpose |
|--------|------|---------|
| Source chunks | During extraction process, after chunking | RAG fallback retrieval |
| Memory records | After extraction creates them + after manual creation/edit | Primary retrieval for query |

### Model

`text-embedding-3-small` (1536 dimensions) — fast, cost-effective, sufficient for MVP.

### Key Decisions

- When a record is edited, re-embed it (replace the old embedding row)
- When a record is soft-deleted, soft-delete its embedding too
- Stored in the unified `embeddings` table with `entity_type` discriminator

---

## 6. Chunking Strategy

### Approach

Fixed-size with overlap.

| Parameter | Value | Notes |
|-----------|-------|-------|
| Chunk size | ~1000 tokens (~4000 chars) | Starting point, tunable |
| Overlap | ~10–20% (100–200 tokens) | Preserves context at boundaries |
| Short content | Single chunk = full content | Simplifies downstream logic |

### Key Decisions

- Chunks are always created, even for short content (already decided in data model)
- Boundaries tracked via `start_offset` / `end_offset` in `source_chunks`
- Chunk size is a configuration value, not hardcoded — allows tuning without code changes

---

## 7. Error Handling

| Scenario | Behavior |
|----------|----------|
| LLM returns malformed JSON | Retry once. If still invalid, mark source `processing_status = 'failed'` |
| LLM returns empty records array | Valid — mark as `completed` with 0 records |
| LLM call times out or errors | Mark as `failed` with error in `processing_error` |
| Embedding call fails | Mark as `failed` — embeddings are required |
| Partial extraction (some chunks succeed, some fail) | Mark as `failed` — no partial results for MVP |

---

## 8. Schema Validation

The AI output contracts map cleanly to the existing data model with no schema changes needed:

- `ExtractedRecord` → `memory_records` + `record_source_links` — all fields map 1:1
- `SummaryResult` → `generated_summaries` — all fields map 1:1
- `QueryResult` → API response only (not persisted)
- Embeddings → `embeddings` table — `entity_type`, `entity_id`, `embedding`, `model_id` all covered

---

## 9. Future Considerations

| Feature | Approach |
|---------|----------|
| Smarter chunking | Semantic chunking (split by topic/paragraph) instead of fixed-size |
| Multi-chunk deduplication | Post-extraction step to merge similar records extracted from overlapping chunks |
| Streaming responses | Stream query answers and summary generation to the frontend |
| Prompt versioning | Track which prompt version produced each extraction/summary for A/B comparison |
| Re-extraction | Re-run extraction on existing sources with updated prompts; handle record replacement |
