---
name: deployment-pipeline
description: >-
  Deployment procedures and CI/CD pipeline configuration for Python/React projects. Use
  when deploying to staging or production, creating CI/CD pipelines with GitHub Actions,
  troubleshooting deployment failures, or planning rollbacks. Covers pipeline stages
  (build/test/staging/production), environment promotion, pre-deployment validation,
  health checks, canary deployment, rollback procedures, and GitHub Actions workflows.
  Does NOT cover Docker image building (use docker-best-practices) or incident response
  (use incident-response).
license: MIT
compatibility: 'GitHub Actions, Docker, Python 3.12+, React 18+'
metadata:
  author: platform-team
  version: '1.0.0'
  sdlc-phase: deployment
allowed-tools: Read Edit Write Bash(docker:*) Bash(gh:*) Bash(git:*)
context: fork
---

# Deployment Pipeline

## When to Use

Use this skill when you need to:

- **Deploy applications** to staging or production environments
- **Create CI/CD pipelines** using GitHub Actions for Python/React projects
- **Troubleshoot deployment failures** including failed builds, health check failures, or environment misconfigurations
- **Plan rollback strategies** for failed deployments or production regressions
- **Configure environment promotion** from staging to production with proper approvals
- **Set up canary deployments** with gradual traffic shifting

Do **NOT** use this skill for:

- Docker image building or Dockerfile optimization -- use `docker-best-practices` instead
- Production incident response or triage -- use `incident-response` instead
- Monitoring and alerting configuration -- use `monitoring-setup` instead

## Instructions

### Pipeline Stages

Every deployment follows four sequential stages. Each stage must pass before the next begins.

#### Stage 1: Build

The build stage compiles, bundles, and packages the application into deployable artifacts.

**Python Backend (FastAPI):**
- Install dependencies from `requirements.txt` or `pyproject.toml` using pip
- Run `python -m compileall` to verify no syntax errors
- Build the Docker image using the multi-stage Dockerfile
- Tag the image with the git SHA and semantic version: `app-backend:1.2.3-abc1234`
- Push the image to the container registry

**React Frontend:**
- Install dependencies with `npm ci` (never `npm install` in CI)
- Run `npm run build` to produce the production bundle
- Build the Docker image (nginx serving static assets)
- Tag the image with the git SHA and semantic version: `app-frontend:1.2.3-abc1234`
- Push the image to the container registry

**Build Validation:**
- Ensure the build completes without warnings treated as errors
- Verify the Docker image starts and responds to a basic health check
- Record build metadata: git SHA, branch, timestamp, builder version

#### Stage 2: Test

The test stage runs the full test suite in the CI environment against the built artifacts.

**Test Execution:**
- Run unit tests with `pytest --tb=short --junitxml=results.xml`
- Run integration tests against test database and Redis instances
- Run frontend tests with `npm test -- --ci --coverage`
- Run end-to-end tests with Playwright against the staged containers
- Run linting: `ruff check .` for Python, `eslint .` for JavaScript/TypeScript
- Run type checking: `mypy` for Python, `tsc --noEmit` for TypeScript

**Test Gates:**
- All tests must pass (zero failures)
- Code coverage must not drop below the configured threshold (default 80%)
- No critical or high security vulnerabilities from dependency scanning
- Linting and type checking produce zero errors

#### Stage 3: Staging

The staging stage deploys to a production-like environment for validation.

**Staging Deployment:**
- Deploy the tagged images to the staging environment
- Run database migrations with `alembic upgrade head`
- Wait for all services to report healthy via health check endpoints
- Run smoke tests against staging endpoints

**Staging Validation Checklist:**
- All health check endpoints return 200 OK
- Critical user flows work end-to-end (login, core features, checkout)
- No error spikes in staging logs for 5 minutes post-deploy
- API response times within acceptable thresholds (p99 < 500ms)
- Database migration completed without errors
- Frontend loads and renders without console errors

#### Stage 4: Production

The production stage uses canary deployment for safe rollout.

**Canary Rollout Strategy:**

Step 1 -- Canary at 10%:
- Route 10% of production traffic to the new version
- Monitor error rates, latency, and business metrics for 5 minutes
- Compare canary metrics against the baseline (current production)
- Automatic rollback if error rate exceeds 1% above baseline

Step 2 -- Canary at 50%:
- If 10% canary is healthy, increase to 50% traffic
- Monitor for an additional 5 minutes
- Validate that latency p99 remains within 20% of baseline
- Automatic rollback if any health check fails

Step 3 -- Full rollout at 100%:
- If 50% canary is healthy, promote to 100% traffic
- Monitor for 15 minutes post-rollout
- Keep the previous version available for instant rollback
- Mark deployment as successful after monitoring period

**Production Monitoring During Deploy:**
- Watch error rate dashboard in real-time
- Monitor application latency percentiles (p50, p95, p99)
- Check business metrics (transaction success rate, sign-up flow completion)
- Verify no memory leaks or CPU spikes in container metrics

