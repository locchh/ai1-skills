# Rollback Procedure Runbook

## Decision Tree: Rollback vs. Hotfix

Before initiating a rollback, determine the correct response:

| Situation | Action | Rationale |
|-----------|--------|-----------|
| Service is completely down | **Rollback immediately** | Restore availability first |
| Data corruption in progress | **Rollback immediately** | Stop the bleeding |
| Performance degraded >50% | **Rollback immediately** | Users are actively affected |
| Minor bug, workaround exists | **Hotfix** | Rollback has its own risks |
| Feature behaves unexpectedly | **Feature flag off** | Least disruptive option |
| Intermittent errors <5% of requests | **Investigate first** | May resolve or may need hotfix |

**Rule of thumb:** If you are unsure, rollback. A rollback is always safer than
debugging under pressure. You can investigate after availability is restored.

---

## Step-by-Step Rollback Procedure

### 1. Announce the Incident

- Post in `#incidents` Slack channel: "Initiating rollback of [service] from [version] to [previous version]. Reason: [brief description]."
- Assign an Incident Commander (IC) if not already designated.

### 2. Identify the Previous Stable Version

```bash
# List recent deployments and their image tags
docker image ls --format "table {{.Repository}}\t{{.Tag}}\t{{.CreatedAt}}" | head -10

# Or check the deployment history in Kubernetes
kubectl rollout history deployment/app -n production
```

### 3. Execute the Rollback

**Option A: Docker Compose (single-host deployments)**

```bash
# Pull and restart with the previous known-good image tag
export IMAGE_TAG="<previous-stable-tag>"
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --no-build
```

**Option B: Kubernetes**

```bash
# Rollback to previous revision
kubectl rollout undo deployment/app -n production

# Or rollback to a specific revision
kubectl rollout undo deployment/app -n production --to-revision=<N>
```

### 4. Rollback Database Migrations (if applicable)

Only rollback migrations if the new migration is the cause of the issue.
Ensure the previous code version is compatible with the current schema first.

```bash
# Check current migration head
alembic current

# Downgrade one revision
alembic downgrade -1

# Verify the rollback
alembic current
```

**WARNING:** If the migration involved destructive operations (DROP COLUMN, DROP
TABLE), data may already be lost. In that case, you may need to restore from a
database backup instead. See the "DB Migration Failure" scenario below.

### 5. Disable Feature Flags (if applicable)

If the issue is isolated to a specific feature behind a flag:

```bash
# Disable the flag via your feature flag service CLI or admin UI
curl -X PATCH https://flags.internal/api/flags/new-checkout \
  -H "Authorization: Bearer ${FLAGS_API_TOKEN}" \
  -d '{"enabled": false}'
```

This is the least disruptive rollback path and should be preferred when possible.

### 6. Verify Health After Rollback

```bash
# Run the health check script
python scripts/health-check.py --url https://app.example.com

# Run smoke tests
./scripts/smoke-test.sh https://app.example.com

# Monitor error rates in your observability platform for 15 minutes
# Check: HTTP 5xx rate, p99 latency, database connection pool usage
```

### 7. Announce Resolution

- Post in `#incidents`: "Rollback complete. Service restored to [version]. Monitoring for stability."
- Update the status page if one was posted.

---

## Communication Protocol During Rollback

| Time | Action |
|------|--------|
| T+0 min | IC announces incident in `#incidents` |
| T+5 min | IC posts initial assessment and planned action |
| T+15 min | IC posts status update (rollback in progress / complete) |
| T+30 min | IC confirms stability or escalates |
| T+60 min | IC posts final status update |
| Next business day | Schedule post-mortem |

---

## Post-Rollback Investigation Checklist

After the service is stable, investigate the root cause:

- [ ] Capture logs from the failed deployment window
- [ ] Identify the exact commit(s) that caused the issue
- [ ] Check if the issue was caught by tests (if not, why not?)
- [ ] Determine if monitoring/alerting detected the issue promptly
- [ ] Write a post-mortem document with timeline, root cause, and action items
- [ ] Create tickets for preventive measures (new tests, better alerts, etc.)
- [ ] Share the post-mortem in the team meeting

---

## Common Rollback Scenarios

### Scenario 1: Bad Deploy (Application Error)

**Symptoms:** Spike in 5xx errors, health check failures immediately after deploy.
**Action:** Roll back the Docker image to the previous tag. No DB changes needed.
**Recovery time:** 2-5 minutes.

### Scenario 2: Database Migration Failure

**Symptoms:** Application errors referencing missing or changed columns/tables.
**Action:**
1. Roll back the application code first (it must work with the old schema).
2. Run `alembic downgrade -1` to revert the migration.
3. If the migration was destructive, restore from the last DB backup.

**Recovery time:** 5-30 minutes (longer if backup restoration is needed).

### Scenario 3: Configuration Error

**Symptoms:** Application starts but cannot connect to dependencies (DB, Redis,
external APIs). Logs show connection refused or authentication errors.
**Action:**
1. Check environment variables and secrets for the deployment.
2. Revert the configuration change (restore previous env vars / secrets).
3. Restart the service.

**Recovery time:** 2-10 minutes.

### Scenario 4: Resource Exhaustion

**Symptoms:** OOM kills, CPU throttling, disk full. Gradual degradation rather
than immediate failure.
**Action:**
1. Scale up or roll back if a code change caused the resource increase.
2. If caused by traffic spike, scale horizontally first, then investigate.

**Recovery time:** 5-15 minutes.
