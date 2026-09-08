import test from "node:test";
import assert from "node:assert/strict";
import {
  readBundle,
  boardRows,
  alternativesFor,
  comparisonPair,
  rankLabel,
  gapLabel,
  pointsLabel,
} from "../src/lib/dg/backend.ts";
const source = {
  report_run: "saved-run",
  report_sha256: "a".repeat(64),
  ownership_as_of: "2026-09-06T13:00:00Z",
  catalog_run: "catalog",
};
function fixture() {
  const row = (
    id: string,
    mine: boolean,
    value: number | null,
    rank: { start: number; end: number; total: number } | null,
  ) => ({
    sleeper_id: id,
    name: id,
    position: "RB",
    team: "BAL",
    on_roster: mine,
    league_ownership: mine ? "Your roster" : "League free agent",
    taxi_or_reserve: null,
    model_value: value,
    market_value: rank ? 42 : null,
    our_rank: rank,
    market_rank: rank ? { start: 1, end: 1, total: 2 } : null,
    model_rank_all: null,
    comparison: rank
      ? { direction: "overlap", gap_min: -1, gap_max: 0 }
      : { direction: "unavailable", gap_min: null, gap_max: null },
    missing_reason: rank ? null : "No saved FantasyCalc price for this player.",
    seasons: [],
    model_zero_tie: value === 0,
    reference_player: null,
  });
  const ranks = [
    row("1", true, 0, { start: 1, end: 2, total: 2 }),
    row("2", false, 0, { start: 1, end: 2, total: 2 }),
  ];
  const available = [
    {
      sleeper_id: "2",
      name: "Available",
      league_position: "RB",
      nfl_team: "BAL",
      population: "default",
      owned_now: false,
      roster_id: null,
      starting_estimate: false,
    },
    {
      sleeper_id: "3",
      name: "Missing",
      league_position: "RB",
      nfl_team: "BAL",
      population: "default",
      owned_now: false,
      roster_id: null,
      starting_estimate: false,
    },
    {
      sleeper_id: "4",
      name: "Other roster",
      league_position: "RB",
      nfl_team: "BAL",
      population: "owned",
      owned_now: true,
      roster_id: 2,
      starting_estimate: false,
    },
    {
      sleeper_id: "5",
      name: "QB available",
      league_position: "QB",
      nfl_team: "BAL",
      population: "default",
      owned_now: false,
      roster_id: null,
      starting_estimate: true,
    },
  ];
  return {
    kind: "dg.read-model.bundle",
    bundle_version: 1,
    generated_at: "2026-09-08T13:00:00Z",
    snapshot: { ...source, forecast_date: "2026-09-06", market_as_of: "2026-09-06T13:00:00Z" },
    basis: { summary: "Five-season projected advantage", years: [2026, 2027, 2028, 2029, 2030] },
    coverage: { total_players: 2, common_players: 2, roster_players: 1 },
    populations: { default: { total: 3 } },
    identity: {
      kind: "headshot_reference",
      path_template: "/assets/headshots/{sleeper_id}.jpg",
      ids: null,
    },
    payloads: {
      market_ranks: { status: "available", source, rows: ranks },
      comparison: {
        source,
        roster: [
          {
            sleeper_id: "1",
            name: "Mine",
            position: "RB",
            now_points: 0,
            future_points: 0,
            seasons: [],
            starting_estimate: false,
          },
        ],
        available: [
          {
            sleeper_id: "2",
            name: "Available",
            position: "RB",
            now_points: 15,
            future_points: 30,
            seasons: [],
            starting_estimate: false,
          },
          {
            sleeper_id: "3",
            name: "Missing",
            position: "RB",
            now_points: null,
            future_points: null,
            seasons: [],
            starting_estimate: false,
          },
          {
            sleeper_id: "5",
            name: "QB available",
            position: "QB",
            now_points: 5,
            future_points: 12,
            seasons: [],
            starting_estimate: true,
          },
        ],
      },
      available: { source: { ...source, pinned: true }, rows: available },
    },
  };
}
test("preserves tied ranks, real zero and the original market price", () => {
  const rows = boardRows(readBundle(fixture()));
  const p = rows.find((x) => x.player_id === "1")!;
  assert.equal(rankLabel(p.our_rank), "1–2");
  assert.equal(p.projected_advantage, 0);
  assert.equal(p.now_points, 0);
  assert.equal(p.market_value, 42);
  assert.equal(gapLabel(p), "Ranks overlap");
  assert.equal("margin" in p, false);
  assert.equal("our_value" in p, false);
});
test("keeps uncovered available players visible with missing, not zero or agreement", () => {
  const p = boardRows(readBundle(fixture())).find((x) => x.player_id === "3")!;
  assert.equal(p.now_points, null);
  assert.equal(p.projected_advantage, null);
  assert.equal(p.market_value, null);
  assert.equal(rankLabel(p.our_rank), "—");
  assert.equal(gapLabel(p), "No comparison");
});
test("alternatives exclude rostered players and other positions without hiding missing forecasts", () => {
  const rows = boardRows(readBundle(fixture()));
  assert.deepEqual(
    alternativesFor(rows, "1")
      .map((x) => x.player_id)
      .sort(),
    ["2", "3"],
  );
  const pair = comparisonPair(rows, "1", "3");
  assert.deepEqual(
    pair.map((x) => x.player_id),
    ["1", "3"],
  );
  assert.throws(() => comparisonPair(rows, "1", "1"));
  assert.throws(() => comparisonPair(rows, "1", "999"));
});
test("market price movement cannot change our independent model value", () => {
  const original = boardRows(readBundle(fixture()));
  const updated = fixture();
  updated.payloads.market_ranks.rows[0].market_value = 9000;
  const changed = boardRows(readBundle(updated));
  assert.deepEqual(
    changed.map((x) => x.projected_advantage),
    original.map((x) => x.projected_advantage),
  );
  assert.equal(changed[0].market_value, 9000);
});
test("rejects mixed snapshots and malformed ranks instead of falling back", () => {
  for (const change of [
    (b: ReturnType<typeof fixture>) =>
      (b.payloads.comparison.source = { ...source, report_sha256: "b".repeat(64) }),
    (b: ReturnType<typeof fixture>) => (b.payloads.available.source.pinned = false),
    (b: ReturnType<typeof fixture>) => (b.payloads.market_ranks.rows[0].our_rank.total = 900),
    (b: ReturnType<typeof fixture>) => (b.bundle_version = 2),
  ]) {
    const b = fixture();
    change(b);
    assert.throws(() => readBundle(b));
  }
});
test("does not substitute export time for forecast date", () => {
  const b = readBundle(fixture());
  assert.equal(b.snapshot.forecast_date, "2026-09-06");
  assert.notEqual(b.snapshot.forecast_date, b.generated_at.slice(0, 10));
});
test("does not attach the catalog owned-player omission note to a valid roster forecast", () => {
  const b = fixture();
  b.payloads.available.rows.push({
    sleeper_id: "1",
    name: "Mine",
    league_position: "RB",
    nfl_team: "BAL",
    population: "owned",
    owned_now: true,
    roster_id: 1,
    starting_estimate: false,
    missing_reason: "owned in your league; forecasts are shown on the research board",
  });
  const row = boardRows(readBundle(b)).find((r) => r.player_id === "1")!;
  assert.equal(row.missing_reason, null);
});
test("rejects a forged comparison or source date even when forecast hashes agree", () => {
  for (const change of [
    (b: ReturnType<typeof fixture>) => (b.payloads.market_ranks.rows[0].comparison.gap_min = 300),
    (b: ReturnType<typeof fixture>) =>
      (b.payloads.market_ranks.rows[0].comparison.direction = "higher"),
    (b: ReturnType<typeof fixture>) =>
      (b.payloads.market_ranks.source = { ...source, market_as_of: "2026-09-08T13:00:00Z" }),
  ]) {
    const b = fixture();
    change(b);
    assert.throws(() => readBundle(b));
  }
});