### Pre-Deployment Validation

Before any deployment to staging or production, verify the following:

1. **CI Pipeline is Green**
   - All tests pass on the target branch
   - No pending or failed checks on the commit being deployed
   - Branch is up to date with main (no merge conflicts)

2. **Security Scan is Clean**
   - Run `trivy image <image>` against the Docker images
   - No critical or high CVEs in dependencies
   - `pip-audit` or `npm audit` shows no actionable vulnerabilities

3. **Database Migration Dry-Run**
   - Run `alembic upgrade head --sql` to generate migration SQL
   - Review the SQL for destructive operations (DROP TABLE, DROP COLUMN)
   - Verify migration is backward-compatible with the current running version
   - Test rollback: `alembic downgrade -1` works without data loss

4. **Staging Smoke Tests Pass**
   - Health endpoints respond correctly
   - Authentication flow works
   - Core API endpoints return expected responses
   - Frontend renders without errors

### Environment Promotion

**Promotion Flow: Staging to Production**

Promotion requires:
- All staging validation checks passing
- Manual approval from at least one team lead (configured in GitHub Actions)
- No active P1 or P2 incidents
- Deployment window compliance (avoid Fridays 4pm+, weekends, holidays)

**Environment Variables:**

Each environment has its own configuration. Never share secrets across environments.

```
# Staging
DATABASE_URL=postgresql://user:pass@staging-db:5432/app_staging
REDIS_URL=redis://staging-redis:6379/0
API_BASE_URL=https://staging-api.example.com
LOG_LEVEL=DEBUG
ENABLE_DEBUG_TOOLBAR=true

# Production
DATABASE_URL=postgresql://user:pass@prod-db:5432/app_prod
REDIS_URL=redis://prod-redis:6379/0
API_BASE_URL=https://api.example.com
LOG_LEVEL=INFO
ENABLE_DEBUG_TOOLBAR=false
```

**Secrets Management:**
- Store secrets in GitHub Actions secrets or a dedicated vault
- Never commit secrets to the repository
- Rotate secrets on a regular schedule (90 days minimum)
- Use separate secrets for each environment
- Audit secret access logs quarterly

### Health Checks

Every deployed service must expose health check endpoints.

**Liveness Endpoint: `/health`**

Returns 200 if the process is alive and can handle requests.

```json
{
  "status": "healthy",
  "version": "1.2.3",
  "git_sha": "abc1234",
  "uptime_seconds": 3600
}
```

The liveness check should be lightweight. It verifies:
- The application process is running
- The HTTP server is accepting connections
- The event loop is not blocked

**Readiness Endpoint: `/ready`**

Returns 200 only if all dependencies are reachable and the service can handle traffic.

```json
{
  "status": "ready",
  "checks": [
    {"name": "database", "status": "ok", "latency_ms": 2},
    {"name": "redis", "status": "ok", "latency_ms": 1},
    {"name": "auth-service", "status": "ok", "latency_ms": 15}
  ]
}
```

Returns 503 if any critical dependency is unreachable:

```json
{
  "status": "not_ready",
  "checks": [
    {"name": "database", "status": "ok", "latency_ms": 2},
    {"name": "redis", "status": "error", "error": "Connection refused"},
    {"name": "auth-service", "status": "ok", "latency_ms": 15}
  ]
}
```

**Dependency Checks:**
- **Database (PostgreSQL):** Execute `SELECT 1` with a 2-second timeout
- **Redis:** Execute `PING` with a 1-second timeout
- **External Services:** HTTP GET to their health endpoints with a 5-second timeout

**Health Check Configuration in Docker Compose / Orchestrator:**

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 10s
```

### Rollback Procedures

When a deployment causes issues, follow this rollback procedure:

**Step 1: Identify the Failure**
- Alert fires or manual detection of degraded service
- Confirm the issue correlates with the recent deployment
- Check error logs, metrics dashboards, and health check status

**Step 2: Trigger Rollback**
- Revert traffic to the previous known-good version
- For canary deployments: set canary weight to 0% and route all traffic to stable
- For full deployments: redeploy the previous image tag
- Command: `gh workflow run rollback.yml -f version=<previous-tag>`

**Step 3: Verify Health After Rollback**
- Confirm all health check endpoints return 200
- Verify error rates return to baseline within 5 minutes
- Check that the reverted version serves traffic correctly
- Run smoke tests against production

**Step 4: Notify the Team**
- Post in the deployment channel: rollback performed, reason, affected version
- Update the status page if users were impacted
- Tag the on-call engineer if the issue requires deeper investigation

**Step 5: Create Incident Ticket**
- Document the failed deployment: version, time, symptoms, rollback time
- Link to relevant logs, metrics, and error traces
- Assign to the team that authored the changes
- Schedule a review to understand the root cause before re-deploying

**Database Migration Rollback:**
- Run `alembic downgrade -1` to revert the last migration
- Verify data integrity after rollback
- If the migration was destructive (data deleted), restore from backup
- Always test migration rollback in staging before production

### GitHub Actions Workflows

**Workflow Structure:**

The CI/CD pipeline is defined in `.github/workflows/deploy.yml`.

```yaml
name: Deploy Pipeline

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        required: true
        default: 'staging'
        type: choice
        options:
          - staging
          - production

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
    steps:
      - uses: actions/checkout@v4
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  test:
    needs: build
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: test_db
          POSTGRES_PASSWORD: test_pass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      - run: pip install -r requirements.txt
      - run: pytest --tb=short --junitxml=results.xml
      - run: ruff check .

  deploy-staging:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - name: Deploy to staging
        run: |
          echo "Deploying ${{ needs.build.outputs.image-tag }} to staging"
          # Deploy commands here
      - name: Run smoke tests
        run: |
          curl -f https://staging-api.example.com/health
          pytest tests/smoke/ --base-url=https://staging-api.example.com

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://api.example.com
    steps:
      - name: Canary 10%
        run: echo "Setting canary weight to 10%"
      - name: Monitor canary
        run: sleep 300 && echo "Canary metrics OK"
      - name: Full rollout
        run: echo "Promoting to 100%"
