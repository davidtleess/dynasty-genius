// Player details keep the football forecast, dynasty valuation, market price and roster context
// separate. DG195 replaces the original separate rank tracks with the shared axis imported from
// Directions, preserving true intervals on both sides and the completed DG192 headshots.
// The design's illustrative causal explanations, position ranks and lineup roles are not data;
// only the actual forecast, valuation basis and captured ownership appear here.
import { comparisonText } from "../market-ranks/MarketRanks";
import { formatAvailablePoints } from "../research/availableHelpers";
import { headshotSrc, PlayerIdentity } from "../ui/PlayerIdentity";
import type { WorkspacePlayer, WorkspacePlayerPanelProps } from "./types";
import { WorkspaceRankScale } from "./WorkspaceRankScale";
import "./WorkspacePlayerPanel.css";

/** The panel's DOM id, derived from the player so the row control can point at it without threading a prop. */
export function panelDomId(playerId: string): string {
  return `dg-workspace-panel-${playerId}`;
}

export function panelLabel(name: string): string {
  return `${name} — our view versus the market`;
}

/** Points keep the board's own precision rule: a value that is not zero never prints as zero, so a genuine 0.0
 *  above replacement stays distinguishable from a small positive one. A market price is not points and keeps its
 *  own integer formatting. */
function points(value: number): string {
  return formatAvailablePoints(value);
}

