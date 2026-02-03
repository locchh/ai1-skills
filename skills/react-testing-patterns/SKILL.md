---
name: react-testing-patterns
description: >-
  React component and hook testing patterns with Testing Library and Vitest. Use when
  writing tests for React components, custom hooks, or data fetching logic. Covers
  component rendering tests, user interaction simulation, async state testing, MSW for
  API mocking, hook testing with renderHook, accessibility assertions, and snapshot
  testing guidelines. Does NOT cover E2E tests (use e2e-testing) or TDD workflow
  enforcement (use tdd-workflow).
license: MIT
compatibility: 'React 18+, Testing Library 14+, Vitest 1+, MSW 2+'
metadata:
  author: platform-team
  version: '1.0.0'
  sdlc-phase: testing
allowed-tools: Read Edit Write Bash(npm:*) Bash(npx:*)
context: fork
---

# React Testing Patterns

Testing patterns for React functional components and custom hooks using Testing Library,
Vitest, and MSW. Core philosophy: **test what the user sees and does, not implementation**.

## When to Use

Use this skill when you are:

- Writing **unit or integration tests** for React functional components.
- Testing **custom hooks** (`useAuth`, `useDebounce`, any `useXxx`) with `renderHook`.
- Mocking **API responses** with MSW to test data fetching flows.
- Writing **accessibility tests** using `jest-axe` for WCAG compliance.
- Testing **async behavior** (loading states, error states, data arrival).

Do **NOT** use this skill for:

- End-to-end tests with Playwright or Cypress (use `e2e-testing`).
- Backend API tests or Python test patterns (use `pytest-patterns`).
- Enforcing red-green-refactor TDD discipline (use `tdd-workflow`).

---

## Instructions

### Component Testing Basics

Follow the **Arrange-Act-Assert** pattern. See `references/component-test-template.tsx`
for a complete template with providers, MSW, and accessibility checks.

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { UserCard } from "@/components/UserCard";

describe("UserCard", () => {
  const defaultProps = {
    userId: 1,
    displayName: "Alice",
    email: "alice@example.com",
    onEdit: vi.fn(),
  };

  it("displays the user name and email", () => {
    render(<UserCard {...defaultProps} />);
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("alice@example.com")).toBeInTheDocument();
  });

  it("calls onEdit when the edit button is clicked", async () => {
    const onEdit = vi.fn();
    const user = userEvent.setup();
    render(<UserCard {...defaultProps} onEdit={onEdit} />);
    await user.click(screen.getByRole("button", { name: /edit alice/i }));
    expect(onEdit).toHaveBeenCalledWith(1);
  });

  it("does not render an avatar when avatarUrl is not provided", () => {
    render(<UserCard {...defaultProps} />);
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });
});
```

Conventions: use `describe` blocks per component, plain English test names describing
behavior, `vi.fn()` for mocks, `screen` for all queries (never destructure from
`render()`), and `queryBy*` when asserting absence.

---

### Query Priority

Use the highest priority query that works. Never query by CSS class or `container.querySelector`.

| Priority | Query              | When to Use                                 |
|----------|--------------------|----------------------------------------------|
| 1        | `getByRole`        | Best default. Buttons, links, headings.      |
| 2        | `getByLabelText`   | Form inputs with a `<label>`.                |
| 3        | `getByPlaceholderText` | When no label exists (prefer adding one).|
| 4        | `getByText`        | Non-interactive text content.                |
| 5        | `getByDisplayValue`| Inputs with a current value.                 |
| 6        | `getByAltText`     | Images.                                      |
| 7        | `getByTitle`       | Last resort before test ID.                  |
| 8        | `getByTestId`      | Escape hatch. Requires `data-testid`.        |

```tsx
// GOOD                                      // BAD
screen.getByRole("button", { name: "Submit" });  // container.querySelector(".btn")
screen.getByLabelText("Email");                   // container.querySelector('[class*="email"]')
```

---

### User Interaction Testing

Always use `@testing-library/user-event` over `fireEvent`. `userEvent` simulates the
full browser event sequence (focus, keydown, keyup, input, click) and catches bugs
that `fireEvent` misses. All methods are async -- always `await` them.

```tsx
import userEvent from "@testing-library/user-event";

