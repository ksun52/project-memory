"use client";

import { ListChecks } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useSource } from "../hooks";
import { SOURCE_TYPE_ICONS, STATUS_VARIANT } from "../constants";

interface SourceDetailProps {
  sourceId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SourceDetail({ sourceId, open, onOpenChange }: SourceDetailProps) {
  const { data: source, isLoading } = useSource(sourceId ?? "");

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="sm:max-w-lg overflow-y-auto">
        {isLoading || !source ? (
          <SheetHeader>
            <Skeleton className="h-5 w-48" />
            <Skeleton className="h-4 w-32 mt-2" />
          </SheetHeader>
        ) : (
          <>
            <SheetHeader>
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">
                  {SOURCE_TYPE_ICONS[source.source_type]}
                </span>
                <SheetTitle>{source.title}</SheetTitle>
              </div>
              <SheetDescription>
                <span className="inline-flex items-center gap-2">
                  <Badge variant={STATUS_VARIANT[source.processing_status]}>
                    {source.processing_status}
                  </Badge>
                  <span>{source.source_type}</span>
                  <span>&middot;</span>
                  <span>{new Date(source.created_at).toLocaleString()}</span>
                </span>
              </SheetDescription>
            </SheetHeader>

            {source.processing_error && (
              <div className="mx-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
                {source.processing_error}
              </div>
            )}

            {source.file && (
              <div className="mx-4 rounded-md border p-3 space-y-1">
                <p className="text-sm font-medium">File Info</p>
                <p className="text-xs text-muted-foreground">
                  {source.file.original_filename}
                </p>
                <p className="text-xs text-muted-foreground">
                  {source.file.mime_type} &middot;{" "}
                  {formatBytes(source.file.size_bytes)}
                </p>
              </div>
            )}

            {source.linked_records_count !== undefined && source.linked_records_count > 0 && (
              <div className="mx-4 flex items-center gap-2 text-sm text-muted-foreground">
                <ListChecks className="h-4 w-4" />
                <span>
                  {source.linked_records_count} linked record{source.linked_records_count !== 1 ? "s" : ""}
                </span>
              </div>
            )}

            {source.content && (
              <div className="mx-4 space-y-2">
                <p className="text-sm font-medium">Content</p>
                <div className="rounded-md border bg-muted/30 p-3 text-sm whitespace-pre-wrap max-h-[60vh] overflow-y-auto">
                  {source.content.content_text}
                </div>
              </div>
            )}
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
