import { apiClient } from "@/shared/api/client";
import type { PaginatedResponse } from "@/shared/types/api";
import type {
  Source,
  SourceContent,
  SourceCreateNote,
  SourceCreateDocument,
  SourceDetail,
  SourceListParams,
} from "./types";

export function listSources(
  memorySpaceId: string,
  params?: SourceListParams
): Promise<PaginatedResponse<Source>> {
  return apiClient.get<PaginatedResponse<Source>>(
    `/memory-spaces/${memorySpaceId}/sources`,
    params
  );
}

export function getSource(id: string): Promise<SourceDetail> {
  return apiClient.get<SourceDetail>(`/sources/${id}`);
}

export function getSourceContent(id: string): Promise<SourceContent> {
  return apiClient.get<SourceContent>(`/sources/${id}/content`);
}

export function createNoteSource(
  memorySpaceId: string,
  data: SourceCreateNote
): Promise<Source> {
  return apiClient.post<Source>(
    `/memory-spaces/${memorySpaceId}/sources`,
    data
  );
}

export function uploadDocumentSource(
  memorySpaceId: string,
  data: SourceCreateDocument
): Promise<Source> {
  const formData = new FormData();
  formData.append("title", data.title);
  formData.append("file", data.file);
  return apiClient.post<Source>(
    `/memory-spaces/${memorySpaceId}/sources`,
    formData
  );
}

export function deleteSource(id: string): Promise<void> {
  return apiClient.del(`/sources/${id}`);
}
