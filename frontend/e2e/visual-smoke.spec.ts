// ─────────────────────────────────────────────────────────────────────────────
// THE BROWSER EVIDENCE GATE — DG-118.
//
// WHAT THIS FILE IS FOR. Everything DG-091 phase 2B built is CSS, layout,
// semantics and copy: things no jsdom test can see. Until this ticket the gate
// that was supposed to protect them visited three URLs — `?surface=what-changed`,
// `?surface=asset-primitive-capture`, `?surface=accuracy-tracker` — and EVERY
// defect the program fixed lived somewhere else: Trade Lab's unbuilt priced
// state, Roster Audit's 185px sideways scroll at 390, Model Trust's 665px. A
// gate that cannot see the breakage it exists to prevent is worse than no gate,
// because it writes a receipt.
//
// ── WHAT IS GATED, EXACTLY ───────────────────────────────────────────────────
//
// COVERED. Every view of every destination in `destinations.ts` — Today, Roster
// (All players + Cut list), Trades (Build a trade + Trade partners), League,
// Track record (Model trust + Accuracy tracker) — at 1440 AND 390, plus two
// states a surface only reaches by being USED (Trade Lab priced, Roster Audit
// with every detail row open) and the developer capture target. The surface
// table is keyed by the `Surface` type and checked against `DESTINATIONS` at
// module load, so adding a destination without gating it fails this file rather
// than quietly widening the blind spot again.
//
// On each of those, at each width, the gate asserts:
//   · content is actually on the screen (see THE FALSE RECEIPT below),
//   · the PAGE does not scroll sideways,
//   · axe reports zero violations, using AXE'S OWN COMPOSITED COLOURS,
//   · no raw pipeline token reached visible text (the DG-109 render rule,
//     re-run in a real browser against the built bundle),
//   · every network read the surface made was fixtured — an unmocked endpoint
//     fails instead of degrading quietly,
// and archives a full-page screenshot and a mid-scroll screenshot as evidence.
//
// NOT COVERED, and these are the honest edges:
//   · The three parked cards, the Project Tracker and the player-card drawer are
//     reachable by URL and are NOT gated here. They are covered in jsdom by
//     `src/lib/renderRule.test.tsx` for copy, and by nothing for layout. (Rookie
//     Board measured clean at both widths on 2026-08-30 — that is a measurement,
//     not a guarantee this file will keep.)
//   · Every disclosure that is closed by default stays closed, except Roster
//     Audit's detail rows, which have their own gated state. What is inside a
//     closed receipt is jsdom's job.
//   · Light theme. `index.html` pins `data-theme="dark"`; there is no other
//     theme to visit.
//   · Real backend responses. Every surface runs on frozen fixtures captured
//     from the live product, so this gate proves the SHELL is sound, never that
//     today's data is.
//
// ── THE MOTION PATH, STATED PLAINLY ──────────────────────────────────────────
//
// BOTH paths are gated, and that is new. Every surface is scanned twice: once
// under `prefers-reduced-motion: reduce`, then reloaded under
// `no-preference` — the default path a reader actually gets — and scanned
// again. Screenshots come from the reduce path only, because that is the
// deterministic one.
//
// Running axe on the default path is exactly what made the old gate a coin flip
// (3 pass / 4 fail over 7 runs on one unchanged tree, DG-105): axe computes
// styles node by node while it scrolls content into view, so an entrance
// animation caught mid-run reports a phantom foreground (measured:
// --dg-text-muted #95999d at opacity 0.75 over the canvas = #767a7e, 3.97:1).
// `settleMotion()` is what makes it safe now, and it is a QUIET WINDOW rather
// than a snapshot: it waits until nothing has been animating for
// MOTION_QUIET_MS continuous milliseconds. A bare "are any animations running
// right now" check answers "no" during the 50ms delay before the daily-open
// entrance starts, which is the same race by a shorter name.
//
// NO axe RULE IS EXCLUDED ANYWHERE IN THIS FILE. `assertContrastRuleRan()`
// proves it for the one rule most likely to be switched off under pressure.
//
// ── THE FALSE RECEIPT ────────────────────────────────────────────────────────
//
// A surface whose backend is unavailable renders an error card: no rows, a
// sentence, and a small, clean axe count. That looks like a pass and is the
// most dangerous output this file can produce. Three independent assertions
// stand against it, because three separate measurement errors this weekend all
// had the same shape — a reading taken without checking the conditions behind
// it:
//   1. `ready` — a locator that exists ONLY in the loaded state, never in the
//      loading, unavailable, config-error or parse-error state.
//   2. `content` — a minimum count of real content nodes, plus a floor on the
//      visible text in <main>. A fixture that goes stale against the generated
//      Zod schema lands in `parse-error` with a two-line card; both of these
//      catch it. (That is not hypothetical: this file's own hand-written
//      capture-health fixture had drifted from the schema and had been silently
//      parse-erroring on the front page for some time. It is a captured live
//      fixture now.)
//   3. `assertEveryReadFixtured` — a catch-all route records any /api/ request
//      no fixture answered and fails the test by name, so a surface cannot
//      quietly degrade around a new endpoint.
//
// ── AND THE CLOCK ────────────────────────────────────────────────────────────
//
// `page.clock.setFixedTime` pins the browser's Date. Two surfaces branch on
// wall-clock age (DailyWhatChanged staleness, SystemHealthCard freshness), so
// without this the gate's own result would change with the calendar.
// ─────────────────────────────────────────────────────────────────────────────
import AxeBuilder from "@axe-core/playwright";
import type { AxeResults, Result as AxeViolation } from "axe-core";
import { expect, type Locator, type Page, test } from "@playwright/test";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";

