"""
Service Unit Test Template
============================

Tests the service (business logic) layer in isolation by mocking the
repository.  This guarantees that failures point to logic bugs, not
database issues.

Approach:
  - Mock the repository with AsyncMock
  - Inject the mock into the service
  - Verify business rules, validation, and exception handling
  - Use @pytest.mark.parametrize for combinatorial inputs
"""

from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.models.order import Order
from app.services.order_service import OrderService
from app.exceptions import InsufficientStockError, OrderNotFoundError
from tests.factories import OrderFactory, UserFactory


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_repo() -> AsyncMock:
    """Return a fully-mocked OrderRepository."""
    return AsyncMock()


@pytest.fixture
def service(mock_repo: AsyncMock) -> OrderService:
    """OrderService wired to the mocked repository."""
    return OrderService(repository=mock_repo)


# ---------------------------------------------------------------------------
# 1. Happy path
# ---------------------------------------------------------------------------
class TestPlaceOrder:

    @pytest.mark.asyncio
    async def test_place_order_persists_and_returns_order(
        self, service: OrderService, mock_repo: AsyncMock
    ):
        """Service should calculate total, persist, and return the order."""
        user = UserFactory.build()
        mock_repo.create.return_value = OrderFactory.build(
            user=user, quantity=3, unit_price=Decimal("10.00"), total=Decimal("30.00")
        )

        result = await service.place_order(
            user_id=user.id, product_id="prod-1", quantity=3, unit_price=Decimal("10.00")
        )

        assert result.total == Decimal("30.00")
        assert result.status == "pending"
        mock_repo.create.assert_awaited_once()


# ---------------------------------------------------------------------------
# 2. Business rule enforcement
# ---------------------------------------------------------------------------
class TestBusinessRules:

    @pytest.mark.asyncio
    async def test_rejects_zero_quantity(self, service: OrderService):
        """Placing an order with quantity <= 0 must raise ValueError."""
        with pytest.raises(ValueError, match="Quantity must be at least 1"):
            await service.place_order(
                user_id=uuid4(), product_id="prod-1", quantity=0, unit_price=Decimal("5.00")
            )

    @pytest.mark.asyncio
    async def test_rejects_negative_price(self, service: OrderService):
        """Negative unit price is not allowed."""
        with pytest.raises(ValueError, match="Unit price must be positive"):
            await service.place_order(
                user_id=uuid4(), product_id="prod-1", quantity=1, unit_price=Decimal("-1.00")
            )

    @pytest.mark.asyncio
    async def test_raises_when_stock_insufficient(
        self, service: OrderService, mock_repo: AsyncMock
    ):
        """Service checks inventory and raises if stock is too low."""
        mock_repo.check_stock.return_value = 2  # only 2 available

        with pytest.raises(InsufficientStockError):
            await service.place_order(
                user_id=uuid4(), product_id="prod-1", quantity=5, unit_price=Decimal("10.00")
            )


# ---------------------------------------------------------------------------
# 3. Exception handling
# ---------------------------------------------------------------------------
class TestGetOrder:

    @pytest.mark.asyncio
    async def test_raises_not_found_for_unknown_id(
        self, service: OrderService, mock_repo: AsyncMock
    ):
        """Service wraps the repo's None return into a domain exception."""
        mock_repo.get_by_id.return_value = None

        with pytest.raises(OrderNotFoundError):
            await service.get_order(order_id=uuid4())

    @pytest.mark.asyncio
    async def test_returns_order_when_found(
        self, service: OrderService, mock_repo: AsyncMock
    ):
        """Happy path: repo returns an order, service passes it through."""
        expected = OrderFactory.build()
        mock_repo.get_by_id.return_value = expected

        result = await service.get_order(order_id=expected.id)

        assert result.id == expected.id
        mock_repo.get_by_id.assert_awaited_once_with(expected.id)


# ---------------------------------------------------------------------------
# 4. Parametrized tests — multiple input combinations
# ---------------------------------------------------------------------------
class TestDiscountCalculation:

    @pytest.mark.parametrize(
        "quantity, unit_price, expected_discount_pct",
        [
            (1, Decimal("100.00"), Decimal("0")),         # no discount
            (10, Decimal("100.00"), Decimal("5")),         # 5% bulk discount
            (50, Decimal("100.00"), Decimal("10")),        # 10% bulk discount
            (100, Decimal("100.00"), Decimal("15")),       # 15% bulk discount
        ],
        ids=["no-discount", "small-bulk", "medium-bulk", "large-bulk"],
    )
    @pytest.mark.asyncio
    async def test_bulk_discount_tiers(
        self,
        service: OrderService,
        mock_repo: AsyncMock,
        quantity: int,
        unit_price: Decimal,
        expected_discount_pct: Decimal,
    ):
        """Verify that the correct discount tier is applied based on quantity."""
        mock_repo.create.return_value = OrderFactory.build(
            quantity=quantity, unit_price=unit_price
        )
        mock_repo.check_stock.return_value = quantity + 100  # plenty of stock

        result = await service.place_order(
            user_id=uuid4(), product_id="prod-1", quantity=quantity, unit_price=unit_price
        )

        assert result.discount_pct == expected_discount_pct
