/**
 * DG-208 — browser check for the track record screen.
 *
 * Drives one synthetic view per state the execution contract names through an intercept, and reads
 * what renders. The screen's failure mode is not a crash: it is implying a record before one exists,
 * turning an absence into a number, or letting a pipeline identifier reach the manager. Each of those
 * has a check here.
 *
 *   DG_LOVABLE_URL    a built Lovable server, already running. Required.
 *   DG_EVIDENCE_DIR   a NEW directory. Required. Never overwritten.
 *   DG_BUNDLE_PATH    an explicitly supplied local board bundle. Required.
 *
 * Installs nothing; Playwright resolves from the repository's existing frontend lockfile.
 */
import { createRequire } from "node:module";
import { mkdirSync, writeFileSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";

const require = createRequire(resolve(process.cwd(), "frontend/package.json"));
const { chromium } = require("playwright");
const { views, captureResults } = await import(
  resolve(process.cwd(), "lovable/tests/fixtures/track-record-views.ts")
);
// The shell reads the board bundle on every page. This tree carries no copy of it, so without one the
// shell renders its own load failure and every assertion below reads that instead of the screen.
// Serving the accepted bundle keeps a genuine console error meaningful.
const { readFileSync: readBundleFile } = await import("node:fs");
const BUNDLE_PATH = process.env["DG_BUNDLE_PATH"];
const URL_BASE = process.env["DG_LOVABLE_URL"];
const EVIDENCE = process.env["DG_EVIDENCE_DIR"];
if (!URL_BASE || !EVIDENCE || !BUNDLE_PATH) {
  console.error("check_track_record_browser: DG_LOVABLE_URL, DG_EVIDENCE_DIR and DG_BUNDLE_PATH are required.");
  process.exit(1);
}
const BUNDLE = readBundleFile(BUNDLE_PATH, "utf8");
if (existsSync(EVIDENCE)) {
  console.error(`check_track_record_browser: ${EVIDENCE} exists. Evidence is never overwritten.`);
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

/** No pipeline identifier may reach the screen, in any state. */
const PIPELINE = /sha256|catalog_content|report_run|report_sha|league_sha|market_sha|snapshot_id|_[a-z]+_/;

const browser = await chromium.launch();
try {
  for (const width of [1440, 390]) {
    const label = width >= 1024 ? "desktop" : "phone";
    for (const [name, view] of Object.entries(views)) {
      const context = await browser.newContext({ viewport: { width, height: 900 } });
      const page = await context.newPage();
      const errors = [];
      page.on("pageerror", (e) => errors.push(String(e)));
      page.on("console", (m) => m.type() === "error" && errors.push(m.text()));

      await context.route("**/api/private/track-record*", (route) =>
        route.request().method() === "POST"
          ? route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(captureResults.partial) })
          : route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(view) }),
      );
      await context.route("**/data/dg-bundle.json", (route) =>
        route.fulfill({ status: 200, contentType: "application/json", body: BUNDLE }),
      );
      await context.route("**/*", async (route) => {
        const host = new URL(route.request().url()).host;
        if (!host || host === new URL(URL_BASE).host) return route.fallback();
        return route.fulfill({ status: 200, contentType: "text/css", body: "" });
      });

      await page.goto(`${URL_BASE}/track-record`, { waitUntil: "domcontentloaded", timeout: 60000 });
      await page.getByRole("heading", { name: "Track record" }).first().waitFor({ timeout: 30000 });
      await page.waitForTimeout(700);
      const body = await page.evaluate(() => document.body.innerText);
      // Scoped to the screen this ticket owns. The shell around it is another lane's file, and a
      // check that fails on their copy would be reporting someone else's defect as mine.
      const main = await page.evaluate(
        () => (document.querySelector("[data-dg-screen='track-record']") ?? document.body).innerText,
      );
      await page.screenshot({ path: join(EVIDENCE, `${label}-${name}.png`), fullPage: true });

      check(`${label}/${name}: no pipeline identifier reaches the screen`,
        !PIPELINE.test(body), (body.match(PIPELINE) ?? []).join(","));
      check(`${label}/${name}: no page errors`, errors.length === 0, errors.slice(0, 2).join(" | "));

      if (name === "unavailable" || name === "not_configured") {
        check(`${label}/${name}: a transport fact, never an empty archive`,
          /not reachable|no archive is configured/i.test(body) &&
            !/no reading has been saved/i.test(body), body.slice(0, 160));
      }
      if (name === "empty") {
        check(`${label}/${name}: an empty archive says so`, /no reading has been saved yet/i.test(body));
      }
      if (name === "enrolledPending") {
        check(`${label}/${name}: the frozen forecast and both baselines are shown`,
          body.includes("Forecast") && body.includes("Prior season") && body.includes("Position median") &&
            body.includes("402.5") && body.includes("310.3") && body.includes("288.0"),
          body.slice(0, 400));
        // Precise rather than blunt: an earlier version banned the string "0.0" anywhere, which fired
        // on a real market momentum of −0.041. What matters is that the UNFORECAST row shows a dash.
        const charlie = body.slice(body.indexOf("Charlie Cast"), body.indexOf("Charlie Cast") + 220);
        check(`${label}/${name}: an absent forecast is a dash with a reason, never a zero`,
          /No forecast was carried for him/i.test(body) && charlie.includes("—") && !/\b0(\.0)?\b/.test(
            charlie.replace(/[\d.]+%/g, "")), charlie.slice(0, 200));
        check(`${label}/${name}: nothing claims a score before the window closes`,
          !/accuracy|we were right|hit rate|win rate/i.test(body));
        check(`${label}/${name}: the two claims stay separate`,
          body.includes("Football production") && body.includes("Market movement") &&
            /never combined into one figure/i.test(body));
      }
      if (name === "inputUnavailable") {
        check(`${label}/${name}: a missing input is stated, not filled in`,
          /required input is missing/i.test(body) && /No player rows are available/i.test(body),
          body.slice(0, 300));
      }
      if (name === "graded" && label === "phone") {
        // A dense grid that scrolls sideways is not a phone layout. Every value must be reachable
        // by scrolling down only, and each one has to carry its own label once stacked.
        const overflow = await page.evaluate(() => ({
          scrollWidth: document.documentElement.scrollWidth,
          innerWidth: window.innerWidth,
          panners: [...document.querySelectorAll("*")].filter(
            (el) => el.scrollWidth > el.clientWidth + 4 && el.clientWidth > 100,
          ).length,
        }));
        check(`${label}/${name}: nothing needs sideways panning`,
          overflow.scrollWidth <= overflow.innerWidth + 1 && overflow.panners === 0,
          JSON.stringify(overflow));
        check(`${label}/${name}: stacked values keep their labels`,
          body.includes("Prior season") && body.includes("Position median") && body.includes("Forecast"),
          body.slice(0, 200));
      }
      if (name === "graded") {
        check(`${label}/${name}: a graded stream shows its comparison and its interval`,
          /95% interval/.test(body) && /inconclusive/i.test(body), body.slice(0, 300));
        check(`${label}/${name}: the market stream stays separately unscored`,
          /One capture is not a movement/i.test(body));
        // "We looked and it is too thin to say" is a result the manager is owed. Gating the whole
        // result on state === "graded" hid it entirely.
        check(`${label}/${name}: an insufficient finding is shown, not hidden`,
          /too little evidence/i.test(body));
        check(`${label}/${name}: no raw engine id or snake_case reaches the screen`,
          !/engine_b|[a-z]+_[a-z]+/.test(main),
          (main.match(/[a-z]+_[a-z]+/g) ?? []).slice(0, 4).join(","));
        check(`${label}/${name}: dates read as prose, not as raw ISO days`,
          !/\b20\d\d-\d\d-\d\d\b/.test(main),
          (main.match(/\b20\d\d-\d\d-\d\d\b/g) ?? []).slice(0, 3).join(","));
        check(`${label}/${name}: filtering is offered and says it does not change the counts`,
          /Find a player/i.test(body) && /never the counts above/i.test(body));
      }
      if (name === "twoSameDay") {
        const saved = [...body.matchAll(/Saved [A-Z][a-z]{2} \d+, \d{4}[^\n]*/g)].map((m) => m[0]);
        check(`${label}/${name}: two readings on one day are told apart without a hash`,
          saved.length >= 2 && new Set(saved).size === saved.length, saved.join(" | "));
      }
      await context.close();
    }
  }
} catch (error) {
  check("the run completed without an exception", false, String(error).slice(0, 300));
} finally {
  await browser.close().catch(() => {});
  writeResults();
}

function writeResults() {
  writeFileSync(join(EVIDENCE, "results.json"), JSON.stringify({ failures, results }, null, 1));
  console.log(`\n${results.length - failures} of ${results.length} checks passed. Evidence: ${EVIDENCE}`);
}
process.exit(failures === 0 ? 0 : 1);
