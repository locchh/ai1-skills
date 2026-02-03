# FastAPI Middleware Examples

## Overview

Middleware in FastAPI wraps every request/response cycle. Each middleware can
inspect or modify the request before it reaches the route handler and the
response before it is sent to the client. Middleware is executed in the order it
is added (outermost first for requests, innermost first for responses).

---

## 1. Request Logging Middleware

Logs the HTTP method, path, status code, and duration of every request. This is
the single most useful middleware for production observability.

```python
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("api.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log method, path, status code, and wall-clock duration for every request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "%s %s -> %d (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 1),
                "client_ip": request.client.host if request.client else "unknown",
            },
        )
        return response
```

### Usage

```python
from fastapi import FastAPI

app = FastAPI()
app.add_middleware(RequestLoggingMiddleware)
```

### Notes
- Use `time.perf_counter()` instead of `time.time()` for monotonic precision.
- The `extra` dict makes structured logging possible with JSON formatters.
- Place this middleware outermost so it captures the full request lifecycle.

---

## 2. Request Timing Middleware

Adds an `X-Process-Time` header to every response so clients and load balancers
can observe backend latency.

```python
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class TimingMiddleware(BaseHTTPMiddleware):
    """Attach X-Process-Time header (seconds) to every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response: Response = await call_next(request)
        elapsed = time.perf_counter() - start
        response.headers["X-Process-Time"] = f"{elapsed:.4f}"
        return response
```

### Usage

```python
app.add_middleware(TimingMiddleware)
```

### Notes
- The value is in seconds with four decimal places (e.g., `0.0342`).
- Lightweight enough for every environment including production.
- If you already have the logging middleware above, you may combine them into
  one middleware to avoid double timing.

---

## 3. CORS Middleware (Proper Configuration)

The built-in `CORSMiddleware` from Starlette is the correct way to handle CORS.
Never use `allow_origins=["*"]` in production -- always enumerate trusted
origins.

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enumerate every allowed origin explicitly
ALLOWED_ORIGINS = [
    "https://app.example.com",
    "https://staging.example.com",
    "http://localhost:3000",  # Local frontend dev server
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Process-Time", "X-Request-ID"],
    max_age=600,  # Cache preflight response for 10 minutes
)
```

### Dynamic Origin Validation

If origins are loaded from a database or environment variable at runtime:

```python
import os

def get_allowed_origins() -> list[str]:
    """Read allowed origins from environment, comma-separated."""
    raw = os.environ.get("CORS_ORIGINS", "")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### Notes
- `allow_credentials=True` and `allow_origins=["*"]` are mutually exclusive
  per the CORS spec. Starlette will not send the correct headers.
- `max_age` controls how long the browser caches the preflight response.
  Higher values reduce OPTIONS requests but delay origin policy changes.
- `expose_headers` determines which response headers JavaScript can read.

---

## 4. Rate Limiting Middleware (Per-IP, Sliding Window)

A simple in-memory sliding-window rate limiter. For production, replace the
in-memory dict with Redis for multi-process/multi-node support.

```python
import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Per-IP sliding window rate limiter.

    Args:
        app: The ASGI application.
        max_requests: Maximum requests allowed within the window.
        window_seconds: Length of the sliding window in seconds.
    """

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # Map of IP -> list of request timestamps
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _clean_old_requests(self, ip: str, now: float) -> None:
        """Remove timestamps outside the current window."""
        cutoff = now - self.window_seconds
        self._requests[ip] = [
            ts for ts in self._requests[ip] if ts > cutoff
        ]

    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        self._clean_old_requests(client_ip, now)

        if len(self._requests[client_ip]) >= self.max_requests:
            retry_after = int(
                self.window_seconds
                - (now - self._requests[client_ip][0])
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Too many requests. Retry after {retry_after}s.",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(max(retry_after, 1))},
            )

        self._requests[client_ip].append(now)

        response = await call_next(request)
        remaining = self.max_requests - len(self._requests[client_ip])
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(self.window_seconds)
        return response
```

### Usage

```python
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)
```

### Notes
- This implementation is single-process only. For production with multiple
  workers or nodes, use Redis with a sorted set per IP.
- The `Retry-After` header tells well-behaved clients how long to wait.
- Consider exempting health-check endpoints from rate limiting.
- For per-user (authenticated) rate limiting, extract the user ID from the JWT
  instead of using the client IP.

---

## 5. Error Handling Middleware

Catches all unhandled exceptions and returns a consistent JSON error response
instead of leaking stack traces to clients.

```python
import logging
import traceback
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("api.errors")


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Catch unhandled exceptions, log them with a correlation ID,
    and return a safe JSON error response.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            error_id = str(uuid.uuid4())

            logger.exception(
                "Unhandled exception [error_id=%s] %s %s: %s",
                error_id,
                request.method,
                request.url.path,
                str(exc),
                extra={
                    "error_id": error_id,
                    "method": request.method,
                    "path": request.url.path,
                    "traceback": traceback.format_exc(),
                },
            )

            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_server_error",
                    "message": "An unexpected error occurred.",
                    "error_id": error_id,
                },
            )
```

### Usage

```python
app.add_middleware(ErrorHandlingMiddleware)
```

### Consistent Error Format

All error responses across the API should follow this shape:

```json
{
    "error": "error_code_snake_case",
    "message": "Human-readable description.",
    "error_id": "uuid-for-correlation",
    "details": {}
}
```

Register additional exception handlers for known error types:

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={
            "error": "validation_error",
            "message": str(exc),
        },
    )
```

### Notes
- The `error_id` is a UUID included in both the log and the response. Support
  teams can use it to correlate a user report with server logs.
- Never send stack traces or internal details in the response body.
- This middleware should be the outermost middleware (added last) so it wraps
  everything including other middleware failures.

---

## Middleware Registration Order

The order in which you add middleware matters. Middleware added first is
outermost (processes request first, response last). A recommended order:

```python
app = FastAPI()

# 1. Error handling (outermost -- catches everything)
app.add_middleware(ErrorHandlingMiddleware)

# 2. Request logging (captures full lifecycle including errors)
app.add_middleware(RequestLoggingMiddleware)

# 3. Timing (measures processing time)
app.add_middleware(TimingMiddleware)

# 4. CORS (must run before route handlers)
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, ...)

# 5. Rate limiting (innermost of the custom middleware)
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)
```

Note: Starlette processes middleware in reverse registration order for requests.
The last middleware added is the outermost. Adjust accordingly based on your
framework version and verify with integration tests.
