/**
 * Custom Hook Test Template
 *
 * Uses @testing-library/react's renderHook to test hooks in isolation
 * without mounting a dummy component.
 *
 * Key principles:
 *  - Wrap state mutations in act() so React processes updates before assertions
 *  - Provide the same providers the hook expects at runtime
 *  - Test the public API of the hook (return values), not internals
 */

import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Hook under test
import { useCounter } from "@/hooks/useCounter";
import { useUserSearch } from "@/hooks/useUserSearch";

// MSW (for hooks that make network requests)
import { server } from "@/mocks/server";
import { http, HttpResponse } from "msw";

// ---------------------------------------------------------------------------
// 1. Test wrapper — mirrors the provider tree of the real app
// ---------------------------------------------------------------------------
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

// ---------------------------------------------------------------------------
// 2. Synchronous hook tests — useCounter(initialValue)
// ---------------------------------------------------------------------------
describe("useCounter", () => {
  it("returns the initial count", () => {
    // Arrange & Act: render the hook with an initial value
    const { result } = renderHook(() => useCounter(5));

    // Assert: the initial state matches what we passed in
    expect(result.current.count).toBe(5);
  });

  it("increments the count", () => {
    const { result } = renderHook(() => useCounter(0));

    // Act: wrap state updates in act() so React flushes the update
    act(() => {
      result.current.increment();
    });

    // Assert: count increased by one
    expect(result.current.count).toBe(1);
  });

  it("decrements the count but never goes below zero", () => {
    const { result } = renderHook(() => useCounter(0));

    act(() => {
      result.current.decrement();
    });

    // Assert: count stays at the floor value
    expect(result.current.count).toBe(0);
  });

  it("resets to the initial value", () => {
    const { result } = renderHook(() => useCounter(10));

    act(() => {
      result.current.increment();
      result.current.increment();
    });
    expect(result.current.count).toBe(12);

    act(() => {
      result.current.reset();
    });
    expect(result.current.count).toBe(10);
  });
});

// ---------------------------------------------------------------------------
// 3. Async hook tests — useUserSearch(query) (uses React Query internally)
// ---------------------------------------------------------------------------
describe("useUserSearch", () => {
  it("returns search results after the query resolves", async () => {
    const { result } = renderHook(() => useUserSearch("alice"), {
      wrapper: createWrapper(),
    });

    // Assert: initially loading
    expect(result.current.isLoading).toBe(true);

    // Assert: eventually returns data (MSW default handler serves results)
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    expect(result.current.data).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ name: "Alice" }),
      ])
    );
  });

  it("returns an error when the API fails", async () => {
    // Arrange: override the search endpoint to return 500
    server.use(
      http.get("/api/users/search", () => {
        return HttpResponse.json(
          { error: "Service unavailable" },
          { status: 500 }
        );
      })
    );

    const { result } = renderHook(() => useUserSearch("alice"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
    expect(result.current.data).toBeUndefined();
  });

  it("does not fetch when the query string is empty", () => {
    const { result } = renderHook(() => useUserSearch(""), {
      wrapper: createWrapper(),
    });

    // The hook should disable the query when input is empty
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isFetching).toBe(false);
  });
});
