// DG-198 — the roster board of direction B: one section per position, dense rows inside it.
//
// Three numbers in the imported design do not exist in this product's payload, so they are not
// rendered here: the per-row position-rank chip, the QB1/QB2 starter slot, and the "starts two"
// lineup rule. Printing any of them would turn a layout choice into a fabricated statistic. What is
// rendered is a rank from us, a rank from the market over the same paired cohort, the gap between
// them in places, and the two season totals in their own units — never subtracted from a price.
import type React from "react";
import { useEffect, useState } from "react";

import type { MarketRanksAvailable, RankComparison } from "../lib/api";
import { comparisonText, rankText } from "../market-ranks/MarketRanks";
import { formatAvailablePoints } from "../research/availableHelpers";
import { headshotSrc, PlayerIdentity } from "../ui/PlayerIdentity";
import type { WorkspaceOrder, WorkspacePlayer } from "./types";
import { sortWorkspacePlayers } from "./workspaceData";
import "./WorkspaceRosterGroups.css";

export type WorkspaceRosterGroupsProps = {
  rows: WorkspacePlayer[];
  data: MarketRanksAvailable;
  nowLabel: string;
  futureLabel: string;
  order: WorkspaceOrder;
  selectedId: string | null;
  onSelect: (player: WorkspacePlayer) => void;
  onWatch: (player: WorkspacePlayer) => void;
  onFindAlternatives: (position: string) => void;
  showDepth?: boolean | undefined;
};

/** The positions this league starts, in the order a manager reads them. Anything else keeps its own
 *  code and follows, so an unexpected position can never drop a player off the board. */
const KNOWN: ReadonlyArray<{ position: string; label: string }> = [
  { position: "QB", label: "Quarterbacks" },
  { position: "RB", label: "Running backs" },
  { position: "WR", label: "Wide receivers" },
  { position: "TE", label: "Tight ends" },
];

/** A position code of four or more capitals would read as machinery and is banned from the DOM by
 *  the copy rule, so an unlabelled code is shown as a word. The data is unchanged. */
function positionLabel(position: string): string {
  if (/^[A-Z]{4,}$/.test(position)) {
    return position.charAt(0) + position.slice(1).toLocaleLowerCase();
  }
  return position;
}

/** The gap at a glance: the least it can be, signed. Overlapping tie ranges make it a bound rather
 *  than a measurement, so only an exact pair of ranks earns a bare number. The full sentence rides
 *  in the row's accessible name, which is why the column never spends width on words. */
function gapChip(comparison: RankComparison): string {
  if (comparison.direction === "unavailable") return "—";
  if (comparison.direction === "overlap") return "tied";
  if (comparison.direction === "same") return "level";
  const places =
    comparison.direction === "higher" ? comparison.gap_min : comparison.gap_max;
  if (places === null) return "—";
  const signed = `${places > 0 ? "+" : "−"}${Math.abs(places)}`;
  if (comparison.gap_min === comparison.gap_max) return signed;
  return `${comparison.direction === "higher" ? "≥" : "≤"}${signed}`;
}

/** A number with the word for what it is. The desktop board names its columns once in the strip
 *  above, so these labels stand down there; on a phone, and on a depth card, they are the ONLY
 *  thing saying whose rank a number is — a lane hue does not survive a colour-blind reader. */
function Reading({
  label,
  className,
  children,
}: {
  label: string;
  className: string;
  children: React.ReactNode;
}) {
  return (
    <span className={className}>
      <span className="dg-roster-groups__reading-label">{label}</span>
      <span className="dg-roster-groups__reading-value">{children}</span>
    </span>
  );
}

function seasonPhrase(label: string, points: number | null | undefined): string {
  return `${label}: ${points == null ? "no forecast" : `${formatAvailablePoints(points)} points`}`;
}

