---
name: tdd-workflow
description: >-
  Test-driven development workflow enforcement for Python and React projects. Use when
  the user requests TDD, test-first development, or red-green-refactor methodology.
  Enforces strict cycle: write ONE failing test -> implement minimum code to pass ->
  refactor while green -> repeat. Applies to both backend (pytest) and frontend (Testing
  Library). Changes agent behavior to write tests before code. Does NOT provide testing
  patterns (use pytest-patterns or react-testing-patterns for how to write tests).
license: MIT
compatibility: 'Python 3.12+, pytest, React 18+, Testing Library, Vitest/Jest'
metadata:
  author: platform-team
  version: '1.0.0'
  sdlc-phase: testing
allowed-tools: Read Edit Write Bash(pytest:*) Bash(npm:*)
context: fork
---

# TDD Workflow

Strict test-driven development workflow enforcement for Python and React projects. This
skill changes agent behavior so that tests are always written before production code,
following the red-green-refactor cycle without exception.

## When to Use

Activate this skill when:

- The user explicitly requests TDD, test-first development, or red-green-refactor
- Building new functions, methods, classes, or modules from scratch
- Creating new API endpoints or route handlers
- Building new React components or hooks
- Fixing bugs that need regression test coverage
- The user says "write tests first" or "I want test coverage for this"

Do NOT use this skill when:

- Modifying configuration files (settings, env, CI configs)
- Writing static content (HTML templates, markdown, copy)
- One-line trivial fixes where the behavior is self-evident
- Updating dependencies or lock files
- Writing database migrations (test the migration result, not the migration itself)
- Generating boilerplate or scaffolding code
- The user explicitly says "skip tests" or "no tests needed"

If the user asks for help writing tests but does not want TDD workflow enforcement, use
`pytest-patterns` (backend) or `react-testing-patterns` (frontend) instead. This skill
is about the workflow discipline, not the testing patterns themselves.

## Instructions

### The TDD Cycle

Every piece of functionality MUST go through these three phases in strict order. There
are no exceptions. Do not combine phases or skip ahead.

#### Phase 1: RED -- Write ONE Failing Test

1. Identify the smallest unit of behavior to implement next.
2. Write exactly ONE test that describes that behavior.
3. The test MUST assert the expected outcome clearly.
4. Run the test suite and confirm the new test FAILS.
5. If the test passes without new code, the test is wrong or the behavior already exists.
   Investigate before proceeding.

The failing test output is your specification. Read the failure message carefully. It
tells you exactly what code you need to write.

```
# Backend: run only the failing test for fast feedback
pytest tests/unit/test_user_service.py::test_create_user_returns_user_object -x

# Frontend: run tests in watch mode filtered to file
npm test -- --watch tests/UserForm.test.tsx
```

#### Phase 2: GREEN -- Write MINIMUM Code to Pass

1. Write the absolute minimum production code to make the failing test pass.
2. Do NOT add extra functionality, handle edge cases, or refactor yet.
3. Do NOT write more than what the test demands.
4. Run the FULL test suite (not just the new test) to confirm all tests pass.
5. If any test fails, fix the production code until ALL tests are green.

```
# Backend: run full suite to ensure nothing broke
pytest -x

# Frontend: run full suite
npm test -- --run
```

Resist the temptation to "just add this one extra thing." If you think of another
behavior, write it down as a future test. Stay in the GREEN phase.

#### Phase 3: REFACTOR -- Clean Up While Green

1. Review both the test code and the production code.
2. Remove duplication. Improve naming. Extract helpers or constants.
3. Simplify logic without changing behavior.
4. After EACH refactoring change, run the full test suite.
5. If any test fails, undo the refactoring change immediately.
6. Commit when all tests pass and the code is clean.

```
# Verify after each refactor step
pytest -x && echo "REFACTOR SAFE"

# Or frontend
npm test -- --run && echo "REFACTOR SAFE"
```

#### Then Repeat

Go back to Phase 1 with the next behavior. Each cycle should take 2-10 minutes.

### Rules -- Non-Negotiable

1. **NEVER write production code without a failing test first.** If you catch yourself
   writing production code, stop. Write the test. See it fail. Then proceed.

