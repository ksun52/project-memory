"use client";

import { useState, useEffect, useCallback } from "react";
import Markdown from "react-markdown";
import { RefreshCw, ScrollText, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { EmptyState } from "@/shared/components/empty-state";
import { useSummarize } from "../hooks";
import type { GeneratedSummary } from "../types";

type SummaryType = "one_pager" | "recent_updates";

interface SummaryPanelProps {
  memorySpaceId: string;
}

const markdownComponents = {
  h1: ({ children, ...props }: React.ComponentProps<"h1">) => (
    <h1 className="text-2xl font-bold mt-6 mb-3" {...props}>{children}</h1>
  ),
  h2: ({ children, ...props }: React.ComponentProps<"h2">) => (
    <h2 className="text-xl font-semibold mt-5 mb-2" {...props}>{children}</h2>
  ),
  h3: ({ children, ...props }: React.ComponentProps<"h3">) => (
    <h3 className="text-lg font-semibold mt-4 mb-2" {...props}>{children}</h3>
  ),
  p: ({ children, ...props }: React.ComponentProps<"p">) => (
    <p className="mb-3 leading-relaxed" {...props}>{children}</p>
  ),
  ul: ({ children, ...props }: React.ComponentProps<"ul">) => (
    <ul className="list-disc pl-6 mb-3 space-y-1" {...props}>{children}</ul>
  ),
  ol: ({ children, ...props }: React.ComponentProps<"ol">) => (
    <ol className="list-decimal pl-6 mb-3 space-y-1" {...props}>{children}</ol>
  ),
  li: ({ children, ...props }: React.ComponentProps<"li">) => (
    <li className="leading-relaxed" {...props}>{children}</li>
  ),
  strong: ({ children, ...props }: React.ComponentProps<"strong">) => (
    <strong className="font-semibold" {...props}>{children}</strong>
  ),
  blockquote: ({ children, ...props }: React.ComponentProps<"blockquote">) => (
    <blockquote className="border-l-4 border-muted-foreground/30 pl-4 italic my-3" {...props}>
      {children}
    </blockquote>
  ),
};

function SummaryLoadingSkeleton() {
  return (
    <div className="space-y-4 pt-4">
      <Skeleton className="h-7 w-64" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-5 w-48 mt-6" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-5/6" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-2/3" />
    </div>
  );
}

export function SummaryPanel({ memorySpaceId }: SummaryPanelProps) {
  const [summaryType, setSummaryType] = useState<SummaryType>("one_pager");
  const [summary, setSummary] = useState<GeneratedSummary | null>(null);
  const summarize = useSummarize();

  const fetchSummary = useCallback(
    (regenerate: boolean) => {
      summarize.mutate(
        { id: memorySpaceId, data: { summary_type: summaryType, regenerate } },
        { onSuccess: (data) => setSummary(data) }
      );
    },
    [memorySpaceId, summaryType]
  );

  // Auto-fetch cached summary on mount and when summary type changes
  useEffect(() => {
    setSummary(null);
    fetchSummary(false);
  }, [fetchSummary]);

  function handleTypeChange(value: string | number | null) {
    if (value === "one_pager" || value === "recent_updates") {
      setSummaryType(value);
    }
  }

  // Error state
  if (summarize.isError && !summary) {
    return (
      <EmptyState
        icon={<AlertCircle className="h-12 w-12" />}
        title="Failed to load summary"
        description="Something went wrong while generating the summary. Please try again."
        action={
          <Button variant="outline" onClick={() => fetchSummary(false)}>
            Retry
          </Button>
        }
      />
    );
  }

  return (
    <div className="space-y-4">
      {/* Header: type selector + regenerate button */}
      <div className="flex items-center justify-between">
        <Select value={summaryType} onValueChange={handleTypeChange}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="one_pager">One-Pager</SelectItem>
            <SelectItem value="recent_updates">Recent Updates</SelectItem>
          </SelectContent>
        </Select>

        <Button
          variant="outline"
          size="sm"
          onClick={() => fetchSummary(true)}
          disabled={summarize.isPending}
        >
          <RefreshCw
            className={`h-4 w-4 mr-1.5 ${summarize.isPending ? "animate-spin" : ""}`}
          />
          Regenerate
        </Button>
      </div>

      {/* Loading state */}
      {summarize.isPending && !summary && <SummaryLoadingSkeleton />}

      {/* Summary content */}
      {summary && (
        <div>
          <h2 className="text-xl font-semibold mb-4">{summary.title}</h2>
          <div className="text-sm text-foreground">
            <Markdown components={markdownComponents}>{summary.content}</Markdown>
          </div>
          <div className="mt-6 flex items-center gap-4 text-xs text-muted-foreground">
            <span>
              Generated{" "}
              {new Date(summary.generated_at).toLocaleDateString(undefined, {
                month: "short",
                day: "numeric",
                year: "numeric",
                hour: "numeric",
                minute: "2-digit",
              })}
            </span>
            <span>Based on {summary.record_ids_used.length} records</span>
          </div>
        </div>
      )}

      {/* Empty state — no summary and not loading */}
      {!summary && !summarize.isPending && !summarize.isError && (
        <EmptyState
          icon={<ScrollText className="h-12 w-12" />}
          title="No summary available"
          description="Generate a summary to get an overview of this memory space."
          action={
            <Button onClick={() => fetchSummary(true)}>
              Generate Summary
            </Button>
          }
        />
      )}
    </div>
  );
}
