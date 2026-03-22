# Architecture Overview (MVP)

**Product:** Project Memory  
**Version:** v0.1 (MVP)  
**Status:** Draft

---

## 1. Frontend

### What We Need
- Create and manage **workspaces**
- Create and manage **memory spaces** (projects) within workspaces
- **Upload/input context** (notes, docs, pasted text)
- **Browse and search** memory records
- **View and edit** individual memory records
- **Generate one-pager** summaries
- **Query memory** via natural language (persistent query bar)
- View **source provenance** (trace records back to original input)

### Decisions
- **Framework:** Next.js 14+ (App Router)
- **UI Components:** shadcn/ui (Radix-based, copied into codebase)
- **Styling:** Tailwind CSS
- **Server State:** TanStack Query (React Query)
- **Client State:** React Context (auth only — no global state library for MVP)
- **Forms:** React Hook Form + Zod
- **Mocking:** MSW (Mock Service Worker) for parallel development
- **Detailed Frontend Plan:** See [FRONTEND.md](./FRONTEND.md)

### API Contract
- **OpenAPI Spec:** [`docs/api/openapi.yaml`](./api/openapi.yaml) (source of truth)
- **Human-Readable:** [`docs/API_CONTRACT.md`](./API_CONTRACT.md)
- Frontend and backend develop in parallel against this shared contract

---

## 2. Backend

### What We Need
- Single **monolithic server** (keep it simple for MVP)
- **REST APIs** to handle all frontend requests
- **Asset upload handling** (documents, files)
- **AI service layer** — make requests to LLM with documents/context, get structured output back
- **Background processing** for extraction (may not need to be async in MVP if inputs are small)

### Decisions
- **Runtime/Framework:** Python 3.12+ / FastAPI / SQLAlchemy 2.0
- **File Upload Strategy:** S3-compatible storage (local filesystem for dev)
- **Auth Approach:** WorkOS SSO + JWT tokens
- **Detailed Backend Plan:** See [BACKEND.md](./BACKEND.md)

---

## 3. Database & Storage

### What We Need
- **Relational database** for core entities (workspaces, memory spaces, sources, memory records)
- **Blob/file storage** for uploaded documents
- **Vector storage** for embeddings (for semantic search / RAG fallback)
  - Could be same DB with vector extension (e.g., pgvector) or separate

### Decisions
- **Primary DB:** PostgreSQL
- **Vector DB:** pgvector (extension on same Postgres instance)
- **File Storage:** S3-compatible (local filesystem for dev, S3 for prod)

---

## 4. Data Model

### Core Entities Needed

| Entity | Purpose |
|--------|---------|
| **Workspace** | Top-level container for a user/team |
| **Memory Space** | Scoped container for a project/client/topic within a workspace |
| **Source** | Raw input (note, doc, transcript, pasted text) |
| **Memory Record** | Normalized, structured unit of context extracted from sources |
| **Record-Source Link** | Many-to-many relationship linking records to their source(s) with optional evidence span |
| **Record Attributes** (optional) | Flexible key-value metadata on records |
| **User** | Basic user identity (can be simple for MVP) |

### Key Design Principles
- **Generic schema** — memory records use broad types (fact, event, decision, issue, question, preference, task, insight) rather than domain-specific tables
- **Strong provenance** — every record links back to source(s)
- **Flexible metadata** — optional JSON attributes for additional structure without rigid schema
- **Status tracking** — records have lifecycle (active, tentative, outdated, archived)

---

## 5. AI/LLM Layer

### What We Need
- **Extraction pipeline** — take raw source input, extract structured memory records
- **Summarization** — generate one-pagers from current memory records
- **Query/retrieval** — answer natural language questions using memory records (+ RAG fallback to sources)
- **Embedding generation** — create embeddings for semantic search

### High-Level Flow
```
Source Input → LLM Extraction → Memory Records → Storage
                                      ↓
User Query → Structured Query (memory records) + RAG fallback (sources) → LLM → Response
                                      ↓
One-Pager Request → Filter/rank memory records → LLM Summarization → Output
```

