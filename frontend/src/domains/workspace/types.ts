export interface Workspace {
  id: string;
  owner_id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceCreate {
  name: string;
  description?: string;
}

export interface WorkspaceUpdate {
  name?: string;
  description?: string;
}