import {
  findRawCopy,
  formatRawCopyFindings,
  jargonReplacement,
} from "../src/lib/renderRule";
import { DESTINATIONS } from "../src/shell/destinations";
import { type Surface, slugForSurface } from "../src/shell/useUrlSurfaceState";

const ARTIFACT_DIR = "artifacts/visual";

/** The instant every surface is rendered at. See "AND THE CLOCK" above. */
const FIXED_CLOCK = new Date("2026-08-30T20:30:00Z");

/**
 * How long nothing may be animating before a scan is allowed to start. The
 * longest animation in the tree is 240ms (`--dg-duration-moderate-02`) and the
 * longest delay 50ms, so 400ms of continuous quiet cannot land inside one.
 */
const MOTION_QUIET_MS = 400;

const WIDTHS = [
  { width: 1440, height: 960, label: "desktop" },
  { width: 390, height: 844, label: "mobile" },
] as const;

// ── Fixtures ────────────────────────────────────────────────────────────────
// Captured read-only from the running product and frozen. The same files the
// jsdom render-rule test reads, so the two gates cannot disagree about what the
// product was handed.
function fixture(name: string): unknown {
  return JSON.parse(
    readFileSync(new URL(`../src/lib/__fixtures__/${name}`, import.meta.url), "utf8"),
  );
}

const LIVE = {
  captureHealth: fixture("captureHealth.live.json"),
  health: fixture("systemHealth.live.json"),
  leaguePulse: fixture("leaguePulse.live.json"),
  modelCard: fixture("modelCard.live.json"),
  modelProvenance: fixture("modelProvenance.live.json"),
  modelScoreboard: fixture("modelScoreboard.live.json"),
  realizedOutcome: fixture("realizedOutcome.live.json"),
  rosterAudit: fixture("rosterAudit.live.json"),
  rosterCapacity: fixture("rosterCapacity.live.json"),
  trustSurface: fixture("trustSurface.live.json"),
  whatChanged: fixture("whatChanged.live.json"),
};

/** Read by the shell on EVERY surface: the status pill, the trust strip. */
const SHELL_ROUTES: Record<string, unknown> = {
  "/api/health": LIVE.health,
  "/api/trust-surface/QB": LIVE.trustSurface,
  "/api/trust-surface/QB/model-card": LIVE.modelCard,
};

// Trade Lab's priced state is two POSTs, so it cannot be captured as a GET
// fixture the way the others were. These are the smallest payloads that satisfy
// the generated Zod schemas AND render every part of the rebuilt surface: a
// verdict, both lanes, a forced cut, a realism warning and a divergence signal.
// If either drifts out of schema the lane lands "unavailable" and the priced
// state's `ready` locator is missing — which is the false-receipt guard doing
// its job rather than a silent downgrade.
const tradeSide = (value: number) => ({
  assets: [],
  consolidation_factor: 1,
  side_value: value,
  xvar_sum: value,
});

const marketOverlay = (label: string, id: string) => ({
  asset_ref: {
    asset_kind: "player",
    decision_supported: false,
    player_id: id,
    sleeper_id: id,
  },
  caveats: [],
  coverage_gap: null,
  decision_supported: false,
  divergence_context: {
    caveats: [],
    decision_supported: false,
    percentile_delta: 0.32,
    sigma_threshold: 0.25,
    signal_label: "model_higher_than_market",
    source_signal_status: null,
  },
  format_key: "dynasty_sf_ppr",
  label,
  market_value: 8400,
  market_volatility: null,
  resolution: "player_sleeper_id",
  source: "fantasycalc",
  source_timestamp: null,
  trend_30d: null,
});

