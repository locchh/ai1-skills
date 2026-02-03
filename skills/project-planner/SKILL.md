---
name: project-planner
description: >-
  Project planning and feature breakdown for Python/React full-stack projects.
  Use during the planning phase when breaking down feature requests, user stories,
  or product requirements into implementation plans. Guides identification of affected
  files and modules, defines acceptance criteria, maps task dependencies, and estimates
  complexity. Produces structured task lists with file paths and verification steps.
  Does NOT cover architecture decisions (use system-architecture) or implementation
  (use python-backend-expert or react-frontend-expert).
license: MIT
compatibility: 'Python 3.12+, React 18+, FastAPI, SQLAlchemy, TypeScript'
metadata:
  author: platform-team
  version: '1.0.0'
  sdlc-phase: planning
allowed-tools: Read Grep Glob
context: fork
---

# Project Planner

## When to Use

Activate this skill when:
- Breaking down feature requests or user stories into implementation tasks
- Sprint planning or backlog refinement for a Python/React project
- Planning a new module, service, or cross-cutting feature
- Estimating complexity of a proposed change
- Identifying dependencies between tasks before starting implementation
- A stakeholder asks "how should we build this?"

Do NOT use this skill for:
- Architecture decisions (component boundaries, technology choices) — use `system-architecture`
- Generating implementation code — use `python-backend-expert` or `react-frontend-expert`
- API contract design — use `api-design-patterns`
- Breaking down tasks that are already well-defined into subtasks — use `task-decomposition`

## Instructions

### Planning Workflow

Follow these five steps in order for every planning request.

#### Step 1: Analyze the Requirement

1. Read the feature request, user story, or product requirement in full
2. Identify the **inputs** (what triggers the feature) and **outputs** (what the user sees or what changes)
3. List any **ambiguities** — questions that must be answered before implementation
4. If ambiguities exist, ask the user to clarify before proceeding
5. Write a one-sentence **objective statement**: "This feature allows [who] to [do what] so that [why]"

#### Step 2: Map Affected Modules

Identify every file and module that will be created or modified. Use this checklist:

**Backend (Python/FastAPI):**
- Routes: `app/routers/` — new or modified endpoint files
- Services: `app/services/` — business logic modules
- Repositories: `app/repositories/` — data access layer
- Models: `app/models/` — SQLAlchemy ORM models
- Schemas: `app/schemas/` — Pydantic request/response models
- Migrations: `alembic/versions/` — database migration files
- Dependencies: `app/dependencies.py` — FastAPI Depends() additions
- Config: `app/core/config.py` — new settings or environment variables

**Frontend (React/TypeScript):**
- Pages: `src/pages/` — new or modified page components
- Components: `src/components/` — shared or feature-specific components
- Hooks: `src/hooks/` — custom hooks (useXxx)
- Services: `src/services/` — API client functions
- Types: `src/types/` — TypeScript interfaces and types
- Tests: `src/__tests__/` or co-located `.test.tsx` files

**Shared:**
- API contract: OpenAPI schema changes
- Environment variables: `.env` additions
- Dependencies: `requirements.txt` / `package.json` additions

Run `Glob` and `Grep` on the codebase to confirm which files already exist and which must be created.

#### Step 3: Decompose into Tasks

Break the feature into ordered implementation tasks. Each task must satisfy:
- **Touches 1-3 files** — if more, split further
- **Has a single clear outcome** — one testable result
- **Includes a verification command** — `pytest`, `npm test`, manual check, or API call
- **Has explicit preconditions** — which tasks must be done first

Use this ordering principle:
1. Database model changes and migrations
2. Backend schemas (Pydantic models)
3. Backend repository layer
4. Backend service layer
5. Backend route/endpoint
6. Shared types (if TypeScript types generated from OpenAPI)
7. Frontend API service functions
8. Frontend hooks
9. Frontend components and pages
10. Tests for each layer (can be interleaved with TDD)
11. Integration and E2E tests

#### Step 4: Define Verification Steps

For each task, specify:
- **Command to run**: exact CLI command (e.g., `pytest tests/unit/test_users.py -k test_create_user`)
- **Expected result**: what "pass" looks like (status code, output text, behavior)
- **Rollback if failed**: what to undo or check if verification fails

#### Step 5: Identify Risks and Unknowns

Review the plan against common risk categories. See `references/risk-assessment-checklist.md` for the full checklist. Flag any item that applies:
- Data migration risks (schema changes, data loss potential)
- API breaking changes (existing consumers affected)
- Authentication/authorization changes (security surface changes)
- Performance regression (new queries, additional API calls, large payloads)
- Third-party dependency risks (new packages, version conflicts)
- Cross-cutting concerns (middleware changes, shared utility changes)

