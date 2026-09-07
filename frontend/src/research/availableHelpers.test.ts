// Plan T4 (available players): pure helpers — filtering, sorting with honest ties, watchlist storage.
import { describe, expect, it } from "vitest";

import {
  type AvailableRow,
  filterAvailable,
  formatAvailablePoints,
  loadWatchlist,
  saveWatchlist,
  sortAvailable,
  WATCHLIST_KEY,
  watchStatus,
} from "./availableHelpers";

const row = (over: Partial<AvailableRow>): AvailableRow =>
  ({
    sleeper_id: "1",
    player_id: "00-1",
    name: "Some Guy",
    league_position: "WR",
    fantasy_positions: "WR",
    availability_class: "active",
    population: "default",
    nfl_team: "KC",
    nfl_status_raw: "ACT",
    now_points: 100,
    future_points: 300,
    future_years: [2027, 2028, 2029, 2030],
    future_reason: null,
    missing_reason: null,
    impact: { h2: 0, h5: 0 },
    forecast: null,
    ...over,
  }) as AvailableRow;

const rows: AvailableRow[] = [
  row({ sleeper_id: "a", name: "Alpha Wide", now_points: 120.5, future_points: 380 }),
  row({
    sleeper_id: "b",
    name: "Beta Back",
    league_position: "RB",
    nfl_team: "MIN",
    availability_class: "practice_squad",
    now_points: 10,
    future_points: 190,
  }),
  row({
    sleeper_id: "c",
    name: "Charlie End",
    league_position: "TE",
    availability_class: "injured_reserve",
    nfl_status_raw: "RES",
    now_points: -1.5,
    future_points: 4,
  }),
  row({
    sleeper_id: "d",
    name: "Delta Wide",
    nfl_team: "GB",
    now_points: null,
    future_points: null,
    impact: { h2: null, h5: null },
    missing_reason: "no forecast from the selected producers; no reason stated",
  }),
  row({ sleeper_id: "e", name: "Echo Wide", now_points: 120.5, future_points: 200 }),
  row({
    sleeper_id: "f",
    name: "Foxtrot Cut",
    league_position: "QB",
    availability_class: "cut",
    population: "cut",
    nfl_status_raw: "CUT",
    now_points: 50,
    future_points: 100,
  }),
];

describe("filterAvailable", () => {
  it("defaults to the verified active / practice-squad / IR pool and never lets ownership or status invent a forecast", () => {
    const out = filterAvailable(rows, {});
    expect(out.map((r) => r.sleeper_id).sort()).toEqual(["a", "b", "c", "d", "e"]);
    expect(out.find((r) => r.sleeper_id === "d")?.now_points).toBeNull();
  });
  it("applies query, position, status, watched-only and missing-only filters together", () => {
    expect(filterAvailable(rows, { query: "wide" }).map((r) => r.sleeper_id)).toEqual([
      "a",
      "d",
      "e",
    ]);
    expect(filterAvailable(rows, { query: "gb" }).map((r) => r.sleeper_id)).toEqual([
      "d",
    ]);
    expect(
      filterAvailable(rows, { positions: ["RB", "TE"] }).map((r) => r.sleeper_id),
    ).toEqual(["b", "c"]);
    expect(
      filterAvailable(rows, { statuses: ["cut"] }).map((r) => r.sleeper_id),
    ).toEqual(["f"]);
    expect(
      filterAvailable(rows, { statuses: ["active"], missingOnly: true }).map(
        (r) => r.sleeper_id,
      ),
    ).toEqual(["d"]);
    expect(
      filterAvailable(rows, { watchedOnly: true, watched: new Set(["c", "f"]) }).map(
        (r) => r.sleeper_id,
      ),
    ).toEqual(["c"]);
    expect(filterAvailable(rows, { query: "zzz" })).toEqual([]);
  });
});