const MODEL_RECONCILIATION = {
  adjusted_david_received_value: 39.1,
  adjusted_fairness_delta: 2.1,
  adjusted_fairness_delta_range: [1.2, 2.3],
  adjusted_favors: "david",
  adjusted_favors_status: "david",
  adjusted_received_value_range: [38, 40],
  adjusted_within_parity_band: false,
  base_evaluation: {
    caveats: [],
    decision_supported: false,
    fairness_delta: 2.1,
    favors: "david",
    favors_xvar_margin: 2.1,
    side_a: tradeSide(41.2),
    side_b: tradeSide(39.1),
    within_parity_band: false,
  },
  caveats: ["no_market_overlay"],
  decision_supported: false,
  roster_penalty: {
    decision_supported: false,
    forced_cut_candidates: [
      { decision_supported: false, full_name: "Rasheen Ali", position: "RB" },
    ],
    forced_cut_penalty_xvar: 0,
    forced_cut_recovery_range: [1.2, 2.3],
    forced_cut_value_at_risk_range: [0.8, 1.9],
    penalty_caveats: [],
    penalty_status: "ok",
    pool_deficits: {},
    post_trade_overflow: 1,
    post_trade_total_players: 25,
  },
};

const MARKET_RECONCILIATION = {
  adjusted_market_received: 7100,
  adjusted_market_sent: 8400,
  caveats: ["market_overlay_display_only"],
  counterparty_forced_cut_penalty: null,
  counterparty_market_penalty_status: "not_requested",
  coverage_gaps: [],
  david_forced_cut_penalty: null,
  decision_supported: false,
  format_key: "dynasty_sf_ppr",
  market_delta_for_david: -1300,
  market_received_raw: 7100,
  market_sent_raw: 8400,
  market_source: "fantasycalc",
  realism_warnings: [
    {
      caveats: [],
      decision_supported: false,
      message: "One player on one side is carrying most of the value.",
      metrics: { top_asset_share: 0.82 },
      severity: "advisory",
      warning_type: "package_dilution_warning",
    },
  ],
  received_assets: [marketOverlay("De'Von Achane", "100")],
  sent_assets: [marketOverlay("Jaxson Dart", "101")],
  source_timestamp: null,
};

/** The draft Trade Lab reads out of localStorage on mount (`tradeState.ts`). */
const TRADE_DRAFT = {
  sent: [
    {
      asset_id: "player:101",
      label: "Jaxson Dart",
      kind: "player",
      model_payload: { asset_kind: "player", player_id: "101" },
      market_ref: { asset_kind: "player", sleeper_id: "101" },
    },
  ],
  received: [
    {
      asset_id: "player:100",
      label: "De'Von Achane",
      kind: "player",
      model_payload: { asset_kind: "player", player_id: "100" },
      market_ref: { asset_kind: "player", sleeper_id: "100" },
    },
  ],
  counterpartyRosterId: null,
};

// ── The surface table ───────────────────────────────────────────────────────

type GatedSurface = {
  /** The `Surface` this state belongs to — the key `DESTINATIONS` is checked against. */
  surface: Surface;
  /** Test name and failure-message subject. */
  name: string;
  /** Screenshot / axe-report basename. */
  artifacts: string;
  /** Endpoints this surface reads, on top of SHELL_ROUTES. */
  routes?: Record<string, unknown>;
  /** Run before the first navigation (seeding localStorage, etc.). */
  prepare?: (page: Page) => Promise<void>;
  /** Drive the surface into the state under test, after it has loaded. */
  drive?: (page: Page) => Promise<void>;
  /** Visible ONLY in the loaded state — never in loading/unavailable/parse-error. */
  ready: (page: Page) => Locator;
  /** Real content nodes, and the fewest of them a healthy render produces. */
  content: { selector: string; min: number };
  /** Floor on visible text in <main>. Set well under the measured value. */
  minMainText: number;
  /** Optional focus evidence: focus something and name the capture. */
  focus?: { locator: (page: Page) => Locator; artifact: string };
};