const user = userEvent.setup(); // Call setup() before interactions

await user.click(screen.getByRole("button", { name: "Submit" }));
await user.type(screen.getByLabelText("Email"), "alice@example.com");
await user.clear(screen.getByLabelText("Email"));
await user.selectOptions(screen.getByLabelText("Role"), "admin");
await user.tab();
await user.keyboard("{Control>}a{/Control}");
```

---

### Testing Async Components

**`findBy*`** waits for an element to appear (default 1000ms). **`waitFor`** waits for
an assertion to pass. Use them for loading states, error states, and data arrival.

```tsx
it("shows user data after loading", async () => {
  render(<UserProfile userId={1} />);
  expect(await screen.findByText("Alice")).toBeInTheDocument();
});

it("removes the spinner after data loads", async () => {
  render(<UserProfile userId={1} />);
  expect(screen.getByRole("progressbar")).toBeInTheDocument();
  await waitFor(() => {
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  });
});
```

**TanStack Query components** need a fresh `QueryClientProvider` per test:

```tsx
function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}
```

Set `retry: false` (fail immediately) and `gcTime: 0` (prevent cache leaks).

---

### API Mocking with MSW

MSW intercepts network requests at the Node level, decoupled from `fetch` vs `axios`.
See `references/msw-handler-examples.ts` for complete CRUD, auth, and error handlers.

**Setup:**

```tsx
// src/test/mocks/server.ts
import { setupServer } from "msw/node";
import { handlers } from "./handlers";
export const server = setupServer(...handlers);

// src/test/setup.ts
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

**Per-test overrides** (restored automatically by `afterEach`):

```tsx
it("shows error state when API returns 500", async () => {
  server.use(
    http.get("/api/users", () =>
      HttpResponse.json({ detail: "Server error" }, { status: 500 }),
    ),
  );
  render(<UsersPage />);
  expect(await screen.findByText(/server error/i)).toBeInTheDocument();
});
```

---

### Hook Testing

Use `renderHook` from Testing Library. See `references/hook-test-template.tsx` for
complete synchronous and async hook examples.

**Synchronous hooks:**

```tsx
import { renderHook, act } from "@testing-library/react";

it("increments the count", () => {
  const { result } = renderHook(() => useCounter(0));
  act(() => { result.current.increment(); });
  expect(result.current.count).toBe(1);
});
```

**Hooks with prop changes:**

```tsx
it("updates debounced value after delay", () => {
  vi.useFakeTimers();
  const { result, rerender } = renderHook(
    ({ value, delay }) => useDebounce(value, delay),
    { initialProps: { value: "hello", delay: 300 } },
  );
  rerender({ value: "world", delay: 300 });
  expect(result.current).toBe("hello");
  act(() => { vi.advanceTimersByTime(300); });
  expect(result.current).toBe("world");
  vi.useRealTimers();
});
```

**Async hooks (TanStack Query):** provide a `QueryClientProvider` wrapper via the
`wrapper` option of `renderHook`, creating a fresh `QueryClient` per test.

---

### Accessibility Testing

Add `jest-axe` assertions to **every component test**. Register the matcher globally
in `src/test/setup.ts`:

```tsx
import { toHaveNoViolations } from "jest-axe";
expect.extend(toHaveNoViolations);
```

Per-component test:

```tsx
it("has no accessibility violations", async () => {
  const { container } = render(<UserCard {...defaultProps} />);
  expect(await axe(container)).toHaveNoViolations();
});
```

For interactive components, test both states (view mode and edit mode). For forms,
test the error state -- error messages must be linked via `aria-describedby`.

---

## Examples

### Testing a UserList with Data Fetching

