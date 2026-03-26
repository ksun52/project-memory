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

export interface MockSource {
  id: string;
  memory_space_id: string;
  source_type: "note" | "document" | "transcript";
  title: string;
  processing_status: "pending" | "processing" | "completed" | "failed";
  processing_error: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface MockSourceContent {
  source_id: string;
  content_text: string;
}

export interface MockSourceFile {
  source_id: string;
  mime_type: string;
  size_bytes: number;
  original_filename: string;
}

export interface MockMemoryRecord {
  id: string;
  memory_space_id: string;
  record_type: string;
  content: string;
  origin: "extracted" | "manual";
  status: "active" | "tentative" | "outdated" | "archived";
  confidence: number;
  importance: "low" | "medium" | "high";
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface MockRecordSourceLink {
  id: string;
  record_id: string;
  source_id: string;
  source_title: string;
  source_type: string;
  evidence_text: string | null;
  created_at: string;
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

// --- Sources ---

const MS1 = "ms-00000001-0000-0000-0000-000000000001";

export const seedSources: MockSource[] = [
  {
    id: "src-00000001-0000-0000-0000-000000000001",
    memory_space_id: MS1,
    source_type: "note",
    title: "Kickoff meeting notes",
    processing_status: "completed",
    processing_error: null,
    created_at: "2025-06-02T10:00:00Z",
    updated_at: "2025-06-02T10:05:00Z",
    deleted_at: null,
  },
  {
    id: "src-00000002-0000-0000-0000-000000000002",
    memory_space_id: MS1,
    source_type: "document",
    title: "Project charter v2",
    processing_status: "completed",
    processing_error: null,
    created_at: "2025-06-03T14:00:00Z",
    updated_at: "2025-06-03T14:12:00Z",
    deleted_at: null,
  },
  {
    id: "src-00000003-0000-0000-0000-000000000003",
    memory_space_id: MS1,
    source_type: "note",
    title: "Follow-up with VP of Eng",
    processing_status: "pending",
    processing_error: null,
    created_at: "2025-06-10T09:30:00Z",
    updated_at: "2025-06-10T09:30:00Z",
    deleted_at: null,
  },
  {
    id: "src-00000004-0000-0000-0000-000000000004",
    memory_space_id: MS1,
    source_type: "document",
    title: "Org chart (corrupted file)",
    processing_status: "failed",
    processing_error: "Unsupported file format: image/png",
    created_at: "2025-06-11T16:00:00Z",
    updated_at: "2025-06-11T16:01:00Z",
    deleted_at: null,
  },
];

export const seedSourceContents: MockSourceContent[] = [
  {
    source_id: "src-00000001-0000-0000-0000-000000000001",
    content_text:
      "Kickoff meeting with Acme Corp stakeholders. Attendees: Jane (CEO), Bob (VP Eng), Sarah (PM).\n\nKey points:\n- Timeline: 12-week engagement starting June 15\n- Budget approved at $240k for Phase 1\n- Main concern is legacy system migration from Oracle to Postgres\n- Bob wants zero downtime during cutover\n- Sarah will be primary point of contact\n- Weekly status syncs on Thursdays at 2pm ET\n- First deliverable: migration assessment report due July 1",
  },
  {
    source_id: "src-00000002-0000-0000-0000-000000000002",
    content_text:
      "PROJECT CHARTER v2\n\nProject Name: Acme Corp Database Migration\nSponsor: Jane Smith, CEO\nProject Manager: Sarah Chen\n\n1. Objective\nMigrate Acme Corp's primary transactional database from Oracle 12c to PostgreSQL 15 while maintaining 99.9% uptime.\n\n2. Scope\n- In scope: orders, inventory, and customer tables (approx. 2.3TB)\n- Out of scope: analytics warehouse, reporting layer\n\n3. Success Criteria\n- Zero data loss during migration\n- Query performance within 10% of current baseline\n- Rollback capability for 72 hours post-cutover\n\n4. Risks\n- Stored procedures use Oracle-specific PL/SQL features\n- Some queries rely on Oracle optimizer hints\n- Integration with 3 downstream systems needs testing",
  },
  {
    source_id: "src-00000003-0000-0000-0000-000000000003",
    content_text:
      "Quick call with Bob (VP Eng).\n\nHe mentioned the team tried a migration 2 years ago and it failed due to stored procedure incompatibilities. Wants us to prioritize the PL/SQL audit.\n\nAlso flagged that the ops team is short-staffed — only 2 DBAs available for the cutover window. Suggested we plan for a weekend cutover in August.",
  },
];

export const seedSourceFiles: MockSourceFile[] = [
  {
    source_id: "src-00000002-0000-0000-0000-000000000002",
    mime_type: "application/pdf",
    size_bytes: 245760,
    original_filename: "acme-project-charter-v2.pdf",
  },
];

// --- Memory Records ---

export const seedMemoryRecords: MockMemoryRecord[] = [
  {
    id: "rec-00000001-0000-0000-0000-000000000001",
    memory_space_id: MS1,
    record_type: "fact",
    content: "Engagement timeline is 12 weeks starting June 15, with a budget of $240k for Phase 1.",
    origin: "extracted",
    status: "active",
    confidence: 0.95,
    importance: "high",
    metadata: {},
    created_at: "2025-06-02T10:05:00Z",
    updated_at: "2025-06-02T10:05:00Z",
    deleted_at: null,
  },
  {
    id: "rec-00000002-0000-0000-0000-000000000002",
    memory_space_id: MS1,
    record_type: "decision",
    content: "Primary database migration path: Oracle 12c to PostgreSQL 15.",
    origin: "extracted",
    status: "active",
    confidence: 0.98,
    importance: "high",
    metadata: {},
    created_at: "2025-06-02T10:05:00Z",
    updated_at: "2025-06-02T10:05:00Z",
    deleted_at: null,
  },
  {
    id: "rec-00000003-0000-0000-0000-000000000003",
    memory_space_id: MS1,
    record_type: "issue",
    content: "Stored procedures use Oracle-specific PL/SQL features that need to be audited and converted.",
    origin: "extracted",
    status: "active",
    confidence: 0.92,
    importance: "high",
    metadata: {},
    created_at: "2025-06-03T14:12:00Z",
    updated_at: "2025-06-03T14:12:00Z",
    deleted_at: null,
  },
  {
    id: "rec-00000004-0000-0000-0000-000000000004",
    memory_space_id: MS1,
    record_type: "fact",
    content: "Sarah Chen is the primary point of contact at Acme Corp.",
    origin: "extracted",
    status: "active",
    confidence: 0.97,
    importance: "medium",
    metadata: {},
    created_at: "2025-06-02T10:05:00Z",
    updated_at: "2025-06-02T10:05:00Z",
    deleted_at: null,
  },
  {
    id: "rec-00000005-0000-0000-0000-000000000005",
    memory_space_id: MS1,
    record_type: "event",
    content: "Weekly status syncs scheduled for Thursdays at 2pm ET.",
    origin: "extracted",
    status: "active",
    confidence: 0.95,
    importance: "medium",
    metadata: {},
    created_at: "2025-06-02T10:05:00Z",
    updated_at: "2025-06-02T10:05:00Z",
    deleted_at: null,
  },
  {
    id: "rec-00000006-0000-0000-0000-000000000006",
    memory_space_id: MS1,
    record_type: "task",
    content: "Migration assessment report due July 1.",
    origin: "extracted",
    status: "active",
    confidence: 0.93,
    importance: "high",
    metadata: {},
    created_at: "2025-06-02T10:05:00Z",
    updated_at: "2025-06-02T10:05:00Z",
    deleted_at: null,
  },
  {
    id: "rec-00000007-0000-0000-0000-000000000007",
    memory_space_id: MS1,
    record_type: "insight",
    content: "A previous migration attempt 2 years ago failed due to stored procedure incompatibilities — PL/SQL audit should be top priority.",
    origin: "extracted",
    status: "active",
    confidence: 0.88,
    importance: "high",
    metadata: {},
    created_at: "2025-06-10T09:35:00Z",
    updated_at: "2025-06-10T09:35:00Z",
    deleted_at: null,
  },
  {
    id: "rec-00000008-0000-0000-0000-000000000008",
    memory_space_id: MS1,
    record_type: "issue",
    content: "Ops team is short-staffed — only 2 DBAs available for the cutover window.",
    origin: "extracted",
    status: "tentative",
    confidence: 0.75,
    importance: "medium",
    metadata: {},
    created_at: "2025-06-10T09:35:00Z",
    updated_at: "2025-06-10T09:35:00Z",
    deleted_at: null,
  },
  {
    id: "rec-00000009-0000-0000-0000-000000000009",
    memory_space_id: MS1,
    record_type: "preference",
    content: "Bob (VP Eng) prefers a weekend cutover window in August to minimize business impact.",
    origin: "extracted",
    status: "active",
    confidence: 0.85,
    importance: "medium",
    metadata: {},
    created_at: "2025-06-10T09:35:00Z",
    updated_at: "2025-06-10T09:35:00Z",
    deleted_at: null,
  },
  {
    id: "rec-00000010-0000-0000-0000-000000000010",
    memory_space_id: MS1,
    record_type: "question",
    content: "Can we achieve zero downtime cutover, or will a maintenance window be required?",
    origin: "manual",
    status: "active",
    confidence: 1.0,
    importance: "high",
    metadata: {},
    created_at: "2025-06-05T11:00:00Z",
    updated_at: "2025-06-05T11:00:00Z",
    deleted_at: null,
  },
];

// --- Record-Source Links ---

export const seedRecordSourceLinks: MockRecordSourceLink[] = [
  {
    id: "rsl-00000001-0000-0000-0000-000000000001",
    record_id: "rec-00000001-0000-0000-0000-000000000001",
    source_id: "src-00000001-0000-0000-0000-000000000001",
    source_title: "Kickoff meeting notes",
    source_type: "note",
    evidence_text: "Timeline: 12-week engagement starting June 15\n- Budget approved at $240k for Phase 1",
    created_at: "2025-06-02T10:05:00Z",
  },
  {
    id: "rsl-00000002-0000-0000-0000-000000000002",
    record_id: "rec-00000002-0000-0000-0000-000000000002",
    source_id: "src-00000002-0000-0000-0000-000000000002",
    source_title: "Project charter v2",
    source_type: "document",
    evidence_text: "Migrate Acme Corp's primary transactional database from Oracle 12c to PostgreSQL 15",
    created_at: "2025-06-03T14:12:00Z",
  },
  {
    id: "rsl-00000003-0000-0000-0000-000000000003",
    record_id: "rec-00000003-0000-0000-0000-000000000003",
    source_id: "src-00000002-0000-0000-0000-000000000002",
    source_title: "Project charter v2",
    source_type: "document",
    evidence_text: "Stored procedures use Oracle-specific PL/SQL features",
    created_at: "2025-06-03T14:12:00Z",
  },
  {
    id: "rsl-00000004-0000-0000-0000-000000000004",
    record_id: "rec-00000004-0000-0000-0000-000000000004",
    source_id: "src-00000001-0000-0000-0000-000000000001",
    source_title: "Kickoff meeting notes",
    source_type: "note",
    evidence_text: "Sarah will be primary point of contact",
    created_at: "2025-06-02T10:05:00Z",
  },
  {
    id: "rsl-00000005-0000-0000-0000-000000000005",
    record_id: "rec-00000007-0000-0000-0000-000000000007",
    source_id: "src-00000003-0000-0000-0000-000000000003",
    source_title: "Follow-up with VP of Eng",
    source_type: "note",
    evidence_text: "the team tried a migration 2 years ago and it failed due to stored procedure incompatibilities",
    created_at: "2025-06-10T09:35:00Z",
  },
  {
    id: "rsl-00000006-0000-0000-0000-000000000006",
    record_id: "rec-00000008-0000-0000-0000-000000000008",
    source_id: "src-00000003-0000-0000-0000-000000000003",
    source_title: "Follow-up with VP of Eng",
    source_type: "note",
    evidence_text: "ops team is short-staffed — only 2 DBAs available for the cutover window",
    created_at: "2025-06-10T09:35:00Z",
  },
];
