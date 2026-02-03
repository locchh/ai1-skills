---
name: pre-merge-checklist
description: >-
  Comprehensive pre-merge validation checklist for Python/React pull requests. Use before
  approving or merging any PR. Covers code quality checks (linting, formatting, type
  checking), test coverage requirements, documentation updates, migration safety, API
  contract compatibility, accessibility compliance, bundle size impact, and deployment
  readiness. Provides a systematic checklist that ensures nothing is missed before merge.
  Does NOT cover security review depth (use code-review-security).
license: MIT
compatibility: 'Python 3.12+, React 18+, ruff, mypy, eslint, prettier'
metadata:
  author: platform-team
  version: '1.0.0'
  sdlc-phase: code-review
allowed-tools: Read Grep Glob Bash(ruff:*) Bash(mypy:*) Bash(npm:*) Bash(npx:*)
context: fork
---

# Pre-Merge Checklist

Systematic pre-merge validation skill for Python (FastAPI) and React pull requests.
Ensures that every PR meets code quality, test coverage, API compatibility, migration
safety, accessibility, and deployment readiness standards before it reaches the main
branch. See `references/checklist-template.md` for a copy-paste ready checklist.

See `scripts/run-all-checks.sh` for automated validation.

## When to Use

Use this skill when:

- **Approving or merging any pull request** to the main branch
- **Validating that CI-equivalent checks pass locally** before pushing
- **Reviewing a PR as a code reviewer** to ensure nothing is missed
- **Preparing a release candidate** and confirming all quality gates are met

Do **NOT** use this skill for:

- In-depth security vulnerability review -- use `code-review-security` instead
- Writing or debugging tests -- use `pytest-patterns`, `react-testing-patterns`, or `e2e-testing` instead
- Architecture or design decisions -- use `system-architecture` or `api-design-patterns` instead

## Instructions

### Code Quality Gate

All code must pass linting, formatting, and type checking before merge.

#### Python: Linting and Formatting (ruff)

```bash
ruff check src/ tests/
ruff format --check src/ tests/
```

**Standards:** Zero ruff errors on changed files. Import sorting follows the configured `isort` profile. No `# noqa` comments without an explanatory justification.

#### Python: Type Checking (mypy)

```bash
mypy src/ --strict
```

**Standards:** Zero mypy errors in changed files. New code must have complete type annotations. Avoid `Any` types. No `# type: ignore` without justification. See `scripts/type-check.sh` for the combined Python + TypeScript type checking script.

#### TypeScript: Linting, Formatting, and Types

```bash
npx eslint src/ --max-warnings 0
npx prettier --check "src/**/*.{ts,tsx,js,jsx,css,json}"
npx tsc --noEmit
```

**Standards:** Zero ESLint errors and warnings. All files Prettier-formatted. Zero TypeScript compiler errors. No `@ts-ignore` or `as any` without justification.

### Test Coverage Gate

Every PR must maintain or improve test coverage. New code must have tests.

| Metric | Threshold | Enforcement |
|--------|-----------|-------------|
| Overall line coverage (Python) | >= 80% | `pytest --cov-fail-under=80` |
| Overall line coverage (JS/TS) | >= 80% | Jest `coverageThreshold` |
| New file coverage | >= 90% | Manual review |
| Changed lines coverage | >= 85% | Manual review of coverage report |

```bash
pytest --cov=src --cov-report=term-missing --cov-fail-under=80
npm test -- --coverage --coverageReporters=text
```

**Requirements by PR type:**
- **New features**: Unit tests for happy path + at least two edge cases. Integration tests for API endpoints.
- **Bug fixes**: Regression test that fails without the fix and passes with it.
- **Refactors**: Existing tests still pass. Coverage must not decrease.
- **Dependency updates**: Existing tests still pass.

**Review questions:** Are tests testing actual behavior or just achieving coverage? Are assertions meaningful? Are edge cases covered? Are tests isolated? Are mocks used appropriately?

### API Contract Check

#### Backward-Compatible Changes (safe)

Adding new endpoints, optional request fields, response fields, query parameters with defaults, or HTTP methods.

#### Breaking Changes (require versioning)

Removing/renaming endpoints or fields, changing field types, making optional fields required, changing success status codes, or changing auth requirements.

**Verification:**

```bash
# Generate and diff OpenAPI schema
python -c "from src.main import app; import json; print(json.dumps(app.openapi(), indent=2))" > /tmp/openapi-new.json
```

Breaking changes must be versioned (`/api/v2/...`), documented in the changelog, and coordinated with client teams.

### Database Migration Check

- [ ] Migration is reversible: `downgrade()` function exists and has been tested
- [ ] No data loss: columns not dropped without data migration first
- [ ] No long-running locks: index creation uses `CONCURRENTLY` (PostgreSQL)
- [ ] NOT NULL columns have defaults or use the multi-step pattern (add nullable, backfill, add constraint)
- [ ] Migration tested on realistic dataset size

```bash
# Dry-run migration
alembic upgrade head --sql
```

**Multi-step pattern for safe column addition:**
1. PR 1: Add column as nullable
2. Deploy + backfill: Populate existing rows
3. PR 2: Add NOT NULL constraint after all rows are populated

