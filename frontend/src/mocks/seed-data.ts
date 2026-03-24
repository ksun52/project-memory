export interface MockUser {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
}

export interface MockWorkspace {
  id: string;
  owner_id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface MockMemorySpace {
  id: string;
  workspace_id: string;
  name: string;
  description: string;
  status: "active" | "archived";
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

// --- Dev User ---

export const DEV_USER: MockUser = {
  id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  email: "dev@projectmemory.local",
  display_name: "Dev User",
  created_at: "2025-01-15T09:30:00Z",
};

export const DEV_TOKEN = "dev-jwt-token-for-testing";

// --- Workspaces ---

export const seedWorkspaces: MockWorkspace[] = [
  {
    id: "ws-00000001-0000-0000-0000-000000000001",
    owner_id: DEV_USER.id,
    name: "Acme Corp",
    description: "Client engagement workspace for Acme Corp",
    created_at: "2025-06-01T10:00:00Z",
    updated_at: "2025-06-01T10:00:00Z",
    deleted_at: null,
  },
  {
    id: "ws-00000002-0000-0000-0000-000000000002",
    owner_id: DEV_USER.id,
    name: "Internal Research",
    description: "Internal research and exploration projects",
    created_at: "2025-06-05T14:30:00Z",
    updated_at: "2025-06-05T14:30:00Z",
    deleted_at: null,
  },
  {
    id: "ws-00000003-0000-0000-0000-000000000003",
    owner_id: DEV_USER.id,
    name: "Product Launch Q3",
    description: "",
    created_at: "2025-07-01T08:00:00Z",
    updated_at: "2025-07-01T08:00:00Z",
    deleted_at: null,
  },
];

// --- Memory Spaces ---

export const seedMemorySpaces: MockMemorySpace[] = [
  {
    id: "ms-00000001-0000-0000-0000-000000000001",
    workspace_id: "ws-00000001-0000-0000-0000-000000000001",
    name: "Stakeholder Interviews",
    description: "Notes and insights from stakeholder interview sessions",
    status: "active",
    created_at: "2025-06-02T09:00:00Z",
    updated_at: "2025-06-02T09:00:00Z",
    deleted_at: null,
  },
  {
    id: "ms-00000002-0000-0000-0000-000000000002",
    workspace_id: "ws-00000001-0000-0000-0000-000000000001",
    name: "Technical Architecture",
    description: "Architecture decisions and technical context",
    status: "active",
    created_at: "2025-06-03T11:00:00Z",
    updated_at: "2025-06-03T11:00:00Z",
    deleted_at: null,
  },
  {
    id: "ms-00000003-0000-0000-0000-000000000003",
    workspace_id: "ws-00000001-0000-0000-0000-000000000001",
    name: "Phase 1 Retro",
    description: "Archived retrospective from phase 1",
    status: "archived",
    created_at: "2025-06-10T16:00:00Z",
    updated_at: "2025-06-20T10:00:00Z",
    deleted_at: null,
  },
  {
    id: "ms-00000004-0000-0000-0000-000000000004",
    workspace_id: "ws-00000002-0000-0000-0000-000000000002",
    name: "Competitor Analysis",
    description: "Research on competitor products and positioning",
    status: "active",
    created_at: "2025-06-06T12:00:00Z",
    updated_at: "2025-06-06T12:00:00Z",
    deleted_at: null,
  },
];
