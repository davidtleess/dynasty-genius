import AxeBuilder from "../../frontend/node_modules/@axe-core/playwright";
import { expect, test } from "../../frontend/node_modules/@playwright/test";
import { writeFileSync } from "node:fs";

async function assertNoHorizontalOverflow(page) {
  const metrics = await page.evaluate(() => ({
    body: document.body.scrollWidth,
    document: document.documentElement.scrollWidth,
    viewport: window.innerWidth,
  }));
  expect(metrics.body).toBeLessThanOrEqual(metrics.viewport);
  expect(metrics.document).toBeLessThanOrEqual(metrics.viewport);
}

async function openTankDellDetail(page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Trade Lab" }).click();
  await page
    .getByRole("searchbox", { name: "Search tradeable assets" })
    .fill("Tank Dell");
  await page.getByRole("button", { name: "Tank Dell", exact: true }).click();
  const inspector = page.getByRole("complementary", { name: "Player inspector" });
  await expect(inspector).toBeVisible();
  await inspector
    .getByRole("button", { name: "Open full evidence card" })
    .click();
  return page.getByRole("article", { name: "Player detail for Tank Dell" });
}

test("DG-022 real Tank Dell surface is truthful on desktop and mobile", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 960 });
  let card = await openTankDellDetail(page);
  await expect(card).toBeVisible();
  await expect(card.getByText("Experimental", { exact: true })).toBeVisible();
  await expect(card.getByText("Not in 2026 model snapshot")).toBeVisible();
  await expect(
    card.getByText("No model prediction was frozen for 2026 outcome evaluation."),
  ).toBeVisible();
  await expect(
    card.getByText("221 of 274 current rostered skill players were included."),
  ).toBeVisible();
  await assertNoHorizontalOverflow(page);
  await page.screenshot({ path: "dg022-tank-desktop.png", fullPage: true });
  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight * 0.45));
  await page.screenshot({ path: "dg022-tank-desktop-mid-scroll.png" });

  const axe = await new AxeBuilder({ page }).include("main").analyze();
  writeFileSync("dg022-axe.json", JSON.stringify(axe.violations, null, 2));
  expect(axe.violations).toEqual([]);

  await page.setViewportSize({ width: 390, height: 844 });
  card = await openTankDellDetail(page);
  await expect(card).toBeVisible();
  await expect(card.getByText("Not in 2026 model snapshot")).toBeVisible();
  await assertNoHorizontalOverflow(page);
  await page.screenshot({ path: "dg022-tank-mobile.png", fullPage: true });
  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight * 0.45));
  await page.screenshot({ path: "dg022-tank-mobile-mid-scroll.png" });
});