function rowLabel(
  player: WorkspacePlayer,
  nowLabel: string,
  futureLabel: string,
): string {
  const who = [player.name, player.position, player.team].filter(Boolean).join(", ");
  const rank = player.rank;
  // Both seasons ride here. A phone hides both columns for width, so an accessible name carrying
  // only the current season would put the future one out of reach entirely.
  const season = [
    seasonPhrase(nowLabel, player.forecast?.now_points),
    seasonPhrase(futureLabel, player.forecast?.future_points),
  ].join(". ");
  if (rank === null) return `${who}. No comparable ranking. ${season}.`;
  const ours =
    rank.our_rank === null
      ? "not ranked"
      : `${rankText(rank.our_rank)} of ${rank.our_rank.total}`;
  const market =
    rank.market_rank === null
      ? rank.market_value === null
        ? "no price carried"
        : "not ranked"
      : `${rankText(rank.market_rank)} of ${rank.market_rank.total}`;
  return `${who}. Our rank ${ours}. Market rank ${market}. ${comparisonText(rank.comparison)}. ${season}.`;
}

type Coverage = { total: number; covered: number; of: number };

/** A season total is only as good as its coverage. A player without that season is MISSING, never a
 *  zero, and a subtotal is never printed as if it were the whole group. */
function coverageFor(
  players: WorkspacePlayer[],
  period: "now" | "future",
): Coverage | null {
  const known = players
    .map((p) => (period === "now" ? p.forecast?.now_points : p.forecast?.future_points))
    .filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  if (known.length === 0) return null;
  return {
    total: known.reduce((sum, v) => sum + v, 0),
    covered: known.length,
    of: players.length,
  };
}

function coverageText(label: string, coverage: Coverage | null): string | null {
  if (coverage === null) return null;
  const points = `${formatAvailablePoints(coverage.total)} pts`;
  if (coverage.covered === coverage.of) return `${label} ${points}`;
  return `${label} ${points} from ${coverage.covered} of ${coverage.of} players`;
}

/** The span of our ranks across a group, built only from the ranks the group actually carries. */
function rankSpan(players: WorkspacePlayer[]): string | null {
  const intervals = players
    .map((p) => p.rank?.our_rank)
    .filter((v): v is NonNullable<typeof v> => v != null);
  if (intervals.length === 0) return null;
  // A tie is an interval, so the top of a span is the furthest END any member reaches. Taking the
  // largest START would report #4–230 for a group whose worst player may sit anywhere down to #388.
  const low = Math.min(...intervals.map((r) => r.start));
  const high = Math.max(...intervals.map((r) => r.end));
  return low === high ? `#${low}` : `#${low}–${high}`;
}

const DESKTOP = "(min-width: 61rem)";

/** True when the viewport is a desktop, and true when we cannot ask. The fallback must REVEAL
 *  players: a component that guesses "phone" without evidence would collapse groups and hide most
 *  of the roster from someone whose browser simply did not answer. */
function desktopNow(): boolean {
  if (typeof window === "undefined") return true;
  if (typeof window.matchMedia !== "function") return true;
  return window.matchMedia(DESKTOP).matches;
}

