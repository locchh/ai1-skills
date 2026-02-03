---
name: e2e-testing
description: >-
  End-to-end testing patterns with Playwright for full-stack Python/React applications.
  Use when writing E2E tests for complete user workflows (login, CRUD, navigation),
  critical path regression tests, or cross-browser validation. Covers test structure,
  page object model, selector strategy (data-testid > role > label), wait strategies,
  auth state reuse, test data management, and CI integration. Does NOT cover unit tests
  or component tests (use pytest-patterns or react-testing-patterns).
license: MIT
compatibility: 'Playwright 1.40+, Node.js 20+'
metadata:
  author: platform-team
  version: '1.0.0'
  sdlc-phase: testing
allowed-tools: Read Edit Write Bash(npx:*) Bash(npm:*)
context: fork
---

# E2E Testing

End-to-end testing patterns with Playwright for full-stack applications. This skill
covers how to write E2E tests that validate complete user workflows through the browser,
from login to data creation to verification.

## When to Use

Activate this skill when:

- Writing tests for complete user workflows (registration, login, CRUD operations)
- Creating critical path regression tests that must not break
- Validating cross-browser compatibility (Chromium, Firefox, WebKit)
- Testing user-facing flows that span multiple pages or components
- Verifying real API integrations through the browser
- Writing smoke tests for deployment validation

Do NOT use this skill when:

- Writing unit tests for individual functions or classes (use `pytest-patterns`)
- Writing component tests for React components (use `react-testing-patterns`)
- Testing API endpoints directly without a browser (use `pytest-patterns` integration)
- Performing security review (use `code-review-security`)
- The feature has no user-facing UI component

E2E tests are the most expensive tests to write and maintain. Use them for critical
paths that, if broken, would directly impact users. For everything else, prefer unit
and integration tests.

## Instructions

### Test Structure

Every E2E test follows the same structure: arrange the preconditions, act through the
browser, and assert the visible outcome.

```typescript
import { test, expect } from '@playwright/test';

test.describe('User Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Arrange: navigate to the page under test
    await page.goto('/dashboard');
  });

  test('displays welcome message with user name', async ({ page }) => {
    // Assert: verify visible outcome
    await expect(page.getByTestId('welcome-message')).toContainText('Welcome, Alice');
  });

  test('shows recent projects in sidebar', async ({ page }) => {
    // Assert: verify list content
    const projects = page.getByTestId('project-list-item');
    await expect(projects).toHaveCount(3);
  });
});
```

Key principles:

- **One assertion focus per test.** Each test verifies one user-visible behavior. If a
  test name contains "and," consider splitting it.
- **Use `test.describe` for grouping.** Group tests by page or feature. Shared setup
  goes in `beforeEach`.
- **Tests must be independent.** Each test can run alone, in any order, in parallel.
  Never depend on another test's side effects.

### Page Object Model

Encapsulate page interactions in page object classes. This isolates selector logic from
test logic, making tests readable and selectors maintainable.

```typescript
// pages/LoginPage.ts
import { Page, Locator } from '@playwright/test';

export class LoginPage {
  readonly page: Page;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly submitButton: Locator;
  readonly errorMessage: Locator;

  constructor(page: Page) {
    this.page = page;
    this.emailInput = page.getByTestId('login-email');
    this.passwordInput = page.getByTestId('login-password');
    this.submitButton = page.getByRole('button', { name: 'Sign in' });
    this.errorMessage = page.getByTestId('login-error');
  }

  async goto() {
    await this.page.goto('/login');
    await this.page.waitForLoadState('networkidle');
    return this;
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
    return this;
  }

  async expectError(message: string) {
    await expect(this.errorMessage).toContainText(message);
    return this;
  }
}
```

```typescript
// pages/DashboardPage.ts
import { Page, Locator } from '@playwright/test';

export class DashboardPage {
  readonly page: Page;
  readonly welcomeMessage: Locator;
  readonly createButton: Locator;
  readonly projectList: Locator;

  constructor(page: Page) {
    this.page = page;
    this.welcomeMessage = page.getByTestId('welcome-message');
    this.createButton = page.getByRole('button', { name: 'Create Project' });
    this.projectList = page.getByTestId('project-list');
  }

  async expectWelcome(name: string) {
    await expect(this.welcomeMessage).toContainText(`Welcome, ${name}`);
    return this;
  }

  async createProject(name: string) {
    await this.createButton.click();
    await this.page.getByTestId('project-name-input').fill(name);
    await this.page.getByRole('button', { name: 'Create' }).click();
    await this.page.waitForLoadState('networkidle');
    return this;
  }
}
```

