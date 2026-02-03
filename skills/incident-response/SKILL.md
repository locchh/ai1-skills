---
name: incident-response
description: >-
  Production incident response procedures for Python/React applications. Use when
  responding to production outages, investigating error spikes, diagnosing performance
  degradation, or conducting post-mortems. Covers severity classification (SEV1-SEV4),
  incident commander role, communication templates, diagnostic commands for FastAPI/
  PostgreSQL/Redis, rollback procedures, and blameless post-mortem process. Does NOT
  cover monitoring setup (use monitoring-setup) or deployment procedures (use
  deployment-pipeline).
license: MIT
compatibility: 'Python 3.12+, FastAPI, PostgreSQL, Redis, Docker'
metadata:
  author: platform-team
  version: '1.0.0'
  sdlc-phase: operations
allowed-tools: Read Grep Glob Bash(docker:*) Bash(curl:*) Bash(psql:*) Bash(redis-cli:*)
context: fork
---

# Incident Response

Production incident response procedures for Python/React applications running on FastAPI with PostgreSQL, Redis, and Docker.

## When to Use

Use this skill when:

- **Production outages occur** and services are returning 5xx errors or are unreachable
- **Error rate spikes** appear in monitoring dashboards or alerting systems
- **Performance degradation** is detected via elevated latency, slow queries, or resource saturation
- **User reports** indicate broken functionality, timeouts, or data inconsistencies
- **Post-mortem analysis** is needed after an incident has been resolved

Do **NOT** use this skill for:

- Setting up monitoring, metrics, or alerting -- use `monitoring-setup` instead
- Deploying code or managing CI/CD pipelines -- use `deployment-pipeline` instead
- Routine operational tasks or infrastructure provisioning

## Instructions

### Severity Classification

Classify every incident immediately. Severity drives response urgency, communication, and escalation.

| Level | Criteria | Response Time | Escalation | Target Resolution |
|-------|----------|---------------|------------|-------------------|
| **SEV1** | Complete outage, all users affected, data loss or breach | 5 min acknowledge | Page on-call, war room, notify leadership in 15 min | Under 1 hour |
| **SEV2** | Major feature degraded, significant user impact | 15 min respond | Notify eng/product leads, status page in 30 min | Under 4 hours |
| **SEV3** | Minor feature impacted, workaround available | 1 hour assess | Notify team via normal channels | Under 24 hours |
| **SEV4** | Cosmetic issue, negligible impact | Bug ticket | None -- prioritize in sprint backlog | Within sprint |

**SEV1 examples:** App completely down, database unreachable, auth broken, security breach.
**SEV2 examples:** Payment processing failing, 10x latency, search broken, job queue halted.
**SEV3 examples:** Export broken but data viewable, non-critical integration intermittent.
**SEV4 examples:** Typo in error message, minor alignment issue, harmless log noise.

### Incident Commander Checklist

The IC is the single point of authority. For SEV1/SEV2, designate an IC within 5 minutes.

#### First 5 Minutes

1. **Acknowledge the alert** and assume the IC role
2. **Open a dedicated incident channel** (`#incident-YYYY-MM-DD-brief-description`)
3. **Classify severity** using the table above
4. **Post the initial assessment:**
   ```
   INCIDENT DECLARED | Severity: SEV2
   Impact: API returning 503 for /orders endpoints
   IC: @your-name | Next update: 15 minutes
   ```
5. **Assign roles:** Communications lead and investigators

#### Communication and Delegation

- **SEV1:** Update every 15 min. **SEV2:** Every 30 min. **SEV3:** As findings occur.
- Communicate even with no new info -- silence creates anxiety.
- The IC coordinates, not debugs. Delegate specific tasks: "Alice, check FastAPI logs." "Bob, review the last deploy diff." "Carol, check PostgreSQL connection pool."

### Diagnostic Commands

Run `scripts/quick-diagnosis.sh` for an automated check of all common health indicators.

#### FastAPI Application

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
curl -s http://localhost:8000/ready | python3 -m json.tool
docker logs --tail 200 --timestamps backend-app 2>&1 | grep -i "error\|exception\|critical"
docker logs --since 30m backend-app 2>&1 | grep -c "500\|503\|timeout"
```

#### PostgreSQL

```bash
# Active connections by state
psql -h localhost -U app_user -d app_db -c \
  "SELECT state, count(*) FROM pg_stat_activity WHERE datname='app_db' GROUP BY state;"

# Slow queries (over 5 seconds)
psql -h localhost -U app_user -d app_db -c \
  "SELECT pid, now()-query_start AS duration, left(query,80) FROM pg_stat_activity
   WHERE (now()-query_start) > interval '5s' AND state != 'idle' ORDER BY duration DESC;"

# Connection pool utilization
psql -h localhost -U app_user -d app_db -c \
  "SELECT (SELECT count(*) FROM pg_stat_activity) AS active,
          (SELECT setting::int FROM pg_settings WHERE name='max_connections') AS max;"
```

#### Redis

```bash
redis-cli -h localhost ping
redis-cli -h localhost info memory | grep -E "used_memory_human|maxmemory_human|mem_fragmentation_ratio"
redis-cli -h localhost info clients | grep -E "connected_clients|blocked_clients"
redis-cli -h localhost slowlog get 10
```

#### Docker

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
docker ps -a --filter "status=exited" --format "table {{.Names}}\t{{.Status}}"
docker inspect --format='{{json .State.Health}}' backend-app | python3 -m json.tool
```

### Common Failure Modes

#### Database Connection Exhaustion

**Symptoms:** "Cannot acquire connection from pool" errors, requests timing out.
**Diagnosis:** Check `pg_stat_activity` for `idle in transaction` connections.
**Resolution:** Terminate leaked connections, restart app, increase pool size if needed, fix missing `async with` session blocks.

