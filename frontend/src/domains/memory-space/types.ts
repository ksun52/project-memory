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
