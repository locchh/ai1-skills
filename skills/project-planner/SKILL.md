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
- Breaking down a feature request or user story into implementation tasks
- Sprint planning or backlog refinement for a Python/React project
- Designing a new module, service, or feature area
- Estimating the complexity of a proposed change
- Identifying file-level dependencies before starting implementation
- Mapping the impact of a change across backend and frontend layers

Do NOT use this skill for:
- Architecture decisions or technology trade-offs (use `system-architecture`)
- Writing implementation code (use `python-backend-expert` or `react-frontend-expert`)
- API contract design (use `api-design-patterns`)
- Task decomposition into atomic sub-tasks (use `task-decomposition`)

## Instructions

### Planning Workflow

Follow this 5-step workflow for every planning request:

#### Step 1: Analyze the Requirement

1. Read the feature request, user story, or product requirement in full
2. Identify the core objective — what value does this deliver?
3. List explicit inputs (what triggers the feature) and outputs (what the user sees)
4. Note ambiguities or missing details — list them as open questions
5. Determine if this is a new feature, enhancement, bug fix, or refactoring

#### Step 2: Map Affected Modules

Scan the project and identify every file or module area affected by the change:

**Backend (FastAPI):**
- `routes/` — New or modified endpoint handlers
- `services/` — Business logic changes
- `repositories/` — Data access layer changes
- `models/` — SQLAlchemy model changes (triggers migration)
- `schemas/` — Pydantic request/response schema changes
- `core/` — Configuration, security, or middleware changes
- `migrations/` — Alembic migration files

**Frontend (React/TypeScript):**
- `pages/` — New or modified page components
- `components/` — Shared UI component changes
- `hooks/` — Custom hook changes or additions
- `services/` — API client changes (TanStack Query keys, mutations)
- `types/` — Shared TypeScript type definitions
- `utils/` — Utility function changes

**Shared / Cross-cutting:**
- `types/` or `shared/` — Types shared between backend and frontend
- `.env` / config — Environment variable changes
- `tests/` — Test files for each changed module

Present the module map as a table:

```
| Layer    | Module           | Change Type       | Impact    |
|----------|-----------------|-------------------|-----------|
| Backend  | models/user.py  | Add field         | Migration |
| Backend  | schemas/user.py | Add response field| API change|
| Frontend | hooks/useUser.ts| Update query      | UI change |
```

#### Step 3: Decompose into Tasks

Break the feature into ordered implementation tasks. Each task must:
- Touch at most 3 files
- Have a single, clear outcome
- Include a verification command (pytest, npm test, or manual check)
- List explicit preconditions (which other tasks must complete first)

Use this format for each task:

```
### Task [N]: [Title]
- **Files:** [list of files to create or modify]
- **Preconditions:** [task numbers that must be done first, or "None"]
- **Steps:**
  1. [Specific action]
  2. [Specific action]
- **Done when:** [concrete verification — command + expected output]
- **Complexity:** [trivial / small / medium / large]
```

#### Step 4: Define Verification Steps

For each task, specify:
- **Command to run:** `pytest tests/unit/test_user.py -x` or `npm test -- --grep "UserProfile"`
- **What to check:** Expected status code, UI element, database state
- **Expected output:** Specific assertion or observable result

For the overall feature, define integration verification:
- End-to-end test scenario describing the complete user flow
- Manual smoke test steps if automated E2E is not available

#### Step 5: Identify Risks and Unknowns

Flag potential issues using the categories below. For each risk:
- **Risk:** Description of what could go wrong
- **Likelihood:** Low / Medium / High
- **Mitigation:** How to reduce or eliminate the risk

See `references/risk-assessment-checklist.md` for the complete risk category list.

### Output Format

Produce a plan document with this structure (or see `references/plan-template.md`):

```markdown
# Implementation Plan: [Feature Name]

## Objective
[1-2 sentence summary of what this delivers]

## Affected Modules
[Module map table from Step 2]

## Task List
[Ordered tasks from Step 3]

## Verification
[Integration verification from Step 4]

## Risks & Unknowns
[Risk table from Step 5]

## Acceptance Criteria
[Bullet list of observable outcomes that confirm the feature works]
```

### Estimation Heuristics

Use these guidelines to estimate task complexity:

| Complexity | Files | Lines Changed | Tests Needed          | Migration |
|-----------|-------|--------------|----------------------|-----------|
| Trivial   | 1     | <20          | None                 | No        |
| Small     | 1-2   | <100         | Unit tests           | No        |
| Medium    | 3-5   | <300         | Unit + integration   | Maybe     |
| Large     | 6+    | 300+         | Full test suite      | Likely    |

