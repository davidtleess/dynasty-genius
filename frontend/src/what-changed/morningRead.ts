/**
 * DG-113 — THE MORNING READ, ASSEMBLED.
 *
 * The screen David opens every season morning has to answer three questions in
 * one glance: *am I ok · what moved · what should I look at.* The first and the
 * third are SENTENCES, and a sentence is the most dangerous thing this product
 * can render — it reads as a conclusion whether or not one was computed.
 *
 * So every clause built in this module is traceable to a field in the payload,
 * and the module is pure: no DOM, no fetch, no clock beyond what is handed in.
 * The rules it holds itself to, in order of how much trouble each has caused:
 *
 * 1. NO CLAUSE WITHOUT A FIELD. If the input is absent the sentence says which
 *    input is absent and that it will be back — it never estimates, and it
 *    never turns "we have no data" into "nothing is wrong". The phase-2A panel
 *    caught three cases of confident prose asserting what the producer never
 *    claimed; every branch below names the producer line it rests on.
 *
 * 2. SILENCE IS NOT A VERDICT. An empty delta list can mean "we compared and
 *    nothing moved" or "we never compared" — daily_diff.py:111-117 returns
 *    `insufficient_history` with no `aborted_reason` at all — and only the
 *    first of those licenses "nothing moved". `movement()` takes the
 *    comparison's own status, not the length of a list.
 *
 * 3. SCOPE TRAVELS WITH THE NUMBER. `roster_deltas` holds every roster player
 *    the market priced IN BOTH captures (daily_diff.py:143-147) — not every
 *    player on the roster. So the coverage is stated wherever a "your roster"
 *    total is, rather than being quietly rounded up to the whole roster.
 *
 * 4. THE SPEC'S EXAMPLE COPY IS A STARTING POINT, NOT A CAGE — AND NOT A
 *    SOURCE. DG091-STUDIO-SPEC.md §2.3 offers "The market has run him up +306
 *    this month to 5,082 — 30th overall, 11th among QBs — while our model
 *    prices him lower than that." Read against the payload, three of those
 *    clauses are false or unsupported: `value_delta` is DAY-over-day (the
 *    comparison window is two adjacent capture dates), the payload carries rank
 *    DELTAS and no absolute rank at all, and there is no model price anywhere
 *    on a market row to compare against. What survives is what the fields say.
 */

import type {
  WhatChangedCutCandidate,
  WhatChangedMarketDelta,
  WhatChangedMarketSection,
  WhatChangedResponse,
  WhatChangedStructuralSection,
} from "../lib/api/types.gen";
import {
  describeToken,
  positionGroup,
  VALUE_OVER_REPLACEMENT,
  valueWord,
} from "../lib/copy";

// ── shared formatting ────────────────────────────────────────────────────────

/** Thousands separators, host-locale-independent (CI-stable). */
export function num(value: number): string {
  return value.toLocaleString("en-US");
}

/** A signed change said in words: "up 306", "down 97". */
export function movementWords(delta: number): string {
  return `${delta > 0 ? "up" : "down"} ${num(Math.abs(delta))}`;
}

const WEEKDAY = new Intl.DateTimeFormat("en-US", {
  timeZone: "America/New_York",
  weekday: "long",
});

/**
 * A calendar date as its weekday. Date-only strings are anchored at noon before
 * formatting: parsed raw they land at UTC midnight, which America/New_York
 * renders as the previous evening — an off-by-one weekday (the same trap
 * `ui/DailyTape.tsx` documents).
 */
function weekday(date: string): string | null {
  const parsed = Date.parse(`${date}T12:00:00`);
  return Number.isNaN(parsed) ? null : WEEKDAY.format(new Date(parsed));
}

export type ComparisonWindow = { from_date?: string | null; to_date?: string | null };

/**
 * How to say "since the last capture" for THIS window.
 *
 * "Overnight" is a claim about elapsed time and it is only true when the two
 * compared captures are adjacent days. The market window is `dates[-2]` vs
 * `dates[-1]` (daily_diff.py:119) — consecutive most mornings, but a missed
 * capture makes them two days apart or more, and the word would then be a small
 * lie repeated on every sentence of the page. Wider windows name the two days
 * instead; an unreadable window falls back to the neutral phrase.
 */