### Decisions
- **LLM Provider:** TBD (OpenAI or Anthropic)
- **Embedding Model:** OpenAI text-embedding-3-small (tentative)
- **Prompt Management:** Versioned prompt templates in code (`app/domains/ai/prompts/`)
- **Detailed AI Pipeline Plan:** See [AI_LAYER.md](./AI_LAYER.md)

---

## 6. Ingestion & Processing

### What We Need
- Accept **text input** (paste, typed notes)
- Accept **document upload** (PDF, DOCX, TXT for MVP)
- **Parse/extract text** from documents
- **Chunking strategy** for large documents (for extraction and embedding)
- Pipeline: `Upload → Parse → Extract → Store Records`

### Decisions
- **Supported formats (MVP):** PDF, DOCX, TXT
- **Parsing libraries:** pdfplumber (PDF), python-docx (DOCX)
- **Chunking approach:** Overlapping fixed-size chunks (details TBD during implementation)

---

## 7. Infrastructure & Deployment

### What We Need (MVP)
- Simple deployment (single server + database)
- Local development environment
- Basic CI/CD for deploys
- Environment separation (dev, prod at minimum)

### Decisions
- **Hosting:** TBD (Vercel, Railway, Fly.io, AWS, etc.)
- **Database hosting:** TBD
- **File storage hosting:** TBD

---

## 8. Security & Access (MVP Scope)

### What We Need
- Basic **user authentication**
- **Data isolation** between workspaces
- **HTTPS** in production
- Don't store sensitive secrets in code

### Not in MVP
- Complex RBAC / team permissions
- Audit logging
- Encryption at rest (beyond DB defaults)

---

## Key Decisions

### User Model
- **Decision:** Design schema for multi-user, implement single-user for MVP
- **Rationale:** Every entity already scoped by `workspace_id`. Workspace has `owner_id` for now. Later, add `workspace_members` join table for multi-user support. This avoids retrofitting the data model later.

### Extraction UX Flow
- **Decision:** User confirms upload → backend creates source + records (no pending state on backend)
- **Flow:**
  1. User selects file / pastes text
  2. Frontend shows preview
  3. User clicks "Confirm Upload"
  4. Backend receives source → stores it → triggers extraction → creates records
  5. Frontend displays created records
- **Note:** Frontend should not pre-create records — only show local preview/placeholder until confirmation, then fetch real data.

### Sync vs Async Extraction
- **Decision:** Start with synchronous extraction, design as swappable service for future async
- **Pattern:**
  - Wrap extraction logic in a service function callable either inline or by a worker
  - Sync (MVP): `POST /sources → parse → extract → save records → return response`
  - Async (future): `POST /sources → save source → enqueue job → return status` + worker processes
- **Option:** Implement simple job queue early for learning purposes (DB-backed queue with polling worker)

### Soft Delete
- **Decision:** All entities (except `users`) use soft delete via nullable `deleted_at` timestamp
- **Behavior:**
  - All queries filter `WHERE deleted_at IS NULL` by default
  - Soft-deleting a parent cascades to children (e.g., source → content, chunks, files, links, embeddings)
  - `users` table does not use soft delete — account deactivation handled separately
- **Rationale:** Preserves audit trail and provenance. Aligns with the system's focus on traceability.

---

## Open Questions

1. **Real-time updates?** Or simple refresh-based UI for MVP?
2. **Voice input in MVP?** Or defer to V2?

---

## Next Steps

- [x] Finalize technology choices for each layer
- [x] Design detailed data model schema
- [x] Plan backend architecture — see [BACKEND.md](./BACKEND.md)
- [x] Plan frontend architecture — see [FRONTEND.md](./FRONTEND.md)
- [x] Define API contract — see [API_CONTRACT.md](./API_CONTRACT.md) and [openapi.yaml](./api/openapi.yaml)
- [x] Design AI/LLM pipeline (high level) — see [AI_LAYER.md](./AI_LAYER.md)
- [ ] Design extraction prompts (detailed)
- [ ] Create example memory records across domains to validate schema
- [ ] Wireframe key user flows
- [ ] Set up project scaffolding — backend (FastAPI + SQLAlchemy + Alembic) and frontend (Next.js + shadcn/ui)
