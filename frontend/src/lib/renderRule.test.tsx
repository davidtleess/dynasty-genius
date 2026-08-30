// @vitest-environment jsdom
//
// DG-109 — the enforcement test. This is the deliverable as much as the strings
// are: it mounts the real surfaces against REAL captured payloads and fails if
// any component prints a raw pipeline key. A future component that renders
// `evidence.caveats` straight, or adds a `<dt>{key}</dt>`, breaks this test.
//
// The fixtures in ./__fixtures__ were captured read-only from the live product
// (http://127.0.0.1:8000) on 2026-08-30 and trimmed only by shortening row
// arrays — no string was edited, so every token the audit sees is a token David
// can see. Capture commands are recorded in the DG-109 close-out.
//
// ── WHAT THE REVIEW PANEL CHANGED HERE ──────────────────────────────────────
//
// The first version of this file mounted seven components and claimed a
// product-wide rule. A refuter drove the built bundle in a real browser and
// found raw keys on FOUR of the ten nav surfaces the test does not mount —
// Roster Audit (79), Model Trust (11, including the exact two strings the second
// commit called "the last two pipeline keys on David's screen"), Accuracy
// Tracker (1) and the parked cards. The claim was false, and the test was the
// reason nobody knew. So the coverage now follows the nav rail: EVERY entry in
// AppShell's ACTIVE_SURFACES, plus the parked cards and the shell strip.
//
// Two structural holes are closed with it:
//
//   1. A component could EARN the receipt exemption by failing — the unmapped
//      fallback stamped `data-receipt` onto a body-copy risk bullet, so the
//      audit skipped exactly the node it existed to catch. Unmapped tokens now
//      go to a receipt paragraph of their own and never onto body copy.
//
//   2. Humanizing an unmapped token is INVISIBLE to a DOM audit — "Model multi
//      vintage ambiguous" contains no underscore and no shout, so it passes the
//      rule while reading as broken English that can be mistaken for a claim
//      (the DG-043 bug). The dictionary already warns on the console for those;
//      this test now FAILS on the warning. That is what makes the rule a rule
//      about the dictionary being complete, not just about underscores.
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { LeaguePulse } from "../league-pulse/LeaguePulse";
import { ModelScoreboard } from "../model-scoreboard/ModelScoreboard";
import { PlayerDetailCard } from "../player/PlayerDetailCard";
import { PlayerInspector } from "../player/PlayerInspector";
import { RealizedOutcomeScorecard } from "../realized-outcome/RealizedOutcomeScorecard";
import { RosterAudit } from "../roster/RosterAudit";
import { RosterCapacitySandbox } from "../roster-capacity/RosterCapacitySandbox";
import { ParkedSurfaceCard } from "../shell/ParkedSurfaceCard";
import { TrustStrip } from "../shell/TrustStrip";
import { SystemHealthCard } from "../system-health/SystemHealthCard";
import { MarketLanePanel } from "../trade/MarketLanePanel";
import { ModelLanePanel } from "../trade/ModelLanePanel";
import { TradeLab } from "../trade/TradeLab";
import { TrustConsole } from "../trust/TrustConsole";
import { DailyTape } from "../ui/DailyTape";
import { DailyWhatChanged } from "../what-changed/DailyWhatChanged";
import leaguePulseLive from "./__fixtures__/leaguePulse.live.json";
import modelCardLive from "./__fixtures__/modelCard.live.json";
import modelScoreboardLive from "./__fixtures__/modelScoreboard.live.json";
import playerDetailLive from "./__fixtures__/playerDetail.live.json";
import realizedOutcomeLive from "./__fixtures__/realizedOutcome.live.json";
import rosterAuditLive from "./__fixtures__/rosterAudit.live.json";
import rosterCapacityLive from "./__fixtures__/rosterCapacity.live.json";
import systemHealthLive from "./__fixtures__/systemHealth.live.json";
import trustSurfaceLive from "./__fixtures__/trustSurface.live.json";
import whatChangedLive from "./__fixtures__/whatChanged.live.json";
import whatChangedDegradedLive from "./__fixtures__/whatChangedDegraded.live.json";
import { VALUE_OVER_REPLACEMENT } from "./copy";
import {
  auditRenderedCopy,
  findRawCopy,
  formatRawCopyFindings,
  jargonReplacement,
} from "./renderRule";

