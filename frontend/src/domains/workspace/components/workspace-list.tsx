"use client";

import { useState } from "react";
import { FolderOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/shared/components/empty-state";
import { ListSkeleton } from "@/shared/components/loading-skeleton";
import { ConfirmDialog } from "@/shared/components/confirm-dialog";
import { usePagination } from "@/shared/hooks/use-pagination";
import { useWorkspaces, useDeleteWorkspace, useUpdateWorkspace } from "../hooks";
import { WorkspaceCard } from "./workspace-card";
import { WorkspaceCreateDialog } from "./workspace-create-dialog";
import type { Workspace } from "../types";

export function WorkspaceList() {
  const { page, pageSize, nextPage, prevPage } = usePagination();
  const { data, isLoading } = useWorkspaces({ page, page_size: pageSize });
  const deleteMutation = useDeleteWorkspace();
  const updateMutation = useUpdateWorkspace();

  const [createOpen, setCreateOpen] = useState(false);
  const [deletingWorkspace, setDeletingWorkspace] = useState<Workspace | null>(null);

  function handleDelete(workspace: Workspace) {
    setDeletingWorkspace(workspace);
  }

  function handleConfirmDelete() {
    if (deletingWorkspace) {
      deleteMutation.mutate(deletingWorkspace.id);
      setDeletingWorkspace(null);
    }
  }

  function handleEdit(workspace: Workspace) {
    const newName = prompt("Workspace name:", workspace.name);
    if (newName !== null && newName !== workspace.name) {
      updateMutation.mutate({ id: workspace.id, data: { name: newName } });
    }
  }

  if (isLoading) {
    return <ListSkeleton />;
  }

  if (!data || data.items.length === 0) {
    return (
      <EmptyState
        icon={<FolderOpen className="h-12 w-12" />}
        title="No workspaces yet"
        description="Create your first workspace to get started."
        action={
          <>
            <Button onClick={() => setCreateOpen(true)}>
              Create Workspace
            </Button>
            <WorkspaceCreateDialog
              open={createOpen}
              onOpenChange={setCreateOpen}
            />
          </>
        }
      />
    );
  }

  const totalPages = Math.ceil(data.total / pageSize);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {data.items.map((workspace) => (
          <WorkspaceCard
            key={workspace.id}
            workspace={workspace}
            onEdit={handleEdit}
            onDelete={handleDelete}
          />
        ))}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4">
          <Button
            variant="outline"
            size="sm"
            onClick={prevPage}
            disabled={page <= 1}
          >
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={nextPage}
            disabled={page >= totalPages}
          >
            Next
          </Button>
        </div>
      )}

      <ConfirmDialog
        open={deletingWorkspace !== null}
        onOpenChange={(open) => !open && setDeletingWorkspace(null)}
        title="Delete workspace"
        description={`Are you sure you want to delete "${deletingWorkspace?.name}"? This action cannot be undone.`}
        onConfirm={handleConfirmDelete}
      />
    </div>
  );
}
