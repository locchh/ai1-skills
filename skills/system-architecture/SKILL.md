---
name: system-architecture
description: >-
  System architecture guidance for Python/React full-stack projects. Use during
  the design phase when making architectural decisions — component boundaries, service
  layer design, data flow patterns, database schema planning, and technology trade-off
  analysis. Covers FastAPI layer architecture (Routes/Services/Repositories/Models),
  React component hierarchy, state management, and cross-cutting concerns (auth, errors,
  logging). Produces architecture documents and ADRs. Does NOT cover implementation
  (use python-backend-expert or react-frontend-expert) or API contract design
  (use api-design-patterns).
license: MIT
compatibility: 'Python 3.12+, FastAPI 0.115+, React 18+, SQLAlchemy 2.0+, TypeScript 5+'
metadata:
  author: platform-team
  version: '1.0.0'
  sdlc-phase: architecture
allowed-tools: Read Grep Glob
context: fork
---

# System Architecture

## When to Use

Activate this skill when:
- Designing a new module or service from scratch
- Adding a major feature that requires structural decisions
- Choosing between architectural approaches (e.g., sync vs async, monolith vs service)
- Planning database schema or refactoring existing schema
- Making frontend state management decisions
- Evaluating technology trade-offs for the project

Do NOT use this skill for:
- Writing implementation code — use `python-backend-expert` or `react-frontend-expert`
- Designing API contracts (endpoints, schemas) — use `api-design-patterns`
- Planning task lists — use `project-planner` or `task-decomposition`

## Instructions

### Project Layer Architecture

The standard architecture for a Python (FastAPI) + React project follows strict layer separation:

```
FastAPI Backend:
  Routers (HTTP concerns)
    → Services (business logic)
      → Repositories (data access)
        → Models (SQLAlchemy 2.0 ORM)
  Schemas (Pydantic v2 request/response)

React Frontend:
  Pages (route entry points)
    → Layouts (shared structure)
      → Feature Components (domain-specific)
        → Shared Components (reusable UI)
  Hooks (data fetching, business logic)
  Services (API client layer)
  Types (shared TypeScript interfaces)
```

**Dependency direction rules:**
- Routers depend on Services (never on Repositories directly)
- Services depend on Repositories (never on Models directly for queries)
- Repositories depend on Models
- Schemas are used by Routers and Services (input/output boundaries)
- **Never skip layers** — no direct DB access from routes

**What belongs in each layer:**

| Layer | Responsibilities | Forbidden |
|-------|-----------------|-----------|
| Router | HTTP status codes, request parsing, response formatting, auth enforcement | Business logic, direct DB queries |
| Service | Business rules, orchestration, domain exceptions | HTTP concepts, SQLAlchemy queries |
| Repository | SQL queries, ORM operations, data mapping | Business rules, HTTP exceptions |
| Model | Table definitions, relationships, column constraints | Business logic, validation |
| Schema | Request/response shapes, field validation, serialization | Database concerns |

See `references/layer-responsibilities.md` for detailed examples.

### Architecture Decision Framework

When making any architectural decision, follow this process:

1. **Define the requirement** — What problem are we solving? What constraints exist?
2. **Identify 2-3 options** — Never evaluate fewer than 2 alternatives
3. **Evaluate against criteria:**
   - Maintainability (can the team understand and modify this in 6 months?)
   - Testability (can each component be tested in isolation?)
   - Performance (does it meet latency/throughput requirements?)
   - Team familiarity (does the team know this technology?)
   - Ecosystem maturity (is it well-supported with documentation?)
4. **Recommend with justification** — Choose the option that best balances criteria
5. **Document as ADR** — See `references/architecture-decision-record-template.md`

### Database Schema Design

**Starting principles:**
- Start normalized (3NF) — denormalize only for proven performance needs
- Every table has: `id` (UUID or BigInt), `created_at`, `updated_at`
- Use SQLAlchemy 2.0 mapped_column syntax

**Index strategy:**
- Primary keys (automatic)
- Foreign keys (automatic in most ORMs, verify)
- Columns in frequent WHERE clauses
- Composite indexes for common multi-column filters
- Partial indexes for filtered queries (PostgreSQL)
- **Never index everything** — each index slows writes

