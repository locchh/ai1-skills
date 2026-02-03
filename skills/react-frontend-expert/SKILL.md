---
name: react-frontend-expert
description: >-
  React/TypeScript frontend implementation patterns. Use during the implementation phase
  when creating or modifying React components, custom hooks, pages, data fetching logic
  with TanStack Query, forms, or routing. Covers component structure, hooks rules, custom
  hook design (useAuth, useDebounce, usePagination), TypeScript strict-mode conventions,
  form handling, accessibility requirements, and project structure. Does NOT cover testing
  (use react-testing-patterns), E2E testing (use e2e-testing), or deployment.
license: MIT
compatibility: 'React 18+, TypeScript 5+, TanStack Query 5+, Vite 5+, React Router 6+'
metadata:
  author: platform-team
  version: '1.0.0'
  sdlc-phase: implementation
allowed-tools: Read Edit Write Bash(npm:*) Bash(npx:*)
context: fork
---

# React Frontend Expert

## When to Use

Use this skill when you are:

- Creating or modifying **React functional components** (pages, UI components, layouts).
- Writing **custom hooks** (`useAuth`, `useDebounce`, `usePagination`, or any `useXxx` pattern).
- Implementing **data fetching** with TanStack Query (`useQuery`, `useMutation`, cache invalidation, optimistic updates).
- Building **forms** with React Hook Form and Zod validation, or controlled form patterns.
- Setting up **routing** with React Router 6+ (nested routes, loaders, protected routes).
- Defining **TypeScript interfaces and types** for props, API responses, and application state.

Do **NOT** use this skill for:

- Writing component or hook tests (use `react-testing-patterns`).
- End-to-end testing with Playwright or Cypress (use `e2e-testing`).
- Deployment, bundling configuration, or CI/CD.

---

## Instructions

### 1. Component Structure

All components must be **functional components** written in TypeScript. Class components are never used.

```tsx
// src/components/UserCard.tsx

interface UserCardProps {
  userId: number;
  displayName: string;
  email: string;
  avatarUrl?: string;
  onEdit: (userId: number) => void;
}

export function UserCard({
  userId,
  displayName,
  email,
  avatarUrl,
  onEdit,
}: UserCardProps) {
  return (
    <article className="user-card" aria-label={`User card for ${displayName}`}>
      {avatarUrl && (
        <img
          src={avatarUrl}
          alt={`${displayName}'s avatar`}
          className="user-card__avatar"
        />
      )}
      <div className="user-card__info">
        <h3>{displayName}</h3>
        <p>{email}</p>
      </div>
      <button
        type="button"
        onClick={() => onEdit(userId)}
        aria-label={`Edit ${displayName}`}
      >
        Edit
      </button>
    </article>
  );
}
```

Key conventions:

- **Props interface** is always defined above the component, named `ComponentNameProps`.
- Use **named exports** for components. Use default exports only for page-level components if the router requires it.
- Destructure props in the function signature for readability.
- Never use `React.FC` -- it adds `children` implicitly and has known issues with generics. Declare the return type implicitly or use `JSX.Element` when needed.
- Keep components focused: if a component exceeds ~150 lines, extract sub-components or custom hooks.

---

### 2. Hooks

#### Rules of Hooks

These rules are enforced by the `eslint-plugin-react-hooks` linter and must never be violated:

1. Only call hooks at the **top level** of a function component or custom hook. Never inside conditions, loops, or nested functions.
2. Only call hooks from **React function components** or **custom hooks** (functions starting with `use`).

#### Custom Hook Design

Extract logic into a custom hook when:

- Two or more components share the same stateful logic.
- A component's logic is complex enough to obscure the rendering.
- The logic involves side effects (data fetching, subscriptions, timers).

**`useAuth` -- Authentication State:**

```tsx
// src/hooks/useAuth.ts

import { useContext } from "react";
import { AuthContext } from "@/contexts/AuthContext";

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
```

**`useDebounce` -- Debounced Value:**

```tsx
// src/hooks/useDebounce.ts

import { useState, useEffect } from "react";

export function useDebounce<T>(value: T, delayMs: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debouncedValue;
}
```

**`usePagination` -- Pagination State:**

```tsx
// src/hooks/usePagination.ts

import { useState, useCallback, useMemo } from "react";

interface PaginationState {
  page: number;
  pageSize: number;
  totalPages: number;
  offset: number;
  goToPage: (page: number) => void;
  nextPage: () => void;
  prevPage: () => void;
  setPageSize: (size: number) => void;
}

