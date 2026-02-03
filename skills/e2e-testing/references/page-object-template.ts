import { type Page, type Locator, expect } from "@playwright/test";

/**
 * Page Object Template
 *
 * Encapsulates page interactions behind a clean API.
 * Uses data-testid selectors for resilience against UI changes.
 * Supports method chaining for fluent test authoring.
 */
export class ExamplePage {
  // --- Selectors (prefer data-testid for stability) ---
  private readonly heading: Locator;
  private readonly nameInput: Locator;
  private readonly emailInput: Locator;
  private readonly submitButton: Locator;
  private readonly successMessage: Locator;
  private readonly errorMessage: Locator;
  private readonly loadingSpinner: Locator;
  private readonly itemList: Locator;

  constructor(private readonly page: Page) {
    this.heading = page.getByTestId("page-heading");
    this.nameInput = page.getByTestId("input-name");
    this.emailInput = page.getByTestId("input-email");
    this.submitButton = page.getByTestId("btn-submit");
    this.successMessage = page.getByTestId("msg-success");
    this.errorMessage = page.getByTestId("msg-error");
    this.loadingSpinner = page.getByTestId("loading-spinner");
    this.itemList = page.getByTestId("item-list");
  }

  // --- Navigation ---

  async navigate(path: string = "/"): Promise<this> {
    await this.page.goto(path);
    await this.heading.waitFor({ state: "visible" });
    return this;
  }

  // --- Form Actions ---

  async fillForm(name: string, email: string): Promise<this> {
    await this.nameInput.fill(name);
    await this.emailInput.fill(email);
    return this;
  }

  async clickSubmit(): Promise<this> {
    await this.submitButton.click();
    return this;
  }

  // --- Wait Helpers ---

  async waitForLoadingComplete(): Promise<this> {
    await this.loadingSpinner.waitFor({ state: "hidden", timeout: 10_000 });
    return this;
  }

  async waitForElement(testId: string): Promise<this> {
    await this.page.getByTestId(testId).waitFor({ state: "visible" });
    return this;
  }

  // --- Assertion Helpers ---

  async expectSuccessMessage(text: string): Promise<this> {
    await expect(this.successMessage).toBeVisible();
    await expect(this.successMessage).toContainText(text);
    return this;
  }

  async expectErrorMessage(text: string): Promise<this> {
    await expect(this.errorMessage).toBeVisible();
    await expect(this.errorMessage).toContainText(text);
    return this;
  }

  async expectItemCount(count: number): Promise<this> {
    await expect(this.itemList.locator(":scope > *")).toHaveCount(count);
    return this;
  }

  // --- Returning a different Page Object on navigation ---

  async submitAndNavigateTo<T>(
    PageObjectClass: new (page: Page) => T
  ): Promise<T> {
    await this.submitButton.click();
    await this.page.waitForURL("**/*");
    return new PageObjectClass(this.page);
  }
}
