// DG-181 — pure helpers behind the roster-spot comparison: search, the signed sentence, and
// formatting. No React, no fetch. Node environment on purpose.
import { describe, expect, it } from "vitest";

import {
  CAVEAT,
  type ComparisonPlayer,
  classWord,
  compareForecasts,
  findPlayer,
  finitePoints,
  formatSignedPoints,
  humanizeDate,
  periodsFor,
  searchPlayers,
  statusWord,
} from "./comparisonHelpers";

function player(
  over: Partial<ComparisonPlayer> & { sleeper_id: string; name: string },
) {
  const base: ComparisonPlayer = {
    sleeper_id: over.sleeper_id,
    name: over.name,
    position: "QB",
    team: "CIN",
    population: "default",
    status: "active",
    now_points: 115.32497628242587,
    future_points: 179.44179369437418,
    seasons: [2026, 2027, 2028, 2029, 2030].map((season) => ({
      season,
      points: 10,
      estimate_class: null,
    })),
    starting_estimate: false,
    missing_reason: null,
    evidence_note: "Accepted forecast.",
  };
  return { ...base, ...over };
}

const flacco = player({ sleeper_id: "19", name: "Joe Flacco" });
const mccarthy = player({
  sleeper_id: "11565",
  name: "J.J. McCarthy",
  team: "MIN",
  status: "rostered",
  now_points: 156.5816995883777,
  future_points: 832.2660448226352,
});
const ali = player({
  sleeper_id: "11570",
  name: "Rasheen Ali",
  position: "RB",
  team: "BAL",
  status: "rostered",
  now_points: 52.07419940832724,
  future_points: 410.4238857735934,
});
const NOW = { key: "now_points", label: "2026" } as const;
const FUTURE = { key: "future_points", label: "2027–2030" } as const;

describe("periodsFor", () => {
  it("names the one current season and the future span from the payload's years", () => {
    expect(
      periodsFor({
        forecast_years: [2026, 2027, 2028, 2029, 2030],
        future_years: [2027, 2028, 2029, 2030],
      }),
    ).toEqual({
      now: { key: "now_points", label: "2026" },
      future: { key: "future_points", label: "2027–2030" },
    });
  });
});

describe("finitePoints", () => {
  it("keeps finite numbers, including zero and negatives, and rejects everything else", () => {
    expect(finitePoints(-0.2117124292497116)).toBe(-0.2117124292497116);
    expect(finitePoints(0)).toBe(0);
    expect(finitePoints(Number.NaN)).toBeNull();
    expect(finitePoints(Number.POSITIVE_INFINITY)).toBeNull();
    expect(finitePoints("12")).toBeNull();
    expect(finitePoints(null)).toBeNull();
    expect(finitePoints(undefined)).toBeNull();
  });
});

describe("findPlayer", () => {
  it("returns the row for a known id and null for a missing or absent id", () => {
    expect(findPlayer([flacco, mccarthy], "11565")).toBe(mccarthy);
    expect(findPlayer([flacco, mccarthy], "nope")).toBeNull();
    expect(findPlayer([flacco, mccarthy], null)).toBeNull();
  });
});

describe("searchPlayers", () => {
  const list = [
    mccarthy,
    ali,
    flacco,
    player({ sleeper_id: "7527", name: "Mac Jones", team: "SF" }),
  ];
  it("matches name, team or position case-insensitively and orders by name", () => {
    expect(searchPlayers(list, "mAc").matches.map((p) => p.name)).toEqual([
      "Mac Jones",
    ]);
    expect(searchPlayers(list, "bal").matches.map((p) => p.name)).toEqual([
      "Rasheen Ali",
    ]);
    expect(searchPlayers(list, "qb").matches.map((p) => p.name)).toEqual([
      "J.J. McCarthy",
      "Joe Flacco",
      "Mac Jones",
    ]);
  });
  it("returns nothing for an empty query unless asked to list everyone", () => {
    expect(searchPlayers(list, "  ")).toEqual({ matches: [], total: 0 });
    const all = searchPlayers(list, "", { allWhenEmpty: true });
    expect(all.total).toBe(4);
    expect(all.matches.map((p) => p.name)).toEqual([
      "J.J. McCarthy",
      "Joe Flacco",
      "Mac Jones",
      "Rasheen Ali",
    ]);
  });
  it("caps the list at the limit while reporting the full match count", () => {
    const r = searchPlayers(list, "qb", { limit: 2 });
    expect(r.matches.map((p) => p.name)).toEqual(["J.J. McCarthy", "Joe Flacco"]);
    expect(r.total).toBe(3);
  });
});

