# Frontend Architecture

**Product:** Project Memory  
**Version:** v0.1 (MVP)  
**Status:** Draft

---

## 1. Overview

### Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Framework | Next.js 16 (App Router) | SSR/SSG flexibility, file-based routing, React Server Components |
| UI Components | shadcn/ui | Composable, accessible, built on Radix primitives — copied into codebase, not a dependency |
| Styling | Tailwind CSS v4 | Utility-first, ships with shadcn, zero runtime overhead; CSS-based config (no `tailwind.config.js`) |
| Server State | TanStack Query (React Query) | Caching, background refetching, optimistic updates, loading/error states |
| Client State | React Context (auth only) | Minimal — no global state library for MVP |
| API Client | Typed fetch wrapper | Thin wrapper around `fetch` with auth interceptors and error normalization |
| Forms | React Hook Form + Zod v4 | shadcn/ui form components are built on these |
| Mocking | MSW (Mock Service Worker) | Mock API responses during parallel development (conforms to API contract) |

### Architecture Principles

- **Domain-driven modules** — frontend code organized by business domain (mirroring backend), not by technical layer
- **API contract as boundary** — frontend and backend communicate only through a shared API contract; no shared code or types
- **Colocation** — components, hooks, types, and API functions live together within their domain module
- **Server Components by default** — use Client Components only when interactivity is required (forms, modals, dynamic filtering, hooks)
- **Shared is truly shared** — the `shared/` layer contains only domain-agnostic utilities used by 3+ domains; two-domain sharing uses direct cross-domain imports from the owning domain
- **TanStack Query owns server state** — no duplicating API data into local state; all server data flows through query hooks
- **Pages are thin shells** — `page.tsx` files fetch initial data server-side and delegate rendering to domain components

---

## 2. Route Structure

All authenticated routes live under the `(dashboard)` route group, which provides the authenticated layout shell (sidebar, navigation, auth guard). Auth routes live under the `(auth)` route group.

| Route | Page | Purpose |
|-------|------|---------|
| `/login` | Login | Initiate WorkOS SSO redirect |
| `/auth/callback` | Auth Callback | Handle WorkOS redirect, store token, redirect to `/workspaces` |
| `/workspaces` | Workspace List | View, create, and manage workspaces |
| `/workspaces/[workspaceId]` | Memory Spaces List | View, create, and manage memory spaces within a workspace |
| `/workspaces/[wId]/memory-spaces/[msId]` | Memory Space Detail | Primary working screen — tabbed interface (Sources, Records, Summary, Ask) |

### Route Groups

- **`(auth)`** — unauthenticated routes (login, callback). Minimal layout, no sidebar.
- **`(dashboard)`** — authenticated routes. Wraps children in the app shell (sidebar, top nav, breadcrumbs). Redirects to `/login` if no valid session.

### Memory Space Detail — Tabbed Layout

The memory space detail page uses **client-side tabs** (not sub-routes) for Sources, Records, Summary, and Ask. Tab state is synced to a query parameter (`?tab=sources`) for shareability without being a full sub-route.

The **Ask** tab provides a dedicated query interface with suggested questions, markdown-rendered answers, and citation links. This replaces an earlier design that used a persistent query bar above the tabs.

```
┌──────────────────────────────────────────────────┐
│  Breadcrumb: Workspaces > Acme Corp > Project X  │
│  Memory Space Name + Description    [active]     │
│  [Sources]  [Records]  [Summary]  [Ask]          │
│  ┌──────────────────────────────────────────────┐│
│  │                                              ││
│  │           (active tab content)               ││
│  │                                              ││
│  └──────────────────────────────────────────────┘│
└──────────────────────────────────────────────────┘
```

---

## 3. Domain Modules

Each frontend domain maps to a backend domain and a set of database entities. Every domain module has the same internal structure:

```
domains/<domain>/
  ├── api.ts            # API call functions (typed fetch calls)
  ├── hooks.ts          # TanStack Query hooks wrapping api.ts
  ├── types.ts          # TypeScript interfaces mirroring API contract DTOs
  └── components/       # Domain-specific UI components
```

| Frontend Domain | Backend Domain | DB Entities | Purpose |
|----------------|---------------|------------|---------|
| `auth` | Auth | `users` | Login flow, token storage, current user context, auth guard |
| `workspace` | Workspace | `workspaces` | Workspace CRUD, workspace selector/list |
| `memory-space` | Memory Space | `memory_spaces`, `generated_summaries` | Memory space CRUD, summary generation, query interface |
| `source` | Source | `sources`, `source_contents`, `source_files` | Source list, upload flow (notes + documents), processing status |
| `memory` | Memory | `memory_records`, `record_source_links` | Record list/filter, record CRUD, provenance view |

