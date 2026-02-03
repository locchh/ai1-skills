# Pre-Merge Checklist Template

Copy this checklist into your PR review comment. Check off each item as you verify it.
Delete sections that do not apply (e.g., "Database Migration" if no migration is included).

---

## Code Quality

- [ ] Python: `ruff check` passes on changed files (zero errors)
- [ ] Python: `ruff format --check` passes (formatting correct)
- [ ] Python: `mypy src/ --strict` passes (zero type errors)
- [ ] TypeScript: `npx eslint src/` passes (zero errors, zero warnings)
- [ ] TypeScript: `npx prettier --check "src/**/*.{ts,tsx}"` passes
- [ ] TypeScript: `npx tsc --noEmit` passes (zero compiler errors)
- [ ] No new `# noqa`, `# type: ignore`, `@ts-ignore`, or `as any` without justification

## Test Coverage

- [ ] Overall Python coverage >= 80% (`pytest --cov-fail-under=80`)
- [ ] Overall JS/TS coverage >= 80%
- [ ] New files have >= 90% coverage
- [ ] New features: unit tests for happy path + edge cases
- [ ] Bug fixes: regression test included (fails without fix, passes with fix)
- [ ] Tests are isolated (no shared state, no execution order dependency)
- [ ] Assertions are meaningful (not just `is not None`)

## API Contract

- [ ] No breaking changes to existing endpoints (or changes are versioned)
- [ ] New endpoints documented with descriptions and examples
- [ ] Error responses documented (status codes, message format)
- [ ] Request/response models reviewed for correctness

## Database Migration

- [ ] Reversible: `downgrade()` function exists and is tested
- [ ] No data loss: columns not dropped without data migration
- [ ] No long-running locks: `CONCURRENTLY` used for index creation
- [ ] NOT NULL columns have defaults or use multi-step pattern
- [ ] Dry-run succeeds: `alembic upgrade head --sql` reviewed

## Frontend Quality

- [ ] Accessibility: labels, keyboard navigation, ARIA, contrast ratios
- [ ] Bundle size impact within threshold (< 250KB gzipped main bundle)
- [ ] Responsive: tested at 375px, 768px, 1280px breakpoints
- [ ] No horizontal scrollbar at any breakpoint

## Documentation

- [ ] API docs updated (OpenAPI descriptions, examples)
- [ ] New env vars documented (name, purpose, example)
- [ ] README updated if development workflow changes
- [ ] Changelog entry added (if user-facing change)

## Deployment Readiness

- [ ] New env vars added to staging and production (or have safe defaults)
- [ ] Feature flag in place for risky changes (defaults to off)
- [ ] Rollback plan documented (revert commit or forward-fix)
- [ ] All CI checks pass (no flaky failures)

## Security (quick check -- for full review use code-review-security)

- [ ] No hardcoded secrets (API keys, passwords, tokens)
- [ ] No `eval()`, `exec()`, or `dangerouslySetInnerHTML` without safeguard
- [ ] User input validated (Pydantic models, length limits)
- [ ] Auth required on new endpoints that serve user data

---

**Verdict:** APPROVED / APPROVED WITH COMMENTS / CHANGES REQUESTED

**Notes:**
<!-- Add any notes, follow-up items, or conditions for approval here -->
