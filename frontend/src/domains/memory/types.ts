export type RecordType =
  | "fact"
  | "event"
  | "decision"
  | "issue"
  | "question"
  | "preference"
  | "task"
  | "insight";

export type RecordOrigin = "extracted" | "manual";

export type RecordStatus = "active" | "tentative" | "outdated" | "archived";

export type RecordImportance = "low" | "medium" | "high";

export interface MemoryRecord {
  id: string;
  memory_space_id: string;
  record_type: RecordType;
  content: string;
  origin: RecordOrigin;
  status: RecordStatus;
  confidence: number;
  importance: RecordImportance;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface RecordCreate {
  record_type: RecordType;
  content: string;
  importance?: RecordImportance;
}

export interface RecordUpdate {
  content?: string;
  status?: RecordStatus;
  importance?: RecordImportance;
}

export interface RecordSourceLink {
  id: string;
  record_id: string;
  source_id: string;
  source_title: string;
  source_type: string;
  evidence_text: string | null;
  created_at: string;
}

export type RecordListParams = {
  page?: number;
  page_size?: number;
  record_type?: RecordType;
  status?: RecordStatus;
  importance?: RecordImportance;
};
