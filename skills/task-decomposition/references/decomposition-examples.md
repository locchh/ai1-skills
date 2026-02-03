# Task Decomposition Examples

Worked examples showing how to decompose features into atomic tasks for Python (FastAPI) + React/TypeScript projects.

## Example 1: Add User Authentication (JWT)

**Objective:** Implement JWT-based authentication with login, register, and token refresh.

### Task 1: Create User model with password hashing
- **Files:** `app/models/user.py`, `alembic/versions/xxx_create_users.py`
- **Preconditions:** none
- **Steps:**
  1. Define User model with id, email, hashed_password, created_at, is_active
  2. Add password hashing utility (bcrypt via passlib)
  3. Generate Alembic migration
- **Done when:** `alembic upgrade head` succeeds, `pytest tests/unit/test_user_model.py` passes
- **Complexity:** small

### Task 2: Create auth schemas
- **Files:** `app/schemas/auth.py`
- **Preconditions:** none
- **Steps:**
  1. Define LoginRequest (email, password)
  2. Define RegisterRequest (email, password, confirm_password)
  3. Define TokenResponse (access_token, refresh_token, token_type)
- **Done when:** Schemas validate with sample data
- **Complexity:** trivial

### Task 3: Create auth service
- **Files:** `app/services/auth_service.py`
- **Preconditions:** Task 1, Task 2
- **Steps:**
  1. Implement register (hash password, check duplicates, create user)
  2. Implement login (verify email + password, issue JWT pair)
  3. Implement refresh (validate refresh token, issue new access token)
- **Done when:** `pytest tests/unit/test_auth_service.py` passes
- **Complexity:** medium

### Task 4: Create JWT utility
- **Files:** `app/core/security.py`
- **Preconditions:** none
- **Steps:**
  1. Implement create_access_token (15min expiry)
  2. Implement create_refresh_token (7day expiry)
  3. Implement decode_token (validate, extract claims)
- **Done when:** `pytest tests/unit/test_security.py` passes
- **Complexity:** small

### Task 5: Create auth dependency
- **Files:** `app/dependencies.py`
- **Preconditions:** Task 4
- **Steps:**
  1. Implement get_current_user dependency (extract token, decode, fetch user)
  2. Handle expired/invalid tokens with 401 response
- **Done when:** `pytest tests/unit/test_dependencies.py -k test_get_current_user` passes
- **Complexity:** small

### Task 6: Create auth router
- **Files:** `app/routers/auth.py`
- **Preconditions:** Task 3, Task 5
- **Steps:**
  1. POST /auth/register — create user, return tokens
  2. POST /auth/login — verify credentials, return tokens
  3. POST /auth/refresh — refresh access token
- **Done when:** `pytest tests/integration/test_auth.py` passes (all 3 endpoints)
- **Complexity:** medium

### Task 7: Frontend auth service
- **Files:** `src/services/authService.ts`, `src/types/auth.ts`
- **Preconditions:** Task 6
- **Steps:**
  1. Define auth TypeScript types
  2. Implement login, register, refresh API calls
  3. Add token storage (httpOnly cookie or localStorage)
- **Done when:** `npm test -- authService` passes
- **Complexity:** small

### Task 8: Frontend auth hook and context
- **Files:** `src/hooks/useAuth.ts`, `src/contexts/AuthContext.tsx`
- **Preconditions:** Task 7
- **Steps:**
  1. Create AuthContext with user state, login, logout, isAuthenticated
  2. Create useAuth hook wrapping context
  3. Add auto-refresh on token expiry
- **Done when:** `npm test -- useAuth` passes
- **Complexity:** medium

### Task 9: Login and register pages
- **Files:** `src/pages/LoginPage.tsx`, `src/pages/RegisterPage.tsx`
- **Preconditions:** Task 8
- **Steps:**
  1. Create login form with email/password inputs
  2. Create register form with email/password/confirm inputs
  3. Handle validation errors, loading states, redirect on success
- **Done when:** Pages render, forms submit, redirect on success
- **Complexity:** medium

**Total: 9 tasks, ~15 files, estimated medium-large overall**

---

## Example 2: Add File Upload with Preview

**Objective:** Allow users to upload files (images, PDFs) with preview and storage.