### Output Format

Produce a structured plan document following the template in `references/plan-template.md`. The plan must include:

1. **Objective** — one sentence
2. **Affected Modules** — file paths grouped by layer
3. **Task List** — ordered tasks with files, preconditions, verification
4. **Dependency Graph** — which tasks block which
5. **Risk Assessment** — flagged risks with mitigation
6. **Acceptance Criteria** — how to verify the feature is complete
7. **Estimated Complexity** — overall sizing (see below)

### Estimation Heuristics

| Size | Files | Lines Changed | Tests Needed | Typical Duration |
|------|-------|---------------|-------------|-----------------|
| Trivial | 1 file | <20 lines | None or 1 unit test | — |
| Small | 1-2 files | <100 lines | Unit tests | — |
| Medium | 3-5 files | <300 lines | Unit + integration tests | — |
| Large | 6+ files | 300+ lines | Full test suite, may need migration | — |

Assign a size to each task AND to the overall feature.

### Dependency Mapping Rules

- Database model changes **must precede** service layer changes
- Backend API endpoints **must precede** frontend integration
- Shared types and schemas **must precede** both backend and frontend consumers
- Tests should follow implementation of each layer (or precede with TDD)
- Migrations **must be tested** before deploying dependent code
- If two tasks have no dependency, they can be worked in parallel — note this explicitly

### Common Planning Patterns for FastAPI + React

**CRUD Feature:**
1. Model + migration → 2. Schemas → 3. Repository → 4. Service → 5. Router → 6. Frontend service → 7. Hook → 8. Component → 9. Tests

**Auth-Protected Feature:**
1. Auth dependency (if new) → 2. Permission model → 3-9. Same as CRUD with auth decorators

**Search/Filter Feature:**
1. Query parameters schema → 2. Repository filter method → 3. Service + router → 4. Frontend hook with debounce → 5. Search component → 6. Tests

**File Upload Feature:**
1. Storage service → 2. Upload endpoint (multipart) → 3. Model field for file reference → 4. Frontend upload component → 5. Preview component → 6. Tests

## Examples

### Example: Add User Profile Picture Upload

**Objective:** Allow users to upload and display a profile picture.

**Affected Modules:**
- Backend: `app/models/user.py`, `app/schemas/user.py`, `app/services/storage_service.py` (new), `app/routers/users.py`, `alembic/versions/xxx_add_avatar_url.py`
- Frontend: `src/components/AvatarUpload.tsx` (new), `src/hooks/useUploadAvatar.ts` (new), `src/pages/ProfilePage.tsx`, `src/services/userService.ts`

**Task List:**
1. **Add avatar_url column** — Files: `app/models/user.py`, `alembic/versions/` — Preconditions: none — Verify: `alembic upgrade head` succeeds, column exists
2. **Create storage service** — Files: `app/services/storage_service.py` — Preconditions: none — Verify: unit test passes
3. **Add avatar schemas** — Files: `app/schemas/user.py` — Preconditions: Task 1 — Verify: schema validates
4. **Add upload endpoint** — Files: `app/routers/users.py` — Preconditions: Tasks 2, 3 — Verify: `pytest tests/integration/test_users.py -k test_upload_avatar`
5. **Add frontend upload hook** — Files: `src/hooks/useUploadAvatar.ts` — Preconditions: Task 4 — Verify: `npm test -- useUploadAvatar`
6. **Add AvatarUpload component** — Files: `src/components/AvatarUpload.tsx` — Preconditions: Task 5 — Verify: component renders, handles file selection
7. **Integrate into ProfilePage** — Files: `src/pages/ProfilePage.tsx` — Preconditions: Task 6 — Verify: manual test — upload, refresh, avatar displays

**Complexity:** Medium (7 tasks, 9 files, unit + integration tests)

## Edge Cases

- **Cross-cutting changes** (auth middleware, error handling, logging): Flag for architecture review before planning implementation. These affect many files and may need their own planning session.
- **Database migrations with data transformation**: Always plan the migration as a separate task with its own rollback strategy. Never combine schema migration with data migration in one step.
- **Frontend state cascades**: When a change affects shared state (context, global store), map the full component tree that depends on it. Use React DevTools to trace consumers.
- **Breaking API changes**: If an endpoint contract changes, plan a versioning strategy (new endpoint, deprecation header) before implementation. Check who consumes the API.
- **Feature flags**: For large features, consider adding a feature flag task at the beginning. This allows partial deployment and rollback without code revert.
- **Third-party dependency additions**: Verify license compatibility, check for known vulnerabilities (npm audit, pip-audit), and pin exact versions in the plan.