export function windowPhrase(window: ComparisonWindow | null | undefined): string {
  const from = window?.from_date;
  const to = window?.to_date;
  if (typeof from !== "string" || typeof to !== "string") {
    return "since the last capture";
  }
  const fromMs = Date.parse(`${from}T12:00:00`);
  const toMs = Date.parse(`${to}T12:00:00`);
  if (Number.isNaN(fromMs) || Number.isNaN(toMs)) {
    return "since the last capture";
  }
  const days = Math.round((toMs - fromMs) / 86_400_000);
  if (days === 1) {
    return "overnight";
  }
  const fromDay = weekday(from);
  const toDay = weekday(to);
  return fromDay && toDay
    ? `between ${fromDay} and ${toDay}`
    : "since the last capture";
}

// ── the market comparison: did it happen at all? ──────────────────────────────

/**
 * The producer's own reasons for not comparing, or an empty list when it did.
 *
 * The market lane reports trouble on TWO axes and only one is an
 * `aborted_reason` — `status` is the closed set {ok, unavailable,
 * insufficient_history} (daily_diff.py:100-118, :150-165). This is the same
 * read `DailyWhatChanged.tsx` uses for its lane notice; it lives here so the
 * verdict and the notice can never disagree about whether a comparison ran.
 */
export function marketReasons(market: WhatChangedMarketSection): string[] {
  if (market.aborted_reason) return [market.aborted_reason];
  return market.status !== "ok" ? [market.status] : [];
}

// ── what moved on his roster ─────────────────────────────────────────────────

export type RosterMovement =
  | { kind: "not-compared"; sentence: string }
  | { kind: "none-priced"; sentence: string }
  | { kind: "flat"; sentence: string; priced: number }
  | {
      kind: "moved";
      sentence: string;
      /**
       * The same sentence in three pieces, split at the largest mover's name.
       *
       * DG-110's rule — every player name in the product is a press target
       * onto his card — applied to the ValueHero's basis line, which is the
       * element the verdict replaced. Handing the caller the pieces keeps the
       * name a handle without anyone splitting prose on a substring at render
       * time, and `sentence` stays the single source the two forms agree on.
       */
      parts: { lead: string; name: string; tail: string };
      priced: number;
      movers: number;
      largest: WhatChangedMarketDelta;
    };

/**
 * The movement half of the verdict, and the only place the page states a
 * roster-wide total.
 *
 * `rosterCount` is `sleeper_snapshot.david_roster_player_count`. It is
 * comparable to `roster_deltas.length` for one specific reason, verified rather
 * than assumed: both are derived from the SAME roster membership set — the
 * `players` array of the roster whose `roster_id` matches `david_roster_id`, in
 * the same injected snapshot file (report.py:441-444 and
 * daily_diff.py:476-479 read it identically). So "the market priced 26 of your
 * 27 players" is a fact about one roster, not two.
 */
export function movement(
  market: WhatChangedMarketSection,
  rosterCount: number | null,
): RosterMovement {
  const reasons = marketReasons(market);
  const when = windowPhrase(market.comparison_window as ComparisonWindow | null);
  if (reasons.length > 0) {
    return {
      kind: "not-compared",
      // Worded to be unreadable as "nothing moved". An earlier draft ended
      // "…so there is no movement to report", which a reader scanning the
      // sentence takes as the very claim the branch exists to refuse.
      sentence:
        "We couldn't compare your prices against an earlier day, so we can't say " +
        "what moved.",
    };
  }
  const rows = market.roster_deltas ?? [];
  if (rows.length === 0) {
    return {
      kind: "none-priced",
      // NOT "nothing moved": the comparison ran, and it found none of his
      // players carrying a price on both dates. That is a coverage fact.
      sentence:
        "The market didn't price any of your players on both of the last two days, " +
        "so there is nothing of yours to compare.",
    };
  }
  const coverage =
    rosterCount !== null && rosterCount > rows.length
      ? `The market priced ${num(rows.length)} of your ${num(rosterCount)} players`
      : `The market priced all ${num(rows.length)} of your players`;
  const movers = rows.filter((row) => row.value_delta !== 0);
  if (movers.length === 0) {
    return {
      kind: "flat",
      priced: rows.length,
      sentence: `${coverage}, and not one of them moved ${when}.`,
    };
  }
  const largest = movers.reduce((best, row) =>
    Math.abs(row.value_delta) > Math.abs(best.value_delta) ? row : best,
  );
  const howMany =
    movers.length === rows.length
      ? `every one of them moved ${when}`
      : `${num(movers.length)} of them moved ${when}`;
  const name = largest.player_name ?? largest.player_key;
  const level =
    largest.current_value != null ? ` to ${num(largest.current_value)}` : "";
  const lead = `${coverage}, and ${howMany} — `;
  const tail = ` most of all, ${movementWords(largest.value_delta)}${level}.`;
  return {
    kind: "moved",
    priced: rows.length,
    movers: movers.length,
    largest,
    parts: { lead, name, tail },
    sentence: `${lead}${name}${tail}`,
  };
}

