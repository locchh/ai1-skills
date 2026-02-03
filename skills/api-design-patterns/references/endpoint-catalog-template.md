# API Endpoint Catalog: [Service Name]

## Base URL

`/v1/[resource]`

## Authentication

| Endpoint | Auth Required | Roles |
|----------|:------------:|-------|
| GET /resources | Yes/No | [roles] |
| POST /resources | Yes | [roles] |

## Endpoints

### GET /v1/[resources]

**Summary:** List [resources] with pagination and filtering

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| cursor | string | No | null | Pagination cursor |
| limit | integer | No | 20 | Page size (max: 100) |
| sort | string | No | created_at | Sort field |
| order | string | No | desc | Sort order (asc/desc) |
| q | string | No | null | Search query |
| status | string | No | null | Filter by status |

**Response (200):**
```json
{
  "items": [
    {
      "id": "uuid",
      "field1": "value",
      "field2": "value",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "next_cursor": "eyJpZCI6IDQyfQ==",
  "has_more": true
}
```

**Errors:**
| Status | Code | Description |
|--------|------|-------------|
| 401 | UNAUTHORIZED | Missing or invalid auth token |
| 422 | VALIDATION_ERROR | Invalid query parameters |

---

### POST /v1/[resources]

**Summary:** Create a new [resource]

**Request Body:**
```json
{
  "field1": "value",
  "field2": "value"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "field1": "value",
  "field2": "value",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

**Errors:**
| Status | Code | Description |
|--------|------|-------------|
| 400 | VALIDATION_ERROR | Invalid request body |
| 401 | UNAUTHORIZED | Missing auth |
| 409 | DUPLICATE | Resource already exists |

---

### GET /v1/[resources]/{id}

**Summary:** Get a [resource] by ID

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | uuid | Resource ID |

**Response (200):**
```json
{
  "id": "uuid",
  "field1": "value",
  "field2": "value",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

**Errors:**
| Status | Code | Description |
|--------|------|-------------|
| 401 | UNAUTHORIZED | Missing auth |
| 404 | NOT_FOUND | Resource not found |

---

### PATCH /v1/[resources]/{id}

**Summary:** Partially update a [resource]

**Request Body (all fields optional):**
```json
{
  "field1": "new value"
}
```

**Response (200):** Full updated resource (same as GET response)

**Errors:**
| Status | Code | Description |
|--------|------|-------------|
| 400 | VALIDATION_ERROR | Invalid field values |
| 401 | UNAUTHORIZED | Missing auth |
| 403 | FORBIDDEN | Not resource owner |
| 404 | NOT_FOUND | Resource not found |

---

### DELETE /v1/[resources]/{id}

**Summary:** Delete a [resource]

**Response (204):** No body

**Errors:**
| Status | Code | Description |
|--------|------|-------------|
| 401 | UNAUTHORIZED | Missing auth |
| 403 | FORBIDDEN | Not resource owner |
| 404 | NOT_FOUND | Resource not found |

---

## Schemas

### [Resource]Create
```
field1: string (required)
field2: string (required)
```

### [Resource]Update
```
field1: string (optional)
field2: string (optional)
```

### [Resource]Response
```
id: uuid
field1: string
field2: string
created_at: datetime
updated_at: datetime
```

### [Resource]ListResponse
```
items: [Resource]Response[]
next_cursor: string | null
has_more: boolean
```

### ErrorResponse
```
detail: string
code: string
field_errors: FieldError[] (optional)
```

### FieldError
```
field: string
message: string
```