### Frontend Quality Check

#### Accessibility (WCAG 2.2)

```bash
bash scripts/accessibility-check.sh http://localhost:3000
```

**Manual checks:** All images have meaningful `alt` text. Form inputs have associated labels. Interactive elements are keyboard accessible. Color contrast meets WCAG AA ratios. ARIA attributes used correctly. Focus management correct for modals.

#### Bundle Size Impact

```bash
npm run build
npx size-limit  # if configured
```

**Thresholds:** Main JS bundle: warn at 250KB gzipped, block at 500KB. Single chunk: warn at 100KB gzipped. If size increases significantly, evaluate whether the dependency is justified, code splitting is applied, and tree-shaking works correctly.

#### Responsive Design

Test at mobile (375px), tablet (768px), and desktop (1280px). No horizontal scrollbar. Touch targets >= 44x44px on mobile.

### Documentation Check

- [ ] New endpoints documented in OpenAPI schema with descriptions and examples
- [ ] Error responses documented (status codes, message format)
- [ ] New environment variables documented (name, purpose, example value)
- [ ] README updated if development workflow changes
- [ ] Changelog entry added for user-facing changes; breaking changes prominently marked

### Deployment Readiness

**Environment Variables:**
- [ ] New env vars documented and added to all deployment environments (or have safe defaults)
- [ ] No env var removed without confirming it is unused everywhere

**Feature Flags:**
- [ ] Large or risky features behind a feature flag (defaults to off in production)
- [ ] Flag has clear naming convention and documented purpose

**Rollback Plan:**
- [ ] Change can be rolled back by reverting merge commit
- [ ] Database migrations are reversible (if applicable)
- [ ] If not rollback-safe, PR documents the forward-fix strategy

**CI/CD:**
- [ ] All CI checks pass (no flaky test failures)
- [ ] Build artifacts produced successfully

## Examples

### Complete Checklist Walkthrough for a Sample PR

**PR #315: Add Password Reset Flow** -- 3 new API endpoints, 2 React pages, 1 migration, 1 email template.

```markdown
## Pre-Merge Checklist: PR #315

### Code Quality
- [x] `ruff check` and `ruff format --check` pass
- [x] `mypy src/ --strict` passes (new functions fully typed)
- [x] `npx eslint` and `npx prettier --check` pass
- [x] `npx tsc --noEmit` passes

### Test Coverage
- [x] Python coverage: 84% (above 80% threshold)
- [x] New endpoint tests: 94% coverage on new files
- [x] Regression test for expired token edge case

### API Contract
- [x] 3 new endpoints (no existing modified) -- backward compatible
- [x] OpenAPI schema updated with descriptions and examples

### Database Migration
- [x] Adds `password_reset_tokens` table (new table, no risk)
- [x] Downgrade drops table (reversible). Index on `token` column.

### Frontend Quality
- [x] Accessibility: labels, keyboard nav, error announcements
- [x] Bundle impact: +2.1KB gzipped. Responsive at all breakpoints.

### Documentation
- [x] New env vars `SMTP_HOST`, `SMTP_FROM` documented in README
- [x] Changelog entry under "Added"

### Deployment Readiness
- [x] Env vars added to staging/production
- [x] Feature flag `enable_password_reset` defaults to off
- [x] Rollback: revert merge commit (migration safe to leave)
- [x] All CI checks pass

### Verdict: APPROVED
```

### Running All Checks Locally

```bash
bash scripts/run-all-checks.sh

# Or run individually
bash scripts/type-check.sh
bash scripts/accessibility-check.sh http://localhost:3000
ruff check src/ tests/
pytest --cov=src --cov-fail-under=80
```

## Edge Cases

### Hotfix PRs

For urgent production fixes (P1/P2 incidents), a reduced checklist applies.

**Required (cannot skip):** Linting and type checks pass. Regression test included. CI passes. Rollback plan documented.

**Can defer to follow-up PR (within 48 hours):** Full test coverage improvements. Documentation updates. Accessibility checks (backend-only fixes). Bundle size analysis. Changelog entry.

**Process:** Create hotfix PR with reduced checklist. Merge after one reviewer approves. Immediately create a follow-up ticket for deferred items.

### Dependency-Only PRs

**Required:** All existing tests pass. No new security vulnerabilities (`safety check`, `npm audit`). Lock file updated. Major version bumps reviewed for breaking changes.

**Not required:** New tests (unless behavior changes). Documentation updates. API contract check.

### Migration-Only PRs

**Required:** Migration reversible and tested. No data loss risk. No long-running locks. Dry-run succeeds. If dropping a column, verify no code references it.

**Not required:** Test coverage (no application code changed). Frontend quality checks.

### Large PRs (20+ Changed Files)

1. Ask if the PR can be split into independent changes.
2. Prioritize review of high-risk files (auth, database, API, payment logic).
3. Run the full automated suite (`scripts/run-all-checks.sh`).
4. Verify test suite is proportionally comprehensive.
5. Check for accidental inclusions: debug code, TODO comments, unrelated changes.

See `references/checklist-template.md` for a copy-paste ready checklist.
