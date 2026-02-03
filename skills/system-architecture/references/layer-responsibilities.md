# Layer Responsibilities Guide

Detailed guide on what belongs in each layer of the Python (FastAPI) + React/TypeScript architecture. When in doubt, check this reference.

## Backend Layers

### Router Layer (`app/routers/`)

**Purpose:** HTTP interface — translates HTTP requests into service calls and service responses into HTTP responses.

**Allowed:**
- Define route paths, HTTP methods, status codes
- Parse request parameters (path, query, body, headers)
- Validate request data using Pydantic schemas
- Call service methods
- Map service exceptions to HTTP status codes
- Set response headers (caching, pagination links)
- Enforce authentication via `Depends(get_current_user)`
- Enforce authorization via `Depends(require_role('admin'))`

**Forbidden:**
- Business logic (calculations, decisions, workflows)
- Direct database access (no session, no queries)
- Importing models or repository classes
- Constructing SQL queries
- Calling external APIs directly

**Example — correct:**
```python
@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    try:
        user = await service.create(data)
        return UserResponse.model_validate(user)
    except DuplicateEmailError:
        raise HTTPException(409, "Email already registered")
```

**Example — wrong:**
```python
# BAD: Business logic in router
@router.post("/users")
async def create_user(data: UserCreate, session: AsyncSession = Depends(get_session)):
    if await session.execute(select(User).where(User.email == data.email)):
        raise HTTPException(409, "duplicate")  # BAD: direct DB access
    user = User(**data.model_dump())
    user.password = hash_password(data.password)  # BAD: business logic here
    session.add(user)
    await session.commit()
```

### Service Layer (`app/services/`)

**Purpose:** Business logic — orchestrates operations, enforces business rules, coordinates between repositories.

**Allowed:**
- Business rule enforcement (validation, authorization checks)
- Orchestrating multiple repository calls
- Calling external services (through injected clients)
- Raising domain exceptions (ValueError, PermissionError, custom exceptions)
- Data transformation between layers
- Transaction coordination (using the session from repository)

**Forbidden:**
- HTTP concepts (status codes, HTTPException, request/response objects)
- Direct SQLAlchemy queries (use repository methods)
- Importing FastAPI-specific modules
- Knowledge of how data is stored (SQL vs NoSQL vs external API)

**Example — correct:**
```python
class UserService:
    def __init__(self, repo: UserRepository):
        self._repo = repo

    async def create(self, data: UserCreate) -> User:
        existing = await self._repo.get_by_email(data.email)
        if existing:
            raise DuplicateEmailError(f"Email {data.email} already registered")
        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
        )
        return await self._repo.create(user)
```

### Repository Layer (`app/repositories/`)

**Purpose:** Data access — encapsulates all database operations behind a clean interface.

**Allowed:**
- SQLAlchemy queries (select, insert, update, delete)
- Relationship loading strategies (selectinload, joinedload)
- Pagination and filtering at the query level
- Mapping database exceptions to domain exceptions
- Using the async session for all operations

**Forbidden:**
- Business rules (what to do with the data)
- HTTP concepts
- Knowledge of who calls it (router, service, background task)
- Raising HTTPException

**Example — correct:**
```python
class UserRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def list_paginated(
        self, cursor: str | None, limit: int
    ) -> list[User]:
        stmt = select(User).order_by(User.id)
        if cursor:
            stmt = stmt.where(User.id > decode_cursor(cursor))
        stmt = stmt.limit(limit + 1)  # fetch one extra to check has_more
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
```

### Model Layer (`app/models/`)

**Purpose:** Database table definitions — the source of truth for database schema.

**Allowed:**
- Column definitions with types and constraints
- Relationship definitions
- Table-level constraints (unique, check, index)
- Hybrid properties for computed columns
- `__tablename__` and table args

**Forbidden:**
- Business logic methods
- Validation beyond database constraints
- Import of service or repository classes

### Schema Layer (`app/schemas/`)

**Purpose:** Data transfer objects — define the shape of API request and response bodies.

**Allowed:**
- Field definitions with types and validation
- Pydantic validators (@field_validator, @model_validator)
- Computed fields (@computed_field)
- Model config (ConfigDict)
- Naming convention: XxxCreate, XxxUpdate, XxxResponse, XxxListResponse

**Forbidden:**
- Database operations
- Business logic beyond field-level validation
- Import of models or repositories

## Frontend Layers

### Pages (`src/pages/`)

**Purpose:** Route entry points — one page component per route.

**Allowed:**
- Compose layout and feature components
- Use hooks for data fetching and state
- Handle route parameters
- Page-level error boundaries

**Forbidden:**
- Direct API calls (use hooks)
- Complex business logic (extract to hooks)

### Feature Components (`src/components/`)

**Purpose:** Domain-specific UI components.

**Allowed:**
- Render domain-specific UI (UserList, OrderForm)
- Use custom hooks for data
- Handle user interactions
- Local state for UI concerns

### Hooks (`src/hooks/`)

**Purpose:** Encapsulate data fetching, business logic, and reusable state.

**Allowed:**
- TanStack Query hooks (useQuery, useMutation)
- State management logic
- Side effects (useEffect)
- Custom business logic

**Forbidden:**
- Direct DOM manipulation
- Rendering JSX

### Services (`src/services/`)

**Purpose:** API client functions — the only layer that knows about HTTP endpoints.

**Allowed:**
- Fetch/axios calls to backend API
- Request/response type definitions
- Token attachment (via interceptor)
- Error response parsing

**Forbidden:**
- React hooks (these are plain functions)
- UI logic
- State management
