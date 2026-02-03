# Pydantic v1 to v2 Migration Guide

## Side-by-Side Comparison

| Pydantic v1                        | Pydantic v2                              | Notes                              |
|------------------------------------|------------------------------------------|------------------------------------|
| `class Config:`                    | `model_config = ConfigDict(...)`         | Class-level config dict            |
| `.dict()`                          | `.model_dump()`                          | Returns dict representation        |
| `.json()`                          | `.model_dump_json()`                     | Returns JSON string                |
| `.parse_obj(data)`                 | `.model_validate(data)`                  | Validate dict into model           |
| `.parse_raw(json_str)`            | `.model_validate_json(json_str)`         | Validate JSON string into model    |
| `.from_orm(obj)`                   | `.model_validate(obj, from_attributes=True)` | ORM mode                     |
| `.schema()`                        | `.model_json_schema()`                   | JSON Schema generation             |
| `.construct()`                     | `.model_construct()`                     | Build without validation           |
| `.copy(update={...})`             | `.model_copy(update={...})`              | Shallow copy with overrides        |
| `@validator`                       | `@field_validator`                       | Per-field validation               |
| `@root_validator`                  | `@model_validator`                       | Whole-model validation             |
| `Field(regex=...)`                | `Field(pattern=...)`                     | Regex renamed to pattern           |
| `Field(min_items=...)`            | `Field(min_length=...)`                  | For list length constraints        |
| `Optional[str]`                    | `str | None`                             | Union syntax preferred             |
| `constr(min_length=1)`            | `Annotated[str, StringConstraints(min_length=1)]` | Annotated style          |

---

## class Config to ConfigDict

### v1

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True
        json_encoders = {datetime: lambda v: v.isoformat()}
        schema_extra = {"example": {"id": 1, "name": "Alice"}}
```

### v2

```python
from pydantic import BaseModel, ConfigDict

class User(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,          # replaces orm_mode
        json_encoders={datetime: lambda v: v.isoformat()},  # deprecated, use custom serializer
        json_schema_extra={"example": {"id": 1, "name": "Alice"}},
    )

    id: int
    name: str
```

Key renames inside ConfigDict:
- `orm_mode` -> `from_attributes`
- `schema_extra` -> `json_schema_extra`
- `allow_population_by_field_name` -> `populate_by_name`
- `anystr_strip_whitespace` -> `str_strip_whitespace`

---

## model_validate vs from_orm

### v1

```python
user = User.from_orm(db_user)
```

### v2

```python
user = User.model_validate(db_user, from_attributes=True)

# Or set it globally in the model config:
class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str

user = User.model_validate(db_user)  # from_attributes inherited from config
```

---

## model_dump vs dict

### v1

```python
data = user.dict(exclude_unset=True, exclude={"password"})
json_str = user.json()
```

### v2

```python
data = user.model_dump(exclude_unset=True, exclude={"password"})
json_str = user.model_dump_json()

# mode parameter controls serialization format
data = user.model_dump(mode="json")  # All values JSON-compatible (datetimes as strings, etc.)
```

---

## @validator to @field_validator

### v1

```python
from pydantic import BaseModel, validator

class User(BaseModel):
    name: str
    email: str

    @validator("name")
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("Name must not be empty")
        return v.strip()

    @validator("email")
    def email_must_contain_at(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email")
        return v
```

### v2

```python
from pydantic import BaseModel, field_validator

class User(BaseModel):
    name: str
    email: str

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name must not be empty")
        return v.strip()

    @field_validator("email")
    @classmethod
    def email_must_contain_at(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email")
        return v
```

Key differences:
- Must add `@classmethod` decorator.
- Type hints on `v` and return are recommended.
- `pre=True` is now `mode="before"`:
  `@field_validator("name", mode="before")`

---

## @root_validator to @model_validator

### v1

```python
from pydantic import BaseModel, root_validator

class DateRange(BaseModel):
    start: date
    end: date

    @root_validator
    def check_dates(cls, values):
        if values.get("end") and values.get("start"):
            if values["end"] < values["start"]:
                raise ValueError("end must be after start")
        return values
```

### v2

```python
from pydantic import BaseModel, model_validator
from typing import Self

class DateRange(BaseModel):
    start: date
    end: date

    @model_validator(mode="after")
    def check_dates(self) -> Self:
        if self.end < self.start:
            raise ValueError("end must be after start")
        return self

    # Or use mode="before" for raw data (receives dict):
    @model_validator(mode="before")
    @classmethod
    def preprocess(cls, data: dict) -> dict:
        # Modify raw input before field validation
        return data
```

Key differences:
- `mode="after"` receives the model instance (`self`), not a dict.
- `mode="before"` receives raw input data and must be a `@classmethod`.
- Return type annotation `Self` is recommended for `mode="after"`.

---

## New Features in v2

### Discriminated Unions

```python
from pydantic import BaseModel, Discriminator, Tag
from typing import Annotated, Literal, Union

class Cat(BaseModel):
    pet_type: Literal["cat"]
    meow_volume: int

class Dog(BaseModel):
    pet_type: Literal["dog"]
    bark_volume: int

class Owner(BaseModel):
    pet: Annotated[Union[Cat, Dog], Discriminator("pet_type")]
```

### Computed Fields

```python
from pydantic import BaseModel, computed_field

class Rectangle(BaseModel):
    width: float
    height: float

    @computed_field
    @property
    def area(self) -> float:
        return self.width * self.height
```

Computed fields appear in `model_dump()` and JSON schema but are not settable.

### TypeAdapter

Validate data without creating a BaseModel subclass.

```python
from pydantic import TypeAdapter

adapter = TypeAdapter(list[int])
result = adapter.validate_python(["1", "2", "3"])
# result: [1, 2, 3]

json_schema = adapter.json_schema()
# {"type": "array", "items": {"type": "integer"}}
```

---

## Common Gotchas During Migration

### 1. Validators Must Be @classmethod

Forgetting `@classmethod` on `@field_validator` raises a confusing error at
class definition time.

### 2. model_validator(mode="after") Receives self, Not dict

If you copy a `@root_validator` and change it to `@model_validator(mode="after")`
without updating the function body from `values["field"]` to `self.field`, you
will get `TypeError`.

### 3. Optional Fields Default to Required

In v1, `Optional[str]` implicitly set the default to `None`. In v2, you must
be explicit:

```python
# v2: This field is REQUIRED (must be str or None, but must be provided)
name: str | None

# v2: This field is optional with a default of None
name: str | None = None
```

### 4. Strict Mode Is Off by Default

v2 coerces types by default (e.g., `"123"` becomes `123` for an `int` field).
Enable strict mode if you want v1-like strictness:

```python
model_config = ConfigDict(strict=True)
```

### 5. json_encoders Is Deprecated

Use custom serializers instead:

```python
from pydantic import field_serializer

class Event(BaseModel):
    timestamp: datetime

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime, _info) -> str:
        return value.isoformat()
```

### 6. __fields__ Renamed to model_fields

Any code accessing `MyModel.__fields__` must change to `MyModel.model_fields`.

### 7. Performance: v2 Is Significantly Faster

v2 uses a Rust-based core (pydantic-core). Expect 5-50x speedups on
validation. No code changes needed to benefit -- just upgrade.
