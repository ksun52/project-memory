import { apiClient } from "@/shared/api/client";
import type { PaginatedResponse } from "@/shared/types/api";
import type {
  MemoryRecord,
  RecordCreate,
  RecordUpdate,
  RecordSourceLink,
  RecordListParams,
} from "./types";

export function listRecords(
  memorySpaceId: string,
  params?: RecordListParams
): Promise<PaginatedResponse<MemoryRecord>> {
  return apiClient.get<PaginatedResponse<MemoryRecord>>(
    `/memory-spaces/${memorySpaceId}/records`,
    params
  );
}

export function getRecord(id: string): Promise<MemoryRecord> {
  return apiClient.get<MemoryRecord>(`/records/${id}`);
}

export function createRecord(
  memorySpaceId: string,
  data: RecordCreate
): Promise<MemoryRecord> {
  return apiClient.post<MemoryRecord>(
    `/memory-spaces/${memorySpaceId}/records`,
    data
  );
}

export function updateRecord(
  id: string,
  data: RecordUpdate
): Promise<MemoryRecord> {
  return apiClient.patch<MemoryRecord>(`/records/${id}`, data);
}

export function deleteRecord(id: string): Promise<void> {
  return apiClient.del(`/records/${id}`);
}

export function getRecordSources(recordId: string): Promise<RecordSourceLink[]> {
  return apiClient.get<RecordSourceLink[]>(`/records/${recordId}/sources`);
}
