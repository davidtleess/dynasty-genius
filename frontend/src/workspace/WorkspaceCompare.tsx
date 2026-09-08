// DG-187 — Compare: an available player against the man holding a roster spot.
//
// Adapted from the imported Claude Design compare composition (David, 2026-09-07: "Implement:
// Dynasty Genius Workspace.dc.html"). Two things the source assumed are corrected here rather than
// reproduced: it labels the current-season figure "ppg" — these forecasts are season TOTALS — and
// its sample values are not data. Everything rendered comes from props.
//
// The two readings are kept apart on purpose. The rank pair is the independent comparison over the
// one cohort both sides cover. The forecast totals are OUR numbers only, and a difference between
// them is spoken only when the two men play the same position, because a raw total does not know
// what a superflex lineup pays for a quarterback.
import "./WorkspaceCompare.css";
import { comparisonText, rankText } from "../market-ranks/MarketRanks";
import { formatAvailablePoints } from "../research/availableHelpers";
import {
  CAVEAT,
  classWord,
  compareForecasts,
  type Period,
  periodsFor,
} from "../research/comparisonHelpers";
import type { WorkspaceCompareProps, WorkspacePlayer } from "./types";

type Side = "available" | "roster";

const SIDE = {
  available: { label: "Available player", placeholder: "Choose an available player" },
  roster: { label: "Your player", placeholder: "Choose one of your players" },
} as const;

const byName = (a: WorkspacePlayer, b: WorkspacePlayer) =>
  a.name < b.name ? -1 : a.name > b.name ? 1 : a.id < b.id ? -1 : a.id > b.id ? 1 : 0;

function poolFor(players: WorkspacePlayer[], side: Side): WorkspacePlayer[] {
  const ownership = side === "available" ? "available" : "roster";
  return players.filter((p) => p.ownership === ownership).sort(byName);
}

function whoLine(player: WorkspacePlayer): string {
  return `${player.position}${player.team === null ? "" : ` ${player.team}`}`;
}

function Picker({
  side,
  pool,
  value,
  onPick,
}: {
  side: Side;
  pool: WorkspacePlayer[];
  value: string | null;
  onPick: (id: string | null) => void;
}) {
  const id = `dg-workspace-compare-${side}`;
  return (
    <div className="dg-workspace-compare__picker">
      <label className="dg-workspace-compare__picker-label" htmlFor={id}>
        {SIDE[side].label}
      </label>
      <select
        id={id}
        className="dg-workspace-compare__select"
        value={value ?? ""}
        onChange={(event) =>
          onPick(event.target.value === "" ? null : event.target.value)
        }
      >
        {/* No automatic first choice: the empty option is selected until David picks. */}
        <option value="">{SIDE[side].placeholder}</option>
        {pool.map((player) => (
          <option key={player.id} value={player.id}>
            {player.name} · {whoLine(player)}
          </option>
        ))}
      </select>
    </div>
  );
}

/** One player's card: who he is, the rank pair, and our own two totals. */
function SideCard({
  player,
  now,
  future,
}: {
  player: WorkspacePlayer;
  now: Period;
  future: Period;
}) {
  const rank = player.rank;
  const forecast = player.forecast;
  const classes = (forecast?.seasons ?? [])
    .map((season) => classWord(season.estimate_class))
    .filter((word): word is string => word !== null);
  const estimate = classes.length > 0 ? classes[0] : null;

  return (
    // biome-ignore lint/a11y/useSemanticElements: a named grouping of readings, not form controls.
    <div
      className="dg-workspace-compare__side"
      role="group"
      aria-label={`Compare: ${player.name}`}
    >
      <div className="dg-workspace-compare__who">
        <span className="dg-workspace-compare__name" data-user-text="">
          {player.name}
        </span>
        <span className="dg-workspace-compare__meta" data-user-text="">
          {whoLine(player)}
        </span>
      </div>

      <div className="dg-workspace-compare__ranks">
        <div className="dg-workspace-compare__rank" data-lane="model">
          <span className="dg-workspace-compare__rank-label">Our rank</span>
          <span className="dg-workspace-compare__rank-value">
            {rankText(rank?.our_rank ?? null)}
          </span>
        </div>
        <div className="dg-workspace-compare__rank" data-lane="market">
          <span className="dg-workspace-compare__rank-label">Market rank</span>
          <span className="dg-workspace-compare__rank-value">
            {rankText(rank?.market_rank ?? null)}
          </span>
        </div>
      </div>
      {rank !== null && (
        <p className="dg-workspace-compare__disagreement">
          {comparisonText(rank.comparison)}
        </p>
      )}
      {rank?.missing_reason != null && (
        <p className="dg-workspace-compare__note">{rank.missing_reason}</p>
      )}

      {forecast === null ? (
        <p className="dg-workspace-compare__note">
          We have no forecast on file for him, so no season totals are shown.
        </p>
      ) : (
        <>
          <div className="dg-workspace-compare__totals">
            <div className="dg-workspace-compare__total">
              <span className="dg-workspace-compare__total-label">
                {now.label} total
              </span>
              <span className="dg-workspace-compare__total-value">
                {formatAvailablePoints(forecast.now_points)}
              </span>
            </div>
            <div className="dg-workspace-compare__total">
              <span className="dg-workspace-compare__total-label">
                {future.label} total
              </span>
              <span className="dg-workspace-compare__total-value">
                {formatAvailablePoints(forecast.future_points)}
              </span>
            </div>
          </div>
          {estimate !== null && (
            <p className="dg-workspace-compare__note">
              Starting estimate; methods differ by season. See the season breakdown.
            </p>
          )}
          <details className="dg-workspace-compare__note">
            <summary>Season breakdown and forecast basis</summary>
            <p>{forecast.evidence_note}</p>
            {forecast.missing_reason && <p>{forecast.missing_reason}</p>}
            <dl>
              {forecast.seasons.map((season) => (
                <div key={season.season}>
                  <dt>{season.season}</dt>
                  <dd>
                    {formatAvailablePoints(season.points)} points
                    {season.estimate_class
                      ? ` · ${classWord(season.estimate_class)}`
                      : ""}
                  </dd>
                </div>
              ))}
            </dl>
          </details>
        </>
      )}
    </div>
  );
}

