---
name: monitoring-setup
description: >-
  Application monitoring and observability setup for Python/React projects. Use when
  configuring logging, metrics collection, health checks, alerting rules, or dashboard
  creation. Covers structured logging with structlog, Prometheus metrics for FastAPI,
  health check endpoints, alert threshold design, Grafana dashboard patterns, error
  tracking with Sentry, and uptime monitoring. Does NOT cover incident response
  procedures (use incident-response) or deployment (use deployment-pipeline).
license: MIT
compatibility: 'Python 3.12+, FastAPI, structlog, prometheus-client, Sentry SDK'
metadata:
  author: platform-team
  version: '1.0.0'
  sdlc-phase: operations
allowed-tools: Read Edit Write Bash(pip:*) Bash(npm:*)
context: fork
---

# Monitoring Setup

Application monitoring and observability for Python/React projects covering structured logging, metrics, health checks, alerting, error tracking, and dashboards.

## When to Use

Use this skill when:

- **Configuring structured logging** for a FastAPI application using structlog
- **Setting up Prometheus metrics** to track request rates, errors, and latency
- **Implementing health check endpoints** (liveness and readiness probes)
- **Designing alerting rules** based on golden signals and SLO targets
- **Integrating error tracking** with Sentry for Python and React applications
- **Creating Grafana dashboards** using RED and USE method patterns
- **Adding frontend monitoring** for Core Web Vitals and API latency

Do **NOT** use this skill for:

- Responding to active production incidents -- use `incident-response` instead
- Deploying code or configuring CI/CD pipelines -- use `deployment-pipeline` instead
- Docker container configuration -- use `docker-best-practices` instead

## Instructions

### Structured Logging

Use `structlog` for machine-parseable JSON log output with consistent fields. See `references/structlog-config.py` for the complete configuration.

#### structlog Configuration

**Key principles:**
- Always output JSON in production. Use console rendering only in development.
- Include a request ID (correlation ID) in every log entry for request tracing.
- Bind contextual fields (user ID, tenant ID) using `structlog.contextvars`.
- Reduce third-party library noise by setting their log level to WARNING.

```python
import structlog
logger = structlog.get_logger()

logger.info("order_created", order_id="ord-123", user_id="usr-456", amount=99.99)

# Bind context for all subsequent log calls in this request
structlog.contextvars.bind_contextvars(user_id="usr-456", tenant="acme")
logger.info("processing_payment")  # user_id and tenant included automatically
```

#### Log Levels

| Level | Usage | Examples |
|-------|-------|---------|
| **DEBUG** | Verbose diagnostics for development | Query params, cache hit/miss |
| **INFO** | Normal operations worth recording | Request completed, job processed |
| **WARNING** | Unexpected but handled gracefully | Retry attempt, deprecated API usage |
| **ERROR** | Operation failed, cannot be retried | Unhandled exception, external call failed |
| **CRITICAL** | System-level failure, immediate attention | Database unreachable, OOM |

**Rules:** Never log ERROR for expected business conditions. Never log sensitive data. Use ERROR only for unrecoverable operation failures.

#### Request ID Propagation

1. **Inbound:** Extract `X-Request-ID` header or generate a UUID.
2. **Logging:** Include the ID in every log entry via a structlog processor.
3. **Outbound:** Forward the ID to downstream service calls.
4. **Response:** Return the ID in the response header for client correlation.

The `LoggingMiddleware` in `references/structlog-config.py` implements this pattern.

### Health Check Endpoints

Every service must expose liveness and readiness endpoints.

#### Liveness vs Readiness

**Liveness (`/health`):** "Is the process alive?" Lightweight, fast (<10ms), no dependency checks.

```json
{"status": "healthy", "version": "1.2.3", "git_sha": "abc1234", "uptime_seconds": 3600}
```

**Readiness (`/ready`):** "Can the service handle traffic?" Checks all critical dependencies. Returns 503 if any are down.

