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
      "Its checks pass; it is waiting on David's sign-off.",
    ]);
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
