// DG-188 — the workspace board: one dense row per player, expanding in place into the four-idea panel.
//
// Every number on the row is a RANK over the one cohort both sides cover, which is what makes the two comparable.
// The imported design put our five-year points total and the market's FantasyCalc price beside each other as
// numbers, and drew a gap bar by subtracting them against a 3,000-point cap. Those are different units; the
// subtraction has no meaning and the cap is invented. So the dense row carries our rank, the market's rank and the
// gap in places, and the values keep their units inside the panel.
import { useState } from "react";
import type { RankComparison } from "../lib/api";
import { comparisonText, rankText } from "../market-ranks/MarketRanks";
import { formatAvailablePoints } from "../research/availableHelpers";
import { PlayerIdentity } from "../ui/PlayerIdentity";
import type { WorkspaceBoardProps, WorkspacePlayer } from "./types";
import { panelDomId, WorkspacePlayerPanel } from "./WorkspacePlayerPanel";
import "./WorkspaceBoard.css";

/** The gap at a glance: the least it can be, signed. The full sentence rides in the row's accessible name and in
 *  the panel, so the column never has to spend width on words. */
function gapChip(comparison: RankComparison): string {
  if (comparison.direction === "unavailable") return "—";
  if (comparison.direction === "overlap") return "tied";
  if (comparison.direction === "same") return "level";
  const places =
    comparison.direction === "higher" ? comparison.gap_min : comparison.gap_max;
  if (places === null) return "—";
  const signed = `${places > 0 ? "+" : "−"}${Math.abs(places)}`;
  // Overlapping tie ranges make the gap a bound, not a measurement. "≥+110" says the least it can be; only a pair
  // of exact ranks earns a bare number, and the row's accessible name says "at least" either way.
  if (comparison.gap_min === comparison.gap_max) return signed;
  return `${comparison.direction === "higher" ? "≥" : "≤"}${signed}`;
}

function rowLabel(player: WorkspacePlayer): string {
  const who = [player.name, player.position, player.team].filter(Boolean).join(", ");
  const rank = player.rank;
  if (rank === null) return `${who}. No comparable ranking.`;
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
  return `${who}. Our rank ${ours}. Market rank ${market}. ${comparisonText(rank.comparison)}.`;
}

export function WorkspaceBoard({
  rows,
  data,
  nowLabel,
  futureLabel,
  onWatch,
  onCompare,
  order,
}: WorkspaceBoardProps) {
  const [openId, setOpenId] = useState<string | null>(null);

  if (rows.length === 0) {
    return (
      <div className="dg-workspace-board dg-workspace-board--empty">
        <p className="dg-workspace-board__empty-title">
          No players match this view yet.
        </p>
        <p className="dg-workspace-board__empty-note">
          Widen the search, or clear the position filter, to bring players back.
        </p>
      </div>
    );
  }

  return (
    <div className="dg-workspace-board">
      {/* The column labels are carried once here. Every row button states them again inside its own accessible
          name, so this strip is visual furniture and is hidden from assistive technology rather than read as a
          set of orphaned words. */}
      <div className="dg-workspace-board__head" aria-hidden="true">
        <span className="dg-workspace-board__head-ours">Ours</span>
        <span className="dg-workspace-board__head-player">Player</span>
        <span className="dg-workspace-board__head-market">Market</span>
        <span className="dg-workspace-board__head-gap">Gap (places)</span>
      </div>

      <ul className="dg-workspace-board__rows">
        {rows.map((player) => {
          const open = openId === player.id;
          const rank = player.rank;
          const noPrice = rank !== null && rank.market_value === null;
          const forecastPoints =
            order === "now"
              ? player.forecast?.now_points
              : player.forecast?.future_points;
          const forecastLine =
            order === "now" || order === "future"
              ? `${order === "now" ? nowLabel : futureLabel}: ${forecastPoints == null ? "no forecast" : `${formatAvailablePoints(forecastPoints)} points`}${player.forecast?.starting_estimate ? " · starting estimate" : ""}`
              : null;
          return (
            <li className="dg-workspace-board__item" key={player.id}>
              <button
                type="button"
                className="dg-workspace-board__row"
                aria-expanded={open}
                aria-controls={panelDomId(player.id)}
                aria-label={[rowLabel(player), forecastLine].filter(Boolean).join(" ")}
                onClick={() => setOpenId(open ? null : player.id)}
              >
                <span className="dg-workspace-board__ours">
                  {rankText(rank?.our_rank ?? null)}
                </span>
                <span className="dg-workspace-board__player">
                  <PlayerIdentity
                    name={player.name}
                    team={player.team ?? ""}
                    position={player.position}
                    imageStatus="available"
                    imageSrc={`/assets/headshots/${player.id}.jpg`}
                    teamId={player.team ?? undefined}
                  />
                  {forecastLine !== null && (
                    <span className="dg-workspace-board__forecast">{forecastLine}</span>
                  )}
                </span>
                <span className="dg-workspace-board__market">
                  {noPrice ? (
                    <span className="dg-workspace-board__no-price">no price</span>
                  ) : (
                    rankText(rank?.market_rank ?? null)
                  )}
                </span>
                <span className="dg-workspace-board__gap">
                  {rank === null ? "—" : gapChip(rank.comparison)}
                </span>
              </button>

              {open ? (
                <WorkspacePlayerPanel
                  player={player}
                  data={data}
                  nowLabel={nowLabel}
                  futureLabel={futureLabel}
                  onWatch={onWatch}
                  onCompare={onCompare}
                />
              ) : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
