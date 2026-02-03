---
name: pytest-patterns
description: >-
  Python backend testing patterns with pytest for FastAPI applications. Use when writing
  Python tests: unit tests for services and repositories, integration tests for API
  endpoints with httpx.AsyncClient, fixture creation, factory setup with factory_boy,
  async testing with pytest-asyncio, mocking strategies, and parametrized tests.
  Covers test organization (tests/unit, tests/integration), conftest hierarchy, and
  coverage requirements. Does NOT cover frontend tests (use react-testing-patterns)
  or E2E browser tests (use e2e-testing).
license: MIT
compatibility: 'Python 3.12+, pytest 8+, pytest-asyncio, httpx, factory_boy'
metadata:
  author: platform-team
  version: '1.0.0'
  sdlc-phase: testing
allowed-tools: Read Edit Write Bash(pytest:*) Bash(python:*)
context: fork
---

# Pytest Patterns

Comprehensive testing patterns for Python backend applications built with FastAPI. This
skill provides fixtures, factories, mocking strategies, and organizational conventions
for writing reliable, maintainable, and fast test suites.

## When to Use

Activate this skill when:

- Writing unit tests for Python services, repositories, or utility modules
- Writing integration tests for FastAPI API endpoints
- Creating or modifying pytest fixtures and conftest files
- Setting up factory_boy factories for test data generation
- Writing async tests with pytest-asyncio or anyio
- Mocking external services, time, or environment variables
- Adding parametrized tests for input/output validation
- Configuring coverage thresholds and test organization

Do NOT use this skill when:

- Writing frontend React/TypeScript tests (use `react-testing-patterns`)
- Writing end-to-end browser tests (use `e2e-testing`)
- Enforcing TDD workflow discipline (use `tdd-workflow`)
- Performing security review of test code (use `code-review-security`)

## Instructions

### Fixture Architecture

Fixtures are the backbone of a pytest test suite. Organize them in a conftest hierarchy
that mirrors the test directory structure.

#### Conftest Hierarchy

```
tests/
  conftest.py              # Root: DB engine, app, base fixtures
  unit/
    conftest.py            # Unit: mocked dependencies, fast fixtures
    test_user_service.py
    test_auth_service.py
  integration/
    conftest.py            # Integration: real DB, API client, seed data
    test_users_api.py
    test_auth_api.py
```

#### Root conftest.py -- Database and Application Fixtures

The root conftest provides the database engine, session, and application instance. These
fixtures are shared by both unit and integration tests.

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.database import Base
from app.main import create_app
from app.config import get_test_settings

@pytest.fixture(scope="session")
def engine():
    """Create a test database engine once per test session."""
    settings = get_test_settings()
    engine = create_engine(settings.database_url, echo=False)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()

@pytest.fixture(scope="function")
def db_session(engine) -> Session:
    """Provide a transactional database session that rolls back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def app(db_session):
    """Create a FastAPI app with the test database session injected."""
    application = create_app()

    def override_get_db():
        yield db_session

    application.dependency_overrides[get_db] = override_get_db
    yield application
    application.dependency_overrides.clear()
```

Key principles:

- **Session scope for engine**: Creating a database engine is expensive. Do it once.
- **Function scope for session**: Each test gets a fresh transaction that rolls back.
  This ensures test isolation without the cost of recreating tables.
- **Yield for teardown**: Use `yield` instead of `return` so cleanup runs even if the
  test fails. Everything after `yield` is teardown code.

#### Unit conftest.py -- Mocked Dependencies

Unit tests should not touch the database or network. Provide fixtures with mocked
dependencies.

```python
# tests/unit/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.user_service import UserService

@pytest.fixture
def mock_user_repository():
    """Provide a mocked user repository for unit testing services."""
    repo = MagicMock()
    repo.get_by_email = MagicMock(return_value=None)
    repo.create = MagicMock()
    return repo

@pytest.fixture
def user_service(mock_user_repository):
    """Provide a UserService with mocked dependencies."""
    return UserService(repository=mock_user_repository)
```

#### Integration conftest.py -- Real HTTP Client

Integration tests hit real endpoints with a real (but transactional) database.

```python
# tests/integration/conftest.py
import pytest
from httpx import AsyncClient, ASGITransport

@pytest.fixture
async def client(app) -> AsyncClient:
    """Provide an async HTTP client for integration testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def authenticated_client(client, auth_token) -> AsyncClient:
    """Provide an authenticated async HTTP client."""
    client.headers["Authorization"] = f"Bearer {auth_token}"
    yield client