2. **NEVER write more than one failing test at a time.** One test, one behavior, one
   cycle. If you have multiple tests in your head, write them down as comments or a
   TODO list, but only implement one at a time.

3. **COMMIT after each GREEN phase.** Each commit represents a working increment. The
   commit message should describe the behavior added, not the implementation details.
   Format: `test: add [behavior] | feat: implement [behavior]`

4. **Each test describes exactly one behavior.** If a test name contains "and," split
   it into two tests. The test name is the specification.

5. **Tests must be deterministic.** No randomness, no time-dependence, no external
   service calls. Mock what you must, freeze time if needed.

6. **Tests must be fast.** Unit tests under 100ms each. If a test is slow, it belongs
   in integration, not unit.

### Backend TDD Flow (Python / pytest)

Follow this exact sequence for each cycle:

```
Step 1: Write the test
  -> Edit tests/unit/test_<module>.py
  -> Add ONE test function: test_<module>_<behavior>

Step 2: Run and confirm failure
  -> pytest tests/unit/test_<module>.py::test_<module>_<behavior> -x
  -> Confirm: FAILED (expected)

Step 3: Write minimum production code
  -> Edit src/<module>.py
  -> Add minimum code to pass

Step 4: Run full suite and confirm green
  -> pytest -x
  -> Confirm: ALL PASSED

Step 5: Refactor
  -> Clean up production code and test code
  -> pytest -x after each change
  -> Confirm: ALL PASSED

Step 6: Commit
  -> git add tests/unit/test_<module>.py src/<module>.py
  -> git commit -m "feat: <behavior description>"
```

### Frontend TDD Flow (React / Testing Library)

Follow this exact sequence for each cycle:

```
Step 1: Write the test
  -> Edit src/components/__tests__/<Component>.test.tsx
  -> Add ONE test: it('should <behavior>')

Step 2: Run and confirm failure
  -> npm test -- --run src/components/__tests__/<Component>.test.tsx
  -> Confirm: FAILED (expected)

Step 3: Write minimum component code
  -> Edit src/components/<Component>.tsx
  -> Add minimum JSX/logic to pass

Step 4: Run full suite and confirm green
  -> npm test -- --run
  -> Confirm: ALL PASSED

Step 5: Refactor
  -> Extract subcomponents, custom hooks, utilities
  -> npm test -- --run after each change
  -> Confirm: ALL PASSED

Step 6: Commit
  -> git add relevant files
  -> git commit -m "feat: <behavior description>"
```

### Bug Fix TDD

When fixing a bug, the TDD cycle is the same but starts with reproducing the bug:

1. **Understand the bug.** Read the report, reproduce manually if possible.
2. **RED: Write a test that reproduces the bug.** The test should fail with the exact
   same symptom the user reported. This is your proof the bug exists.
3. **GREEN: Fix the bug.** Write the minimum code to make the reproducing test pass.
4. **REFACTOR: Clean up the fix.** Ensure all tests pass.
5. **Commit.** The commit message references the bug: `fix: prevent duplicate user
   creation (closes #123)`

The reproducing test is now a permanent regression guard. The bug can never return
without this test catching it.

## Examples

### TDD a UserService.create_user() Method

**Cycle 1: Basic user creation**

RED -- Write the first test:

```python
# tests/unit/test_user_service.py
import pytest
from app.services.user_service import UserService
from app.schemas.user import UserCreate

class TestCreateUser:
    def test_create_user_returns_user_with_email(self, db_session):
        service = UserService(db_session)
        user_data = UserCreate(email="alice@example.com", password="SecureP@ss1")

        result = service.create_user(user_data)

        assert result.email == "alice@example.com"
```

Run: `pytest tests/unit/test_user_service.py::TestCreateUser::test_create_user_returns_user_with_email -x`
Expected: FAILED (ImportError or AttributeError -- UserService.create_user does not exist)

GREEN -- Write minimum code:

```python
# app/services/user_service.py
from app.schemas.user import UserCreate, UserRead

class UserService:
    def __init__(self, db):
        self.db = db

    def create_user(self, data: UserCreate) -> UserRead:
        user = User(email=data.email, hashed_password="placeholder")
        self.db.add(user)
        self.db.flush()
        return UserRead.model_validate(user)
```

Run: `pytest -x` -> ALL PASSED. Commit.

