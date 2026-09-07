import { useState } from "react";
import type {
  MarketRankPlayer,
  MarketRanksAvailable,
  RankComparison,
  RankInterval,
} from "../lib/api";
import { PlayerNameButton } from "../player/playerSelection";
import { PlayerIdentity } from "../ui/PlayerIdentity";
import { useMarketRanks } from "./MarketRanksContext";
import "./MarketRanks.css";

export function rankText(rank: RankInterval | null): string {
  if (rank === null) return "—";
  return rank.start === rank.end ? `#${rank.start}` : `#${rank.start}–${rank.end}`;
}

export function comparisonText(comparison: RankComparison): string {
  const { direction, gap_min: min, gap_max: max } = comparison;
  if (direction === "unavailable") return "No comparable rank pair";
  if (direction === "overlap") return "Tied ranks overlap · no clear preference";
  if (direction === "same") return "We rank him the same";
  const gap = direction === "higher" ? min : max === null ? null : Math.abs(max);
  if (gap === null) return "No comparable rank pair";
  return `We rank him ${min === max ? "" : "at least "}${gap} ${gap === 1 ? "place" : "places"} ${direction}`;
}

function dateLabel(iso: string): string {
  return new Date(iso.length === 10 ? `${iso}T12:00:00Z` : iso).toLocaleDateString(
    "en-US",
    { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" },
  );
}

export function RankLoadingOrError() {
  const state = useMarketRanks();
  return state.status === "loading" ? (
    <p role="status">Loading our ranks and the market…</p>
  ) : (
    <p role="alert">
      Us vs market is unavailable. Reload to try again. Older model scores have not been
      substituted.
    </p>
  );
}

function RankPair({ player }: { player: MarketRankPlayer }) {
  return (
    <div className="dg-market-ranks__pair">
      <div className="dg-market-ranks__ours">
        <span>Our rank</span>
        <strong>{rankText(player.our_rank)}</strong>
      </div>
      <div className="dg-market-ranks__market">
        <span>Market rank</span>
        <strong>{rankText(player.market_rank)}</strong>
      </div>
    </div>
  );
}

function SourceDetails({ data }: { data: MarketRanksAvailable }) {
  return (
    <>
      <p>{data.basis.summary}</p>
      <p>{data.basis.scoring_note}</p>
      <p>
        Forecasts: {dateLabel(data.source.forecast_date)}. Market:{" "}
        {dateLabel(data.source.market_as_of)}. Your roster:{" "}
        {dateLabel(data.source.ownership_as_of)}.
      </p>
      <p>
        The primary ranks compare the same {data.coverage.common_players} players with
        both a five-year valuation and a FantasyCalc price. Equal values share a rank
        range on either side. Draft picks are excluded.
      </p>
      <p>
        Our full board covers {data.coverage.model_players} players; FantasyCalc prices{" "}
        {data.coverage.market_players} players and {data.coverage.market_picks} draft
        picks. Players missing either side have no comparable rank pair.
      </p>
    </>
  );
}

export function RankPlayerView({
  player,
  data,
}: {
  player: MarketRankPlayer;
  data: MarketRanksAvailable;
}) {
  return (
    <article
      className="dg-market-ranks dg-market-ranks--player"
      aria-label={`Player detail for ${player.name}`}
    >
      <header>
        <h2>{player.name}</h2>
        <p>
          {player.position} · {player.team ?? "No NFL team"}
          {` · ${player.league_ownership}`}
          {player.taxi_or_reserve ? " · Taxi or reserve" : ""}
        </p>
      </header>
      <RankPair player={player} />
      <p className="dg-market-ranks__verdict">{comparisonText(player.comparison)}</p>
      <p className="dg-market-ranks__muted">
        Overall, among the same {data.coverage.common_players} players · lower rank is
        better.
      </p>
      {player.missing_reason && <p>{player.missing_reason}</p>}
      {player.model_zero_tie && (
        <p className="dg-market-ranks__tie">
          Our model does not distinguish this group: each has zero projected advantage
          above replacement. That does not mean zero fantasy points or no chance to
          become useful.
        </p>
      )}
      <p className="dg-market-ranks__muted">{data.basis.market_proxy_note}</p>
      <details className="dg-market-ranks__details">
        <summary>Why these ranks?</summary>
        <SourceDetails data={data} />
        {player.model_value !== null && (
          <>
            <p>
              Our five-year advantage:{" "}
              <strong>
                {player.model_value.toLocaleString("en-US", {
                  maximumFractionDigits: 1,
                })}
              </strong>{" "}
              research points above the positional reference
              {player.reference_player ? ` (${player.reference_player})` : ""}. Negative
              annual margins contribute zero. This is not a FantasyCalc price.
            </p>
            <div className="dg-market-ranks__seasons">
              {player.seasons.map((s) => (
                <div key={s.season}>
                  <span>{s.season}</span>
                  <strong>
                    {s.advantage.toLocaleString("en-US", { maximumFractionDigits: 1 })}
                  </strong>
                </div>
              ))}
            </div>
            <p>
              Our full-board rank: {rankText(player.model_rank_all)} of{" "}
              {data.coverage.model_players} players.
            </p>
          </>
        )}
        {player.market_value !== null && (
          <p>
            FantasyCalc Market Value:{" "}
            <strong>{player.market_value.toLocaleString("en-US")}</strong>. Published
            player rank:{" "}
            {player.market_rank_published === null
              ? "unavailable"
              : `#${player.market_rank_published}`}{" "}
            among {data.coverage.market_players} players. Its published order can
            separate equal prices; our primary market rank keeps equal prices tied.
          </p>
        )}
        <p>
          A rank gap describes disagreement, not its dollar size or a proven trade
          opportunity. A zero above-replacement value does not measure a young player's
          full future upside.
        </p>
      </details>
    </article>
  );
}

export function RankedPlayerPage({ sleeperId }: { sleeperId: string }) {
  const state = useMarketRanks();
  if (state.status !== "available") return <RankLoadingOrError />;
  const player = state.data.rows.find((row) => row.sleeper_id === sleeperId);
  return player ? (
    <RankPlayerView key={sleeperId} player={player} data={state.data} />
  ) : (
    <p role="status">
      No comparable ranking for this player. Neither a zero value nor an older model
      score has been substituted.
    </p>
  );
}

export function MarketRankRoster({ data }: { data: MarketRanksAvailable }) {
  const [search, setSearch] = useState("");
  const [position, setPosition] = useState("all");
  const all = data.rows.filter((row) => row.on_roster);
  const rows = all
    .filter(
      (row) =>
        (position === "all" || position === row.position) &&
        row.name.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()),
    )
    .sort(
      (a, b) =>
        (a.our_rank?.start ?? Infinity) - (b.our_rank?.start ?? Infinity) ||
        a.name.localeCompare(b.name),
    );
  return (
    <section className="dg-market-ranks" aria-label="Your roster versus the market">
      <header>
        <h2>Us vs market</h2>
        <p>
          Your {data.coverage.roster_players} players ·{" "}
          {data.coverage.roster_common_players} with both ranks ·{" "}
          {dateLabel(data.source.market_as_of)}
        </p>
      </header>
      <p className="dg-market-ranks__muted">
        Overall ranks among the same {data.coverage.common_players} players. Lower is
        better. Our view: five years above replacement. Market: FantasyCalc.
      </p>
      <div className="dg-market-ranks__controls">
        <label>
          Search your roster
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        <label>
          Position
          <select value={position} onChange={(e) => setPosition(e.target.value)}>
            <option value="all">All positions</option>
            {["QB", "RB", "WR", "TE"].map((pos) => (
              <option key={pos}>{pos}</option>
            ))}
          </select>
        </label>
      </div>
      <ul className="dg-market-ranks__list" aria-label="Roster rank comparisons">
        {rows.map((player) => (
          <li
            className="dg-market-ranks__row"
            key={player.sleeper_id}
            data-sleeper-id={player.sleeper_id}
          >
            <div className="dg-market-ranks__identity">
              <PlayerNameButton
                sleeperId={player.sleeper_id}
                name={player.name}
                context={`${player.position} ${player.team ?? "No NFL team"}`}
              >
                <PlayerIdentity
                  name={player.name}
                  position={player.position}
                  team={player.team ?? ""}
                  imageStatus="available"
                  imageSrc={`/assets/headshots/${player.sleeper_id}.jpg`}
                />
              </PlayerNameButton>
            </div>
            <RankPair player={player} />
            <p className="dg-market-ranks__row-verdict">
              {comparisonText(player.comparison)}
            </p>
          </li>
        ))}
      </ul>
      {rows.length === 0 && (
        <p role="status">No players match your search and position filter.</p>
      )}
      <p className="dg-market-ranks__muted">{data.basis.market_proxy_note}</p>
      <details className="dg-market-ranks__details">
        <summary>How to read this comparison</summary>
        <SourceDetails data={data} />
        <p>
          Ranges indicate tied values, not forecast uncertainty. When rank ranges
          overlap, the model cannot support a clear higher or lower preference. Open a
          player for the underlying numbers.
        </p>
      </details>
    </section>
  );
}