describe("compareForecasts — same position", () => {
  it("says lower with the signed full-precision difference and both values for the named period", () => {
    const v = compareForecasts(flacco, mccarthy, NOW);
    expect(v.kind).toBe("same_position");
    if (v.kind !== "same_position") throw new Error("kind");
    expect(v.direction).toBe("lower");
    expect(v.diff).toBe(115.32497628242587 - 156.5816995883777);
    expect(v.sentence).toBe(
      "For 2026, Joe Flacco's forecast is lower than J.J. McCarthy's by 41.3 points (115.3 vs 156.6).",
    );
  });
  it("says higher when the first player's forecast is larger", () => {
    const v = compareForecasts(mccarthy, flacco, FUTURE);
    if (v.kind !== "same_position") throw new Error("kind");
    expect(v.direction).toBe("higher");
    expect(v.sentence).toBe(
      "For 2027–2030, J.J. McCarthy's forecast is higher than Joe Flacco's by 652.8 points (832.3 vs 179.4).",
    );
  });
  it("calls an exact tie a tie", () => {
    const twin = player({
      ...mccarthy,
      sleeper_id: "tt",
      name: "Tie Twin",
      now_points: flacco.now_points,
    });
    const v = compareForecasts(flacco, twin, NOW);
    if (v.kind !== "same_position") throw new Error("kind");
    expect(v.direction).toBe("tie");
    expect(v.diff).toBe(0);
    expect(v.sentence).toBe(
      "For 2026, the two forecasts are an exact tie (115.3 vs 115.3).",
    );
  });
  it("names a difference under one point as such and never prints it as zero", () => {
    const twin = player({
      ...mccarthy,
      sleeper_id: "tt",
      name: "Tie Twin",
      future_points: 179.47179369437418,
    });
    const v = compareForecasts(flacco, twin, FUTURE);
    if (v.kind !== "same_position") throw new Error("kind");
    expect(v.sentence).toBe(
      "For 2027–2030, Joe Flacco's forecast is lower than Tie Twin's by 0.03 points (179.4 vs 179.5), a difference under one point.",
    );
  });
  it("keeps a negative forecast's sign in the sentence", () => {
    const rourke = player({
      sleeper_id: "12477",
      name: "Kurtis Rourke",
      now_points: -0.2117124292497116,
    });
    const v = compareForecasts(rourke, mccarthy, NOW);
    if (v.kind !== "same_position") throw new Error("kind");
    expect(v.sentence).toContain("(-0.2 vs 156.6)");
    expect(v.sentence).toContain("by 156.8 points");
    expect(v.sentence).not.toContain("by -");
  });
});

describe("compareForecasts — missing and cross-position", () => {
  it("names the player without a forecast and offers no comparison for that period", () => {
    const bradley = player({
      sleeper_id: "11851",
      name: "Carter Bradley",
      now_points: null,
    });
    expect(compareForecasts(bradley, mccarthy, NOW)).toEqual({
      kind: "missing",
      sentence:
        "No 2026 forecast for Carter Bradley, so no comparison for that period.",
    });
  });
  it("names both players when neither has a forecast", () => {
    const bradley = player({
      sleeper_id: "11851",
      name: "Carter Bradley",
      future_points: null,
    });
    const dell = player({ sleeper_id: "9502", name: "Tank Dell", future_points: null });
    expect(compareForecasts(bradley, dell, FUTURE).sentence).toBe(
      "No 2027–2030 forecast for Carter Bradley or Tank Dell, so no comparison for that period.",
    );
  });
  it("refuses a pair whose difference overflows instead of naming a winner or a zero", () => {
    const huge = player({ sleeper_id: "h", name: "Huge Row", now_points: 1e308 });
    const tiny = player({ sleeper_id: "t", name: "Tiny Row", now_points: -1e308 });
    const v = compareForecasts(huge, tiny, NOW);
    expect(v.kind).toBe("missing");
    expect(v.sentence).toBe(
      "The 2026 forecasts for Huge Row and Tiny Row cannot be compared: their difference is not a finite number.",
    );
    expect(v.sentence).not.toMatch(/higher|lower|Infinity/);
  });
  it("treats a non-finite value as missing rather than arithmetic", () => {
    const broken = player({
      sleeper_id: "x",
      name: "Broken Row",
      now_points: Number.NaN,
    });
    expect(compareForecasts(broken, mccarthy, NOW).kind).toBe("missing");
  });
  it("names no winner across positions and explains that position and lineup slots matter", () => {
    const v = compareForecasts(flacco, ali, NOW);
    expect(v.kind).toBe("cross_position");
    expect(v.sentence).toBe(
      "Different positions (QB vs RB): raw point totals alone do not settle this roster choice.",
    );
    expect(v.sentence).not.toMatch(/higher|lower|\bby\b/);
  });
  it("carries the standing caveat in plain words", () => {
    expect(CAVEAT).toBe(
      "Projected production; your lineup and roster needs still matter.",
    );
  });
});

