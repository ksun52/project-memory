---
description: TypeScript coding standards and best practices for modern web development
globs: **/*.ts, **/*.tsx, **/*.d.ts
---

# TypeScript

## Types
- Prefer interfaces for object shapes, types for unions/intersections/mapped types
- Use `unknown` over `any`
- Leverage built-in utility types and generics
- Use readonly for immutable properties
- Use discriminated unions and type guards for type safety
                                                                                                                                                    
## Naming
- PascalCase for types/interfaces, camelCase for variables/functions, UPPER_CASE for constants
- Descriptive names with auxiliary verbs (isLoading, hasError)
- Suffix React prop interfaces with `Props`

## Organization
- Keep types close to usage; shared types in a `types/` directory
- Explicit return types for public functions
- Use async/await over raw Promises