```

**Job Dependencies:**
- `test` depends on `build` (needs the built image)
- `deploy-staging` depends on `test` (needs all tests passing)
- `deploy-production` depends on `deploy-staging` (needs staging validation)

**Caching Strategy:**
- Python pip packages: `actions/setup-python` with `cache: 'pip'`
- Node modules: `actions/setup-node` with `cache: 'npm'`
- Docker layers: GitHub Actions cache (`type=gha`)
- Playwright browsers: cache `~/.cache/ms-playwright`

**Secrets Configuration:**
- `DOCKER_REGISTRY_TOKEN` -- for pushing images to the container registry
- `DATABASE_URL` -- environment-specific database connection string
- `DEPLOY_KEY` -- SSH key or token for deployment
- Store all secrets in GitHub Actions settings, never in workflow files

## Examples

### Deploy FastAPI + React to Production with Canary Rollout

Scenario: You have a FastAPI backend and React frontend ready to deploy after merging to main.

**Step 1: Verify the build.**

Confirm the CI pipeline has completed successfully on the main branch:

```bash
gh run list --branch main --limit 5
```

Check the latest run status:

```bash
gh run view <run-id>
```

**Step 2: Confirm staging deployment.**

Verify staging health:

```bash
curl -s https://staging-api.example.com/health | jq .
curl -s https://staging-api.example.com/ready | jq .
```

Run smoke tests against staging:

```bash
pytest tests/smoke/ --base-url=https://staging-api.example.com -v
```

**Step 3: Trigger production deployment.**

If staging is healthy and smoke tests pass:

```bash
gh workflow run deploy.yml -f environment=production
```

**Step 4: Monitor the canary.**

Watch the canary deployment progress:

```bash
gh run watch <run-id>
```

Check production health at each canary stage:

```bash
curl -s https://api.example.com/health | jq .
```

**Step 5: Verify full rollout.**

After the deployment completes:

```bash
curl -s https://api.example.com/health | jq .
curl -s https://api.example.com/ready | jq .
```

Confirm the version matches the expected release:

```bash
curl -s https://api.example.com/health | jq '.version, .git_sha'
```

## Edge Cases

### Database Migration with Rollback

When a deployment includes database schema changes, extra caution is required.

**Problem:** A migration adds a NOT NULL column without a default value, breaking the running application before the new code is deployed.

**Solution: Expand-and-Contract Pattern**

1. **Expand (Migration 1):** Add the column as nullable with a default value
2. **Deploy new code** that writes to the new column
3. **Backfill** existing rows with the appropriate value
4. **Contract (Migration 2):** Add the NOT NULL constraint after all rows are populated

```python
# Migration 1: Expand
def upgrade():
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=True, server_default='false'))

def downgrade():
    op.drop_column('users', 'email_verified')

# Migration 2: Contract (deployed later)
def upgrade():
    op.alter_column('users', 'email_verified', nullable=False)

def downgrade():
    op.alter_column('users', 'email_verified', nullable=True)
```

### Zero-Downtime Deployment

**Problem:** During deployment, there is a brief period where old and new versions coexist. API contracts must remain compatible.

**Solution:**
- Ensure backward compatibility: new code handles old request formats
- Ensure forward compatibility: old code handles new response formats gracefully
- Use feature flags to toggle new functionality independently of deployment
- Database migrations must be compatible with both old and new code versions
- Run both versions simultaneously during the canary phase

### Secrets Rotation During Deployment

**Problem:** A secret (e.g., database password) needs to be rotated, but the application is mid-deployment.

**Solution:**
1. Add the new secret alongside the old one (dual-read support)
2. Deploy code that accepts both old and new secrets
3. Update the secret in the environment configuration
4. Deploy again to remove support for the old secret
5. Revoke the old secret

Never rotate secrets and deploy new code simultaneously. These should be separate operations to isolate failure causes.