/** One period's verdict, kept in its own card so this season and the future never blur together. */
function VerdictCard({ title, sentence }: { title: string; sentence: string }) {
  return (
    // biome-ignore lint/a11y/useSemanticElements: a named grouping of prose, not form controls.
    <div className="dg-workspace-compare__verdict" role="group" aria-label={title}>
      <span className="dg-workspace-compare__verdict-title">{title}</span>
      <p className="dg-workspace-compare__verdict-body">{sentence}</p>
    </div>
  );
}

function verdictFor(
  a: WorkspacePlayer | null,
  b: WorkspacePlayer | null,
  period: Period,
): string | null {
  if (a === null || b === null) return null;
  // A player with no forecast is not a zero and not a loss: say whose number is missing.
  const missing = [a, b]
    .filter((player) => player.forecast === null)
    .map((p) => p.name);
  if (missing.length > 0) {
    return `We have no forecast for ${missing.join(" or ")}, so these two cannot be compared on points.`;
  }
  return compareForecasts(
    a.forecast as NonNullable<WorkspacePlayer["forecast"]>,
    b.forecast as NonNullable<WorkspacePlayer["forecast"]>,
    period,
  ).sentence;
}

export function WorkspaceCompare({
  players,
  data,
  comparison,
  selection,
  onSelect,
}: WorkspaceCompareProps) {
  const availablePool = poolFor(players, "available");
  const rosterPool = poolFor(players, "roster");
  // Derived from the ids on every render, so a changed pick can never leave the previous player's
  // numbers standing under a new name.
  const available = availablePool.find((p) => p.id === selection.availableId) ?? null;
  const roster = rosterPool.find((p) => p.id === selection.rosterId) ?? null;
  const strayAvailable = selection.availableId !== null && available === null;
  const strayRoster = selection.rosterId !== null && roster === null;
  const { now, future } = periodsFor(comparison);
  const nowVerdict = verdictFor(available, roster, now);
  const futureVerdict = verdictFor(available, roster, future);

  return (
    <section className="dg-workspace-compare" aria-label="Compare players">
      <div className="dg-workspace-compare__head">
        <p className="dg-workspace-compare__lede">
          An available player against the man occupying the roster spot. Help this
          season and future potential are kept apart, and the forecast comparison is
          stated as a points difference only for players at the same position.
        </p>
      </div>

      <div className="dg-workspace-compare__pickers">
        <Picker
          side="available"
          pool={availablePool}
          value={selection.availableId}
          onPick={(id) => onSelect({ ...selection, availableId: id })}
        />
        <Picker
          side="roster"
          pool={rosterPool}
          value={selection.rosterId}
          onPick={(id) => onSelect({ ...selection, rosterId: id })}
        />
      </div>

      {(strayAvailable || strayRoster) && (
        <p className="dg-workspace-compare__notice" role="status">
          That player is not available to compare here: this screen pairs an available
          player with one of yours.
        </p>
      )}

      {available === null && roster === null && !strayAvailable && !strayRoster && (
        <p className="dg-workspace-compare__note">
          Pick an available player and one of your own to see the two side by side.
        </p>
      )}

      {(available !== null || roster !== null) && (
        <div className="dg-workspace-compare__sides">
          {available !== null && (
            <SideCard player={available} now={now} future={future} />
          )}
          {roster !== null && <SideCard player={roster} now={now} future={future} />}
        </div>
      )}

      {(available !== null || roster !== null) && (
        // A rank means nothing without the population it is out of, and this one is the cohort
        // both sides cover — not our whole forecast and not the market's whole board.
        <p className="dg-workspace-compare__note">
          Both ranks are out of the {data.coverage.common_players} players our forecast
          and the market both cover.
        </p>
      )}

      {nowVerdict !== null && futureVerdict !== null && (
        <div className="dg-workspace-compare__verdicts">
          <VerdictCard title="Help this season" sentence={nowVerdict} />
          <VerdictCard title="Future potential" sentence={futureVerdict} />
        </div>
      )}

      <p className="dg-workspace-compare__caveat">{CAVEAT}</p>
    </section>
  );
}
