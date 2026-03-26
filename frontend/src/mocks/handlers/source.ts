import { http, HttpResponse } from "msw";
import {
  seedSources,
  seedSourceContents,
  seedSourceFiles,
  type MockSource,
  type MockSourceContent,
  type MockSourceFile,
} from "../seed-data";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

let sources: MockSource[] = [...seedSources];
let sourceContents: MockSourceContent[] = [...seedSourceContents];
let sourceFiles: MockSourceFile[] = [...seedSourceFiles];

export function resetSources(): void {
  sources = [...seedSources];
  sourceContents = [...seedSourceContents];
  sourceFiles = [...seedSourceFiles];
}

function toResponse(s: MockSource) {
  const { deleted_at: _, ...rest } = s;
  return rest;
}

function toDetailResponse(s: MockSource) {
  const base = toResponse(s);
  const content = sourceContents.find((c) => c.source_id === s.id) ?? null;
  const file = sourceFiles.find((f) => f.source_id === s.id);
  return {
    ...base,
    content,
    file: file
      ? { mime_type: file.mime_type, size_bytes: file.size_bytes, original_filename: file.original_filename }
      : null,
  };
}

export const sourceHandlers = [
  // POST /memory-spaces/:msId/sources
  http.post(`${BASE}/memory-spaces/:msId/sources`, async ({ params, request }) => {
    const contentType = request.headers.get("content-type") ?? "";
    const now = new Date().toISOString();

    if (contentType.includes("application/json")) {
      const body = (await request.json()) as {
        source_type?: string;
        title?: string;
        content?: string;
      };

      if (!body.title || !body.content) {
        return HttpResponse.json(
          { error: { code: "validation_error", message: "Title and content are required" } },
          { status: 422 }
        );
      }

      const source: MockSource = {
        id: crypto.randomUUID(),
        memory_space_id: params.msId as string,
        source_type: "note",
        title: body.title.trim(),
        processing_status: "pending",
        processing_error: null,
        created_at: now,
        updated_at: now,
        deleted_at: null,
      };
      sources.push(source);

      sourceContents.push({
        source_id: source.id,
        content_text: body.content,
      });

      // Simulate async processing: move to completed after a short delay
      setTimeout(() => {
        const s = sources.find((x) => x.id === source.id);
        if (s && s.processing_status === "pending") {
          s.processing_status = "completed";
          s.updated_at = new Date().toISOString();
        }
      }, 5000);

      return HttpResponse.json(toResponse(source), { status: 201 });
    }

    // Multipart form data (document upload)
    const formData = await request.formData();
    const title = formData.get("title") as string | null;
    const file = formData.get("file") as File | null;

    if (!title || !file) {
      return HttpResponse.json(
        { error: { code: "validation_error", message: "Title and file are required" } },
        { status: 422 }
      );
    }

    const source: MockSource = {
      id: crypto.randomUUID(),
      memory_space_id: params.msId as string,
      source_type: "document",
      title: title.trim(),
      processing_status: "pending",
      processing_error: null,
      created_at: now,
      updated_at: now,
      deleted_at: null,
    };
    sources.push(source);

    sourceFiles.push({
      source_id: source.id,
      mime_type: file.type || "application/octet-stream",
      size_bytes: file.size,
      original_filename: file.name,
    });

    const text = await file.text();
    sourceContents.push({
      source_id: source.id,
      content_text: text || `[Parsed content of ${file.name}]`,
    });

    setTimeout(() => {
      const s = sources.find((x) => x.id === source.id);
      if (s && s.processing_status === "pending") {
        s.processing_status = "completed";
        s.updated_at = new Date().toISOString();
      }
    }, 5000);

    return HttpResponse.json(toResponse(source), { status: 201 });
  }),

  // GET /memory-spaces/:msId/sources
  http.get(`${BASE}/memory-spaces/:msId/sources`, ({ params, request }) => {
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get("page") ?? "1", 10);
    const pageSize = parseInt(url.searchParams.get("page_size") ?? "20", 10);
    const typeFilter = url.searchParams.get("source_type");
    const statusFilter = url.searchParams.get("processing_status");

    let active = sources.filter(
      (s) => s.memory_space_id === params.msId && s.deleted_at === null
    );

    if (typeFilter) {
      active = active.filter((s) => s.source_type === typeFilter);
    }
    if (statusFilter) {
      active = active.filter((s) => s.processing_status === statusFilter);
    }

    const total = active.length;
    const start = (page - 1) * pageSize;
    const items = active.slice(start, start + pageSize).map(toResponse);

    return HttpResponse.json({ items, total, page, page_size: pageSize });
  }),

  // GET /sources/:id
  http.get(`${BASE}/sources/:id`, ({ params }) => {
    const source = sources.find(
      (s) => s.id === params.id && s.deleted_at === null
    );

    if (!source) {
      return HttpResponse.json(
        { error: { code: "not_found", message: "Source not found" } },
        { status: 404 }
      );
    }

    return HttpResponse.json(toDetailResponse(source));
  }),

  // GET /sources/:id/content
  http.get(`${BASE}/sources/:id/content`, ({ params }) => {
    const source = sources.find(
      (s) => s.id === params.id && s.deleted_at === null
    );

    if (!source) {
      return HttpResponse.json(
        { error: { code: "not_found", message: "Source not found" } },
        { status: 404 }
      );
    }

    const content = sourceContents.find((c) => c.source_id === source.id);
    if (!content) {
      return HttpResponse.json(
        { error: { code: "not_found", message: "Source content not found" } },
        { status: 404 }
      );
    }

    return HttpResponse.json(content);
  }),

  // DELETE /sources/:id
  http.delete(`${BASE}/sources/:id`, ({ params }) => {
    const source = sources.find(
      (s) => s.id === params.id && s.deleted_at === null
    );

    if (!source) {
      return HttpResponse.json(
        { error: { code: "not_found", message: "Source not found" } },
        { status: 404 }
      );
    }

    source.deleted_at = new Date().toISOString();

    return new HttpResponse(null, { status: 204 });
  }),
];
