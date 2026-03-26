"use client";

import { Trash2, Eye, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SOURCE_TYPE_ICONS, STATUS_VARIANT, STATUS_LABEL } from "../constants";
import type { Source } from "../types";

interface SourceCardProps {
  source: Source;
  onView: (source: Source) => void;
  onDelete: (source: Source) => void;
}

export function SourceCard({ source, onView, onDelete }: SourceCardProps) {
  const isProcessing =
    source.processing_status === "pending" || source.processing_status === "processing";

  return (
    <div className="flex items-center gap-3 rounded-lg border p-3 hover:bg-muted/50 transition-colors">
      <div className="text-muted-foreground">
        {SOURCE_TYPE_ICONS[source.source_type]}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium truncate text-sm">{source.title}</span>
          <Badge variant={STATUS_VARIANT[source.processing_status]}>
            {isProcessing && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
            {STATUS_LABEL[source.processing_status]}
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground mt-0.5">
          {source.source_type} &middot;{" "}
          {new Date(source.created_at).toLocaleDateString()}
        </p>
        {source.processing_error && (
          <p className="text-xs text-destructive mt-0.5 truncate">
            {source.processing_error}
          </p>
        )}
      </div>

      <div className="flex items-center gap-1 shrink-0">
        <Button variant="ghost" size="icon-sm" onClick={() => onView(source)}>
          <Eye className="h-4 w-4" />
          <span className="sr-only">View</span>
        </Button>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => onDelete(source)}
          className="text-destructive"
        >
          <Trash2 className="h-4 w-4" />
          <span className="sr-only">Delete</span>
        </Button>
      </div>
    </div>
  );
}
