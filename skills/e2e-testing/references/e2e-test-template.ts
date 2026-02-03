import { test, expect } from "@playwright/test";
import { ExamplePage } from "./page-object-template";

/**
 * E2E Test Template
 *
 * Demonstrates a complete CRUD user workflow using Page Objects.
 * Wait strategies are annotated with comments for clarity.
 */

test.describe("Example Feature - Full CRUD Workflow", () => {
  let examplePage: ExamplePage;

  test.beforeEach(async ({ page }) => {
    examplePage = new ExamplePage(page);

    // Navigate to the page and wait for the heading to be visible
    // (handled inside the page object's navigate method).
    await examplePage.navigate("/items");

    // If auth is required, authenticate first.
    // With Playwright's storageState the login session is typically
    // restored automatically via the global setup project.
  });

  test("should complete full item lifecycle: create, verify, update, delete", async ({
    page,
  }) => {
    // --- CREATE ---
    await examplePage.fillForm("New Item", "item@example.com");
    await examplePage.clickSubmit();

    // waitForLoadingComplete waits until the spinner disappears,
    // ensuring the server round-trip has finished before asserting.
    await examplePage.waitForLoadingComplete();
    await examplePage.expectSuccessMessage("Item created successfully");

    // --- VERIFY ---
    // Use Playwright's auto-waiting: getByTestId will retry until
    // the element is actionable (visible, stable, enabled).
    const createdItem = page.getByTestId("item-New Item");
    await expect(createdItem).toBeVisible();
    await expect(createdItem).toContainText("item@example.com");

    // --- UPDATE ---
    await createdItem.getByTestId("btn-edit").click();

    // waitFor ensures the edit form is rendered before interacting.
    await page.getByTestId("edit-form").waitFor({ state: "visible" });
    await page.getByTestId("input-name").fill("Updated Item");
    await page.getByTestId("btn-save").click();

    // toHaveText uses auto-retrying assertions; Playwright re-checks
    // the DOM until the text matches or the timeout expires.
    await expect(page.getByTestId("item-Updated Item")).toHaveText(
      /Updated Item/
    );
    await examplePage.expectSuccessMessage("Item updated successfully");

    // --- DELETE ---
    await page.getByTestId("item-Updated Item").getByTestId("btn-delete").click();

    // Handle confirmation dialog.
    await page.getByTestId("btn-confirm-delete").click();
    await examplePage.waitForLoadingComplete();

    // toBeHidden waits until the element is no longer visible,
    // confirming the deletion propagated to the UI.
    await expect(page.getByTestId("item-Updated Item")).toBeHidden();
    await examplePage.expectSuccessMessage("Item deleted successfully");
  });

  test("should show validation errors for empty form", async () => {
    await examplePage.clickSubmit();
    await examplePage.expectErrorMessage("Name is required");
  });
});
