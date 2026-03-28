import { http, HttpResponse } from "msw";
import { seedMemorySpaces, type MockMemorySpace } from "../seed-data";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

// In-memory store, seeded from seed-data
let memorySpaces: MockMemorySpace[] = [...seedMemorySpaces];

const ONE_PAGER_MARKDOWN = `## Overview

This engagement focuses on migrating the client's legacy Oracle 12c database infrastructure to PostgreSQL 15, targeting **99.9% uptime** during the transition period.

## Key Facts

- **Timeline:** 12-week engagement starting June 15
- **Budget:** $240k approved for Phase 1
- **Team:** 3 senior engineers + 1 DBA consultant
- **Stakeholders:** VP Engineering (sponsor), CTO (executive oversight)

## Current Status

The discovery phase is complete. Schema mapping is **80% done**, with stored procedure conversion identified as the primary risk area. A previous migration attempt failed 2 years ago due to PL/SQL incompatibilities.

## Open Risks

1. **Stored procedure compatibility** — 47 procedures use Oracle-specific PL/SQL features that have no direct PostgreSQL equivalent
2. **DBA availability** — Limited to 20 hrs/week during the cutover window
3. **Data volume** — 2.3TB of production data requires careful migration sequencing

## Next Steps

- Complete stored procedure audit by end of week 3
- Set up parallel-run environment for validation
- Schedule stakeholder review for Phase 1 checkpoint`;

const RECENT_UPDATES_MARKDOWN = `## Recent Updates

### March 25, 2026
- Completed schema mapping for the **orders** and **inventory** modules
- Identified 12 additional stored procedures requiring manual conversion

### March 22, 2026
- DBA consultant onboarded and granted access to staging environment
- Initial performance benchmarks show **15% improvement** on read queries with PostgreSQL

### March 19, 2026
- Kicked off Phase 1 with stakeholder alignment meeting
- Budget approval confirmed at $240k
- Risk register created and shared with engineering leadership`;

export function resetMemorySpaces(): void {
  memorySpaces = [...seedMemorySpaces];
}

function toResponse(ms: MockMemorySpace) {
  const { deleted_at: _, ...rest } = ms;
  return rest;
}

