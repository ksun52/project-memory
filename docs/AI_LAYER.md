# AI/LLM Layer Design

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

## 2. Extraction Pipeline

Transforms raw source content into structured memory records.

### Pipeline Steps

```
1. Receive source (content_text, source_type, source_id)
2. Pre-process: normalize whitespace, handle encoding issues
3. Decide: does content exceed extraction token threshold?
   - No  → use full text as single extraction unit
   - Yes → split into extraction chunks (see §5 Chunking Strategy)
4. For each extraction unit:
   a. Build extraction prompt (content + instructions + output schema)
   b. Call LLM → receive structured JSON response
   c. Validate response against expected schema
   d. On validation failure: retry once, then mark as failed
5. Store memory_records with origin='extracted', status='active'
6. Store record_source_links with evidence_text + computed offsets
7. Chunk content for embedding → store source_chunks
8. Generate embeddings for source_chunks + memory_records → store in embeddings
9. Update source.processing_status → 'completed'
```

### Input

| Field | Type | Description |
|-------|------|-------------|
| `source_id` | UUID | Reference to the source being processed |
| `content_text` | string | Full extracted/transcribed text from `source_contents` |
| `source_type` | enum | `note`, `document`, `transcript` — affects prompt behavior |

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

### LLM Response Schema

The LLM is instructed to return a JSON object matching this shape:

```json
{
  "records": [
    {
      "record_type": "decision",
      "content": "Team decided to use Postgres with pgvector for MVP",
      "confidence": 0.95,
      "importance": "high",
      "evidence_text": "We agreed to go with Postgres + pgvector to keep the stack simple"
    }
  ]
}
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

---

## 3. Extraction Prompt Requirements

The extraction prompt is not specified here, but must satisfy these requirements.

### Prompt Inputs

| Input | Purpose |
|-------|---------|
| Raw text (or extraction chunk) | The content to extract from |
| Source type | `note`, `document`, `transcript` — adjusts extraction heuristics |
| Chunk position (if chunked) | e.g., "section 2 of 4" — helps LLM understand it's seeing a fragment |
| Output schema | The JSON structure it must produce |
| Record type definitions | Clear, unambiguous descriptions of all 8 types |

### What the Prompt Must Instruct

**Record extraction:**
- Extract discrete, atomic memory records (one idea per record)
- Each record must be self-contained — readable without the original source
- Prefer specificity over vagueness
- Don't extract trivial or redundant information

**Classification — record type definitions the prompt needs:**

| Type | Prompt should describe as |
|------|---------------------------|
| `fact` | A piece of factual information — names, numbers, relationships, attributes |
| `event` | Something that happened or is scheduled — has a temporal quality |
| `decision` | A choice that was made — implies alternatives were considered |
| `issue` | A problem, concern, risk, or blocker |
| `question` | An open question, uncertainty, or unresolved point |
| `preference` | A stated preference, requirement, or constraint |
| `task` | An action item or to-do — implies someone should do something |
| `insight` | An observation, inference, or interpretation — goes beyond raw fact |

**Confidence scoring guidelines:**
- 0.90–1.00: Explicitly and unambiguously stated in the source
- 0.70–0.89: Strongly implied or stated with minor ambiguity
- 0.50–0.69: Inferred from context, reasonable but not certain
- Below 0.50: Speculative — generally should not be extracted

**Importance scoring guidelines:**
- `high`: Decisions, blockers, key stakeholders, critical deadlines, core requirements
- `medium`: Supporting facts, context, general updates (default)
- `low`: Background information, minor details, tangential mentions

**Evidence extraction:**
- Quote the specific passage that supports the record
- Keep evidence concise but sufficient to justify the record
- Evidence should be a direct excerpt, not a paraphrase

### Source-Type Variations

One base extraction prompt with a small source-type-specific instruction block:

| Source Type | Additional Instructions |
|-------------|------------------------|
| `note` | Freeform input — may contain mixed topics, shorthand, or fragments. Be tolerant of informal language. |
| `document` | Structured input — may have sections, headings, and formal language. Respect document structure in extraction. |
| `transcript` | Conversational input — look for decisions, action items, and disagreements. Attribute to speakers when identifiable. |

### Prompt Versioning

Track prompt versions as simple string identifiers (e.g., `extraction-v1`, `one-pager-v1`) stored alongside outputs:
- `generated_summaries.prompt_version` — already in data model
- `memory_records.metadata.prompt_version` — stored in the JSONB metadata field for extracted records

No prompt registry or database table needed in MVP. Version strings in a constants file are sufficient.

---

## 4. Summarization Pipeline

Generates one-pagers and recent update summaries from structured memory records.

### Pipeline Steps

```
1. Receive request (memory_space_id, summary_type)
2. Query memory_records (status='active') from the memory space
3. Filter/rank records:
   - one_pager: all active records, weighted by importance
   - recent_updates: records created/updated within time window