describe("sortAvailable", () => {
  it("orders by the stated basis, names exact ties, and keeps missing-forecast rows in their own ordered tail", () => {
    const pool = filterAvailable(rows, {});
    const byNow = sortAvailable(pool, "now");
    expect(byNow.ranked.map((r) => r.row.sleeper_id)).toEqual(["a", "e", "b", "c"]);
    expect(byNow.ranked[0]?.tied_with).toEqual(["e"]);
    expect(byNow.ranked[1]?.tied_with).toEqual(["a"]);
    expect(byNow.ranked[2]?.tied_with).toEqual([]);
    expect(byNow.missing.map((m) => m.row.sleeper_id)).toEqual(["d"]);
    expect(byNow.missing[0]?.reason).toBe(
      "no forecast from the selected producers; no reason stated",
    );
    expect(byNow.basis_label).toBe("2026 projected points (championship window)");
    const byFuture = sortAvailable(pool, "future");
    expect(byFuture.ranked.map((r) => r.row.sleeper_id)).toEqual(["a", "e", "b", "c"]);
    expect(byFuture.basis_label).toBe("projected points 2027–2030 summed");
    expect(sortAvailable(pool, "name").ranked.map((r) => r.row.sleeper_id)).toEqual([
      "a",
      "b",
      "c",
      "e",
    ]);
  });
  it("treats an undefined future as missing for the future basis, never as zero", () => {
    const pool = [
      row({
        sleeper_id: "x",
        now_points: 30,
        future_points: null,
        future_reason: "2030 forecast missing",
      }),
      row({ sleeper_id: "y", now_points: 20, future_points: 0 }),
    ];
    const s = sortAvailable(pool, "future");
    expect(s.ranked.map((r) => r.row.sleeper_id)).toEqual(["y"]);
    expect(s.missing.map((m) => m.row.sleeper_id)).toEqual(["x"]);
    expect(s.missing[0]?.reason).toBe("2030 forecast missing");
  });
});

describe("watchlist", () => {
  it("round-trips through storage keyed by stable id and survives corrupt or missing storage", () => {
    const store = new Map<string, string>();
    const storage = {
      getItem: (k: string) => store.get(k) ?? null,
      setItem: (k: string, v: string) => void store.set(k, v),
    };
    expect(loadWatchlist(storage)).toEqual({ entries: new Map(), notice: null });
    const meta = { name: null, position: null, team: null, watched_at: null };
    saveWatchlist(
      storage,
      new Map([
        ["c", meta],
        ["b", meta],
      ]),
    );
    expect([...loadWatchlist(storage).entries.keys()]).toEqual(["b", "c"]);
    store.set(WATCHLIST_KEY, "{not json");
    const bad = loadWatchlist(storage);
    expect(bad.entries.size).toBe(0);
    expect(bad.notice).toMatch(/could not be read/);
    const throwing = {
      getItem: () => {
        throw new Error("blocked");
      },
      setItem: () => {
        throw new Error("blocked");
      },
    };
    expect(loadWatchlist(throwing).notice).toMatch(/unavailable/);
    expect(saveWatchlist(throwing, new Map())).toBe(false);
  });
  it("says plainly when a watched player is no longer available", () => {
    expect(watchStatus(row({ population: "default" }), true)).toBe(
      "watched · available",
    );
    expect(
      watchStatus(row({ population: "cut", availability_class: "cut" }), true),
    ).toBe("watched · left the default pool (cut)");
    expect(watchStatus({ ...row({}), owned_now: true } as AvailableRow, true)).toBe(
      "watched · now owned in your league",
    );
    expect(watchStatus(row({}), false)).toBe("");
  });
});

