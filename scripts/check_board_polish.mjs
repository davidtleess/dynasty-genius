/**
 * DG-210 — browser check for the board polish.
 *
 * The polish moved the unit labels into the headers and rebuilt the phone row as a card. Both moves
 * can quietly lose meaning, so this reads the rendered board against the real accepted bundle and
 * checks that the three things which must survive did: the unit, a missing value, and a tie.
 *
 *   DG_LOVABLE_URL    a built Lovable server, already running. Required.
 *   DG_EVIDENCE_DIR   a NEW directory. Required. Never overwritten.
 */
import { createRequire } from "node:module";
import { mkdirSync, writeFileSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";

const require = createRequire(resolve(process.cwd(), "frontend/package.json"));
const { chromium } = require("playwright");

const URL_BASE = process.env["DG_LOVABLE_URL"];
const EVIDENCE = process.env["DG_EVIDENCE_DIR"];
if (!URL_BASE || !EVIDENCE) {
  console.error("DG_LOVABLE_URL and DG_EVIDENCE_DIR are both required.");
  process.exit(1);
}
if (existsSync(EVIDENCE)) {
  console.error(`${EVIDENCE} exists. Evidence is never overwritten.`);
  process.exit(1);
}
mkdirSync(EVIDENCE, { recursive: true });

const results = [];
let failures = 0;
const check = (name, ok, detail = "") => {
  if (!ok) failures += 1;
  results.push({ name, ok: Boolean(ok), detail });
  console.log(`  ${ok ? "ok  " : "FAIL"}  ${name}${ok || !detail ? "" : `\n          ${detail}`}`);
};

const browser = await chromium.launch();
try {
  for (const [label, width, height] of [["desktop", 1440, 950], ["phone", 390, 844], ["narrow", 320, 700]]) {
    const context = await browser.newContext({ viewport: { width, height } });
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(String(e)));
    page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
    await context.route("**/*", (route) => {
      const host = new URL(route.request().url()).host;
      return !host || host === new URL(URL_BASE).host
        ? route.fallback()
        : route.fulfill({ status: 200, contentType: "text/css", body: "" });
    });

    await page.goto(`${URL_BASE}/`, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.locator("button[aria-label*='. ']:visible").first().waitFor({ timeout: 30000 });
    await page.waitForTimeout(900);
    const body = await page.evaluate(() => document.body.innerText);
    await page.screenshot({ path: join(EVIDENCE, `${label}-roster.png`), fullPage: true });

    // --- the three things the polish must not lose ---------------------------------------------------
    check(`${label}: our unit and the market's are both named`,
      /points over replacement/i.test(body) && /FantasyCalc price/i.test(body), body.slice(0, 200));
    check(`${label}: the two are never differenced or shown as money`,
      !/\$/.test(body) && !/net (model )?value|% (over|above) market/i.test(body),
      (body.match(/\$[\d,]+|net value[^\n]*/g) ?? []).slice(0, 3).join(","));
    check(`${label}: a player with no price says so rather than showing a number`,
      /Not priced/.test(body));
    check(`${label}: a true zero at the floor is distinct from a missing value`,
      /0 · floor/.test(body) && /No valuation|Not priced/.test(body));
    check(`${label}: a tied rank still renders as its span`, /\d+–\d+/.test(body),
      (body.match(/\d+–\d+/g) ?? []).slice(0, 3).join(","));
    check(`${label}: no page or console errors`, errors.length === 0, errors.slice(0, 2).join(" | "));
    // Real photos are served in this tree now, so a face that fails is a real failure rather than a
    // stand-in. Initials remain the fallback and are not asserted away.
    // Rows are lazily loaded, so an off-screen photo is correctly not fetched yet. Demanding all of
    // them would penalise the behaviour rather than test it. What must hold: everything visible has
    // loaded, and everything loads once scrolled to.
    const visible = await page.evaluate(() => {
      const imgs = [...document.querySelectorAll("img[src*='/assets/headshots/']")];
      const inView = imgs.filter((img) => {
        const box = img.getBoundingClientRect();
        return box.top < window.innerHeight && box.bottom > 0;
      });
      return { total: imgs.length, inView: inView.length, loaded: inView.filter((i) => i.naturalWidth > 0).length };
    });
    check(`${label}: every headshot on screen has loaded`,
      visible.inView > 0 && visible.loaded === visible.inView, JSON.stringify(visible));
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(2500);
    // Both layouts are in the DOM and one is display:none at any width, so its lazy images are
    // correctly never fetched. Only the rendered layout is asserted.
    const all = await page.evaluate(() => {
      const imgs = [...document.querySelectorAll("img[src*='/assets/headshots/']")].filter(
        (img) => img.getBoundingClientRect().width > 0,
      );
      return { rendered: imgs.length, loaded: imgs.filter((i) => i.naturalWidth > 0).length };
    });
    check(`${label}: the rest load as the board is scrolled`,
      all.rendered > 0 && all.loaded === all.rendered, JSON.stringify(all));
    await page.evaluate(() => window.scrollTo(0, 0));
    check(`${label}: nothing scrolls sideways`,
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));

    if (label === "desktop") {
      // The unit belongs in the header once. Repeating it on 27 rows is the noise this pass removed.
      const repeats = (body.match(/pts over replacement/g) ?? []).length;
      check("desktop: the unit is stated in the header, not on every row", repeats === 0,
        `saw ${repeats} per-row unit labels`);
      const aligned = await page.evaluate(() => {
        const cells = [...document.querySelectorAll("[style*='tabular-nums']")];
        return { count: cells.length, tabular: cells.every((c) => getComputedStyle(c).fontVariantNumeric.includes("tabular-nums")) };
      });
      check("desktop: focal numbers are tabular", aligned.count > 0 && aligned.tabular, JSON.stringify(aligned));
      check("desktop: no header repeats its unit word", !/points points/i.test(body),
        (body.match(/\w+ points points/gi) ?? []).join(","));
      const wrapped = await page.evaluate(() => {
        const cells = [...document.querySelectorAll("span")].filter((el) =>
          /places (higher|lower)$/.test(el.textContent ?? ""));
        return cells.filter((el) => el.getBoundingClientRect().height > 26).length;
      });
      check("desktop: the focal column does not wrap to two lines", wrapped === 0, `${wrapped} wrapped`);
    }

    if (label !== "desktop") {
      // A phone card that shows only ranks makes the manager open every player to see a value.
      check(`${label}: phone cards carry the values, not just the ranks`,
        /points over replacement/i.test(body) && /FantasyCalc price/i.test(body) &&
          /\d{4} points/.test(body), body.slice(0, 300));
      // Scoped to this ticket's own surfaces. Two controls in the shell (the player search at 38px
      // and "Reload saved snapshot" at 28px) are below 44 and belong to another lane's file; they are
      // reported in the handoff rather than graded here as mine.
      const targets = await page.evaluate(() => {
        const owned = [
          ...document.querySelectorAll("[data-dg-owned='board-controls'] select, [data-dg-owned='board-controls'] input, [data-dg-owned='board-controls'] button"),
          ...document.querySelectorAll("button[aria-label*='. ']"),
        ];
        return owned
          .filter((el) => el.getBoundingClientRect().height > 0)
          .map((el) => Math.round(el.getBoundingClientRect().height));
      });
      check(`${label}: every control this ticket owns keeps a 44px target`,
        targets.length > 0 && targets.every((h) => h >= 44),
        targets.length ? `smallest ${Math.min(...targets)}px of ${targets.length}` : "no owned controls found");
    }

    // --- the drawer keeps its units, because compact is a table concern only --------------------------
    if (label === "desktop") {
      const firstRow = page.locator("button[aria-label*='. ']:visible").first();
      await firstRow.click();
      const drawer = page.getByRole("dialog");
      await drawer.waitFor({ state: "visible", timeout: 15000 });
      const inside = await drawer.innerText();
      await page.screenshot({ path: join(EVIDENCE, `${label}-drawer.png`) });
      check("desktop: a standalone cell in the drawer still carries its unit",
        /pts over replacement/i.test(inside) || /points over replacement/i.test(inside),
        inside.slice(0, 200));
    }
    await context.close();
  }
} catch (error) {
  check("the run completed without an exception", false, String(error).slice(0, 300));
} finally {
  await browser.close().catch(() => {});
  writeFileSync(join(EVIDENCE, "results.json"), JSON.stringify({ failures, results }, null, 1));
  console.log(`\n${results.length - failures} of ${results.length} checks passed. Evidence: ${EVIDENCE}`);
}
process.exit(failures === 0 ? 0 : 1);
