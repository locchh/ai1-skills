---
name: fastapi-patterns
description: >-
  FastAPI framework mechanics and advanced patterns. Use when configuring middleware,
  creating dependency injection chains, implementing WebSocket endpoints, customizing
  OpenAPI documentation, setting up CORS, building authentication dependencies (JWT
  validation, role-based access), implementing background tasks, or managing application
  lifespan (startup/shutdown). Does NOT cover basic endpoint CRUD or repository/service
  patterns (use python-backend-expert) or testing (use pytest-patterns).
license: MIT
compatibility: 'Python 3.12+, FastAPI 0.115+, Starlette'
metadata:
  author: platform-team
  version: '1.0.0'
  sdlc-phase: implementation
allowed-tools: Read Edit Write Bash(python:*) Bash(uvicorn:*)
context: fork
---

# FastAPI Patterns

## When to Use

Use this skill when you are:

- Configuring or ordering **middleware** (CORS, logging, timing, custom request/response processing).
- Building **dependency injection chains** with nested `Depends()`, cached dependencies, or `yield`-based teardown dependencies.
- Implementing **WebSocket endpoints** including connection lifecycle, room-based broadcast, and WebSocket authentication.
- Customizing **OpenAPI documentation** (tags, descriptions, security schemes, response examples).
- Setting up **CORS** policies for cross-origin frontend clients.
- Creating **authentication/authorization dependencies** (JWT token validation, role-based access control, API key verification).
- Scheduling **background tasks** after a response is returned.
- Managing **application lifespan** events (database pool initialization, Redis connections, HTTP client setup/teardown).

Do **NOT** use this skill for:

- Basic CRUD endpoints, Pydantic model design, SQLAlchemy ORM models, or repository/service layer patterns (use `python-backend-expert`).
- Writing tests for FastAPI applications (use `pytest-patterns`).

---

## Instructions

### 1. Middleware Stack

Middleware in FastAPI (Starlette) is applied in **LIFO order**: the last middleware added wraps the outermost layer, so it runs first on the request and last on the response. Plan your stack accordingly.

**Recommended ordering (top = outermost = first to execute on request):**

1. CORS middleware (must be outermost to handle preflight before anything else)
2. Request ID / logging middleware
3. Timing middleware
4. Custom exception-catching middleware

**Custom Middleware Pattern:**

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import time
import uuid


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request for tracing."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """Log request duration in milliseconds."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.1f}"
        return response
```

**CORS Configuration:**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,  # Cache preflight for 10 minutes
)
```

Key rules:

- Never use `allow_origins=["*"]` with `allow_credentials=True`. Browsers reject this combination.
- Be explicit about allowed methods and headers. Wildcards reduce security.
- Add CORS middleware **last** (so it wraps outermost due to LIFO) to ensure preflight requests are handled before other middleware.

**Custom Exception Handler:**

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.services.exceptions import DomainError

app = FastAPI()


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"error": exc.__class__.__name__, "detail": str(exc)},
    )
```

---

### 2. Authentication Dependencies

Authentication is implemented as a dependency chain. Each step in the chain can be tested and overridden independently.

**JWT Token Validation:**

```python
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import settings
from app.schemas.auth import TokenPayload

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