export const memorySpaceHandlers = [
  // POST /workspaces/:wId/memory-spaces
  http.post(`${BASE}/workspaces/:wId/memory-spaces`, async ({ params, request }) => {
    const body = (await request.json()) as { name?: string; description?: string };

    if (!body.name) {
      return HttpResponse.json(
        { error: { code: "validation_error", message: "Name is required" } },
        { status: 422 }
      );
    }

    const now = new Date().toISOString();
    const ms: MockMemorySpace = {
      id: crypto.randomUUID(),
      workspace_id: params.wId as string,
      name: body.name,
      description: body.description ?? "",
      status: "active",
      created_at: now,
      updated_at: now,
      deleted_at: null,
    };
    memorySpaces.push(ms);

    return HttpResponse.json(toResponse(ms), { status: 201 });
  }),

  // GET /workspaces/:wId/memory-spaces
  http.get(`${BASE}/workspaces/:wId/memory-spaces`, ({ params, request }) => {
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get("page") ?? "1", 10);
    const pageSize = parseInt(url.searchParams.get("page_size") ?? "20", 10);
    const statusFilter = url.searchParams.get("status");

    let active = memorySpaces.filter(
      (ms) => ms.workspace_id === params.wId && ms.deleted_at === null
    );

    if (statusFilter) {
      active = active.filter((ms) => ms.status === statusFilter);
    }

    const total = active.length;
    const start = (page - 1) * pageSize;
    const items = active.slice(start, start + pageSize).map(toResponse);

    return HttpResponse.json({ items, total, page, page_size: pageSize });
  }),

  // GET /memory-spaces/:id
  http.get(`${BASE}/memory-spaces/:id`, ({ params }) => {
    const ms = memorySpaces.find(
      (m) => m.id === params.id && m.deleted_at === null
    );

    if (!ms) {
      return HttpResponse.json(
        { error: { code: "not_found", message: "Memory space not found" } },
        { status: 404 }
      );
    }

    return HttpResponse.json(toResponse(ms));
  }),

  // PATCH /memory-spaces/:id
  http.patch(`${BASE}/memory-spaces/:id`, async ({ params, request }) => {
    const ms = memorySpaces.find(
      (m) => m.id === params.id && m.deleted_at === null
    );

    if (!ms) {
      return HttpResponse.json(
        { error: { code: "not_found", message: "Memory space not found" } },
        { status: 404 }
      );
    }

    const body = (await request.json()) as {
      name?: string;
      description?: string;
      status?: "active" | "archived";
    };

    if (body.status && !["active", "archived"].includes(body.status)) {
      return HttpResponse.json(
        { error: { code: "validation_error", message: "Status must be 'active' or 'archived'" } },
        { status: 422 }
      );
    }

    if (body.name !== undefined) ms.name = body.name;
    if (body.description !== undefined) ms.description = body.description;
    if (body.status !== undefined) ms.status = body.status;
    ms.updated_at = new Date().toISOString();

    return HttpResponse.json(toResponse(ms));
  }),

  // DELETE /memory-spaces/:id
  http.delete(`${BASE}/memory-spaces/:id`, ({ params }) => {
    const ms = memorySpaces.find(
      (m) => m.id === params.id && m.deleted_at === null
    );

    if (!ms) {
      return HttpResponse.json(
        { error: { code: "not_found", message: "Memory space not found" } },
        { status: 404 }
      );
    }

    ms.deleted_at = new Date().toISOString();

    return new HttpResponse(null, { status: 204 });
  }),

  // POST /memory-spaces/:id/summarize
  http.post(`${BASE}/memory-spaces/:id/summarize`, async ({ params, request }) => {
    const ms = memorySpaces.find(
      (m) => m.id === params.id && m.deleted_at === null
    );

    if (!ms) {
      return HttpResponse.json(
        { error: { code: "not_found", message: "Memory space not found" } },
        { status: 404 }
      );
    }

    const body = (await request.json()) as {
      summary_type?: string;
      regenerate?: boolean;
    };
    const summaryType = body.summary_type ?? "one_pager";
    const isOnePager = summaryType === "one_pager";

    const now = new Date().toISOString();
    return HttpResponse.json({
      id: crypto.randomUUID(),
      memory_space_id: params.id,
      summary_type: summaryType,
      title: isOnePager
        ? `${ms.name} — One-Pager`
        : `${ms.name} — Recent Updates`,
      content: isOnePager ? ONE_PAGER_MARKDOWN : RECENT_UPDATES_MARKDOWN,
      is_edited: false,
      edited_content: null,
      record_ids_used: [
        "rec-00000001-0000-0000-0000-000000000001",
        "rec-00000002-0000-0000-0000-000000000002",
        "rec-00000003-0000-0000-0000-000000000003",
      ],
      generated_at: now,
      created_at: now,
      updated_at: now,
    });
  }),

  // POST /memory-spaces/:id/query
  http.post(`${BASE}/memory-spaces/:id/query`, async ({ params, request }) => {
    const ms = memorySpaces.find(
      (m) => m.id === params.id && m.deleted_at === null
    );

    if (!ms) {
      return HttpResponse.json(
        { error: { code: "not_found", message: "Memory space not found" } },
        { status: 404 }
      );
    }

    const body = (await request.json()) as { question?: string };
    if (!body.question?.trim()) {
      return HttpResponse.json(
        { error: { code: "validation_error", message: "Question is required" } },
        { status: 422 }
      );
    }

    // Simulate LLM processing delay
    await new Promise((resolve) => setTimeout(resolve, 800));

    return HttpResponse.json({
      answer: `Based on the records in **${ms.name}**, here is what I found:\n\nThe engagement is a 12-week project starting June 15 with a budget of $240k for Phase 1. The primary objective is migrating from Oracle 12c to PostgreSQL 15 with 99.9% uptime.\n\n**Key risks** include stored procedure incompatibilities (a previous attempt failed 2 years ago) and limited DBA availability during the cutover window.`,
      citations: [
        {
          record_id: "rec-00000001-0000-0000-0000-000000000001",
          source_id: "src-00000001-0000-0000-0000-000000000001",
          chunk_id: null,
          excerpt:
            "Timeline: 12-week engagement starting June 15, budget approved at $240k for Phase 1",
        },
        {
          record_id: "rec-00000003-0000-0000-0000-000000000003",
          source_id: "src-00000002-0000-0000-0000-000000000002",
          chunk_id: null,
          excerpt:
            "Stored procedures use Oracle-specific PL/SQL features that have no direct PostgreSQL equivalent",
        },
      ],
    });
  }),
];
