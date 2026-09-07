// Plan T4 (2026-09-06 player comparison): pure helpers for the research preview.
import { describe, expect, it } from "vitest";

import { filterLeague, formatMargin, marginLabel } from "./researchHelpers";

const row = (
  name: string,
  value: number | null,
  position = "WR",
  team: string | null = "KC",
  player_id = name,
) => ({ name, value, position, team, player_id }) as never;

describe("filterLeague", () => {
  const rows = [
    row("Jayden Reed", 0, "WR", "GB"),
    row("Braelon Allen", 0, "RB", "NYJ"),
    row("Jaxson Dart", 134, "QB", "NYG"),
    row("Ashton Jeanty", 181, "RB", "LV"),
    row("Kaelon Black", 43, "RB", null),
  ];
  it("returns nothing for an empty or blank query so the default view stands", () => {
    expect(filterLeague(rows, "")).toEqual([]);
    expect(filterLeague(rows, "   ")).toEqual([]);
  });
  it("matches name, team and position case-insensitively and orders by value desc then name", () => {
    expect(filterLeague(rows, "rb").map((r: { name: string }) => r.name)).toEqual([
      "Ashton Jeanty",
      "Kaelon Black",
      "Braelon Allen",
    ]);
    expect(filterLeague(rows, "ja").map((r: { name: string }) => r.name)).toEqual([
      "Jaxson Dart",
      "Jayden Reed",
    ]);
    expect(filterLeague(rows, "nyj").map((r: { name: string }) => r.name)).toEqual([
      "Braelon Allen",
    ]);
  });
  it("finds a player outside any top-40 slice and returns [] when nothing matches", () => {
    expect(filterLeague(rows, "reed").length).toBe(1);
    expect(filterLeague(rows, "zzz")).toEqual([]);
  });
  it("is deterministic on ties: name, then player id", () => {
    const tied = [
      row("B", 0, "WR", "KC", "2"),
      row("A", 0, "WR", "KC", "3"),
      row("A", 0, "WR", "KC", "1"),
    ];
    expect(
      filterLeague(tied, "wr").map((r: { player_id: string }) => r.player_id),
    ).toEqual(["1", "3", "2"]);
  });
});

describe("marginLabel and formatMargin", () => {
  it("names an exact tie and never a rounded zero direction", () => {
    expect(marginLabel(0)).toBe("equal to reference");
    expect(marginLabel(0.3)).toBe("above reference");
    expect(marginLabel(-0.2)).toBe("below reference");
    expect(formatMargin(0)).toBe("0");
    expect(formatMargin(0.3)).toBe("+0.3");
    expect(formatMargin(-0.2)).toBe("-0.2");
    expect(formatMargin(-0.04)).toBe("-0.04");
    expect(formatMargin(12.445)).toBe("+12");
    expect(formatMargin(-53.61)).toBe("-54");
    expect(`${formatMargin(-0.2)} ${marginLabel(-0.2)}`).not.toMatch(
      /^-?0 (above|below)/,
    );
  });
  it("leaves an absent margin absent", () => {
    expect(marginLabel(null)).toBe("");
    expect(formatMargin(null)).toBe("—");
  });
});

describe("near-zero margins never render as a signed zero", () => {
  it("shows enough decimals for any tiny margin and a within-threshold label below a thousandth", () => {
    expect(formatMargin(0.004)).toBe("+0.004");
    expect(formatMargin(-0.004)).toBe("-0.004");
    expect(formatMargin(0.0004)).toBe("+<0.001");
    expect(formatMargin(-0.00004)).toBe("-<0.001");
    for (const m of [0.004, -0.004, 0.0004, 0.00001, -0.049, 0.09]) {
      const text = `${formatMargin(m)} ${marginLabel(m)}`;
      expect(text).not.toMatch(/^[+-]?0(\.0+)? (above|below)/);
    }
    expect(marginLabel(0.0004)).toBe("within 0.001 of reference");
    expect(marginLabel(-0.004)).toBe("below reference");
  });
});
