"use client";

import { FileText, StickyNote, Mic } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useRecordSources } from "../hooks";
import { SourceDetail } from "@/domains/source/components/source-detail";
import { useState } from "react";

const TYPE_ICONS: Record<string, React.ReactNode> = {
  note: <StickyNote className="h-4 w-4" />,
  document: <FileText className="h-4 w-4" />,
  transcript: <Mic className="h-4 w-4" />,
};

interface RecordProvenanceProps {
  recordId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function RecordProvenance({ recordId, open, onOpenChange }: RecordProvenanceProps) {
  const { data: links, isLoading } = useRecordSources(recordId ?? "");
  const [viewingSourceId, setViewingSourceId] = useState<string | null>(null);

  return (
    <>
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent className="sm:max-w-lg overflow-y-auto">
          <SheetHeader>
            <SheetTitle>Source Provenance</SheetTitle>
            <SheetDescription>
              Sources that contributed to this record.
            </SheetDescription>
          </SheetHeader>

          {isLoading ? (
            <div className="mx-4 space-y-3">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
            </div>
          ) : !links || links.length === 0 ? (
            <p className="mx-4 text-sm text-muted-foreground">
              No linked sources found.
            </p>
          ) : (
            <div className="mx-4 space-y-3">
              {links.map((link) => (
                <button
                  key={link.id}
                  type="button"
                  className="w-full rounded-lg border p-3 text-left space-y-2 hover:bg-muted/50 transition-colors"
                  onClick={() => setViewingSourceId(link.source_id)}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">
                      {TYPE_ICONS[link.source_type] ?? <FileText className="h-4 w-4" />}
                    </span>
                    <span className="text-sm font-medium">{link.source_title}</span>
                    <Badge variant="secondary">{link.source_type}</Badge>
                  </div>
                  {link.evidence_text && (
                    <blockquote className="border-l-2 border-muted-foreground/30 pl-3 text-xs text-muted-foreground italic">
                      {link.evidence_text}
                    </blockquote>
                  )}
                </button>
              ))}
            </div>
          )}
        </SheetContent>
      </Sheet>

      <SourceDetail
        sourceId={viewingSourceId}
        open={viewingSourceId !== null}
        onOpenChange={(isOpen) => !isOpen && setViewingSourceId(null)}
      />
    </>
  );
}