export function usePagination(totalItems: number, initialPageSize = 20): PaginationState {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSizeState] = useState(initialPageSize);

  const totalPages = useMemo(
    () => Math.max(1, Math.ceil(totalItems / pageSize)),
    [totalItems, pageSize],
  );

  const goToPage = useCallback(
    (p: number) => setPage(Math.max(1, Math.min(p, totalPages))),
    [totalPages],
  );

  const nextPage = useCallback(() => goToPage(page + 1), [page, goToPage]);
  const prevPage = useCallback(() => goToPage(page - 1), [page, goToPage]);

  const setPageSize = useCallback(
    (size: number) => {
      setPageSizeState(size);
      setPage(1);
    },
    [],
  );

  const offset = (page - 1) * pageSize;

  return { page, pageSize, totalPages, offset, goToPage, nextPage, prevPage, setPageSize };
}
```

---

### 3. TanStack Query (Data Fetching)

TanStack Query (formerly React Query) is the standard for server-state management. Local UI state uses `useState` or `useReducer`.

**Query Key Conventions:**

Query keys are arrays that uniquely identify a query. Use a structured hierarchy:

```tsx
// Entity list
["users", { page: 1, search: "alice" }]

// Single entity
["users", userId]

// Nested resource
["users", userId, "posts"]
```

**`useQuery` -- Fetching Data:**

```tsx
// src/hooks/useUsers.ts

import { useQuery } from "@tanstack/react-query";
import { userService } from "@/services/userService";

interface UseUsersParams {
  page: number;
  search?: string;
}

export function useUsers({ page, search }: UseUsersParams) {
  return useQuery({
    queryKey: ["users", { page, search }],
    queryFn: () => userService.list({ page, search }),
    staleTime: 30_000, // 30 seconds
    placeholderData: (previousData) => previousData, // Keep previous data while loading next page
  });
}
```

**`useMutation` -- Mutating Data:**

```tsx
// src/hooks/useCreateUser.ts

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { userService } from "@/services/userService";

export function useCreateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: userService.create,
    onSuccess: () => {
      // Invalidate all user list queries to refetch
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (error) => {
      // Handle error in the calling component
      console.error("Failed to create user:", error);
    },
  });
}
```

**Optimistic Updates:**

```tsx
export function useUpdateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: userService.update,
    onMutate: async (updatedUser) => {
      // Cancel outgoing fetches
      await queryClient.cancelQueries({ queryKey: ["users", updatedUser.id] });

      // Snapshot previous value
      const previous = queryClient.getQueryData<User>(["users", updatedUser.id]);

      // Optimistically update
      queryClient.setQueryData(["users", updatedUser.id], updatedUser);

      return { previous };
    },
    onError: (_error, updatedUser, context) => {
      // Roll back on error
      if (context?.previous) {
        queryClient.setQueryData(["users", updatedUser.id], context.previous);
      }
    },
    onSettled: (_data, _error, updatedUser) => {
      // Always refetch after mutation
      queryClient.invalidateQueries({ queryKey: ["users", updatedUser.id] });
    },
  });
}
```

**Loading and Error States:**

Every query must handle loading and error states explicitly:

```tsx
function UserList() {
  const { data, isLoading, isError, error } = useUsers({ page: 1 });

  if (isLoading) return <Spinner aria-label="Loading users" />;
  if (isError) return <ErrorMessage message={error.message} />;

  return (
    <ul role="list" aria-label="Users">
      {data.users.map((user) => (
        <li key={user.id}>
          <UserCard {...user} onEdit={handleEdit} />
        </li>
      ))}
    </ul>
  );
}
```

---

### 4. TypeScript Conventions

The project must use TypeScript strict mode (`"strict": true` in `tsconfig.json`).

**Interface vs Type:**

- Use `interface` for object shapes (props, API responses, data models). Interfaces are extendable and produce better error messages.
- Use `type` for unions, intersections, mapped types, and utility types.

```tsx
// Interface for object shapes
interface User {
  id: number;
  email: string;
  displayName: string;
  role: UserRole;
}

// Type for unions
type UserRole = "admin" | "editor" | "viewer";

// Discriminated union
type ApiResult<T> =
  | { status: "success"; data: T }
  | { status: "error"; error: string };
```

**Strict rules:**

- **Never use `any`**. Use `unknown` when the type is truly unknown, then narrow with type guards.
- Always type function parameters and return values for exported functions.
- Use `satisfies` operator for type checking without widening:

```tsx
const config = {
  apiUrl: "https://api.example.com",
  timeout: 5000,
} satisfies AppConfig;
```

---

### 5. Forms

Use React Hook Form with Zod for schema-based validation.

```tsx
// src/pages/CreateUserPage.tsx

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useCreateUser } from "@/hooks/useCreateUser";

