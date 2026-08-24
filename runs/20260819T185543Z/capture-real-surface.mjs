import { chromium } from "../../frontend/node_modules/playwright/index.mjs";
import AxeBuilder from "../../frontend/node_modules/@axe-core/playwright/dist/index.js";
import { writeFile } from "node:fs/promises";

const browser = await chromium.launch({
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  headless: true,
});
const context = await browser.newContext({ viewport: { width: 1440, height: 960 } });
const page = await context.newPage();

async function openTankDellDetail() {
  await page.goto("http://127.0.0.1:8122/", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Trade Lab" }).click();
  await page
    .getByRole("searchbox", { name: "Search tradeable assets" })
    .fill("Tank Dell");
  await page.getByRole("button", { name: "Tank Dell", exact: true }).click();
  const inspector = page.getByRole("complementary", { name: "Player inspector" });
  await inspector.getByRole("button", { name: "Open full evidence card" }).click();
  const card = page.getByRole("article", { name: "Player detail for Tank Dell" });
  await card.waitFor();
  return card;
}

async function verifyPage(card) {
  await card.getByText("Experimental", { exact: true }).waitFor();
  await card.getByText("Not in 2026 model snapshot").waitFor();
  await card
    .getByText("No model prediction was frozen for 2026 outcome evaluation.")
    .waitFor();
  await card
    .getByText("221 of 274 current rostered skill players were included.")
    .waitFor();
  const metrics = await page.evaluate(() => ({
    body: document.body.scrollWidth,
    document: document.documentElement.scrollWidth,
    viewport: window.innerWidth,
  }));
  if (metrics.body > metrics.viewport || metrics.document > metrics.viewport) {
    throw new Error(`horizontal_overflow:${JSON.stringify(metrics)}`);
  }
}

let card = await openTankDellDetail();
await verifyPage(card);
await page.screenshot({ path: "dg022-tank-desktop.png", fullPage: true });
await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight * 0.45));
await page.screenshot({ path: "dg022-tank-desktop-mid-scroll.png" });
const axe = await new AxeBuilder({ page }).include("main").analyze();
await writeFile("dg022-axe.json", JSON.stringify(axe.violations, null, 2));
if (axe.violations.length) throw new Error(`axe_violations:${axe.violations.length}`);

await page.setViewportSize({ width: 390, height: 844 });
card = await openTankDellDetail();
await verifyPage(card);
await page.screenshot({ path: "dg022-tank-mobile.png", fullPage: true });
await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight * 0.45));
await page.screenshot({ path: "dg022-tank-mobile-mid-scroll.png" });

await browser.close();
console.log("DG022_REAL_SURFACE_OK");
