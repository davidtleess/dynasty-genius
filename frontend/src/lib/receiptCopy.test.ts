// DG-120 — the receipt dictionary, tested against the strings the producers
// actually emit.
//
// The DOM audit in renderRule.test.tsx proves no machinery REACHES the screen.
// That is a different question from whether what replaced it is TRUE, and the
// DG-091 programme was burned three times by prose that read well and claimed
// something the producer never said. So this file checks the sentences
// themselves: every one of them against the live payload captured on
// 2026-08-30, and the two facts a translation is most likely to quietly drop —
// which store, and which days.
import { describe, expect, it, vi } from "vitest";
import { DESTINATIONS } from "../shell/destinations";
import systemHealthLive from "./__fixtures__/systemHealth.live.json";
import {
  disclosureSentence,
  type ReceiptSegment,
  reportBasisMessage,
  subsystemBasisMessage,
  surfaceName,
} from "./copy";
import { findRawCopy } from "./renderRule";

/** What a person reads: the prose and the addresses, in order. */
const read = (segments: ReceiptSegment[]): string =>
  segments.map((s) => (s.kind === "prose" ? s.text : s.raw)).join("");

/** Just the addresses, which must survive translation byte for byte. */
const addresses = (segments: ReceiptSegment[]): string[] =>
  segments.flatMap((s) => (s.kind === "identifier" ? [s.raw] : []));