export function WorkspaceRosterGroups({
  rows,
  data,
  nowLabel,
  futureLabel,
  order,
  selectedId,
  onSelect,
  onWatch,
  onFindAlternatives,
  showDepth,
}: WorkspaceRosterGroupsProps) {
  const [desktop, setDesktop] = useState<boolean>(desktopNow);
  // A group the reader has opened or closed keeps their choice; everything else follows the
  // viewport default, so rotating a phone never silently hides a section someone opened.
  const [choice, setChoice] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function")
      return;
    const query = window.matchMedia(DESKTOP);
    const onChange = () => setDesktop(query.matches);
    if (typeof query.addEventListener !== "function") return;
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  const seen = new Set(rows.map((p) => p.position));
  const groups = [
    ...KNOWN.filter((g) => seen.has(g.position)),
    ...rows
      .map((p) => p.position)
      .filter(
        (position, index, all) =>
          !KNOWN.some((g) => g.position === position) &&
          all.indexOf(position) === index,
      )
      .map((position) => ({ position, label: positionLabel(position) })),
  ];

  if (rows.length === 0) {
    return (
      <div className="dg-roster-groups dg-roster-groups--empty">
        <p className="dg-roster-groups__empty-title">No players match this view yet.</p>
        <p className="dg-roster-groups__empty-note">
          Clear the search to bring your roster back.
        </p>
      </div>
    );
  }

  const quarterbacks = rows.filter((p) => p.position === "QB");
  // Ranked first, then the ones this order cannot place. The section says "the quarterbacks you
  // own", so dropping an unranked one would make its own sentence false.
  const quarterbackOrder = sortWorkspacePlayers(quarterbacks, order);
  const depth = [...quarterbackOrder.ranked, ...quarterbackOrder.missing];
  // The badge quotes the league format only where the payload itself states it. Nothing about a
  // starting requirement is claimed, because nothing in this payload establishes one.
  const superflex = /superflex/i.test(data.basis.scoring_note);

  return (
    <div className="dg-roster-groups">
      {showDepth === true && quarterbacks.length > 0 ? (
        <section className="dg-roster-groups__depth" aria-label="Quarterback depth">
          <div className="dg-roster-groups__depth-head">
            <h2 className="dg-roster-groups__depth-title">Quarterback depth</h2>
            {superflex ? (
              <span className="dg-roster-groups__depth-badge">Superflex</span>
            ) : null}
          </div>
          <ul className="dg-roster-groups__depth-cards">
            {depth.map((qb) => (
              <li key={qb.id}>
                <button
                  type="button"
                  className="dg-roster-groups__depth-card"
                  aria-pressed={selectedId === qb.id}
                  aria-label={rowLabel(qb, nowLabel, futureLabel)}
                  onClick={() => onSelect(qb)}
                >
                  <PlayerIdentity
                    name={qb.name}
                    team={qb.team ?? ""}
                    position={qb.position}
                    imageStatus="available"
                    imageSrc={headshotSrc(qb.id)}
                    teamId={qb.team ?? undefined}
                  />
                  <span className="dg-roster-groups__depth-numbers">
                    <Reading label="Ours" className="dg-roster-groups__ours">
                      {rankText(qb.rank?.our_rank ?? null)}
                    </Reading>
                    <Reading label="Market" className="dg-roster-groups__market">
                      {rankText(qb.rank?.market_rank ?? null)}
                    </Reading>
                    <Reading
                      label={`${nowLabel} pts`}
                      className="dg-roster-groups__now"
                    >
                      {formatAvailablePoints(qb.forecast?.now_points)}
                    </Reading>
                  </span>
                </button>
              </li>
            ))}
          </ul>
          <div className="dg-roster-groups__depth-foot">
            <p className="dg-roster-groups__depth-note">
              These are the quarterbacks you own, in the order this board is sorted. We
              do not model your weekly lineup, so nothing here says who to play.
            </p>
            <button
              type="button"
              className="dg-roster-groups__depth-action"
              onClick={() => onFindAlternatives("QB")}
            >
              Browse available quarterbacks
            </button>
          </div>
        </section>
      ) : null}

      {/* The units are carried once. Every row states them again inside its own accessible name,
          so this strip is visual furniture rather than a set of orphaned words. */}
      {/* The strip repeats a row's own shape EXACTLY — the same grid inside the same flex line,
          beside the same 44px cell. A full-width strip over a row that reserves 48px for its watch
          button puts every column label 48px off the numbers it names. */}
      <div className="dg-roster-groups__head" aria-hidden="true">
        <span className="dg-roster-groups__head-grid">
          <span className="dg-roster-groups__head-ours">Ours</span>
          <span className="dg-roster-groups__head-player">Player</span>
          <span className="dg-roster-groups__head-market">Market</span>
          <span className="dg-roster-groups__head-gap">Gap (places)</span>
          <span className="dg-roster-groups__head-now">{nowLabel} pts</span>
          <span className="dg-roster-groups__head-future">{futureLabel} pts</span>
        </span>
        <span className="dg-roster-groups__head-watch">Watch</span>
      </div>

      {groups.map((group, index) => {
        const members = rows.filter((p) => p.position === group.position);
        const { ranked, missing } = sortWorkspacePlayers(members, order);
        const open = choice[group.position] ?? (desktop || index === 0);
        const listId = `dg-roster-group-${group.position.toLocaleLowerCase()}`;
        const span = rankSpan(members);
        const summary = [
          `${members.length} ${members.length === 1 ? "player" : "players"}`,
          span,
          coverageText(nowLabel, coverageFor(members, "now")),
          coverageText(futureLabel, coverageFor(members, "future")),
        ].filter((part): part is string => part !== null);

        return (
          <section className="dg-roster-groups__group" key={group.position}>
            <h2 className="dg-roster-groups__group-heading">
              <button
                type="button"
                className="dg-roster-groups__group-toggle"
                aria-expanded={open}
                aria-controls={listId}
                onClick={() =>
                  setChoice((prev) => ({ ...prev, [group.position]: !open }))
                }
              >
                <span className="dg-roster-groups__group-label">{group.label}</span>
                <span className="dg-roster-groups__group-summary">
                  {summary.join(" · ")}
                </span>
                <span className="dg-roster-groups__group-chevron" aria-hidden="true">
                  {open ? "⌄" : "›"}
                </span>
              </button>
            </h2>

            <ul className="dg-roster-groups__rows" id={listId} hidden={!open}>
              {ranked.map((p) => (
                <RosterRow
                  key={p.id}
                  player={p}
                  nowLabel={nowLabel}
                  futureLabel={futureLabel}
                  selected={selectedId === p.id}
                  onSelect={onSelect}
                  onWatch={onWatch}
                />
              ))}
              {missing.length > 0 ? (
                <li className="dg-roster-groups__missing-label">
                  Not ranked in this order · shown by name
                </li>
              ) : null}
              {missing.map((p) => (
                <RosterRow
                  key={p.id}
                  player={p}
                  nowLabel={nowLabel}
                  futureLabel={futureLabel}
                  selected={selectedId === p.id}
                  onSelect={onSelect}
                  onWatch={onWatch}
                />
              ))}
            </ul>
          </section>
        );
      })}

      <p className="dg-roster-groups__basis">
        Our rank and the market rank are both taken over the players carrying a rank
        from both sources. The season columns are our forecast points in research PPR
        scoring, which is not every custom rule your league runs.{" "}
        {data.basis.scoring_note}
      </p>
    </div>
  );
}

