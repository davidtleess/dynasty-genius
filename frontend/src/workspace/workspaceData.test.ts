import { describe, expect, it } from "vitest";
import {
  joinWorkspacePlayers,
  sortWorkspacePlayers,
  validateComparison,
} from "./workspaceData";
import { comparison, forecast, ranks } from "./workspaceFixtures";

describe("workspace source and population contract", () => {
  it("accepts a matching source and refuses mixed report, ownership, years, position or roster", () => {
    expect(validateComparison(comparison, ranks)).toMatchObject(comparison);
    for (const changed of [
      { ...comparison, source: { ...comparison.source, report_sha256: "different" } },
      {
        ...comparison,
        source: { ...comparison.source, ownership_as_of: "2026-09-05" },
      },
      { ...comparison, future_years: [2028] },
      { ...comparison, roster: [] },
      { ...comparison, available: [{ ...forecast("free"), position: "WR" }] },
      { ...comparison, available: [forecast("owned")] },
      { ...comparison, available: [{ ...forecast("free"), now_points: "42" }] },
    ])
      expect(() => validateComparison(changed, ranks)).toThrow();
  });
  it("only calls the explicit default unowned population available; preserves missing forecasts and watch identities", () => {
    const watch = new Map([
      [
        "vanished",
        {
          name: "Remembered Player",
          position: "WR",
          team: "NYJ",
          watched_at: "2026-09-01T10:00:00Z",
        },
      ],
    ]);
    const rows = joinWorkspacePlayers(ranks, comparison, watch);
    expect(
      rows
        .filter((p) => p.ownership === "available")
        .map((p) => p.id)
        .sort(),
    ).toEqual(["free", "missing"]);
    expect(rows.find((p) => p.id === "other-manager")?.ownership).toBe("league");
    expect(rows.find((p) => p.id === "cut")?.ownership).toBe("outside");
    expect(rows.find((p) => p.id === "vanished")).toMatchObject({
      name: "Remembered Player",
      watched: true,
      ownership: "unknown",
      rank: null,
      forecast: null,
    });
    expect(rows.find((p) => p.id === "owned")?.rank).toBe(ranks.rows[0]);
  });
  it("retains rank roster when forecasts fail without asserting availability", () => {
    const rows = joinWorkspacePlayers(ranks, null, new Map());
    expect(rows.filter((p) => p.ownership === "roster")).toHaveLength(1);
    expect(rows.filter((p) => p.ownership === "available")).toHaveLength(0);
    expect(rows.every((p) => p.forecast === null)).toBe(true);
  });
  it("keeps zero in the numeric order and missing outside; leaves rank ties unchanged", () => {
    const players = joinWorkspacePlayers(ranks, comparison, new Map());
    const sorted = sortWorkspacePlayers(players, "now");
    expect(sorted.ranked.some((p) => p.id === "free")).toBe(true);
    expect(sorted.missing.some((p) => p.id === "missing")).toBe(true);
    const gap = sortWorkspacePlayers(players, "gap");
    expect(gap.ranked.find((p) => p.id === "free")?.rank?.our_rank).toEqual({
      start: 2,
      end: 3,
      total: 3,
    });
    expect(sortWorkspacePlayers(players, "name").missing).toHaveLength(0);
  });
});
