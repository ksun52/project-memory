"use client";

import { Pencil, Trash2, Link2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { MemoryRecord, RecordType } from "../types";

const TYPE_COLORS: Record<RecordType, string> = {
  fact: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  event: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
  decision: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
  issue: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  question: "bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200",
  preference: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  task: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
  insight: "bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200",
};

const IMPORTANCE_VARIANT: Record<string, "default" | "secondary" | "outline"> = {
  high: "default",
  medium: "secondary",
  low: "outline",
};

interface RecordCardProps {
  record: MemoryRecord;
  onEdit: (record: MemoryRecord) => void;
  onDelete: (record: MemoryRecord) => void;
  onViewProvenance: (record: MemoryRecord) => void;
}

export function RecordCard({
  record,
  onEdit,
  onDelete,
  onViewProvenance,
}: RecordCardProps) {
  return (
    <div className="rounded-lg border p-4 space-y-2 hover:bg-muted/50 transition-colors">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${TYPE_COLORS[record.record_type]}`}
          >
            {record.record_type}
          </span>
          <Badge variant={IMPORTANCE_VARIANT[record.importance]}>
            {record.importance}
          </Badge>
          <Badge variant={record.origin === "extracted" ? "secondary" : "outline"}>
            {record.origin}
          </Badge>
          {record.status !== "active" && (
            <Badge variant="destructive">{record.status}</Badge>
          )}
        </div>

        <div className="flex items-center gap-1 shrink-0">
          {record.origin === "extracted" && (
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => onViewProvenance(record)}
              title="View sources"
            >
              <Link2 className="h-4 w-4" />
              <span className="sr-only">View sources</span>
            </Button>
          )}
          <Button variant="ghost" size="icon-sm" onClick={() => onEdit(record)}>
            <Pencil className="h-4 w-4" />
            <span className="sr-only">Edit</span>
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => onDelete(record)}
            className="text-destructive"
          >
            <Trash2 className="h-4 w-4" />
            <span className="sr-only">Delete</span>
          </Button>
        </div>
      </div>

      <p className="text-sm">{record.content}</p>

      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        <span>Confidence: {(record.confidence * 100).toFixed(0)}%</span>
        <span>{new Date(record.created_at).toLocaleDateString()}</span>
      </div>
    </div>
  );
}
