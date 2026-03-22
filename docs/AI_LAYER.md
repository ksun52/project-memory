# AI/LLM Layer Design

**Product:** Project Memory  
**Version:** v0.1 (MVP)  
**Status:** Draft

---

## Overview

This document describes the design of the AI/LLM layer for Project Memory. It covers the four core AI capabilities — extraction, summarization, query/RAG, and embedding — detailing the pipeline shape, input/output contracts, chunking strategy, prompt requirements, and MVP defaults for key design decisions.

---

## 1. Extraction Pipeline

The extraction pipeline transforms raw source content into structured memory records.

### Pipeline Steps

```
1. Receive source (content_text, source_type, source_id)
2. Pre-process: normalize whitespace, handle encoding issues
3. Decide: does content exceed extraction token threshold?
   - No  → use full text as single extraction unit
   - Yes → split into extraction chunks (see §3 Chunking Strategy)
4. For each extraction unit:
   a. Build extraction prompt (content + instructions + output schema)
   b. Call LLM → receive structured JSON response
   c. Validate response against expected schema
   d. On validation failure: save valid records, log malformed ones (see §7.6)
5. If chunked: merge + deduplicate records across chunks (future — see §7.2)
6. Store memory_records with origin='extracted', status='active'
7. Store record_source_links with evidence_text + computed offsets
8. Chunk content for embedding → store source_chunks
9. Generate embeddings for source_chunks + memory_records → store in embeddings
10. Update source.processing_status → 'completed'
```

### Input

| Field | Type | Description |
|-------|------|-------------|
| `source_id` | UUID | Reference to the source being processed |
| `content_text` | string | Full extracted/transcribed text from `source_contents` |
| `source_type` | enum | `note`, `document`, `transcript` — affects prompt behavior |

### Output (per record)

| Field | Type | Maps to |
|-------|------|---------|
| `record_type` | enum | `memory_records.record_type` |
| `content` | string | `memory_records.content` |
| `confidence` | float (0.00–1.00) | `memory_records.confidence` |
| `importance` | enum | `memory_records.importance` |
| `evidence_text` | string | `record_source_links.evidence_text` |

Evidence offsets (`evidence_start_offset`, `evidence_end_offset`) are computed by the application via string matching against `source_contents.content_text`, not requested from the LLM.

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

---

## 2. Extraction Prompt Requirements

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

---

## 3. Chunking Strategy

There are two distinct chunking concerns with different purposes, sizes, and storage characteristics.

### Tier 1: Extraction Chunks (transient)

| Property | Value |
|----------|-------|
| **Purpose** | Fit content into LLM context window for extraction |
| **Size** | ~4K–8K tokens per chunk |
| **Overlap** | Minimal (1–2 sentences) |
| **Stored in DB?** | No — transient, used only during processing |
| **When used** | Only when source exceeds extraction threshold |

### Tier 2: Embedding Chunks (permanent)

| Property | Value |
|----------|-------|
| **Purpose** | Small, focused segments for precise semantic retrieval |
| **Size** | ~500–1000 tokens per chunk |
| **Overlap** | 10–20% (preserves context at boundaries) |
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
4. Build summarization prompt (records + type-specific instructions)
5. Call LLM → receive markdown output
6. Store in generated_summaries with record_ids_used, prompt_version, model_id
```

### Input

| Field | Type | Description |
|-------|------|-------------|
| `memory_space_id` | UUID | Which memory space to summarize |
| `summary_type` | enum | `one_pager` or `recent_updates` |
| `time_window` | duration (optional) | For `recent_updates` — how far back to look |

### Memory Records Passed to Prompt

Each record is provided as a structured object:

```json
{
  "record_type": "decision",
  "content": "Team decided to use Postgres with pgvector",
  "importance": "high",
  "created_at": "2026-03-15T10:30:00Z"
}
```

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

### Output

| Field | Stored in |
|-------|-----------|
| Markdown content | `generated_summaries.content` |
| Record IDs used | `generated_summaries.record_ids_used` |
| Prompt version | `generated_summaries.prompt_version` |
| Model ID | `generated_summaries.model_id` |

---

## 5. Query/RAG Pipeline

Answers natural language questions using memory records and source chunks.

### Pipeline Steps

```
1. Receive question (query_text, memory_space_id)
2. Embed the question
3. Search memory_record embeddings for semantic matches (top-K)
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

