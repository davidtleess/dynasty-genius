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
import { PlayerCardDrawer } from "../player/PlayerCardDrawer";
import { PlayerDetailCard } from "../player/PlayerDetailCard";
import { PlayerDetailPage } from "../player/PlayerDetailPage";
import { RealizedOutcomeScorecard } from "../realized-outcome/RealizedOutcomeScorecard";
import { RosterAudit } from "../roster/RosterAudit";
import { RosterCapacitySandbox } from "../roster-capacity/RosterCapacitySandbox";
import { ParkedSurfaceCard } from "../shell/ParkedSurfaceCard";
import { TrustStrip } from "../shell/TrustStrip";
import { SystemHealthCard } from "../system-health/SystemHealthCard";
import { MarketLanePanel } from "../trade/MarketLanePanel";
import { ModelLanePanel } from "../trade/ModelLanePanel";
import { TradeLab } from "../trade/TradeLab";
import { TradePartners } from "../trade/TradePartners";
import { TradeVerdict } from "../trade/TradeVerdict";
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

  // PANEL FINDINGS on the rule itself, both proven against it before the fix.
  it("catches the plural, and reports one offender exactly once", () => {
    // The first way a term drifts is by being pluralised, and a rule that
    // rejects every suffix walked straight past it: findRawCopy("xVARs") was [].
    expect(findRawCopy("the xVARs on this roster")).toEqual(["xVARs"]);
    expect(jargonReplacement("xVARs")).toBe(VALUE_OVER_REPLACEMENT);

    // Blanking by VALUE blanked the wrong occurrence when an earlier one was
    // skipped by the lookarounds, so the real offender survived into the shout
    // pass and was named twice: findRawCopy("myXVAR XVAR") gave
    // ["XVAR","XVAR"] for one offender. Blanking AT THE MATCH ends that.
    expect(findRawCopy("myXVAR XVAR")).toEqual(["XVAR"]);
    // Two genuine offenders are still two findings — and "2XVAR" is one of
    // them, not a duplicate of its neighbour: the shout pattern's lookbehind
    // excludes a preceding LETTER only, so a digit-prefixed shout is a raw
    // token in its own right and the rule is right to name it.
    expect(findRawCopy("ENGINE_B and XVAR")).toEqual(["ENGINE_B", "XVAR"]);
    expect(findRawCopy("2XVAR and XVAR")).toEqual(["XVAR", "XVAR"]);
  });

  it("exempts declared identifiers and the league's own words, and nothing else", () => {
    const host = document.createElement("div");
    host.innerHTML = `
      <p>engine_b_not_decision_grade</p>
      <p data-receipt>artifact <span data-identifier>pvo_refresh</span></p>
      <h4 data-user-text>MDEF</h4>
      <span data-identifier><em>nested_raw_key</em></span>
    `;
    const findings = auditRenderedCopy(host);
    expect(findings.map((f) => f.token)).toEqual(["engine_b_not_decision_grade"]);
  });

  // ── DG-120: identifiers vs messages inside a receipt ──────────────────────
  //
  // The DG-109 exemption was doing double duty. `[data-receipt]` said "raw text
  // lives here" and the audit skipped the whole subtree, so a STATUS MESSAGE
  // nobody had written in English rode in under the same declaration that
  // legitimately protects a file path. One click on the header pill put
  // `roster_capacity: live_precondition_not_ok:capture_health_ok=degraded` on
  // David's screen, and the rule that exists to stop exactly that was blind to
  // it by construction.
  //
  // The split the rule now enforces: an IDENTIFIER is an address — a path, an
  // artifact id, a run id, a hash, a git sha, a schema version — and rewording
  // it destroys the thing it names, so it is declared `data-identifier` and
  // kept byte-exact. A MESSAGE is a sentence — a status, a reason, a condition,
  // a count — and there is no address in it to destroy, so it goes through the
  // dictionary like every other sentence in the product.
  //
  // `[data-receipt]` survives as the LAYER marker (it is what the health card's
  // provenance rows are), but it no longer grants an exemption. A component can
  // no longer buy silence by calling itself a receipt; it has to point at the
  // exact bytes that are an address.
  it("fails a snake_case MESSAGE inside a receipt and spares the identifier beside it", () => {
    const host = document.createElement("div");
    host.innerHTML = `
      <div data-receipt>
        <span data-identifier>app/data/model_capture/pvo_refresh_latest_report.json</span>
        <span data-identifier>scripts/run_pvo_refresh.py</span>
        <span>live_precondition_not_ok:capture_health_ok=degraded</span>
      </div>
    `;
    const findings = auditRenderedCopy(host);
    expect(
      findings.map((f) => f.token),
      `the receipt exemption still swallowed a message:\n${formatRawCopyFindings(findings)}`,
    ).toEqual(["live_precondition_not_ok", "capture_health_ok"]);
  });

  // The four strings the 2026-08-30 closeout audit measured on David's screen,
  // each one a sentence someone declined to write. Every one of them must be
  // seen by the rule when it sits inside a receipt undeclared.
  it("sees each string the closeout audit found behind the receipt exemption", () => {
    const measured = [
      "roster_capacity: live_precondition_not_ok:capture_health_ok=degraded",
      "2 of 3 stores degraded — model_forward_capture: missing 1 of 67 days (2026-08-12)",
      "adapter_status:ok",
      "mtime_fresh",
    ];
    for (const message of measured) {
      const host = document.createElement("div");
      const receipt = document.createElement("div");
      receipt.setAttribute("data-receipt", "");
      receipt.textContent = message;
      host.appendChild(receipt);
      expect(
        auditRenderedCopy(host).length,
        `a receipt hid this from the rule: ${message}`,
      ).toBeGreaterThan(0);
    }
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

  // DG-120 — THE SECOND RECEIPT ONE CLICK FROM DAVID. The health sheet under
  // "Details" on the front page is shut on arrival, so neither this test nor
  // the browser gate had ever rendered it; both mounts above audit clean for
  // free. Opened, on the degraded fixture, it printed
  //   Feed status: degraded · market ok · model model_multi_vintage_ambiguous
  //   · producer reasons, verbatim: model_multi_vintage_ambiguous
  // — a raw enum three times over, on the surface the nav opens on, behind a
  // `data-receipt` that exempted the whole paragraph. The sheet is opened here
  // in both feed states so it can never go unlooked-at again.
  it.each([
    ["quiet", whatChangedLive],
    ["degraded", whatChangedDegradedLive],
  ])("holds inside the front page's health sheet (%s feed)", async (label, fixture) => {
    mockRoutes({ "/api/league/what-changed": fixture as Wire });

    const { container } = render(<DailyWhatChanged />);
    await screen.findByRole("region", { name: /daily what-changed/i });
    screen.getByTestId("wc-health-sheet-toggle").click();
    await screen.findByTestId("wc-health-sheet");

    expectClean(container, `Daily What-Changed health sheet (${label} feed)`);
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

  // The verdict block reads the per-asset `signal_label` enum, and the strip it
  // replaced rendered those keys straight to the screen — `inside_band` was on
  // the live surface under a drafted trade. It was never in this audit, which
  // is exactly how it survived; it is now.
  it("holds on the Trade Lab verdict for every divergence signal", () => {
    const overlay = (label: string, signal: string) =>
      ({
        asset_ref: {
          asset_kind: "player",
          decision_supported: false,
          player_id: "100",
          sleeper_id: "100",
        },
        caveats: [],
        coverage_gap: null,
        decision_supported: false,
        divergence_context: {
          caveats: [],
          decision_supported: false,
          percentile_delta: 0.32,
          sigma_threshold: 0.25,
          signal_label: signal,
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
      }) as Wire;

    const side = (value: number) => ({
      assets: [],
      caveats: [],
      side_value: value,
      unpriced_count: 0,
    });
    const model = {
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
        side_a: side(41.2),
        side_b: side(39.1),
        within_parity_band: false,
      },
      caveats: [],
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
    } as Wire;

    for (const signal of [
      "model_higher_than_market",
      "model_lower_than_market",
      "inside_band",
      "unavailable",
    ]) {
      const market = {
        adjusted_market_received: 7100,
        adjusted_market_sent: 8400,
        caveats: [],
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
        realism_warnings: [],
        received_assets: [overlay("De'Von Achane", signal)],
        sent_assets: [overlay("Jaxson Dart", signal)],
        source_timestamp: null,
      } as Wire;

      const verdict = render(<TradeVerdict model={model} market={market} />);
      expectClean(verdict.container, `Trade Lab verdict (${signal})`);
      verdict.unmount();

      // DG-116 panel fixes added three states in which a lane is not allowed a
      // direction, and each one builds its sentence out of producer material:
      // the unscored caveat (which carries the raw key `PRE_MODEL` and a
      // Sleeper id), the capacity range, and an unpriced asset's label. All
      // three go through the audit here rather than being trusted.
      const unscored = render(
        <TradeVerdict
          model={
            {
              ...model,
              adjusted_david_received_value: 0,
              base_evaluation: {
                ...model.base_evaluation,
                caveats: ["100: unscored (PRE_MODEL) — excluded from trade math"],
                side_b: side(0),
              },
            } as Wire
          }
          market={market}
        />,
      );
      expectClean(unscored.container, `Trade Lab verdict, unscored (${signal})`);
      unscored.unmount();

      const uncertain = render(
        <TradeVerdict
          model={
            {
              ...model,
              adjusted_favors_status: "uncertain_range_crosses_parity",
              adjusted_received_value_range: [30.68, 2.85],
            } as Wire
          }
          market={market}
        />,
      );
      expectClean(uncertain.container, `Trade Lab verdict, uncertain (${signal})`);
      uncertain.unmount();

      const unpriced = render(
        <TradeVerdict
          model={model}
          market={
            {
              ...market,
              received_assets: [
                { ...overlay("2027 Round 1 Pick", signal), market_value: null },
              ],
            } as Wire
          }
        />,
      );
      expectClean(unpriced.container, `Trade Lab verdict, unpriced (${signal})`);
      unpriced.unmount();
    }
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

  // DG-114 moved Partner Rankings off League Pulse and onto Trades, so the
  // League Pulse mount above no longer covers those cards. They are covered
  // here instead — the panel is unchanged, only its address moved.
  it("holds on the trade partners view with live data", async () => {
    mockRoutes({ "/api/league/pulse": leaguePulseLive as Wire });

    const { container } = render(<TradePartners />);
    await screen.findByLabelText(/who to call/i);

    expectClean(container, "Trade partners");
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

  it("holds on the player card drawer, which frames every player read", async () => {
    mockRoutes({ "/api/players/12508": playerDetailLive as Wire });

    const { container } = render(
      <PlayerCardDrawer onClose={() => {}}>
        <PlayerDetailPage sleeperId="12508" />
      </PlayerCardDrawer>,
    );
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull());

    expectClean(container, "player card drawer");
  });

  it("holds on the data-freshness card with live data", async () => {
    mockRoutes({ "/api/health": systemHealthLive as Wire });

    const { container } = render(<SystemHealthCard now={new Date("2026-08-30")} />);
    await screen.findByText(/data freshness/i);

    expectClean(container, "System health card");
  });

  // DG-120. The card above is the surface one click behind "Attention — details
  // inside", and until now its receipts were the ONE place the rule could not
  // see. These two assertions are the ticket's honesty law in test form:
  // translation, not deletion. The messages are gone as machinery; every
  // identifier they sat beside is still on screen, byte for byte.
  it("keeps every receipt identifier byte-exact while its messages become prose", async () => {
    mockRoutes({ "/api/health": systemHealthLive as Wire });

    const { container } = render(<SystemHealthCard now={new Date("2026-08-30")} />);
    await screen.findByText(/data freshness/i);
    const text = (container as HTMLElement).innerText ?? container.textContent ?? "";

    // Every ADDRESS the payload carries still reaches the screen unaltered.
    for (const report of (systemHealthLive as Wire).reports) {
      expect(text, `the artifact id left the receipt: ${report.artifact_id}`).toContain(
        report.artifact_id,
      );
      expect(text, `the producer left the receipt: ${report.producer}`).toContain(
        report.producer,
      );
      expect(text, `the file path left the receipt: ${report.artifact_path}`).toContain(
        report.artifact_path,
      );
    }
    for (const subsystem of (systemHealthLive as Wire).subsystems) {
      expect(
        text,
        `the guard id left the receipt: ${subsystem.subsystem_id}`,
      ).toContain(subsystem.subsystem_id);
    }

    // And every MESSAGE the closeout audit measured is gone as machinery. The
    // FACTS inside them are asserted separately, in SystemHealthCard.test.tsx.
    for (const machinery of [
      "live_precondition_not_ok",
      "adapter_status:ok",
      "mtime_fresh",
      "embedded_timestamp_fresh",
      "past_grace",
      "timestamp_source:mtime_fallback",
      "core_substrate",
      "daily_diagnostics",
    ]) {
      expect(
        text,
        `a pipeline message survived in a receipt: ${machinery}`,
      ).not.toContain(machinery);
    }
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