Usage in tests:

```typescript
test('user can log in and see dashboard', async ({ page }) => {
  const loginPage = new LoginPage(page);
  const dashboardPage = new DashboardPage(page);

  await loginPage.goto();
  await loginPage.login('alice@example.com', 'SecureP@ss1');
  await dashboardPage.expectWelcome('Alice');
});
```

Page objects encapsulate the HOW (selectors, clicks, waits). Tests express the WHAT
(user behavior and expected outcomes).

### Selector Strategy

Use selectors in this priority order. Higher priority selectors are more stable and
resistant to UI refactoring.

| Priority | Selector Type     | Example                                         | When to Use           |
|----------|-------------------|-------------------------------------------------|-----------------------|
| 1        | data-testid       | `page.getByTestId('submit-btn')`                | Always preferred      |
| 2        | ARIA role         | `page.getByRole('button', { name: 'Submit' })`  | Accessible elements   |
| 3        | Label text        | `page.getByLabel('Email address')`               | Form inputs           |
| 4        | Placeholder       | `page.getByPlaceholder('Search...')`             | Search/filter inputs  |
| 5        | Text content      | `page.getByText('Welcome back')`                 | Static display text   |
| NEVER    | CSS selectors     | `page.locator('.btn-primary')`                   | NEVER in E2E tests    |
| NEVER    | XPath             | `page.locator('//div[@class="header"]')`         | NEVER in E2E tests    |

Why never CSS or XPath:

- CSS classes change during styling refactors, breaking tests that test behavior.
- XPath is brittle to DOM structure changes.
- data-testid attributes are stable, intentional, and clearly communicate "this element
  is tested."

Add `data-testid` attributes to components during development:

```tsx
<button data-testid="create-project-btn" onClick={handleCreate}>
  Create Project
</button>
```

### Wait Strategies

Playwright auto-waits for elements, but complex flows need explicit wait strategies.

#### Correct Wait Patterns

```typescript
// Wait for network to settle after navigation
await page.goto('/dashboard');
await page.waitForLoadState('networkidle');

// Wait for a specific element to appear
await page.waitForSelector('[data-testid="project-list"]');

// Wait for a specific API response
const responsePromise = page.waitForResponse('**/api/v1/projects');
await page.getByTestId('refresh-btn').click();
const response = await responsePromise;
expect(response.status()).toBe(200);

// Wait for navigation after form submit
await Promise.all([
  page.waitForURL('**/dashboard'),
  page.getByRole('button', { name: 'Submit' }).click(),
]);
```

#### NEVER Use waitForTimeout

```typescript
// BAD -- arbitrary delays make tests slow and flaky
await page.waitForTimeout(3000);

// GOOD -- wait for the specific condition
await page.waitForSelector('[data-testid="success-toast"]');
```

`waitForTimeout` is the number one cause of flaky E2E tests. It either waits too long
(slow test) or not long enough (flaky test). Always wait for a specific condition.

### Authentication State Reuse

Authentication is expensive. Do not log in through the UI for every test. Instead,
authenticate once and reuse the browser state.

#### Setup Project for Auth

```typescript
// playwright.config.ts
import { defineConfig } from '@playwright/test';

export default defineConfig({
  projects: [
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
    },
    {
      name: 'chromium',
      use: {
        storageState: 'playwright/.auth/user.json',
      },
      dependencies: ['setup'],
    },
  ],
});
```

#### Auth Setup File

```typescript
// tests/auth.setup.ts
import { test as setup, expect } from '@playwright/test';

const authFile = 'playwright/.auth/user.json';

setup('authenticate', async ({ page }) => {
  await page.goto('/login');
  await page.getByTestId('login-email').fill('testuser@example.com');
  await page.getByTestId('login-password').fill('TestP@ssword1');
  await page.getByRole('button', { name: 'Sign in' }).click();

  // Wait for auth to complete
  await page.waitForURL('**/dashboard');
  await expect(page.getByTestId('welcome-message')).toBeVisible();

  // Save auth state
  await page.context().storageState({ path: authFile });
});
```

Now every test in the `chromium` project starts already authenticated. The login flow
runs once, not per-test.

### Test Data Management

E2E tests need data in the database. Manage it carefully to avoid conflicts.

#### Seed the Database

Create a seed script that runs before E2E tests:

```typescript
// tests/global-setup.ts
import { FullConfig } from '@playwright/test';

async function globalSetup(config: FullConfig) {
  // Reset test database to known state
  const response = await fetch('http://localhost:8000/api/test/reset', {
    method: 'POST',
    headers: { 'X-Test-Secret': process.env.TEST_SECRET || '' },
  });
  if (!response.ok) throw new Error('Failed to reset test database');

  // Seed required data
  await fetch('http://localhost:8000/api/test/seed', {
    method: 'POST',
    headers: { 'X-Test-Secret': process.env.TEST_SECRET || '' },
  });
}

export default globalSetup;
```

#### Unique Test Data

When tests create data, use unique identifiers to avoid conflicts in parallel runs:

```typescript
import { v4 as uuidv4 } from 'uuid';

test('user creates a new project', async ({ page }) => {
  const projectName = `Test Project ${uuidv4().slice(0, 8)}`;
  const dashboard = new DashboardPage(page);

  await dashboard.createProject(projectName);

  await expect(page.getByText(projectName)).toBeVisible();
});
```

#### Cleanup

Tests that create data should clean up after themselves, or rely on the global teardown
to reset the database:

```typescript
// playwright.config.ts
export default defineConfig({
  globalSetup: require.resolve('./tests/global-setup'),
  globalTeardown: require.resolve('./tests/global-teardown'),
});
```

### Debugging

When a test fails, use these tools to diagnose the issue.

#### Debug Mode

```bash
# Run with Playwright Inspector (step through test visually)
PWDEBUG=1 npx playwright test tests/e2e/login.spec.ts

# Run headed (see the browser)
npx playwright test --headed

# Run in slow motion
npx playwright test --headed --slow-mo=500
```

#### Trace Viewer

Enable traces to capture a full recording of failed tests:

```typescript
// playwright.config.ts
export default defineConfig({
  use: {
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on-first-retry',
  },
  retries: 1,
});
```

View traces after failure:

```bash
npx playwright show-trace test-results/tests-e2e-login-Login-test-chromium/trace.zip
```

The trace viewer shows every action, network request, console log, and DOM snapshot.
It is the most powerful debugging tool for E2E tests.

#### Screenshot on Failure

Screenshots are captured automatically on failure when configured. Access them in the
test results directory or CI artifacts.

### CI Integration

Configure Playwright for headless execution in CI pipelines.

#### CI Configuration

```yaml
# .github/workflows/e2e.yml
name: E2E Tests
on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20

      - name: Install dependencies
        run: npm ci

      - name: Install Playwright browsers
        run: npx playwright install --with-deps chromium

      - name: Start application
        run: docker compose -f docker-compose.test.yml up -d

      - name: Wait for app ready
        run: npx wait-on http://localhost:3000 --timeout 60000

      - name: Run E2E tests
        run: npx playwright test --project=chromium

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 7
```

#### Playwright CI Config

```typescript
// playwright.config.ts
export default defineConfig({
  workers: process.env.CI ? 2 : undefined,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? 'html' : 'list',
  use: {
    headless: true,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
});
```

Key CI settings:

- **workers: 2** -- Parallel execution speeds up the suite but uses more resources.
  Tune based on CI runner capacity.
- **retries: 2** -- Retry failed tests to reduce flaky false negatives. Never use
  retries to mask real failures.
- **reporter: html** -- Generate an HTML report for easy debugging in CI artifacts.
- **headless: true** -- No display server needed in CI.

## Examples

### E2E Test: User Registration to Resource Creation

This example tests the complete flow: register, log in, create a project, and verify
it appears in the dashboard.

```typescript
// tests/e2e/user-flow.spec.ts
import { test, expect } from '@playwright/test';
import { v4 as uuidv4 } from 'uuid';

test.describe('New User Complete Flow', () => {
  const testId = uuidv4().slice(0, 8);
  const email = `e2e-${testId}@test.example.com`;
  const password = 'E2eTestP@ss123';
  const fullName = `E2E User ${testId}`;

  test('register, login, create project, verify', async ({ page }) => {
    // Step 1: Register
    await page.goto('/register');
    await page.getByTestId('register-email').fill(email);
    await page.getByTestId('register-password').fill(password);
    await page.getByTestId('register-name').fill(fullName);
    await page.getByRole('button', { name: 'Create Account' }).click();

    // Wait for redirect to dashboard
    await page.waitForURL('**/dashboard');
    await expect(page.getByTestId('welcome-message')).toContainText(fullName);

    // Step 2: Create a project
    const projectName = `Test Project ${testId}`;
    await page.getByRole('button', { name: 'Create Project' }).click();
    await page.getByTestId('project-name-input').fill(projectName);
    await page.getByTestId('project-description-input').fill('Created by E2E test');
    await page.getByRole('button', { name: 'Create' }).click();

    // Wait for project creation
    await page.waitForLoadState('networkidle');

    // Step 3: Verify project appears in list
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    const projectCard = page.getByTestId('project-card').filter({
      hasText: projectName,
    });
    await expect(projectCard).toBeVisible();

    // Step 4: Verify project detail page
    await projectCard.click();
    await page.waitForURL(/\/projects\/.+/);
    await expect(page.getByTestId('project-title')).toHaveText(projectName);
    await expect(page.getByTestId('project-owner')).toContainText(fullName);
  });
});
```