Overall feature complexity = highest individual task complexity + integration overhead.

### Dependency Mapping Rules

When ordering tasks, follow these dependency rules:

1. **Database model changes** must precede service layer changes
2. **Alembic migrations** must be created and tested before code that depends on new schema
3. **Backend API endpoints** must precede frontend integration
4. **Shared types** must precede both backend and frontend code
5. **Service layer** must precede route handlers
6. **Tests** should follow implementation of each layer (not all at the end)
7. **Configuration changes** (.env, settings) should come early if other tasks depend on them

## Examples

### Example: Plan "Add User Profile Picture Upload"

**Objective:** Allow users to upload and display a profile picture.

**Affected Modules:**

| Layer    | Module                    | Change Type    | Impact       |
|----------|--------------------------|----------------|-------------|
| Backend  | models/user.py           | Add avatar_url | Migration    |
| Backend  | schemas/user.py          | Add field      | API contract |
| Backend  | services/upload.py       | New service    | New file     |
| Backend  | routes/users.py          | Add endpoint   | API change   |
| Frontend | components/AvatarUpload  | New component  | UI change    |
| Frontend | hooks/useUploadAvatar.ts | New hook       | Data fetch   |
| Frontend | pages/ProfilePage.tsx    | Integrate      | UI change    |

**Task List:**

### Task 1: Add avatar_url to User model
- **Files:** models/user.py, migrations/
- **Preconditions:** None
- **Steps:** Add `avatar_url: Mapped[str | None]` to User model, generate Alembic migration
- **Done when:** `alembic upgrade head` succeeds, `avatar_url` column exists in DB
- **Complexity:** small

### Task 2: Update User schemas
- **Files:** schemas/user.py
- **Preconditions:** Task 1
- **Steps:** Add `avatar_url` to `UserResponse` schema
- **Done when:** `pytest tests/unit/test_schemas.py -x` passes
- **Complexity:** trivial

### Task 3: Create upload service
- **Files:** services/upload.py, tests/unit/test_upload.py
- **Preconditions:** Task 1
- **Steps:** Implement file validation (type, size), storage (local or S3), URL generation
- **Done when:** `pytest tests/unit/test_upload.py -x` passes
- **Complexity:** medium

### Task 4: Add upload endpoint
- **Files:** routes/users.py, tests/integration/test_users.py
- **Preconditions:** Tasks 2, 3
- **Steps:** Add `POST /users/{id}/avatar` endpoint accepting multipart/form-data
- **Done when:** `pytest tests/integration/test_users.py -x` passes with upload test
- **Complexity:** small

### Task 5: Create AvatarUpload component
- **Files:** components/AvatarUpload.tsx, components/AvatarUpload.test.tsx
- **Preconditions:** Task 4
- **Steps:** File picker, preview, upload via useMutation, progress indicator
- **Done when:** `npm test -- --grep "AvatarUpload"` passes
- **Complexity:** medium

### Task 6: Integrate into ProfilePage
- **Files:** pages/ProfilePage.tsx, hooks/useUploadAvatar.ts
- **Preconditions:** Task 5
- **Steps:** Add AvatarUpload to profile page, create upload hook with TanStack Query
- **Done when:** `npm test -- --grep "ProfilePage"` passes, avatar displays after upload
- **Complexity:** small

**Risks:**
- File size limits need validation (server + client) — Medium likelihood — Add early validation
- S3 permissions may need configuration — Low likelihood — Test with local storage first

## Edge Cases

- **Cross-cutting changes** (auth middleware, error handling, logging): These affect many files. Flag for architecture review before planning tasks. Consider whether the change should be its own plan.

- **Database migrations with data transformation**: Always plan the migration as a separate task. Test rollback (`alembic downgrade -1`) as part of verification. Never combine migration with code changes in the same task.

- **Frontend state cascades**: When modifying shared state (React Context, TanStack Query cache), map the component tree to identify all consumers. Plan verification for each affected component.

- **API breaking changes**: If modifying an existing endpoint's contract, check for frontend consumers first. Consider API versioning if external consumers exist. Plan frontend updates in the same sprint.

- **Feature flags**: For large features spanning multiple sprints, plan a feature flag as Task 1. All subsequent tasks should be gated behind the flag. Plan flag removal as the final task.

- **Third-party dependency updates**: If the feature requires a new package, plan installation and lockfile updates as a dedicated task. Check for peer dependency conflicts.
