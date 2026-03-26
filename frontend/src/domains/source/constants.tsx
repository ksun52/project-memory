import { FileText, StickyNote, Mic } from "lucide-react";
import type { SourceType, ProcessingStatus } from "./types";

export const SOURCE_TYPE_ICONS: Record<SourceType, React.ReactNode> = {
  note: <StickyNote className="h-4 w-4" />,
  document: <FileText className="h-4 w-4" />,
  transcript: <Mic className="h-4 w-4" />,
};

export const STATUS_VARIANT: Record<
  ProcessingStatus,
  "default" | "secondary" | "destructive" | "outline"
> = {
  pending: "outline",
  processing: "secondary",
  completed: "default",
  failed: "destructive",
};

export const STATUS_LABEL: Record<ProcessingStatus, string> = {
  pending: "Pending",
  processing: "Processing",
  completed: "Completed",
  failed: "Failed",
};