**Migration planning (Alembic):**
- One migration per logical change
- Always include `downgrade()` function
- Test migration on copy of production data
- For data migrations: separate file from schema migrations
- Naming convention: `YYYYMMDD_HHMM_description.py`

**Relationship patterns:**
- One-to-many: foreign key on the "many" side
- Many-to-many: association table
- Self-referential: parent_id column on same table
- Polymorphic: discriminator column or separate tables (prefer separate)

### Frontend Architecture

**Component hierarchy:**
```
Pages (route-level, 1:1 with routes)
  └── Layouts (shared page structure: header, sidebar, footer)
       └── Feature Components (domain-specific: UserList, OrderForm)
            └── Shared Components (generic: Button, Modal, Table, Input)
```

**State management decision tree:**
- Server state (API data) → **TanStack Query** (useQuery, useMutation)
- Global UI state (theme, sidebar open, current user) → **React Context**
- Local component state (form input, toggle, hover) → **useState/useReducer**
- URL state (filters, pagination, search) → **URL search params**

**TanStack Query conventions:**
- Query keys: `['resource', id?]` for single, `['resource', 'list', filters?]` for lists
- Stale time: 5 minutes for most data, 0 for frequently-changing data
- Cache invalidation: invalidate on mutation success
- Optimistic updates: only for high-frequency user actions (likes, toggles)

**Data fetching architecture:**
```
Component → Custom Hook (useUsers) → TanStack Query (useQuery) → API Service (fetchUsers) → Backend
```
Never call API services directly from components — always through hooks.

### Cross-Cutting Concerns

**Authentication flow (JWT):**
1. User submits credentials → POST /auth/login
2. Backend validates → returns access_token (15min) + refresh_token (7d)
3. Frontend stores tokens → httpOnly cookie (preferred) or memory
4. API calls include Authorization: Bearer {access_token}
5. On 401 → try refresh → on refresh fail → redirect to login

**Error handling (layered):**
- Routes: catch service exceptions → map to HTTP status codes → return error response
- Services: raise domain exceptions (ValueError, PermissionError, NotFoundError)
- Repositories: catch DB exceptions (IntegrityError) → raise domain exceptions
- Frontend: TanStack Query error handling → error boundary → user-friendly message
- **Rule:** Never raise HTTPException from services or repositories

**Logging (structlog):**
- Backend: structlog with JSON output, correlation IDs via contextvars
- Frontend: console (dev), structured reporting (production)
- Log levels: DEBUG (dev only), INFO (requests, key actions), WARNING (recoverable issues), ERROR (failures)
- **Never log secrets, passwords, or full request bodies with sensitive data**

**Configuration:**
- Backend: pydantic-settings (BaseSettings), loaded from environment variables
- Frontend: environment variables via Vite (VITE_* prefix)
- Secrets: never in code, always from environment or secret manager

## Examples

### Example: Architecture Decision — Real-Time Notifications

**Requirement:** Users should see notifications in real-time without refreshing.

**Option A: WebSocket**
- Pros: True real-time, bidirectional, efficient for high-frequency updates
- Cons: More complex server infrastructure, connection management, harder to scale

**Option B: Server-Sent Events (SSE)**
- Pros: Simpler than WebSocket, HTTP-based (works through proxies), one-directional
- Cons: One-directional only, limited browser connections per domain

**Option C: Polling (TanStack Query refetchInterval)**
- Pros: Simplest implementation, no infrastructure changes, works everywhere
- Cons: Not truly real-time (delay = poll interval), wastes bandwidth if no updates

**Recommendation:** Start with **Option C (Polling)** at 30-second intervals. For a team under 10 with moderate notification volume, this is the simplest solution. Upgrade to SSE if polling bandwidth becomes a problem. Upgrade to WebSocket only if bidirectional communication is needed.

**ADR:** Documented in `references/architecture-decision-record-template.md`

## Edge Cases

- **Monolith vs microservices**: Default to modular monolith for teams under 10. Extract services only when a module has genuinely different scaling requirements or deployment cadence.
- **When to break the layer pattern**: Background tasks and event handlers may bypass the router layer. They should still use services and repositories — never access DB directly.
- **Shared code between backend and frontend**: Use OpenAPI schema generation to keep types in sync. Never maintain duplicate type definitions manually.
- **Legacy code integration**: Wrap legacy modules behind a repository or service interface. Never let legacy patterns leak into new architecture.