describe("formatSignedPoints", () => {
  it("signs every nonzero value with enough decimals to show it", () => {
    expect(formatSignedPoints(47.26)).toBe("+47.3");
    expect(formatSignedPoints(-0.03)).toBe("-0.03");
    expect(formatSignedPoints(-0.0004)).toBe("-0.0004");
    expect(formatSignedPoints(0.00001)).toBe("+<0.0001");
    expect(formatSignedPoints(0)).toBe("0.0");
  });
});

describe("humanizeDate", () => {
  it("renders an ISO timestamp with microseconds and an RFC-1123 date the same readable way, in UTC", () => {
    expect(humanizeDate("2026-09-06T13:00:52.635970+00:00")).toBe(
      "Sep 6, 2026, 13:00 UTC",
    );
    expect(humanizeDate("Sun, 06 Sep 2026 11:28:11 GMT")).toBe(
      "Sep 6, 2026, 11:28 UTC",
    );
  });
  it("passes an unparseable string through unchanged and shows a dash for nothing", () => {
    expect(humanizeDate("league-20260906T130052Z")).toBe("league-20260906T130052Z");
    expect(humanizeDate(null)).toBe("—");
    expect(humanizeDate("")).toBe("—");
  });
});

describe("statusWord", () => {
  it("humanizes an available player's dated status and flags the non-default pool and starting estimates", () => {
    expect(statusWord(flacco, "available")).toBe("active");
    expect(
      statusWord(
        player({ sleeper_id: "1", name: "A", status: "practice_squad" }),
        "available",
      ),
    ).toBe("practice squad");
    expect(
      statusWord(
        player({
          sleeper_id: "11065",
          name: "Adrian Martinez",
          status: "cut",
          population: "cut",
        }),
        "available",
      ),
    ).toBe("cut · outside the default available pool; pickup eligibility not asserted");
    expect(
      statusWord(
        player({ sleeper_id: "12477", name: "Kurtis Rourke", starting_estimate: true }),
        "available",
      ),
    ).toBe("active · starting estimate");
    expect(
      statusWord(
        player({ sleeper_id: "u", name: "U", status: "odd_state" }),
        "available",
      ),
    ).toBe("odd state");
  });
  it("says a roster player is on your roster and adds only an informative status", () => {
    expect(statusWord(mccarthy, "roster")).toBe("on your roster");
    expect(
      statusWord(player({ ...mccarthy, status: "injured_reserve" }), "roster"),
    ).toBe("on your roster · injured reserve");
    expect(
      statusWord(
        player({ ...mccarthy, status: "", starting_estimate: true }),
        "roster",
      ),
    ).toBe("on your roster · starting estimate");
  });
});

describe("classWord", () => {
  it("names the sidecar estimate classes in words and leaves nothing for no class", () => {
    expect(classWord("cold_start_candidate")).toBe("draft-based starting estimate");
    expect(classWord("baseline_research_candidate")).toBe(
      "historical position average",
    );
    expect(classWord("unsupported")).toBe("not estimated by the producer");
    expect(classWord("some_other_class")).toBe("some other class");
    expect(classWord(null)).toBeNull();
    expect(classWord(undefined)).toBeNull();
  });
});