The AI domain has **no frontend counterpart** — it is entirely backend-internal, exposed through memory-space endpoints (`/summarize`, `/query`).

### Domain Dependencies

Cross-domain imports follow a directed dependency graph. The owning domain exports; consuming domains import directly.

```
auth         <── all domains (user types, auth hooks)
workspace    <── memory-space (workspace context/ID)
memory-space <── source, memory (memory space context/ID)
source       (leaf — no other domain imports from source)
memory       (leaf — no other domain imports from memory)
```

---

## 4. Types Per Domain

Each domain's `types.ts` defines TypeScript interfaces that mirror the API contract DTOs. These are the frontend's representation of backend data — they are defined independently (not shared from the backend) to maintain decoupling.

| Domain | Types |
|--------|-------|
| **auth** | `User`, `TokenResponse`, `AuthState` |
| **workspace** | `Workspace`, `WorkspaceCreate`, `WorkspaceUpdate` |
| **memory-space** | `MemorySpace`, `MemorySpaceCreate`, `MemorySpaceUpdate`, `SummaryRequest`, `SummaryResponse`, `QueryRequest`, `QueryResponse`, `QueryCitation` |
| **source** | `Source`, `SourceDetail`, `SourceContent`, `SourceFile`, `SourceCreateNote`, `SourceCreateDocument` |
| **memory** | `MemoryRecord`, `RecordCreate`, `RecordUpdate`, `RecordSourceLink` |

Shared types used by all domains (defined in `shared/types/api.ts`):

- `PaginatedResponse<T>` — `{ items: T[], total: number, page: number, page_size: number }`
- `ApiError` — `{ error: { code: string, message: string } }`
- `PaginationParams` — `{ page?: number, page_size?: number }`

---

## 5. Hooks Per Domain

Each domain's `hooks.ts` exports TanStack Query hooks that wrap the domain's `api.ts` functions. These are the primary interface for components to interact with server data.

### Auth Hooks

- `useCurrentUser()` — returns the authenticated user; redirects to login if unauthenticated
- `useLogout()` — mutation that clears token and redirects to login

### Workspace Hooks

- `useWorkspaces()` — list the current user's workspaces
- `useWorkspace(id)` — get a single workspace
- `useCreateWorkspace()` — mutation; invalidates workspace list on success
- `useUpdateWorkspace()` — mutation; invalidates workspace detail + list
- `useDeleteWorkspace()` — mutation; invalidates workspace list

### Memory Space Hooks

- `useMemorySpaces(workspaceId, filters?)` — list memory spaces with optional status filter
- `useMemorySpace(id)` — get a single memory space
- `useCreateMemorySpace()` — mutation; invalidates memory space list
- `useUpdateMemorySpace()` — mutation; invalidates detail + list
- `useDeleteMemorySpace()` — mutation; invalidates list
- `useGenerateSummary(memorySpaceId)` — mutation; triggers one-pager or recent updates generation
- `useQueryMemorySpace(memorySpaceId)` — mutation; sends NL question, returns answer with citations

### Source Hooks

- `useSources(memorySpaceId, filters?)` — list sources with optional type/status filters
- `useSource(id)` — get source detail (includes content and file metadata)
- `useSourceContent(id)` — get full text content
- `useCreateNoteSource()` — mutation; creates a note source
- `useUploadDocumentSource()` — mutation; uploads a document (multipart)
- `useDeleteSource()` — mutation; invalidates source list

### Memory Hooks

- `useRecords(memorySpaceId, filters?)` — list/filter records by type, status, importance
- `useRecord(id)` — get a single record
- `useCreateRecord()` — mutation; creates a manual record
- `useUpdateRecord()` — mutation; updates content, status, importance
- `useDeleteRecord()` — mutation; invalidates record list
- `useRecordSources(recordId)` — get linked sources (provenance)

---

## 6. Key Components Per Domain

### Auth

| Component | Purpose |
|-----------|---------|
| `LoginForm` | SSO sign-in button, initiates WorkOS redirect |
| `AuthGuard` | Wraps authenticated routes; redirects to `/login` if no session |
| `AuthProvider` | React Context provider; holds current user and token in localStorage |

### Workspace

