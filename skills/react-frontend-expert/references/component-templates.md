# React Component Templates

## 1. Page Component (Data Fetching with TanStack Query)

A full page component that fetches data, handles loading/error states, and
renders within a layout.

```tsx
import { useQuery } from "@tanstack/react-query";
import { useParams, useNavigate } from "react-router-dom";

// --- Types ---

interface User {
  id: string;
  name: string;
  email: string;
  role: "admin" | "member";
  createdAt: string;
}

interface UserPageProps {
  /** Optional: override user ID for embedding this page in other contexts */
  userId?: string;
}

// --- API Layer ---

async function fetchUser(userId: string): Promise<User> {
  const response = await fetch(`/api/users/${userId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch user: ${response.status}`);
  }
  return response.json();
}

// --- Component ---

export function UserPage({ userId: propUserId }: UserPageProps) {
  const { id: paramId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const userId = propUserId ?? paramId;

  const {
    data: user,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["users", userId],
    queryFn: () => fetchUser(userId!),
    enabled: !!userId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  if (!userId) {
    return <p>No user ID provided.</p>;
  }

  if (isLoading) {
    return (
      <div role="status" aria-label="Loading user">
        <span className="spinner" />
        <p>Loading user...</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div role="alert">
        <h2>Something went wrong</h2>
        <p>{error instanceof Error ? error.message : "Unknown error"}</p>
        <button onClick={() => refetch()}>Retry</button>
        <button onClick={() => navigate(-1)}>Go Back</button>
      </div>
    );
  }

  if (!user) {
    return <p>User not found.</p>;
  }

  return (
    <main className="page-container">
      <header>
        <h1>{user.name}</h1>
        <span className="badge">{user.role}</span>
      </header>
      <section>
        <dl>
          <dt>Email</dt>
          <dd>{user.email}</dd>
          <dt>Member since</dt>
          <dd>{new Date(user.createdAt).toLocaleDateString()}</dd>
        </dl>
      </section>
    </main>
  );
}
```

### Usage Notes
- `enabled: !!userId` prevents the query from firing when userId is undefined.
- `staleTime` avoids refetching on every mount when navigating back and forth.
- Always provide `role="status"` or `role="alert"` for screen readers on
  loading and error states.
- Extract the API function to a separate module in real projects.

---

## 2. Form Component (Controlled Inputs, Zod Validation)

A reusable form with controlled inputs, schema validation, and error display.

```tsx
import { useState, type FormEvent } from "react";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";

// --- Validation Schema ---

const createUserSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  email: z.string().email("Please enter a valid email address"),
  role: z.enum(["admin", "member"], {
    errorMap: () => ({ message: "Please select a role" }),
  }),
});

type CreateUserInput = z.infer<typeof createUserSchema>;

// --- Props ---

interface CreateUserFormProps {
  onSuccess?: (user: User) => void;
  onCancel?: () => void;
}

// --- Component ---

export function CreateUserForm({ onSuccess, onCancel }: CreateUserFormProps) {
  const queryClient = useQueryClient();

  const [formData, setFormData] = useState<CreateUserInput>({
    name: "",
    email: "",
    role: "member",
  });
  const [fieldErrors, setFieldErrors] = useState<
    Partial<Record<keyof CreateUserInput, string>>
  >({});

  const mutation = useMutation({
    mutationFn: async (data: CreateUserInput) => {
      const res = await fetch("/api/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!res.ok) throw new Error("Failed to create user");
      return res.json() as Promise<User>;
    },
    onSuccess: (newUser) => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      onSuccess?.(newUser);
    },
  });

  function handleChange(
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear field error on change
    setFieldErrors((prev) => ({ ...prev, [name]: undefined }));
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFieldErrors({});

    const result = createUserSchema.safeParse(formData);
    if (!result.success) {
      const errors: Partial<Record<keyof CreateUserInput, string>> = {};
      for (const issue of result.error.issues) {
        const field = issue.path[0] as keyof CreateUserInput;
        errors[field] = issue.message;
      }
      setFieldErrors(errors);
      return;
    }

    mutation.mutate(result.data);
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div className="field">
        <label htmlFor="name">Name</label>
        <input
          id="name"
          name="name"
          value={formData.name}
          onChange={handleChange}
          aria-invalid={!!fieldErrors.name}
          aria-describedby={fieldErrors.name ? "name-error" : undefined}
        />
        {fieldErrors.name && (
          <p id="name-error" className="error" role="alert">
            {fieldErrors.name}
          </p>
        )}
      </div>

      <div className="field">
        <label htmlFor="email">Email</label>
        <input
          id="email"
          name="email"
          type="email"
          value={formData.email}
          onChange={handleChange}
          aria-invalid={!!fieldErrors.email}
          aria-describedby={fieldErrors.email ? "email-error" : undefined}
        />
        {fieldErrors.email && (
          <p id="email-error" className="error" role="alert">
            {fieldErrors.email}
          </p>
        )}
      </div>

      <div className="field">
        <label htmlFor="role">Role</label>
        <select
          id="role"
          name="role"
          value={formData.role}
          onChange={handleChange}
        >
          <option value="member">Member</option>
          <option value="admin">Admin</option>
        </select>
        {fieldErrors.role && (
          <p className="error" role="alert">{fieldErrors.role}</p>
        )}
      </div>

      {mutation.isError && (
        <p className="error" role="alert">
          {mutation.error instanceof Error
            ? mutation.error.message
            : "An error occurred"}
        </p>
      )}

      <div className="actions">
        <button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Creating..." : "Create User"}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
```

### Usage Notes
- `noValidate` disables browser-native validation so Zod handles everything.
- `aria-invalid` and `aria-describedby` link inputs to their error messages for
  screen readers.
- Field errors are cleared individually on change to avoid stale messages.
- The mutation disables the submit button while pending to prevent double submits.

---

## 3. List with Cursor-Based Pagination

A list component with "Load More" button, empty state, and cursor-based paging.

```tsx
import { useInfiniteQuery } from "@tanstack/react-query";

// --- Types ---

interface Article {
  id: string;
  title: string;
  summary: string;
  publishedAt: string;
}

interface ArticlesResponse {
  items: Article[];
  nextCursor: string | null;
}

interface ArticleListProps {
  categoryId?: string;
}

// --- API ---

async function fetchArticles(
  cursor: string | null,
  categoryId?: string,
): Promise<ArticlesResponse> {
  const params = new URLSearchParams();
  if (cursor) params.set("cursor", cursor);
  if (categoryId) params.set("category", categoryId);
  params.set("limit", "20");

  const res = await fetch(`/api/articles?${params}`);
  if (!res.ok) throw new Error("Failed to fetch articles");
  return res.json();
}

// --- Component ---

export function ArticleList({ categoryId }: ArticleListProps) {
  const {
    data,
    isLoading,
    isError,
    error,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ["articles", "list", { categoryId }],
    queryFn: ({ pageParam }) => fetchArticles(pageParam, categoryId),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.nextCursor,
  });

  if (isLoading) {
    return <p role="status">Loading articles...</p>;
  }

  if (isError) {
    return (
      <div role="alert">
        <p>Failed to load articles.</p>
        <p>{error instanceof Error ? error.message : "Unknown error"}</p>
      </div>
    );
  }

  const articles = data?.pages.flatMap((page) => page.items) ?? [];

  if (articles.length === 0) {
    return (
      <div className="empty-state">
        <p>No articles found.</p>
        <p>Check back later or try a different category.</p>
      </div>
    );
  }

  return (
    <section>
      <ul className="article-list" role="list">
        {articles.map((article) => (
          <li key={article.id} className="article-card">
            <h3>{article.title}</h3>
            <p>{article.summary}</p>
            <time dateTime={article.publishedAt}>
              {new Date(article.publishedAt).toLocaleDateString()}
            </time>
          </li>
        ))}
      </ul>

      {hasNextPage && (
        <button
          onClick={() => fetchNextPage()}
          disabled={isFetchingNextPage}
          className="load-more"
        >
          {isFetchingNextPage ? "Loading more..." : "Load More"}
        </button>
      )}
    </section>
  );
}
```

### Usage Notes
- `initialPageParam: null` represents the first page (no cursor).
- `getNextPageParam` returns `null` when there are no more pages, which sets
  `hasNextPage` to `false` automatically.
- `data.pages.flatMap(...)` flattens all pages into one array for rendering.
- The `key` prop uses the article ID, not the array index.

---

## 4. Modal Dialog (Portal, Focus Trap, Keyboard Dismiss)

An accessible modal component using a portal, focus trapping, and keyboard
navigation.

```tsx
import {
  useEffect,
  useRef,
  useCallback,
  type ReactNode,
  type KeyboardEvent,
} from "react";
import { createPortal } from "react-dom";

// --- Props ---

interface ModalProps {
  /** Whether the modal is currently open */
  isOpen: boolean;
  /** Called when the user requests to close (Escape, backdrop click, close button) */
  onClose: () => void;
  /** Modal title displayed in the header */
  title: string;
  /** Modal body content */
  children: ReactNode;
  /** Optional footer (action buttons) */
  footer?: ReactNode;
}

// --- Helpers ---

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

// --- Component ---

export function Modal({ isOpen, onClose, title, children, footer }: ModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  // Save and restore focus
  useEffect(() => {
    if (isOpen) {
      previousFocusRef.current = document.activeElement as HTMLElement;

      // Focus the first focusable element inside the modal
      requestAnimationFrame(() => {
        const firstFocusable = contentRef.current?.querySelector<HTMLElement>(
          FOCUSABLE_SELECTOR,
        );
        firstFocusable?.focus();
      });
    }

    return () => {
      previousFocusRef.current?.focus();
    };
  }, [isOpen]);

  // Lock body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  // Focus trap
  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLDivElement>) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }

      if (e.key !== "Tab") return;

      const focusableElements =
        contentRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
      if (!focusableElements || focusableElements.length === 0) return;

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (e.shiftKey) {
        // Shift+Tab: wrap to last element
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement.focus();
        }
      } else {
        // Tab: wrap to first element
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();
        }
      }
    },
    [onClose],
  );

  // Click on backdrop closes
  const handleBackdropClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === overlayRef.current) {
        onClose();
      }
    },
    [onClose],
  );

  if (!isOpen) return null;

  return createPortal(
    <div
      ref={overlayRef}
      className="modal-overlay"
      onClick={handleBackdropClick}
      onKeyDown={handleKeyDown}
      role="presentation"
    >
      <div
        ref={contentRef}
        className="modal-content"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        <header className="modal-header">
          <h2 id="modal-title">{title}</h2>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="modal-close"
          >
            &times;
          </button>
        </header>

        <div className="modal-body">{children}</div>

        {footer && <footer className="modal-footer">{footer}</footer>}
      </div>
    </div>,
    document.body,
  );
}
```

### Usage

```tsx
function App() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <button onClick={() => setIsOpen(true)}>Open Modal</button>
      <Modal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title="Confirm Action"
        footer={
          <div>
            <button onClick={() => setIsOpen(false)}>Cancel</button>
            <button onClick={handleConfirm}>Confirm</button>
          </div>
        }
      >
        <p>Are you sure you want to proceed?</p>
      </Modal>
    </>
  );
}
```

### Usage Notes
- `createPortal` renders the modal at the document body level, escaping any
  parent `overflow: hidden` or `z-index` stacking contexts.
- Focus is trapped: Tab and Shift+Tab cycle within the modal.
- Escape key dismisses the modal.
- Clicking the backdrop (outside the content area) dismisses the modal.
- Focus is returned to the previously focused element on close.
- `aria-modal="true"` tells assistive technology that content behind the modal
  is inert.
- Body scroll is locked while the modal is open to prevent background scrolling.
