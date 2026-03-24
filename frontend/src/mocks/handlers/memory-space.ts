import { http, HttpResponse } from "msw";
import { seedMemorySpaces, type MockMemorySpace } from "../seed-data";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

// In-memory store, seeded from seed-data
let memorySpaces: MockMemorySpace[] = [...seedMemorySpaces];

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

  // POST /memory-spaces/:id/summarize — stub 501
  http.post(`${BASE}/memory-spaces/:id/summarize`, () => {
    return HttpResponse.json(
      { error: { code: "not_implemented", message: "Summarization not yet available" } },
      { status: 501 }
    );
  }),

  // POST /memory-spaces/:id/query — stub 501
  http.post(`${BASE}/memory-spaces/:id/query`, () => {
    return HttpResponse.json(
      { error: { code: "not_implemented", message: "Query not yet available" } },
      { status: 501 }
    );
  }),
];
