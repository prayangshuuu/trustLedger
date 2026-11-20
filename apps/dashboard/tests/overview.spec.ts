import { expect, test } from "@playwright/test";

const API_KEY = process.env.TL_API_KEY ?? "dev-key";

test("overview shows live KPIs after API-key login", async ({ page }) => {
  await page.goto("/");
  const login = page.getByLabel("API key");
  if (await login.isVisible().catch(() => false)) {
    await login.fill(API_KEY);
    await page.getByRole("button", { name: "Sign in" }).click();
  }
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await expect(page.getByTestId("kpi-applications")).toContainText(/\d/);
  await expect(page.getByTestId("kpi-lift")).toContainText("%");
  await page.getByRole("link", { name: "Fairness" }).click();
  await expect(page.getByText(/PASS ≤ 0.05|FAIL > 0.05/)).toBeVisible();
});