// ── the roster limit: the one action this report can actually detect ─────────

export type CutPressure =
  | { kind: "clear"; totalPlayers: number; totalCapacity: number }
  | {
      kind: "cut";
      cutsRequired: number;
      totalPlayers: number;
      totalCapacity: number;
      /** The producer's ranked first candidate, or null when it has no ranking. */
      ranked: WhatChangedCutCandidate | null;
    }
  | { kind: "unknown"; why: string };

/**
 * Read the roster-limit check.
 *
 * `cuts_required = max(0, total_players - total_capacity)`
 * (roster_cut_engine.py:225) — a hard arithmetic fact, not a judgement, which
 * is exactly why it is the one thing the morning read is willing to call an
 * action.
 *
 * The ranked candidate is taken at `cut_priority === 1` and NOT simply as
 * `top_candidates[0]`, because those are different things. `cut_priority` 0 is
 * a FORCED review — a reserve player whose injury-list compliance failed
 * (roster_cut_engine.py:286-297) — and it is not ranked by value at all; those
 * candidates are unshifted onto the front of the list. Reading position 0 as
 * "the most expendable player" would attach a value ordering to a roster-rules
 * problem, which is the sort of plausible-but-unearned sentence this module
 * exists to stop. Rank 1 is the head of the value-sorted pool
 * (roster_cut_engine.py:359-375) and only rank 1 licenses the value claim.
 */
export function cutPressure(section: WhatChangedStructuralSection): CutPressure {
  const summary = section.summary;
  if (
    section.status !== "ok" ||
    summary?.cuts_required == null ||
    summary.total_players == null ||
    summary.total_capacity == null
  ) {
    return {
      kind: "unknown",
      why: section.aborted_reason
        ? describeToken(section.aborted_reason)
        : "The roster-limit check didn't come through this morning.",
    };
  }
  if (summary.cuts_required <= 0) {
    return {
      kind: "clear",
      totalPlayers: summary.total_players,
      totalCapacity: summary.total_capacity,
    };
  }
  const ranked =
    (section.top_candidates ?? []).find(
      (candidate) => candidate.cut_priority === 1 && candidate.player_name,
    ) ?? null;
  return {
    kind: "cut",
    cutsRequired: summary.cuts_required,
    totalPlayers: summary.total_players,
    totalCapacity: summary.total_capacity,
    ranked,
  };
}

/** "you're carrying 27 players in 26 spots" — the arithmetic behind a cut. */
function crowdingClause(totalPlayers: number, totalCapacity: number): string {
  return `you're carrying ${num(totalPlayers)} players in ${num(totalCapacity)} spots`;
}

// ── the verdict ──────────────────────────────────────────────────────────────

export type Verdict = {
  /** The first sentence: what, if anything, needs doing. */
  headline: string;
  /** The second: what moved, plus a staleness clause when there is one. */
  detail: string;
  /**
   * The largest mover's name, and the text either side of it, when the detail
   * names one — so the renderer can make the name a handle onto his card
   * (DG-110) without cutting prose apart at render time. `detail` is the same
   * string either way.
   */
  detailParts: { lead: string; name: string; tail: string } | null;
  /** Drives the accent only — the words carry the meaning on their own. */
  tone: "clear" | "action" | "unknown";
};

/**
 * One or two plain sentences, and the three §2.2 states fall out of the same
 * assembler rather than being three hand-written paragraphs that can drift.
 *
 * The headline is SCOPED on purpose. "Nothing needs doing today" on its own
 * would be the exact fabrication the phase-2A panel caught — a rollup "ok"
 * rendered as a claim the backend declines to make. The clause after the dash
 * names the only check that produced it, so a reader can see how far the
 * all-clear reaches: it reaches the roster limit and no further.
 */
