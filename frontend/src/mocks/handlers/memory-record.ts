import { http, HttpResponse } from "msw";
import {
  seedMemoryRecords,
  seedRecordSourceLinks,
  type MockMemoryRecord,
  type MockRecordSourceLink,
} from "../seed-data";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

let records: MockMemoryRecord[] = [...seedMemoryRecords];
let recordSourceLinks: MockRecordSourceLink[] = [...seedRecordSourceLinks];

export function resetMemoryRecords(): void {
  records = [...seedMemoryRecords];
  recordSourceLinks = [...seedRecordSourceLinks];
}

function toResponse(r: MockMemoryRecord) {
  const { deleted_at: _, ...rest } = r;
  return rest;
}

const VALID_RECORD_TYPES = [
  "fact", "event", "decision", "issue", "question", "preference", "task", "insight",
];
const VALID_STATUSES = ["active", "tentative", "outdated", "archived"];
const VALID_IMPORTANCES = ["low", "medium", "high"];

export const memoryRecordHandlers = [
  // POST /memory-spaces/:msId/records
  http.post(`${BASE}/memory-spaces/:msId/records`, async ({ params, request }) => {
    const body = (await request.json()) as {
      record_type?: string;
      content?: string;
      importance?: string;
    };

    if (!body.record_type || !body.content) {
      return HttpResponse.json(
        { error: { code: "validation_error", message: "record_type and content are required" } },
        { status: 422 }
      );
    }

    if (!VALID_RECORD_TYPES.includes(body.record_type)) {
      return HttpResponse.json(
        { error: { code: "validation_error", message: `Invalid record_type: ${body.record_type}` } },
        { status: 422 }
      );
    }

    const now = new Date().toISOString();
    const record: MockMemoryRecord = {
      id: crypto.randomUUID(),
      memory_space_id: params.msId as string,
      record_type: body.record_type,
      content: body.content,
      origin: "manual",
      status: "active",
      confidence: 1.0,
      importance: VALID_IMPORTANCES.includes(body.importance ?? "")
        ? (body.importance as MockMemoryRecord["importance"])
        : "medium",
      metadata: {},
      created_at: now,
      updated_at: now,
      deleted_at: null,
    };
    records.push(record);

    return HttpResponse.json(toResponse(record), { status: 201 });
  }),

  // GET /memory-spaces/:msId/records
  http.get(`${BASE}/memory-spaces/:msId/records`, ({ params, request }) => {
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get("page") ?? "1", 10);
    const pageSize = parseInt(url.searchParams.get("page_size") ?? "20", 10);
    const typeFilter = url.searchParams.get("record_type");
    const statusFilter = url.searchParams.get("status");
    const importanceFilter = url.searchParams.get("importance");

    let active = records.filter(
      (r) => r.memory_space_id === params.msId && r.deleted_at === null
    );

    if (typeFilter) {
      active = active.filter((r) => r.record_type === typeFilter);
    }
    if (statusFilter) {
      active = active.filter((r) => r.status === statusFilter);
    }
    if (importanceFilter) {
      active = active.filter((r) => r.importance === importanceFilter);
    }

    const total = active.length;
    const start = (page - 1) * pageSize;
    const items = active.slice(start, start + pageSize).map(toResponse);

    return HttpResponse.json({ items, total, page, page_size: pageSize });
  }),

  // GET /records/:id
  http.get(`${BASE}/records/:id`, ({ params }) => {
    const record = records.find(
      (r) => r.id === params.id && r.deleted_at === null
    );

    if (!record) {
      return HttpResponse.json(
        { error: { code: "not_found", message: "Record not found" } },
        { status: 404 }
      );
    }

    return HttpResponse.json(toResponse(record));
  }),

  // PATCH /records/:id
  http.patch(`${BASE}/records/:id`, async ({ params, request }) => {
    const record = records.find(
      (r) => r.id === params.id && r.deleted_at === null
    );

    if (!record) {
      return HttpResponse.json(
        { error: { code: "not_found", message: "Record not found" } },
        { status: 404 }
      );
    }

    const body = (await request.json()) as {
      content?: string;
      status?: string;
      importance?: string;
    };

    if (body.status && !VALID_STATUSES.includes(body.status)) {
      return HttpResponse.json(
        { error: { code: "validation_error", message: `Invalid status: ${body.status}` } },
        { status: 422 }
      );
    }
    if (body.importance && !VALID_IMPORTANCES.includes(body.importance)) {
      return HttpResponse.json(
        { error: { code: "validation_error", message: `Invalid importance: ${body.importance}` } },
        { status: 422 }
      );
    }

    if (body.content !== undefined) record.content = body.content;
    if (body.status !== undefined) record.status = body.status as MockMemoryRecord["status"];
    if (body.importance !== undefined) record.importance = body.importance as MockMemoryRecord["importance"];
    record.updated_at = new Date().toISOString();

    return HttpResponse.json(toResponse(record));
  }),

  // DELETE /records/:id
  http.delete(`${BASE}/records/:id`, ({ params }) => {
    const record = records.find(
      (r) => r.id === params.id && r.deleted_at === null
    );

    if (!record) {
      return HttpResponse.json(
        { error: { code: "not_found", message: "Record not found" } },
        { status: 404 }
      );
    }

    record.deleted_at = new Date().toISOString();

    return new HttpResponse(null, { status: 204 });
  }),

  // GET /records/:id/sources
  http.get(`${BASE}/records/:id/sources`, ({ params }) => {
    const record = records.find(
      (r) => r.id === params.id && r.deleted_at === null
    );

    if (!record) {
      return HttpResponse.json(
        { error: { code: "not_found", message: "Record not found" } },
        { status: 404 }
      );
    }

    const links = recordSourceLinks.filter((l) => l.record_id === record.id);

    return HttpResponse.json(links);
  }),
];