| Component | Purpose |
|-----------|---------|
| `WorkspaceList` | Grid of workspace cards with create button; delete confirmation via `ConfirmDialog` |
| `WorkspaceCard` | Displays workspace name, description, memory space count; dropdown menu with edit and delete actions |
| `WorkspaceCreateDialog` | Modal form for creating a new workspace |

### Memory Space

| Component | Purpose |
|-----------|---------|
| `MemorySpaceList` | Grid of memory space cards with status badges and create button |
| `MemorySpaceCard` | Displays name, description, status with inline archive/activate toggle, edit, and delete |
| `MemorySpaceCreateDialog` | Modal form for creating a new memory space |
| `SummaryPanel` | Summary tab — type selector (one-pager / recent updates), generate and regenerate, renders markdown |
| `QueryPanel` | Ask tab — question input with suggestions, markdown answers, citation list with record type badges |

### Source

| Component | Purpose |
|-----------|---------|
| `SourceList` | Table/list of sources with type icons, titles, processing status badges; uses smart polling via `useSources` hook |
| `SourceCard` | Individual source row — title, type, status badge (with animated spinner for pending/processing), timestamp, error display |
| `UploadDialog` | Two-mode dialog: "Quick Note" (text input) or "Upload Document" (file picker with drag-and-drop) |
| `SourceDetail` | Slide-over or expandable panel showing full content and linked records |

### Memory

| Component | Purpose |
|-----------|---------|
| `RecordList` | Filterable list of memory records with filter controls |
| `RecordCard` | Displays content, type badge, confidence score, importance, provenance link |
| `RecordEditDialog` | Modal form for editing record content, status, importance |
| `RecordCreateDialog` | Modal form for manually creating a new record |
| `RecordProvenance` | Shows linked sources with evidence text excerpts |

---

## 7. State Management

### Server State — TanStack Query

All data from the API is managed exclusively by TanStack Query. Each domain's `hooks.ts` provides query and mutation hooks that handle:

- Caching and background refetching
- Loading, error, and success states
- Cache invalidation after mutations (e.g., creating a source invalidates the source list)
- Initial data hydration from server-side fetches (via `initialData` option)

There is no separate client-side store for server data. Components access data only through TanStack Query hooks.

### Client State — React Context (Auth Only)

The only client-side state is the auth context, which holds:

- Current authenticated user
- JWT access token (stored in localStorage for persistence across page refreshes)
- Auth state (loading, authenticated, unauthenticated)

This is provided by `AuthProvider` and consumed via `useCurrentUser()` and the API client (which reads the token for request headers).

### No Global State Library

For MVP, there is no Zustand, Redux, or similar. If a future need arises (e.g., complex cross-domain client state), Zustand can be introduced at that point. TanStack Query + auth context covers all current requirements.

### Cross-Domain Data Sharing Rules

- If only the owning domain uses a type/hook, it stays in that domain
- If 2 domains share something, the owning domain exports it and the consumer imports directly
- Only if 3+ domains need the same utility does it move to `shared/`

---

## 8. Server vs Client Component Boundary

### Guiding Principle

Use Server Components for **layout, navigation, and initial data fetching**. Use Client Components for **interactivity, mutations, and stateful UI**.

### Server Components (zero client-side JS)

| What | Why Server |
|------|-----------|
| Root layout (`app/layout.tsx`) | Static shell — fonts, metadata, providers wrapper |
| Dashboard layout (`app/(dashboard)/layout.tsx`) | Sidebar shell, navigation chrome |
| Page components (`page.tsx` files) | Initial data fetch, pass as props to client components |
| Breadcrumbs | Derived from route params, no interactivity |
| Static page headers | Title and description from fetched data |

### Client Components (`'use client'`)

| What | Why Client |
|------|-----------|
| All domain `components/` | Use TanStack Query hooks, handle events, manage form state |
| `AuthProvider` | Manages token in localStorage, reacts to auth state |
| `Providers` wrapper | `QueryClientProvider` + `AuthProvider` must be client components |
| Forms and dialogs | Interactive input, validation, submission |
| Tab navigation | `useState` for active tab |
| Query bar | User input, loading states, result display |
| Filter controls | Dropdowns, toggles |
| Paginated lists | Page navigation, loading on page change |

### Page Pattern

Pages are thin Server Component shells that fetch initial data and delegate to Client Component domain components:

```
page.tsx (Server Component)
  └── fetches initial data server-side
      └── renders domain component (Client Component)
          └── TanStack Query takes over with initialData
              └── handles all subsequent interactivity
```