describe("receipt messages say what the producer said", () => {
  // Every basis the live health endpoint carried on 2026-08-30 (both files:
  // frontend/src/lib/__fixtures__/systemHealth.live.json), each one translated
  // and then checked back against the fact it started from.
  it("translates every report basis in the live payload with nothing left raw", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    for (const row of systemHealthLive.reports) {
      const message = reportBasisMessage(row.basis);
      const text = read(message);
      expect(text.length, `empty message for ${row.basis}`).toBeGreaterThan(0);
      // Anything still machine-shaped must be a DECLARED address, never prose.
      const prose = message
        .filter((s) => s.kind === "prose")
        .map((s) => (s as { text: string }).text)
        .join("");
      expect(
        findRawCopy(prose),
        `${row.basis} left machinery in prose: ${prose}`,
      ).toEqual([]);
    }
    expect(
      warn.mock.calls.filter((c) => String(c[0]).startsWith("Copy dictionary:")),
      "a live basis had no entry in the dictionary",
    ).toEqual([]);
    warn.mockRestore();
  });

  it("keeps the stream ids inside a degraded-inputs basis byte-exact", () => {
    // feature_refresh, 2026-08-30. `_describe_stream`
    // (system_health_models.py:383-405) writes the stream id first and its
    // description after; the id is an address into the producer's own input
    // block and the description is already plain language.
    const basis =
      "EARLIER SEASON: pbp 2025 (ValueError), player_stats 2025 (ConnectionError), snap_counts 2025 (ValueError) | LIVE: participation (334,682 rows; season not reported by source), rosters 2026";
    const message = reportBasisMessage(basis);

    expect(addresses(message)).toEqual([
      "pbp",
      "player_stats",
      "snap_counts",
      "participation",
      "rosters",
    ]);
    // The shouted section headers are gone as machinery and present as facts:
    // `EARLIER SEASON` is `fallback_used is True` (:460), which means the season
    // ASKED FOR was refused and an earlier one served. DG-023: never a cache.
    const text = read(message);
    expect(text).not.toContain("EARLIER SEASON");
    expect(text).not.toContain("LIVE:");
    expect(text).toContain("Served an earlier season than the one asked for");
    expect(text).toContain("Loaded live");
    // Every count and season the producer wrote is still on the screen.
    expect(text).toContain("2025 (ValueError)");
    expect(text).toContain("2025 (ConnectionError)");
    expect(text).toContain("334,682 rows; season not reported by source");
    expect(text).toContain("rosters 2026");
  });

  it("breaks a degraded capture-health basis into one row per store, dates intact", () => {
    const subsystem = systemHealthLive.subsystems.find(
      (s) => s.subsystem_id === "capture_health",
    );
    expect(subsystem).toBeTruthy();
    const { summary, lines } = subsystemBasisMessage(
      (subsystem as { basis: string }).basis,
    );

    expect(read(summary)).toBe(
      "2 of 3 daily capture feeds are in a bad state. Which, and why:",
    );
    expect(lines.map((l) => l.identifier)).toEqual([
      "model_forward_capture",
      "market_divergence_history",
    ]);
    expect(lines.map((l) => l.label)).toEqual([
      "Daily model scores",
      "Model-versus-market price gaps",
    ]);
    // THE FACT THAT MUST NOT GO MISSING. `_store_reason` (system_health.py:75-105)
    // exists because "degraded" alone cannot be acted on — one uncaptured day is
    // what blocks two surfaces downstream, and a message that does not name the
    // date is useless. Both rows keep their counts and every date.
    expect(read(lines[0]?.message ?? [])).toBe("missing 1 of 67 days (2026-08-12)");
    expect(read(lines[1]?.message ?? [])).toBe(
      "missing 4 of 52 days (2026-07-10, 2026-07-12, 2026-07-17, 2026-08-12)",
    );
  });

  it("says one shared reason once, and different reasons separately", () => {
    const shared = subsystemBasisMessage(
      "roster_capacity: live_precondition_not_ok:capture_health_ok=degraded; trade_lab: live_precondition_not_ok:capture_health_ok=degraded",
    );
    expect(read(shared.summary)).toBe(
      "2 parts of the product are not graded ready, all for the same reason. Waiting on the capture health check, which is reporting: something needs attention.",
    );
    // The rows keep their names and ids and do NOT repeat the sentence.
    expect(shared.lines.map((l) => l.label)).toEqual(["Cut list", "Build a trade"]);
    expect(shared.lines.map((l) => l.identifier)).toEqual([
      "roster_capacity",
      "trade_lab",
    ]);
    expect(shared.lines.every((l) => l.message.length === 0)).toBe(true);

    // Two genuinely different problems stay two sentences — the grouping is a
    // statement about the payload, never a shortcut applied regardless.
    const differing = subsystemBasisMessage(
      "roster_capacity: live_precondition_not_ok:capture_health_ok=degraded; trade_lab: awaiting_david_ratification",
    );
    expect(read(differing.summary)).toBe(
      "2 parts of the product are not graded ready. Which, and why:",
    );
    expect(differing.lines.map((l) => read(l.message))).toEqual([
      "Waiting on the capture health check, which is reporting: something needs attention.",
      "It has not been signed off by David yet.",
    ]);
  });

  it("never calls a surface not ready when the producer says it passed", () => {
    // THE FILTER THAT FILTERS NOTHING. `_default_tier_readiness_status`
    // (system_health.py:63-68) builds this basis from
    // `[... for s in response.surfaces if s.tier_status != "ok"]`, and "ok" is
    // NOT a member of `TierStatus` (system_tier_readiness_models.py:25-30). The
    // comparison is a tautology, so the list is EVERY surface whenever the
    // rollup is degraded — ready ones included. Reachable today: the R8 overlay
    // (system_tier_readiness.py:196-214) downgrades ONE surface whose own
    // producer artifact is absent, and the five surfaces declare five different
    // artifacts. A heading counting the list length said "5 parts of the
    // product are not graded ready" over four rows reading "Every readiness
    // check passed."
    const mixed = subsystemBasisMessage(
      "roster_capacity: all_readiness_checks_passed; daily_what_changed: producer_artifact_missing:app/data/what_changed/what_changed_latest_report.json; model_trust_console: all_readiness_checks_passed; trade_lab: all_readiness_checks_passed; league_pulse: readiness_active_with_insufficient_data",
    );
    expect(read(mixed.summary)).toBe(
      "One part of the 5 checked is not graded ready. Where each stands:",
    );
    // Every row still speaks for itself, and the one that is held back names
    // the missing file byte-exact.
    expect(mixed.lines.map((l) => read(l.message))).toEqual([
      "Every readiness check passed.",
      "A file its producer is supposed to write is missing: app/data/what_changed/what_changed_latest_report.json.",
      "Every readiness check passed.",
      "Every readiness check passed.",
      "Running, with too little data behind one of its checks to grade it.",
    ]);
    expect(addresses(mixed.lines[1]?.message ?? [])).toEqual([
      "app/data/what_changed/what_changed_latest_report.json",
    ]);

    // And when the whole list is ready, the receipt claims nothing about
    // readiness at all — the rollup is degraded for some other reason, and
    // nothing on this list is it.
    const allReady = subsystemBasisMessage(
      "roster_capacity: all_readiness_checks_passed; trade_lab: all_readiness_checks_passed",
    );
    expect(read(allReady.summary)).toBe("Where each part of the product stands:");
    expect(allReady.lines.map((l) => read(l.message))).toEqual([
      "Every readiness check passed.",
      "Every readiness check passed.",
    ]);
  });

  it("writes the four bases a failing gate component actually puts on a surface", () => {
    // system_tier_readiness_models.py:301-320 — every component defect writes
    // `{defect}:{component}` as the SURFACE basis. None of the four was written
    // until the review found them, so the realistic broken morning printed raw
    // machinery. The component name is an address and stays exact.
    const { summary } = subsystemBasisMessage(
      "roster_capacity: component_failed:audit_hygiene; trade_lab: component_failed:audit_hygiene",
    );
    expect(read(summary)).toBe(
      "2 parts of the product are not graded ready, all for the same reason. Its readiness check audit_hygiene did not pass.",
    );

    const each = subsystemBasisMessage(
      "roster_capacity: component_state_missing:mif_breaker; trade_lab: unknown_component_status:audit_hygiene; league_pulse: required_component_not_applicable:mif_breaker",
    );
    expect(each.lines.map((l) => read(l.message))).toEqual([
      "Its readiness check mif_breaker recorded no state at all.",
      "Its readiness check audit_hygiene reported a status this product does not recognise.",
      "Its readiness check mif_breaker reported itself not applicable, and it is not optional.",
    ]);
    expect(each.lines.flatMap((l) => addresses(l.message))).toEqual([
      "mif_breaker",
      "audit_hygiene",
      "mif_breaker",
    ]);
  });

  it("keeps the other rows translated when one surface id is unknown", () => {
    // One id the dictionary does not know used to send the WHOLE receipt back
    // to the raw 400-character dump this ticket exists to kill.
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const { lines } = subsystemBasisMessage(
      "roster_capacity: all_readiness_checks_passed; accuracy_tracker: all_readiness_checks_passed",
    );
    expect(lines.map((l) => l.label)).toEqual(["Cut list", "Accuracy tracker"]);
    expect(lines.map((l) => read(l.message))).toEqual([
      "Every readiness check passed.",
      "Every readiness check passed.",
    ]);
    expect(warn).toHaveBeenCalledWith(
      "Copy dictionary: no name for surface",
      "accuracy_tracker",
    );
    warn.mockRestore();
  });

  it("agrees the verb when exactly one capture feed is degraded", () => {
    // The live shape for model_forward_capture today.
    const { summary } = subsystemBasisMessage(
      "1 of 3 stores degraded — model_forward_capture: missing 1 of 67 days (2026-08-12)",
    );
    expect(read(summary)).toBe(
      "1 of 3 daily capture feeds is in a bad state. Which, and why:",
    );
  });

  it("hands back an unwritten store caveat and an unwritten failure reason RAW", () => {
    // THE FALLBACK MUST NOT BUY SILENCE, and these are the two branches where it
    // could. Both used to route through `describeToken`, whose miss path is
    // `humanize` — so `unexpected_settings_hash_detected` reached David as
    // "Unexpected settings hash detected" with the producer's token nowhere in
    // the document and `findRawCopy` seeing no underscores to fail on.
    //
    // Class A is a closed two-token set (system_capture_health_models.py:400-404)
    // and everything else degrades by default, so the caveats that can reach a
    // DEGRADED store's reason (system_health.py:103) are exactly the class-B set,
    // none of which the dictionary has a sentence for.
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const { lines } = subsystemBasisMessage(
      "1 of 3 stores degraded — model_forward_capture: missing 1 of 67 days (2026-08-12); unexpected_settings_hash_detected",
    );
    const storeText = read(lines[0]?.message ?? []);
    expect(storeText).toBe(
      "missing 1 of 67 days (2026-08-12) · unexpected_settings_hash_detected",
    );
    expect(findRawCopy(storeText)).toContain("unexpected_settings_hash_detected");

    // Same law for a producer's own failure text. `report_freshness.json`
    // declares a free-text `failure_reason_field` on six of nine artifacts.
    const failure = reportBasisMessage("producer_failure:market_source_prior_date");
    expect(read(failure)).toBe(
      "The run reported that it failed: market_source_prior_date",
    );
    expect(findRawCopy(read(failure))).toContain("market_source_prior_date");
    warn.mockRestore();
  });

  it("says an adapter that returned only a status returned only a status", () => {
    // system_health.py:216 — `basis = reason or f"adapter_status:{status}"`. The
    // fallback fires precisely when the adapter gave NO reason, so the honest
    // translation is that there is nothing further, not an invented detail.
    const { summary, lines } = subsystemBasisMessage("adapter_status:ok");
    expect(read(summary)).toBe(
      "The check returned only its status (running normally), with nothing further.",
    );
    expect(lines).toEqual([]);
  });

  it("keeps both disclosures, and both change what the row's own numbers mean", () => {
    expect(read(disclosureSentence("timestamp_source:mtime_fallback"))).toBe(
      "The time on this row is when the file was last written, not a timestamp inside it.",
    );
    expect(read(disclosureSentence("auxiliary_info_only"))).toBe(
      "Secondary data: this row is reported for information and does not move the overall status.",
    );
  });

  it("hands an unwritten message back raw rather than paraphrasing it", () => {
    // The last resort. A sentence nobody has written must not be invented from
    // the token's own letters — "Model multi vintage ambiguous" reads as broken
    // English and can be mistaken for a claim (the DG-043 bug). It comes back
    // as the producer's own bytes, as PROSE, so `renderRule` sees it and the
    // gate goes red instead of the string going quiet.
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const message = reportBasisMessage("some_future_basis_nobody_wrote");
    expect(read(message)).toBe("some_future_basis_nobody_wrote");
    expect(addresses(message)).toEqual([]);
    expect(findRawCopy(read(message))).toEqual(["some_future_basis_nobody_wrote"]);
    expect(warn).toHaveBeenCalledWith(
      "Copy dictionary: no sentence for receipt message",
      "some_future_basis_nobody_wrote",
    );
    warn.mockRestore();
  });
});

describe("a surface is named the way the nav names it", () => {
  // The receipt tells a person WHICH PART of the product is held back. A name
  // he cannot find in the rail does not do that, so these are locked to
  // `destinations.ts` rather than to the backend's `display_name` — which says
  // "Roster Capacity", "Trade Lab" and "League Pulse" where the rail says "Cut
  // list", "Build a trade" and "League". If the rail is relabelled, this fails.
  const navLabels = new Set(
    DESTINATIONS.flatMap((destination) => destination.views.map((view) => view.label)),
  );

  it.each([
    ["roster_capacity", "Cut list"],
    ["daily_what_changed", "Today"],
    ["model_trust_console", "Model trust"],
    ["trade_lab", "Build a trade"],
    ["league_pulse", "League"],
  ])("%s is called %s, the same as the nav", (surfaceId, expected) => {
    expect(surfaceName(surfaceId)).toBe(expected);
    expect(
      navLabels.has(expected),
      `"${expected}" is not a label in destinations.ts — the receipt would name a place David cannot find`,
    ).toBe(true);
  });
});