// ── root's frontend specification review (2026-09-07) ───────────────────────────────────────
describe("filterAvailable — explicit selections", () => {
  it("treats an undefined status filter as the default pool but an explicitly empty selection as no match", () => {
    expect(filterAvailable(rows, {}).length).toBe(5);
    expect(filterAvailable(rows, { statuses: [] })).toEqual([]);
  });
  it("keeps the missing-forecast filter about forecast coverage, never about the sort basis", () => {
    const recovered = row({
      sleeper_id: "g",
      name: "Golf Back",
      league_position: "RB",
      now_points: 30,
      future_points: 150,
      impact: { h2: null, h5: null },
      recovered: true,
      forecast: { producer: "vet", seasons: [] },
    });
    expect(
      filterAvailable([...rows, recovered], { missingOnly: true }).map(
        (r) => r.sleeper_id,
      ),
    ).toEqual(["d"]);
  });
});

describe("sortAvailable — value for THIS ordering", () => {
  const recovered = row({
    sleeper_id: "g",
    name: "Golf Back",
    league_position: "RB",
    now_points: 30,
    future_points: 150,
    impact: { h2: null, h5: null },
    recovered: true,
    forecast: { producer: "vet", seasons: [] },
  });
  const pool = filterAvailable([...rows, recovered], {});
  it("ranks a recovered forecast by points but lists it apart under impact with the specific reason", () => {
    expect(sortAvailable(pool, "now").ranked.map((r) => r.row.sleeper_id)).toEqual([
      "a",
      "e",
      "g",
      "b",
      "c",
    ]);
    const byImpact = sortAvailable(pool, "impact5");
    expect(byImpact.ranked.map((r) => r.row.sleeper_id)).toEqual(["a", "b", "c", "e"]);
    expect(byImpact.missing.map((m) => m.row.sleeper_id)).toEqual(["d", "g"]);
    expect(byImpact.missing[1]?.reason).toBe(
      "recovered forecast: not among the accepted board rows, so it has no impact number",
    );
    expect(byImpact.missing[0]?.reason).toBe(
      "no forecast from the selected producers; no reason stated",
    );
    const partial = row({
      sleeper_id: "h",
      name: "Hotel Wide",
      now_points: 12,
      future_points: null,
      future_reason: "2030 forecast missing: future total undefined, not zero",
    });
    const byFuture = sortAvailable([...pool, partial], "future");
    expect(byFuture.missing.find((m) => m.row.sleeper_id === "h")?.reason).toBe(
      "2030 forecast missing: future total undefined, not zero",
    );
  });
  it("names ties on the selected basis only", () => {
    expect(sortAvailable(pool, "now").ranked[0]?.tied_with).toEqual(["e"]);
    expect(
      sortAvailable(pool, "future").ranked.every((r) => r.tied_with.length === 0),
    ).toBe(true);
  });
});