function RosterRow({
  player,
  nowLabel,
  futureLabel,
  selected,
  onSelect,
  onWatch,
}: {
  player: WorkspacePlayer;
  nowLabel: string;
  futureLabel: string;
  selected: boolean;
  onSelect: (player: WorkspacePlayer) => void;
  onWatch: (player: WorkspacePlayer) => void;
}) {
  const rank = player.rank;
  const noPrice = rank !== null && rank.market_value === null;
  return (
    <li className="dg-roster-groups__item">
      {/* The row and the watch control are SIBLINGS. The imported design nested the watch button
          inside a clickable row, which is neither valid nor operable by keyboard. */}
      <button
        type="button"
        className="dg-roster-groups__row"
        aria-pressed={selected}
        aria-label={rowLabel(player, nowLabel, futureLabel)}
        onClick={() => onSelect(player)}
      >
        <span className="dg-roster-groups__player">
          <PlayerIdentity
            name={player.name}
            team={player.team ?? ""}
            position={player.position}
            imageStatus="available"
            imageSrc={headshotSrc(player.id)}
            teamId={player.team ?? undefined}
          />
        </span>
        {/* One wrapper that WRAPS on a phone and dissolves into the row's grid on a desktop
            (`display: contents`). The first cut positioned these with fixed left margins, which a
            wide tie range like #230–388 would have run straight through. */}
        <span className="dg-roster-groups__readings">
          <Reading label="Ours" className="dg-roster-groups__ours">
            {rankText(rank?.our_rank ?? null)}
          </Reading>
          <Reading label="Market" className="dg-roster-groups__market">
            {noPrice ? (
              <span className="dg-roster-groups__no-price">no price</span>
            ) : (
              rankText(rank?.market_rank ?? null)
            )}
          </Reading>
          <Reading label="Gap" className="dg-roster-groups__gap">
            {rank === null ? "—" : gapChip(rank.comparison)}
          </Reading>
          <span className="dg-roster-groups__now">
            {formatAvailablePoints(player.forecast?.now_points)}
          </span>
          <span className="dg-roster-groups__future">
            {formatAvailablePoints(player.forecast?.future_points)}
          </span>
        </span>
        <span className="dg-roster-groups__chevron" aria-hidden="true">
          ›
        </span>
      </button>
      <button
        type="button"
        className="dg-roster-groups__watch"
        aria-pressed={player.watched}
        aria-label={`Watch ${player.name}`}
        onClick={() => onWatch(player)}
      >
        <span aria-hidden="true">{player.watched ? "★" : "☆"}</span>
      </button>
    </li>
  );
}
