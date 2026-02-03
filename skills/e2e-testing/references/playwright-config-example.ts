import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright Configuration Template
 *
 * Covers multi-browser testing, CI-aware retries, auth state setup,
 * and a local dev server.
 *
 * See https://playwright.dev/docs/test-configuration for full reference.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,

  /* Retry twice on CI to absorb flakiness; zero retries locally. */
  retries: process.env.CI ? 2 : 0,

  /* Limit parallel workers on CI to avoid resource contention. */
  workers: process.env.CI ? 2 : undefined,

  /* Reporters: interactive list locally, HTML report always. */
  reporter: [["list"], ["html", { open: "never" }]],

  /* Shared settings applied to every project. */
  use: {
    baseURL: process.env.BASE_URL || "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },

  projects: [
    /* --- Auth setup (runs once before browser projects) --- */
    {
      name: "setup",
      testMatch: /.*\.setup\.ts/,
    },

    /* --- Desktop browsers --- */
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        storageState: "e2e/.auth/user.json",
      },
      dependencies: ["setup"],
    },
    {
      name: "firefox",
      use: {
        ...devices["Desktop Firefox"],
        storageState: "e2e/.auth/user.json",
      },
      dependencies: ["setup"],
    },
    {
      name: "webkit",
      use: {
        ...devices["Desktop Safari"],
        storageState: "e2e/.auth/user.json",
      },
      dependencies: ["setup"],
    },
  ],

  /* Start the local dev server before running tests. */
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
