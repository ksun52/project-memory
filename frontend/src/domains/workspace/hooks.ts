import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { toast } from "sonner";
import type { PaginationParams } from "@/shared/types/api";
import {
  listWorkspaces,
  getWorkspace,
  createWorkspace,
  updateWorkspace,
  deleteWorkspace,
} from "./api";
import type { WorkspaceCreate, WorkspaceUpdate } from "./types";

export function useWorkspaces(params?: PaginationParams) {
  return useQuery({
    queryKey: ["workspaces", params],
    queryFn: () => listWorkspaces(params),
  });
}

export function useWorkspace(id: string) {
  return useQuery({
    queryKey: ["workspaces", id],
    queryFn: () => getWorkspace(id),
    enabled: !!id,
  });
}

export function useCreateWorkspace() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: WorkspaceCreate) => createWorkspace(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workspaces"] });
      toast.success("Workspace created");
    },
  });
}

export function useUpdateWorkspace() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: WorkspaceUpdate }) =>
      updateWorkspace(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workspaces"] });
      toast.success("Workspace updated");
    },
  });
}

export function useDeleteWorkspace() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteWorkspace(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workspaces"] });
      toast.success("Workspace deleted");
    },
  });
}
