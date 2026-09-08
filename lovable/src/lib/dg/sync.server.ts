import { LEAGUE, MODEL_VERSION, POSITIONS } from "./league";
import { assignTier, scorePlayer, type Position, type ProductionRow } from "./model";

type Admin = Awaited<ReturnType<typeof getAdmin>>;

async function getAdmin() {
  const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
  return supabaseAdmin;
}

/* ------------------------------ tiny csv reader ------------------------------ */

function parseCsv(text: string): Record<string, string>[] {
  const rows: string[][] = [];
  let field = "";
  let row: string[] = [];
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i += 1;
        } else quoted = false;
      } else field += ch;
      continue;
    }
    if (ch === '"') quoted = true;
    else if (ch === ",") {
      row.push(field);
      field = "";
    } else if (ch === "\n") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else if (ch !== "\r") field += ch;
  }
  if (field.length || row.length) {
    row.push(field);
    rows.push(row);
  }
  const header = rows.shift() ?? [];
  return rows
    .filter((r) => r.length > 1)
    .map((r) => {
      const obj: Record<string, string> = {};
      header.forEach((h, idx) => {
        obj[h] = r[idx] ?? "";
      });
      return obj;
    });
}

/** jsonb payloads: the generated types want Json; keep the call sites readable. */
const j = (v: unknown) => v as never;

const num = (v: string | undefined) => {
  if (v == null || v === "" || v === "NA") return 0;
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
};

/* --------------------------------- sources --------------------------------- */

type SleeperPlayer = {
  player_id: string;
  full_name?: string;
  first_name?: string;
  last_name?: string;
  position?: string;
  team?: string | null;
  age?: number;
  birth_date?: string;
  years_exp?: number;
  college?: string;
  status?: string;
  injury_status?: string | null;
  gsis_id?: string | null;
  metadata?: Record<string, string> | null;
  active?: boolean;
};

type MarketRow = {
  sleeperId: string | null;
  value: number;
  overallRank: number;
  positionRank: number;
  trend30Day: number | null;
  draftYear: number | null;
  draftRound: number | null;
  draftPick: number | null;
  age: number | null;
};

async function fetchSleeperPlayers(): Promise<Record<string, SleeperPlayer>> {
  const res = await fetch("https://api.sleeper.app/v1/players/nfl");
  if (!res.ok) throw new Error(`Sleeper player universe unavailable (${res.status})`);
  return (await res.json()) as Record<string, SleeperPlayer>;
}

async function fetchMarket(): Promise<Map<string, MarketRow>> {
  const res = await fetch(
    "https://api.fantasycalc.com/values/current?isDynasty=true&numQbs=2&numTeams=12&ppr=1",
  );
  if (!res.ok) throw new Error(`Market prices unavailable (${res.status})`);
  const raw = (await res.json()) as Array<{
    player: {
      sleeperId: string | null;
      maybeAge: number | null;
      maybeDraftInfo?: { year: number; round: number; pick: number } | null;
    };
    value: number;
    overallRank: number;
    positionRank: number;
    trend30Day: number | null;
  }>;
  const map = new Map<string, MarketRow>();
  for (const entry of raw) {
    const id = entry.player?.sleeperId;
    if (!id) continue;
    map.set(String(id), {
      sleeperId: String(id),
      value: entry.value,
      overallRank: entry.overallRank,
      positionRank: entry.positionRank,
      trend30Day: entry.trend30Day ?? null,
      draftYear: entry.player.maybeDraftInfo?.year ?? null,
      draftRound: entry.player.maybeDraftInfo?.round ?? null,
      draftPick: entry.player.maybeDraftInfo?.pick ?? null,
      age: entry.player.maybeAge ?? null,
    });
  }
  return map;
}

/**
 * Sleeper's own file only carries a league-office id for a fraction of players,
 * so production would go missing for most of the universe. This crosswalk ties
 * a Sleeper player to his league-office id, which is how production is filed.
 */
