// @vitest-environment node
import { describe, expect, it } from "vitest";
import { applyFilter, applyGroup, applySort } from "./rosterTransform";

const mk = (o) => ({
  player_id: o.id,
  full_name: o.id,
  position: o.pos ?? "WR",
  is_prospect: o.prospect ?? false,
  model_grade: "ACTIVE_B",
  age: o.age ?? null,
  xvar: o.xvar ?? null,
  signal_completeness: o.sc ?? 0,
  roster_audit: o.ra === undefined ? null : o.ra,
});

describe("applySort", () => {
  it("none preserves input order", () => {
    const ps = [mk({ id: "a" }), mk({ id: "b" }), mk({ id: "c" })];
    expect(applySort(ps, "none").map((p) => p.player_id)).toEqual(["a", "b", "c"]);
  });

  it("age desc, nulls last", () => {
    const ps = [
      mk({ id: "y", age: 24 }),
      mk({ id: "n", age: null }),
      mk({ id: "o", age: 31 }),
    ];
    expect(applySort(ps, "age").map((p) => p.player_id)).toEqual(["o", "y", "n"]);
  });

  it("signal_completeness asc (lowest first)", () => {
    const ps = [mk({ id: "hi", sc: 0.9 }), mk({ id: "lo", sc: 0.1 })];
    expect(applySort(ps, "signal_completeness").map((p) => p.player_id)).toEqual([
      "lo",
      "hi",
    ]);
  });

  it("xvar desc; negatives below positives; null last", () => {
    const ps = [
      mk({ id: "neg", xvar: -2 }),
      mk({ id: "nul", xvar: null }),
      mk({ id: "pos", xvar: 5 }),
    ];
    expect(applySort(ps, "xvar").map((p) => p.player_id)).toEqual([
      "pos",
      "neg",
      "nul",
    ]);
  });

  it("age_cliff_risk desc with tie-breakers; missing roster_audit last", () => {
    const ps = [
      mk({ id: "tieA", ra: { age_cliff_risk: 0.5, years_to_cliff: 3 } }),
      mk({ id: "tieB", ra: { age_cliff_risk: 0.5, years_to_cliff: 1 } }),
      mk({ id: "low", ra: { age_cliff_risk: 0.2, years_to_cliff: 5 } }),
      mk({ id: "none", ra: null }),
    ];
    expect(applySort(ps, "age_cliff_risk").map((p) => p.player_id)).toEqual([
      "tieB",
      "tieA",
      "low",
      "none",
    ]);
  });

  it("is stable for fully-equal keys", () => {
    const ps = [
      mk({ id: "1", age: 25 }),
      mk({ id: "2", age: 25 }),
      mk({ id: "3", age: 25 }),
    ];
    expect(applySort(ps, "age").map((p) => p.player_id)).toEqual(["1", "2", "3"]);
  });
});

describe("applyFilter", () => {
  const ps = [
    mk({ id: "wr", pos: "WR", prospect: false }),
    mk({ id: "qb", pos: "QB", prospect: false }),
    mk({ id: "rookie", pos: "RB", prospect: true }),
  ];

  it("empty positions = all", () => {
    expect(
      applyFilter(ps, { positions: [], prospect: "all" }).map((p) => p.player_id),
    ).toEqual(["wr", "qb", "rookie"]);
  });

  it("position multi-select subsets", () => {
    expect(
      applyFilter(ps, { positions: ["WR", "QB"], prospect: "all" }).map(
        (p) => p.player_id,
      ),
    ).toEqual(["wr", "qb"]);
  });

  it("prospect=active excludes prospects", () => {
    expect(
      applyFilter(ps, { positions: [], prospect: "active" }).map((p) => p.player_id),
    ).toEqual(["wr", "qb"]);
  });

  it("prospect=prospects keeps only prospects", () => {
    expect(
      applyFilter(ps, { positions: [], prospect: "prospects" }).map((p) => p.player_id),
    ).toEqual(["rookie"]);
  });
});

