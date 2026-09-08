import type { Tier } from "./copy";

export type Position = "QB" | "RB" | "WR" | "TE";

export type ProductionRow = {
  season: number;
  games: number;
  pprPoints: number;
  targets: number;
  carries: number;
  attempts: number;
  targetShare: number;
};

export type ScoreInput = {
  position: Position;
  age: number | null;
  yearsExp: number | null;
  draftRound: number | null;
  draftPick: number | null;
  production: ProductionRow[];
};

export type ScoreOutput = {
  score: number | null;
  parts: {
    productionPerGame: number | null;
    weightedGames: number;
    opportunity: number | null;
    draftPrior: number | null;
    ageMultiplier: number;
    positionWeight: number;
    seasonsUsed: number[];
  };
  reason?: string;
};

const SEASON_WEIGHTS: Record<number, number> = { 2025: 0.6, 2024: 0.26, 2023: 0.14 };

/** Superflex, full PPR, no tight end premium — quarterbacks carry more roster value. */
const POSITION_WEIGHT: Record<Position, number> = { QB: 1.24, RB: 0.92, WR: 1.0, TE: 0.9 };

/** Peak age and how fast worth decays either side of it, by position. */
const AGE_CURVE: Record<Position, { peak: number; rise: number; fall: number }> = {
  QB: { peak: 27, rise: 0.02, fall: 0.045 },
  RB: { peak: 24, rise: 0.03, fall: 0.11 },
  WR: { peak: 26, rise: 0.025, fall: 0.075 },
  TE: { peak: 27, rise: 0.03, fall: 0.07 },
};

export function ageMultiplier(position: Position, age: number | null): number {
  if (age == null) return 1;
  const curve = AGE_CURVE[position];
  const gap = age - curve.peak;
  const raw = gap <= 0 ? 1 - Math.abs(gap) * curve.rise : 1 - gap * curve.fall;
  return Math.max(0.35, Math.min(1.12, raw));
}

/** Draft capital only carries weight while a player has little NFL production. */
export function draftPrior(round: number | null, pick: number | null): number | null {
  if (round == null) return null;
  const overall = pick != null && pick > 0 ? (round - 1) * 32 + pick : (round - 1) * 32 + 16;
  return Math.max(0, 1 - Math.log(overall + 4) / Math.log(260));
}

function opportunityScore(position: Position, rows: ProductionRow[]): number | null {
  const usable = rows.filter((r) => r.games > 0);
  if (!usable.length) return null;
  let total = 0;
  let weight = 0;
  for (const row of usable) {
    const w = SEASON_WEIGHTS[row.season] ?? 0.05;
    let value: number;
    if (position === "QB") value = row.attempts / row.games / 38;
    else if (position === "RB") value = (row.carries + row.targets) / row.games / 22;
    else value = row.targetShare > 0 ? row.targetShare / 0.3 : row.targets / row.games / 9;
    total += Math.max(0, Math.min(1.4, value)) * w;
    weight += w;
  }
  return weight ? total / weight : null;
}

export function scorePlayer(input: ScoreInput): ScoreOutput {
  const rows = input.production.filter((r) => r.games > 0 && SEASON_WEIGHTS[r.season] != null);
  const prior = draftPrior(input.draftRound, input.draftPick);
  const age = input.age;
  const ageMult = ageMultiplier(input.position, age);
  const posWeight = POSITION_WEIGHT[input.position];

  let weighted = 0;
  let weight = 0;
  let gamesWeighted = 0;
  for (const row of rows) {
    const w = SEASON_WEIGHTS[row.season] ?? 0.05;
    weighted += (row.pprPoints / row.games) * w;
    weight += w;
    gamesWeighted += row.games * w;
  }
  const perGame = weight ? weighted / weight : null;
  const opportunity = opportunityScore(input.position, rows);

  if (perGame == null && prior == null) {
    return {
      score: null,
      parts: {
        productionPerGame: null,
        weightedGames: 0,
        opportunity: null,
        draftPrior: null,
        ageMultiplier: ageMult,
        positionWeight: posWeight,
        seasonsUsed: [],
      },
      reason: "no production on file and no draft capital to lean on",
    };
  }

  // Production is the spine. Opportunity separates two players whose points
  // look alike. Draft capital only fills the gap while production is thin.
  const cap = input.position === "QB" ? 26 : 20;
  const productionUnit = perGame == null ? 0 : Math.min(1.35, perGame / cap);
  const confidence = Math.min(1, gamesWeighted / 14);
  const priorUnit = prior ?? 0;

  const blended =
    productionUnit * (0.66 * confidence) +
    (opportunity ?? 0) * (0.16 * confidence) +
    priorUnit * (0.18 + 0.66 * (1 - confidence));

  return {
    score: Math.max(0, blended * ageMult * posWeight),
    parts: {
      productionPerGame: perGame,
      weightedGames: Number(gamesWeighted.toFixed(1)),
      opportunity: opportunity == null ? null : Number(opportunity.toFixed(3)),
      draftPrior: prior == null ? null : Number(prior.toFixed(3)),
      ageMultiplier: Number(ageMult.toFixed(3)),
      positionWeight: posWeight,
      seasonsUsed: rows.map((r) => r.season).sort(),
    },
  };
}

/**
 * A tier is only legal when a calibration earns it: the player's place in the
 * scored field plus a production or opportunity floor. The basis is disclosed.
 */
export function assignTier(args: {
  rank: number;
  poolSize: number;
  age: number | null;
  perGame: number | null;
  weightedGames: number;
  position: Position;
}): { tier: Tier | null; basis: Record<string, unknown> } {
  const pct = args.rank / args.poolSize;
  const seen = args.weightedGames >= 6;
  const basis: Record<string, unknown> = {
    rank: args.rank,
    scoredPool: args.poolSize,
    percentile: Number((pct * 100).toFixed(1)),
    pointsPerGame: args.perGame == null ? null : Number(args.perGame.toFixed(1)),
    weightedGames: args.weightedGames,
    age: args.age,
  };

  if (!seen && pct > 0.06) {
    return { tier: null, basis: { ...basis, note: "too little NFL time to calibrate a tier" } };
  }
  if (pct <= 0.01)
    return { tier: "Generational", basis: { ...basis, band: "top 1% of the scored field" } };
  if (pct <= 0.05)
    return { tier: "Elite", basis: { ...basis, band: "top 5% of the scored field" } };
  if (pct <= 0.15 && args.age != null && args.age <= 25) {
    return { tier: "Cornerstone", basis: { ...basis, band: "top 15% and 25 or younger" } };
  }
  if (pct <= 0.4)
    return { tier: "Starter", basis: { ...basis, band: "top 40% of the scored field" } };
  return { tier: "Depth", basis: { ...basis, band: "outside the top 40% of the scored field" } };
}