const createUserSchema = z.object({
  email: z.string().email("Please enter a valid email"),
  displayName: z.string().min(1, "Name is required").max(100),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

type CreateUserFormData = z.infer<typeof createUserSchema>;

export function CreateUserPage() {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CreateUserFormData>({
    resolver: zodResolver(createUserSchema),
  });

  const createUser = useCreateUser();

  const onSubmit = (data: CreateUserFormData) => {
    createUser.mutate(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate aria-label="Create user form">
      <div>
        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          aria-describedby={errors.email ? "email-error" : undefined}
          aria-invalid={!!errors.email}
          {...register("email")}
        />
        {errors.email && (
          <p id="email-error" role="alert">
            {errors.email.message}
          </p>
        )}
      </div>

      <div>
        <label htmlFor="displayName">Display Name</label>
        <input
          id="displayName"
          type="text"
          aria-describedby={errors.displayName ? "name-error" : undefined}
          aria-invalid={!!errors.displayName}
          {...register("displayName")}
        />
        {errors.displayName && (
          <p id="name-error" role="alert">
            {errors.displayName.message}
          </p>
        )}
      </div>

      <div>
        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          aria-describedby={errors.password ? "password-error" : undefined}
          aria-invalid={!!errors.password}
          {...register("password")}
        />
        {errors.password && (
          <p id="password-error" role="alert">
            {errors.password.message}
          </p>
        )}
      </div>

      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Creating..." : "Create User"}
      </button>

      {createUser.isError && (
        <p role="alert" className="form-error">
          {createUser.error.message}
        </p>
      )}
    </form>
  );
}
```

Key conventions:

- Always use `noValidate` on the `<form>` to disable browser validation in favor of JS validation.
- Connect error messages to inputs with `aria-describedby` and `aria-invalid`.
- Display server errors from `useMutation` below the form.
- Use `isSubmitting` to disable the submit button and prevent double submission.

---

### 6. Accessibility (WCAG 2.1 AA)

Accessibility is a requirement, not an afterthought. Every component must meet WCAG 2.1 AA.

**Semantic HTML:**

- Use `<button>` for actions, `<a>` for navigation. Never use `<div onClick>`.
- Use heading hierarchy (`h1` > `h2` > `h3`) without skipping levels.
- Use `<nav>`, `<main>`, `<aside>`, `<header>`, `<footer>` landmarks.
- Use `<ul>` / `<ol>` for lists, `<table>` for tabular data.

**ARIA:**

- Add `aria-label` or `aria-labelledby` to interactive elements that lack visible text.
- Use `role="alert"` for error messages that appear dynamically.
- Use `aria-live="polite"` for non-urgent status updates (loading indicators, success messages).
- Never use ARIA to replicate semantics that native HTML provides. If a `<button>` works, do not use `<div role="button">`.

**Keyboard Navigation:**

- All interactive elements must be reachable via Tab.
- Custom components (dropdowns, modals, tabs) must implement arrow key navigation per WAI-ARIA patterns.
- Modals must trap focus and return focus to the trigger element on close.
- Use `tabIndex={0}` sparingly and only on elements that genuinely need to be focusable.

**Focus Management:**

- After navigation, move focus to the main content heading or use a skip link.
- After adding an item to a list, announce it with `aria-live` and optionally focus the new item.
- After deleting, focus the next logical element (next item in list, or the list container).

---

### 7. Project Structure

```
src/
  components/       # Reusable UI components (Button, Card, Modal, Spinner)
    UserCard.tsx
    ErrorMessage.tsx
  hooks/            # Custom hooks (useAuth, useDebounce, usePagination)
    useAuth.ts
    useDebounce.ts
    useUsers.ts
  pages/            # Route-level page components
    UsersPage.tsx
    CreateUserPage.tsx
  services/         # API client functions (fetch wrappers)
    userService.ts
    authService.ts
  types/            # Shared TypeScript interfaces and types
    user.ts
    api.ts
  contexts/         # React context providers
    AuthContext.tsx
  utils/            # Pure utility functions (formatDate, cn)
    format.ts
```

Rules:

- Components in `components/` are reusable and do not fetch data directly. They receive data via props.
- Hooks in `hooks/` encapsulate stateful logic and TanStack Query calls.
- Pages in `pages/` compose components and hooks into full views. They are the top-level route targets.
- Services in `services/` are plain async functions that call the API. They do not use React hooks.
- Types in `types/` are shared across the application. Component-specific prop interfaces live alongside the component file.

---

## Examples

### User List Page with TanStack Query, Pagination, and Search

```tsx
// src/pages/UsersPage.tsx

import { useState } from "react";
import { useUsers } from "@/hooks/useUsers";
import { useDebounce } from "@/hooks/useDebounce";
import { usePagination } from "@/hooks/usePagination";
import { UserCard } from "@/components/UserCard";
import { Spinner } from "@/components/Spinner";
import { ErrorMessage } from "@/components/ErrorMessage";
import { Pagination } from "@/components/Pagination";

export default function UsersPage() {
  const [searchInput, setSearchInput] = useState("");
  const debouncedSearch = useDebounce(searchInput, 300);

  // We need total count from a separate or combined query; assume useUsers returns it.
  const { page, pageSize, totalPages, goToPage, nextPage, prevPage } =
    usePagination(0, 20); // Will update once data loads

  const { data, isLoading, isError, error } = useUsers({
    page,
    search: debouncedSearch || undefined,
  });

  const handleEdit = (userId: number) => {
    // Navigate to edit page
    window.location.href = `/users/${userId}/edit`;
  };

  return (
    <main>
      <h1>Users</h1>

      <div role="search">
        <label htmlFor="user-search">Search users</label>
        <input
          id="user-search"
          type="search"
          placeholder="Search by name or email..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          aria-label="Search users by name or email"
        />
      </div>

      {isLoading && <Spinner aria-label="Loading users" />}

      {isError && <ErrorMessage message={error.message} />}

      {data && (
        <>
          <p aria-live="polite">
            Showing {data.users.length} of {data.total} users
          </p>

          <ul role="list" aria-label="User list">
            {data.users.map((user) => (
              <li key={user.id}>
                <UserCard
                  userId={user.id}
                  displayName={user.displayName}
                  email={user.email}
                  avatarUrl={user.avatarUrl}
                  onEdit={handleEdit}
                />
              </li>
            ))}
          </ul>

          {data.users.length === 0 && (
            <p>No users found matching your search.</p>
          )}

          <Pagination
            currentPage={page}
            totalPages={Math.ceil(data.total / pageSize)}
            onPageChange={goToPage}
            onNext={nextPage}
            onPrev={prevPage}
          />
        </>
      )}
    </main>
  );
}
```

---

## Edge Cases

### Stale Closures in Event Handlers

When an event handler or callback captures a state value from a previous render, it reads stale data. This is the stale closure problem.

```tsx
// BAD: count is captured at render time, stale in setTimeout
function Counter() {
  const [count, setCount] = useState(0);

  const handleClick = () => {
    setTimeout(() => {
      setCount(count + 1); // Uses stale `count`
    }, 1000);
  };

  return <button onClick={handleClick}>{count}</button>;
}

// GOOD: use functional update to always read latest state
function Counter() {
  const [count, setCount] = useState(0);

  const handleClick = () => {
    setTimeout(() => {
      setCount((prev) => prev + 1); // Always latest
    }, 1000);
  };

  return <button onClick={handleClick}>{count}</button>;
}
```

Use `useRef` for mutable values that callbacks need but that should not trigger re-renders (e.g., timers, previous values).

### TanStack Query Key Collisions

If two queries share the same key but fetch different data, they will overwrite each other's cache. Always include all parameters that affect the response in the query key:

```tsx
// BAD: same key for different pages
useQuery({ queryKey: ["users"], queryFn: () => fetchUsers({ page: 1 }) });
useQuery({ queryKey: ["users"], queryFn: () => fetchUsers({ page: 2 }) });

// GOOD: page is part of the key
useQuery({ queryKey: ["users", { page: 1 }], queryFn: () => fetchUsers({ page: 1 }) });
useQuery({ queryKey: ["users", { page: 2 }], queryFn: () => fetchUsers({ page: 2 }) });
```

### Infinite Re-renders

Common causes and fixes:

1. **Object/array literals in dependency arrays**: `useEffect` compares by reference. Creating a new object each render triggers the effect every time.

```tsx
// BAD: new object every render
useEffect(() => { fetchData(params); }, [{ page, search }]);

// GOOD: use primitive values
useEffect(() => { fetchData({ page, search }); }, [page, search]);
```

2. **Setting state inside useEffect without proper dependencies**: This creates a render loop.

```tsx
// BAD: sets state on every render
useEffect(() => {
  setProcessedData(transform(rawData));
}); // Missing dependency array!

// GOOD: only run when rawData changes
useEffect(() => {
  setProcessedData(transform(rawData));
}, [rawData]);

// BETTER: use useMemo instead of useEffect + setState
const processedData = useMemo(() => transform(rawData), [rawData]);
```

3. **Inline function definitions as props**: If a child component uses the function in its dependency array, it will re-render on every parent render.

```tsx
// BAD: new function reference every render
<ChildComponent onSelect={(id) => selectItem(id)} />

// GOOD: memoize with useCallback
const handleSelect = useCallback((id: number) => selectItem(id), []);
<ChildComponent onSelect={handleSelect} />
```

### Unmounted Component State Updates

If an async operation (API call, timeout) completes after the component unmounts, calling `setState` will log a warning. TanStack Query handles this automatically for queries. For custom async logic, use an abort signal or a ref-based guard:

```tsx
useEffect(() => {
  const controller = new AbortController();

  fetchData({ signal: controller.signal })
    .then(setData)
    .catch((err) => {
      if (err.name !== "AbortError") throw err;
    });

  return () => controller.abort();
}, []);
```