### Task 1: Create storage service
- **Files:** `app/services/storage_service.py`
- **Preconditions:** none
- **Steps:**
  1. Create StorageService class with upload, download, delete methods
  2. Support local filesystem (dev) and S3 (production) via config
  3. Add file type validation (allowed extensions, max size)
- **Done when:** `pytest tests/unit/test_storage_service.py` passes
- **Complexity:** medium

### Task 2: Add file model and migration
- **Files:** `app/models/file.py`, `alembic/versions/xxx_create_files.py`
- **Preconditions:** none
- **Steps:**
  1. Define File model with id, filename, content_type, size, storage_path, uploaded_by, created_at
  2. Generate migration
- **Done when:** `alembic upgrade head` succeeds
- **Complexity:** small

### Task 3: Add file schemas and repository
- **Files:** `app/schemas/file.py`, `app/repositories/file_repository.py`
- **Preconditions:** Task 2
- **Steps:**
  1. Define FileUploadResponse, FileListResponse schemas
  2. Create repository with create, get_by_id, list_by_user, delete methods
- **Done when:** `pytest tests/unit/test_file_repository.py` passes
- **Complexity:** small

### Task 4: Add upload endpoint
- **Files:** `app/routers/files.py`
- **Preconditions:** Task 1, Task 3
- **Steps:**
  1. POST /files/upload — accept multipart/form-data, validate, store, save metadata
  2. GET /files/{id} — return file metadata
  3. GET /files/{id}/download — stream file content
  4. DELETE /files/{id} — remove file and metadata
- **Done when:** `pytest tests/integration/test_files.py` passes (all endpoints)
- **Complexity:** medium

### Task 5: Frontend upload component
- **Files:** `src/components/FileUpload.tsx`, `src/hooks/useFileUpload.ts`, `src/services/fileService.ts`
- **Preconditions:** Task 4
- **Steps:**
  1. Create file service with upload, list, delete API calls
  2. Create useFileUpload hook with progress tracking
  3. Create FileUpload component with drag-and-drop, preview, progress bar
- **Done when:** Component renders, file uploads with progress, preview shows for images
- **Complexity:** large

**Total: 5 tasks, ~10 files, estimated medium overall**

---

## Example 3: Add Pagination to Existing List

**Objective:** Convert an existing unpaginated list endpoint to cursor-based pagination.

### Task 1: Add pagination utility
- **Files:** `app/utils/pagination.py`
- **Preconditions:** none
- **Steps:**
  1. Create `CursorPage` generic class with items, next_cursor, has_more
  2. Create `paginate` helper that applies cursor + limit to a SQLAlchemy query
- **Done when:** `pytest tests/unit/test_pagination.py` passes
- **Complexity:** small

### Task 2: Update repository with cursor pagination
- **Files:** `app/repositories/item_repository.py`
- **Preconditions:** Task 1
- **Steps:**
  1. Replace `list_all` with `list_paginated(cursor, limit)`
  2. Implement cursor encoding/decoding (base64 of id)
- **Done when:** `pytest tests/unit/test_item_repository.py -k test_paginated` passes
- **Complexity:** small

### Task 3: Update endpoint and schemas
- **Files:** `app/routers/items.py`, `app/schemas/item.py`
- **Preconditions:** Task 2
- **Steps:**
  1. Add `cursor` and `limit` query parameters to GET /items
  2. Update response schema to include next_cursor and has_more
  3. Keep backward compatibility: no cursor = first page
- **Done when:** `pytest tests/integration/test_items.py -k test_pagination` passes
- **Complexity:** small

### Task 4: Update frontend hook and component
- **Files:** `src/hooks/useItems.ts`, `src/pages/ItemsPage.tsx`
- **Preconditions:** Task 3
- **Steps:**
  1. Update useItems hook to use `useInfiniteQuery` with cursor
  2. Add "Load more" button or infinite scroll to ItemsPage
- **Done when:** Items load page by page, "load more" fetches next cursor
- **Complexity:** medium

**Total: 4 tasks, ~6 files, estimated small-medium overall**

---

## Anti-Patterns to Avoid

1. **God task**: A single task that touches 10+ files. Always split.
2. **Vague verification**: "It should work" is not a done-condition. Use exact commands.
3. **Missing preconditions**: Every task after the first should list what it depends on.
4. **Over-decomposition**: 1-line config changes don't need their own task. Bundle trivial related changes.
5. **Ignoring parallelism**: If two tasks are independent, say so explicitly — it saves implementation time.
