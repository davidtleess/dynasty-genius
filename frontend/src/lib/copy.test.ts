import { afterEach, describe, expect, it, vi } from "vitest";

import {
  describeToken,
  fieldLabel,
  formatCaptureTimestamp,
  lookupToken,
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
      /not one player's score moved/,
    );
    expect(valueWord("PRE_MODEL")).toBe("Not scored yet");
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
    ];
    for (const seed of seeds) {
      const note = lookupToken(seed);
      expect(note.mapped, `${seed} is not in the dictionary`).toBe(true);
      expect(findRawCopy(note.text), `${seed} translated to raw copy`).toEqual([]);
    }
    expect(warn).not.toHaveBeenCalled();
  });
});
