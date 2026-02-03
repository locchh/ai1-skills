"""
Prometheus metrics setup for FastAPI.

Provides RED metrics (Rate, Errors, Duration) via middleware,
custom business metrics, and a /metrics endpoint for Prometheus scraping.

Usage:
    from prometheus_metrics_example import PrometheusMiddleware, metrics_endpoint

    app = FastAPI()
    app.add_middleware(PrometheusMiddleware)
    app.add_route("/metrics", metrics_endpoint)

    # Record custom business metrics:
    from prometheus_metrics_example import order_counter, payment_duration
    order_counter.labels(status="completed", region="us-east-1").inc()
    with payment_duration.labels(provider="stripe").time():
        process_payment(...)
"""

import time

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


# ---------------------------------------------------------------------------
# RED Metrics (Rate, Errors, Duration)
# ---------------------------------------------------------------------------

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total number of HTTP requests.",
    ["method", "path", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "path"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being processed.",
    ["method"],
)


# ---------------------------------------------------------------------------
# Custom Business Metrics
# ---------------------------------------------------------------------------

order_counter = Counter(
    "business_orders_total",
    "Total number of orders processed.",
    ["status", "region"],
)

payment_duration = Histogram(
    "business_payment_duration_seconds",
    "Duration of payment processing.",
    ["provider"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

active_websocket_connections = Gauge(
    "websocket_connections_active",
    "Number of active WebSocket connections.",
    ["channel"],
)

cache_operations = Counter(
    "cache_operations_total",
    "Total cache operations.",
    ["operation", "result"],  # operation: get/set/delete, result: hit/miss/error
)


# ---------------------------------------------------------------------------
# Path Normalization
# ---------------------------------------------------------------------------

def _normalize_path(path: str) -> str:
    """
    Normalize URL paths to prevent high-cardinality metric labels.

    Replaces dynamic segments (numeric IDs, UUIDs) with placeholders so that
    /users/123 and /users/456 map to the same label /users/{id}.
    """
    parts = path.strip("/").split("/")
    normalized: list[str] = []
    for part in parts:
        if part.isdigit():
            normalized.append("{id}")
        elif len(part) == 36 and part.count("-") == 4:
            # UUID pattern: 8-4-4-4-12
            normalized.append("{uuid}")
        else:
            normalized.append(part)
    return "/" + "/".join(normalized) if normalized else "/"


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware that records RED metrics for every HTTP request.

    - Increments request counter with method, normalized path, and status code.
    - Observes request duration in the latency histogram.
    - Tracks in-progress requests via a gauge.
    - Skips recording metrics for the /metrics endpoint itself to avoid feedback loops.
    """

    SKIP_PATHS = {"/metrics", "/health", "/ready"}

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = _normalize_path(request.url.path)

        # Skip instrumentation for internal endpoints
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        method = request.method
        REQUESTS_IN_PROGRESS.labels(method=method).inc()
        start_time = time.perf_counter()
        status_code = "500"

        try:
            response = await call_next(request)
            status_code = str(response.status_code)
            return response
        except Exception:
            status_code = "500"
            raise
        finally:
            duration = time.perf_counter() - start_time
            REQUEST_COUNT.labels(method=method, path=path, status_code=status_code).inc()
            REQUEST_LATENCY.labels(method=method, path=path).observe(duration)
            REQUESTS_IN_PROGRESS.labels(method=method).dec()


# ---------------------------------------------------------------------------
# Metrics Endpoint
# ---------------------------------------------------------------------------

async def metrics_endpoint(request: Request) -> Response:
    """Expose all registered Prometheus metrics in text exposition format."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
