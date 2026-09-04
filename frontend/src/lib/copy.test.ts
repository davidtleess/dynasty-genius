import { afterEach, describe, expect, it, vi } from "vitest";

import {
  describeToken,
  fieldLabel,
  formatCaptureTimestamp,
  lookupToken,
  MODEL_STANDING_SENTENCE,
  receiptDetail,
  reportCountLabel,
  reportStateLabel,
  sourcedCaveat,
  valueWord,
} from "./copy";
import { findRawCopy } from "./renderRule";

// A console spy survives into the next test unless it is restored, and the last
// case here asserts SILENCE — every seed is mapped, so nothing warns.
afterEach(() => vi.restoreAllMocks());

describe("the copy dictionary", () => {
  it("says every seeded token as prose that keeps the token's fact", () => {
    // Studio spec §3.5, David's own screen: the fact is the age RISK, and the
    // sentence still carries "years away".
    expect(describeToken("age_not_near_position_cliff")).toBe(
      "Age is on his side — he is years away from the usual decline at his position.",
    );
    // A caveat may never soften into permission: the "not decision-grade" fact
    // survives as an instruction to weigh it, not as a licence to trade on it.
    expect(describeToken("engine_b_not_decision_grade")).toMatch(
      /not a proven market-beater/,
    );
    // Stale still says stale; unscored still says unscored.
    expect(describeToken("vintage_changed_no_score_delta")).toMatch(
      /changed since yesterday/,
    );
    // DG-150: and it must NOT name a cause. After DG-141 (B) the flag fires for
    // a player's captured details moving, for a governance bump, AND for a real
    // model rebuild — the payload distinguishes none of them, so the sentence
    // claims none of them.
    expect(describeToken("vintage_changed_no_score_delta")).not.toMatch(
      /model run|rebuilt|model files|new model/i,
    );
    // ...and the SCOPE of that "nothing moved" is stated, because the producer
    // only ever compared players present in both captures (daily_diff.py:349).
    // An earlier draft said "not one player's score moved" — a universal
    // negative over the whole league that the producer never computes.
    expect(describeToken("vintage_changed_no_score_delta")).toMatch(
      /none of the players we could compare moved/,
    );
    expect(valueWord("PRE_MODEL")).toBe("Not scored yet");
  });

  // The three sentences the DG-109 review panel found asserting MORE than their
  // token knows. Each token is a statement about the SCOPE of an analysis, and
  // each earlier draft turned it into a claim about the world that the same card
  // disproves a few lines further up.
  it("keeps a scope statement a scope statement, and never a claim about the world", () => {
    // `ROSTER_CAVEATS`/`_PVO_CAVEATS` are constants applied to every row
    // (roster_auditor.py:59, :81, :492). The card that carries this caveat also
    // prints "Market value 5082 · 30th overall".
    const market = describeToken("no_market_overlay");
    expect(market).toMatch(/left out/i);
    expect(market).not.toMatch(/nobody|no one|not quoting|no market price/i);

    // Emitted when `biological_debt_score()` returns None for want of an input
    // (roster_auditor.py:493-494) — on cards that print "Dynasty value 77.5".
    const internal = describeToken("no_internal_value_signal");
    expect(internal).toMatch(/age-weighted value risk/i);
    expect(internal).not.toMatch(/no value score|not scored/i);

    // Hardcoded structurally on every roster-fit card
    // (league_opportunity_map.py:292), where no gate ran and OpportunityCards
    // renders the card's full evidence regardless.
    const gated = valueWord("evidence_gated");
    expect(gated).toMatch(/not cleared/i);
    expect(gated).not.toMatch(/held back|withheld|suppressed/i);
  });

  it("keeps the numbers and the full missing list in the signal-completeness sentence", () => {
    const text = describeToken(
      "Signal completeness 83% — missing: ppg_t_minus_1, ppg_t_minus_2, snap_share_t_minus_1",
    );
    expect(text).toContain("83%");
    expect(text).toContain("last season's points per game");
    expect(text).toContain("the season before's points per game");
    expect(text).toContain("last season's snap share");
    expect(findRawCopy(text)).toEqual([]);
  });

  // DG-128 (2026-09-01): the blend's caveat, screened before any blend row serves
  // (the range-only cut serves none; the held fill would). The backend's caveat is a
  // token carrying the one number a manager can use (his pro games); the weight
  // rides on its own field, so the sentence must neither quote a weight nor hedge —
  // "interpret with caution" is exactly what David struck. DG-144 (2026-09-03): the
  // clause that pointed at a wider range went with the range — "one number per
  // player" — so the sentence may not mention a range either.
  it("says the short-sample blend as pedigree, never as a hedge and never as a range", () => {
    const text = describeToken("engine_ab_blend_low_sample:games=6");
    expect(text).toBe(
      "Only 6 pro games on record, so his number leans partly on his draft pedigree.",
    );
    expect(text).not.toMatch(/caution|w_B|blend|range/i);
    expect(findRawCopy(text)).toEqual([]);
    expect(describeToken("engine_ab_blend_low_sample:games=1")).toMatch(
      /^Only 1 pro game on record/,
    );
  });

  it("keeps the suffix of a real-shape token verbatim", () => {
    expect(describeToken("league_pulse_artifact_state_2026-08-29")).toBe(
      "This league snapshot was built from data captured 2026-08-29.",
    );
    expect(describeToken("WR_waiver_range_unavailable_recovery_unverifiable")).toBe(
      "No replacement-value range at WR — recovery unverifiable.",
    );
  });

  it("names the lane's own source inside a market caveat", () => {
    expect(sourcedCaveat("market_overlay_static_caveat", "FantasyCalc").text).toBe(
      "Market values come from a saved FantasyCalc snapshot, not a live feed.",
    );
    expect(sourcedCaveat("market_overlay_static_caveat", "").text).toBe(
      "Market values come from a saved snapshot, not a live feed.",
    );
  });

  it("marks an unmapped token unmapped and warns, instead of inventing prose", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});

    const note = lookupToken("some_new_backend_token");

    expect(note.mapped).toBe(false);
    expect(note.raw).toBe("some_new_backend_token");
    // It still renders clean — the render rule holds even on a miss.
    expect(findRawCopy(note.text)).toEqual([]);
    expect(warn).toHaveBeenCalledWith(
      "Copy dictionary: no sentence for token",
      "some_new_backend_token",
    );
  });

  it("humanizes an unmapped LABEL in place, because a label invents nothing", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});

    expect(fieldLabel("some_new_column")).toBe("Some new column");
    expect(warn).toHaveBeenCalledWith(
      "Copy dictionary: no label for field",
      "some_new_column",
    );
  });

  it("covers every report freshness state the contract can carry", () => {
    for (const status of [
      "fresh",
      "freshness_overdue",
      "stale",
      "corrupt_or_empty",
      "dormant",
      "missing",
      "producer_failed",
      "inputs_degraded",
    ]) {
      expect(findRawCopy(reportStateLabel(status))).toEqual([]);
      expect(findRawCopy(reportCountLabel(status))).toEqual([]);
      // A count label has to read correctly at any n: "2 on degraded inputs".
      expect(reportCountLabel(status)).toBe(reportCountLabel(status).toLowerCase());
    }
  });

  it("builds a receipt that names the field and keeps the raw value", () => {
    expect(receiptDetail("lineup_xvar", 97.39)).toBe(
      "Starting lineup value — 97.39 (from lineup_xvar)",
    );
    expect(receiptDetail("lineup_xvar", null)).toBe(
      "Starting lineup value — not recorded (from lineup_xvar)",
    );
  });

  it("formats capture timestamps deterministically for America/New_York", () => {
    expect(formatCaptureTimestamp("2026-07-05T13:45:00Z")).toBe(
      "Jul 5, 2026, 9:45 AM EDT",
    );
    expect(formatCaptureTimestamp(null)).toBe("—");
    expect(formatCaptureTimestamp(undefined)).toBe("—");
    expect(formatCaptureTimestamp("still-not-a-date")).toBe("still-not-a-date");
    expect(formatCaptureTimestamp("still-not-a-date")).not.toMatch(/NaN|Invalid Date/);
  });

  it("renders every seeded sentence clean under the render rule", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const seeds = [
      "no_market_overlay",
      "no_internal_value_signal",
      "engine_b_not_decision_grade",
      "fantasycalc_overlay",
      "captured_at_vs_report_generated_at",
      "phase18_heuristic_posture",
      "partner_score_market_influenced",
      "thin_unrostered_pool_below_min_4",
      "valuation_coverage_below_floor",
      // DG-111: the two producer aborts the front page can actually hit.
      "missing_sleeper_snapshot",
      "missing_structural_artifact",
    ];
    for (const seed of seeds) {
      const note = lookupToken(seed);
      expect(note.mapped, `${seed} is not in the dictionary`).toBe(true);
      expect(findRawCopy(note.text), `${seed} translated to raw copy`).toEqual([]);
    }
    expect(warn).not.toHaveBeenCalled();
  });
});