test("rank gaps say higher or lower without an ambiguous signed range", () => {
  assert.equal(
    gapLabel({ comparison: { direction: "lower", gap_min: -184, gap_max: -26 } }),
    "26–184 places lower",
  );
  assert.equal(
    gapLabel({ comparison: { direction: "higher", gap_min: 110, gap_max: 111 } }),
    "110–111 places higher",
  );
  assert.equal(
    gapLabel({ comparison: { direction: "lower", gap_min: -2, gap_max: -2 } }),
    "2 places lower",
  );
});
test("zero floors stay explicit and do not attach to missing valuations", () => {
  const rows = boardRows(readBundle(fixture()));
  assert.equal(rows.find((r) => r.player_id === "1")!.model_zero_tie, true);
  assert.equal(rows.find((r) => r.player_id === "3")!.model_zero_tie, false);
});
test("small signed forecasts remain distinct from an exact zero", () => {
  assert.equal(pointsLabel(0), "0.0");
  assert.equal(pointsLabel(-0.035094152746863325), "-0.04");
  assert.equal(pointsLabel(-0.005219088248154104), "-0.01");
  assert.equal(pointsLabel(-0.02014271792564188), "-0.02");
  assert.equal(pointsLabel(0.023341), "0.02");
  assert.equal(pointsLabel(-0.00004), "-<0.0001");
  assert.equal(pointsLabel(112.0066), "112.0");
});
