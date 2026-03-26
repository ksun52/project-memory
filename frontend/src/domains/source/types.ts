export type SourceType = "note" | "document" | "transcript";

export type ProcessingStatus = "pending" | "processing" | "completed" | "failed";

export interface Source {
  id: string;
  memory_space_id: string;
  source_type: SourceType;
  title: string;
  processing_status: ProcessingStatus;
  processing_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface SourceContent {
  source_id: string;
  content_text: string;
}

export interface SourceFile {
  mime_type: string;
  size_bytes: number;
  original_filename: string;
}

export interface SourceDetail extends Source {
  content: SourceContent | null;
  file: SourceFile | null;
  linked_records_count?: number;
}

export interface SourceCreateNote {
  source_type: "note";
  title: string;
  content: string;
}

export interface SourceCreateDocument {
  title: string;
  file: File;
}

export type SourceListParams = {
  page?: number;
  page_size?: number;
  source_type?: SourceType;
  processing_status?: ProcessingStatus;
};
