# FastAPI Dependency Injection Patterns

## Basic Depends() Pattern

The simplest form: a callable (function or class) that FastAPI resolves and
injects into route handlers.

```python
from fastapi import Depends, FastAPI, Query

app = FastAPI()


def pagination_params(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> dict[str, int]:
    return {"skip": skip, "limit": limit}


@app.get("/items")
async def list_items(pagination: dict = Depends(pagination_params)):
    return {"skip": pagination["skip"], "limit": pagination["limit"]}
```

---

## Nested Dependencies

Dependencies can themselves declare dependencies. FastAPI resolves the entire
graph automatically.

```python
from fastapi import Depends

def get_settings() -> Settings:
    return Settings()

def get_db_url(settings: Settings = Depends(get_settings)) -> str:
    return settings.database_url

def get_db_session(db_url: str = Depends(get_db_url)) -> Session:
    engine = create_engine(db_url)
    return Session(engine)

@app.get("/users")
async def list_users(session: Session = Depends(get_db_session)):
    return session.query(User).all()
```

FastAPI resolves the chain: `get_settings` -> `get_db_url` -> `get_db_session`.

---

## Cached Dependencies (Per-Request)

By default, if the same dependency appears multiple times in one request's
dependency graph, FastAPI calls it only **once** and reuses the result. This is
called per-request caching.

```python
def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Called only once per request, even if multiple dependencies use it."""
    return decode_and_fetch_user(token)

def check_is_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(403, "Admin required")
    return user

@app.get("/admin/stats")
async def admin_stats(
    user: User = Depends(get_current_user),       # Same instance
    admin: User = Depends(check_is_admin),         # Reuses get_current_user
):
    # user and admin.user are the same object
    ...
```

To force a fresh call, use `Depends(get_current_user, use_cache=False)`.

---

## Parameterized Dependencies (Factory Functions)

When you need configurable dependencies, write a factory that returns a
dependency function.

```python
from fastapi import Depends, HTTPException

def require_role(role: str):
    """Factory: returns a dependency that enforces the given role."""
    def dependency(user: User = Depends(get_current_user)) -> User:
        if role not in user.roles:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{role}' is required",
            )
        return user
    return dependency

@app.get("/admin/dashboard")
async def admin_dashboard(user: User = Depends(require_role("admin"))):
    return {"message": f"Welcome, {user.name}"}

@app.get("/editor/articles")
async def editor_articles(user: User = Depends(require_role("editor"))):
    return {"message": f"Articles for {user.name}"}
```

---

## get_current_user Pattern (JWT + DB Lookup)

The canonical authentication dependency for FastAPI.

```python
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await session.get(User, int(user_id))
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user
```

### Usage

```python
@app.get("/me")
async def read_me(user: User = Depends(get_current_active_user)):
    return user
```

---

## require_role Factory Pattern

A more complete version with proper error messages and logging.

```python
import logging
from functools import wraps
from fastapi import Depends, HTTPException

logger = logging.getLogger(__name__)


def require_role(*roles: str):
    """
    Dependency factory that enforces one or more roles.

    Usage:
        @app.get("/admin", dependencies=[Depends(require_role("admin"))])
        @app.get("/staff", dependencies=[Depends(require_role("admin", "staff"))])
    """
    allowed = set(roles)

    async def dependency(user: User = Depends(get_current_active_user)) -> User:
        user_roles = set(user.roles)
        if not user_roles & allowed:
            logger.warning(
                "Access denied for user %s (roles=%s, required=%s)",
                user.id,
                user_roles,
                allowed,
            )
            raise HTTPException(
                status_code=403,
                detail=f"One of the following roles is required: {', '.join(sorted(allowed))}",
            )
        return user

    return dependency


# Apply to a single route
@app.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: User = Depends(require_role("admin")),
):
    ...

# Apply to an entire router
from fastapi import APIRouter

admin_router = APIRouter(
    prefix="/admin",
    dependencies=[Depends(require_role("admin"))],
)
```

---

## Yield Dependencies for Resource Cleanup

Use `yield` to run setup code before the route handler and teardown code after
the response is sent. This is the recommended pattern for database sessions,
file handles, and temporary resources.

```python
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@app.get("/users")
async def list_users(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(User))
    return result.scalars().all()
```

### File Handle Example

```python
import aiofiles
from typing import AsyncGenerator


async def get_temp_file() -> AsyncGenerator[aiofiles.threadpool.text.AsyncTextIOWrapper, None]:
    f = await aiofiles.open("/tmp/processing.log", mode="a")
    try:
        yield f
    finally:
        await f.close()
```

### Key Rules for Yield Dependencies

1. Only **one** `yield` is allowed per dependency function.
2. Code before `yield` runs before the route handler (setup).
3. Code after `yield` runs after the response is sent (teardown).
4. Exceptions in the route handler propagate into the dependency's `finally`
   block, so cleanup always runs.
5. Yield dependencies work with both `async def` and regular `def`.

---

## Overriding Dependencies in Tests

FastAPI's `app.dependency_overrides` dict lets you swap any dependency with a
test double.

```python
import pytest
from httpx import AsyncClient, ASGITransport
from main import app, get_async_session, get_current_user


# Fake user for tests
def fake_current_user() -> User:
    return User(id=1, name="Test User", roles=["admin"], is_active=True)


# In-memory SQLite session for tests
async def fake_session():
    async with test_session_factory() as session:
        yield session


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = fake_current_user
    app.dependency_overrides[get_async_session] = fake_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Clean up overrides after the test
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_list_users(client: AsyncClient):
    response = await client.get("/users")
    assert response.status_code == 200
```

### Override Patterns

```python
# Override with a lambda
app.dependency_overrides[get_settings] = lambda: Settings(debug=True)

# Override with a class
class FakeEmailService:
    async def send(self, to: str, body: str) -> None:
        pass  # No-op in tests

app.dependency_overrides[get_email_service] = FakeEmailService

# Override a parameterized dependency
# Note: you override the RESULT of the factory, not the factory itself
app.dependency_overrides[require_role("admin")] = lambda: fake_admin_user
```

### Important Notes on Overrides

1. Override the exact same callable object used in the route. If the dependency
   is `get_current_user`, override `get_current_user` -- not a copy.
2. Always call `app.dependency_overrides.clear()` after tests to prevent
   cross-test pollution.
3. Overrides apply globally to the app instance. Use fixtures to scope them.
4. You can override yield dependencies with regular functions (no yield needed
   in the override).

---

## Class-Based Dependencies

For complex dependencies with configuration, use a callable class.

```python
class Paginator:
    def __init__(self, max_limit: int = 100):
        self.max_limit = max_limit

    def __call__(
        self,
        skip: int = Query(0, ge=0),
        limit: int = Query(20, ge=1),
    ) -> dict[str, int]:
        return {"skip": skip, "limit": min(limit, self.max_limit)}


paginate = Paginator(max_limit=50)

@app.get("/items")
async def list_items(pagination: dict = Depends(paginate)):
    ...
```

This pattern is useful when you need to configure the dependency once and reuse
it across multiple routes with different settings.