const GATED_SURFACES: GatedSurface[] = [
  {
    surface: "Daily What-Changed",
    name: "Today",
    artifacts: "daily-open",
    routes: {
      "/api/league/what-changed": LIVE.whatChanged,
      "/api/system/capture-health": LIVE.captureHealth,
      "/api/system/model-provenance": LIVE.modelProvenance,
    },
    ready: (page) => page.getByTestId("wc-verdict"),
    content: { selector: "main section", min: 4 },
    minMainText: 1200,
    // The focus ring must land on an AssetRow receipt control, not merely on
    // the shell rail — the primitive is the thing under test.
    focus: {
      locator: (page) =>
        page.getByRole("button", { name: /provenance for/i }).first(),
      artifact: "daily-open-primitive-focus-capture",
    },
  },
  {
    surface: "Roster Audit",
    name: "Roster · All players",
    artifacts: "roster-audit",
    routes: { "/api/roster/audit": LIVE.rosterAudit },
    ready: (page) => page.getByRole("region", { name: "Roster audit status" }),
    content: { selector: "main tbody tr", min: 5 },
    minMainText: 1200,
  },
  {
    // The 185px sideways scroll DG-117 fixed was on this table. The row-detail
    // panels are where the copy dictionary has the most to leak, and they are
    // shut on arrival, so the closed state above cannot see them.
    surface: "Roster Audit",
    name: "Roster · All players, every detail row open",
    artifacts: "roster-audit-expanded",
    routes: { "/api/roster/audit": LIVE.rosterAudit },
    drive: async (page) => {
      const rows = page.getByRole("button", { name: /^Details for / });
      await rows.first().waitFor({ state: "visible", timeout: 15_000 });
      const count = await rows.count();
      expect(
        count,
        "no detail rows to open — the fixture rendered no players",
      ).toBeGreaterThan(0);
      for (let index = 0; index < count; index += 1) {
        await rows.nth(index).click();
      }
    },
    ready: (page) => page.getByRole("region", { name: "Roster audit status" }),
    content: { selector: "main tbody tr", min: 10 },
    minMainText: 6000,
  },
  {
    surface: "Roster Capacity",
    name: "Roster · Cut list",
    artifacts: "roster-capacity",
    routes: { "/api/roster/capacity": LIVE.rosterCapacity },
    ready: (page) => page.getByRole("region", { name: "Roster Capacity Sandbox" }),
    content: { selector: "main tbody tr", min: 5 },
    minMainText: 1000,
  },
  {
    surface: "Trade Lab",
    name: "Trades · Build a trade (empty board)",
    artifacts: "trade-lab",
    ready: (page) => page.getByRole("region", { name: "Build a trade" }),
    content: { selector: "main li", min: 3 },
    minMainText: 600,
  },
  {
    // DG-116 rebuilt this state and no gate had ever rendered it. The first run
    // that did found a heading-order violation in it.
    surface: "Trade Lab",
    name: "Trades · Build a trade (priced)",
    artifacts: "trade-lab-priced",
    routes: {
      "/api/trade/reconcile": MODEL_RECONCILIATION,
      "/api/trade/reconcile/market": MARKET_RECONCILIATION,
    },
    prepare: async (page) => {
      await page.addInitScript(
        ([key, value]) => window.localStorage.setItem(key, value),
        ["dg.tradeLab.draft", JSON.stringify(TRADE_DRAFT)] as const,
      );
    },
    drive: async (page) => {
      await page.getByRole("button", { name: "Price this trade" }).click();
    },
    ready: (page) => page.getByTestId("trade-verdict"),
    content: { selector: '[data-testid="model-lane"], [data-testid="market-lane"]', min: 2 },
    minMainText: 1500,
  },
  {
    surface: "Trade Partners",
    name: "Trades · Trade partners",
    artifacts: "trade-partners",
    routes: { "/api/league/pulse": LIVE.leaguePulse },
    ready: (page) => page.getByRole("region", { name: "Trade partners" }),
    content: { selector: "main article", min: 1 },
    minMainText: 900,
  },
  {
    surface: "League Pulse",
    name: "League",
    artifacts: "league-pulse",
    routes: { "/api/league/pulse": LIVE.leaguePulse },
    ready: (page) => page.getByTestId("league-pulse-ready"),
    content: { selector: "main section", min: 4 },
    minMainText: 3500,
  },
  {
    // The 665px sideways scroll DG-117 fixed was on this surface's fold table.
    surface: "Model Trust",
    name: "Track record · Model trust",
    artifacts: "model-trust",
    ready: (page) => page.getByText("Trust data loaded", { exact: true }),
    content: { selector: "main tbody tr", min: 3 },
    minMainText: 1800,
  },
  {
    surface: "Accuracy Tracker",
    name: "Track record · Accuracy tracker",
    artifacts: "model-scoreboard",
    routes: {
      "/api/model-scoreboard": LIVE.modelScoreboard,
      "/api/realized-outcome/scorecard": LIVE.realizedOutcome,
    },
    ready: (page) => page.getByRole("region", { name: "Diagnostic Scorecard" }),
    content: { selector: "main section", min: 2 },
    minMainText: 1500,
  },
  {
    // Not a destination — the developer capture target, URL-only. Kept because
    // it is where the shared primitives are exercised in isolation.
    surface: "Asset Primitive Capture",
    name: "Asset primitive capture",
    artifacts: "asset-primitive-capture",
    ready: (page) => page.getByText("Asset primitive capture"),
    content: { selector: "main li", min: 3 },
    minMainText: 250,
    focus: {
      locator: (page) => page.getByRole("button").first(),
      artifact: "asset-primitive-capture-focus",
    },
  },
];

// THE COVERAGE LOCK. Adding a view to `destinations.ts` without adding it here
// fails the gate at load time, which is the only mechanism that keeps this file
// honest as the product grows. It is the exact hole DG-118 exists to close: the
// old gate did not know which surfaces existed, so it could not know it was
// missing seven of them.
const GATED_SURFACE_NAMES = new Set(GATED_SURFACES.map((entry) => entry.surface));
const UNGATED_DESTINATION_VIEWS = DESTINATIONS.flatMap((destination) =>
  destination.views
    .filter((view) => !GATED_SURFACE_NAMES.has(view.surface))
    .map((view) => `${destination.label} · ${view.label} (${view.surface})`),
);

