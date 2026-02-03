---
name: task-decomposition
description: >-
  Decompose high-level objectives into atomic implementation tasks for Python/React
  projects. Use when breaking down large features, multi-file changes, or tasks
  requiring more than 3 steps. Produces independently-verifiable tasks with done-conditions,
  file paths, complexity estimates, and explicit ordering. Creates persistent task files
  (task_plan.md, progress.md) to track state across context windows. Does NOT cover
  high-level planning (use project-planner) or architecture decisions (use system-architecture).
license: MIT
compatibility: 'Python 3.12+, React 18+, FastAPI, TypeScript'
metadata:
  author: platform-team
  version: '1.0.0'
  sdlc-phase: planning
allowed-tools: Read Grep Glob Write
context: fork
---

# Task Decomposition

## When to Use

Activate this skill when:
- A large feature requires 4+ implementation steps
- Multi-file changes span both backend and frontend
- Tracking progress across context windows is needed
- The user says "break this down", "decompose", "create subtasks", or "what are the steps?"
- A previously-planned feature needs to be turned into executable tasks

Do NOT use this skill for:
- High-level planning and risk assessment — use `project-planner`
- Architecture decisions — use `system-architecture`
- Single-file changes or trivial fixes — just do them directly

## Instructions

### Decomposition Rules

Every task produced by this skill must satisfy ALL of the following:

1. **Atomic scope**: Touches at most 2-3 files
2. **Independently verifiable**: Has a concrete command that proves completion
3. **Single outcome**: One clear, testable result per task
4. **Explicit preconditions**: Lists which other task IDs must be done first
5. **Sized**: Assigned a complexity (trivial/small/medium/large)

If a task touches >3 files or changes >200 lines, split it further.

### Task Template

Use this format for every task:

```
### Task [N]: [Title]
- **Files:** [list of files to create/modify]
- **Preconditions:** [task IDs that must be done first, or "none"]
- **Steps:**
  1. [concrete action]
  2. [concrete action]
- **Done when:** [exact verification command and expected output]
- **Complexity:** trivial | small | medium | large
- **Parallel:** [can run alongside Task X | must be sequential]
```

### Decomposition Process

1. **Read the objective** — Understand the full scope from user input or an existing plan
2. **Identify layers** — Which layers are affected? (model, schema, repo, service, router, type, service, hook, component, page, test)
3. **Create tasks per layer** — One task per layer per feature unit. Use this default ordering:
   - Infrastructure and shared code first
   - Database models and migrations
   - Backend schemas (Pydantic)
   - Backend repository
   - Backend service
   - Backend router/endpoint
   - Shared TypeScript types
   - Frontend API service
   - Frontend hooks
   - Frontend components and pages
   - Unit tests (per layer)
   - Integration tests
   - E2E tests (if applicable)
4. **Map dependencies** — Draw precondition chains. Look for parallelization opportunities.
5. **Assign complexity** — Use these heuristics:
   - **Trivial**: 1 file, <20 lines, no new tests needed
   - **Small**: 1-2 files, <100 lines, unit tests
   - **Medium**: 2-3 files, <200 lines, unit + integration tests
   - **Large**: 3+ files, 200+ lines, full test coverage
6. **Write persistent files** — Save decomposition to disk (see below)

### Persistent Task Files

Create these files in the project root to track state across context windows:

**task_plan.md** — The complete task list:
```markdown
# Task Plan: [Feature Name]

Status: IN_PROGRESS
Total tasks: [N]
Completed: [M]

[All tasks in template format]
```

**progress.md** — Current state:
```markdown
# Progress

## Current Task
Task [N]: [Title]
Status: [not started | in progress | blocked | done]

## Completed
- [x] Task 1: [Title]
- [x] Task 2: [Title]

## Next Up
- [ ] Task 3: [Title]

## Blockers
[Any issues discovered during work]
```

**findings.md** — Notes discovered during implementation:
```markdown
# Findings

## Decisions Made
- [decision and rationale]

## Blockers Encountered
- [blocker and resolution]

## Scope Changes
- [any tasks added or removed and why]
```

Update these files after completing each task. This allows recovery if the context window resets.

### Prioritization Rules

When multiple tasks have no dependency between them, prioritize in this order:
1. Infrastructure and configuration
2. Shared code and types
3. Backend implementation
4. Frontend implementation
5. Tests
6. Documentation

### Handling Scope Changes

If during implementation you discover:
- A task is larger than estimated → Split it and update task_plan.md
- A new task is needed → Add it with correct preconditions
- A task is unnecessary → Mark as "SKIPPED" with reason
- A circular dependency exists → Restructure to break the cycle

Always update the persistent files when scope changes.

## Examples

### Example: Decompose "Add Search to Users List"

**Objective:** Add server-side search to the users list page with debounced input.

**Tasks:**

### Task 1: Add search query parameter to user repository
- **Files:** `app/repositories/user_repository.py`
- **Preconditions:** none
- **Steps:**
  1. Add `search(self, query: str, limit: int, offset: int)` method
  2. Use `ilike` for case-insensitive search on name and email
- **Done when:** `pytest tests/unit/test_user_repository.py -k test_search` passes
- **Complexity:** small
- **Parallel:** Can run alongside Task 2

### Task 2: Add search schema
- **Files:** `app/schemas/user.py`
- **Preconditions:** none
- **Steps:**
  1. Add `UserSearchParams` schema with `q: str | None`, `limit: int`, `offset: int`
- **Done when:** Schema validates with sample data
- **Complexity:** trivial
- **Parallel:** Can run alongside Task 1

### Task 3: Add search endpoint
- **Files:** `app/routers/users.py`, `app/services/user_service.py`
- **Preconditions:** Task 1, Task 2
- **Steps:**
  1. Add `search_users` method to service
  2. Add `GET /users/search?q=&limit=&offset=` endpoint
- **Done when:** `pytest tests/integration/test_users.py -k test_search_users` passes
- **Complexity:** small

### Task 4: Add frontend search hook
- **Files:** `src/hooks/useSearchUsers.ts`
- **Preconditions:** Task 3
- **Steps:**
  1. Create hook using `useQuery` with debounced search parameter
  2. Query key: `['users', 'search', { q, limit, offset }]`
- **Done when:** `npm test -- useSearchUsers` passes
- **Complexity:** small

### Task 5: Add search input to users page
- **Files:** `src/pages/UsersPage.tsx`, `src/components/SearchInput.tsx`
- **Preconditions:** Task 4
- **Steps:**
  1. Create `SearchInput` component with debounce (300ms)
  2. Integrate into `UsersPage` with `useSearchUsers` hook
- **Done when:** Search input renders, typing triggers debounced API call, results update
- **Complexity:** medium

## Edge Cases

- **Tasks with circular dependencies**: Restructure by extracting the shared dependency into its own task that both can depend on. If truly circular, combine into one task.
- **Tasks that are hard to verify in isolation**: Add a lightweight integration test as the verification command. If the only way to verify is manual testing, document the manual steps explicitly.
- **Context window running out**: Immediately save current state to progress.md and findings.md. The next context can resume by reading these files.
- **Scope explosion**: If decomposition produces >15 tasks, group related tasks into phases. Complete phase 1 before decomposing phase 2 in detail.
- **External dependency blocking**: Mark the task as "BLOCKED" in progress.md with the reason. Continue with non-blocked tasks.
