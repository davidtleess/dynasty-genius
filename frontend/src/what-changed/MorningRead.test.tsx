// @vitest-environment jsdom
//
// DG-113 — THE MORNING READ.
//
// The test David set: one glance answers *am I ok · what moved · what should I
// look at.* These specs drive that against the REAL captured payload
// (whatChanged.live.json — the 2026-08-29 report, trimmed only by shortening
// row arrays), so every sentence they pin is a sentence David can actually see.
//
// The honesty half is the hard half and it is pinned here too: the verdict and
// the recommendation cards are ASSEMBLED sentences, and every clause has to be
// entailed by a field in that payload. `morningRead.test.ts` holds the clause-
// by-clause entailment specs; this file holds what reaches the screen.
import { render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import whatChangedLive from "../lib/__fixtures__/whatChanged.live.json";
import { DailyWhatChanged } from "./DailyWhatChanged";

// biome-ignore lint/suspicious/noExplicitAny: a captured wire payload; the surface's own Zod parse is the contract check.
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

// The fixture is a dated report. Freezing the clock an hour after it was
// generated is what makes it read as THIS morning's report rather than as a
// stale one — the staleness branch has its own specs and must not leak in here.
const FIXTURE_MORNING = new Date("2026-08-29T14:00:00+00:00");

function mountLive(overrides: (body: Wire) => void = () => {}) {
  const body = structuredClone(whatChangedLive) as Wire;
  overrides(body);
  mockRoutes({ "/api/league/what-changed": body });
  return render(<DailyWhatChanged />);
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.setSystemTime(FIXTURE_MORNING);
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("DG-113 the morning read answers am-I-ok in one glance", () => {
  it("leads with a verdict that names the one thing needing doing, from the payload's own numbers", async () => {
    mountLive();

    const verdict = await screen.findByTestId("wc-verdict");
    // whatChanged.live.json: drop_pressure.summary = 27 players, 26 capacity,
    // cuts_required 1. The verdict says that in a sentence, not as a count row.
    expect(verdict.textContent).toMatch(/one thing needs doing/i);
    expect(verdict.textContent).toMatch(/27 players/i);
    expect(verdict.textContent).toMatch(/26/);
    // …and the movement half: 3 roster rows, all three moved, Dart largest at
    // +306 to 5,082 (market.roster_deltas[0]).
    expect(verdict.textContent).toMatch(/Jaxson Dart/);
    expect(verdict.textContent).toMatch(/306/);
    expect(verdict.textContent).toMatch(/5,?082/);
  });

  it("prints up to two recommendation cards, each a verdict plus reasons from on-screen fields", async () => {
    mountLive();

    const worthALook = await screen.findByTestId("wc-worth-a-look");
    // David green-lit the named cut. drop_pressure.top_candidates[0] is
    // Rasheen Ali at cut_priority 1 with xvar_pct 36.8 — the producer's own
    // lowest-first ordering (roster_cut_engine.py:359).
    expect(worthALook.textContent).toMatch(/Rasheen Ali/);
    expect(worthALook.textContent).toMatch(/36\.8/);
    // A card is a verdict line plus its reasons, not a bare name in a list.
    const cards = within(worthALook).getAllByTestId("wc-recommendation");
    expect(cards.length).toBeGreaterThanOrEqual(1);
    expect(cards.length).toBeLessThanOrEqual(2);
    // Dart's +306 on a 5,082 price is a 6.0% move — over the stated bar, so the
    // second card fires and says the size of the move it is reacting to.
    expect(worthALook.textContent).toMatch(/Jaxson Dart/);
    expect(worthALook.textContent).toMatch(/6\.0%/);
  });

  it("never shows a roster player twice — around-the-league excludes your own", async () => {
    mountLive();

    const league = await screen.findByTestId("wc-around-the-league");
    const mine = await screen.findByTestId("wc-your-roster");

    // The unfiltered query David saw: Jaxson Dart at #1 of BOTH lists with
    // identical numbers. He belongs to exactly one of them.
    expect(within(mine).getAllByText(/Jaxson Dart/).length).toBeGreaterThan(0);
    expect(within(league).queryByText(/Jaxson Dart/)).toBeNull();
  });

  it("kills the debug dump: no same-number-two-names, no counts of internal objects", async () => {
    const { container } = mountLive();
    await screen.findByTestId("wc-verdict");

    const page = container.textContent ?? "";
    // "Starting lineup value: 97.39" sat directly above "Weekly lineup
    // strength: 97.39" — one number under two names.
    expect(page).not.toMatch(/Starting lineup value/i);
    expect(page).not.toMatch(/Weekly lineup strength/i);
    expect(page).not.toMatch(/Top-asset core value/i);
    expect(page).not.toMatch(/Whole-roster value, capped/i);
    // …and the object counts beside them.
    expect(page).not.toMatch(/Card count/i);
    expect(page).not.toMatch(/David roster player count/i);
    expect(page).not.toMatch(/Partner ranking count/i);
    expect(page).not.toMatch(/League roster count/i);
    expect(page).not.toMatch(/Total capacity:/i);
  });

  it("says where you stand in prose, and only once", async () => {
    mountLive();

    const stand = await screen.findByTestId("wc-where-you-stand");
    // team_posture.david_posture = "REBUILDING" → the dictionary's word, and
    // the roster count against its limit, said the way a manager says it.
    expect(stand.textContent).toMatch(/rebuilding/i);
    expect(stand.textContent).toMatch(/27/);
    expect(stand.textContent).toMatch(/26/);
  });

  it("replaces the tape pane and the diagnostics rail with one freshness sentence and a health sheet", async () => {
    const { container } = mountLive();
    await screen.findByTestId("wc-verdict");

    // The monospace tape pane leaves the front page entirely.
    expect(container.querySelector(".dg-ui-tape")).toBeNull();
    // One freshness line, with a status dot, and a control that opens the
    // health sheet where the tape's facts now live.
    const freshness = screen.getByTestId("wc-freshness");
    expect(freshness.querySelector("[data-freshness-dot]")).toBeTruthy();
    expect(screen.getByTestId("wc-health-sheet-toggle")).toBeTruthy();
  });
});

// ── PANEL FIXES, DRIVEN AGAINST THE REAL PAYLOAD ─────────────────────────────
//
// Each of these mutates ONE field of the captured report into a state the
// producer demonstrably emits, and asserts what the screen is then allowed to
// say. None of them is reachable on the payload as captured, which is precisely
// why the build's own browser pass could not see them.

describe("a producer that declines to answer is never rendered as a zero", () => {
  it("does not count the priced pool when the comparison never ran", async () => {
    // daily_diff.py's two failure returns carry NO entered/exited keys at all:
    // `missing_sleeper_snapshot` (:102-107) and `insufficient_history`
    // (:112-117) return only status / decision_supported / comparison_window /
    // market_source. `market.entered ?? []` manufactured the zero, and the new
    // copy stated it as a fact about the world four inches under "we couldn't
    // compare".
    mountLive((body) => {
      body.daily_diff.market = {
        status: "unavailable",
        decision_supported: false,
        aborted_reason: "missing_sleeper_snapshot",
        market_source: "fantasycalc_overlay",
      };
    });

    const league = await screen.findByTestId("wc-around-the-league");
    expect(within(league).queryByText(/New to the priced pool/i)).toBeNull();
    expect(within(league).queryByText(/Nobody new carried a price today/i)).toBeNull();
    expect(
      within(league).queryByText(/Nobody dropped out of the priced pool/i),
    ).toBeNull();
    expect(
      within(league).getByText(
        /couldn't compare the priced pool against an earlier day/i,
      ),
    ).toBeTruthy();
  });

  it("does not count it when one of the two arrays is missing either", async () => {
    mountLive((body) => {
      body.daily_diff.market.exited = null;
    });
    const league = await screen.findByTestId("wc-around-the-league");
    expect(within(league).queryByText(/New to the priced pool/i)).toBeNull();
  });

  it("still counts, and still says 'nobody', when the producer really did send both", async () => {
    mountLive((body) => {
      body.daily_diff.market.entered = [];
      body.daily_diff.market.exited = [];
    });
    const league = await screen.findByTestId("wc-around-the-league");
    expect(
      within(league).getByText(/New to the priced pool: 0 · Dropped out: 0/),
    ).toBeTruthy();
  });
});

describe("a stale section reaches the verdict it was promoted into", () => {
  it("qualifies the directive rather than leaving the notice at the page foot", async () => {
    // THE BLOCKER. drop_pressure returns status "ok" — complete and
    // well-formed — when yesterday's artifact is reused, and its own
    // staleness_caveat is the only thing that says so. The section clock and
    // the report clock provably diverge on live data (league_opportunity at
    // 119.4h inside a 0.0h report).
    mountLive((body) => {
      body.structural_context.sections.drop_pressure.staleness_caveat = {
        basis: "captured_at_vs_report_generated_at",
        report_generated_at: body.generated_at,
        age_hours: 30.2,
        is_stale: true,
      };
    });

    const verdict = await screen.findByTestId("wc-verdict");
    expect(verdict.textContent).toMatch(
      /roster-limit check behind this is 30\.2 hours old/i,
    );
    expect(verdict.textContent).toMatch(
      /last verified read rather than this morning's/i,
    );

    // And the card that names a real player carries it too — a directive
    // qualified only in the paragraph above it is a directive people will act
    // on unqualified.
    const worth = screen.getByTestId("wc-worth-a-look");
    const cut = within(worth)
      .getAllByTestId("wc-recommendation")
      .find((card) => card.getAttribute("data-rec-id") === "required-cut");
    expect(cut?.textContent).toMatch(/30\.2 hours old/);
  });

  it("carries the roster read's own clock too, now the debug dump is gone", async () => {
    // sleeper_snapshot's david_roster_player_count was promoted INTO the
    // verdict sentence, and the only place its notice used to render went with
    // the dump that carried it.
    mountLive((body) => {
      body.structural_context.sections.sleeper_snapshot.staleness_caveat = {
        basis: "captured_at_vs_report_generated_at",
        report_generated_at: body.generated_at,
        age_hours: 26.0,
        is_stale: true,
      };
    });
    const verdict = await screen.findByTestId("wc-verdict");
    expect(verdict.textContent).toMatch(/roster read behind this is 26 hours old/i);
  });

  it("says nothing of the kind on the payload as captured", async () => {
    mountLive();
    const verdict = await screen.findByTestId("wc-verdict");
    expect(verdict.textContent).not.toMatch(/hours old/i);
  });
});

describe("the cards under 'What moved' are movers", () => {
  it("never promotes a flat row into a card on a near-quiet morning", async () => {
    // roster_deltas keeps every roster player priced on both days EVEN IF FLAT
    // (daily_diff.py:143-147); only `movers` filters value_delta != 0. Slicing
    // the unfiltered list put players who did not move into three large cards
    // under a heading reading "What moved".
    mountLive((body) => {
      const rows = body.daily_diff.market.roster_deltas as Wire[];
      rows.forEach((r: Wire, i: number) => {
        r.value_delta = i === 0 ? 120 : 0;
        r.value_delta_direction = i === 0 ? "up" : "flat";
      });
    });

    const cards = await screen.findByTestId("wc-mover-cards");
    expect(cards.querySelectorAll(":scope > li")).toHaveLength(1);
    // Everything else is still on the page — the filter moves rows between the
    // cards and the tape, it never drops one. The fixture carries three roster
    // rows, so the two flat ones land on the tape below.
    const roster = screen.getByTestId("wc-your-roster");
    expect(roster.querySelectorAll(".dg-wc__rows > li")).toHaveLength(2);
  });

  it("numbers the tape by its place in the producer's list, not by the slice", async () => {
    // The numeral used to be `i + 1` over whatever slice the caller handed in,
    // so the tape restarted at 1 on the fourth-biggest mover — directly under a
    // card showing the third.
    mountLive((body) => {
      const rows = body.daily_diff.market.roster_deltas as Wire[];
      rows.forEach((r: Wire, i: number) => {
        r.value_delta = 100 - i;
        r.value_delta_direction = "up";
      });
    });

    const roster = await screen.findByTestId("wc-your-roster");
    // All three moved, so all three are cards and the tape is empty.
    expect(roster.querySelectorAll(".dg-wc__rows > li")).toHaveLength(0);
  });
});
