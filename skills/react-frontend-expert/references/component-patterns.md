# React Component Patterns

## 1. Container / Presentation Pattern

Separate data fetching (container) from rendering (presentation). The presentation
component is pure and reusable; the container wires it to data sources.

```tsx
// Presentation: receives data via props, no side effects
interface UserProfileViewProps {
  user: User;
  onEdit: (userId: string) => void;
}

export function UserProfileView({ user, onEdit }: UserProfileViewProps) {
  return (
    <article aria-label={`Profile for ${user.name}`}>
      <h2>{user.name}</h2>
      <p>{user.email}</p>
      <button onClick={() => onEdit(user.id)}>Edit</button>
    </article>
  );
}

// Container: handles data fetching and state
export function UserProfileContainer({ userId }: { userId: string }) {
  const { data: user, isLoading, isError } = useQuery({
    queryKey: ["users", userId],
    queryFn: () => fetchUser(userId),
  });

  if (isLoading) return <Spinner aria-label="Loading profile" />;
  if (isError || !user) return <ErrorMessage message="Failed to load user" />;

  return <UserProfileView user={user} onEdit={handleEdit} />;
}
```

## 2. Compound Component Pattern

A set of components that work together, sharing implicit state through context.
The parent manages state; children consume it. This keeps the API flexible while
enforcing correct composition.

```tsx
import { createContext, useContext, useState, type ReactNode } from "react";

// Shared context
interface AccordionContextValue {
  openIndex: number | null;
  toggle: (index: number) => void;
}

const AccordionContext = createContext<AccordionContextValue | null>(null);

function useAccordion() {
  const ctx = useContext(AccordionContext);
  if (!ctx) throw new Error("Accordion components must be used within <Accordion>");
  return ctx;
}

// Parent
export function Accordion({ children }: { children: ReactNode }) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const toggle = (index: number) =>
    setOpenIndex((prev) => (prev === index ? null : index));

  return (
    <AccordionContext.Provider value={{ openIndex, toggle }}>
      <div role="region">{children}</div>
    </AccordionContext.Provider>
  );
}

// Child: header (trigger)
export function AccordionItem({ index, title, children }: {
  index: number;
  title: string;
  children: ReactNode;
}) {
  const { openIndex, toggle } = useAccordion();
  const isOpen = openIndex === index;

  return (
    <div>
      <button
        onClick={() => toggle(index)}
        aria-expanded={isOpen}
        aria-controls={`panel-${index}`}
      >
        {title}
      </button>
      {isOpen && (
        <div id={`panel-${index}`} role="region">
          {children}
        </div>
      )}
    </div>
  );
}

// Usage:
// <Accordion>
//   <AccordionItem index={0} title="Section 1">Content 1</AccordionItem>
//   <AccordionItem index={1} title="Section 2">Content 2</AccordionItem>
// </Accordion>
```

## 3. Render Props (Modern Version)

Pass a function as a child or prop to delegate rendering. Useful when a component
manages complex state or behavior that multiple consumers render differently.

```tsx
interface MouseTrackerProps {
  children: (position: { x: number; y: number }) => ReactNode;
}

export function MouseTracker({ children }: MouseTrackerProps) {
  const [position, setPosition] = useState({ x: 0, y: 0 });

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    setPosition({ x: e.clientX, y: e.clientY });
  }, []);

  return <div onMouseMove={handleMouseMove}>{children(position)}</div>;
}

// Usage:
// <MouseTracker>
//   {({ x, y }) => <p>Cursor at ({x}, {y})</p>}
// </MouseTracker>
```

**When to prefer a custom hook instead:** If the render prop only provides data (no DOM
wrapping needed), extract a `useMousePosition` hook instead. Render props are best when
the provider needs to wrap DOM (e.g., attaching event listeners to a container element).

## 4. HOC Pattern (When Still Needed)

Higher-Order Components wrap a component to inject props. In modern React, prefer hooks
for most cases. HOCs are still useful for cross-cutting concerns that need to wrap the
component at the module level (e.g., route-level auth guards, feature flags).

```tsx
import { type ComponentType } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";

export function withAuth<P extends object>(WrappedComponent: ComponentType<P>) {
  function AuthGuard(props: P) {
    const { isAuthenticated, isLoading } = useAuth();

    if (isLoading) return <Spinner aria-label="Checking authentication" />;
    if (!isAuthenticated) return <Navigate to="/login" replace />;

    return <WrappedComponent {...props} />;
  }

  AuthGuard.displayName = `withAuth(${WrappedComponent.displayName || WrappedComponent.name})`;
  return AuthGuard;
}

// Usage:
// const ProtectedDashboard = withAuth(Dashboard);
```

## 5. Error Boundary Component

Class-based error boundary (the only remaining valid use of class components in React).
Catches JavaScript errors in child components and displays a fallback UI.

```tsx
import { Component, type ErrorInfo, type ReactNode } from "react";

interface ErrorBoundaryProps {
  fallback: ReactNode | ((error: Error) => ReactNode);
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  children: ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.props.onError?.(error, errorInfo);
  }

  render() {
    if (this.state.error) {
      const { fallback } = this.props;
      return typeof fallback === "function" ? fallback(this.state.error) : fallback;
    }
    return this.props.children;
  }
}

// Usage:
// <ErrorBoundary
//   fallback={(error) => <p>Error: {error.message}</p>}
//   onError={(error) => logToService(error)}
// >
//   <Dashboard />
// </ErrorBoundary>
```

## 6. Suspense Wrapper Patterns

Wrap async components and data loading with Suspense boundaries. Place boundaries
at meaningful UI boundaries so partial content can render while other parts load.

```tsx
import { Suspense, lazy } from "react";

const LazyDashboard = lazy(() => import("@/pages/Dashboard"));
const LazySettings = lazy(() => import("@/pages/Settings"));

// Pattern A: Shared fallback for a route group
export function AppRoutes() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <Routes>
        <Route path="/dashboard" element={<LazyDashboard />} />
        <Route path="/settings" element={<LazySettings />} />
      </Routes>
    </Suspense>
  );
}

// Pattern B: Granular Suspense boundaries for independent sections
export function DashboardPage() {
  return (
    <main>
      <h1>Dashboard</h1>
      <Suspense fallback={<CardSkeleton count={3} />}>
        <StatsPanel />
      </Suspense>
      <Suspense fallback={<TableSkeleton rows={5} />}>
        <RecentActivityTable />
      </Suspense>
    </main>
  );
}
```

**Guidelines:**

- Place `Suspense` at route boundaries for code-split pages.
- Place `Suspense` around independent data-loading sections so one slow section
  does not block the entire page.
- Use skeleton components as fallbacks rather than generic spinners for better UX.
- Combine with `ErrorBoundary` to handle both loading and error states.
