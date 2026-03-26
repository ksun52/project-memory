import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { toast } from "sonner";
import {
  listRecords,
  getRecord,
  createRecord,
  updateRecord,
  deleteRecord,
  getRecordSources,
} from "./api";
import type { RecordCreate, RecordUpdate, RecordListParams } from "./types";

export function useRecords(
  memorySpaceId: string,
  params?: RecordListParams
) {
  return useQuery({
    queryKey: ["records", memorySpaceId, params],
    queryFn: () => listRecords(memorySpaceId, params),
    enabled: !!memorySpaceId,
  });
}

export function useRecord(id: string) {
  return useQuery({
    queryKey: ["records", "detail", id],
    queryFn: () => getRecord(id),
    enabled: !!id,
  });
}

export function useCreateRecord() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      memorySpaceId,
      data,
    }: {
      memorySpaceId: string;
      data: RecordCreate;
    }) => createRecord(memorySpaceId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["records"] });
      toast.success("Record created");
    },
  });
}

export function useUpdateRecord() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: RecordUpdate }) =>
      updateRecord(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["records"] });
      toast.success("Record updated");
    },
  });
}

export function useDeleteRecord() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteRecord(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["records"] });
      toast.success("Record deleted");
    },
  });
}

export function useRecordSources(recordId: string) {
  return useQuery({
    queryKey: ["records", "sources", recordId],
    queryFn: () => getRecordSources(recordId),
    enabled: !!recordId,
  });
}
