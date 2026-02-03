/**
 * React Component Test Template
 *
 * This template demonstrates a production-quality component test structure
 * using React Testing Library, user-event, MSW, and jest-axe.
 *
 * Key principles:
 *  - Test behavior, not implementation details
 *  - Query elements the way a user would (by role, label, text)
 *  - Prefer userEvent over fireEvent for realistic interactions
 *  - Always assert accessibility with jest-axe
 */

// ---------------------------------------------------------------------------
// 1. Imports
// ---------------------------------------------------------------------------
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";

// Component under test
import { UserProfile } from "@/components/UserProfile";

// MSW server (configured in setupTests.ts)
import { server } from "@/mocks/server";
import { http, HttpResponse } from "msw";

// Extend expect with accessibility matchers
expect.extend(toHaveNoViolations);

// ---------------------------------------------------------------------------
// 2. Test wrapper — provides context that the component depends on
// ---------------------------------------------------------------------------
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}

interface WrapperProps {
  children: React.ReactNode;
  initialRoute?: string;
}

function TestWrapper({ children, initialRoute = "/" }: WrapperProps) {
  const queryClient = createTestQueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialRoute]}>
        <Routes>
          <Route path="*" element={children} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

// Helper: render with all providers already applied
function renderWithProviders(
  ui: React.ReactElement,
  { initialRoute = "/" } = {}
) {
  const user = userEvent.setup();
  return {
    user,
    ...render(ui, {
      wrapper: ({ children }) => (
        <TestWrapper initialRoute={initialRoute}>{children}</TestWrapper>
      ),
    }),
  };
}

// ---------------------------------------------------------------------------
// 3. Default props — keeps individual tests concise
// ---------------------------------------------------------------------------
const defaultProps: React.ComponentProps<typeof UserProfile> = {
  userId: "user-1",
  onSave: vi.fn(),
};

// ---------------------------------------------------------------------------
// 4. Test suite
// ---------------------------------------------------------------------------
describe("UserProfile", () => {
  // --- Synchronous render test -------------------------------------------
  it("renders the user name and email after data loads", async () => {
    // Arrange: render the component (MSW default handler returns mock user)
    renderWithProviders(<UserProfile {...defaultProps} />);

    // Assert: wait for async data to appear
    expect(await screen.findByText("Jane Doe")).toBeInTheDocument();
    expect(screen.getByText("jane@example.com")).toBeInTheDocument();
  });

  // --- User interaction test ---------------------------------------------
  it("saves updated name when the form is submitted", async () => {
    const onSave = vi.fn();
    const { user } = renderWithProviders(
      <UserProfile {...defaultProps} onSave={onSave} />
    );

    // Act: wait for form to load, then interact
    const nameInput = await screen.findByLabelText(/full name/i);
    await user.clear(nameInput);
    await user.type(nameInput, "Updated Name");
    await user.click(screen.getByRole("button", { name: /save/i }));

    // Assert: callback was invoked with the new value
    await waitFor(() => {
      expect(onSave).toHaveBeenCalledWith(
        expect.objectContaining({ name: "Updated Name" })
      );
    });
  });

  // --- Error state test --------------------------------------------------
  it("shows an error message when the API returns 500", async () => {
    // Arrange: override the default MSW handler for this test only
    server.use(
      http.get("/api/users/:id", () => {
        return HttpResponse.json(
          { error: "Internal server error" },
          { status: 500 }
        );
      })
    );

    renderWithProviders(<UserProfile {...defaultProps} />);

    // Assert: error UI is displayed
    expect(
      await screen.findByRole("alert")
    ).toHaveTextContent(/something went wrong/i);
  });

  // --- Accessibility test ------------------------------------------------
  it("has no accessibility violations", async () => {
    const { container } = renderWithProviders(
      <UserProfile {...defaultProps} />
    );

    // Wait for the component to finish loading before running axe
    await screen.findByText("Jane Doe");

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  // --- Scoped query test -------------------------------------------------
  it("renders action buttons inside the toolbar region", async () => {
    renderWithProviders(<UserProfile {...defaultProps} />);

    const toolbar = await screen.findByRole("toolbar");
    const saveButton = within(toolbar).getByRole("button", { name: /save/i });

    expect(saveButton).toBeEnabled();
  });
});