#### Memory Leaks

**Symptoms:** Steadily increasing memory, eventual OOM kills.
**Diagnosis:** `docker stats --no-stream backend-app` -- watch trend over multiple samples.
**Resolution:** Restart to restore service, then investigate with `tracemalloc`/`objgraph` in staging. Check for unbounded caches, growing module-level collections, unclosed sessions.
See `references/runbooks/memory-leak-runbook.md` for detailed steps.

#### Cascading Failures

**Symptoms:** Multiple services failing, retry storms, circuit breakers tripping.
**Resolution:** Check bottom-up (database -> backend -> frontend). Stabilize root service first. Enable rate limiting to stop retry storms. Recover layers sequentially.

#### Certificate Expiry

**Symptoms:** TLS handshake failures, "certificate has expired" in logs.
**Resolution:** Renew immediately, deploy to load balancer, verify with `curl -vI`. Set up automated renewal and 30-day expiry alerts.

### Rollback Decision Framework

#### When to Rollback

- Issue introduced by the most recent deployment
- Fix not obvious or will take over 30 minutes
- SEV1/SEV2 where every minute matters
- Deployment included many changes, hard to isolate
- Database migrations are backward-compatible

#### When to Hotfix

- Root cause identified, fix is small (<20 lines)
- Rollback would cause more disruption (e.g., irreversible migration)
- Issue is pre-existing, surfaced by new traffic patterns
- Fix deployable in under 30 minutes

#### Rollback Procedure

```bash
docker images --format "{{.Repository}}:{{.Tag}}\t{{.CreatedAt}}" | head -10
# gh workflow run rollback.yml -f version=<previous-good-tag>
docker compose up -d --no-deps backend-app
curl -s http://localhost:8000/health | python3 -m json.tool
curl -s http://localhost:8000/ready | python3 -m json.tool
```

Monitor for 15 minutes to confirm stability, then communicate the all-clear.

### Communication Templates

#### Status Page Updates

**Investigating:** "We are investigating [impact description]. Some users may experience [symptoms]. Next update: [time]."
**Identified:** "We have identified the cause: [brief description]. Our team is implementing a fix. Estimated resolution: [time]."
**Resolved:** "The issue has been resolved. [Brief summary]. Service normal since [time]. Duration: [total]. We apologize for the inconvenience."

#### Slack -- Initial Post

```
INCIDENT DECLARED -- [SEV level]
Service: [name] | Impact: [one-line description]
IC: @[name] | Channel: #incident-[date]-[slug]
Dashboard: [link] | Next update: [time]
```

#### Stakeholder Email (SEV1/SEV2)

Subject: `[SEV1] Production Incident - [Service] - [Description]`. Include: impact, start time, current status, IC name, key findings, next steps, update cadence, incident channel link.

### Post-Mortem Process

Every SEV1/SEV2 requires a blameless post-mortem. SEV3 if recurring within 30 days.

**Principles:** Blameless (systems, not people), thorough (full timeline), actionable (concrete items with owners and deadlines).

**Timeline:** Draft within 3 business days. Review meeting within 5 days. Action items tracked with owners and due dates.

**Structure:**
1. Incident metadata (date, severity, duration, services, IC, responders)
2. Executive summary (2-3 sentences)
3. Minute-by-minute timeline from detection to resolution
4. Root cause analysis using 5 Whys
5. Contributing factors (missing monitoring, outdated runbook, insufficient testing)
6. What went well / What could be improved
7. Action items (specific, measurable, assigned, time-bound)

See `references/post-mortem-template.md` for the complete format.

## Examples

### SEV2 Walkthrough: Database Connection Exhaustion

**14:00** -- PagerDuty fires: "5xx rate above 5% for 5 minutes."

**14:02** -- IC Alice opens `#incident-2025-03-15-api-errors`.

**14:03** -- Initial diagnosis: `/health` returns 200 but `/ready` shows database error "Cannot acquire connection from pool." Redis is fine.

**14:05** -- Alice delegates: Bob checks PostgreSQL, Carol checks recent deploys.

**14:07** -- Bob finds 48 of 50 connections stuck in `idle in transaction`.

**14:08** -- Carol finds a deployment at 13:45 with a new `/api/v1/reports/export` endpoint that leaks database sessions on the error path.

**14:10** -- IC decides: rollback (faster than hotfix while connections are draining).

```bash
# Terminate leaked connections
psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity
         WHERE state='idle in transaction' AND query_start < now()-interval '5 min';"
# Rollback to v2.4.0
```

**14:15** -- `/ready` returns healthy. Error rates back to baseline.

**14:20** -- All-clear posted. Post-mortem scheduled.

**Action items:** Fix leak with proper `async with`, add integration test for session cleanup, add alerting on idle-in-transaction count, add connection pool metrics to dashboard.

## Edge Cases

### Multi-Service Failures

Check shared infrastructure first (database, Redis, DNS, load balancer). Most multi-service failures have a single root cause. Assign separate investigators but keep them in the same channel. Look for common triggers: traffic spike, third-party outage, certificate expiry, DNS change.

### Data Corruption

Stop writes immediately. Assess scope (rows, time window). Check if recoverable from logs or event sourcing. For point-in-time recovery, restore backup to a secondary database and compare. Never fix corrupted data in production without a verified plan and fresh backup. Document every modification for audit.

### Third-Party Service Outages

Confirm via their status page and direct API calls. Classify severity based on YOUR user impact. Activate fallbacks (cached responses, queued processing, graceful degradation). Communicate upstream provider issue to your users. Monitor their status page for recovery. Verify your integration after they recover -- do not assume automatic recovery.

See `references/runbooks/` for service-specific runbooks covering API 503 errors, database slowness, high error rates, and memory leaks.
