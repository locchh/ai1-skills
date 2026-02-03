"""
FastAPI health check endpoints with dependency checks.

Implements liveness (/health) and readiness (/ready) probes following
Kubernetes conventions. Each dependency check has an independent timeout
so a single slow dependency does not block the entire readiness response.

Usage:
    from health_check_example import router as health_router

    app = FastAPI()
    app.include_router(health_router)
"""

import asyncio
import time
from typing import Any

import asyncpg
import redis.asyncio as aioredis
import httpx
from fastapi import APIRouter, Response
from pydantic import BaseModel

router = APIRouter()

# ---------------------------------------------------------------------------
# Configuration -- replace with your actual connection details or inject via
# dependency injection / settings.
# ---------------------------------------------------------------------------
DATABASE_URL = "postgresql://app_user:password@localhost:5432/app_db"
REDIS_URL = "redis://localhost:6379/0"
AUTH_SERVICE_URL = "http://auth-service:8001/health"

APP_VERSION = "1.0.0"
APP_GIT_SHA = "abc1234"
_start_time = time.monotonic()


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class DependencyCheck(BaseModel):
    name: str
    status: str  # "ok" or "error"
    latency_ms: float | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    git_sha: str
    uptime_seconds: float


class ReadinessResponse(BaseModel):
    status: str  # "ready" or "not_ready"
    checks: list[DependencyCheck]


# ---------------------------------------------------------------------------
# Dependency Check Helpers
# ---------------------------------------------------------------------------

async def _check_database(timeout: float = 2.0) -> DependencyCheck:
    """Execute SELECT 1 against PostgreSQL with a timeout."""
    start = time.perf_counter()
    try:
        conn = await asyncio.wait_for(
            asyncpg.connect(DATABASE_URL), timeout=timeout
        )
        try:
            await asyncio.wait_for(conn.fetchval("SELECT 1"), timeout=timeout)
        finally:
            await conn.close()
        latency = round((time.perf_counter() - start) * 1000, 2)
        return DependencyCheck(name="database", status="ok", latency_ms=latency)
    except Exception as exc:
        latency = round((time.perf_counter() - start) * 1000, 2)
        return DependencyCheck(
            name="database", status="error", latency_ms=latency, error=str(exc)[:200]
        )


async def _check_redis(timeout: float = 1.0) -> DependencyCheck:
    """Send PING to Redis with a timeout."""
    start = time.perf_counter()
    try:
        client = aioredis.from_url(REDIS_URL, socket_connect_timeout=timeout)
        try:
            await asyncio.wait_for(client.ping(), timeout=timeout)
        finally:
            await client.aclose()
        latency = round((time.perf_counter() - start) * 1000, 2)
        return DependencyCheck(name="redis", status="ok", latency_ms=latency)
    except Exception as exc:
        latency = round((time.perf_counter() - start) * 1000, 2)
        return DependencyCheck(
            name="redis", status="error", latency_ms=latency, error=str(exc)[:200]
        )


async def _check_external_service(
    name: str, url: str, timeout: float = 5.0
) -> DependencyCheck:
    """HTTP GET an external service health endpoint with a timeout."""
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        latency = round((time.perf_counter() - start) * 1000, 2)
        return DependencyCheck(name=name, status="ok", latency_ms=latency)
    except Exception as exc:
        latency = round((time.perf_counter() - start) * 1000, 2)
        return DependencyCheck(
            name=name, status="error", latency_ms=latency, error=str(exc)[:200]
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    """
    Liveness probe. Returns 200 if the process is alive.
    Does NOT check external dependencies -- keep this fast (<10ms).
    """
    return HealthResponse(
        status="healthy",
        version=APP_VERSION,
        git_sha=APP_GIT_SHA,
        uptime_seconds=round(time.monotonic() - _start_time, 1),
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness(response: Response) -> ReadinessResponse:
    """
    Readiness probe. Checks all critical dependencies in parallel.
    Returns 503 if any critical dependency is unhealthy.
    """
    checks = await asyncio.gather(
        _check_database(),
        _check_redis(),
        _check_external_service("auth-service", AUTH_SERVICE_URL),
    )

    all_ok = all(c.status == "ok" for c in checks)
    if not all_ok:
        response.status_code = 503

    return ReadinessResponse(
        status="ready" if all_ok else "not_ready",
        checks=list(checks),
    )
