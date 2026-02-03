---
name: api-design-patterns
description: >-
  API contract design conventions for FastAPI projects with Pydantic v2. Use during
  the design phase when planning new API endpoints, defining request/response contracts,
  designing pagination or filtering, standardizing error responses, or planning API
  versioning. Covers RESTful naming, HTTP method semantics, Pydantic v2 schema naming
  conventions (XxxCreate/XxxUpdate/XxxResponse), cursor-based pagination, standard error
  format, and OpenAPI documentation. Does NOT cover implementation details (use
  python-backend-expert) or system-level architecture (use system-architecture).
license: MIT
compatibility: 'Python 3.12+, FastAPI 0.115+, Pydantic v2'
metadata:
  author: platform-team
  version: '1.0.0'
  sdlc-phase: architecture
allowed-tools: Read Grep Glob
context: fork
---

# API Design Patterns

## When to Use

Activate this skill when:
- Designing new API endpoints (before writing code)
- Defining request/response contracts for a feature
- Standardizing pagination, filtering, or sorting across endpoints
- Designing error response format
- Planning API versioning strategy
- Reviewing API contracts for consistency

Do NOT use this skill for:
- Writing endpoint implementation code — use `python-backend-expert`
- System architecture decisions — use `system-architecture`
- Frontend API integration — use `react-frontend-expert`

## Instructions

### URL Naming Conventions

**Rules:**
- Use plural nouns for resource collections: `/users`, `/orders`, `/products`
- Use kebab-case for multi-word resources: `/order-items`, `/user-profiles`
- Maximum 2 nesting levels: `/users/{user_id}/orders` (not deeper)
- Use query parameters for filtering, sorting, pagination — not URL segments
- Action endpoints use verbs only when CRUD doesn't fit: `/users/{id}/activate`

**URL patterns:**

| Pattern | Method | Purpose | Example |
|---------|--------|---------|---------|
| `/resources` | GET | List all | `GET /users?status=active` |
| `/resources` | POST | Create one | `POST /users` |
| `/resources/{id}` | GET | Get one | `GET /users/123` |
| `/resources/{id}` | PUT | Full replace | `PUT /users/123` |
| `/resources/{id}` | PATCH | Partial update | `PATCH /users/123` |
| `/resources/{id}` | DELETE | Delete one | `DELETE /users/123` |
| `/resources/{id}/sub-resources` | GET | Nested list | `GET /users/123/orders` |

### HTTP Method Semantics

| Method | Idempotent | Safe | Status Code | Body |
|--------|-----------|------|-------------|------|
| GET | Yes | Yes | 200 | Response data |
| POST | No | No | 201 | Created resource |
| PUT | Yes | No | 200 | Updated resource |
| PATCH | No | No | 200 | Updated resource |
| DELETE | Yes | No | 204 | No body |

**Status code mapping:**

| Scenario | Status Code |
|----------|------------|
| Success (with body) | 200 OK |
| Created | 201 Created |
| Accepted (async processing) | 202 Accepted |
| No content (delete) | 204 No Content |
| Bad request (validation) | 400 Bad Request |
| Unauthorized (no auth) | 401 Unauthorized |
| Forbidden (no permission) | 403 Forbidden |
| Not found | 404 Not Found |
| Conflict (duplicate) | 409 Conflict |
| Unprocessable entity | 422 Unprocessable Entity |
| Rate limited | 429 Too Many Requests |
| Server error | 500 Internal Server Error |

### Schema Naming Convention (Pydantic v2)

Follow this naming pattern for all Pydantic models:

| Pattern | Purpose | Example |
|---------|---------|---------|
| `XxxCreate` | Request body for creation | `UserCreate(email, password)` |
| `XxxUpdate` | Request body for partial update | `UserUpdate(name?, email?)` — all Optional |
| `XxxResponse` | Single resource response | `UserResponse(id, email, name, created_at)` |
| `XxxListResponse` | Paginated list response | `UserListResponse(items, next_cursor, has_more)` |
| `XxxFilter` | Query parameters for filtering | `UserFilter(status?, role?, search?)` |

**Rules:**
- `XxxCreate`: No `id`, no timestamps. Only fields the client provides.
- `XxxUpdate`: All fields are `Optional`. Client sends only changed fields.
- `XxxResponse`: Full model with `id`, timestamps, computed fields.
- Always use `model_validate()` (not `from_orm()`) and `model_dump()` (not `dict()`)
- Use `ConfigDict(from_attributes=True)` for ORM model conversion