export function verdict({
  pressure,
  moved,
  stalenessClause,
}: {
  pressure: CutPressure;
  moved: RosterMovement;
  /** Present only when the report itself is old; the header says it too. */
  stalenessClause: string | null;
}): Verdict {
  const tailClause = stalenessClause === null ? "" : ` ${stalenessClause}`;
  const prefix =
    pressure.kind === "unknown"
      ? `${pressure.why} It will be back on the next run. `
      : "";
  const detail = `${prefix}${moved.sentence}${tailClause}`;
  const detailParts =
    moved.kind === "moved"
      ? {
          lead: `${prefix}${moved.parts.lead}`,
          name: moved.parts.name,
          tail: `${moved.parts.tail}${tailClause}`,
        }
      : null;
  if (pressure.kind === "unknown") {
    return {
      tone: "unknown",
      headline: "We can't tell you whether anything needs doing today.",
      detail,
      detailParts,
    };
  }
  if (pressure.kind === "clear") {
    return {
      tone: "clear",
      headline: `Nothing needs doing today — your ${num(pressure.totalPlayers)} players fit inside your ${num(pressure.totalCapacity)} spots.`,
      detail,
      detailParts,
    };
  }
  const cuts =
    pressure.cutsRequired === 1
      ? "one has to go"
      : `${num(pressure.cutsRequired)} have to go`;
  return {
    tone: "action",
    headline: `One thing needs doing: ${crowdingClause(pressure.totalPlayers, pressure.totalCapacity)}, so ${cuts}.`,
    detail,
    detailParts,
  };
}

// ── "worth a look" ───────────────────────────────────────────────────────────

export type RecommendationAction =
  | { kind: "surface"; label: string; slug: string }
  | {
      kind: "player";
      label: string;
      sleeperId: string | null | undefined;
      name: string;
      context: string | undefined;
    };

export type Recommendation = {
  id: string;
  /**
   * The bold one-line call.
   *
   * NAMED `headline`, NOT `verdict`, and the name is load-bearing. `verdict` is
   * a banned FIELD (frontend/src/shell/banned_vocabulary.json) because the
   * backend contract carries no such field, and a frontend rendering
   * `card.verdict` would look for all the world like it was printing one —
   * which is the exact class of calibrated-sounding readout the evidence-typing
   * gate exists to stop. This string is a sentence this module assembled, and
   * it is named like one.
   */
  headline: string;
  /** Exactly two sentences of reason, each clause from a field on this page. */
  reasons: [string, string];
  action: RecommendationAction;
};

/**
 * The bar a market move has to clear to be worth a look.
 *
 * Any bar is a choice, so the choice is STATED on the block (see
 * `RECOMMENDATION_METHOD`) rather than left as a mystery the reader has to
 * reverse-engineer. A raw delta cannot be the bar on its own: +306 is a 6%
 * move on a 5,082 player and a rounding error on a 40,000 one, and a list that
 * ranked by raw size would show the same expensive names every morning.
 */
export const MARKET_MOVE_BAR_PCT = 5;

export const RECOMMENDATION_METHOD =
  `We flag a price move here when it is the largest among your players and worth at ` +
  `least ${MARKET_MOVE_BAR_PCT}% of what that player is priced at.`;

export type WorthALook = {
  cards: Recommendation[];
  /** Inputs we would normally have used and did not get, said plainly. */
  missing: string[];
};