describe("applyGroup", () => {
  it("position groups in first-seen backend order; group order independent of sort", () => {
    const ps = [
      mk({ id: "wr1", pos: "WR", xvar: 1 }),
      mk({ id: "qb1", pos: "QB", xvar: 99 }),
      mk({ id: "wr2", pos: "WR", xvar: 50 }),
    ];

    const groups = applyGroup(ps, "position", "xvar");

    expect(groups.map((g) => g.key)).toEqual(["WR", "QB"]);
    expect(groups[0].players.map((p) => p.player_id)).toEqual(["wr2", "wr1"]);
  });

  it("depreciation_band uses producer token severity order; missing last", () => {
    const ps = [
      mk({ id: "noSig", ra: null }),
      mk({ id: "appr", ra: { signal: "approaching_cliff" } }),
      mk({ id: "past", ra: { signal: "past_cliff" } }),
      mk({ id: "far", ra: { signal: "no_age_signal" } }),
      mk({ id: "at", ra: { signal: "at_cliff" } }),
    ];

    const groups = applyGroup(ps, "depreciation_band", "none");

    expect(groups.map((g) => g.label)).toEqual([
      "Past cliff age",
      "At cliff age",
      "Approaching cliff",
      "3+ years (No immediate cliff)",
      "Missing age signal",
    ]);
  });

  it("xvar_bracket groups finite xVAR high to low with not-modeled last", () => {
    const ps = [
      mk({ id: "notModeled", xvar: null }),
      mk({ id: "negative", xvar: -3.5 }),
      mk({ id: "replacement", xvar: 0.0 }),
      mk({ id: "positive", xvar: 12.4 }),
    ];

    const groups = applyGroup(ps, "xvar_bracket", "none");

    expect(groups.map((g) => g.label)).toEqual([
      "xVAR 0.0+",
      "xVAR below 0.0 (sub-replacement)",
      "xVAR not modeled",
    ]);
    expect(groups.map((g) => g.players.map((p) => p.player_id))).toEqual([
      ["replacement", "positive"],
      ["negative"],
      ["notModeled"],
    ]);
  });

  it("xvar_bracket treats boundary and non-finite xVAR values exactly", () => {
    const undefinedXvar = mk({ id: "undefined" });
    undefinedXvar.xvar = undefined;
    const ps = [
      mk({ id: "nan", xvar: Number.NaN }),
      mk({ id: "posInf", xvar: Number.POSITIVE_INFINITY }),
      mk({ id: "negInf", xvar: Number.NEGATIVE_INFINITY }),
      undefinedXvar,
      mk({ id: "null", xvar: null }),
      mk({ id: "zero", xvar: 0.0 }),
      mk({ id: "justBelow", xvar: -0.0001 }),
    ];

    const groups = applyGroup(ps, "xvar_bracket", "none");

    expect(groups.map((g) => g.label)).toEqual([
      "xVAR 0.0+",
      "xVAR below 0.0 (sub-replacement)",
      "xVAR not modeled",
    ]);
    expect(groups.map((g) => g.players.map((p) => p.player_id))).toEqual([
      ["zero"],
      ["justBelow"],
      ["nan", "posInf", "negInf", "undefined", "null"],
    ]);
  });

  it("xvar_bracket omits empty buckets for empty, all-missing, and single-bucket rosters", () => {
    expect(applyGroup([], "xvar_bracket", "none")).toEqual([]);

    const allMissing = applyGroup(
      [mk({ id: "a", xvar: null }), mk({ id: "b", xvar: Number.NaN })],
      "xvar_bracket",
      "none",
    );
    expect(allMissing.map((g) => g.label)).toEqual(["xVAR not modeled"]);
    expect(allMissing[0].players.map((p) => p.player_id)).toEqual(["a", "b"]);

    const singleBucket = applyGroup(
      [mk({ id: "a", xvar: 1 }), mk({ id: "b", xvar: 2 })],
      "xvar_bracket",
      "none",
    );
    expect(singleBucket.map((g) => g.label)).toEqual(["xVAR 0.0+"]);
    expect(singleBucket[0].players.map((p) => p.player_id)).toEqual(["a", "b"]);
  });

  it("xvar_bracket applies the active sort key within each bucket", () => {
    const ps = [
      mk({ id: "lowPositive", xvar: 1 }),
      mk({ id: "highPositive", xvar: 15 }),
      mk({ id: "lessNegative", xvar: -2 }),
      mk({ id: "moreNegative", xvar: -20 }),
    ];

    const groups = applyGroup(ps, "xvar_bracket", "xvar");

    expect(groups.map((g) => g.players.map((p) => p.player_id))).toEqual([
      ["highPositive", "lowPositive"],
      ["lessNegative", "moreNegative"],
    ]);
  });

  it("none returns a single unlabeled group, sorted", () => {
    const ps = [mk({ id: "a", age: 20 }), mk({ id: "b", age: 30 })];

    const groups = applyGroup(ps, "none", "age");

    expect(groups.length).toBe(1);
    expect(groups[0].players.map((p) => p.player_id)).toEqual(["b", "a"]);
  });
});
