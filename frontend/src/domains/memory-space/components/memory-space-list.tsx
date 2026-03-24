"use client";

import { useState } from "react";
import { Brain } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState } from "@/shared/components/empty-state";
import { ListSkeleton } from "@/shared/components/loading-skeleton";
import { usePagination } from "@/shared/hooks/use-pagination";
import {
  useMemorySpaces,
  useDeleteMemorySpace,
  useUpdateMemorySpace,
} from "../hooks";
import { MemorySpaceCard } from "./memory-space-card";
import { MemorySpaceCreateDialog } from "./memory-space-create-dialog";
import type { MemorySpace } from "../types";

type StatusFilter = "all" | "active" | "archived";

interface MemorySpaceListProps {
  workspaceId: string;
}

export function MemorySpaceList({ workspaceId }: MemorySpaceListProps) {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const { page, pageSize, nextPage, prevPage, resetPage } = usePagination();

  const queryParams = {
    page,
    page_size: pageSize,
    ...(statusFilter !== "all" ? { status: statusFilter } : {}),
  };

  const { data, isLoading } = useMemorySpaces(workspaceId, queryParams);
  const deleteMutation = useDeleteMemorySpace();
  const updateMutation = useUpdateMemorySpace();

  const [createOpen, setCreateOpen] = useState(false);

  function handleDelete(memorySpace: MemorySpace) {
    if (confirm(`Delete "${memorySpace.name}"? This cannot be undone.`)) {
      deleteMutation.mutate(memorySpace.id);
    }
  }

  function handleEdit(memorySpace: MemorySpace) {
    const newName = prompt("Memory space name:", memorySpace.name);
    if (newName !== null && newName !== memorySpace.name) {
      updateMutation.mutate({ id: memorySpace.id, data: { name: newName } });
    }
  }

  function handleToggleStatus(memorySpace: MemorySpace) {
    const newStatus = memorySpace.status === "active" ? "archived" : "active";
    updateMutation.mutate({ id: memorySpace.id, data: { status: newStatus } });
  }

  function handleFilterChange(value: string | number | null) {
    if (value !== null) {
      setStatusFilter(value as StatusFilter);
      resetPage();
    }
  }

  if (isLoading) {
    return <ListSkeleton />;
  }

  if (!data || data.items.length === 0) {
    // Show empty state only when no filter is active and there are truly no items
    if (statusFilter === "all") {
      return (
        <EmptyState
          icon={<Brain className="h-12 w-12" />}
          title="No memory spaces yet"
          description="Create your first memory space to start capturing context."
          action={
            <>
              <Button onClick={() => setCreateOpen(true)}>
                Create Memory Space
              </Button>
              <MemorySpaceCreateDialog
                workspaceId={workspaceId}
                open={createOpen}
                onOpenChange={setCreateOpen}
              />
            </>
          }
        />
      );
    }

    // Filtered empty state
    return (
      <div className="space-y-6">
        <StatusFilterTabs value={statusFilter} onChange={handleFilterChange} />
        <div className="text-center py-12 text-muted-foreground">
          No {statusFilter} memory spaces found.
        </div>
      </div>
    );
  }

  const totalPages = Math.ceil(data.total / pageSize);

  return (
    <div className="space-y-6">
      <StatusFilterTabs value={statusFilter} onChange={handleFilterChange} />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {data.items.map((memorySpace) => (
          <MemorySpaceCard
            key={memorySpace.id}
            memorySpace={memorySpace}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onToggleStatus={handleToggleStatus}
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
    </div>
  );
}

function StatusFilterTabs({
  value,
  onChange,
}: {
  value: StatusFilter;
  onChange: (value: string | number | null) => void;
}) {
  return (
    <Tabs value={value} onValueChange={onChange}>
      <TabsList>
        <TabsTrigger value="all">All</TabsTrigger>
        <TabsTrigger value="active">Active</TabsTrigger>
        <TabsTrigger value="archived">Archived</TabsTrigger>
      </TabsList>
    </Tabs>
  );
}