### Query Prompt Requirements

**What the prompt must instruct:**
- Answer based **only** on the provided context (no hallucination)
- Cite which records or sources support the answer
- If context is insufficient, say so explicitly rather than guessing
- Distinguish between information from curated records vs raw source chunks

### Output

The response is returned directly to the user (not stored). It includes:
- The answer text
- Citations referencing specific memory records or sources

---

## 6. Embedding Pipeline

Generates vector embeddings for semantic search across memory records and source chunks.

### What Gets Embedded

| Entity | When | Stored as |
|--------|------|-----------|
| `source_chunks` | During ingestion, after chunking | `entity_type = 'source_chunk'` |
| `memory_records` | After extraction or manual creation | `entity_type = 'memory_record'` |

### When Embeddings Are Regenerated

- **Record edited:** Re-embed the updated memory record
- **Source re-processed:** Re-embed all affected source chunks
- **Model upgrade:** Re-embed all entities (supported by `model_id` column)

### Embedding Input

| Entity | Text Embedded |
|--------|---------------|
| `source_chunk` | `source_chunks.content` (the chunk text) |
| `memory_record` | `memory_records.content` (the concise summary) |

---

## 7. MVP Design Decisions

### 7.1 Extraction: Full-Text by Default

- **Decision:** Use full-text extraction for MVP. Fall back to chunked extraction only if a source exceeds ~6K tokens.
- **Rationale:** Most MVP inputs (notes, short docs, transcripts) fit within modern LLM context windows. Full-text extraction produces more coherent records with fewer duplicates.

### 7.2 Cross-Chunk Deduplication: Deferred

- **Decision:** Defer cross-chunk deduplication to post-MVP.
- **Rationale:** Full-text extraction avoids this problem for most cases. When chunked extraction is needed (large docs), accept minor duplication for now. Users can manually archive duplicate records.

### 7.3 Evidence Offsets: Computed via String Matching

- **Decision:** The LLM returns `evidence_text` only. The application computes `evidence_start_offset` and `evidence_end_offset` by finding the evidence string within `source_contents.content_text`.
- **Rationale:** LLMs are unreliable at character offset calculation. String matching is deterministic and verifiable. If the exact string isn't found (LLM slightly paraphrased), offsets are left null.

### 7.4 Source-Type-Specific Prompts: One Base + Type Block

- **Decision:** One base extraction prompt with a small, swappable instruction block per `source_type`.
- **Rationale:** Keeps prompt management simple while allowing type-aware behavior. The base prompt handles schema, types, and quality guidelines. The type block adds 2–3 sentences of source-specific guidance.

### 7.5 Prompt Versioning: Simple String Identifiers

- **Decision:** Track prompt versions as simple string identifiers (e.g., `extraction-v1`, `one-pager-v1`) stored alongside outputs.
- **Where tracked:**
  - `generated_summaries.prompt_version` — already in data model
  - `memory_records.metadata.prompt_version` — stored in the JSONB metadata field for extracted records
- **Rationale:** No need for a prompt registry or database table in MVP. Version strings in a constants file are sufficient. Enables debugging and comparison without infrastructure overhead.

### 7.6 Error Handling: Save Valid, Log Malformed

- **Decision:** If the LLM returns a mix of valid and malformed records, save the valid ones and log the malformed ones. Don't retry individual records.
- **Status logic:**
  - All records valid → `processing_status = 'completed'`
  - Some valid, some malformed → `processing_status = 'completed'` (partial success is still success)
  - Zero valid records or total LLM failure → `processing_status = 'failed'` with `processing_error` populated
- **Rationale:** Partial results are better than no results. Malformed records are logged for debugging but don't block the pipeline.

---

## Pipeline Summary

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

## Open for Post-MVP

| Area | What to Revisit |
|------|-----------------|
| Cross-chunk deduplication | Embedding similarity or LLM comparison to detect duplicate records from chunked extraction |
| Contradiction detection | Compare new records against existing ones for conflicting information |
| Confidence recalibration | Adjust confidence scores based on user feedback (edits, deletions) |
| Streaming extraction | Stream records to frontend as they're extracted rather than waiting for full completion |
| Prompt optimization | A/B test prompt variants using `prompt_version` tracking |
| Embedding model upgrades | Re-embed all entities when switching models (supported by `model_id` column) |
