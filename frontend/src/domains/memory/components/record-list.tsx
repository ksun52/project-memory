"use client";

import { useState } from "react";
import { Plus, Brain } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { EmptyState } from "@/shared/components/empty-state";
import { ListSkeleton } from "@/shared/components/loading-skeleton";
import { ConfirmDialog } from "@/shared/components/confirm-dialog";
import { usePagination } from "@/shared/hooks/use-pagination";
import { useRecords, useDeleteRecord } from "../hooks";
import { RecordCard } from "./record-card";
import { RecordCreateDialog } from "./record-create-dialog";
import { RecordEditDialog } from "./record-edit-dialog";
import { RecordProvenance } from "./record-provenance";
import type { MemoryRecord, RecordType, RecordStatus, RecordImportance } from "../types";

const RECORD_TYPES: RecordType[] = [
  "fact", "event", "decision", "issue", "question", "preference", "task", "insight",
];
const STATUSES: RecordStatus[] = ["active", "tentative", "outdated", "archived"];
const IMPORTANCES: RecordImportance[] = ["low", "medium", "high"];

interface RecordListProps {
  memorySpaceId: string;
}

export function RecordList({ memorySpaceId }: RecordListProps) {
  const { page, pageSize, nextPage, prevPage, resetPage } = usePagination();

  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [importanceFilter, setImportanceFilter] = useState<string>("all");

  const queryParams = {
    page,
    page_size: pageSize,
    ...(typeFilter !== "all" ? { record_type: typeFilter as RecordType } : {}),
    ...(statusFilter !== "all" ? { status: statusFilter as RecordStatus } : {}),
    ...(importanceFilter !== "all" ? { importance: importanceFilter as RecordImportance } : {}),
  };

  const { data, isLoading } = useRecords(memorySpaceId, queryParams);
  const deleteMutation = useDeleteRecord();

  const [createOpen, setCreateOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<MemoryRecord | null>(null);
  const [deletingRecord, setDeletingRecord] = useState<MemoryRecord | null>(null);
  const [provenanceRecordId, setProvenanceRecordId] = useState<string | null>(null);

  function handleFilterChange(setter: (v: string) => void) {
    return (value: string | number | null) => {
      if (value !== null) {
        setter(String(value));
        resetPage();
      }
    };
  }

  function handleConfirmDelete() {
    if (deletingRecord) {
      deleteMutation.mutate(deletingRecord.id);
      setDeletingRecord(null);
    }
  }

  const hasFilters = typeFilter !== "all" || statusFilter !== "all" || importanceFilter !== "all";

  if (isLoading) {
    return <ListSkeleton />;
  }

  if (!data || (data.items.length === 0 && !hasFilters)) {
    return (
      <>
        <EmptyState
          icon={<Brain className="h-12 w-12" />}
          title="No memory records yet"
          description="Records will appear here after sources are processed, or you can add them manually."
          action={
            <Button onClick={() => setCreateOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Record
            </Button>
          }
        />
        <RecordCreateDialog
          memorySpaceId={memorySpaceId}
          open={createOpen}
          onOpenChange={setCreateOpen}
        />
      </>
    );
  }

  const totalPages = Math.ceil(data.total / pageSize);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <FilterSelect
            value={typeFilter}
            onChange={handleFilterChange(setTypeFilter)}
            placeholder="Type"
            options={RECORD_TYPES}
          />
          <FilterSelect
            value={statusFilter}
            onChange={handleFilterChange(setStatusFilter)}
            placeholder="Status"
            options={STATUSES}
          />
          <FilterSelect
            value={importanceFilter}
            onChange={handleFilterChange(setImportanceFilter)}
            placeholder="Importance"
            options={IMPORTANCES}
          />
        </div>
        <Button onClick={() => setCreateOpen(true)} size="sm">
          <Plus className="h-4 w-4 mr-2" />
          Add Record
        </Button>
      </div>

      {data.items.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          No records match the current filters.
        </div>
      ) : (
        <div className="space-y-2">
          {data.items.map((record) => (
            <RecordCard
              key={record.id}
              record={record}
              onEdit={setEditingRecord}
              onDelete={setDeletingRecord}
              onViewProvenance={(r) => setProvenanceRecordId(r.id)}
            />
          ))}
        </div>
      )}

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

      <RecordCreateDialog
        memorySpaceId={memorySpaceId}
        open={createOpen}
        onOpenChange={setCreateOpen}
      />

      <RecordEditDialog
        record={editingRecord}
        open={editingRecord !== null}
        onOpenChange={(open) => !open && setEditingRecord(null)}
      />

      <RecordProvenance
        recordId={provenanceRecordId}
        open={provenanceRecordId !== null}
        onOpenChange={(open) => !open && setProvenanceRecordId(null)}
      />

      <ConfirmDialog
        open={deletingRecord !== null}
        onOpenChange={(open) => !open && setDeletingRecord(null)}
        title="Delete record"
        description={`Are you sure you want to delete this ${deletingRecord?.record_type} record? This action cannot be undone.`}
        onConfirm={handleConfirmDelete}
      />
    </div>
  );
}

function FilterSelect({
  value,
  onChange,
  placeholder,
  options,
}: {
  value: string;
  onChange: (value: string | number | null) => void;
  placeholder: string;
  options: string[];
}) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger size="sm">
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">All {placeholder}s</SelectItem>
        {options.map((opt) => (
          <SelectItem key={opt} value={opt}>
            {opt.charAt(0).toUpperCase() + opt.slice(1)}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
