# Implementation Plan Template

Use this template when producing an implementation plan for a feature, enhancement, or change.

---

## Objective

<!-- 1-2 sentence summary of what this delivers and why it matters -->

[Feature name]: [Clear description of the value delivered]

## Context

<!-- Background information that helps understand the change -->

- **Triggered by:** [User story / feature request / bug report / tech debt]
- **Related work:** [Links to related plans, ADRs, or PRs]
- **Open questions:** [List any ambiguities that need resolution before implementation]

## Affected Modules

<!-- Complete module map showing every area of the codebase impacted -->

| Layer | Module | Change Type | Impact | Notes |
|-------|--------|------------|--------|-------|
| Backend | models/ | | | |
| Backend | schemas/ | | | |
| Backend | services/ | | | |
| Backend | routes/ | | | |
| Backend | repositories/ | | | |
| Backend | migrations/ | | | |
| Frontend | pages/ | | | |
| Frontend | components/ | | | |
| Frontend | hooks/ | | | |
| Frontend | services/ | | | |
| Frontend | types/ | | | |
| Shared | config | | | |
| Tests | unit/ | | | |
| Tests | integration/ | | | |

**Change Types:** New file, Modify, Delete, Rename
**Impact:** Migration, API change, UI change, Config change, None

## Task List

<!-- Ordered implementation tasks with dependencies -->

### Task 1: [Title]
- **Files:** [files to create or modify]
- **Preconditions:** None
- **Steps:**
  1. [Specific action]
  2. [Specific action]
- **Done when:** [verification command + expected output]
- **Complexity:** [trivial / small / medium / large]

### Task 2: [Title]
- **Files:** [files to create or modify]
- **Preconditions:** Task 1
- **Steps:**
  1. [Specific action]
  2. [Specific action]
- **Done when:** [verification command + expected output]
- **Complexity:** [trivial / small / medium / large]

<!-- Add more tasks as needed -->

## Task Dependency Graph

<!-- Visual representation of task ordering -->

```
Task 1 (model) ──> Task 2 (schema) ──> Task 4 (route)
                                    ↗
Task 3 (service) ──────────────────
                                    ↘
                                     Task 5 (frontend) ──> Task 6 (integration)
```

## Verification

### Per-Task Verification

Each task includes its own `Done when` verification. Run these as you complete each task.

### Integration Verification

<!-- End-to-end test or manual smoke test for the complete feature -->

**Automated E2E:**
```
[E2E test command, e.g., npx playwright test tests/e2e/feature-name.spec.ts]
```

**Manual Smoke Test:**
1. [Step 1: Navigate to...]
2. [Step 2: Perform action...]
3. [Step 3: Verify result...]
4. [Expected outcome]

### Regression Check

- [ ] Existing tests still pass: `pytest -x && npm test`
- [ ] No type errors: `mypy src/ && npx tsc --noEmit`
- [ ] No lint issues: `ruff check src/ && npm run lint`

## Risks & Unknowns

<!-- Potential issues with likelihood and mitigation -->

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| [Description] | Low/Med/High | Low/Med/High | [How to reduce risk] |

## Acceptance Criteria

<!-- Observable outcomes that confirm the feature is complete -->

- [ ] [Criterion 1: User can...]
- [ ] [Criterion 2: System responds with...]
- [ ] [Criterion 3: Data persists in...]
- [ ] [Criterion 4: Error case handles...]
- [ ] All tests pass (unit + integration)
- [ ] No regressions in existing functionality
- [ ] Code reviewed and approved

## Estimation Summary

| Metric | Value |
|--------|-------|
| Total tasks | [N] |
| Estimated complexity | [trivial / small / medium / large] |
| Backend tasks | [N] |
| Frontend tasks | [N] |
| Test tasks | [N] |
| Migration required | [Yes / No] |
| API changes | [Yes / No] |

## Notes

<!-- Any additional context, decisions, or constraints -->

- [Note 1]
- [Note 2]
