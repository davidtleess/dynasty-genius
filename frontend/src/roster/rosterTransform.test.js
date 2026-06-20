// @vitest-environment node
import { describe, expect, it } from "vitest";
import { applySort } from "./rosterTransform";

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
