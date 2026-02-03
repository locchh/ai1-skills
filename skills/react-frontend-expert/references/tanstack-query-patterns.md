# TanStack Query v5 Patterns

## 1. Query Key Factory Pattern

Centralize query keys in a factory object. This prevents key typos, makes
invalidation predictable, and provides autocompletion.

```tsx
// src/queries/userKeys.ts

export const userKeys = {
  all:     ["users"] as const,
  lists:   () => [...userKeys.all, "list"] as const,
  list:    (filters: { page: number; search?: string }) =>
             [...userKeys.lists(), filters] as const,
  details: () => [...userKeys.all, "detail"] as const,
  detail:  (id: string) => [...userKeys.details(), id] as const,
};

// Usage in hooks:
// queryKey: userKeys.list({ page: 1, search: "alice" })
// queryKey: userKeys.detail("user-123")

// Invalidation (all user lists, regardless of filters):
// queryClient.invalidateQueries({ queryKey: userKeys.lists() })

// Invalidation (everything user-related):
// queryClient.invalidateQueries({ queryKey: userKeys.all })
```

## 2. Prefetching Patterns

Prefetch data before the user navigates to avoid loading spinners on the next page.

```tsx
// Prefetch on hover (link or button)
function UserListItem({ userId, name }: { userId: string; name: string }) {
  const queryClient = useQueryClient();

  const prefetchUser = () => {
    queryClient.prefetchQuery({
      queryKey: userKeys.detail(userId),
      queryFn: () => fetchUser(userId),
      staleTime: 60_000, // Only prefetch if data is older than 1 minute
    });
  };

  return (
    <Link
      to={`/users/${userId}`}
      onMouseEnter={prefetchUser}
      onFocus={prefetchUser}
    >
      {name}
    </Link>
  );
}

// Prefetch in a route loader (React Router 6+)
export function usersPageLoader(queryClient: QueryClient) {
  return async () => {
    await queryClient.ensureQueryData({
      queryKey: userKeys.list({ page: 1 }),
      queryFn: () => fetchUsers({ page: 1 }),
    });
    return null;
  };
}
```

## 3. Infinite Query Pattern

Implement cursor-based or offset-based pagination with "Load More" or infinite scroll.

```tsx
import { useInfiniteQuery } from "@tanstack/react-query";

interface PageResponse<T> {
  items: T[];
  nextCursor: string | null;
}

export function useInfiniteUsers(search?: string) {
  return useInfiniteQuery({
    queryKey: userKeys.list({ page: -1, search }), // -1 signals infinite mode
    queryFn: async ({ pageParam }): Promise<PageResponse<User>> => {
      const params = new URLSearchParams();
      if (pageParam) params.set("cursor", pageParam);
      if (search) params.set("search", search);
      params.set("limit", "20");

      const res = await fetch(`/api/users?${params}`);
      if (!res.ok) throw new Error("Failed to fetch users");
      return res.json();
    },
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.nextCursor,
  });
}

// In the component:
// const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteUsers();
// const allUsers = data?.pages.flatMap((page) => page.items) ?? [];
```

## 4. Dependent Queries

When one query depends on the result of another, use the `enabled` option to prevent
the dependent query from running until its prerequisite resolves.

```tsx
export function useUserProjects(userId?: string) {
  // First query: fetch user to get their organization ID
  const userQuery = useQuery({
    queryKey: userKeys.detail(userId!),
    queryFn: () => fetchUser(userId!),
    enabled: !!userId,
  });

  // Second query: depends on the user's org ID
  const projectsQuery = useQuery({
    queryKey: ["projects", { orgId: userQuery.data?.orgId }],
    queryFn: () => fetchProjects(userQuery.data!.orgId),
    enabled: !!userQuery.data?.orgId,
  });

  return {
    user: userQuery.data,
    projects: projectsQuery.data,
    isLoading: userQuery.isLoading || projectsQuery.isLoading,
    isError: userQuery.isError || projectsQuery.isError,
  };
}
```

## 5. Query Invalidation Strategies

Choose the right invalidation strategy based on the mutation's effect.

```tsx
import { useMutation, useQueryClient } from "@tanstack/react-query";

export function useDeleteUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userId: string) => deleteUser(userId),
    onSuccess: (_data, userId) => {
      // Strategy 1: Invalidate — refetch from server (most common)
      queryClient.invalidateQueries({ queryKey: userKeys.lists() });

      // Strategy 2: Remove — delete from cache immediately (detail page)
      queryClient.removeQueries({ queryKey: userKeys.detail(userId) });

      // Strategy 3: Manual update — modify cache without refetch
      // queryClient.setQueryData(userKeys.list({ page: 1 }), (old) => ({
      //   ...old,
      //   users: old.users.filter((u) => u.id !== userId),
      // }));
    },
  });
}
```

**When to use each:**

| Strategy           | Use When                                          |
|--------------------|---------------------------------------------------|
| `invalidateQueries` | Default. Server is source of truth.              |
| `removeQueries`    | The entity no longer exists (delete).             |
| `setQueryData`     | You have the complete new data (optimistic update). |
| `cancelQueries`    | Before an optimistic update, cancel in-flight fetches. |

## 6. Optimistic Update Complete Example

Show the update immediately in the UI, roll back on error, and refetch to reconcile.

```tsx
import { useMutation, useQueryClient } from "@tanstack/react-query";

interface UpdateUserInput {
  id: string;
  name: string;
  email: string;
}

export function useUpdateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: UpdateUserInput) => updateUser(input),

    onMutate: async (input) => {
      // 1. Cancel in-flight fetches so they do not overwrite our optimistic update
      await queryClient.cancelQueries({ queryKey: userKeys.detail(input.id) });

      // 2. Snapshot current cache for rollback
      const previousUser = queryClient.getQueryData<User>(
        userKeys.detail(input.id),
      );

      // 3. Optimistically update the cache
      queryClient.setQueryData<User>(userKeys.detail(input.id), (old) =>
        old ? { ...old, name: input.name, email: input.email } : old,
      );

      // 4. Return snapshot for rollback in onError
      return { previousUser };
    },

    onError: (_error, input, context) => {
      // 5. Roll back to the previous value
      if (context?.previousUser) {
        queryClient.setQueryData(
          userKeys.detail(input.id),
          context.previousUser,
        );
      }
    },

    onSettled: (_data, _error, input) => {
      // 6. Always refetch to reconcile with server state
      queryClient.invalidateQueries({ queryKey: userKeys.detail(input.id) });
      queryClient.invalidateQueries({ queryKey: userKeys.lists() });
    },
  });
}
```

**Optimistic update checklist:**

1. `cancelQueries` to prevent in-flight fetches from overwriting.
2. Snapshot the current cache value.
3. Apply the optimistic update with `setQueryData`.
4. Return the snapshot from `onMutate` so `onError` can access it.
5. Roll back in `onError` using the snapshot.
6. Invalidate in `onSettled` (runs on both success and error) to reconcile.
