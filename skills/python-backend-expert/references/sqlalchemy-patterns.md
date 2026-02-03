# SQLAlchemy 2.0 Advanced Patterns

## Async Session Patterns

### Creating an Async Engine and Session Factory

```python
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Use the async driver (asyncpg for PostgreSQL, aiosqlite for SQLite)
engine = create_async_engine(
    "postgresql+asyncpg://user:password@localhost:5432/mydb",
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
)

# async_sessionmaker replaces the old sessionmaker(class_=AsyncSession) pattern
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevents lazy-load issues after commit
)
```

### Dependency-Injected Session (FastAPI)

```python
from typing import AsyncGenerator

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a session and ensure it is closed after the request."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### Session Lifecycle Rules

1. One session per request -- never share sessions across requests or tasks.
2. Keep sessions short-lived -- open late, close early.
3. Set `expire_on_commit=False` when you need to access attributes after commit
   without triggering implicit IO.
4. Always use `async with` or explicit `close()` to avoid connection leaks.

---

## Query Optimization: Eager Loading Strategies

### selectinload -- Preferred Default

Executes a second `SELECT ... WHERE id IN (...)` query. Best for one-to-many
and many-to-many relationships because it avoids the cartesian product problem.

```python
from sqlalchemy.orm import selectinload
from sqlalchemy import select

stmt = (
    select(User)
    .options(selectinload(User.orders))
    .where(User.is_active == True)
)
result = await session.execute(stmt)
users = result.scalars().all()
# Each user.orders is already loaded -- no additional queries.
```

### joinedload -- Use for Many-to-One / One-to-One

Performs a LEFT OUTER JOIN in the same query. Ideal when the related object is
a single row (e.g., `Order.user`). Avoid for collections -- the join duplicates
the parent row for every child row.

```python
from sqlalchemy.orm import joinedload

stmt = (
    select(Order)
    .options(joinedload(Order.user))
    .where(Order.total > 100)
)
result = await session.execute(stmt)
orders = result.unique().scalars().all()  # unique() required with joinedload
```

### subqueryload -- Use for Large Collections

Issues a separate subquery. Useful when the IN-list for `selectinload` would be
too large (thousands of parent IDs).

```python
from sqlalchemy.orm import subqueryload

stmt = (
    select(Department)
    .options(subqueryload(Department.employees))
)
```

### When to Use Each

| Strategy       | Best For                        | Avoids                     |
|----------------|---------------------------------|----------------------------|
| selectinload   | One-to-many, many-to-many       | Cartesian product          |
| joinedload     | Many-to-one, one-to-one         | Extra query round-trip     |
| subqueryload   | Very large parent result sets   | Huge IN-clause             |
| lazyload       | Rarely accessed relationships   | N+1 (use with caution)     |

---

## Bulk Operations

### bulk_save_objects (ORM-level, slower)

Triggers ORM events and identity map management. Use only when you need ORM
hooks.

```python
users = [User(name=f"user_{i}") for i in range(10_000)]
session.add_all(users)
await session.flush()
```

### bulk_insert_mappings (Faster, Bypasses ORM Events)

Accepts plain dictionaries. Skips most ORM overhead.

```python
await session.execute(
    User.__table__.insert(),
    [{"name": f"user_{i}", "email": f"user_{i}@example.com"} for i in range(10_000)],
)
await session.commit()
```

### Core execute for Raw Performance

The fastest path. Bypasses the ORM entirely.

```python
from sqlalchemy import insert

stmt = insert(User).values(
    [{"name": f"user_{i}", "email": f"user_{i}@example.com"} for i in range(10_000)]
)
await session.execute(stmt)
await session.commit()
```

### Bulk Upsert (PostgreSQL)

```python
from sqlalchemy.dialects.postgresql import insert as pg_insert

stmt = pg_insert(User).values(rows)
stmt = stmt.on_conflict_do_update(
    index_elements=["email"],
    set_={"name": stmt.excluded.name, "updated_at": func.now()},
)
await session.execute(stmt)
```

---

## Relationship Loading Strategies with Code Examples

### Nested Eager Loading

```python
stmt = (
    select(User)
    .options(
        selectinload(User.orders).selectinload(Order.items),
        selectinload(User.profile),
    )
)
```

### Conditional Loading with contains_eager

Use when you already have a join in the query and want SQLAlchemy to populate
the relationship from the joined data instead of issuing a separate query.

```python
from sqlalchemy.orm import contains_eager

