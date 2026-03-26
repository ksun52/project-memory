import { useState, useCallback, useEffect } from "react";
import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { toast } from "sonner";
import type { PaginatedResponse } from "@/shared/types/api";
import {
  listSources,
  getSource,
  getSourceContent,
  createNoteSource,
  uploadDocumentSource,
  deleteSource,
} from "./api";
import type {
  Source,
  SourceCreateNote,
  SourceCreateDocument,
  SourceListParams,
} from "./types";

const POLL_INTERVAL_MS = 3000;
const POLL_TIMEOUT_MS = 60000;

export function useSources(
  memorySpaceId: string,
  params?: SourceListParams
) {
  const [pollingSince, setPollingSince] = useState<number | null>(null);

  const query = useQuery({
    queryKey: ["sources", memorySpaceId, params],
    queryFn: () => listSources(memorySpaceId, params),
    enabled: !!memorySpaceId,
    refetchInterval: pollingSince ? POLL_INTERVAL_MS : false,
  });

  // Start/stop polling based on whether any source is pending/processing
  useEffect(() => {
    const data = query.data as PaginatedResponse<Source> | undefined;
    if (!data) return;

    const hasPending = data.items.some(
      (s) => s.processing_status === "pending" || s.processing_status === "processing"
    );

    if (hasPending && !pollingSince) {
      setPollingSince(Date.now());
    } else if (!hasPending && pollingSince) {
      setPollingSince(null);
    }
  }, [query.data, pollingSince]);

  // Stop polling after timeout
  useEffect(() => {
    if (!pollingSince) return;

    const remaining = POLL_TIMEOUT_MS - (Date.now() - pollingSince);
    if (remaining <= 0) {
      setPollingSince(null);
      return;
    }

    const timer = setTimeout(() => setPollingSince(null), remaining);
    return () => clearTimeout(timer);
  }, [pollingSince]);

  const resetPolling = useCallback(() => {
    setPollingSince(Date.now());
  }, []);

  return { ...query, resetPolling };
}

export function useSource(id: string) {
  return useQuery({
    queryKey: ["sources", "detail", id],
    queryFn: () => getSource(id),
    enabled: !!id,
  });
}

export function useSourceContent(id: string) {
  return useQuery({
    queryKey: ["sources", "content", id],
    queryFn: () => getSourceContent(id),
    enabled: !!id,
  });
}

export function useCreateNoteSource() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      memorySpaceId,
      data,
    }: {
      memorySpaceId: string;
      data: SourceCreateNote;
    }) => createNoteSource(memorySpaceId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources"] });
      toast.success("Note source created");
    },
  });
}

export function useUploadDocumentSource() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      memorySpaceId,
      data,
    }: {
      memorySpaceId: string;
      data: SourceCreateDocument;
    }) => uploadDocumentSource(memorySpaceId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources"] });
      toast.success("Document uploaded");
    },
  });
}

export function useDeleteSource() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteSource(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources"] });
      toast.success("Source deleted");
    },
  });
}
