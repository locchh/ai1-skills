# Risk Assessment Checklist for Python/React Projects

Use this checklist during the planning phase (Step 5 of the Planning Workflow) to identify risks before implementation begins. Check each category and flag any that apply.

## Data & Database Risks

- [ ] **Schema migration required** — Adding/removing/renaming columns or tables
  - Mitigation: Write migration with `downgrade()`, test both directions, run dry-run on staging
- [ ] **Data transformation required** — Existing data must be migrated or converted
  - Mitigation: Separate data migration from schema migration, add rollback script, backup before run
- [ ] **Index changes** — Adding or removing indexes on large tables
  - Mitigation: Use `CREATE INDEX CONCURRENTLY` (PostgreSQL), schedule during low traffic
- [ ] **Foreign key changes** — Adding or modifying relationships
  - Mitigation: Verify referential integrity, plan cascade behavior, test with realistic data volume
- [ ] **Data loss potential** — Column removal, type narrowing, or constraint addition
  - Mitigation: Archive data first, add reversible soft-delete, never drop columns without data backup

## API & Contract Risks

- [ ] **Breaking API change** — Modifying existing endpoint request/response contract
  - Mitigation: Version the endpoint (/v2/), add deprecation headers, notify consumers
- [ ] **New required field** — Adding required fields to existing endpoints
  - Mitigation: Make field optional with default first, migrate consumers, then make required
- [ ] **Endpoint removal** — Removing or renaming an endpoint
  - Mitigation: Deprecate first (Sunset header), monitor usage for 2 sprints, then remove
- [ ] **Response format change** — Changing pagination, error format, or envelope structure
  - Mitigation: Version the API, update all frontend consumers simultaneously

## Authentication & Authorization Risks

- [ ] **Auth flow changes** — Modifying login, logout, token refresh, or session management
  - Mitigation: Extensive integration testing, test edge cases (expired tokens, concurrent sessions)
- [ ] **Permission model changes** — Adding roles, modifying access control
  - Mitigation: Default to deny, audit all endpoints for new permission checks
- [ ] **Token format changes** — Modifying JWT claims or token structure
  - Mitigation: Support both old and new format during transition, set expiry for old tokens
- [ ] **Third-party auth integration** — Adding OAuth provider or SSO
  - Mitigation: Test in sandbox first, handle provider downtime gracefully

## Performance Risks

- [ ] **N+1 query potential** — New relationships or list endpoints without eager loading
  - Mitigation: Use `selectinload()` / `joinedload()` in SQLAlchemy, add query count assertions in tests
- [ ] **Large payload risk** — Endpoints that could return unbounded data
  - Mitigation: Add pagination, enforce page size limits, implement cursor-based pagination
- [ ] **New external API call** — Adding calls to third-party services in request path
  - Mitigation: Add timeout, circuit breaker, cache results, move to background task if possible
- [ ] **File upload/download** — Handling binary data in endpoints
  - Mitigation: Set size limits, use streaming, offload to object storage (S3)
- [ ] **Frontend bundle size** — Adding large dependencies to the frontend
  - Mitigation: Check bundle impact with `npm run build --analyze`, use dynamic imports

## Third-Party Dependency Risks

- [ ] **New package addition** — Adding a dependency to requirements.txt or package.json
  - Mitigation: Check license compatibility (MIT/Apache OK, GPL check with legal), run `pip-audit` / `npm audit`
- [ ] **Version conflict** — New package conflicts with existing dependencies
  - Mitigation: Test in isolated environment first, pin exact versions
- [ ] **Unmaintained dependency** — Package with no recent releases or known vulnerabilities
  - Mitigation: Check last release date, GitHub stars, open issues; consider alternatives
- [ ] **Native extension** — Package requires compilation or system libraries
  - Mitigation: Update Dockerfile, test in CI environment, pin version tightly

## Cross-Cutting Risks

- [ ] **Middleware changes** — Modifying request/response middleware
  - Mitigation: Test all endpoints, check ordering effects, add middleware-specific tests
- [ ] **Shared utility changes** — Modifying functions used across multiple modules
  - Mitigation: Search all callers with `Grep`, update all usage sites, add regression tests
- [ ] **Configuration changes** — New environment variables or settings
  - Mitigation: Add to `.env.example`, document in README, add validation in config loading
- [ ] **Logging/monitoring changes** — Modifying log format or metrics
  - Mitigation: Verify dashboards and alerts still work, update log parsing rules

## Frontend-Specific Risks

- [ ] **Shared state changes** — Modifying React context, global store, or shared hooks
  - Mitigation: Map all consumers, test each consuming component
- [ ] **Route changes** — Adding, removing, or modifying URL paths
  - Mitigation: Update all internal links, add redirects for removed routes
- [ ] **Form validation changes** — Modifying validation rules
  - Mitigation: Test all input combinations, verify error messages, check accessibility
- [ ] **Component API changes** — Modifying props interface of shared components
  - Mitigation: Search all usage sites, update TypeScript types first (compiler catches misuse)

## Deployment Risks

- [ ] **Database migration in production** — Running schema changes on live database
  - Mitigation: Test on staging with production-like data, plan rollback, schedule maintenance window if needed
- [ ] **Environment variable additions** — New config needed in production
  - Mitigation: Add to deployment checklist, verify in staging, use sensible defaults
- [ ] **Infrastructure changes** — New services, containers, or scaling requirements
  - Mitigation: Test in staging, update deployment scripts, monitor resource usage

## Scoring

For each flagged risk, assess:

| Factor | Scale |
|--------|-------|
| **Likelihood** | Low (unlikely) / Medium (possible) / High (probable) |
| **Impact** | Low (cosmetic) / Medium (degraded feature) / High (data loss, outage, security breach) |

**Priority matrix:**
- High likelihood + High impact → **Must mitigate before implementation**
- High likelihood + Low impact → **Monitor during implementation**
- Low likelihood + High impact → **Have rollback plan ready**
- Low likelihood + Low impact → **Accept risk, document**