stmt = (
    select(Order)
    .join(Order.user)
    .options(contains_eager(Order.user))
    .where(User.is_active == True)
)
```

### Defer / Undefer Columns

```python
from sqlalchemy.orm import defer, undefer

# Skip the heavy 'body' column by default
stmt = select(Article).options(defer(Article.body))

# Explicitly load it when needed
stmt = select(Article).options(undefer(Article.body))
```

---

## Connection Pool Tuning

```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,        # Steady-state connections kept open
    max_overflow=10,     # Extra connections allowed above pool_size under burst
    pool_timeout=30,     # Seconds to wait for a connection before raising
    pool_recycle=1800,   # Seconds before a connection is recycled (avoid stale)
    pool_pre_ping=True,  # Verify connection liveness before checkout
)
```

### Guidelines

| Parameter      | Default | Recommendation                                      |
|----------------|---------|-----------------------------------------------------|
| pool_size      | 5       | Set to expected concurrent request count             |
| max_overflow   | 10      | Keep equal to or less than pool_size                 |
| pool_timeout   | 30      | Lower in latency-sensitive services (e.g., 10)       |
| pool_recycle   | -1      | Set to 1800 for MySQL/Aurora; PostgreSQL can be -1   |
| pool_pre_ping  | False   | Always True in production to avoid broken connections|

### Monitoring Pool Health

```python
from sqlalchemy import event

@event.listens_for(engine.sync_engine, "checkout")
def on_checkout(dbapi_conn, connection_rec, connection_proxy):
    logger.debug("Connection checked out from pool")

@event.listens_for(engine.sync_engine, "checkin")
def on_checkin(dbapi_conn, connection_rec):
    logger.debug("Connection returned to pool")
```

---

## Common Pitfalls

### 1. Detached Instance Errors

**Problem:** Accessing a relationship on an object after the session is closed.

```python
async with async_session_factory() as session:
    user = await session.get(User, 1)

# Session is closed -- this raises DetachedInstanceError
print(user.orders)
```

**Fix:** Eagerly load everything you need before closing the session, or set
`expire_on_commit=False`.

### 2. Lazy Loading in Async Context

**Problem:** SQLAlchemy lazy loading triggers implicit IO, which is forbidden in
an async session. You will get `MissingGreenlet` errors.

```python
# This will FAIL in async
user = await session.get(User, 1)
print(user.orders)  # MissingGreenlet error
```

**Fix:** Always use explicit eager loading (`selectinload`, `joinedload`) or
`await session.run_sync()` as an escape hatch.

```python
# Escape hatch (not recommended for production hot paths)
def _load_orders(session):
    user = session.get(User, 1)
    _ = user.orders  # Triggers lazy load inside sync context
    return user

user = await session.run_sync(_load_orders)
```

### 3. Session Scope Too Wide

**Problem:** Reusing a session across multiple requests leads to stale data and
concurrency bugs.

**Fix:** Create one session per request (see `get_async_session` above).

### 4. Forgetting unique() with joinedload

**Problem:** `joinedload` duplicates parent rows. Without `unique()`, you get
duplicate objects in results.

```python
# Wrong
result = await session.execute(stmt)
orders = result.scalars().all()  # May contain duplicates

# Correct
orders = result.unique().scalars().all()
```

### 5. N+1 Query in Loops

**Problem:** Iterating over results and accessing a relationship inside the loop.

```python
users = (await session.execute(select(User))).scalars().all()
for user in users:
    print(user.orders)  # Triggers a query per user -- N+1
```

**Fix:** Use `selectinload(User.orders)` in the original query.

### 6. Mixing sync and async engines

**Problem:** Using a synchronous engine URL (`postgresql://`) with
`create_async_engine`.

**Fix:** Always use the async driver variant:
- PostgreSQL: `postgresql+asyncpg://`
- MySQL: `mysql+aiomysql://`
- SQLite: `sqlite+aiosqlite://`