test("every destination in the nav has a gated surface", () => {
  expect(
    UNGATED_DESTINATION_VIEWS,
    "these nav destinations are reachable by David and are not visited by this gate — add them to GATED_SURFACES:",
  ).toEqual([]);
});

// ── Helpers ─────────────────────────────────────────────────────────────────

/**
 * Waits until nothing has been animating for MOTION_QUIET_MS continuously.
 *
 * Quiescence, not emptiness, and a WINDOW rather than an instant. Two shapes
 * break the naive check: an animation that has not started yet (the daily-open
 * entrance has a 50ms delay, and `getAnimations()` is empty during it, so an
 * instantaneous check passes early and axe scans mid-fade), and an endless one
 * (a spinner never reaches `finished`, so waiting for it would hang until the
 * timeout and read like a contrast failure — the exact misdiagnosis this gate
 * exists to end). Neither shape exists in the tree today; both are handled so
 * the gate stays legible when one appears.
 */
async function settleMotion(page: Page): Promise<void> {
  await page.evaluate(() => {
    (window as unknown as { __dgLastBusy?: number }).__dgLastBusy = undefined;
  });
  await page.waitForFunction(
    (quietMs: number) => {
      const store = window as unknown as { __dgLastBusy?: number };
      const busy = document.getAnimations().some((animation) => {
        const timing = animation.effect?.getComputedTiming();
        const endless = timing?.iterations === Number.POSITIVE_INFINITY;
        return !endless && animation.playState !== "finished";
      });
      const now = performance.now();
      if (busy || store.__dgLastBusy === undefined) {
        store.__dgLastBusy = now;
        return false;
      }
      return now - store.__dgLastBusy >= quietMs;
    },
    MOTION_QUIET_MS,
    { polling: "raf", timeout: 10_000 },
  );
}

/**
 * THE PAGE must not scroll sideways. A wide table scrolling inside its own
 * `overflow-x: auto` container is CORRECT and is deliberately not flagged —
 * that is the DG-117 pattern (`TableScroll`), and measuring the table itself
 * would condemn the fix. What is measured is the document and the body, which
 * is what strands the rest of a 390px layout beside empty canvas.
 */
async function expectNoHorizontalOverflow(page: Page, label: string): Promise<void> {
  const metrics = await page.evaluate(() => ({
    innerWidth: window.innerWidth,
    docWidth: document.documentElement.scrollWidth,
    bodyWidth: document.body.scrollWidth,
    // Named only to make the failure actionable; never asserted on.
    widestOffender: (() => {
      let worst: { over: number; description: string } | null = null;
      for (const element of Array.from(document.querySelectorAll("body *"))) {
        const rect = element.getBoundingClientRect();
        const over = rect.right - window.innerWidth;
        if (over > 1 && (worst === null || over > worst.over)) {
          const className =
            typeof element.className === "string" ? element.className : "";
          worst = {
            over: Math.round(over),
            description: `${element.tagName.toLowerCase()}.${className}`.slice(0, 90),
          };
        }
      }
      return worst;
    })(),
  }));

  const blame =
    metrics.widestOffender === null
      ? ""
      : ` widest element past the viewport: ${metrics.widestOffender.description} (+${metrics.widestOffender.over}px)`;

  expect(
    metrics.docWidth,
    `${label}: documentElement scrolls sideways (${metrics.docWidth} > ${metrics.innerWidth}).${blame}`,
  ).toBeLessThanOrEqual(metrics.innerWidth);
  expect(
    metrics.bodyWidth,
    `${label}: body scrolls sideways (${metrics.bodyWidth} > ${metrics.innerWidth}).${blame}`,
  ).toBeLessThanOrEqual(metrics.innerWidth);
}

async function expectTrustStripPainted(page: Page): Promise<void> {
  const strip = page.getByRole("banner", { name: "Trust strip" });
  await expect(strip).toBeVisible();

  const styles = await strip.evaluate((node: HTMLElement) => {
    const computed = window.getComputedStyle(node);
    return {
      backgroundColor: computed.backgroundColor,
      backgroundImage: computed.backgroundImage,
      borderBottomColor: computed.borderBottomColor,
    };
  });

  expect(
    styles.backgroundColor,
    "Trust strip must paint an opaque surface; transparent sticky chrome lets content scroll through it.",
  ).not.toMatch(/rgba?\(\s*0\s*,\s*0\s*,\s*0\s*(?:,\s*0(?:\.0+)?)?\s*\)/i);
  expect(
    styles.backgroundColor,
    "Trust strip must not be transparent.",
  ).not.toMatch(/rgba\([^)]*,\s*0(?:\.0+)?\s*\)$/i);
  expect(styles.backgroundImage).toBe("none");
  expect(styles.borderBottomColor).not.toBe("rgba(0, 0, 0, 0)");
}

