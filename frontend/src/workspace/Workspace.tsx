import { useEffect, useState } from "react";
import { useMarketRanks } from "../market-ranks/MarketRanksContext";
import { useWatchlist } from "../research/AvailablePlayers";
import { unresolvedRow } from "../research/availableHelpers";
import type { ComparisonPayload } from "../research/comparisonHelpers";
import { periodsFor } from "../research/comparisonHelpers";
import type { WorkspaceOrder, WorkspacePlayer, WorkspaceView } from "./types";
import { WorkspaceBoard } from "./WorkspaceBoard";
import { WorkspaceCompare } from "./WorkspaceCompare";
import { WorkspaceFrame } from "./WorkspaceFrame";
import { WorkspaceHistory } from "./WorkspaceHistory";
import {
  joinWorkspacePlayers,
  matchesWorkspacePlayer,
  minimumGap,
  sortWorkspacePlayers,
  validateComparison,
} from "./workspaceData";
import "./Workspace.css";

const views = [
  "today",
  "roster",
  "available",
  "watchlist",
  "compare",
  "history",
] as const;
function readView(): WorkspaceView {
  const q = new URLSearchParams(window.location.search);
  if (["roster", "roster-audit"].includes(q.get("surface") ?? "")) return "roster";
  const view = q.get("view");
  return views.find((v) => v === view) ?? "today";
}
const labels: Record<WorkspaceView, string> = {
  today: "Today",
  roster: "Roster",
  available: "Available players",
  watchlist: "Watchlist",
  compare: "Compare",
  history: "What changed",
};
const orderLabels: Record<WorkspaceOrder, string> = {
  ours: "Our rank",
  market: "Market rank",
  gap: "Disagreement",
  now: "This season",
  future: "Future",
  name: "Name",
};

