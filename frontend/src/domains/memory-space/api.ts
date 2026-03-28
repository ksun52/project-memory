import { apiClient } from "@/shared/api/client";
import type { PaginatedResponse, PaginationParams } from "@/shared/types/api";
import type {
  MemorySpace,
  MemorySpaceCreate,
  MemorySpaceUpdate,
  SummaryRequest,
  GeneratedSummary,
  QueryRequest,
  QueryResponse,
} from "./types";

export function listMemorySpaces(
  workspaceId: string,
  params?: PaginationParams & { status?: string }
): Promise<PaginatedResponse<MemorySpace>> {
  return apiClient.get<PaginatedResponse<MemorySpace>>(
    `/workspaces/${workspaceId}/memory-spaces`,
    params
  );
}

export function getMemorySpace(id: string): Promise<MemorySpace> {
  return apiClient.get<MemorySpace>(`/memory-spaces/${id}`);
}

export function createMemorySpace(
  workspaceId: string,
  data: MemorySpaceCreate
): Promise<MemorySpace> {
  return apiClient.post<MemorySpace>(
    `/workspaces/${workspaceId}/memory-spaces`,
    data
  );
}

export function updateMemorySpace(
  id: string,
  data: MemorySpaceUpdate
): Promise<MemorySpace> {
  return apiClient.patch<MemorySpace>(`/memory-spaces/${id}`, data);
}

export function deleteMemorySpace(id: string): Promise<void> {
  return apiClient.del(`/memory-spaces/${id}`);
}

export function summarizeMemorySpace(
  id: string,
  data: SummaryRequest
): Promise<GeneratedSummary> {
  return apiClient.post<GeneratedSummary>(
    `/memory-spaces/${id}/summarize`,
    data
  );
}

export function queryMemorySpace(
  id: string,
  data: QueryRequest
): Promise<QueryResponse> {
  return apiClient.post<QueryResponse>(`/memory-spaces/${id}/query`, data);
}