4. If too many records to fit in context, select by importance (high first) and recency
5. Build summarization prompt (records + type-specific instructions)
6. Call LLM → receive markdown output
7. Store in generated_summaries with record_ids_used, prompt_version, model_id
```

### Input

| Field | Type | Description |
|-------|------|-------------|
| `memory_space_id` | UUID | Which memory space to summarize |
| `summary_type` | enum | `one_pager` or `recent_updates` |
| `time_window` | duration (optional) | For `recent_updates` — how far back to look |

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

### Summarization Prompt Requirements

**What the prompt must instruct:**
- Synthesize records into a coherent narrative, not a raw list
- Output well-structured markdown with section headings
- Prioritize high-importance records (decisions, issues, tasks)
- Group related records logically
- Handle volume — if many records exist, summarize/group rather than enumerate

**Type-specific instructions:**

| Summary Type | Focus |
|-------------|-------|
| `one_pager` | Comprehensive project overview — key facts, decisions, open issues, current status |
| `recent_updates` | What changed recently — new decisions, resolved issues, new questions |

### Key Decisions

- Summaries are always regenerated fresh from current records (not incremental)
- Cached in `generated_summaries` — re-serve cached version until the user explicitly requests regeneration or records have changed
- One-pager format: structured sections (key facts, decisions, open questions, recent updates) — prompt-guided, output is freeform markdown

---

## 5. Chunking Strategy

There are two distinct chunking concerns with different purposes, sizes, and storage characteristics.

### Tier 1: Extraction Chunks (transient)

| Property | Value |
|----------|-------|
| **Purpose** | Fit content into LLM context window for extraction |
| **Size** | ~4K–8K tokens per chunk |
| **Overlap** | Minimal (1–2 sentences) |
| **Stored in DB?** | No — transient, used only during processing |
| **When used** | Only when source exceeds extraction threshold (~6K tokens) |

### Tier 2: Embedding Chunks (permanent)

| Property | Value |
|----------|-------|
| **Purpose** | Small, focused segments for precise semantic retrieval |
| **Size** | ~500–1000 tokens (~4000 chars) per chunk |
| **Overlap** | 10–20% (100–200 tokens / 2–3 sentences carried over) |
| **Stored in DB?** | Yes — `source_chunks` table |
| **When used** | Always created for every source |

### Extraction Approach: Full-Text First

For MVP, extraction runs on the full source text. Rationale:
- Most MVP sources (notes, short docs) will be well under the context window limit
- Full-text extraction produces better coherence and fewer duplicates
- Avoids the complexity of cross-chunk deduplication

If a source exceeds ~6K tokens, fall back to Tier 1 chunked extraction. The pipeline interface is the same either way — the extraction service accepts a list of text units and returns records.

### Chunking Implementation

Embedding chunks are split by:
1. Sentence boundaries (preferred) or paragraph boundaries
2. Target size of ~500–1000 tokens
3. Overlap of 10–20% (2–3 sentences carried over from previous chunk)
4. `start_offset` and `end_offset` recorded for each chunk (maps back to `source_contents.content_text`)

Chunk size is a configuration value, not hardcoded — allows tuning without code changes. Short content becomes a single chunk equal to the full content.

---

## 6. Query / RAG Pipeline

Answers natural language questions using memory records and source chunks.

### Pipeline Steps

```
1. Receive question (query_text, memory_space_id)
2. Embed the question
3. Search memory_record embeddings for semantic matches (top-K, start with K=10)
4. If insufficient results: also search source_chunk embeddings (RAG fallback)
5. Rank and filter retrieved context
6. Build query prompt (question + retrieved records/chunks)
7. Call LLM → generate answer with citations
```

### Input

| Field | Type | Description |
|-------|------|-------------|
| `query_text` | string | The user's natural language question |
| `memory_space_id` | UUID | Scopes retrieval to this memory space |

### Retrieval Strategy

Two-tier retrieval with memory records as the primary source:

1. **Primary:** Search `embeddings` where `entity_type = 'memory_record'` — returns structured, curated knowledge
2. **Fallback:** Search `embeddings` where `entity_type = 'source_chunk'` — returns raw source context for gaps in extracted records

Both searches are scoped to the memory space via joins.

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

### Query Prompt Requirements

**What the prompt must instruct:**
- Answer based **only** on the provided context (no hallucination)
- Cite which records or sources support the answer
- If context is insufficient, say so explicitly rather than guessing
- Distinguish between information from curated records vs raw source chunks

### Key Decisions

- Search memory records first (structured, distilled knowledge). Source chunks act as fallback for details not captured in records.
- If no relevant results found, the LLM should say so rather than hallucinate
- Citations are best-effort — LLM is asked to reference specific records, but strict citation accuracy is not enforced for MVP

---

## 7. Embedding Strategy

Generates vector embeddings for semantic search across memory records and source chunks.

### What Gets Embedded

| Entity | When | Purpose |
|--------|------|---------|
| `source_chunks` | During ingestion, after chunking | RAG fallback retrieval |
| `memory_records` | After extraction or manual creation/edit | Primary retrieval for query |

### Embedding Input

| Entity | Text Embedded |
|--------|---------------|
| `source_chunk` | `source_chunks.content` (the chunk text) |
| `memory_record` | `memory_records.content` (the concise summary) |

### Model

`text-embedding-3-small` (1536 dimensions) — fast, cost-effective, sufficient for MVP.

### When Embeddings Are Regenerated

- **Record edited:** Re-embed the updated memory record (replace the old embedding row)
- **Source re-processed:** Re-embed all affected source chunks
- **Record soft-deleted:** Soft-delete its embedding too
- **Model upgrade:** Re-embed all entities (supported by `model_id` column)

### Storage

Stored in the unified `embeddings` table with `entity_type` discriminator (`'memory_record'` or `'source_chunk'`).

---

## 8. Error Handling

| Scenario | Behavior |
|----------|----------|
| LLM returns malformed JSON | Retry once. If still invalid, mark source `processing_status = 'failed'` with `processing_error` populated |
| LLM returns empty records array | Valid — mark as `completed` with 0 records |
| LLM returns mix of valid and malformed records | Save valid records, log malformed ones. Mark as `completed` (partial success is still success) |
| Zero valid records from non-empty source | Mark as `failed` with `processing_error` populated |
| LLM call times out or errors | Mark as `failed` with error in `processing_error` |
| Embedding call fails | Mark as `failed` — embeddings are required |
| Partial extraction (some chunks succeed, some fail) | Mark as `failed` — no partial results for MVP |

---

## 9. Schema Validation

The AI output contracts map cleanly to the existing data model with no schema changes needed:

- `ExtractedRecord` → `memory_records` + `record_source_links` — all fields map 1:1
- `SummaryResult` → `generated_summaries` — all fields map 1:1
- `QueryResult` → API response only (not persisted)
- Embeddings → `embeddings` table — `entity_type`, `entity_id`, `embedding`, `model_id` all covered

---

## 10. Pipeline Summary

```
                          ┌─────────────────────────────────┐
                          │         SOURCE INPUT             │
                          │  (note / document / transcript)  │
                          └──────────────┬──────────────────┘
                                         │
                                         ▼
                          ┌─────────────────────────────────┐
                          │         PRE-PROCESS              │
                          │  normalize text, parse files     │
                          └──────────────┬──────────────────┘
                                         │
                          ┌──────────────┴──────────────┐
                          ▼                             ▼
                   ┌─────────────┐              ┌─────────────┐
                   │  < 6K tokens │              │ ≥ 6K tokens  │
                   │  full text   │              │ chunk for    │
                   │  extraction  │              │ extraction   │
                   └──────┬──────┘              └──────┬──────┘
                          │                             │
                          └──────────────┬──────────────┘
                                         │
                                         ▼
                          ┌─────────────────────────────────┐
                          │       LLM EXTRACTION             │
                          │  prompt + content → JSON records │
                          └──────────────┬──────────────────┘
                                         │
                                         ▼
                          ┌─────────────────────────────────┐
                          │       VALIDATE & STORE           │
                          │  memory_records                  │
                          │  record_source_links (+ offsets) │
                          └──────────────┬──────────────────┘
                                         │
                                         ▼
                          ┌─────────────────────────────────┐
                          │       CHUNK FOR EMBEDDING        │
                          │  500–1000 token chunks           │
                          │  → source_chunks table           │
                          └──────────────┬──────────────────┘
                                         │
                                         ▼
                          ┌─────────────────────────────────┐
                          │       GENERATE EMBEDDINGS        │
                          │  source_chunks + memory_records  │
                          │  → embeddings table              │
                          └──────────────┬──────────────────┘
                                         │
                                         ▼
                          ┌─────────────────────────────────┐
                          │       MARK COMPLETE              │
                          │  source.processing_status =      │
                          │  'completed'                     │
                          └─────────────────────────────────┘