/**
 * The three-part guard against a clean-looking empty screen. See THE FALSE
 * RECEIPT in the header.
 */
async function expectContentPresent(page: Page, spec: GatedSurface): Promise<void> {
  await expect(
    spec.ready(page),
    `${spec.name}: the loaded-state marker never appeared, so this surface rendered a loading, unavailable or parse-error card. A clean axe count on an error card is a false receipt, not a pass.`,
  ).toBeVisible({ timeout: 10_000 });

  const nodes = await page.locator(spec.content.selector).count();
  expect(
    nodes,
    `${spec.name}: found ${nodes} of "${spec.content.selector}", expected at least ${spec.content.min}. The surface rendered without its content.`,
  ).toBeGreaterThanOrEqual(spec.content.min);

  const mainText = await page.evaluate(
    () => (document.querySelector("main") as HTMLElement | null)?.innerText.trim() ?? "",
  );
  expect(
    mainText.length,
    `${spec.name}: <main> holds ${mainText.length} visible characters, below the ${spec.minMainText} floor. First 200: ${JSON.stringify(mainText.slice(0, 200))}`,
  ).toBeGreaterThanOrEqual(spec.minMainText);
}

/**
 * DG-109's render rule, run in a real browser against the built bundle.
 *
 * The RULE — the patterns, the jargon list, the allowed shouts — is imported
 * from `src/lib/renderRule.ts` and never restated here, so the browser gate and
 * the jsdom gate can never drift about what counts as a raw token. What this
 * adds over jsdom is VISIBILITY: `checkVisibility()` is real layout, so a string
 * hidden by `display: none` at 390 is not audited at 390 and the rail's search
 * box (hidden on the phone) is audited at 1440 only. The two widths union to
 * cover both.
 *
 * The audit found "xVAR" had slipped the whole copy dictionary because it is
 * four characters with three capitals; the jargon list in `renderRule.ts` is
 * what sees it, and this is where it is enforced on the shipped bundle.
 */
async function expectNoRawCopy(page: Page, label: string): Promise<void> {
  const strings = await page.evaluate(() => {
    const SKIPPED_TAGS = new Set(["SCRIPT", "STYLE", "TEMPLATE"]);
    // Same exemptions the module declares: the receipt layer may cite an
    // artifact by its real name, and the league's own people may name their own
    // teams. Both are DECLARATIONS in the markup, never silent defaults.
    const EXEMPT = "[data-receipt],[data-user-text]";
    const AUDITED_ATTRIBUTES = ["aria-label", "alt", "placeholder"];
    const collected: { text: string; where: string }[] = [];

    const describe = (element: Element): string => {
      const parts: string[] = [];
      let current: Element | null = element;
      while (current !== null && parts.length < 4) {
        const className =
          typeof current.className === "string" && current.className.trim() !== ""
            ? `.${current.className.trim().split(/\s+/).join(".")}`
            : "";
        parts.unshift(`${current.tagName.toLowerCase()}${className}`);
        current = current.parentElement;
      }
      return parts.join(" > ");
    };

    const visit = (element: Element): void => {
      if (SKIPPED_TAGS.has(element.tagName)) return;
      if (element.matches(EXEMPT)) return;
      if (typeof element.checkVisibility === "function" && !element.checkVisibility())
        return;

      for (const attribute of AUDITED_ATTRIBUTES) {
        const value = element.getAttribute(attribute);
        if (value !== null && value !== "") {
          collected.push({ text: value, where: `${describe(element)} [${attribute}]` });
        }
      }
      for (const child of Array.from(element.childNodes)) {
        if (child.nodeType === 3) {
          const text = child.textContent ?? "";
          if (text.trim() !== "") collected.push({ text, where: describe(element) });
        } else if (child.nodeType === 1) {
          visit(child as Element);
        }
      }
    };

    visit(document.body);
    return collected;
  });

  expect(
    strings.length,
    `${label}: nothing visible to audit — the page was blank when the render rule ran.`,
  ).toBeGreaterThan(0);

  const findings = strings.flatMap((entry) =>
    findRawCopy(entry.text).map((token) => ({
      token,
      context: entry.text.trim().slice(0, 160),
      where: entry.where,
    })),
  );

  expect(
    findings,
    `${label} leaked raw pipeline keys to the screen:\n${formatRawCopyFindings(findings)}${findings
      .map((finding) =>
        jargonReplacement(finding.token) === undefined
          ? ""
          : `\n  ${finding.token} → say: ${jargonReplacement(finding.token)}`,
      )
      .join("")}`,
  ).toEqual([]);
}

