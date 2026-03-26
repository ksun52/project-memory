"use client";

import { useState } from "react";
import { Plus, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/shared/components/empty-state";
import { ListSkeleton } from "@/shared/components/loading-skeleton";
import { ConfirmDialog } from "@/shared/components/confirm-dialog";
import { usePagination } from "@/shared/hooks/use-pagination";
import { useSources, useDeleteSource } from "../hooks";
import { SourceCard } from "./source-card";
import { UploadDialog } from "./upload-dialog";
import { SourceDetail } from "./source-detail";
import type { Source } from "../types";

interface SourceListProps {
  memorySpaceId: string;
}

export function SourceList({ memorySpaceId }: SourceListProps) {
  const { page, pageSize, nextPage, prevPage } = usePagination();
  const { data, isLoading, resetPolling } = useSources(memorySpaceId, {
    page,
    page_size: pageSize,
  });
  const deleteMutation = useDeleteSource();

  const [uploadOpen, setUploadOpen] = useState(false);
  const [viewingSourceId, setViewingSourceId] = useState<string | null>(null);
  const [deletingSource, setDeletingSource] = useState<Source | null>(null);

  function handleView(source: Source) {
    setViewingSourceId(source.id);
  }

  function handleDelete(source: Source) {
    setDeletingSource(source);
  }

  function handleConfirmDelete() {
    if (deletingSource) {
      deleteMutation.mutate(deletingSource.id);
      setDeletingSource(null);
    }
  }

  function handleSourceCreated() {
    resetPolling();
  }

  if (isLoading) {
    return <ListSkeleton />;
  }

  if (!data || data.items.length === 0) {
    return (
      <>
        <EmptyState
          icon={<FileText className="h-12 w-12" />}
          title="No sources yet"
          description="Add a note or upload a document to start capturing context."
          action={
            <Button onClick={() => setUploadOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Source
            </Button>
          }
        />
        <UploadDialog
          memorySpaceId={memorySpaceId}
          open={uploadOpen}
          onOpenChange={setUploadOpen}
          onSourceCreated={handleSourceCreated}
        />
      </>
    );
  }

  const totalPages = Math.ceil(data.total / pageSize);

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={() => setUploadOpen(true)} size="sm">
          <Plus className="h-4 w-4 mr-2" />
          Add Source
        </Button>
      </div>

      <div className="space-y-2">
        {data.items.map((source) => (
          <SourceCard
            key={source.id}
            source={source}
            onView={handleView}
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

      <UploadDialog
        memorySpaceId={memorySpaceId}
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        onSourceCreated={handleSourceCreated}
      />

      <SourceDetail
        sourceId={viewingSourceId}
        open={viewingSourceId !== null}
        onOpenChange={(open) => !open && setViewingSourceId(null)}
      />

      <ConfirmDialog
        open={deletingSource !== null}
        onOpenChange={(open) => !open && setDeletingSource(null)}
        title="Delete source"
        description={`Are you sure you want to delete "${deletingSource?.title}"? This will also remove any linked memory records. This action cannot be undone.`}
        onConfirm={handleConfirmDelete}
      />
    </div>
  );
}