export function Workspace() {
  const ranks = useMarketRanks();
  const data = ranks.status === "available" ? ranks.data : null;
  const watchlist = useWatchlist();
  const [view, setView] = useState<WorkspaceView>(readView);
  const [query, setQuery] = useState("");
  const [position, setPosition] = useState("all");
  const [order, setOrder] = useState<WorkspaceOrder>(() =>
    readView() === "available" ? "now" : "ours",
  );
  const [selection, setSelection] = useState<{
    availableId: string | null;
    rosterId: string | null;
  }>({ availableId: null, rosterId: null });
  const [comparison, setComparison] = useState<ComparisonPayload | null>(null);
  const [forecastError, setForecastError] = useState(false);
  useEffect(() => {
    if (!data) return;
    let active = true;
    setComparison(null);
    setForecastError(false);
    void (async () => {
      try {
        const response = await fetch("/api/research/comparison");
        if (!response.ok) throw new Error("Forecast unavailable");
        const payload = validateComparison(await response.json(), data);
        if (active) setComparison(payload);
      } catch {
        if (active) setForecastError(true);
      }
    })();
    return () => {
      active = false;
    };
  }, [data]);
  useEffect(() => {
    const pop = () => {
      const previousView = readView();
      setView(previousView);
      setOrder(previousView === "available" ? "now" : "ours");
      setQuery("");
      setPosition("all");
    };
    window.addEventListener("popstate", pop);
    return () => window.removeEventListener("popstate", pop);
  }, []);

  function navigate(next: WorkspaceView) {
    window.history.pushState(null, "", `?surface=workspace&view=${next}`);
    setView(next);
    setQuery("");
    setPosition("all");
    setOrder(next === "available" ? "now" : "ours");
    window.scrollTo?.({ top: 0, behavior: "instant" });
  }
  function watch(p: WorkspacePlayer) {
    watchlist.toggle(
      unresolvedRow(p.id, {
        name: p.name,
        position: p.position,
        team: p.team,
        watched_at: p.watchedAt,
      }),
    );
  }
  function compare(p: WorkspacePlayer) {
    if (p.ownership === "available")
      setSelection((prev) => ({ ...prev, availableId: p.id }));
    else if (p.ownership === "roster")
      setSelection((prev) => ({ ...prev, rosterId: p.id }));
    else return;
    navigate("compare");
  }
  const players = data ? joinWorkspacePlayers(data, comparison, watchlist.entries) : [];
  const owned = players.filter((p) => p.ownership === "roster");
  const available = players.filter((p) => p.ownership === "available");
  const watched = players.filter((p) => p.watched);
  const searching = query.trim().length > 0;
  const pool = searching
    ? players
    : view === "available"
      ? available
      : view === "watchlist"
        ? watched
        : owned;
  const filtered = pool.filter((p) => matchesWorkspacePlayer(p, query, position));
  const actualOrder = view === "today" && !searching ? "gap" : order;
  const sorted = sortWorkspacePlayers(filtered, actualOrder);
  const shown =
    view === "today" && !searching
      ? sorted.ranked.filter((p) => (minimumGap(p) ?? 0) > 0).slice(0, 5)
      : sorted.ranked;
  const periods = comparison
    ? periodsFor(comparison)
    : {
        now: { label: String(data?.basis.years[0] ?? "This season") },
        future: {
          label: data ? `${data.basis.years[1]}–${data.basis.years.at(-1)}` : "Future",
        },
      };
  const board = data
    ? {
        data,
        nowLabel: periods.now.label,
        futureLabel: periods.future.label,
        onWatch: watch,
        onCompare: compare,
        order: actualOrder,
      }
    : null;
  const forecastNotice = forecastError
    ? "Available players and forecasts could not be matched to this ranking snapshot. Your roster ranks remain available. Reload to try again."
    : "Loading available players and forecasts…";
  return (
    <WorkspaceFrame
      view={view}
      onNavigate={navigate}
      query={query}
      onQuery={setQuery}
      counts={{
        roster: data?.coverage.roster_players ?? null,
        available: comparison ? available.length : null,
        watchlist: watchlist.entries.size,
      }}
      source={
        data
          ? {
              forecastDate: data.source.forecast_date,
              marketDate: data.source.market_as_of,
              ownershipDate: data.source.ownership_as_of,
              commonPlayers: data.coverage.common_players,
            }
          : null
      }
    >
      <section className="dg-workspace-content">
        <h1>{searching ? "Search results" : labels[view]}</h1>
        {!data ? (
          <p role={ranks.status === "loading" ? "status" : "alert"}>
            {ranks.status === "loading"
              ? "Loading your workspace…"
              : "Our ranks and the market are unavailable. Reload to try again."}
          </p>
        ) : (
          <>
            {watchlist.notice && <p role="status">{watchlist.notice}</p>}
            {searching ? (
              <p>
                {filtered.length} matching players across the full player list.
                Ownership is shown on each player.
              </p>
            ) : view === "today" ? (
              <>
                <p className="dg-workspace-content__lede">
                  Your {owned.length} players, in perspective:{" "}
                  {data.coverage.roster_common_players} have both our rank and a market
                  rank.
                </p>
                <h2>Where we disagree most on players you own</h2>
                <p>
                  Largest minimum rank gap first. A disagreement is a reason to look,
                  not proof of an opportunity.
                </p>
              </>
            ) : view === "roster" ? (
              <p>
                Every player you own. Our view and FantasyCalc, ranked among the same{" "}
                {data.coverage.common_players} players.
              </p>
            ) : view === "available" ? (
              <p>
                Players unowned in your saved league snapshot. Current-season and future
                forecasts stay separate; players without forecasts stay visible.
              </p>
            ) : view === "watchlist" ? (
              <p>
                Your own shortlist, saved in this browser. Watched players stay here if
                they become owned or leave the available pool.
              </p>
            ) : null}
            {(searching || ["roster", "available", "watchlist"].includes(view)) && (
              <>
                <div className="dg-workspace-content__controls">
                  <label className="dg-workspace-content__mobile-order">
                    Order by
                    <select
                      value={order}
                      onChange={(e) => setOrder(e.target.value as WorkspaceOrder)}
                    >
                      {(Object.keys(orderLabels) as WorkspaceOrder[]).map((key) => (
                        <option key={key} value={key}>
                          {orderLabels[key]}
                        </option>
                      ))}
                    </select>
                  </label>
                  <fieldset
                    className="dg-workspace-content__orders"
                    aria-label="Order players"
                  >
                    <span>Order by</span>
                    {(Object.keys(orderLabels) as WorkspaceOrder[]).map((key) => (
                      <button
                        type="button"
                        key={key}
                        aria-pressed={order === key}
                        onClick={() => setOrder(key)}
                      >
                        {orderLabels[key]}
                      </button>
                    ))}
                  </fieldset>
                  <label>
                    Position
                    <select
                      value={position}
                      onChange={(e) => setPosition(e.target.value)}
                    >
                      <option value="all">All positions</option>
                      {["QB", "RB", "WR", "TE"].map((p) => (
                        <option key={p}>{p}</option>
                      ))}
                    </select>
                  </label>
                </div>
                <p className="dg-workspace-content__caption">
                  {actualOrder === "now"
                    ? `${periods.now.label} expected season points, highest first.`
                    : actualOrder === "future"
                      ? `${periods.future.label} expected points added together, highest first.`
                      : actualOrder === "gap"
                        ? "Largest minimum rank gap first; overlapping ties have no clear preference."
                        : actualOrder === "name"
                          ? "Alphabetical by name."
                          : "Overall ranks on the shared player set; lower is better. Equal values stay tied."}{" "}
                  {filtered.length} players shown.
                </p>
              </>
            )}
            {!searching && ["available", "compare"].includes(view) && !comparison ? (
              <p role={forecastError ? "alert" : "status"}>{forecastNotice}</p>
            ) : !searching && view === "compare" && comparison ? (
              <WorkspaceCompare
                players={players}
                data={data}
                comparison={comparison}
                selection={selection}
                onSelect={setSelection}
              />
            ) : !searching && view === "history" ? (
              <WorkspaceHistory players={players} />
            ) : (
              board && (
                <>
                  {shown.length > 0 && (
                    <WorkspaceBoard
                      key={`${view}-${actualOrder}-ranked`}
                      rows={shown}
                      {...board}
                    />
                  )}
                  {view !== "today" || searching ? (
                    <>
                      {sorted.missing.length > 0 && (
                        <section
                          className="dg-workspace-content__missing"
                          aria-label="Outside this ordering"
                        >
                          <h2>No number for this ordering</h2>
                          <p>
                            These players are outside the numeric order. Missing
                            information is not zero. Open a player for what we do know.
                          </p>
                          <WorkspaceBoard
                            key={`${view}-${actualOrder}-missing`}
                            rows={sorted.missing}
                            {...board}
                          />
                        </section>
                      )}
                      {filtered.length === 0 && (
                        <p role="status">
                          {view === "watchlist" && !searching
                            ? "Your watchlist is empty. Open a player and choose Watch to save him here."
                            : "No players match this search and position filter."}
                        </p>
                      )}
                    </>
                  ) : (
                    shown.length === 0 && (
                      <p>
                        No clear rank disagreement on the paired players in your roster.
                      </p>
                    )
                  )}
                  {view === "today" && !searching && (
                    <button
                      type="button"
                      className="dg-workspace-content__link"
                      onClick={() => navigate("roster")}
                    >
                      See your full roster
                    </button>
                  )}
                  {!comparison && (view !== "available" || searching) && (
                    <p role={forecastError ? "alert" : "status"}>{forecastNotice}</p>
                  )}
                </>
              )
            )}
            <details className="dg-workspace-content__method">
              <summary>How to read our comparison</summary>
              <p>{data.basis.summary}</p>
              <p>{data.basis.scoring_note}</p>
              <p>{data.basis.market_proxy_note}</p>
              <p>
                Both primary ranks use the same {data.coverage.common_players} players.
                Tied values share a rank range; ranges are ties, not confidence bands.
                Rank gaps are places, not price differences. Our model points and
                FantasyCalc Market Value use different units.
              </p>
              <p>
                Alphabetical ordering within an exact tie does not express a preference.
              </p>
            </details>
          </>
        )}
      </section>
    </WorkspaceFrame>
  );
}