describe("watchlist — entries with identity metadata, honest repair", () => {
  it("saves nonblank string ids with minimal identity metadata and reads them back", () => {
    const store = new Map<string, string>();
    const storage = {
      getItem: (k: string) => store.get(k) ?? null,
      setItem: (k: string, v: string) => void store.set(k, v),
    };
    const entries = new Map([
      [
        "a",
        {
          name: "Alpha Wide",
          position: "WR",
          team: "KC",
          watched_at: "2026-09-07T01:00:00Z",
        },
      ],
      [
        "f",
        {
          name: "Foxtrot Cut",
          position: "QB",
          team: null,
          watched_at: "2026-09-07T01:00:00Z",
        },
      ],
    ]);
    expect(saveWatchlist(storage, entries)).toBe(true);
    const parsed = JSON.parse(store.get(WATCHLIST_KEY) ?? "{}");
    expect(parsed.version).toBe(2);
    expect(Object.keys(parsed.entries)).toEqual(["a", "f"]);
    const back = loadWatchlist(storage);
    expect(back.notice).toBeNull();
    expect([...back.entries.keys()]).toEqual(["a", "f"]);
    expect(back.entries.get("a")?.name).toBe("Alpha Wide");
  });
  it("migrates a version-1 id list into entries without metadata", () => {
    const storage = {
      getItem: () => JSON.stringify({ version: 1, ids: ["f", "a"] }),
      setItem: () => undefined,
    };
    const out = loadWatchlist(storage);
    expect([...out.entries.keys()]).toEqual(["a", "f"]);
    expect(out.entries.get("f")).toEqual({
      name: null,
      position: null,
      team: null,
      watched_at: null,
    });
    expect(out.notice).toBeNull();
  });
  it("keeps the readable subset of a mixed-corruption payload and says so; blanks and non-strings are never identities", () => {
    const storage = {
      getItem: () => JSON.stringify({ version: 1, ids: ["a", null, "", " ", 7] }),
      setItem: () => undefined,
    };
    const out = loadWatchlist(storage);
    expect([...out.entries.keys()]).toEqual(["a"]);
    expect(out.notice).toBe(
      "The saved watchlist had 4 unreadable entries, which were ignored; the 1 readable one was kept.",
    );
    const v2 = {
      getItem: () =>
        JSON.stringify({
          version: 2,
          entries: {
            a: { name: "Alpha Wide", position: "WR", team: "KC", watched_at: null },
            "": { name: "x" },
            b: "bad",
            c: { name: 5 },
          },
        }),
      setItem: () => undefined,
    };
    const out2 = loadWatchlist(v2);
    expect([...out2.entries.keys()]).toEqual(["a"]);
    expect(out2.notice).toBe(
      "The saved watchlist had 3 unreadable entries, which were ignored; the 1 readable one was kept.",
    );
    const none = {
      getItem: () => JSON.stringify({ version: 1, ids: [null, ""] }),
      setItem: () => undefined,
    };
    expect([...loadWatchlist(none).entries.keys()]).toEqual([]);
    expect(loadWatchlist(none).notice).toBe(
      "The saved watchlist had 2 unreadable entries and no readable one; watch players again to rebuild it.",
    );
  });
  it("says plainly when a watched id is not in the current census", () => {
    expect(watchStatus(undefined, true)).toBe(
      "watched · not in the current census; identity unresolved",
    );
  });
});

describe("formatAvailablePoints — a nonzero value never prints as zero", () => {
  it("keeps one decimal for ordinary values, adds precision under 0.1, and keeps exact zero as 0.0", () => {
    expect(formatAvailablePoints(0)).toBe("0.0");
    expect(formatAvailablePoints(120.5)).toBe("120.5");
    expect(formatAvailablePoints(-1.5)).toBe("-1.5");
    expect(formatAvailablePoints(-0.035094)).toBe("-0.04");
    expect(formatAvailablePoints(-0.005219)).toBe("-0.01");
    expect(formatAvailablePoints(0.023341)).toBe("0.02");
    expect(formatAvailablePoints(0.007147)).toBe("0.01");
    expect(formatAvailablePoints(0.0004)).toBe("0.0004");
    expect(formatAvailablePoints(0.00004)).toBe("+<0.0001");
    expect(formatAvailablePoints(-0.00004)).toBe("-<0.0001");
    expect(formatAvailablePoints(null)).toBe("—");
  });
});

describe("watchlist — container and entry shapes", () => {
  it("rejects an array container as unreadable and drops array entries with a repair notice; never fabricates an id", () => {
    const arrayContainer = {
      getItem: () => JSON.stringify({ version: 2, entries: [{ name: "Alpha" }] }),
      setItem: () => undefined,
    };
    const out = loadWatchlist(arrayContainer);
    expect(out.entries.size).toBe(0);
    expect(out.notice).toMatch(/could not be read/);
    const arrayEntry = {
      getItem: () =>
        JSON.stringify({
          version: 2,
          entries: {
            a: [],
            b: { name: "Beta Back", position: "RB", team: null, watched_at: null },
          },
        }),
      setItem: () => undefined,
    };
    const out2 = loadWatchlist(arrayEntry);
    expect([...out2.entries.keys()]).toEqual(["b"]);
    expect(out2.notice).toBe(
      "The saved watchlist had 1 unreadable entry, which was ignored; the 1 readable one was kept.",
    );
  });
});
