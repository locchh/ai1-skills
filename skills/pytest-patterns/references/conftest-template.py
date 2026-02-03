"""
Production conftest.py Template
================================

This conftest provides shared fixtures for a FastAPI + SQLAlchemy async
test suite.  It manages:
  - A dedicated test database engine (session-scoped for speed)
  - Per-test database sessions that roll back automatically
  - An httpx.AsyncClient wired to the FastAPI app
  - An authenticated client with a valid JWT

Scope guidance:
  session   -> expensive resources created once (engine, table DDL)
  function  -> cheap resources that must be isolated per test (DB session)
"""

from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Application entry points
from app.core.config import settings
from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_async_session
from app.main import create_app

# Factory registrations (see factory-template.py)
from tests.factories import UserFactory, OrderFactory


# ---------------------------------------------------------------------------
# 1. pytest-asyncio configuration
# ---------------------------------------------------------------------------
# All async fixtures and tests use asyncio by default; no need for
# @pytest.mark.asyncio on every test.
pytest_plugins = []


# ---------------------------------------------------------------------------
# 2. Database engine (session scope)
# ---------------------------------------------------------------------------
# Created once per test session.  Using a dedicated test database avoids
# interference with development data.
@pytest_asyncio.fixture(scope="session")
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create an async engine pointed at the test database."""
    engine = create_async_engine(
        settings.TEST_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )

    # Create all tables before the first test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Tear down all tables after the last test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


# ---------------------------------------------------------------------------
# 3. Async session (function scope, transaction rollback)
# ---------------------------------------------------------------------------
# Each test gets its own session wrapped in a transaction that is always
# rolled back, keeping the database clean without expensive truncation.
@pytest_asyncio.fixture
async def db_session(
    db_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session that rolls back after each test."""
    connection = await db_engine.connect()
    transaction = await connection.begin()

    session_factory = async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    session = session_factory()

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


# ---------------------------------------------------------------------------
# 4. httpx.AsyncClient (function scope)
# ---------------------------------------------------------------------------
# Uses ASGI transport so no real HTTP server is started — tests are fast.
@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async test client with the DB session overridden."""
    app = create_app()

    # Override the DB dependency so all requests use the test session
    app.dependency_overrides[get_async_session] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 5. Authenticated client (function scope)
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def auth_client(
    client: AsyncClient,
    db_session: AsyncSession,
) -> AsyncClient:
    """Return a client whose requests carry a valid Authorization header."""
    # Create a real user in the test database via factory
    user = UserFactory.build()
    db_session.add(user)
    await db_session.flush()

    token = create_access_token(subject=str(user.id))
    client.headers["Authorization"] = f"Bearer {token}"
    return client


# ---------------------------------------------------------------------------
# 6. Factory session binding
# ---------------------------------------------------------------------------
# Wire factory_boy factories to the current test session so that
# Factory.create() persists objects through the same transactional session.
@pytest.fixture(autouse=True)
def _bind_factories(db_session: AsyncSession) -> None:
    """Bind all registered factories to the current test DB session."""
    for factory_cls in (UserFactory, OrderFactory):
        factory_cls._meta.sqlalchemy_session = db_session  # type: ignore[attr-defined]