/**
 * Reasons axe is allowed to hand back an UNDECIDED contrast reading, each with
 * the argument for why it is not a place a real failure can hide.
 *
 * Zero violations plus a pile of undecided nodes is a receipt with a hole in it,
 * so this file counts them and refuses a reason it has not accounted for. It is
 * an allowlist of REASONS, never of elements, and it disables nothing:
 *
 *   elmPartiallyObscured / elmPartiallyObscuring
 *     At 390 a wide table's right-hand cells sit outside their `overflow-x`
 *     container's visible box, and the fixed bottom tab bar overlaps content
 *     scrolled under it, so axe cannot resolve a background. MEASURED: the same
 *     nodes are DECIDED at 1440 (roster-audit and model-trust both return zero
 *     incomplete there), and the gate runs both widths, so the union covers
 *     them. If a surface ever went incomplete at 1440 this reason would still be
 *     allowed — that is this allowlist's real edge, and it is why the counts are
 *     written into the receipt rather than only checked.
 *   shortTextContent
 *     A cell holding "7". Axe declines to guess whether one character is text.
 *   nonBmp
 *     The receipt trigger's glyph: an icon with no text to contrast, carrying
 *     its meaning in `aria-label`.
 *
 * A reason NOT on this list — bgImage, bgGradient, imgNode, pseudoContent — is
 * a genuine unmeasured surface and fails.
 */
const ACCOUNTED_INCOMPLETE_REASONS = new Set([
  "elmPartiallyObscured",
  "elmPartiallyObscuring",
  "shortTextContent",
  "nonBmp",
]);

type ContrastReading = {
  target: string;
  contrastRatio: unknown;
  expectedContrastRatio: unknown;
  foreground: unknown;
  background: unknown;
};

/** Axe's OWN numbers, not getComputedStyle's. See the note on runAxe. */
function contrastReadings(violations: AxeViolation[]): ContrastReading[] {
  return violations
    .filter((violation) => violation.id === "color-contrast")
    .flatMap((violation) =>
      violation.nodes.map((node) => {
        const data = (node.any[0]?.data ?? {}) as Record<string, unknown>;
        return {
          target: node.target.join(" "),
          contrastRatio: data.contrastRatio,
          expectedContrastRatio: data.expectedContrastRatio,
          foreground: data.fgColor,
          background: data.bgColor,
        };
      }),
    );
}

/**
 * COMPOSITED COLOURS, NOT COMPUTED ONES. `getComputedStyle` reports the colour
 * an element declares; axe blends it through every ancestor's opacity, and axe
 * is right. Measured during this program: a getComputedStyle sweep reported 0
 * contrast failures on surfaces where the composited sweep found 21, one of
 * them a badge at 2.89:1 under a cumulative opacity of 0.65. So this gate runs
 * axe and quotes axe's numbers, and there is no hand-rolled colour check
 * anywhere in this file.
 */
async function runAxe(
  page: Page,
  spec: GatedSurface,
  label: string,
  reportPath: string,
): Promise<void> {
  await settleMotion(page);
  const results: AxeResults = await new AxeBuilder({ page }).analyze();

  const incompleteByReason: Record<string, number> = {};
  for (const check of results.incomplete) {
    for (const node of check.nodes) {
      const data = (node.any[0]?.data ?? node.all[0]?.data ?? {}) as Record<
        string,
        unknown
      >;
      const reason = `${check.id}:${String(data.messageKey ?? "unspecified")}`;
      incompleteByReason[reason] = (incompleteByReason[reason] ?? 0) + 1;
    }
  }

  writeFileSync(
    reportPath,
    `${JSON.stringify(
      {
        surface: spec.name,
        state: label,
        // Axe's own composited numbers for every contrast failure, so the
        // receipt records what axe measured rather than what CSS declared.
        contrast_readings: contrastReadings(results.violations),
        violation_count: results.violations.length,
        violations: results.violations,
        // Nodes axe could not decide. Zero violations plus these is a partial
        // reading, and a receipt that hid them would be the same false comfort
        // this ticket exists to end.
        incomplete_by_reason: incompleteByReason,
        rules_run: results.passes.length + results.violations.length,
        test_engine: results.testEngine,
      },
      null,
      2,
    )}\n`,
  );

  // No rule may be bought off. If `color-contrast` ever stops appearing in any
  // bucket, it was disabled, and this fails before the violation count is read.
  const exercisedRules = new Set(
    [
      ...results.passes,
      ...results.violations,
      ...results.incomplete,
      ...results.inapplicable,
    ].map((check) => check.id),
  );
  expect(
    exercisedRules.has("color-contrast"),
    `${label}: axe did not run color-contrast at all. A rule that is not running cannot fail, and buying green that way is the one thing this gate must never do.`,
  ).toBe(true);

  const unaccounted = Object.keys(incompleteByReason).filter(
    (reason) => !ACCOUNTED_INCOMPLETE_REASONS.has(reason.split(":")[1] ?? ""),
  );
  expect(
    unaccounted,
    `${label}: axe could not decide these checks and this file has no argument for them — a clean violation count with an unexplained hole in it is not a pass:\n${JSON.stringify(incompleteByReason, null, 2)}`,
  ).toEqual([]);

  expect(
    results.violations.map(
      (violation) =>
        `${violation.id} × ${violation.nodes.length}: ${violation.nodes
          .map((node) => node.target.join(" "))
          .join(", ")}`,
    ),
    `${label}: axe violations. Contrast numbers are axe's composited readings, in ${reportPath}.`,
  ).toEqual([]);
}