### Providers

The root layout wraps children in a `Providers` client component that sets up `QueryClientProvider` and `AuthProvider`. This is one of the few things that genuinely belongs in `shared/`.

---

## 9. Cross-Cutting Concerns

### Authentication Flow

1. User clicks "Sign in" → frontend redirects to WorkOS SSO via `GET /api/v1/auth/login`
2. WorkOS redirects back to `/auth/callback` with an authorization code
3. Callback page exchanges code via `GET /api/v1/auth/callback` → receives JWT
4. Token is stored in localStorage (via `AuthProvider` context) for persistence across page refreshes
5. API client reads token from context and attaches as `Authorization: Bearer <token>` header
6. `AuthGuard` component checks auth state on dashboard routes; redirects to `/login` if unauthenticated

### API Client

A thin typed wrapper around `fetch` living in `shared/api/client.ts`:

- Base URL configuration (from environment variable)
- Automatic `Authorization` header injection
- Response normalization (JSON parsing, error extraction)
- Consistent error handling — maps HTTP errors to typed `ApiError` objects
- Used by every domain's `api.ts` as the sole interface to the backend

### Error Handling

- **API errors** — caught by the API client, normalized to `ApiError` format, surfaced via TanStack Query's `error` state
- **Component-level errors** — each domain component handles its own loading/error states using TanStack Query's `isLoading`, `isError`, `error` properties
- **Global error boundary** — a React error boundary in the dashboard layout catches unexpected rendering errors
- **Toast notifications** — mutations (create, update, delete) show success/error toasts via shadcn/ui's toast component

### Pagination

All list hooks accept `PaginationParams` (`page`, `page_size`) and return `PaginatedResponse<T>`. A shared `usePagination` hook in `shared/hooks/` manages page state and provides prev/next/goto helpers.

### Loading States

- **Initial page load** — Server Component fetches data; no loading spinner on first render
- **Tab switches / filter changes** — TanStack Query shows cached data immediately, refetches in background
- **Mutations** — loading state on submit buttons, optimistic updates where appropriate (e.g., record status change)
- **Long operations** — summary generation shows a progress/pending state since LLM calls may take several seconds

### Smart Source Polling

The `useSources` hook automatically polls when any source has `pending` or `processing` status:

- **Poll interval:** 3 seconds
- **Timeout:** 60 seconds (stops polling to prevent indefinite requests)
- **Trigger:** polling starts when any source in the list has a non-terminal status, stops when all sources reach `completed` or `failed`
- **Manual reset:** `resetPolling()` returned by the hook restarts the polling timer (used after uploading a new source)

### Destructive Action Confirmation

A shared `ConfirmDialog` component (`shared/components/confirm-dialog.tsx`) wraps shadcn/ui's `AlertDialog` to provide consistent confirmation for destructive actions (delete workspace, delete memory space, delete source). Each list component manages its own "deleting" state and renders the dialog conditionally.

### Theming

Dark mode infrastructure is in place via `next-themes`:

- `suppressHydrationWarning` set on `<html>` element for theme provider hydration
- Sonner toast component reads `useTheme()` to match toast styling to the active theme
- shadcn/ui components use CSS variables that support both light and dark modes
- No user-facing theme toggle is implemented yet — defaults to system preference

---

## 10. Project Folder Structure