This test validates the most critical user path in one flow. If this test passes, the
core registration-to-creation pipeline is working.

## Edge Cases

### Flaky Tests

E2E tests are inherently more prone to flakiness than unit tests. Common causes and
solutions:

| Cause                       | Symptom                        | Fix                                           |
|-----------------------------|--------------------------------|-----------------------------------------------|
| Network timing              | Element not found              | Use `waitForLoadState('networkidle')`          |
| Animation interference      | Click hits wrong element       | Disable animations in test config              |
| Dynamic content loading     | Stale element reference        | Use Playwright auto-waiting locators           |
| Test data collision         | Duplicate key errors           | Use unique IDs per test run                    |
| Server cold start           | Timeout on first request       | Add readiness check in global setup            |

Disable animations in tests:

```typescript
// playwright.config.ts
export default defineConfig({
  use: {
    // Reduce motion to prevent animation interference
    contextOptions: {
      reducedMotion: 'reduce',
    },
  },
});
```

### Auth Token Expiry

Long-running test suites may encounter expired auth tokens. Handle this by:

1. Using short-lived tokens with a refresh mechanism in the app.
2. Setting generous token expiry for the test environment (e.g., 24 hours).
3. Re-authenticating in a `beforeAll` hook if the suite runs longer than token lifetime.

```typescript
test.describe('Long suite', () => {
  test.beforeAll(async ({ browser }) => {
    // Re-authenticate if token might be expired
    const context = await browser.newContext();
    const page = await context.newPage();
    // ... login flow ...
    await context.storageState({ path: 'playwright/.auth/user.json' });
    await context.close();
  });

  // Tests use refreshed auth state
});
```

### Parallel Test Isolation

When running tests in parallel (multiple workers), each worker gets its own browser
context, but they share the same database. Prevent data conflicts by:

1. **Unique identifiers**: Every test-created entity uses a UUID or timestamp suffix.
2. **Worker-scoped data**: Use `test.describe.configure({ mode: 'serial' })` for tests
   that must run sequentially within a describe block.
3. **Database per worker**: For maximum isolation, create a separate test database per
   worker using the `workerIndex` fixture.

```typescript
test('creates unique resource', async ({ page }, testInfo) => {
  const uniqueName = `resource-${testInfo.workerIndex}-${Date.now()}`;
  // Use uniqueName for all created data
});
```

### Mobile Viewport Testing

Test responsive behavior by configuring viewports per project:

```typescript
// playwright.config.ts
export default defineConfig({
  projects: [
    {
      name: 'Desktop Chrome',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 14'] },
    },
    {
      name: 'Tablet',
      use: {
        viewport: { width: 768, height: 1024 },
        isMobile: true,
      },
    },
  ],
});
```

### Handling File Uploads

```typescript
test('user uploads a profile picture', async ({ page }) => {
  await page.goto('/settings/profile');

  const fileInput = page.getByTestId('avatar-upload');
  await fileInput.setInputFiles('tests/fixtures/avatar.png');

  await page.getByRole('button', { name: 'Save' }).click();
  await expect(page.getByTestId('avatar-image')).toHaveAttribute(
    'src',
    /\/uploads\/avatars\/.+\.png/
  );
});
```

### Handling Dialogs and Confirmations

```typescript
test('user confirms project deletion', async ({ page }) => {
  // Set up dialog handler BEFORE triggering the dialog
  page.on('dialog', async (dialog) => {
    expect(dialog.message()).toContain('Are you sure');
    await dialog.accept();
  });

  await page.getByTestId('delete-project-btn').click();

  // Verify project is removed
  await expect(page.getByTestId('project-card')).toHaveCount(0);
});
```