**Cycle 2: Password is hashed**

RED:

```python
    def test_create_user_hashes_password(self, db_session):
        service = UserService(db_session)
        user_data = UserCreate(email="bob@example.com", password="SecureP@ss1")

        service.create_user(user_data)

        stored_user = db_session.query(User).filter_by(email="bob@example.com").first()
        assert stored_user.hashed_password != "SecureP@ss1"
        assert stored_user.hashed_password.startswith("$2b$")
```

Run: FAILED (hashed_password is "placeholder", not bcrypt). Expected.

GREEN:

```python
    def create_user(self, data: UserCreate) -> UserRead:
        hashed = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()
        user = User(email=data.email, hashed_password=hashed)
        self.db.add(user)
        self.db.flush()
        return UserRead.model_validate(user)
```

Run: `pytest -x` -> ALL PASSED. Commit.

**Cycle 3: Duplicate email raises error**

RED:

```python
    def test_create_user_duplicate_email_raises(self, db_session):
        service = UserService(db_session)
        user_data = UserCreate(email="dup@example.com", password="SecureP@ss1")

        service.create_user(user_data)

        with pytest.raises(ValueError, match="Email already registered"):
            service.create_user(user_data)
```

Run: FAILED (IntegrityError instead of ValueError, or no error). Expected.

GREEN:

```python
    def create_user(self, data: UserCreate) -> UserRead:
        existing = self.db.query(User).filter_by(email=data.email).first()
        if existing:
            raise ValueError("Email already registered")
        hashed = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()
        user = User(email=data.email, hashed_password=hashed)
        self.db.add(user)
        self.db.flush()
        return UserRead.model_validate(user)
```

Run: `pytest -x` -> ALL PASSED. Commit.

Three cycles, three behaviors, three commits. Each increment is tested and working.

## Edge Cases

### When to Skip TDD

TDD is a discipline, not a religion. Skip it when the overhead outweighs the benefit:

- **Configuration files**: `settings.py`, `.env`, `pyproject.toml`. Test the behavior
  the configuration enables, not the configuration itself.
- **Static content**: HTML templates, marketing copy, README files.
- **Generated code**: ORM migrations, protobuf stubs, OpenAPI client code. Test what
  uses them, not the generated output.
- **Exploratory spikes**: When you are investigating feasibility, not building features.
  Throw away the spike and TDD the real implementation.
- **One-line obvious fixes**: Typo in a string, bumping a version number, fixing an
  import path. Use judgment -- if the fix could break something, write the test.

When you skip TDD, leave a comment or commit message explaining why: `chore: update
config (no TDD -- static configuration only)`

### TDD with External Dependencies

External services (APIs, databases, message queues) require careful handling in TDD:

- **Unit tests**: Always mock external dependencies. The test must run offline and in
  milliseconds. Use `unittest.mock.patch` or `pytest-mock`.
- **Integration tests**: Use real dependencies but in controlled environments (test
  database, mock server, Docker containers). These run slower and are separate from the
  TDD cycle.
- **Contract tests**: When mocking an external API, record the real response first, then
  replay it in tests. Libraries like `responses` (Python) or `msw` (React) help.

The TDD cycle itself uses unit tests. Integration tests are written after the TDD cycles
are complete to verify the pieces connect correctly.

### Handling Flaky Tests

If a test passes sometimes and fails sometimes, it is not a valid TDD test:

1. Identify the source of flakiness (time, randomness, concurrency, external service).
2. Eliminate it (freeze time with `freezegun`, seed random, serialize tests, mock service).
3. If you cannot eliminate flakiness, move the test to integration suite and mark it
   `@pytest.mark.flaky(reruns=3)` as a temporary measure.
4. Never ignore a flaky test. It erodes trust in the entire test suite.

### TDD for Async Code

Async code follows the same RED-GREEN-REFACTOR cycle. The only difference is test setup:

```python
import pytest

@pytest.mark.anyio
async def test_async_create_user(async_db_session):
    service = UserService(async_db_session)
    result = await service.create_user(UserCreate(email="a@b.com", password="Pass123!"))
    assert result.email == "a@b.com"
```

The cycle is identical. Write async test, see it fail, write async code, see it pass,
refactor, commit. The `anyio` marker handles the event loop.
