// DG-199 — the Roster-first inspector (design B, approved by David on 2026-09-08: "you can do roster first").
//
// B's inspector is a drawing of one player, and three of the things it draws do not exist in this product:
// a position-rank chip, a lineup role, and a "why" list of causal drivers with push badges. There is no
// per-player causal attribution in this payload at all, so this component says what the numbers are and
// where they came from, and says plainly that the snapshot carries no player-specific reason for the
// disagreement. Inventing one would be the most expensive kind of wrong here: a sentence the reader would
// act on that nothing produced.
//
// Root owns the aside, the modal, close, focus, navigation, the alternatives list and selection. This file
// owns only what sits inside the frame.
import type { MarketRanksAvailable } from "../lib/api";
import { comparisonText, rankText } from "../market-ranks/MarketRanks";
import { formatAvailablePoints } from "../research/availableHelpers";
import { headshotSrc, PlayerIdentity } from "../ui/PlayerIdentity";
import type { WorkspacePlayer } from "./types";
import { WorkspacePlayerPanel } from "./WorkspacePlayerPanel";
import { WorkspaceRankScale } from "./WorkspaceRankScale";
import "./WorkspaceInspector.css";

export type WorkspaceInspectorProps = {
  player: WorkspacePlayer;
  data: MarketRanksAvailable;
  nowLabel: string;
  futureLabel: string;
  onWatch: (player: WorkspacePlayer) => void;
  onCompare: (player: WorkspacePlayer) => void;
  onAlternatives: (player: WorkspacePlayer) => void;
};

/** Ownership is read, never inferred. The served field wins; the map is only for a row that arrived without
 *  one, and it still describes ownership rather than guessing at it. */
function ownershipLabel(player: WorkspacePlayer): string {
  if (player.rank?.league_ownership) return player.rank.league_ownership;
  const spoken: Record<WorkspacePlayer["ownership"], string> = {
    roster: "Your roster",
    available: "Available",
    league: "Rostered by another team",
    outside: "Outside the league's player pool",
    unknown: "Ownership not resolved",
  };
  return spoken[player.ownership];
}

/** He is either the available side of a comparison or the roster spot being compared against. A player
 *  another team owns is neither, so the action is absent rather than present and inert. */
function canCompare(player: WorkspacePlayer): boolean {
  return player.ownership === "available" || player.ownership === "roster";
}

/**
 * One reading and its unit, kept in its own labelled group.
 *
 * `formatAvailablePoints` is the board's own rule and the reason this is not a bare `?? 0`: a genuine
 * projected 0.0 prints as 0.0 and stays distinguishable from a value nobody produced, which prints as
 * words. A missing number that renders as zero is a fact the reader cannot tell from a real one.
 *
 * The season readings are projected TOTAL points for their window. The replacement-adjusted number is a
 * different quantity — `rank.model_value`, which is what our rank is built from — and the two must never
 * be described in each other's terms.
 */
function Reading({
  label,
  value,
  unit,
  missing,
}: {
  label: string;
  value: number | null | undefined;
  unit: string;
  missing: string;
}) {
  const absent = value == null || Number.isNaN(value);
  return (
    // biome-ignore lint/a11y/useSemanticElements: a labelled reading and its unit, not a form control.
    <div className="dg-inspector__reading" role="group" aria-label={label}>
      <span className="dg-inspector__reading-label">{label}</span>
      <span
        className={`dg-inspector__reading-value${absent ? " dg-inspector__reading-value--absent" : ""}`}
      >
        {absent
          ? missing
          : unit === "points"
            ? formatAvailablePoints(value)
            : value.toLocaleString("en-US")}
      </span>
      <span className="dg-inspector__reading-unit">
        {unit === "points" ? "points" : "market units"}
      </span>
    </div>
  );
}