function dayLabel(iso: string): string {
  const date = new Date(iso.length === 10 ? `${iso}T12:00:00Z` : iso);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

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

/** Compare needs somewhere to put him: he is either the available side or the roster spot. Missing points are fine
 *  — you can still weigh an unpriced player against a spot — but a player another team owns is neither side. */
function canCompare(player: WorkspacePlayer): boolean {
  return player.ownership === "available" || player.ownership === "roster";
}

function Idea({
  title,
  question,
  value,
  note,
}: {
  title: string;
  question: string;
  value: string;
  note: string;
}) {
  return (
    <li className="dg-workspace-panel__idea">
      <span className="dg-workspace-panel__idea-title">{title}</span>
      <span className="dg-workspace-panel__idea-question">{question}</span>
      <strong className="dg-workspace-panel__idea-value">{value}</strong>
      <span className="dg-workspace-panel__idea-note">{note}</span>
    </li>
  );
}

export function WorkspacePlayerPanel({
  player,
  data,
  nowLabel,
  futureLabel,
  onWatch,
  onCompare,
}: WorkspacePlayerPanelProps) {
  const rank = player.rank;
  const forecast = player.forecast;
  const cohort = data.coverage.common_players;
  const paired = rank !== null && rank.our_rank !== null && rank.market_rank !== null;

  const limits: string[] = [];
  if (rank?.model_zero_tie === true) {
    limits.push(
      "He is projected at or below replacement in every season. This valuation floors each season’s advantage at zero, so it does not distinguish players below that bar. They share a rank; their football forecasts can still differ.",
    );
  }
  if (forecast?.missing_reason) limits.push(forecast.missing_reason);
  if (forecast?.starting_estimate === true) limits.push(forecast.evidence_note);
  if (rank?.missing_reason) limits.push(rank.missing_reason);
  limits.push(data.basis.scoring_note);

  return (
    <section
      className="dg-workspace-panel"
      aria-label={panelLabel(player.name)}
      id={panelDomId(player.id)}
    >
      {/* DG-194: the face beside the name. The detail previously opened straight into the rank
          lanes with no identity at all, so a reader who arrived from search had to trust the
          heading. A missing photo degrades to initials; nothing else about the panel changes. */}
      <div className="dg-workspace-panel__identity">
        <PlayerIdentity
          name={player.name}
          team={player.team ?? ""}
          position={player.position}
          imageStatus="available"
          imageSrc={headshotSrc(player.id)}
        />
      </div>

      <div className="dg-workspace-panel__answer">
        <WorkspaceRankScale
          ourRank={rank?.our_rank ?? null}
          marketRank={rank?.market_rank ?? null}
          playerName={player.name}
        />
        {rank !== null && rank.market_value === null && (
          <p className="dg-workspace-panel__cohort">
            No price carried in this capture — missing, not zero.
          </p>
        )}

        <p className="dg-workspace-panel__verdict">
          {rank === null
            ? "No comparable ranking for this player."
            : comparisonText(rank.comparison)}
        </p>
        <p className="dg-workspace-panel__cohort">
          {paired
            ? `Both ranks cover the same ${cohort.toLocaleString("en-US")} players.`
            : `Primary paired ranks cover the ${cohort.toLocaleString("en-US")} players both sides carry, and he is not one of them. Our own board ranks ${data.coverage.model_players.toLocaleString("en-US")}.`}
        </p>
        <p className="dg-workspace-panel__units">
          The underlying model points and market prices are in different units —
          five-year points above replacement against a FantasyCalc price — so those two
          numbers do not compare directly. The ranks do, because both cover the same
          players. A rank difference is still not a trade price.
        </p>
      </div>

      <ul
        className="dg-workspace-panel__ideas"
        aria-label={`Four ways to read ${player.name}`}
      >
        <Idea
          title="Football forecast"
          question="What might he produce?"
          value={
            forecast?.now_points == null ? "No forecast" : points(forecast.now_points)
          }
          note={`Total points for ${nowLabel}, not a per-game average.`}
        />
        <Idea
          title="Dynasty valuation"
          question="What is that worth over time, here?"
          value={rank?.model_value == null ? "No valuation" : points(rank.model_value)}
          note="Five-year points above replacement, seasons weighted equally."
        />
        <Idea
          title="Market valuation"
          question="What does the broad market pay?"
          value={
            rank?.market_value == null
              ? "No price"
              : rank.market_value.toLocaleString("en-US")
          }
          note="FantasyCalc Market Value, in its own units."
        />
        <Idea
          title="Your situation"
          question="Where does he sit for you?"
          value={ownershipLabel(player)}
          note={
            rank?.taxi_or_reserve === true
              ? "Kept on taxi or injured reserve in your saved roster."
              : `Ownership as captured ${dayLabel(data.source.ownership_as_of)}.`
          }
        />
      </ul>

      {/* biome-ignore lint/a11y/useSemanticElements: a named non-form grouping of two readings; a fieldset would describe them as form controls. */}
      <div
        className="dg-workspace-panel__horizon"
        role="group"
        aria-label="This season versus later"
      >
        <div className="dg-workspace-panel__period">
          <span className="dg-workspace-panel__period-label">{nowLabel}</span>
          <strong className="dg-workspace-panel__period-value">
            {forecast?.now_points == null ? "—" : points(forecast.now_points)}
          </strong>
          <span className="dg-workspace-panel__period-note">total points</span>
        </div>
        <div className="dg-workspace-panel__period">
          <span className="dg-workspace-panel__period-label">{futureLabel}</span>
          <strong className="dg-workspace-panel__period-value">
            {forecast?.future_points == null ? "—" : points(forecast.future_points)}
          </strong>
          <span className="dg-workspace-panel__period-note">total points, summed</span>
        </div>
      </div>

      <ul
        className="dg-workspace-panel__limits"
        aria-label={`What limits this read on ${player.name}`}
      >
        {limits.map((limit) => (
          <li key={limit}>{limit}</li>
        ))}
      </ul>

      {/* biome-ignore lint/a11y/useSemanticElements: a named grouping around a disclosure, not a set of form controls. */}
      <div
        className="dg-workspace-panel__sources"
        role="group"
        aria-label="How these numbers were made"
      >
        <details>
          <summary>How these numbers were made</summary>
          <div className="dg-workspace-panel__source-body">
            <ul
              className="dg-workspace-panel__basis"
              aria-label="Basis of this comparison"
            >
              <li>
                <span className="dg-workspace-panel__basis-label">Forecast basis</span>
                <p>
                  {forecast?.evidence_note?.trim() ||
                    "A forecast explanation is not available in this snapshot."}
                </p>
              </li>
              <li>
                <span className="dg-workspace-panel__basis-label">Valuation basis</span>
                <p>{data.basis.summary}</p>
              </li>
              <li>
                <span className="dg-workspace-panel__basis-label">Market context</span>
                <p>{data.basis.market_proxy_note}</p>
              </li>
            </ul>
            <p>
              These describe the forecast and valuation assumptions. This snapshot does
              not include player-specific reasons for the rank difference.
            </p>
            <p>{data.basis.scoring_note}</p>
            <p>
              Forecast dated {dayLabel(data.source.forecast_date)}, market prices
              captured {dayLabel(data.source.market_as_of)}, ownership as of{" "}
              {dayLabel(data.source.ownership_as_of)}.
            </p>
            {rank?.reference_player ? (
              <p>
                Measured against {rank.reference_player}, the replacement available at
                his position.
              </p>
            ) : null}
          </div>
        </details>
      </div>

      {/* biome-ignore lint/a11y/useSemanticElements: a named grouping of buttons; a fieldset would imply a form. */}
      <div
        className="dg-workspace-panel__actions"
        role="group"
        aria-label={`Actions for ${player.name}`}
      >
        <button
          type="button"
          className="dg-workspace-panel__action"
          aria-label={`${player.watched ? "Unwatch" : "Watch"} ${player.name}`}
          onClick={() => onWatch(player)}
        >
          {player.watched ? "Unwatch" : "Watch"}
        </button>
        {canCompare(player) ? (
          <button
            type="button"
            className="dg-workspace-panel__action"
            aria-label={`Compare ${player.name}`}
            onClick={() => onCompare(player)}
          >
            Compare against a roster spot
          </button>
        ) : null}
      </div>
    </section>
  );
}