export function worthALook({
  pressure,
  moved,
  window,
}: {
  pressure: CutPressure;
  moved: RosterMovement;
  window: ComparisonWindow | null | undefined;
}): WorthALook {
  const cards: Recommendation[] = [];
  const missing: string[] = [];

  if (pressure.kind === "unknown") {
    missing.push(
      `We'd normally check your roster limit here. ${pressure.why} It will be back on the next run.`,
    );
  }

  if (pressure.kind === "cut") {
    const crowding = `${crowdingClause(pressure.totalPlayers, pressure.totalCapacity).replace(/^you're/, "You're")}, so ${pressure.cutsRequired === 1 ? "one has to go" : `${num(pressure.cutsRequired)} have to go`}.`;
    const ranked = pressure.ranked;
    if (ranked?.player_name) {
      cards.push({
        id: "required-cut",
        headline:
          pressure.cutsRequired === 1
            ? `Your required cut: start with ${ranked.player_name}.`
            : `Your ${num(pressure.cutsRequired)} required cuts: start with ${ranked.player_name}.`,
        reasons: [crowding, rankedCutReason(ranked)],
        action: {
          kind: "surface",
          label: "Open the cut list",
          slug: "roster-capacity",
        },
      });
    } else {
      cards.push({
        id: "required-cut-unranked",
        headline:
          pressure.cutsRequired === 1
            ? "One cut is due."
            : `${num(pressure.cutsRequired)} cuts are due.`,
        reasons: [
          crowding,
          // The list exists but its head is a forced roster-rules review, or
          // there is no list at all. Either way the value ordering that would
          // name a player is not there, and inventing one is the whole thing
          // this module refuses to do.
          "We don't have a value-ranked list of who to drop this morning, so this one is yours to judge.",
        ],
        action: {
          kind: "surface",
          label: "Open the cut list",
          slug: "roster-capacity",
        },
      });
    }
  }

  const marketCard = marketMoveCard(moved, window);
  if (marketCard) cards.push(marketCard);

  return { cards: cards.slice(0, 2), missing };
}

/**
 * Why the producer put this player at the top of the cut list.
 *
 * The ordering is `_tier_sort_key` (roster_cut_engine.py:171-181): tier first,
 * then the tier's own score ASCENDING. A rank-1 candidate carrying `xvar_pct`
 * is tier A, tier A sorts before every other tier, and tier A sorts on
 * `xvar_percentile_overall` — so he has the lowest value over replacement of
 * anyone the list ranks, and no unranked tier can be hiding below him. A rank-1
 * candidate WITHOUT `xvar_pct` was sorted on dynasty value instead, and the
 * sentence says that instead. With neither number the ordering still holds but
 * has no figure to show, so no figure is shown.
 */
function rankedCutReason(candidate: WhatChangedCutCandidate): string {
  const lead =
    "Our cut list ranks the players you're allowed to drop lowest-value first, and he sits at the bottom of it";
  if (candidate.xvar_pct != null) {
    return `${lead} — his ${VALUE_OVER_REPLACEMENT.toLowerCase()} is at the ${candidate.xvar_pct} percentile.`;
  }
  if (candidate.dvs != null) {
    return `${lead} — ranked on dynasty value, where his is ${candidate.dvs}.`;
  }
  return `${lead}.`;
}

/**
 * The day's biggest price move on his roster, when it is big enough to matter.
 *
 * What this card deliberately does NOT say: that the move is a sell-high
 * window, that the market is now ahead of our own price, or that the player is
 * at a high for the period on screen. None of the three is available here — a
 * market delta row carries no model value at all, and the sparkline's own
 * series disproves the third outright on the very example the spec offers
 * (Dart's 5,082 sits BELOW his 5,381 of four weeks earlier). What it says is
 * the size of the move, its share of his price, where it moved him on the
 * market's board, and where to go to see it beside our projection.
 */
function marketMoveCard(
  moved: RosterMovement,
  window: ComparisonWindow | null | undefined,
): Recommendation | null {
  if (moved.kind !== "moved") return null;
  const row = moved.largest;
  const level = row.current_value;
  if (level == null || level <= 0) return null;
  const pct = (Math.abs(row.value_delta) / level) * 100;
  if (pct < MARKET_MOVE_BAR_PCT) return null;

  const name = row.player_name ?? row.player_key;
  const when = windowPhrase(window);
  const rose = row.value_delta > 0;
  const share = `${pct.toFixed(1)}%`;

  // `*_rank_delta = latest - prior`, so NEGATIVE is toward rank #1 — the
  // producer's locked sign convention (daily_diff.py header) and the reason
  // this reads the sign rather than the `_direction` word beside it.
  const rankClauses: string[] = [];
  if (row.overall_rank_delta !== 0) {
    rankClauses.push(
      `${num(Math.abs(row.overall_rank_delta))} ${Math.abs(row.overall_rank_delta) === 1 ? "place" : "places"} ${row.overall_rank_delta < 0 ? "up" : "down"} the market's overall board`,
    );
  }
  const group = positionGroup(row.position);
  if (group !== null && row.position_rank_delta !== 0) {
    rankClauses.push(
      `${num(Math.abs(row.position_rank_delta))} ${Math.abs(row.position_rank_delta) === 1 ? "spot" : "spots"} ${row.position_rank_delta < 0 ? "up" : "down"} among ${group}`,
    );
  }
  const rankSentence =
    rankClauses.length > 0 ? `That moved him ${rankClauses.join(" and ")}. ` : "";

  return {
    id: "market-move",
    headline: `${name}'s price ${rose ? "jumped" : "dropped"} ${when}.`,
    reasons: [
      `He's ${movementWords(row.value_delta)} to ${num(level)} — a ${share} move, and the largest among the players the market priced for you.`,
      `${rankSentence}This page carries market prices only, so open his card to see that move beside our own projection.`,
    ],
    action: {
      kind: "player",
      label: "See his card",
      sleeperId: row.sleeper_id,
      name,
      context: row.position ?? undefined,
    },
  };
}

