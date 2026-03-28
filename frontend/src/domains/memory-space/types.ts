export interface MemorySpace {
  id: string;
  workspace_id: string;
  name: string;
  description: string;
  status: "active" | "archived";
  created_at: string;
  updated_at: string;
}

export interface MemorySpaceCreate {
  name: string;
  description?: string;
}

export interface MemorySpaceUpdate {
  name?: string;
  description?: string;
  status?: "active" | "archived";
}

export interface GeneratedSummary {
  id: string;
  memory_space_id: string;
  summary_type: "one_pager" | "recent_updates";
  title: string;
  content: string;
  is_edited: boolean;
  edited_content: string | null;
  record_ids_used: string[];
  generated_at: string;
  created_at: string;
  updated_at: string;
}

export interface SummaryRequest {
  summary_type: "one_pager" | "recent_updates";
  regenerate?: boolean;
}

export interface Citation {
  record_id: string | null;
  source_id: string | null;
  chunk_id: string | null;
  excerpt: string;
}

export interface QueryResponse {
  answer: string;
  citations: Citation[];
}

export interface QueryRequest {
  question: string;
}