async function fetchCrosswalk(): Promise<Map<string, string>> {
  const map = new Map<string, string>();
  const res = await fetch(
    "https://raw.githubusercontent.com/dynastyprocess/data/master/files/db_playerids.csv",
  );
  if (!res.ok) return map;
  for (const r of parseCsv(await res.text())) {
    const sleeper = r["sleeper_id"];
    const gsis = r["gsis_id"];
    if (sleeper && gsis) map.set(String(sleeper), String(gsis));
  }
  return map;
}

async function fetchProduction(): Promise<Map<string, ProductionRow[]>> {
  const seasons = [2023, 2024, 2025];
  const out = new Map<string, ProductionRow[]>();
  for (const season of seasons) {
    const url = `https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_reg_${season}.csv`;
    const res = await fetch(url);
    if (!res.ok) continue;
    const rows = parseCsv(await res.text());
    for (const r of rows) {
      const gsis = r["player_id"];
      if (!gsis) continue;
      const row: ProductionRow = {
        season,
        games: num(r["games"]),
        pprPoints: num(r["fantasy_points_ppr"]),
        targets: num(r["targets"]),
        carries: num(r["carries"]),
        attempts: num(r["attempts"]),
        targetShare: num(r["target_share"]),
      };
      const list = out.get(gsis) ?? [];
      list.push(row);
      out.set(gsis, list);
    }
  }
  return out;
}

/* ---------------------------------- league ---------------------------------- */

async function syncLeague(admin: Admin, players: Record<string, SleeperPlayer>) {
  const [rostersRes, usersRes, picksRes, txRes] = await Promise.all([
    fetch(`https://api.sleeper.app/v1/league/${LEAGUE.id}/rosters`),
    fetch(`https://api.sleeper.app/v1/league/${LEAGUE.id}/users`),
    fetch(`https://api.sleeper.app/v1/league/${LEAGUE.id}/traded_picks`),
    fetch(`https://api.sleeper.app/v1/league/${LEAGUE.id}/transactions/1`),
  ]);
  const rosters = (await rostersRes.json()) as Array<{
    roster_id: number;
    owner_id: string;
    players: string[] | null;
    starters: string[] | null;
    reserve: string[] | null;
    taxi: string[] | null;
    settings?: {
      wins?: number;
      losses?: number;
      ties?: number;
      fpts?: number;
      fpts_decimal?: number;
    };
  }>;
  const users = (await usersRes.json()) as Array<{
    user_id: string;
    display_name: string;
    avatar: string | null;
    metadata?: { team_name?: string };
  }>;

  const userById = new Map(users.map((u) => [u.user_id, u]));

  await admin.from("league_teams").upsert(
    rosters.map((r) => {
      const user = userById.get(r.owner_id);
      return {
        roster_id: r.roster_id,
        owner_id: r.owner_id,
        display_name: user?.display_name ?? null,
        team_name: user?.metadata?.team_name ?? user?.display_name ?? null,
        avatar: user?.avatar ?? null,
        is_mine: r.owner_id === LEAGUE.ownerSleeperUserId,
        wins: r.settings?.wins ?? null,
        losses: r.settings?.losses ?? null,
        ties: r.settings?.ties ?? null,
        points_for: (r.settings?.fpts ?? 0) + (r.settings?.fpts_decimal ?? 0) / 100,
        updated_at: new Date().toISOString(),
      };
    }),
    { onConflict: "roster_id" },
  );

  const rosterRows: Array<{ roster_id: number; player_id: string; slot: string }> = [];
  for (const r of rosters) {
    const starters = new Set(r.starters ?? []);
    const reserve = new Set(r.reserve ?? []);
    const taxi = new Set(r.taxi ?? []);
    for (const pid of r.players ?? []) {
      if (!players[pid]) continue;
      const slot = starters.has(pid)
        ? "starter"
        : reserve.has(pid)
          ? "ir"
          : taxi.has(pid)
            ? "taxi"
            : "bench";
      rosterRows.push({ roster_id: r.roster_id, player_id: pid, slot });
    }
  }
  await admin.from("roster_players").delete().gte("roster_id", 0);
  for (let i = 0; i < rosterRows.length; i += 500) {
    await admin.from("roster_players").insert(rosterRows.slice(i, i + 500));
  }

  const picks = (await picksRes.json()) as Array<{
    season: string;
    round: number;
    roster_id: number;
    owner_id: number;
  }>;
  if (Array.isArray(picks) && picks.length) {
    await admin.from("draft_picks").upsert(
      picks.map((p) => ({
        season: p.season,
        round: p.round,
        original_roster_id: p.roster_id,
        owner_roster_id: p.owner_id,
        updated_at: new Date().toISOString(),
      })),
      { onConflict: "season,round,original_roster_id" },
    );
  }

  const tx = (await txRes.json().catch(() => [])) as Array<{
    transaction_id: string;
    type: string;
    status: string;
    leg: number;
    created: number;
    roster_ids: number[];
    adds: Record<string, number> | null;
    drops: Record<string, number> | null;
    draft_picks: unknown[] | null;
  }>;
  if (Array.isArray(tx) && tx.length) {
    await admin.from("league_transactions").upsert(
      tx.map((t) => ({
        transaction_id: t.transaction_id,
        type: t.type,
        status: t.status,
        week: t.leg ?? null,
        created_ms: t.created,
        roster_ids: t.roster_ids,
        adds: t.adds ?? null,
        drops: t.drops ?? null,
        draft_picks: j(t.draft_picks ?? null),
        raw: j(t),
      })),
      { onConflict: "transaction_id" },
    );
  }

  return {
    teams: rosters.length,
    rosterSpots: rosterRows.length,
    transactions: Array.isArray(tx) ? tx.length : 0,
  };
}