```json
{
  "status": "ready",
  "checks": [
    {"name": "database", "status": "ok", "latency_ms": 3},
    {"name": "redis", "status": "ok", "latency_ms": 1},
    {"name": "auth-service", "status": "ok", "latency_ms": 12}
  ]
}
```

#### Dependency Checks

- **Database:** `SELECT 1` with 2-second timeout
- **Redis:** `PING` with 1-second timeout
- **External HTTP:** GET their health endpoint with 5-second timeout
- Non-critical dependencies should fail open (not make the app unready)

See `references/health-check-example.py` for a complete implementation with Pydantic response models.

### Prometheus Metrics

Use `prometheus-client` to expose application metrics. See `references/prometheus-metrics-example.py` for the complete middleware.

#### Request Duration Histogram

```python
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency.",
    ["method", "path"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)
```

Include buckets around your SLO threshold (e.g., if SLO is p99 < 500ms, include 0.25, 0.5, 1.0).

#### Active Connections Gauge

```python
REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress", "Requests currently being processed.", ["method"],
)
```

#### Error Counter

```python
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests.", ["method", "path", "status_code"],
)
```

#### Custom Business Metrics

```python
order_counter = Counter("business_orders_total", "Orders processed.", ["status", "region"])
order_counter.labels(status="completed", region="us-east-1").inc()
```

### Alerting Rules

Design alerts around the four golden signals. See `references/alerting-rules.yml` for complete examples.

#### Golden Signals

**Latency:** Alert on p95 > 1s for 5min (warning), p99 > 2s for 10min (critical). Track per endpoint.

**Traffic:** Alert on >50% drop in 5min (upstream failure?), >200% surge in 5min (DDoS?). Use hour-of-day baselines.

**Errors:** Alert on 5xx rate > 1% for 5min (warning), > 5% for 5min (critical). Track 4xx separately.

**Saturation:** CPU > 85% for 10min, memory > 85% for 10min (warning) / > 95% for 5min (critical), DB pool > 80%, disk > 85%.

#### Threshold Design

1. **Alert on symptoms, not causes.** "Error rate > 5%" not "CPU > 80%."
2. **Use `for` duration** to avoid flapping on transient spikes.
3. **Set thresholds based on SLOs.** Alert when error budget burn rate is dangerous.
4. **Two tiers:** Warnings notify in Slack. Critical pages the on-call engineer.
5. **Review quarterly.** Adjust as traffic and capacity change.

### Error Tracking

