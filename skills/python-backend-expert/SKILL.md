---
name: python-backend-expert
description: >-
  Python backend implementation patterns for FastAPI applications with SQLAlchemy 2.0,
  Pydantic v2, and async patterns. Use during the implementation phase when creating
  or modifying FastAPI endpoints, Pydantic models, SQLAlchemy models, service layers,
  or repository classes. Covers async session management, dependency injection via
  Depends(), layered error handling, and Alembic migrations. Does NOT cover testing
  (use pytest-patterns), deployment (use deployment-pipeline), or FastAPI framework
  mechanics like middleware and WebSockets (use fastapi-patterns).
license: MIT
compatibility: 'Python 3.12+, FastAPI 0.115+, SQLAlchemy 2.0+, Pydantic v2, Alembic 1.13+'
metadata:
  author: platform-team
  version: '1.0.0'
  sdlc-phase: implementation
allowed-tools: Read Edit Write Bash(python:*) Bash(pip:*) Bash(alembic:*)
context: fork
---

# Python Backend Expert

## When to Use

Use this skill when you are:

- Creating or modifying **FastAPI route handlers** (endpoints) that serve HTTP requests.
- Defining or updating **Pydantic v2 schemas** for request validation, response serialization, or internal data transfer objects.
- Writing or changing **SQLAlchemy 2.0 ORM models** with mapped columns, relationships, and constraints.
- Implementing **service layer classes** that contain business logic and orchestrate calls between repositories.
- Building **repository classes** that encapsulate database queries using async sessions.
- Running **Alembic migrations** to evolve the database schema.

Do **NOT** use this skill for:

- Writing tests for any of the above (use `pytest-patterns`).
- Deployment, CI/CD pipelines, or containerization (use `deployment-pipeline`).
- FastAPI framework-level concerns such as middleware stacks, WebSocket endpoints, CORS configuration, or authentication dependency chains (use `fastapi-patterns`).

---

## Instructions

### 1. FastAPI Endpoint Pattern

Every route handler must follow this structure. Endpoints are thin: they parse the request, call a service, and return a response. Business logic never lives in the route.

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.schemas.user import UserCreate, UserRead
from app.services.user_service import UserService
from app.services.exceptions import UserAlreadyExistsError, UserNotFoundError

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def create_user(
    payload: UserCreate,
    session: AsyncSession = Depends(get_async_session),
) -> UserRead:
    """Create a new user account.

    Raises:
        HTTPException 409: If the email is already registered.
    """
    service = UserService(session)
    try:
        user = await service.register(payload)
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return user