/** Installs the catch-all first so the specific routes registered after it win. */
async function installRoutes(page: Page, spec: GatedSurface): Promise<string[]> {
  const unfixtured: string[] = [];
  await page.route("**/api/**", async (route) => {
    unfixtured.push(new URL(route.request().url()).pathname);
    await route.fulfill({ status: 503, json: {} });
  });
  for (const [path, body] of Object.entries({ ...SHELL_ROUTES, ...spec.routes })) {
    await page.route(`**${path}`, (route) => route.fulfill({ json: body }));
  }
  return unfixtured;
}

function assertEveryReadFixtured(unfixtured: string[], label: string): void {
  expect(
    [...new Set(unfixtured)],
    `${label}: the surface read endpoints no fixture answered, so it rendered a degraded state that would otherwise have passed clean. Add them to the surface's routes.`,
  ).toEqual([]);
}

async function captureMidScroll(page: Page, path: string): Promise<void> {
  await page.evaluate(() => {
    const maxY = Math.max(
      document.documentElement.scrollHeight - window.innerHeight,
      0,
    );
    window.scrollTo(0, Math.floor(maxY * 0.45));
  });
  await page.screenshot({ path });
  await page.evaluate(() => window.scrollTo(0, 0));
}

// `drive` runs BEFORE the ready wait, not after: for the priced Trade Lab the
// verdict block does not exist until the button is pressed, so waiting for it
// first would time out on the state the gate exists to cover. Every `drive`
// therefore auto-waits on its own locators.
async function openSurface(page: Page, spec: GatedSurface): Promise<void> {
  await page.goto(`/?surface=${slugForSurface(spec.surface)}`);
  if (spec.drive !== undefined) {
    await spec.drive(page);
  }
  await expect(
    spec.ready(page),
    `${spec.name}: never reached its loaded state.`,
  ).toBeVisible({ timeout: 15_000 });
  await settleMotion(page);
}

// ── The gate ────────────────────────────────────────────────────────────────

for (const spec of GATED_SURFACES) {
  for (const viewport of WIDTHS) {
    test(`${spec.name} @ ${viewport.width}`, async ({ page }) => {
      mkdirSync(ARTIFACT_DIR, { recursive: true });
      const base = `${ARTIFACT_DIR}/${spec.artifacts}-${viewport.label}`;

      await page.clock.setFixedTime(FIXED_CLOCK);
      await page.emulateMedia({ reducedMotion: "reduce" });
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      if (spec.prepare !== undefined) {
        await spec.prepare(page);
      }
      const unfixtured = await installRoutes(page, spec);

      // ── Pass 1: reduced motion. Evidence is captured here because this is
      //    the path with no animation state to catch it mid-flight.
      const reduceLabel = `${spec.name} @ ${viewport.width} (reduced motion)`;
      await openSurface(page, spec);

      await expectContentPresent(page, spec);
      await expectNoHorizontalOverflow(page, reduceLabel);
      await expectTrustStripPainted(page);
      await expectNoRawCopy(page, reduceLabel);

      await page.screenshot({ path: `${base}.png`, fullPage: true });
      await captureMidScroll(page, `${base}-mid-scroll.png`);

      if (spec.focus !== undefined) {
        const target = spec.focus.locator(page);
        await expect(target).toBeVisible({ timeout: 5_000 });
        await target.focus();
        await expect(target).toBeFocused();
        await page.screenshot({ path: `${ARTIFACT_DIR}/${spec.focus.artifact}.png` });
      }

      await runAxe(page, spec, reduceLabel, `${base}-axe.json`);

      // ── Pass 2: the default motion path, which is what a reader without a
      //    reduced-motion preference actually gets. Same assertions, no
      //    screenshots: after settleMotion the two paths land on the same
      //    frame, and proving that is the point of running it.
      const motionLabel = `${spec.name} @ ${viewport.width} (default motion)`;
      await page.emulateMedia({ reducedMotion: "no-preference" });
      await openSurface(page, spec);

      await expectContentPresent(page, spec);
      await expectNoHorizontalOverflow(page, motionLabel);
      await expectNoRawCopy(page, motionLabel);
      await runAxe(page, spec, motionLabel, `${base}-axe-default-motion.json`);

      assertEveryReadFixtured(unfixtured, `${spec.name} @ ${viewport.width}`);
    });
  }
}
