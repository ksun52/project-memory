# Frontend Architecture Reference

A guide to the key patterns and libraries used in the Project Memory frontend.

---

## Table of Contents

1. [Tech Stack Overview](#tech-stack-overview)
2. [React Query (TanStack Query)](#react-query-tanstack-query)
3. [Providers & Context](#providers--context)
4. [MSW (Mock Service Worker)](#msw-mock-service-worker)
5. [Auth System](#auth-system)
6. [API Client](#api-client)
7. [Directory Structure](#directory-structure)

---

## Tech Stack Overview

| Library | Purpose |
|---------|---------|
| Next.js 16 (App Router) | Framework — routing, SSR, server components |
| React 19 | UI rendering |
| TypeScript | Type safety |
| TanStack React Query | Server state management (fetching, caching, mutations) |
| Tailwind CSS v4 | Utility-first styling |
| shadcn/ui (base-nova) | Pre-built UI components using Base UI primitives |
| MSW | API mocking during development |
| Sonner | Toast notifications |
| Lucide React | Icons |

---

## React Query (TanStack Query)

React Query manages **server state** — data that lives on the backend and needs to be fetched, cached, and kept in sync.

### The Problem It Solves

Without React Query, every component that needs data repeats the same pattern:

```tsx
const [data, setData] = useState(null);
const [loading, setLoading] = useState(true);
const [error, setError] = useState(null);

useEffect(() => {
  fetch("/api/workspaces")
    .then(res => res.json())
    .then(setData)
    .catch(setError)
    .finally(() => setLoading(false));
}, []);
```

This gets messy fast — no caching, no deduplication, no background refetching, and every component manages its own loading/error state.

### How We Use It

**Queries** (reading data):

```tsx
const { data, isLoading, error } = useQuery({
  queryKey: ["workspaces"],        // unique cache key
  queryFn: () => listWorkspaces(), // function that returns a promise
});
```

**Mutations** (creating/updating/deleting data):

```tsx
const createMutation = useMutation({
  mutationFn: (data) => createWorkspace(data),
  onSuccess: () => {
    // Invalidate the cache so the list refetches
    queryClient.invalidateQueries({ queryKey: ["workspaces"] });
  },
});

// Use it:
createMutation.mutate({ name: "New Workspace" });
```

### Key Behaviors

- **Caching**: If two components request the same `queryKey`, only one fetch fires. The second gets cached data.
- **Stale time**: Data is considered fresh for 60 seconds (configured in `providers.tsx`). No refetch during that window.
- **Background refetching**: When you revisit a page, cached data renders immediately while a background refetch runs. If data changed, the UI updates seamlessly.
- **Cache invalidation**: After a mutation, you invalidate related query keys. React Query automatically refetches the stale data.
- **Retry**: Failed queries retry once by default (configured in `providers.tsx`).

### Query Keys

Query keys are arrays that uniquely identify cached data:

```tsx
["workspaces"]                    // all workspaces
["workspaces", workspaceId]       // single workspace
["memory-spaces", workspaceId]    // memory spaces for a workspace
["auth", "me"]                    // current user
```

Invalidating `["workspaces"]` also invalidates `["workspaces", id]` because React Query matches by prefix.

### File: `shared/components/providers.tsx`

```tsx
<QueryClientProvider client={queryClient}>  {/* makes React Query available to all children */}
  <AuthProvider>{children}</AuthProvider>
</QueryClientProvider>
```

---

## Providers & Context

### What Are Providers?

React components can only pass data **down** through props. Without providers, if a deeply nested component needs data (like the current user), every intermediate component must pass it along — this is called "prop drilling":

```
Layout → Sidebar → NavSection → UserDisplay
         (each passes `user` as a prop — tedious and fragile)
```

Providers use React Context to **broadcast** state to any descendant:

```
AuthProvider (holds user state)
  └─ Layout
       └─ Sidebar
            └─ NavSection
                 └─ UserDisplay   ← reads user directly via useAuth()
```

No intermediate components need to know about `user`.

### How They Work

A provider has two parts:

1. **The Provider component** — wraps a section of the tree and holds state
2. **A hook** — lets any descendant read that state

```tsx
// Provider holds the state
<AuthProvider>
  {children}   {/* anything in here can call useAuth() */}
</AuthProvider>

// Any descendant reads it
function UserDisplay() {
  const { user } = useAuth();
  return <span>{user.display_name}</span>;
}
```

### Our Provider Stack

Providers are nested in a specific order because each layer may depend on the one above it:

```tsx
<MswProvider>              {/* 1. Ensures mock service worker is ready before any API calls */}
  <QueryClientProvider>    {/* 2. React Query is available for data fetching */}
    <AuthProvider>         {/* 3. Auth can call /auth/me via React Query */}
      {children}           {/* 4. App components can use useAuth() and useQuery() */}
    </AuthProvider>
  </QueryClientProvider>
</MswProvider>
```

**Why this order matters:**
- `MswProvider` must be outermost — it blocks rendering until the service worker is registered, preventing API calls from hitting a non-existent server
- `QueryClientProvider` comes next — `AuthProvider` uses API calls internally, which need React Query
- `AuthProvider` is innermost — app components need both auth context and React Query

---

## MSW (Mock Service Worker)

MSW intercepts HTTP requests **at the network level** using a browser Service Worker. Your app code makes real `fetch()` calls, but the Service Worker catches them and returns mock responses. The app doesn't know the difference.

### Request Flow

```
App calls fetch("/api/v1/workspaces")
        ↓
Browser Service Worker intercepts (before the request leaves the browser)
        ↓
MSW matches the URL to a handler you defined
        ↓
Handler returns a mock JSON response
        ↓
App receives it as if a real server responded
```

### File Structure

```
src/mocks/
├── browser.ts              # Creates the MSW worker instance with all handlers
├── init.ts                 # Conditionally starts MSW (only in dev, only in browser)
├── msw-provider.tsx        # React component that blocks rendering until worker is ready
├── seed-data.ts            # Typed mock data (users, workspaces, memory spaces)
└── handlers/
    ├── index.ts            # Barrel — combines all handlers into one array
    ├── auth.ts             # GET /auth/me, /auth/login, /auth/callback, POST /auth/logout
    ├── workspace.ts        # 5 CRUD endpoints with in-memory array
    └── memory-space.ts     # 7 endpoints (5 CRUD + 2 stubs returning 501)
```

### How Each Part Works

**`seed-data.ts`** — The fake database. Typed arrays of mock users, workspaces, and memory spaces. Handlers import these as their initial state.

**`handlers/*.ts`** — Route handlers using MSW's `http.get()`, `http.post()`, etc. They match URLs and return responses. Workspace and memory-space handlers maintain mutable in-memory arrays, so create/update/delete persist during a session (reset on page reload).

**`browser.ts`** — `setupWorker(...handlers)` creates the MSW worker instance with all handlers registered.

**`init.ts`** — Guards against running on the server (Next.js SSR) and only starts if `NEXT_PUBLIC_ENABLE_MSW=true`. Uses `onUnhandledRequest: "bypass"` so unmatched requests (Next.js internals, etc.) pass through.

**`msw-provider.tsx`** — Solves a race condition: without it, components could fire API calls before the Service Worker is registered. It renders `null` until MSW is ready, then renders children.

### URL Matching

Handlers specify the full URL to match:

```ts
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
http.get(`${BASE}/workspaces`, ...)
```

`BASE` uses the same env var as the API client, so they stay in sync.

### Turning Off MSW

Set `NEXT_PUBLIC_ENABLE_MSW=false` in `.env.local` — all requests go to the real backend. No code changes needed.

---

## Auth System

### Overview

Auth uses a token-based flow. In production this will be WorkOS SSO; in development, MSW mocks the entire flow with a dev token.

### Files

```
src/domains/auth/
├── types.ts                # User, TokenResponse, AuthState types
├── api.ts                  # getMe(), login(), callback(), logout() — API functions
├── hooks.ts                # useCurrentUser(), useLogout() — React Query wrappers
├── auth-provider.tsx       # AuthProvider context + useAuth() hook
└── components/
    ├── login-form.tsx      # Sign-in button
    └── auth-guard.tsx      # Route protection wrapper
```

### Login Flow

```
1. User visits /login → sees LoginForm
2. Clicks "Sign in" → calls login() API
3. API returns { redirect_url: "/auth/callback?code=dev" }
4. Browser navigates to /auth/callback?code=dev
5. Callback page calls callback("dev") API → gets { access_token: "..." }
6. Token stored in AuthProvider → triggers getMe() call
7. getMe() succeeds → authState becomes "authenticated"
8. AuthGuard allows rendering → user sees dashboard
```

### Auth Provider Lifecycle

On mount:
1. In MSW mode, auto-sets a dev token (so the login flow is automatic)
2. Wires the token into `apiClient` via `setTokenGetter()` — every subsequent API call includes `Authorization: Bearer <token>`
3. Calls `GET /auth/me` to validate the token
4. If valid: stores user, sets `authState: "authenticated"`
5. If invalid: clears token, sets `authState: "unauthenticated"`

### Auth Guard

Wraps routes that require authentication:
- `authState === "loading"` → shows loading indicator
- `authState === "unauthenticated"` → redirects to `/login`
- `authState === "authenticated"` → renders children

---

## API Client

**File:** `shared/api/client.ts`

A thin wrapper around `fetch()` that handles:

- **Base URL**: Reads from `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000/api/v1`)
- **Auth token**: Injected via `setTokenGetter()` — called by AuthProvider when the token changes
- **Content type**: Auto-sets `Content-Type: application/json` (skips for FormData)
- **Error handling**: Non-OK responses are parsed as `ApiError` objects and thrown
- **204 responses**: Returns `undefined` (for DELETE endpoints)

```ts
apiClient.get<Workspace[]>("/workspaces")
apiClient.post<Workspace>("/workspaces", { name: "Acme" })
apiClient.patch<Workspace>("/workspaces/123", { name: "Updated" })
apiClient.del("/workspaces/123")
```

---

## Directory Structure

```
frontend/src/
├── app/                          # Next.js App Router pages and layouts
│   ├── (auth)/                   # Auth route group (no sidebar)
│   │   ├── login/page.tsx
│   │   └── auth/callback/page.tsx
│   ├── (dashboard)/              # Dashboard route group (with sidebar)
│   │   ├── layout.tsx            # AuthGuard + Sidebar shell
│   │   └── workspaces/...
│   ├── layout.tsx                # Root layout (MswProvider → Providers)
│   ├── page.tsx                  # Redirects to /workspaces
│   └── globals.css               # Tailwind theme + CSS variables
├── components/ui/                # shadcn/ui components (auto-generated)
├── domains/                      # Domain-driven feature modules
│   ├── auth/                     # types, api, hooks, provider, components
│   ├── workspace/                # types, api, hooks, components
│   └── memory-space/             # types, api, hooks, components
├── lib/
│   └── utils.ts                  # cn() utility for Tailwind class merging
├── mocks/                        # MSW mock layer (dev only)
│   ├── handlers/                 # Mock API route handlers
│   ├── seed-data.ts              # Mock data
│   └── ...
└── shared/                       # Cross-domain shared code
    ├── api/client.ts             # API client
    ├── components/               # Shared UI (sidebar, breadcrumbs, etc.)
    ├── hooks/                    # Shared hooks (pagination, etc.)
    └── types/api.ts              # Shared API types (PaginatedResponse, etc.)
```

### Domain Module Pattern

Each domain follows the same structure:

```
domains/{domain}/
├── types.ts          # TypeScript interfaces matching the API contract
├── api.ts            # API functions (thin wrappers around apiClient)
├── hooks.ts          # React Query hooks (useQuery/useMutation wrappers)
└── components/       # Domain-specific UI components
```

This keeps related code together and makes it easy to find things by feature rather than by file type.