async def get_token_payload(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> TokenPayload:
    """Decode and validate a JWT token. Raises 401 if invalid or expired."""
    try:
        raw = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        payload = TokenPayload.model_validate(raw)
    except (JWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if payload.exp < datetime.now(tz=timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload
```

**Get Current User from Token:**

```python
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.db.models.user import User
from app.repositories.user_repository import UserRepository


async def get_current_user(
    payload: Annotated[TokenPayload, Depends(get_token_payload)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> User:
    """Resolve the authenticated user from the token payload."""
    repo = UserRepository(session)
    user = await repo.get_by_id(payload.sub)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive.",
        )
    return user
```

**Role-Based Access Factory:**

```python
def require_role(*roles: str):
    """Factory that returns a dependency enforcing one or more roles."""

    async def _check_role(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {current_user.role!r} is not authorized. Required: {roles}.",
            )
        return current_user

    return _check_role


# Usage in a route:
@router.delete("/users/{user_id}", dependencies=[Depends(require_role("admin"))])
async def delete_user(user_id: int, session: AsyncSession = Depends(get_async_session)):
    ...
```

**API Key Dependency:**

```python
from fastapi import Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")


async def verify_api_key(
    api_key: Annotated[str, Security(api_key_header)],
) -> str:
    if api_key not in settings.valid_api_keys:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key.",
        )
    return api_key
```

---

### 3. Dependency Injection Chains

FastAPI's `Depends()` system supports nesting, caching, yield-based teardown, and test overrides.

**Nested Dependencies:**

Dependencies can depend on other dependencies. FastAPI resolves the entire graph automatically.

```python
async def get_user_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> UserService:
    return UserService(session)


@router.get("/users/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserRead:
    return await service.get_by_id(user_id)
```

**Dependency Caching:**

By default, FastAPI caches dependencies within a single request. If `get_async_session` is used in two different dependency branches, the same session instance is reused. To disable caching:

```python
session: AsyncSession = Depends(get_async_session, use_cache=False)
```

**Yield Dependencies (Teardown):**

Use `yield` for dependencies that need cleanup logic:

```python
from collections.abc import AsyncGenerator
import httpx


async def get_http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(timeout=30) as client:
        yield client
    # client is closed here automatically
```

**Overriding in Tests:**

```python
from fastapi.testclient import TestClient

app.dependency_overrides[get_current_user] = lambda: fake_user
client = TestClient(app)
response = client.get("/users/me")
app.dependency_overrides.clear()
```

---

### 4. Background Tasks

Use `BackgroundTasks` for lightweight work that should run after the response is sent.

```python
from fastapi import BackgroundTasks


async def log_user_activity(user_id: int, action: str) -> None:
    """Log to an external analytics service."""
    # This runs after the response is sent to the client.
    async with httpx.AsyncClient() as client:
        await client.post(
            "https://analytics.internal/events",
            json={"user_id": user_id, "action": action},
        )


@router.post("/orders/", response_model=OrderRead, status_code=201)
async def create_order(
    payload: OrderCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session),
) -> OrderRead:
    service = OrderService(session)
    order = await service.create(payload)
    background_tasks.add_task(log_user_activity, payload.user_id, "order_created")
    return order
```

When to use **BackgroundTasks** vs **Celery/Dramatiq**:

| Criteria               | BackgroundTasks         | Celery / Task Queue       |
|------------------------|-------------------------|---------------------------|
| Duration               | Seconds                 | Minutes to hours          |
| Retries needed         | No                      | Yes                       |
| Survives server crash  | No                      | Yes (persisted in broker) |
| Scalable independently | No (runs in web worker) | Yes (dedicated workers)   |

---

### 5. WebSocket Endpoints

WebSocket connections follow a lifecycle: connect, exchange messages, disconnect.

```python
from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    """Manage active WebSocket connections for broadcasting."""

    def __init__(self) -> None:
        self._active: dict[str, list[WebSocket]] = {}

    async def connect(self, room: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._active.setdefault(room, []).append(websocket)

    def disconnect(self, room: str, websocket: WebSocket) -> None:
        self._active.get(room, []).remove(websocket) if websocket in self._active.get(room, []) else None

    async def broadcast(self, room: str, message: dict) -> None:
        for ws in self._active.get(room, []):
            await ws.send_json(message)


manager = ConnectionManager()


@router.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str) -> None:
    # Authenticate before accepting (use query param or first message)
    token = websocket.query_params.get("token")
    if not token or not validate_token(token):
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await manager.connect(room, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(room, data)
    except WebSocketDisconnect:
        manager.disconnect(room, websocket)
```

Key rules for WebSocket:

- Authenticate **before** calling `accept()` or in the first message exchange. There is no middleware support for WebSocket auth.
- Always wrap the message loop in `try/except WebSocketDisconnect`.
- Use close codes in the 4000-4999 range for application-level errors.

---

### 6. Application Lifespan

Use the lifespan context manager (introduced in FastAPI 0.93+) instead of the deprecated `on_event("startup")` / `on_event("shutdown")`.

```python
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize and teardown shared resources."""
    # Startup: create database engine, Redis pool, HTTP client
    app.state.db_engine = create_async_engine(settings.database_url)
    app.state.http_client = httpx.AsyncClient(timeout=30)

    yield  # Application runs here

    # Shutdown: close connections gracefully
    await app.state.http_client.aclose()
    await app.state.db_engine.dispose()


app = FastAPI(lifespan=lifespan)
```

Key rules:

- Everything before `yield` runs on startup; everything after runs on shutdown.
- Store shared resources on `app.state` so dependencies can access them.
- Never use `@app.on_event("startup")` or `@app.on_event("shutdown")` -- they are deprecated.
- If startup fails, the application will not start. Let exceptions propagate to surface configuration errors early.

---

## Examples

### JWT Auth Dependency Chain with Role-Based Access

This example shows a protected admin endpoint that deletes a user. The dependency chain resolves as follows:

1. `oauth2_scheme` extracts the Bearer token from the `Authorization` header.
2. `get_token_payload` decodes and validates the JWT.
3. `get_current_user` loads the user from the database.
4. `require_role("admin")` checks the user's role.

```python
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.db.models.user import User
from app.dependencies.auth import get_current_user, require_role
from app.services.user_service import UserService
from app.services.exceptions import UserNotFoundError

router = APIRouter(prefix="/admin", tags=["admin"])


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user (admin only)",
)
async def admin_delete_user(
    user_id: int,
    admin: Annotated[User, Depends(require_role("admin"))],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> None:
    service = UserService(session)
    try:
        await service.delete(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
```

In tests, override the auth dependency to bypass JWT validation:

```python
from app.dependencies.auth import get_current_user

fake_admin = User(id=1, email="admin@test.com", role="admin", is_active=True)
app.dependency_overrides[get_current_user] = lambda: fake_admin
```

---

## Edge Cases

### Middleware vs Dependency

Use **middleware** when you need to intercept every request/response regardless of route (logging, timing, CORS). Use **dependencies** when behavior is route-specific (authentication, authorization, input transformation).

Middleware cannot access route-specific information like path parameters or the resolved `response_model`. Dependencies can.

### BaseHTTPMiddleware vs Pure ASGI Middleware

`BaseHTTPMiddleware` is convenient but has limitations:

- It reads the entire request body into memory, which breaks streaming.
- It wraps the response in `StreamingResponse`, which can interfere with certain response types.

For production-grade middleware that needs to handle streaming or large payloads, write pure ASGI middleware:

```python
from starlette.types import ASGIApp, Receive, Scope, Send


class PureTimingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        start = time.perf_counter()
        await self.app(scope, receive, send)
        duration = time.perf_counter() - start
        # Log duration (cannot modify response headers here without wrapping send)
```

### Lifespan vs on_event

`on_event("startup")` and `on_event("shutdown")` are deprecated since FastAPI 0.93. They do not support sharing state between startup and shutdown. The `lifespan` context manager naturally shares state through local variables or `app.state`.

If you need to support both old and new FastAPI versions, check `FastAPI.__version__` at import time, but prefer requiring 0.93+ and using `lifespan` exclusively.

### Dependency Caching Pitfalls

If two routes share a dependency that yields a database session, caching ensures they get the same session within one request. However, if a dependency is used across different `Depends()` branches with `use_cache=False`, you may accidentally create multiple sessions for the same request, leading to inconsistent reads. Always use the default caching behavior unless you have a specific reason to disable it.
