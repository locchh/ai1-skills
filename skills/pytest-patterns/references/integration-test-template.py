"""
Integration Test Template
===========================

Tests the repository and service layers together with a real (test)
database.  Unlike unit tests, nothing is mocked — the goal is to verify
that SQL queries, ORM mappings, and transaction behavior work correctly.

Fixtures used:
  db_session  -> transactional AsyncSession (rolls back after each test)

These tests are slower than pure unit tests but catch issues that mocks
cannot: bad SQL, incorrect column mappings, constraint violations, and
transaction semantics.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.user import User
from app.repositories.order_repository import OrderRepository
from app.repositories.user_repository import UserRepository
from app.services.order_service import OrderService
from tests.factories import UserFactory, OrderFactory


# ---------------------------------------------------------------------------
# Fixtures — wire real repositories and service
# ---------------------------------------------------------------------------
@pytest.fixture
def user_repo(db_session: AsyncSession) -> UserRepository:
    return UserRepository(session=db_session)


@pytest.fixture
def order_repo(db_session: AsyncSession) -> OrderRepository:
    return OrderRepository(session=db_session)


@pytest.fixture
def order_service(order_repo: OrderRepository) -> OrderService:
    return OrderService(repository=order_repo)


# ---------------------------------------------------------------------------
# 1. Repository — data persistence
# ---------------------------------------------------------------------------
class TestOrderRepository:

    @pytest.mark.asyncio
    async def test_create_persists_order_to_database(
        self, order_repo: OrderRepository, db_session: AsyncSession
    ):
        """Verify that create() writes a row visible within the same session."""
        user = UserFactory.build()
        db_session.add(user)
        await db_session.flush()

        order = Order(
            id=uuid4(),
            user_id=user.id,
            status="pending",
            quantity=2,
            unit_price=Decimal("25.00"),
            total=Decimal("50.00"),
        )
        created = await order_repo.create(order)

        # Read back from the session to confirm persistence
        result = await db_session.execute(
            select(Order).where(Order.id == created.id)
        )
        persisted = result.scalar_one()
        assert persisted.total == Decimal("50.00")
        assert persisted.user_id == user.id

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_for_missing_record(
        self, order_repo: OrderRepository
    ):
        """Repository returns None instead of raising when the ID is absent."""
        result = await order_repo.get_by_id(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_list_by_user_returns_only_that_users_orders(
        self, order_repo: OrderRepository, db_session: AsyncSession
    ):
        """Filtering by user_id must not leak orders from other users."""
        user_a = UserFactory.build()
        user_b = UserFactory.build()
        db_session.add_all([user_a, user_b])
        await db_session.flush()

        order_a = OrderFactory.build(user=user_a, user_id=user_a.id)
        order_b = OrderFactory.build(user=user_b, user_id=user_b.id)
        db_session.add_all([order_a, order_b])
        await db_session.flush()

        results = await order_repo.list_by_user(user_a.id)

        assert len(results) == 1
        assert results[0].user_id == user_a.id


# ---------------------------------------------------------------------------
# 2. Service + Repository — end-to-end business logic
# ---------------------------------------------------------------------------
class TestOrderServiceIntegration:

    @pytest.mark.asyncio
    async def test_place_order_writes_correct_total(
        self, order_service: OrderService, db_session: AsyncSession
    ):
        """
        The service calculates the total and the repository persists it.
        Verify the computed value survives the round-trip to the database.
        """
        user = UserFactory.build()
        db_session.add(user)
        await db_session.flush()

        order = await order_service.place_order(
            user_id=user.id,
            product_id="prod-42",
            quantity=4,
            unit_price=Decimal("12.50"),
        )

        # Re-query to confirm the DB holds the correct total
        result = await db_session.execute(
            select(Order).where(Order.id == order.id)
        )
        persisted = result.scalar_one()
        assert persisted.total == Decimal("50.00")
        assert persisted.status == "pending"


# ---------------------------------------------------------------------------
# 3. Transaction behavior
# ---------------------------------------------------------------------------
class TestTransactionBehavior:

    @pytest.mark.asyncio
    async def test_failed_operation_does_not_leave_partial_data(
        self, order_service: OrderService, db_session: AsyncSession
    ):
        """
        If the service raises mid-operation, no partial records should
        remain.  The test session's transaction rollback guarantees this,
        but we verify it explicitly.
        """
        user = UserFactory.build()
        db_session.add(user)
        await db_session.flush()

        # Force a failure (negative price triggers ValueError in the service)
        with pytest.raises(ValueError):
            await order_service.place_order(
                user_id=user.id,
                product_id="prod-99",
                quantity=1,
                unit_price=Decimal("-5.00"),
            )

        # Confirm no order was persisted
        result = await db_session.execute(
            select(Order).where(Order.user_id == user.id)
        )
        assert result.scalars().all() == []

    @pytest.mark.asyncio
    async def test_session_isolation_between_tests(
        self, db_session: AsyncSession
    ):
        """
        Verify that data created in other tests is not visible here.
        Because each test wraps in a rolled-back transaction, the orders
        table should be empty at the start of every test.
        """
        result = await db_session.execute(select(Order))
        orders = result.scalars().all()

        # If isolation is working, no leftover rows from previous tests
        assert len(orders) == 0
