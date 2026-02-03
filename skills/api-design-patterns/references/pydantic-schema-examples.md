# Pydantic v2 Schema Examples

Complete code examples for common Pydantic v2 patterns used in FastAPI projects.

## Base Schemas

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(from_attributes=True)
```

## User Schemas (CRUD Pattern)

```python
class UserCreate(BaseModel):
    """Request body for creating a user. No id, no timestamps."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=255)


class UserUpdate(BaseModel):
    """Request body for partial update. All fields Optional."""
    email: EmailStr | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)


class UserResponse(BaseSchema):
    """Single user response. Full model with id and timestamps."""
    id: UUID
    email: str
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    """Paginated list of users."""
    items: list[UserResponse]
    next_cursor: str | None = None
    has_more: bool = False
```

## Pagination Schemas

```python
class CursorParams(BaseModel):
    """Query parameters for cursor-based pagination."""
    cursor: str | None = None
    limit: int = Field(default=20, ge=1, le=100)


class PaginatedResponse[T](BaseModel):
    """Generic paginated response."""
    items: list[T]
    next_cursor: str | None = None
    has_more: bool = False
```

## Filter Schema

```python
from enum import StrEnum


class UserStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class UserFilter(BaseModel):
    """Query parameters for filtering users."""
    status: UserStatus | None = None
    role: str | None = None
    q: str | None = Field(default=None, description="Search query")
    created_after: datetime | None = None
    created_before: datetime | None = None
```

## Error Schemas

```python
class FieldError(BaseModel):
    """Single field validation error."""
    field: str
    message: str


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    code: str
    field_errors: list[FieldError] = []
```

## Nested Resource Schemas

```python
class AddressCreate(BaseModel):
    street: str = Field(max_length=500)
    city: str = Field(max_length=100)
    state: str = Field(max_length=100)
    zip_code: str = Field(pattern=r"^\d{5}(-\d{4})?$")
    country: str = Field(default="US", max_length=2)


class AddressResponse(BaseSchema):
    id: UUID
    street: str
    city: str
    state: str
    zip_code: str
    country: str


class UserWithAddressesResponse(UserResponse):
    """User response with nested addresses."""
    addresses: list[AddressResponse] = []
```

## Discriminated Union (Polymorphic Schemas)

```python
from typing import Annotated, Literal, Union

from pydantic import Discriminator


class EmailNotification(BaseModel):
    type: Literal["email"] = "email"
    to_email: EmailStr
    subject: str
    body: str


class SMSNotification(BaseModel):
    type: Literal["sms"] = "sms"
    phone_number: str
    message: str = Field(max_length=160)


class PushNotification(BaseModel):
    type: Literal["push"] = "push"
    device_token: str
    title: str
    body: str


NotificationCreate = Annotated[
    Union[EmailNotification, SMSNotification, PushNotification],
    Discriminator("type"),
]
```

## Computed Fields

```python
from pydantic import computed_field


class OrderResponse(BaseSchema):
    id: UUID
    items: list["OrderItemResponse"]
    created_at: datetime

    @computed_field
    @property
    def total_amount(self) -> float:
        return sum(item.price * item.quantity for item in self.items)

    @computed_field
    @property
    def item_count(self) -> int:
        return len(self.items)


class OrderItemResponse(BaseSchema):
    id: UUID
    product_name: str
    price: float
    quantity: int
```

## Custom Validators

```python
from pydantic import field_validator, model_validator


class DateRangeFilter(BaseModel):
    start_date: datetime | None = None
    end_date: datetime | None = None

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                raise ValueError("start_date must be before end_date")
        return self


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    price: float = Field(gt=0)
    sku: str = Field(pattern=r"^[A-Z]{3}-\d{6}$")
    tags: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, v: list[str]) -> list[str]:
        return [tag.lower().strip() for tag in v if tag.strip()]
```

## Response Envelope Pattern (Optional)

```python
from typing import Generic, TypeVar

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Optional response envelope for consistent API structure."""
    data: T
    meta: dict | None = None


# Usage:
# ApiResponse[UserResponse](data=user, meta={"cached": True})
```

## Migration from Pydantic v1

| v1 Pattern | v2 Replacement |
|------------|---------------|
| `class Config:` | `model_config = ConfigDict(...)` |
| `Config.orm_mode = True` | `ConfigDict(from_attributes=True)` |
| `.from_orm(obj)` | `.model_validate(obj)` |
| `.dict()` | `.model_dump()` |
| `.json()` | `.model_dump_json()` |
| `@validator` | `@field_validator` |
| `@root_validator` | `@model_validator` |
| `Optional[str] = None` | `str \| None = None` |
| `constr(min_length=1)` | `Field(min_length=1)` |