// DG-111 — the stamp is gone and the fact it stood on is not.
describe("DG-111 the retired disclosure line", () => {
  it("exports no DISCLOSURE_LINE for a surface to reach for", async () => {
    const mod = (await import("./copy")) as Record<string, unknown>;
    expect(mod.DISCLOSURE_LINE).toBeUndefined();
  });

  it("says the model's standing in one plain sentence instead", () => {
    // The fact `decision_supported=false` carried survives verbatim: a second
    // opinion, and explicitly NOT a proven market-beater. It must never soften
    // into permission, so the sentence is pinned here as well as at its two
    // call sites (player card foot, Model Trust panel).
    expect(MODEL_STANDING_SENTENCE).toBe(
      "Our model is a sharp second opinion, not a proven market-beater — weigh it accordingly.",
    );
    expect(MODEL_STANDING_SENTENCE).toMatch(/not a proven market-beater/);
    expect(findRawCopy(MODEL_STANDING_SENTENCE)).toEqual([]);
  });
});

// DG-147: a rookie with no rookie-model row reaches the "unscored" caveat
// through the ROOKIE contract, so the sentence must name that model, not the
// active-player one it used to blame for every variant of the token.
describe("DG-147 the unscored caveat names the model the backend consulted", () => {
  it("says the rookie model has not scored him for the Engine A variant", () => {
    const note = lookupToken(
      "dynasty_value_score unavailable: Engine A (prospect) not yet validated; model_grade is PRE_MODEL",
    );
    expect(note.text).toBe(
      "No dynasty value for him yet — the rookie model has not scored him, so he is unscored.",
    );
  });

  it("keeps the active-player wording for the Engine B variant", () => {
    const note = lookupToken(
      "dynasty_value_score unavailable: Engine B (active player) not yet validated; model_grade is PRE_MODEL",
    );
    expect(note.text).toContain("the active-player model has not been validated");
  });
});