@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Retrieve a user by ID",
)
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> UserRead:
    """Fetch a single user by their primary key.

    Raises:
        HTTPException 404: If no user with the given ID exists.
    """
    service = UserService(session)
    try:
        user = await service.get_by_id(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return user
```

Key rules for endpoints:

- Always declare `response_model` so FastAPI generates accurate OpenAPI docs and filters output fields.
- Use `status_code` on the decorator for success codes other than 200.
- Catch **domain exceptions** from the service layer and translate them to `HTTPException` here and only here.
- Type the return annotation to match `response_model` for static analysis.
- Accept `AsyncSession` via `Depends(get_async_session)` -- never construct sessions manually.

---

### 2. Repository Pattern

Repositories are the only layer that touches the database. They accept an `AsyncSession`, execute queries, and return ORM model instances or `None`.

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User


class UserRepository:
    """Encapsulates all database operations for the User aggregate."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: int) -> User | None:
        stmt = select(User).where(User.id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self, *, offset: int = 0, limit: int = 100
    ) -> list[User]:
        stmt = select(User).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def update(self, user: User) -> User:
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        await self._session.delete(user)
        await self._session.flush()
```

Key rules for repositories:

- Use `flush()` instead of `commit()` -- the session middleware or service caller manages commit/rollback boundaries.
- Always call `refresh()` after `flush()` when you need server-generated defaults (auto-increment IDs, timestamps).
- Use `scalar_one_or_none()` for single-row lookups. Avoid `first()` because it silently ignores duplicate results.
- Never raise HTTP-layer exceptions. If a query fails, let the database exception propagate or raise a data-layer exception.
- Use `select()` statements (SQLAlchemy 2.0 style). Never use the legacy `session.query()` API.

---

### 3. Service Layer Pattern

Services contain business logic. They depend on one or more repositories and raise domain-specific exceptions. They never import anything from `fastapi`.

```python
from app.db.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate
from app.services.exceptions import UserAlreadyExistsError, UserNotFoundError
from app.core.security import hash_password

from sqlalchemy.ext.asyncio import AsyncSession


class UserService:
    """Business logic for user management."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = UserRepository(session)

    async def register(self, data: UserCreate) -> User:
        """Register a new user account.

        Raises:
            UserAlreadyExistsError: If the email is already taken.
        """
        existing = await self._repo.get_by_email(data.email)
        if existing is not None:
            raise UserAlreadyExistsError(
                f"A user with email {data.email!r} already exists."
            )

        user = User(
            email=data.email,
            display_name=data.display_name,
            hashed_password=hash_password(data.password),
        )
        return await self._repo.create(user)

    async def get_by_id(self, user_id: int) -> User:
        """Retrieve a user by primary key.

        Raises:
            UserNotFoundError: If no user with the ID exists.
        """
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(f"User {user_id} not found.")
        return user

    async def update_profile(self, user_id: int, data: UserUpdate) -> User:
        """Update mutable profile fields.

        Raises:
            UserNotFoundError: If no user with the ID exists.
        """
        user = await self.get_by_id(user_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        return await self._repo.update(user)
```

Domain exceptions are simple classes:

```python
# app/services/exceptions.py

class DomainError(Exception):
    """Base class for all domain/business rule errors."""


class UserAlreadyExistsError(DomainError):
    """Raised when attempting to create a user with a duplicate email."""


class UserNotFoundError(DomainError):
    """Raised when a requested user does not exist."""
```

Key rules for services:

- **NEVER** import or raise `HTTPException` from the service layer. Services know nothing about HTTP.
- Accept Pydantic schemas as input and return ORM models (or domain objects). The route converts to response schemas.
- Each public method should document which domain exceptions it may raise.
- Services may call other services or multiple repositories within the same session boundary.

---

### 4. Pydantic v2 Schema Conventions

All schemas must use Pydantic v2 APIs. Legacy Pydantic v1 patterns (`class Config`, `orm_mode`, `from_orm()`) are forbidden.

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Payload for creating a new user."""

    email: EmailStr
    display_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    """Payload for partial updates. All fields are optional."""

    display_name: str | None = Field(default=None, min_length=1, max_length=100)


class UserRead(BaseModel):
    """Response representation of a user."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    display_name: str
    created_at: datetime
    updated_at: datetime
```

Key conventions:

- Use `model_config = ConfigDict(from_attributes=True)` instead of the legacy `class Config: orm_mode = True`.
- Convert ORM models to schemas with `UserRead.model_validate(user_orm_instance)`.
- Serialize schemas with `schema.model_dump()` or `schema.model_dump(exclude_unset=True)` for partial updates.
- Always set field constraints via `Field()` for validation.
- Use `EmailStr` from `pydantic[email]` for email validation.
- Mark optional update fields with `| None` and `default=None` so clients can send partial payloads.

---

### 5. Async Session Management

A single async session should span the entire request lifecycle. Provide it through a FastAPI dependency.

```python
# app/db/session.py

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session that commits on success, rolls back on error."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

Key rules:

- Set `expire_on_commit=False` so that attributes remain accessible after the commit without triggering lazy loads.
- The `get_async_session` dependency manages the commit/rollback boundary. Repositories call `flush()`, not `commit()`.
- Use `pool_pre_ping=True` to detect stale connections before checkout.
- Never create ad-hoc engines or sessions outside this module.

---

### 6. Error Handling Rules

Errors are handled differently at each layer. Following these rules prevents leaking implementation details and keeps each layer testable in isolation.

| Layer       | Exception Type        | Example                       |
|-------------|-----------------------|-------------------------------|
| Route       | `HTTPException`       | 404, 409, 422                 |
| Service     | Domain exceptions     | `UserNotFoundError`           |
| Repository  | Data-layer exceptions | `IntegrityError` (propagated) |

Rules:

1. **Routes** catch domain exceptions and translate them to `HTTPException` with the appropriate status code and a user-safe message.
2. **Services** raise domain exceptions defined in `app/services/exceptions.py`. They never import `fastapi`.
3. **Repositories** let SQLAlchemy exceptions propagate naturally. If a constraint violation is expected (e.g., unique email), the service handles it.
4. **NEVER** raise `HTTPException` from a service or repository. This couples business logic to the transport layer and makes the service unusable from CLI tools, background workers, or other non-HTTP contexts.
5. Use `from exc` when re-raising to preserve the exception chain for debugging.

---

### 7. Alembic Migration Workflow

All schema changes must be tracked with Alembic migrations.

```bash
# Generate a migration after changing ORM models
alembic revision --autogenerate -m "add_users_table"

# Apply all pending migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1

# Roll back to a specific revision
alembic downgrade <revision_id>

# View current applied revision
alembic current

# View migration history
alembic history --verbose
```

Naming conventions:

- Use snake_case for migration messages: `add_users_table`, `add_email_index_to_users`, `drop_legacy_roles`.
- Start with a verb: `add_`, `drop_`, `alter_`, `create_`, `rename_`.
- Never modify a migration that has been applied in a shared environment. Create a new migration instead.
- Always review the auto-generated migration before applying. Autogenerate does not detect renamed columns, data migrations, or some index changes -- add those manually.
- Include both `upgrade()` and `downgrade()` functions. If a migration is not reversible, raise `NotImplementedError` in `downgrade()` with an explanation.

---

## Examples

### Complete User Registration Flow Across All Layers

Below is a full example showing how a user registration request flows through each layer.

**ORM Model:**

```python
# app/db/models/user.py

from datetime import datetime
from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100))
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
```

**Schemas** (see Section 4 above).

**Repository** (see Section 2 above).

**Service** (see Section 3 above).

**Route** (see Section 1 above).

**Request flow:**

1. Client sends `POST /users/` with `{"email": "a@b.com", "display_name": "Alice", "password": "secret123"}`.
2. FastAPI validates the body against `UserCreate`.
3. The route function receives the validated schema and an `AsyncSession` via `Depends`.
4. It instantiates `UserService(session)` and calls `service.register(payload)`.
5. The service checks for duplicate emails via the repository, hashes the password, and creates the ORM instance.
6. The repository calls `session.add()`, `flush()`, and `refresh()` to persist and hydrate the model.
7. On success, the route returns the ORM instance, which FastAPI serializes using `UserRead` (with `from_attributes=True`).
8. The `get_async_session` dependency commits the transaction after the route returns.
9. If any exception occurs, the session rolls back automatically.

---

## Edge Cases

### Detached Instance Errors

If you access a relationship or lazy-loaded attribute after the session is closed, SQLAlchemy raises `DetachedInstanceError`. Solutions:

- Use `expire_on_commit=False` on the session factory (already configured above).
- Eagerly load relationships in the query with `selectinload()` or `joinedload()`:

```python
from sqlalchemy.orm import selectinload

stmt = select(User).options(selectinload(User.posts)).where(User.id == user_id)
```

- Convert ORM models to Pydantic schemas within the session scope before returning them.

### Async Session in Background Tasks

FastAPI background tasks run after the response is sent. The request-scoped session is already closed by then. You must create a new session inside the background task:

```python
from fastapi import BackgroundTasks

async def send_welcome_email(user_id: int) -> None:
    async with async_session_factory() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(user_id)
        if user:
            # send email logic here
            pass
        await session.commit()

@router.post("/users/", response_model=UserRead, status_code=201)
async def create_user(
    payload: UserCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session),
) -> UserRead:
    service = UserService(session)
    user = await service.register(payload)
    background_tasks.add_task(send_welcome_email, user.id)
    return user
```

### N+1 Query Problem

When iterating over a collection of ORM objects and accessing a relationship on each one, SQLAlchemy fires a separate query per object. This is the N+1 problem. Prevent it by using eager loading:

```python
# BAD: triggers N+1
users = await repo.list_all()
for user in users:
    print(user.posts)  # separate query per user

# GOOD: single query with selectinload
stmt = select(User).options(selectinload(User.posts)).offset(0).limit(100)
result = await session.execute(stmt)
users = list(result.scalars().all())
for user in users:
    print(user.posts)  # already loaded, no extra query
```

Use `selectinload()` for one-to-many and many-to-many relationships. Use `joinedload()` for many-to-one or one-to-one relationships where you expect at most one related object.

### Circular Import Prevention

When models reference each other (e.g., `User` has `posts` relationship and `Post` has `author` relationship), use string-based `relationship()` declarations and ensure all models are imported in `app/db/base.py` before Alembic runs autogenerate:

```python
# app/db/models/user.py
class User(Base):
    __tablename__ = "users"
    posts: Mapped[list["Post"]] = relationship(back_populates="author")

# app/db/models/post.py
class Post(Base):
    __tablename__ = "posts"
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    author: Mapped["User"] = relationship(back_populates="posts")
```

### Unique Constraint Violations

Rather than catching `IntegrityError` at the repository level, prefer a check-then-act pattern in the service layer. This produces clearer error messages:

```python
async def register(self, data: UserCreate) -> User:
    existing = await self._repo.get_by_email(data.email)
    if existing:
        raise UserAlreadyExistsError(f"Email {data.email!r} is taken.")
    # proceed with creation
```

Be aware of race conditions in high-concurrency scenarios. For those, add a database-level unique constraint AND handle `IntegrityError` as a fallback in the service.