/* ---------------------------------- the run ---------------------------------- */

export async function runFullSync() {
  const admin = await getAdmin();
  const started = new Date().toISOString();

  const [universe, market, production, crosswalk] = await Promise.all([
    fetchSleeperPlayers(),
    fetchMarket(),
    fetchProduction(),
    fetchCrosswalk(),
  ]);

  const leagueResult = await syncLeague(admin, universe);

  const kept = Object.values(universe).filter(
    (p) =>
      p.position &&
      (POSITIONS as readonly string[]).includes(p.position) &&
      (market.has(p.player_id) || p.active !== false),
  );

  // players table
  const playerRows = kept.map((p) => {
    const m = market.get(p.player_id);
    return {
      player_id: p.player_id,
      full_name:
        p.full_name ?? (`${p.first_name ?? ""} ${p.last_name ?? ""}`.trim() || "Unnamed player"),
      first_name: p.first_name ?? null,
      last_name: p.last_name ?? null,
      position: p.position ?? null,
      team: p.team ?? null,
      age: p.age ?? m?.age ?? null,
      birth_date: p.birth_date ?? null,
      years_exp: p.years_exp ?? null,
      college: p.college ?? null,
      draft_round: m?.draftRound ?? null,
      draft_pick: m?.draftPick ?? null,
      draft_year: m?.draftYear ?? null,
      status: p.status ?? null,
      injury_status: p.injury_status ?? null,
      headshot_url: `https://sleepercdn.com/content/nfl/players/${p.player_id}.jpg`,
      fantasycalc_id: m ? p.player_id : null,
      active: p.active !== false,
      updated_at: new Date().toISOString(),
    };
  });
  for (let i = 0; i < playerRows.length; i += 500) {
    await admin.from("players").upsert(playerRows.slice(i, i + 500), { onConflict: "player_id" });
  }

  // score every kept player
  type Scored = {
    playerId: string;
    position: Position;
    age: number | null;
    score: number;
    perGame: number | null;
    weightedGames: number;
    parts: Record<string, unknown>;
  };
  const scored: Scored[] = [];
  const unscored: Array<{ playerId: string; reason: string }> = [];

  for (const p of kept) {
    const gsis = crosswalk.get(p.player_id) ?? p.gsis_id ?? null;
    const rows = gsis ? (production.get(gsis) ?? []) : [];
    const m = market.get(p.player_id);
    const out = scorePlayer({
      position: p.position as Position,
      age: p.age ?? m?.age ?? null,
      yearsExp: p.years_exp ?? null,
      draftRound: m?.draftRound ?? null,
      draftPick: m?.draftPick ?? null,
      production: rows,
    });
    if (out.score == null) {
      unscored.push({ playerId: p.player_id, reason: out.reason ?? "no active model score" });
      continue;
    }
    scored.push({
      playerId: p.player_id,
      position: p.position as Position,
      age: p.age ?? m?.age ?? null,
      score: out.score,
      perGame: out.parts.productionPerGame,
      weightedGames: out.parts.weightedGames,
      parts: out.parts as unknown as Record<string, unknown>,
    });
  }

  scored.sort((a, b) => b.score - a.score);

  // Put our worth in the market's own units: our rank reads off the market's
  // value curve, so a margin is a like-for-like comparison, never apples to oranges.
  const marketValues = [...market.values()].map((m) => m.value).sort((a, b) => b - a);
  const valueAtRank = (rank: number) => {
    if (!marketValues.length) return null;
    const idx = Math.min(marketValues.length - 1, rank - 1);
    return marketValues[idx] ?? marketValues[marketValues.length - 1] ?? null;
  };

  const posCounters: Record<string, number> = {};
  const snapshotDate = new Date().toISOString().slice(0, 10);
  const dayRows = scored.map((s, idx) => {
    const rank = idx + 1;
    posCounters[s.position] = (posCounters[s.position] ?? 0) + 1;
    const ourValue = valueAtRank(rank);
    const m = market.get(s.playerId);
    const marketValue = m?.value ?? null;
    const tier = assignTier({
      rank,
      poolSize: scored.length,
      age: s.age,
      perGame: s.perGame,
      weightedGames: s.weightedGames,
      position: s.position,
    });
    return {
      snapshot_date: snapshotDate,
      player_id: s.playerId,
      our_value: ourValue,
      our_rank: rank,
      our_pos_rank: posCounters[s.position] ?? null,
      market_value: marketValue,
      market_rank: m?.overallRank ?? null,
      market_pos_rank: m?.positionRank ?? null,
      margin:
        ourValue != null && marketValue != null
          ? Number((ourValue - marketValue).toFixed(1))
          : null,
      margin_pct:
        ourValue != null && marketValue
          ? Number((((ourValue - marketValue) / marketValue) * 100).toFixed(1))
          : null,
      rank_margin: m?.overallRank != null ? m.overallRank - rank : null,
      tier: tier.tier,
      tier_basis: j(tier.basis),
      model_version: MODEL_VERSION,
      receipts: j({
        inputs: s.parts,
        marketTrend30Day: m?.trend30Day ?? null,
        howOurWorthIsSet:
          "Our rank is read off the market's own value curve, so both prices share one set of units.",
        sources: [
          "Sleeper player universe",
          "FantasyCalc dynasty superflex",
          "nflverse regular-season production",
        ],
      }),
    };
  });

  const unscoredRows = unscored.map((u) => ({
    snapshot_date: snapshotDate,
    player_id: u.playerId,
    our_value: null,
    our_rank: null,
    our_pos_rank: null,
    market_value: market.get(u.playerId)?.value ?? null,
    market_rank: market.get(u.playerId)?.overallRank ?? null,
    market_pos_rank: market.get(u.playerId)?.positionRank ?? null,
    margin: null,
    margin_pct: null,
    rank_margin: null,
    tier: null,
    tier_basis: j({ note: u.reason }),
    model_version: MODEL_VERSION,
    receipts: j({ absence: u.reason }),
  }));

  const all = [...dayRows, ...unscoredRows];
  for (let i = 0; i < all.length; i += 500) {
    await admin
      .from("player_days")
      .upsert(all.slice(i, i + 500), { onConflict: "snapshot_date,player_id" });
  }

  const detail = {
    players: playerRows.length,
    scored: scored.length,
    unscored: unscored.length,
    market: market.size,
    withProduction: scored.filter((s) => (s.weightedGames ?? 0) > 0).length,
    ...leagueResult,
  };

  await admin.from("sync_runs").insert({
    source: "sleeper + fantasycalc + nflverse",
    status: "ok",
    started_at: started,
    finished_at: new Date().toISOString(),
    rows_written: all.length,
    detail: j(detail),
  });

  return detail;
}
