"""
Prometheus metrics configuration template for FastAPI.

Provides RED metrics (Rate, Errors, Duration) and custom business metrics.

Usage:
    from metrics_config import PrometheusMiddleware, metrics_endpoint, order_counter

    app = FastAPI()
    app.add_middleware(PrometheusMiddleware)
    app.add_route("/metrics", metrics_endpoint)

    # Custom business metric usage:
    order_counter.labels(status="completed", region="us-east-1").inc()
"""

import time
from typing import Any, Callable

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

# --- RED Metrics (Rate, Errors, Duration) ---

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

# --- Custom Business Metrics ---

order_counter = Counter(
    "business_orders_total",
    "Total number of orders processed.",
    ["status", "region"],
)

payment_amount_histogram = Histogram(
    "business_payment_amount_dollars",
    "Payment amounts in dollars.",
    ["currency"],
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000, 5000],
)

active_users_gauge = Gauge(
    "business_active_users",
    "Number of currently active users.",
    ["tier"],
)

external_call_duration = Histogram(
    "external_call_duration_seconds",
    "Duration of calls to external services.",
    ["service", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)


# --- Middleware ---

def _normalize_path(path: str) -> str:
    """
    Normalize URL paths to prevent high-cardinality labels.
    Replace dynamic segments (UUIDs, numeric IDs) with placeholders.
    """
    parts = path.strip("/").split("/")
    normalized = []
    for part in parts:
        if part.isdigit():
            normalized.append("{id}")
        elif len(part) == 36 and part.count("-") == 4:
            normalized.append("{uuid}")
        else:
            normalized.append(part)
    return "/" + "/".join(normalized) if normalized else "/"


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware that records RED metrics for every HTTP request."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        method = request.method
        path = _normalize_path(request.url.path)

        REQUESTS_IN_PROGRESS.labels(method=method).inc()
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            status_code = str(response.status_code)
        except Exception:
            status_code = "500"
            raise
        finally:
            duration = time.perf_counter() - start_time
            REQUEST_COUNT.labels(method=method, path=path, status_code=status_code).inc()
            REQUEST_LATENCY.labels(method=method, path=path).observe(duration)
            REQUESTS_IN_PROGRESS.labels(method=method).dec()

        return response


# --- Metrics Endpoint ---

async def metrics_endpoint(request: Request) -> Response:
    """Expose Prometheus metrics at /metrics."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