#### Sentry -- Python (FastAPI)

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn="https://key@o0.ingest.sentry.io/0",
    environment="production", release="myapp@1.2.3",
    traces_sample_rate=0.1,
    integrations=[FastApiIntegration()],
    send_default_pii=False,
)
```

**Breadcrumbs:** `sentry_sdk.add_breadcrumb(category="payment", message=f"Processing {order_id}", level="info")`
**User context:** `sentry_sdk.set_user({"id": user.id, "email": user.email})`
**Filtering:** Use `before_send` to drop expected errors (NotFoundError, KeyboardInterrupt).

#### Sentry -- React

```typescript
import * as Sentry from "@sentry/react";
Sentry.init({
  dsn: "https://key@o0.ingest.sentry.io/0",
  environment: import.meta.env.MODE,
  release: import.meta.env.VITE_APP_VERSION,
  tracesSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
  integrations: [Sentry.browserTracingIntegration(), Sentry.replayIntegration()],
});
```

Wrap your app with `<Sentry.ErrorBoundary fallback={<ErrorFallback />}>` for automatic crash reporting.

### Dashboard Patterns

#### RED Method Dashboard (Request-focused)

Track Rate, Errors, Duration for every service:

- **Rate:** `sum(rate(http_requests_total[5m]))`
- **Errors:** `sum(rate(http_requests_total{status_code=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))`
- **Duration:** `histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))`

Layout: Row 1 (Rate, Error %), Row 2 (Latency p50/p95/p99, In-progress), Row 3 (By endpoint).
See `references/dashboard-template.json` for a complete Grafana definition.

#### USE Method Dashboard (Resource-focused)

For CPU, memory, disk, network: track Utilization (% in use), Saturation (queue depth), Errors.
Layout: Row 1 (CPU util, CPU load), Row 2 (Memory util, Swap), Row 3 (Disk I/O, Network I/O).

#### SLI/SLO Tracking Dashboard

- **Availability SLI:** `1 - (error_rate_30d)`
- **Latency SLI:** `histogram_quantile(0.99, ...[30d])`
- **Error Budget:** Remaining budget for current month
- **Burn Rate:** Budget consumption across 1h, 6h, 24h windows

### Frontend Monitoring

#### Core Web Vitals

- **LCP** (Largest Contentful Paint): Target < 2.5s
- **INP** (Interaction to Next Paint): Target < 200ms
- **CLS** (Cumulative Layout Shift): Target < 0.1

```typescript
import { onCLS, onINP, onLCP } from "web-vitals";
function report(metric: { name: string; value: number; id: string }) {
  fetch("/api/v1/metrics/web-vitals", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: metric.name, value: metric.value, page: location.pathname }),
  });
}
onCLS(report); onINP(report); onLCP(report);
```

#### Error Boundary Reporting

Use Sentry's `ErrorBoundary` or a custom `componentDidCatch` that calls `Sentry.captureException` with the component stack.

#### API Latency Tracking

Wrap your fetch client to measure duration and report via `navigator.sendBeacon`. Normalize paths by replacing numeric IDs and UUIDs with `{id}` and `{uuid}` to avoid high cardinality.

## Examples

### Complete Monitoring Setup for a FastAPI Service

**Step 1:** Install dependencies: `pip install structlog prometheus-client sentry-sdk[fastapi]`

**Step 2:** Configure structured logging from `references/structlog-config.py`:
```python
from app.logging_config import setup_logging, LoggingMiddleware
setup_logging(log_level="INFO")
app = FastAPI(title="My Service", version="1.2.3")
app.add_middleware(LoggingMiddleware)
```

**Step 3:** Add Prometheus metrics from `references/prometheus-metrics-example.py`:
```python
from app.metrics import PrometheusMiddleware, metrics_endpoint
app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics", metrics_endpoint)
```

**Step 4:** Add health checks from `references/health-check-example.py`:
```python
from app.health import router as health_router
app.include_router(health_router)
```

**Step 5:** Configure Sentry:
```python
sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT,
                release=f"myapp@{settings.VERSION}", traces_sample_rate=0.1,
                integrations=[FastApiIntegration()])
```

**Step 6:** Deploy `references/alerting-rules.yml` to Prometheus, adjust thresholds.

**Step 7:** Import `references/dashboard-template.json` into Grafana.

**Verify:** `/health` returns 200, `/ready` checks dependencies, `/metrics` exposes Prometheus data, test error appears in Sentry, JSON logs include request IDs.

## Edge Cases

### High-Cardinality Labels

**Problem:** Labels with user IDs, request IDs, or raw paths create millions of time series, exhausting Prometheus memory.

**Prevention:** Never use unbounded values as labels. Normalize paths (`/users/{id}`). Limit to <100 unique values per label. Use `_normalize_path` from `references/prometheus-metrics-example.py`. Monitor `prometheus_tsdb_head_series` for early detection.

### Log Volume Management

**Problem:** Debug logging in production generates gigabytes per hour.

**Prevention:** INFO default in production, never DEBUG for extended periods. Sample high-frequency events (1-in-100). Set retention: 7d DEBUG, 30d INFO, 90d ERROR. Suppress noisy libraries.

```python
import random
def log_sampled(msg: str, rate: float = 0.01, **kw):
    if random.random() < rate:
        logger.info(msg, sampled=True, sample_rate=rate, **kw)
```

### Alert Fatigue

**Problem:** Too many non-actionable alerts cause engineers to ignore them.

**Prevention:** Every alert needs a documented remediation action. Require `runbook_url` on every rule. Alerts firing >5x/week without action should be tuned or removed. Use multi-burn-rate SLO alerts. Separate warnings (Slack) from critical (PagerDuty). Aggregate related alerts.