```

### Factory Pattern

Use factory_boy to generate test data consistently. Factories produce realistic data
without manual construction in every test.

#### Basic Factory Setup

```python
# tests/factories.py
import factory
from factory import LazyAttribute, Sequence, SubFactory, Faker
from app.models import User, Organization, Project

class OrganizationFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Organization
        sqlalchemy_session = None  # Set in conftest
        sqlalchemy_session_persistence = "flush"

    name = Sequence(lambda n: f"Organization {n}")
    slug = LazyAttribute(lambda obj: obj.name.lower().replace(" ", "-"))
    is_active = True

class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "flush"

    email = Faker("email")
    username = Sequence(lambda n: f"user_{n}")
    hashed_password = "$2b$12$LJ3m4ys1rJa3YDSfgGzr4OG8IuGve0TZPV1eA1XqBx.RuV4xFHJKa"
    is_active = True
    organization = SubFactory(OrganizationFactory)

class ProjectFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Project
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "flush"

    name = Faker("catch_phrase")
    description = Faker("paragraph", nb_sentences=2)
    owner = SubFactory(UserFactory)
    organization = LazyAttribute(lambda obj: obj.owner.organization)
```

#### Wiring Factories to Test Sessions

```python
# tests/conftest.py (add to existing)
from tests.factories import UserFactory, OrganizationFactory, ProjectFactory

@pytest.fixture(autouse=True)
def set_factory_sessions(db_session):
    """Bind all factories to the current test database session."""
    UserFactory._meta.sqlalchemy_session = db_session
    OrganizationFactory._meta.sqlalchemy_session = db_session
    ProjectFactory._meta.sqlalchemy_session = db_session
    yield
```

#### Using Factories in Tests

```python
def test_user_belongs_to_organization(db_session):
    org = OrganizationFactory(name="Acme Corp")
    user = UserFactory(organization=org)

    assert user.organization.name == "Acme Corp"
    assert user.organization_id == org.id

def test_project_inherits_owner_organization(db_session):
    project = ProjectFactory()

    assert project.organization == project.owner.organization
```

Factories produce the minimum viable object. Override only the fields relevant to your
test. Let defaults handle the rest.

### API Integration Tests

Integration tests for FastAPI endpoints use httpx.AsyncClient with the ASGI transport.
Each test hits a real endpoint, goes through middleware, dependency injection, and returns
a real response.

```python
# tests/integration/test_users_api.py
import pytest
from tests.factories import UserFactory