```tsx
// src/components/__tests__/UserList.test.tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { server } from "@/test/mocks/server";
import { UserList } from "@/components/UserList";

expect.extend(toHaveNoViolations);

function renderWithProviders(ui: React.ReactElement) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  const user = userEvent.setup();
  return { user, ...render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>) };
}

describe("UserList", () => {
  it("shows a loading indicator while fetching", () => {
    renderWithProviders(<UserList />);
    expect(screen.getByLabelText("Loading users")).toBeInTheDocument();
  });

  it("renders users after data loads", async () => {
    renderWithProviders(<UserList />);
    expect(await screen.findByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
  });

  it("filters users when typing in search", async () => {
    const { user } = renderWithProviders(<UserList />);
    await screen.findByText("Alice");
    await user.type(screen.getByLabelText("Search users"), "Alice");
    await waitFor(() => {
      expect(screen.queryByText("Bob")).not.toBeInTheDocument();
    });
  });

  it("shows error when the API fails", async () => {
    server.use(
      http.get("/api/users", () =>
        HttpResponse.json({ detail: "Service unavailable" }, { status: 500 }),
      ),
    );
    renderWithProviders(<UserList />);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = renderWithProviders(<UserList />);
    await screen.findByText("Alice");
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

---

## Edge Cases

### Testing Portals and Modals

Components rendered via `createPortal` render outside the component tree in the DOM,
but `screen` queries the entire `document.body`, so they are still found normally.

```tsx
it("renders modal content when open", async () => {
  const user = userEvent.setup();
  render(<ModalTrigger />);
  await user.click(screen.getByRole("button", { name: "Open Modal" }));
  expect(screen.getByRole("dialog")).toBeInTheDocument();
});

it("closes the modal on Escape", async () => {
  const user = userEvent.setup();
  render(<ModalTrigger />);
  await user.click(screen.getByRole("button", { name: "Open Modal" }));
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});
```

### Context Provider Wrappers

Create a shared `renderWithProviders` utility wrapping `QueryClientProvider`,
`MemoryRouter`, `AuthProvider`, etc. Use `MemoryRouter` (not `BrowserRouter`) in tests
-- it does not touch browser history and can be initialized to any route.

```tsx
// src/test/renderWithProviders.tsx
export function renderWithProviders(
  ui: React.ReactElement,
  { initialRoute = "/", ...options }: ExtendedRenderOptions = {},
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={[initialRoute]}>{children}</MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );
  }
  return render(ui, { wrapper: Wrapper, ...options });
}
```

### Testing Error Boundaries

Suppress `console.error` for expected errors, then restore after the assertion.

```tsx
it("renders fallback UI when the component throws", () => {
  const spy = vi.spyOn(console, "error").mockImplementation(() => {});
  function Broken() { throw new Error("boom"); }
  render(
    <ErrorBoundary fallback={<p>Something went wrong</p>}><Broken /></ErrorBoundary>,
  );
  expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  spy.mockRestore();
});
```

### Testing React.lazy and Suspense

```tsx
it("shows fallback then the lazy component", async () => {
  render(<Suspense fallback={<p>Loading...</p>}><LazyDashboard /></Suspense>);
  expect(screen.getByText("Loading...")).toBeInTheDocument();
  expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
});
```

### Flaky Async Test Prevention

| Cause                        | Fix                                                          |
|------------------------------|--------------------------------------------------------------|
| Not awaiting async ops       | Use `findBy*` or `waitFor` -- never `setTimeout` in tests.   |
| Shared QueryClient cache     | Create a new `QueryClient` per test with `gcTime: 0`.        |
| MSW handler leaks            | Ensure `afterEach(() => server.resetHandlers())` runs.       |
| Timer-dependent logic        | Use `vi.useFakeTimers()`, restore in `afterEach`.            |
| Shared mutable mock state    | Call `vi.fn()` fresh or `mockClear()` in `beforeEach`.       |

### Snapshot Testing Guidelines

Snapshot tests are **discouraged** for component output -- they break on every UI change
and get approved without review. Use explicit behavioral assertions instead. The only
acceptable use case is testing **serialized data structures** (config objects, transformed
API responses) where exact shape matters:

```tsx
// ACCEPTABLE: data transformation snapshot
expect(transformUserResponse(apiResponse)).toMatchInlineSnapshot(`
  { "fullName": "Alice Smith", "initials": "AS", "memberSince": "January 2024" }
`);

// DISCOURAGED: rendered HTML snapshot
expect(container).toMatchSnapshot(); // Breaks on every UI tweak
```
