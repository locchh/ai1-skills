"""
factory_boy Factory Template
==============================

Factories generate realistic test data with minimal boilerplate.  They
integrate with SQLAlchemy so that `Factory.create()` persists objects
through the test session (which rolls back after each test).

Key concepts:
  SubFactory     -> creates a related object automatically
  LazyAttribute  -> computes a field from other fields
  Trait          -> activates a named set of overrides
  Sequence       -> guarantees uniqueness across calls

Usage examples at the bottom of this file.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import factory
from factory import Faker, LazyAttribute, Sequence, SubFactory, Trait
from factory.alchemy import SQLAlchemyModelFactory

# Application models
from app.models.user import User
from app.models.order import Order


# ---------------------------------------------------------------------------
# 1. Base factory — shared configuration for all factories
# ---------------------------------------------------------------------------
class BaseFactory(SQLAlchemyModelFactory):
    """
    All factories inherit from this base.

    The session is injected at test time via the `_bind_factories` fixture
    in conftest.py, so factories always write through the transactional
    test session.
    """

    class Meta:
        abstract = True
        sqlalchemy_session = None            # set by fixture
        sqlalchemy_session_persistence = "flush"  # flush, not commit


# ---------------------------------------------------------------------------
# 2. UserFactory
# ---------------------------------------------------------------------------
class UserFactory(BaseFactory):
    class Meta:
        model = User

    id = LazyAttribute(lambda _: uuid4())
    email = Sequence(lambda n: f"user{n}@example.com")
    name = Faker("name")
    hashed_password = "$2b$12$fakehash"  # bcrypt-shaped placeholder
    is_active = True
    created_at = LazyAttribute(lambda _: datetime.now(timezone.utc))

    # -- Traits: activate with UserFactory(admin=True) ---------------------
    class Params:
        admin = Trait(
            role="admin",
            email=Sequence(lambda n: f"admin{n}@example.com"),
        )
        inactive = Trait(
            is_active=False,
        )
        with_avatar = Trait(
            avatar_url=Faker("image_url"),
        )

    # Default role when no trait is active
    role = "member"


# ---------------------------------------------------------------------------
# 3. OrderFactory — demonstrates relationships and computed fields
# ---------------------------------------------------------------------------
class OrderFactory(BaseFactory):
    class Meta:
        model = Order

    id = LazyAttribute(lambda _: uuid4())

    # SubFactory: automatically creates a User if none is provided
    user = SubFactory(UserFactory)
    user_id = LazyAttribute(lambda obj: obj.user.id)

    status = "pending"
    quantity = Faker("random_int", min=1, max=20)
    unit_price = LazyAttribute(
        lambda _: Decimal(str(round(Faker("pyfloat", min_value=5, max_value=500).evaluate(None, None, {"locale": None}), 2)))
    )

    # LazyAttribute: compute total from other fields
    total = LazyAttribute(lambda obj: obj.unit_price * obj.quantity)

    created_at = LazyAttribute(lambda _: datetime.now(timezone.utc))
    shipped_at = None

    # -- Traits ------------------------------------------------------------
    class Params:
        shipped = Trait(
            status="shipped",
            shipped_at=LazyAttribute(
                lambda obj: obj.created_at + timedelta(days=2)
            ),
        )
        cancelled = Trait(
            status="cancelled",
            total=Decimal("0.00"),
        )


# ---------------------------------------------------------------------------
# Usage examples (for reference — not executed)
# ---------------------------------------------------------------------------
"""
# Basic creation
user = UserFactory()            # persisted to DB, all fields auto-generated
user = UserFactory.build()      # in-memory only, not persisted

# Override fields
user = UserFactory(name="Alice", email="alice@test.com")

# Use a trait
admin = UserFactory(admin=True)
inactive = UserFactory(inactive=True)

# Create related objects
order = OrderFactory()                # also creates a User automatically
order = OrderFactory(user=admin)      # use an existing user

# Batch creation
users = UserFactory.create_batch(10)
admins = UserFactory.create_batch(3, admin=True)

# Build without persistence (useful for unit tests that don't need the DB)
order = OrderFactory.build()
"""
