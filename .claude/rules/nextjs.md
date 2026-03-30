---
description: Next.js with TypeScript and Tailwind UI best practices
globs: **/*.tsx, **/*.ts, src/**/*.ts, src/**/*.tsx
---

# Next.js                                                                                                                                           
                  
## Structure
- Use App Router directory structure
- Route-specific components in `app/`, shared components in `components/`
- Utilities in `lib/`, lowercase-with-dashes for directories

## Components
- Server Components by default, explicit 'use client' when needed
- Wrap client components in Suspense with fallback
- Dynamic loading for non-critical components
- Implement error boundaries

## Data & State
- Fetch data in Server Components when possible
- Handle loading and error states for all routes
- Minimize client-side state