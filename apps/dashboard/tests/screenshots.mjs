// Capture dashboard screenshots for docs/media: node tests/screenshots.mjs (preview server + API running)
import { chromium } from "@playwright/test";

const base = process.env.DASH_URL ?? "http://127.0.0.1:4173";
const key = process.env.TL_API_KEY ?? "dev-key";
const out = new URL("../../../docs/media/", import.meta.url).pathname;
const browser = await chromium.launch();
for (const theme of ["light", "dark"]) {
  const page = await browser.newPage({ viewport: { width: 1360, height: 900 }, colorScheme: theme });
  await page.goto(base);
  const login = page.getByLabel("API key");
  if (await login.isVisible().catch(() => false)) {
    await login.fill(key);
    await page.getByRole("button", { name: "Sign in" }).click();
  }
  await page.getByRole("heading", { name: "Overview" }).waitFor();
  const pages = theme === "light" ? ["/", "/fairness", "/map", "/feed", "/distribution"] : ["/"];
  for (const path of pages) {
    await page.goto(base + path);
    await page.waitForTimeout(1500);
    const name = path === "/" ? "overview" : path.slice(1);
    await page.screenshot({ path: `${out}dashboard_${name}${theme === "dark" ? "_dark" : ""}.png`, fullPage: true });
  }
  await page.close();
}
await browser.close();
console.log("saved to", out);