class TestCreateUser:
    @pytest.mark.anyio
    async def test_create_user_returns_201(self, client):
        payload = {"email": "new@example.com", "password": "SecureP@ss123"}

        response = await client.post("/api/v1/users", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "new@example.com"
        assert "id" in data
        assert "password" not in data
        assert "hashed_password" not in data

    @pytest.mark.anyio
    async def test_create_user_duplicate_email_returns_409(self, client, db_session):
        UserFactory(email="taken@example.com")

        payload = {"email": "taken@example.com", "password": "SecureP@ss123"}
        response = await client.post("/api/v1/users", json=payload)

        assert response.status_code == 409
        assert "already registered" in response.json()["detail"].lower()

    @pytest.mark.anyio
    async def test_create_user_invalid_email_returns_422(self, client):
        payload = {"email": "not-an-email", "password": "SecureP@ss123"}

        response = await client.post("/api/v1/users", json=payload)

        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_create_user_weak_password_returns_422(self, client):
        payload = {"email": "valid@example.com", "password": "123"}

        response = await client.post("/api/v1/users", json=payload)

        assert response.status_code == 422
```

Key principles for API integration tests:

- Test the HTTP contract: status code, response shape, error format.
- Use factories to set up preconditions (existing users, organizations).
- Assert what the API consumer cares about (response body), not internals.
- Test happy path, validation errors, conflict errors, and authorization errors.

### Async Testing

FastAPI is async. Many tests need to be async as well. Use the `anyio` marker from
pytest-asyncio for portable async tests.

#### Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

Or mark individual tests:

```python
@pytest.mark.anyio
async def test_something():
    result = await some_async_function()
    assert result is not None
```

#### Async Fixtures

```python
@pytest.fixture
async def async_db_session(engine):
    """Provide an async database session."""
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        async with session.begin():
            yield session
            await session.rollback()

@pytest.fixture
async def seeded_users(async_db_session):
    """Create a set of test users and return them."""
    users = []
    for i in range(5):
        user = User(email=f"user{i}@test.com", username=f"user_{i}")
        async_db_session.add(user)
    await async_db_session.flush()
    return users
```

#### Async Fixture Cleanup

Always use `yield` with async fixtures so teardown runs even on failure:

```python
@pytest.fixture
async def temp_file():
    path = Path("/tmp/test_output.json")
    path.write_text("{}")
    yield path
    if path.exists():
        path.unlink()
```

### Mocking Strategy

Follow these rules for what to mock and what to leave real:

| Dependency          | Mock it? | Why                                        |
|---------------------|----------|--------------------------------------------|
| External HTTP APIs  | YES      | Tests must run offline and fast             |
| Time / dates        | YES      | Tests must be deterministic                 |
| Environment vars    | YES      | Tests must not depend on host config        |
| Database            | NO       | Use a test DB with transaction rollback     |
| Internal services   | DEPENDS  | Mock in unit tests, real in integration     |
| File system         | DEPENDS  | Use tmp_path fixture when possible          |
| Logging             | NO       | Let it log; assert log output if needed     |

#### Mocking External Services

```python
from unittest.mock import patch, AsyncMock

@pytest.mark.anyio
async def test_send_welcome_email(user_service):
    mock_email = AsyncMock(return_value={"status": "sent"})

    with patch("app.services.email.send_email", mock_email):
        await user_service.create_user(UserCreate(
            email="new@test.com", password="Pass123!"
        ))

    mock_email.assert_called_once_with(
        to="new@test.com",
        template="welcome",
    )
```

#### Freezing Time

```python
from freezegun import freeze_time

@freeze_time("2025-01-15 10:00:00")
def test_token_expiry(auth_service):
    token = auth_service.create_token(user_id=1, expires_minutes=30)
    payload = auth_service.decode_token(token)

    assert payload["exp"] == 1736935800  # 2025-01-15 10:30:00 UTC
```

#### Monkeypatch for Environment

```python
def test_uses_production_url_in_prod(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("API_URL", "https://api.prod.example.com")

    config = load_config()

    assert config.api_url == "https://api.prod.example.com"
```

### Parametrize

Use `@pytest.mark.parametrize` to test multiple inputs against the same logic. This
reduces test code duplication and makes the input/output relationship explicit.

```python
@pytest.mark.parametrize("email,is_valid", [
    ("user@example.com", True),
    ("user@sub.domain.com", True),
    ("user+tag@example.com", True),
    ("", False),
    ("no-at-sign", False),
    ("@no-local.com", False),
    ("user@", False),
    ("user @example.com", False),
])
def test_email_validation(email, is_valid):
    if is_valid:
        assert validate_email(email) is True
    else:
        with pytest.raises(ValueError):
            validate_email(email)
```

For complex parametrize cases, use `pytest.param` with IDs:

```python
@pytest.mark.parametrize("payload,expected_status,expected_error", [
    pytest.param(
        {"email": "ok@test.com", "password": "StrongP@ss1"},
        201,
        None,
        id="valid-user-creation",
    ),
    pytest.param(
        {"email": "bad-email", "password": "StrongP@ss1"},
        422,
        "Invalid email",
        id="invalid-email-format",
    ),
    pytest.param(
        {"email": "ok@test.com", "password": "123"},
        422,
        "Password too short",
        id="weak-password",
    ),
])
@pytest.mark.anyio
async def test_create_user_validation(client, payload, expected_status, expected_error):
    response = await client.post("/api/v1/users", json=payload)
    assert response.status_code == expected_status
    if expected_error:
        assert expected_error in response.json()["detail"]
```

### Test Organization

#### Directory Structure

```
tests/
  __init__.py
  conftest.py                        # Root fixtures (engine, app, factories)
  factories.py                       # factory_boy factories
  unit/
    __init__.py
    conftest.py                      # Unit-specific fixtures (mocks)
    test_user_service.py             # Service unit tests
    test_auth_service.py
    test_validators.py
  integration/
    __init__.py
    conftest.py                      # Integration-specific (client, auth)
    test_users_api.py                # API endpoint tests
    test_auth_api.py
    test_health_api.py
```

#### Naming Conventions

- Test files: `test_<module>_<aspect>.py` (e.g., `test_user_service.py`)
- Test classes: `Test<Feature>` (e.g., `TestCreateUser`)
- Test functions: `test_<module>_<behavior>` (e.g., `test_create_user_returns_201`)
- Fixtures: descriptive nouns (e.g., `db_session`, `authenticated_client`)
- Factories: `<Model>Factory` (e.g., `UserFactory`)

#### Running Tests

```bash
# Run all tests
pytest

# Run only unit tests (fast)
pytest tests/unit -x

# Run only integration tests
pytest tests/integration -x

# Run with coverage
pytest --cov=app --cov-report=term-missing --cov-fail-under=80

# Run specific test class
pytest tests/unit/test_user_service.py::TestCreateUser -v

# Run with verbose failure output
pytest -x --tb=short
```

### Coverage Requirements

Enforce minimum coverage to prevent untested code from reaching production:

```toml
# pyproject.toml
[tool.coverage.run]
source = ["app"]
omit = ["app/migrations/*", "app/config.py"]

[tool.coverage.report]
fail_under = 80
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.",
]
```

Coverage of 80% is the minimum gate. Strive for higher on critical paths (auth,
payments, data mutations) and accept lower on generated code or simple wrappers.

## Examples

### Test User Registration Endpoint (Full Example)

This example shows a complete integration test file for a user registration endpoint,
covering the happy path, duplicate email conflict, and invalid input validation.

```python
# tests/integration/test_user_registration.py
import pytest
from tests.factories import UserFactory

class TestUserRegistration:
    """Test POST /api/v1/auth/register endpoint."""

    REGISTER_URL = "/api/v1/auth/register"

    @pytest.mark.anyio
    async def test_register_valid_user_returns_201_with_tokens(self, client):
        payload = {
            "email": "newuser@example.com",
            "password": "V3rySecure!Pass",
            "full_name": "Alice Smith",
        }

        response = await client.post(self.REGISTER_URL, json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["full_name"] == "Alice Smith"
        assert "access_token" in data
        assert "refresh_token" in data
        assert "password" not in data["user"]

    @pytest.mark.anyio
    async def test_register_duplicate_email_returns_409(self, client, db_session):
        UserFactory(email="existing@example.com")

        payload = {
            "email": "existing@example.com",
            "password": "V3rySecure!Pass",
            "full_name": "Bob Jones",
        }

        response = await client.post(self.REGISTER_URL, json=payload)

        assert response.status_code == 409
        assert "already registered" in response.json()["detail"].lower()

    @pytest.mark.anyio
    @pytest.mark.parametrize("invalid_payload,expected_field", [
        pytest.param(
            {"email": "not-email", "password": "V3rySecure!Pass"},
            "email",
            id="invalid-email",
        ),
        pytest.param(
            {"email": "ok@test.com", "password": "short"},
            "password",
            id="weak-password",
        ),
        pytest.param(
            {"password": "V3rySecure!Pass"},
            "email",
            id="missing-email",
        ),
        pytest.param(
            {"email": "ok@test.com"},
            "password",
            id="missing-password",
        ),
    ])
    async def test_register_invalid_input_returns_422(
        self, client, invalid_payload, expected_field
    ):
        response = await client.post(self.REGISTER_URL, json=invalid_payload)

        assert response.status_code == 422
        error_fields = [
            err["loc"][-1] for err in response.json()["detail"]
        ]
        assert expected_field in error_fields
```

## Edge Cases

### Async Fixture Cleanup

Async fixtures that acquire resources MUST release them even if the test fails. Always
use the yield pattern with try/finally for critical cleanup:

```python
@pytest.fixture
async def temp_upload(s3_client):
    key = f"test-uploads/{uuid4()}.txt"
    await s3_client.put_object(Bucket="test", Key=key, Body=b"test data")
    yield key
    try:
        await s3_client.delete_object(Bucket="test", Key=key)
    except Exception:
        pass  # Best-effort cleanup; don't mask test failures
```

### Test Isolation

Every test must be independent. Never rely on test execution order. Common pitfalls:

- **Shared mutable state**: Do not use module-level variables that tests modify. Use
  fixtures with function scope instead.
- **Database state leakage**: Always use transaction rollback (not truncation or manual
  delete). The `db_session` fixture above handles this.
- **File system artifacts**: Use `tmp_path` fixture for files. It auto-cleans.
- **Global singletons**: If your app uses singletons (caches, connection pools), reset
  them in a fixture or use dependency injection to swap them.

Test for isolation: run your test suite with `pytest --randomly-seed=12345`. If tests
fail in random order but pass in default order, you have an isolation bug.

### Flaky Tests

Flaky tests (pass sometimes, fail sometimes) destroy confidence in the test suite. Common
causes and fixes:

| Cause                    | Fix                                                  |
|--------------------------|------------------------------------------------------|
| Time-dependent logic     | Use `freezegun` to freeze time                       |
| Random data              | Seed the RNG or use deterministic factories          |
| Async race conditions    | Use proper await, avoid fire-and-forget tasks        |
| External service calls   | Mock all external calls; never hit real services     |
| Database ordering        | Add explicit ORDER BY; never assume row order        |
| Port conflicts           | Use dynamic port allocation in fixtures              |

If a test is flaky and you cannot fix it immediately, mark it and create a tracking
issue:

```python
@pytest.mark.flaky(reruns=3, reason="Intermittent timeout - see #456")
@pytest.mark.anyio
async def test_slow_external_service(client):
    ...
```

Never leave flaky tests unmarked. They silently erode trust.

### Testing with freezegun

When testing time-sensitive logic (token expiry, scheduled tasks, rate limiting), always
freeze time to make tests deterministic:

```python
from freezegun import freeze_time
from datetime import datetime, timedelta

class TestTokenExpiry:
    @freeze_time("2025-06-01 12:00:00")
    def test_token_is_valid_before_expiry(self, auth_service):
        token = auth_service.create_token(user_id=1, expires_minutes=60)
        assert auth_service.verify_token(token) is True

    @freeze_time("2025-06-01 12:00:00")
    def test_token_is_invalid_after_expiry(self, auth_service):
        token = auth_service.create_token(user_id=1, expires_minutes=60)

        with freeze_time("2025-06-01 13:01:00"):
            assert auth_service.verify_token(token) is False
```

### Database Constraint Testing

Test that database constraints work correctly by asserting the right exceptions:

```python
from sqlalchemy.exc import IntegrityError

def test_unique_email_constraint(db_session):
    UserFactory(email="unique@test.com")

    with pytest.raises(IntegrityError):
        UserFactory(email="unique@test.com")
        db_session.flush()
```
