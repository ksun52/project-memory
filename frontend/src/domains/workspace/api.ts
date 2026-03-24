import { apiClient } from "@/shared/api/client";
import type { PaginatedResponse, PaginationParams } from "@/shared/types/api";
import type { Workspace, WorkspaceCreate, WorkspaceUpdate } from "./types";

export function listWorkspaces(
  params?: PaginationParams
): Promise<PaginatedResponse<Workspace>> {
  return apiClient.get<PaginatedResponse<Workspace>>("/workspaces", params);
}

export function getWorkspace(id: string): Promise<Workspace> {
  return apiClient.get<Workspace>(`/workspaces/${id}`);
}

export function createWorkspace(data: WorkspaceCreate): Promise<Workspace> {
  return apiClient.post<Workspace>("/workspaces", data);
}

export function updateWorkspace(
  id: string,
  data: WorkspaceUpdate
): Promise<Workspace> {
  return apiClient.patch<Workspace>(`/workspaces/${id}`, data);
}

export function deleteWorkspace(id: string): Promise<void> {
  return apiClient.del(`/workspaces/${id}`);
}
