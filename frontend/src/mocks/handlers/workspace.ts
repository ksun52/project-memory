import { http, HttpResponse } from "msw";
import { seedWorkspaces, DEV_USER, type MockWorkspace } from "../seed-data";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

// In-memory store, seeded from seed-data
let workspaces: MockWorkspace[] = [...seedWorkspaces];

export function resetWorkspaces(): void {
  workspaces = [...seedWorkspaces];
}

function toResponse(ws: MockWorkspace) {
  const { deleted_at: _, ...rest } = ws;
  return rest;
}

export const workspaceHandlers = [
  // POST /workspaces
  http.post(`${BASE}/workspaces`, async ({ request }) => {
    const body = (await request.json()) as { name?: string; description?: string };

    if (!body.name) {
      return HttpResponse.json(
        { error: { code: "validation_error", message: "Name is required" } },
        { status: 422 }
      );
    }

    const now = new Date().toISOString();
    const ws: MockWorkspace = {
      id: crypto.randomUUID(),
      owner_id: DEV_USER.id,
      name: body.name,
      description: body.description ?? "",
      created_at: now,
      updated_at: now,
      deleted_at: null,
    };
    workspaces.push(ws);

    return HttpResponse.json(toResponse(ws), { status: 201 });
  }),

  // GET /workspaces
  http.get(`${BASE}/workspaces`, ({ request }) => {
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get("page") ?? "1", 10);
    const pageSize = parseInt(url.searchParams.get("page_size") ?? "20", 10);

    const active = workspaces.filter((ws) => ws.deleted_at === null);
    const total = active.length;
    const start = (page - 1) * pageSize;
    const items = active.slice(start, start + pageSize).map(toResponse);

    return HttpResponse.json({ items, total, page, page_size: pageSize });
  }),

  // GET /workspaces/:id
  http.get(`${BASE}/workspaces/:id`, ({ params }) => {
    const ws = workspaces.find(
      (w) => w.id === params.id && w.deleted_at === null
    );

    if (!ws) {
      return HttpResponse.json(
        { error: { code: "not_found", message: "Workspace not found" } },
        { status: 404 }
      );
    }

    return HttpResponse.json(toResponse(ws));
  }),

  // PATCH /workspaces/:id
  http.patch(`${BASE}/workspaces/:id`, async ({ params, request }) => {
    const ws = workspaces.find(
      (w) => w.id === params.id && w.deleted_at === null
    );

    if (!ws) {
      return HttpResponse.json(
        { error: { code: "not_found", message: "Workspace not found" } },
        { status: 404 }
      );
    }

    const body = (await request.json()) as {
      name?: string;
      description?: string;
    };

    if (body.name !== undefined) ws.name = body.name;
    if (body.description !== undefined) ws.description = body.description;
    ws.updated_at = new Date().toISOString();

    return HttpResponse.json(toResponse(ws));
  }),

  // DELETE /workspaces/:id
  http.delete(`${BASE}/workspaces/:id`, ({ params }) => {
    const ws = workspaces.find(
      (w) => w.id === params.id && w.deleted_at === null
    );

    if (!ws) {
      return HttpResponse.json(
        { error: { code: "not_found", message: "Workspace not found" } },
        { status: 404 }
      );
    }

    ws.deleted_at = new Date().toISOString();

    return new HttpResponse(null, { status: 204 });
  }),
];