export function WorkspaceInspector({
  player,
  data,
  nowLabel,
  futureLabel,
  onWatch,
  onCompare,
  onAlternatives,
}: WorkspaceInspectorProps) {
  const rank = player.rank;
  const forecast = player.forecast;
  const owned = player.ownership === "roster";
  // The paired population is whatever the payload says it is. B welds "of 388 paired" into its markup; a
  // component that did the same would keep saying 388 after the cohort changed.
  const paired =
    rank?.our_rank?.total ?? rank?.market_rank?.total ?? data.coverage.common_players;
  const board = rank?.model_rank_all ?? null;

  return (
    <section className="dg-inspector" aria-label={`Player overview for ${player.name}`}>
      {/* biome-ignore lint/a11y/useSemanticElements: a named grouping of identity facts, not form
          controls; a fieldset would announce them as inputs. */}
      <div
        className="dg-inspector__identity"
        role="group"
        aria-label={`${player.name} identity`}
      >
        <PlayerIdentity
          name={player.name}
          team={player.team ?? ""}
          position={player.position}
          imageStatus="available"
          imageSrc={headshotSrc(player.id)}
        />
        <p className="dg-inspector__ownership">{ownershipLabel(player)}</p>
        {forecast?.taxi_or_reserve ? (
          <p className="dg-inspector__flag">
            Kept on taxi or reserve in the saved roster. That is the list he sits on,
            not a statement about who starts.
          </p>
        ) : null}
      </div>

      {/* The two readings, the gap between them and the population they share are one thing to read,
          so they are one named group — and it is what lets either surface be addressed unambiguously
          once the reused panel adds its own copy of the same sentence. */}
      {/* biome-ignore lint/a11y/useSemanticElements: a named grouping of readings, not form controls. */}
      <div
        className="dg-inspector__comparison"
        role="group"
        aria-label={`Rank comparison for ${player.name}`}
      >
        <div className="dg-inspector__ranks">
          {/* biome-ignore lint/a11y/useSemanticElements: a named reading, not a form control. */}
          <div
            className="dg-inspector__rank"
            data-side="ours"
            role="group"
            aria-label="Our rank"
          >
            <span className="dg-inspector__rank-label">Our rank</span>
            <span className="dg-inspector__rank-value">
              {rankText(rank?.our_rank ?? null)}
            </span>
          </div>
          {/* biome-ignore lint/a11y/useSemanticElements: a named reading, not a form control. */}
          <div
            className="dg-inspector__rank"
            data-side="market"
            role="group"
            aria-label="Market rank"
          >
            <span className="dg-inspector__rank-label">Market rank</span>
            <span className="dg-inspector__rank-value">
              {rankText(rank?.market_rank ?? null)}
            </span>
          </div>
        </div>

        <p className="dg-inspector__gap">
          {rank === null ? "No comparable rank pair" : comparisonText(rank.comparison)}
        </p>
        <p className="dg-inspector__population">
          {rank?.our_rank && rank?.market_rank
            ? `Both ranks are places among the same ${paired.toLocaleString("en-US")} paired players.`
            : `No comparable rank pair. The shared ranking covers ${paired.toLocaleString("en-US")} players with both readings.`}
          {board
            ? ` He is ${rankText(board)} of ${board.total.toLocaleString("en-US")} on our own board, which ranks more players than the market prices.`
            : ""}
        </p>
      </div>

      <WorkspaceRankScale
        ourRank={rank?.our_rank ?? null}
        marketRank={rank?.market_rank ?? null}
        playerName={player.name}
      />

      <div className="dg-inspector__readings">
        <Reading
          label={`This season ${nowLabel}`}
          value={forecast?.now_points}
          unit="points"
          missing="No forecast"
        />
        <Reading
          label={`Future ${futureLabel}`}
          value={forecast?.future_points}
          unit="points"
          missing="No forecast"
        />
        <Reading
          label="FantasyCalc Market Value"
          value={rank?.market_value}
          unit="market"
          missing="No price"
        />
      </div>

      <p className="dg-inspector__units">
        Season readings are projected total points. Our rank uses five-year points above
        replacement. FantasyCalc Market Value is a market price in separate units. Full
        detail explains the assumptions.
      </p>
      {forecast?.starting_estimate ? (
        <p className="dg-inspector__flag">
          This season's total is a starting estimate, not a completed forecast.
        </p>
      ) : null}
      {forecast?.missing_reason ? (
        <p className="dg-inspector__flag">{forecast.missing_reason}</p>
      ) : null}

      {/* biome-ignore lint/a11y/useSemanticElements: a named set of buttons; a fieldset would
          announce a form that does not exist. */}
      <div
        className="dg-inspector__actions"
        role="group"
        aria-label={`Inspector actions for ${player.name}`}
      >
        <button
          type="button"
          className="dg-inspector__action"
          aria-label={`${player.watched ? "Unwatch" : "Watch"} ${player.name}`}
          onClick={() => onWatch(player)}
        >
          {player.watched ? "Unwatch" : "Watch"}
        </button>
        {canCompare(player) ? (
          <button
            type="button"
            className="dg-inspector__action"
            aria-label={`Compare ${player.name} against a roster spot`}
            onClick={() => onCompare(player)}
          >
            Compare
          </button>
        ) : null}
        {owned ? (
          <button
            type="button"
            className="dg-inspector__action dg-inspector__action--wide"
            aria-label={`Find an alternative at ${player.position} for ${player.name}`}
            onClick={() => onAlternatives(player)}
          >
            Find an alternative at {player.position}
          </button>
        ) : null}
      </div>

      {/* One expansion, not a second copy of the surface. The existing panel already carries the four
          readings, the basis rows and the provenance, so the compact view stays compact. Its own Watch and
          Compare appear here once it is open — the inspector's actions carry their own labelled group so
          either surface can be addressed unambiguously. */}
      <details className="dg-inspector__detail">
        <summary>Full detail</summary>
        <WorkspacePlayerPanel
          player={player}
          data={data}
          nowLabel={nowLabel}
          futureLabel={futureLabel}
          onWatch={onWatch}
          onCompare={onCompare}
        />
      </details>
    </section>
  );
}
