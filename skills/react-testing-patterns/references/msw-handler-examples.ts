/**
 * MSW v2 Handler Examples
 *
 * Mock Service Worker (MSW) intercepts network requests at the service-worker
 * or Node level, letting tests run against realistic API mocks without
 * touching the network.
 *
 * Usage:
 *  - Import `handlers` into your MSW `setupServer` call.
 *  - Override individual handlers per-test with `server.use(...)`.
 */

import { http, HttpResponse, delay } from "msw";

// ---------------------------------------------------------------------------
// Shared mock data
// ---------------------------------------------------------------------------
const USERS = [
  { id: "1", name: "Alice", email: "alice@example.com", role: "admin" },
  { id: "2", name: "Bob", email: "bob@example.com", role: "member" },
  { id: "3", name: "Carol", email: "carol@example.com", role: "member" },
];

// ---------------------------------------------------------------------------
// 1. CRUD handlers — the default "happy path" used by most tests
// ---------------------------------------------------------------------------
export const userHandlers = [
  // GET /api/users — list with pagination
  http.get("/api/users", ({ request }) => {
    const url = new URL(request.url);
    const page = Number(url.searchParams.get("page") ?? "1");
    const limit = Number(url.searchParams.get("limit") ?? "10");
    const start = (page - 1) * limit;
    const slice = USERS.slice(start, start + limit);

    return HttpResponse.json({
      data: slice,
      meta: { page, limit, total: USERS.length },
    });
  }),

  // GET /api/users/:id — single resource
  http.get("/api/users/:id", ({ params }) => {
    const user = USERS.find((u) => u.id === params.id);
    if (!user) {
      return HttpResponse.json(
        { error: "User not found" },
        { status: 404 }
      );
    }
    return HttpResponse.json({ data: user });
  }),

  // POST /api/users — create
  http.post("/api/users", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    const created = { id: crypto.randomUUID(), ...body };
    return HttpResponse.json({ data: created }, { status: 201 });
  }),

  // PATCH /api/users/:id — partial update
  http.patch("/api/users/:id", async ({ params, request }) => {
    const user = USERS.find((u) => u.id === params.id);
    if (!user) {
      return HttpResponse.json(
        { error: "User not found" },
        { status: 404 }
      );
    }
    const updates = (await request.json()) as Record<string, unknown>;
    const updated = { ...user, ...updates };
    return HttpResponse.json({ data: updated });
  }),

  // DELETE /api/users/:id
  http.delete("/api/users/:id", ({ params }) => {
    const exists = USERS.some((u) => u.id === params.id);
    if (!exists) {
      return HttpResponse.json(
        { error: "User not found" },
        { status: 404 }
      );
    }
    return new HttpResponse(null, { status: 204 });
  }),
];

// ---------------------------------------------------------------------------
// 2. Auth handlers
// ---------------------------------------------------------------------------
export const authHandlers = [
  // Successful login — returns a JWT-style token
  http.post("/api/auth/login", async ({ request }) => {
    const { email, password } = (await request.json()) as {
      email: string;
      password: string;
    };

    if (email === "alice@example.com" && password === "correct-password") {
      return HttpResponse.json({
        token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.mock-token",
        user: USERS[0],
      });
    }

    // Login failure — 401 Unauthorized
    return HttpResponse.json(
      { error: "Invalid email or password" },
      { status: 401 }
    );
  }),

  // Token refresh
  http.post("/api/auth/refresh", () => {
    return HttpResponse.json({
      token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refreshed-token",
    });
  }),
];

// ---------------------------------------------------------------------------
// 3. Error / edge-case handlers (use as per-test overrides)
// ---------------------------------------------------------------------------

/** Simulates a 500 Internal Server Error for the users list endpoint. */
export const serverErrorHandler = http.get("/api/users", () => {
  return HttpResponse.json(
    { error: "Internal server error" },
    { status: 500 }
  );
});

/** Simulates a 422 validation error on user creation. */
export const validationErrorHandler = http.post("/api/users", () => {
  return HttpResponse.json(
    {
      error: "Validation failed",
      details: [
        { field: "email", message: "Email is required" },
        { field: "name", message: "Name must be at least 2 characters" },
      ],
    },
    { status: 422 }
  );
});

/** Simulates a slow response (useful for testing loading states). */
export const slowResponseHandler = http.get("/api/users", async () => {
  await delay(3000);
  return HttpResponse.json({ data: USERS, meta: { page: 1, limit: 10, total: 3 } });
});

/** Simulates a network error (request never completes). */
export const networkErrorHandler = http.get("/api/users", () => {
  return HttpResponse.error();
});

// ---------------------------------------------------------------------------
// 4. Aggregate default handlers — import this in setupServer
// ---------------------------------------------------------------------------
export const handlers = [...userHandlers, ...authHandlers];

// ---------------------------------------------------------------------------
// 5. Per-test override example
// ---------------------------------------------------------------------------
/*
  import { server } from "@/mocks/server";
  import { serverErrorHandler } from "@/mocks/handlers";

  it("shows error banner when the API is down", async () => {
    // Override only for this test; afterEach in setupTests calls
    // server.resetHandlers() to restore defaults.
    server.use(serverErrorHandler);

    renderWithProviders(<UserList />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/error/i);
  });
*/