```
frontend/
├── src/
│   ├── app/                              # Next.js App Router pages
│   │   ├── layout.tsx                    # Root layout (fonts, metadata, Providers)
│   │   ├── page.tsx                      # Root redirect → /workspaces or /login
│   │   ├── (auth)/
│   │   │   ├── login/
│   │   │   │   └── page.tsx              # Login page
│   │   │   └── auth/
│   │   │       └── callback/
│   │   │           └── page.tsx          # WorkOS callback handler
│   │   └── (dashboard)/
│   │       ├── layout.tsx                # Authenticated shell (sidebar, nav, auth guard)
│   │       └── workspaces/
│   │           ├── page.tsx              # Workspace list
│   │           └── [workspaceId]/
│   │               ├── page.tsx          # Memory spaces list
│   │               └── memory-spaces/
│   │                   └── [memorySpaceId]/
│   │                       └── page.tsx  # Memory space detail (tabbed)
│   │
│   ├── domains/                          # Domain-driven modules
│   │   ├── auth/
│   │   │   ├── api.ts
│   │   │   ├── hooks.ts
│   │   │   ├── types.ts
│   │   │   ├── auth-provider.tsx
│   │   │   └── components/
│   │   │       ├── login-form.tsx
│   │   │       └── auth-guard.tsx
│   │   │
│   │   ├── workspace/
│   │   │   ├── api.ts
│   │   │   ├── hooks.ts
│   │   │   ├── types.ts
│   │   │   └── components/
│   │   │       ├── workspace-list.tsx
│   │   │       ├── workspace-card.tsx
│   │   │       └── workspace-create-dialog.tsx
│   │   │
│   │   ├── memory-space/
│   │   │   ├── api.ts
│   │   │   ├── hooks.ts
│   │   │   ├── types.ts
│   │   │   └── components/
│   │   │       ├── memory-space-list.tsx
│   │   │       ├── memory-space-card.tsx
│   │   │       ├── memory-space-create-dialog.tsx
│   │   │       ├── memory-space-detail.tsx
│   │   │       ├── query-bar.tsx
│   │   │       ├── query-result-panel.tsx
│   │   │       ├── summary-display.tsx
│   │   │       └── generate-summary-button.tsx
│   │   │
│   │   ├── source/
│   │   │   ├── api.ts
│   │   │   ├── hooks.ts
│   │   │   ├── types.ts
│   │   │   └── components/
│   │   │       ├── source-list.tsx
│   │   │       ├── source-card.tsx
│   │   │       ├── upload-dialog.tsx
│   │   │       └── source-detail.tsx
│   │   │
│   │   └── memory/
│   │       ├── api.ts
│   │       ├── hooks.ts
│   │       ├── types.ts
│   │       └── components/
│   │           ├── record-list.tsx
│   │           ├── record-card.tsx
│   │           ├── record-edit-dialog.tsx
│   │           ├── record-create-dialog.tsx
│   │           └── record-provenance.tsx
│   │
│   ├── shared/                           # Domain-agnostic (used by 3+ domains)
│   │   ├── api/
│   │   │   └── client.ts                # Fetch wrapper (base URL, auth header, error handling)
│   │   ├── components/
│   │   │   ├── providers.tsx             # QueryClientProvider + AuthProvider
│   │   │   ├── app-sidebar.tsx
│   │   │   ├── breadcrumbs.tsx
│   │   │   ├── page-header.tsx
│   │   │   ├── empty-state.tsx
│   │   │   ├── loading-skeleton.tsx
│   │   │   └── error-boundary.tsx
│   │   ├── hooks/
│   │   │   └── use-pagination.ts
│   │   ├── types/
│   │   │   └── api.ts                   # PaginatedResponse<T>, ApiError, PaginationParams
│   │   └── utils/
│   │       └── format.ts                # Date formatting, etc.
│   │
│   ├── lib/
│   │   └── utils.ts                      # cn() helper
│   │
│   └── components/
│       └── ui/                           # shadcn-generated components (button, dialog, etc.)
│
├── public/
├── next.config.ts
├── tsconfig.json
├── components.json                       # shadcn/ui configuration
├── package.json
├── .env.example
└── .env.local
```

---

## 11. Parallel Development Strategy

The frontend and backend are developed independently against a shared API contract.

### Contract-First Workflow

1. **Define** — both sides agree on `docs/API_CONTRACT.md` and `docs/api/openapi.yaml`
2. **Frontend mocks** — API client is backed by MSW (Mock Service Worker) returning contract-conformant responses
3. **Backend validates** — backend tests verify response shapes match contract
4. **Integrate** — swap mocks for the real API base URL when both sides are ready
5. **Evolve** — changes to the contract require explicit agreement; both sides update independently

### MSW Setup

MSW intercepts `fetch` calls at the network level and returns mock responses. Mock handlers are organized by domain and return data matching the API contract types. This allows full frontend development — including loading states, error states, and pagination — without a running backend.

---

## 12. Future Considerations

| Feature | Approach |
|---------|----------|
| Real-time extraction progress | WebSocket or SSE for processing status updates; TanStack Query subscription |
| Voice input | Add "Record Audio" option to `UploadDialog`; transcription handled by backend |
| Semantic search | Add search endpoint to memory-space domain; search bar doubles as semantic search input |
| Offline support | TanStack Query persistence plugin for cached data |
| Dark mode toggle | Infrastructure is in place (see §9 Theming); add a user-facing toggle component |
| Multi-user workspaces | Add workspace members list, invite flow; role-based UI visibility |
| Global state library | Introduce Zustand if complex cross-domain client state emerges |
| E2E testing | Playwright for critical user flows (login → upload → view records) |