// biome-ignore lint/suspicious/noExplicitAny: fixtures are captured wire payloads; the components' own Zod parse is the contract check under test.
type Wire = any;

function mockRoutes(routes: Record<string, unknown>) {
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    const body = routes[url];
    if (body === undefined) {
      return { ok: false, status: 503, json: async () => ({}) } as Response;
    }
    return { ok: true, status: 200, json: async () => body } as unknown as Response;
  }) as typeof fetch;
}

// Every dictionary miss warns with this prefix (copy.ts). A miss is a real
// defect even when the DOM audit passes, because `describeToken` humanizes an
// unmapped token straight into body copy.
let warn: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  warn = vi.spyOn(console, "warn").mockImplementation(() => {});
});

function unmappedTokens(): string[] {
  return (warn.mock.calls as unknown[][])
    .filter((call) => String(call[0]).startsWith("Copy dictionary:"))
    .map((call) => `${String(call[0])} ${String(call[1])}`);
}

function expectClean(root: Element, surface: string) {
  const findings = auditRenderedCopy(root);
  expect(
    findings,
    `${surface} leaked raw pipeline keys to the screen:\n${formatRawCopyFindings(findings)}`,
  ).toEqual([]);
  const misses = unmappedTokens();
  expect(
    misses,
    `${surface} rendered tokens the dictionary has no entry for, so they were humanized into prose nobody wrote:\n  ${misses.join("\n  ")}`,
  ).toEqual([]);
}

afterEach(() => vi.restoreAllMocks());

