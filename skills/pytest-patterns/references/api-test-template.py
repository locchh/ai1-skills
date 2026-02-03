"""
API Integration Test Template
===============================

Tests FastAPI endpoints through an httpx.AsyncClient that speaks directly
to the ASGI app (no real HTTP server).  Every test runs inside a rolled-back
database transaction, so tests are isolated and fast.

Fixtures used:
  client       -> unauthenticated AsyncClient
  auth_client  -> AsyncClient with Authorization header
  db_session   -> transactional SQLAlchemy AsyncSession
"""

import pytest
from httpx import AsyncClient

from tests.factories import UserFactory, OrderFactory


# ---------------------------------------------------------------------------
# 1. CRUD — Users resource
# ---------------------------------------------------------------------------
class TestUserEndpoints:
    """Full CRUD lifecycle for /api/v1/users."""

    # -- CREATE ------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_create_user_returns_201(self, auth_client: AsyncClient):
        """POST /api/v1/users with valid payload returns 201 and the new resource."""
        payload = {"name": "Ada Lovelace", "email": "ada@example.com"}

        response = await auth_client.post("/api/v1/users", json=payload)

        assert response.status_code == 201
        body = response.json()
        assert body["data"]["name"] == "Ada Lovelace"
        assert body["data"]["email"] == "ada@example.com"
        assert "id" in body["data"]  # server-generated ID

    # -- READ (list) -------------------------------------------------------
    @pytest.mark.asyncio
    async def test_list_users_returns_paginated_results(
        self, auth_client: AsyncClient, db_session
    ):
        """GET /api/v1/users returns a paginated list."""
        # Arrange: seed 3 users via factory
        for _ in range(3):
            user = UserFactory.build()
            db_session.add(user)
        await db_session.flush()

        response = await auth_client.get("/api/v1/users", params={"page": 1, "limit": 2})

        assert response.status_code == 200
        body = response.json()
        assert len(body["data"]) == 2
        assert body["meta"]["total"] >= 3

    # -- READ (single) -----------------------------------------------------
    @pytest.mark.asyncio
    async def test_get_user_by_id(self, auth_client: AsyncClient, db_session):
        """GET /api/v1/users/:id returns the correct user."""
        user = UserFactory.build()
        db_session.add(user)
        await db_session.flush()

        response = await auth_client.get(f"/api/v1/users/{user.id}")

        assert response.status_code == 200
        assert response.json()["data"]["email"] == user.email

    # -- UPDATE ------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_update_user_returns_200(self, auth_client: AsyncClient, db_session):
        """PATCH /api/v1/users/:id with valid payload returns updated resource."""
        user = UserFactory.build(name="Old Name")
        db_session.add(user)
        await db_session.flush()

        response = await auth_client.patch(
            f"/api/v1/users/{user.id}",
            json={"name": "New Name"},
        )

        assert response.status_code == 200
        assert response.json()["data"]["name"] == "New Name"

    # -- DELETE ------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_delete_user_returns_204(self, auth_client: AsyncClient, db_session):
        """DELETE /api/v1/users/:id removes the resource."""
        user = UserFactory.build()
        db_session.add(user)
        await db_session.flush()

        response = await auth_client.delete(f"/api/v1/users/{user.id}")
        assert response.status_code == 204

        # Verify the resource is gone
        get_response = await auth_client.get(f"/api/v1/users/{user.id}")
        assert get_response.status_code == 404


# ---------------------------------------------------------------------------
# 2. Error cases
# ---------------------------------------------------------------------------
class TestUserErrorCases:

    @pytest.mark.asyncio
    async def test_get_nonexistent_user_returns_404(self, auth_client: AsyncClient):
        """GET /api/v1/users/:id with unknown ID returns 404."""
        response = await auth_client.get("/api/v1/users/nonexistent-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_duplicate_email_returns_409(
        self, auth_client: AsyncClient, db_session
    ):
        """POST /api/v1/users with an already-taken email returns 409 Conflict."""
        user = UserFactory.build(email="taken@example.com")
        db_session.add(user)
        await db_session.flush()

        response = await auth_client.post(
            "/api/v1/users",
            json={"name": "Another User", "email": "taken@example.com"},
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_user_with_invalid_payload_returns_422(
        self, auth_client: AsyncClient
    ):
        """POST /api/v1/users with missing required fields returns 422."""
        response = await auth_client.post("/api/v1/users", json={})

        assert response.status_code == 422
        errors = response.json()["detail"]
        field_names = [e["loc"][-1] for e in errors]
        assert "name" in field_names
        assert "email" in field_names

    @pytest.mark.asyncio
    async def test_unauthenticated_request_returns_401(self, client: AsyncClient):
        """Requests without a token are rejected with 401."""
        response = await client.get("/api/v1/users")
        assert response.status_code == 401
        assert "authorization" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 3. Response header assertions
# ---------------------------------------------------------------------------
class TestResponseHeaders:

    @pytest.mark.asyncio
    async def test_list_includes_cache_control(self, auth_client: AsyncClient):
        """GET endpoints return appropriate cache headers."""
        response = await auth_client.get("/api/v1/users")

        assert "cache-control" in response.headers
        assert "no-store" in response.headers["cache-control"]

    @pytest.mark.asyncio
    async def test_create_returns_location_header(self, auth_client: AsyncClient):
        """POST returns a Location header pointing to the new resource."""
        payload = {"name": "Grace Hopper", "email": "grace@example.com"}
        response = await auth_client.post("/api/v1/users", json=payload)

        assert response.status_code == 201
        assert "location" in response.headers
        assert response.headers["location"].startswith("/api/v1/users/")