```

---

## 11. MVP Design Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **Full-text extraction by default.** Fall back to chunked extraction only if source exceeds ~6K tokens. | Most MVP inputs fit within context windows. Full-text produces more coherent records with fewer duplicates. |
| 2 | **Cross-chunk deduplication deferred** to post-MVP. | Full-text extraction avoids the problem for most cases. Accept minor duplication for large docs; users can manually archive duplicates. |
| 3 | **Evidence offsets computed via string matching**, not requested from LLM. | LLMs are unreliable at character offset calculation. String matching is deterministic. If exact string isn't found (LLM slightly paraphrased), offsets are left null. |
| 4 | **One base extraction prompt + swappable type block** per `source_type`. | Keeps prompt management simple while allowing type-aware behavior. |
| 5 | **Prompt versioning via simple string identifiers** (e.g., `extraction-v1`). | No prompt registry needed for MVP. Version strings in a constants file are sufficient. |
| 6 | **Partial extraction success is still success.** Save valid records, log malformed ones. | Partial results are better than no results. Malformed records are logged for debugging but don't block the pipeline. |

---

## 12. Future Considerations

| Area | What to Revisit |
|------|-----------------|
| Cross-chunk deduplication | Embedding similarity or LLM comparison to detect duplicate records from overlapping chunks |
| Contradiction detection | Compare new records against existing ones for conflicting information |
| Confidence recalibration | Adjust confidence scores based on user feedback (edits, deletions) |
| Streaming | Stream extraction records and query answers to frontend as they're generated |
| Prompt optimization | A/B test prompt variants using `prompt_version` tracking |
| Embedding model upgrades | Re-embed all entities when switching models (supported by `model_id` column) |
| Smarter chunking | Semantic chunking (split by topic/paragraph) instead of fixed-size |
| Re-extraction | Re-run extraction on existing sources with updated prompts; handle record replacement |