describe("the render rule: no raw pipeline key reaches the DOM", () => {
  it("flags underscore keys and shouted tokens, and leaves plain prose alone", () => {
    expect(findRawCopy("age_not_near_position_cliff")).toEqual([
      "age_not_near_position_cliff",
    ]);
    expect(findRawCopy("Signal completeness 83% — missing: ppg_t_minus_1")).toEqual([
      "ppg_t_minus_1",
    ]);
    expect(findRawCopy("REBUILDING")).toEqual(["REBUILDING"]);
    // One offender, one line to fix — not ENGINE_B plus its shouted halves.
    expect(findRawCopy("ENGINE_B")).toEqual(["ENGINE_B"]);
    // Fantasy vocabulary a manager reads as English survives untouched.
    expect(findRawCopy("QB · Giants · 22 years old")).toEqual([]);
    expect(
      findRawCopy("Age is on his side — years from the usual QB decline."),
    ).toEqual([]);
  });

  // DG-117. The shape patterns above are blind to a term that looks like a
  // word: "xVAR" is three capitals under a four-capital floor and carries no
  // underscore, so it walked through the whole DG-109 dictionary pass and ended
  // up with FOUR spellings of one quantity on David's screen. The jargon list
  // is the rule that can see it, and the dictionary is where the one name lives.
  it("names jargon the shape patterns cannot see, and says what to use instead", () => {
    expect(findRawCopy("Value above replacement (xVAR)")).toEqual(["xVAR"]);
    expect(findRawCopy("xVAR bracket")).toEqual(["xVAR"]);
    // Case-insensitive: no spelling of it is the agreed name.
    expect(findRawCopy("xvar 0.0+")).toEqual(["xvar"]);
    expect(findRawCopy("XVAR")).toEqual(["XVAR"]);
    // The one name, and only that one, passes.
    expect(findRawCopy(VALUE_OVER_REPLACEMENT)).toEqual([]);
    expect(jargonReplacement("xVAR")).toBe(VALUE_OVER_REPLACEMENT);
    // Whole word only — a player named Xavier is not machinery, and an
    // underscore key is still reported once, as the key it is.
    expect(findRawCopy("Xavier Legette · WR")).toEqual([]);
    expect(findRawCopy("asset_xvar")).toEqual(["asset_xvar"]);
  });

  it("exempts the receipt layer and the league's own words, and nothing else", () => {
    const host = document.createElement("div");
    host.innerHTML = `
      <p>engine_b_not_decision_grade</p>
      <p data-receipt>artifact pvo_refresh</p>
      <h4 data-user-text>MDEF</h4>
      <span data-receipt><em>nested_raw_key</em></span>
    `;
    const findings = auditRenderedCopy(host);
    expect(findings.map((f) => f.token)).toEqual(["engine_b_not_decision_grade"]);
  });

  // ── The nav rail, surface by surface ──────────────────────────────────────

  it("holds on the front page (Daily What-Changed) with live data", async () => {
    mockRoutes({ "/api/league/what-changed": whatChangedLive as Wire });

    const { container } = render(<DailyWhatChanged />);
    await screen.findByRole("region", { name: /daily what-changed/i });

    expectClean(container, "Daily What-Changed");
  });

  // The regression the panel caught. The fixture above is a QUIET day: its
  // `comparison_window` has no `status` and both `aborted_reason`s are absent,
  // so the branch that leaked never rendered. This one is the SAME endpoint
  // captured while the feed was degraded — `model_multi_vintage_ambiguous`, the
  // key that was on David's screen on 2026-08-30 — so the degraded render state
  // is covered too.
  it("holds on the front page when the model feed is degraded", async () => {
    mockRoutes({ "/api/league/what-changed": whatChangedDegradedLive as Wire });

    const { container } = render(<DailyWhatChanged />);
    await screen.findByRole("region", { name: /daily what-changed/i });

    expect(
      (whatChangedDegradedLive as Wire).daily_diff.model.comparison_window.status,
    ).toBe("model_multi_vintage_ambiguous");
    expectClean(container, "Daily What-Changed (degraded model feed)");
  });

  it("holds on Roster Audit with live data", async () => {
    mockRoutes({ "/api/roster/audit": rosterAuditLive as Wire });

    const { container } = render(<RosterAudit />);
    await screen.findByLabelText(/roster audit status/i);
    // The per-player detail rows are collapsed by default and carry the drivers,
    // risk flags and caveats, so the audit has to see them opened.
    // DG-110 renamed this control's accessible name to "Details for <player>"
    // so it contains its own visible word. The audit must still OPEN every row
    // — the drivers, risk flags and caveats it inspects live behind them.
    const detailControls = screen.getAllByRole("button", { name: /^Details for / });
    expect(detailControls.length).toBeGreaterThan(0);
    for (const button of detailControls) {
      button.click();
    }
    await waitFor(() => expect(screen.getAllByRole("row").length).toBeGreaterThan(1));

    expectClean(container, "Roster Audit");
  });

  it("holds on Trade Lab with live data", async () => {
    mockRoutes({ "/api/trade/assets": { assets: [] } });

    const { container } = render(<TradeLab />);
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull());

    expectClean(container, "Trade Lab");
  });

  // Trade Lab renders its lanes ONLY with a drafted trade, so the empty-draft
  // mount above audits clean for free — which is precisely how the two lane
  // panels kept `reconciliation.caveats` and `coverage_gaps` raw through the
  // first pass. The panels are mounted directly, with the same reconciliation
  // shapes the lane tests use, so that hole cannot reopen.
  it("holds on the Trade Lab lanes with a drafted trade", () => {
    const market = {
      adjusted_market_received: 7100,
      adjusted_market_sent: 8400,
      caveats: ["market_overlay_display_only", "decision_supported_false"],
      counterparty_forced_cut_penalty: null,
      counterparty_market_penalty_status: "not_requested",
      coverage_gaps: ["fantasycalc_uncovered"],
      david_forced_cut_penalty: null,
      decision_supported: false,
      format_key: "dynasty_sf_ppr",
      market_delta_for_david: -1300,
      market_received_raw: 7100,
      market_sent_raw: 8400,
      realism_warnings: [
        { warning_type: "value_gap", severity: "advisory", message: "Wide value gap." },
      ],
      received_assets: [],
      sent_assets: [],
      source: "fantasycalc",
      source_timestamp: "2026-05-24T17:19:44Z",
    } as Wire;

    const { container } = render(<MarketLanePanel reconciliation={market} />);
    expectClean(container, "Trade Lab market lane");

    const side = (value: number) => ({
      assets: [],
      caveats: [],
      side_value: value,
      unpriced_count: 0,
    });
    const model = {
      base_evaluation: {
        caveats: [],
        decision_supported: false,
        fairness_delta: 2.1,
        favors: "david",
        favors_xvar_margin: 2.1,
        side_a: side(41.2),
        side_b: side(39.1),
        within_parity_band: true,
      },
      caveats: ["no_market_overlay", "engine_b_not_decision_grade"],
      decision_supported: false,
      received_assets: [],
      roster_penalty: {
        decision_supported: false,
        forced_cut_candidates: [],
        forced_cut_penalty_xvar: 3.1,
        forced_cut_recovery_range: [1.2, 2.3],
        forced_cut_value_at_risk_range: [0.8, 1.9],
        penalty_caveats: ["market_replacement_pool_stale"],
        penalty_status: "ok",
        pool_deficits: {},
        post_trade_overflow: 1,
        post_trade_total_players: 25,
      },
      sent_assets: [],
    } as Wire;

    const modelLane = render(<ModelLanePanel reconciliation={model} />);
    expectClean(modelLane.container, "Trade Lab model lane");
  });

  it("holds on Roster Capacity with live data", async () => {
    mockRoutes({ "/api/roster/capacity": rosterCapacityLive as Wire });

    const { container } = render(<RosterCapacitySandbox />);
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull());

    expectClean(container, "Roster Capacity");
  });

  it("holds on the league surfaces with live data", async () => {
    mockRoutes({ "/api/league/pulse": leaguePulseLive as Wire });

    const { container } = render(<LeaguePulse />);
    await screen.findByTestId("league-pulse-ready");

    expectClean(container, "League Pulse");
  });

  it("holds on the Model Trust console with live data", async () => {
    mockRoutes({
      "/api/trust-surface/QB": trustSurfaceLive as Wire,
      "/api/trust-surface/QB/model-card": modelCardLive as Wire,
    });

    const { container } = render(<TrustConsole />);
    await screen.findByText(/trust data loaded/i);

    expectClean(container, "Model Trust console");
  });

  it("holds on the Accuracy Tracker with live data", async () => {
    mockRoutes({
      "/api/model-scoreboard": modelScoreboardLive as Wire,
      "/api/realized-outcome/scorecard": realizedOutcomeLive as Wire,
    });

    const { container } = render(
      <div>
        <ModelScoreboard />
        <RealizedOutcomeScorecard />
      </div>,
    );
    await screen.findByLabelText(/diagnostic scorecard/i);

    expectClean(container, "Accuracy Tracker");
  });

  it("holds on the parked surface cards, which exist to be read", () => {
    for (const surface of ["Rookie Board", "Waiver Radar", "Research Assistant"]) {
      const { container } = render(<ParkedSurfaceCard surface={surface} />);
      expectClean(container, `Parked card (${surface})`);
    }
  });

  // ── The player card and the shell furniture that rides every surface ───────

  it("holds on the player card with live data", () => {
    const { container } = render(
      <PlayerDetailCard detail={playerDetailLive as Wire} />,
    );
    expectClean(container, "player card");
  });

  it("holds on the player inspector with live data", async () => {
    mockRoutes({ "/api/players/12508": playerDetailLive as Wire });

    const { container } = render(
      <PlayerInspector
        player={{ sleeperId: "12508", label: "Jaxson Dart" }}
        onClose={() => {}}
      />,
    );
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull());

    expectClean(container, "player inspector");
  });

  it("holds on the data-freshness card with live data", async () => {
    mockRoutes({ "/api/health": systemHealthLive as Wire });

    const { container } = render(<SystemHealthCard now={new Date("2026-08-30")} />);
    await screen.findByText(/data freshness/i);

    expectClean(container, "System health card");
  });

  it("holds on the trust strip, which rides every surface, with live data", async () => {
    mockRoutes({ "/api/trust-surface/QB": trustSurfaceLive as Wire });

    const { container } = render(<TrustStrip position="QB" />);
    await screen.findByText(/^In use/);

    expectClean(container, "Trust strip");
  });

  it("holds on the daily tape in both its states", () => {
    const ready = render(
      <DailyTape
        capture={{ consecutiveDays: 52, lastCaptureAt: "2026-08-29", status: "ok" }}
        provenance={{ registryVersion: 3, modelVintage: "ok", status: "ok" }}
      />,
    );
    expectClean(ready.container, "Daily tape (fresh)");

    const degraded = render(
      <DailyTape
        capture={{ consecutiveDays: 0, lastCaptureAt: "", status: "unavailable" }}
        provenance={{
          registryVersion: 0,
          modelVintage: "unavailable",
          status: "degraded",
        }}
      />,
    );
    expectClean(degraded.container, "Daily tape (degraded)");
  });
});