// ── where you stand ──────────────────────────────────────────────────────────

export type WhereYouStand = {
  teamName: string | null;
  /** One sentence; null when the producer has no posture to report. */
  posture: string | null;
  /** The roster against its limit, or null when the check did not run. */
  roster: string | null;
};

/**
 * The prose that replaces the "Current roster context" dump.
 *
 * What the dump printed: "Starting lineup value: 97.39" directly above "Weekly
 * lineup strength: 97.39" — `lineup_xvar` and `starter_weighted_xvar`, two
 * genuinely different quantities that happened to be equal that morning, under
 * two names a manager has no way to tell apart — plus "Card count: 5", "Partner
 * ranking count: 2", "Team count: 12" and "David roster player count: 27".
 *
 * None of those five numbers comes back here. Spec §2.6 puts the roster-value
 * figures on the Roster surface, which owns them and can label them properly;
 * repeating them here under one name would just pick a winner between two names
 * for a problem whose real answer is that the front page does not need either.
 *
 * `posture_label` on the team-value summary is likewise NOT read: it says
 * "UNCLASSIFIED" on the same payload where `team_posture.david_posture` says
 * "REBUILDING". Two fields disagreeing is precisely the same-thing-two-names
 * failure in another costume, so the posture section's own field is the one
 * that speaks and the other is left where it lies.
 */
export function whereYouStand(
  response: WhatChangedResponse,
  pressure: CutPressure,
): WhereYouStand {
  const posture = response.structural_context.sections.team_posture;
  const raw = posture.david_posture ?? null;
  return {
    teamName: posture.david_team_name ?? null,
    posture:
      raw === null
        ? null
        : raw === "UNCLASSIFIED"
          ? "We don't have enough signal to put a label on your team yet."
          : // team_posture.py:145-150 weights four roster signals into this
            // word. Saying so is not a hedge — it is what stops "Rebuilding"
            // reading as a plan somebody made.
            `You're ${valueWord(raw).toLowerCase()} — that is a formula over your roster's starters, ages and picks, not a read on what you intend.`,
    roster:
      pressure.kind === "cut"
        ? `${crowdingClause(pressure.totalPlayers, pressure.totalCapacity).replace(/^you're/, "You're")}.`
        : pressure.kind === "clear"
          ? `You're carrying ${num(pressure.totalPlayers)} players in ${num(pressure.totalCapacity)} spots.`
          : null,
  };
}

// ── around the league ────────────────────────────────────────────────────────

export type LeagueMovers = {
  rows: WhatChangedMarketDelta[];
  /** How many were dropped because they are already up in "your roster". */
  excluded: number;
};

/**
 * The league list with his own players taken out.
 *
 * Both lists are slices of the same `deltas_by_id` map (daily_diff.py:135-160),
 * so a roster player who is also a top mover appears in both with identical
 * numbers — which is what David saw, and what reads as an unfiltered query
 * rather than as two sections. The exclusion is by sleeper id, and the count is
 * kept so the footer can say where those rows went instead of silently
 * shrinking a total.
 */
export function leagueMovers(market: WhatChangedMarketSection): LeagueMovers {
  const mine = new Set(
    (market.roster_deltas ?? [])
      .map((row) => row.sleeper_id)
      .filter((id): id is string => typeof id === "string" && id !== ""),
  );
  const all = market.top_movers ?? [];
  const rows = all.filter(
    (row) => typeof row.sleeper_id !== "string" || !mine.has(row.sleeper_id),
  );
  return { rows, excluded: all.length - rows.length };
}