See `references/pydantic-schema-examples.md` for complete code examples.

### Pagination

**Default: Cursor-based pagination**

Request: `GET /resources?cursor={opaque_string}&limit=20`

Response:
```json
{
  "items": [...],
  "next_cursor": "eyJpZCI6IDQyfQ==",
  "has_more": true
}
```

**Rules:**
- `cursor` is opaque (base64-encoded, client should not parse it)
- `limit` has a default (20) and maximum (100)
- `has_more` tells the client whether to request another page
- First page: no cursor parameter
- Empty result: `items: [], next_cursor: null, has_more: false`

**When to use offset pagination instead:**
- Admin dashboards where "jump to page N" is needed
- Total count is required
- Dataset is small and rarely changes

### Filtering and Sorting

**Filtering via query parameters:**
```
GET /users?status=active&role=admin&created_after=2024-01-01
```

**Sorting:**
```
GET /users?sort=created_at&order=desc
```
- `sort`: field name (validate against allowed fields)
- `order`: `asc` or `desc` (default: `asc`)

**Search:**
```
GET /users?q=john
```
- `q`: full-text search across relevant fields

### Error Response Format

**Standard error structure:**
```json
{
  "detail": "Email already registered",
  "code": "DUPLICATE_EMAIL",
  "field_errors": [
    {
      "field": "email",
      "message": "A user with this email already exists"
    }
  ]
}
```

**Rules:**
- `detail`: Human-readable error message
- `code`: Machine-readable error code (UPPER_SNAKE_CASE)
- `field_errors`: Array of field-specific errors (for 400/422 responses)
- Validation errors (422) always include `field_errors`
- Server errors (500) never expose internal details

**Common error codes:**
- `VALIDATION_ERROR` — request body validation failed
- `NOT_FOUND` — resource does not exist
- `DUPLICATE` — unique constraint violation
- `UNAUTHORIZED` — authentication required
- `FORBIDDEN` — insufficient permissions
- `RATE_LIMITED` — too many requests

### API Versioning

**Strategy: URL prefix versioning**
```
/v1/users
/v2/users
```

**Rules:**
- Version when making breaking changes to existing endpoints
- Non-breaking changes (new optional fields, new endpoints) don't need new version
- Deprecation process:
  1. Add `Sunset` header to old version: `Sunset: Sat, 01 Mar 2025 00:00:00 GMT`
  2. Add `Deprecation` header: `Deprecation: true`
  3. Monitor usage for 2+ release cycles
  4. Remove old version

**What counts as breaking:**
- Removing a field from response
- Making an optional request field required
- Changing field types
- Removing an endpoint
- Changing error format

**What is NOT breaking:**
- Adding new optional request fields
- Adding new response fields
- Adding new endpoints
- Adding new error codes

### OpenAPI Documentation

- Use `summary` for short endpoint description (shown in list)
- Use `description` for detailed endpoint documentation
- Use `response_model` on every endpoint
- Use `tags` to group related endpoints
- Add `examples` to Pydantic schemas for auto-generated docs
- Mark deprecated endpoints with `deprecated=True`

## Examples

### Example: Design Contract for /v1/products

**Endpoints:**
| Method | Path | Summary | Status |
|--------|------|---------|--------|
| GET | `/v1/products` | List products (paginated) | 200 |
| POST | `/v1/products` | Create product | 201 |
| GET | `/v1/products/{id}` | Get product by ID | 200 |
| PATCH | `/v1/products/{id}` | Update product | 200 |
| DELETE | `/v1/products/{id}` | Delete product | 204 |
| GET | `/v1/products?q=&category=` | Search/filter products | 200 |

**Schemas:** ProductCreate, ProductUpdate, ProductResponse, ProductListResponse, ProductFilter

See `references/endpoint-catalog-template.md` for full documentation format.

## Edge Cases

- **Bulk operations**: `POST /v1/users/bulk` with array body. Return 200 with per-item status (not 201). Handle partial failures: `{results: [{id, status: "created"}, {index: 1, status: "failed", error: "..."}]}`.
- **File upload endpoints**: Use `multipart/form-data`, not JSON. Define max file size. Return file metadata in response.
- **Long-running operations**: Return `202 Accepted` with `{task_id, status_url}`. Client polls status_url until complete.
- **Nested resource creation**: `POST /users/{id}/addresses` — validate parent exists first, return 404 if not.
- **Partial failure in batch**: Never use 207 Multi-Status — it's confusing. Use 200 with per-item status in body.
