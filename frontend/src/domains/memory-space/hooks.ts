import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { toast } from "sonner";
import type { PaginationParams } from "@/shared/types/api";
import {
  listMemorySpaces,
  getMemorySpace,
  createMemorySpace,
  updateMemorySpace,
  deleteMemorySpace,
} from "./api";
import type { MemorySpaceCreate, MemorySpaceUpdate } from "./types";

export function useMemorySpaces(
  workspaceId: string,
  params?: PaginationParams & { status?: string }
) {
  return useQuery({
    queryKey: ["memory-spaces", workspaceId, params],
    queryFn: () => listMemorySpaces(workspaceId, params),
    enabled: !!workspaceId,
  });
}

export function useMemorySpace(id: string) {
  return useQuery({
    queryKey: ["memory-spaces", id],
    queryFn: () => getMemorySpace(id),
    enabled: !!id,
  });
}

export function useCreateMemorySpace() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      workspaceId,
      data,
    }: {
      workspaceId: string;
      data: MemorySpaceCreate;
    }) => createMemorySpace(workspaceId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["memory-spaces"] });
      toast.success("Memory space created");
    },
  });
}

export function useUpdateMemorySpace() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: MemorySpaceUpdate }) =>
      updateMemorySpace(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["memory-spaces"] });
      toast.success("Memory space updated");
    },
  });
}

export function useDeleteMemorySpace() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteMemorySpace(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["memory-spaces"] });
      toast.success("Memory space deleted");
    },
  });
}
