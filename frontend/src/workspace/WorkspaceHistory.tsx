import { type ReactNode, useEffect, useState } from "react";
import { z } from "zod";
import type { WorkspacePlayer } from "./types";
import "./WorkspaceHistory.css";

const dated = z.string().refine((s) => Number.isFinite(Date.parse(s)));
const historySchema = z.object({
  daily_diff: z.object({
    market: z.object({
      status: z.literal("ok"),
      market_source: z.literal("fantasycalc_overlay"),
      aborted_reason: z.null().optional(),
      comparison_window: z.object({
        from_date: dated,
        to_date: dated,
        status: z.null().optional(),
      }),
      roster_deltas: z.array(
        z.object({
          sleeper_id: z.string(),
          player_name: z.string().nullable().optional(),
          value_delta: z.number().finite(),
        }),
      ),
    }),
  }),
});
type History = z.infer<typeof historySchema>["daily_diff"]["market"];
function date(s: string) {
  return new Date(s).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

export function WorkspaceHistory({
  players,
  snapshots,
}: {
  players: WorkspacePlayer[];
  snapshots?: ReactNode;
}) {
  const [market, setMarket] = useState<History | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    let live = true;
    void (async () => {
      try {
        const response = await fetch("/api/league/what-changed");
        if (!response.ok) throw new Error("History unavailable");
        const payload = historySchema.parse(await response.json()).daily_diff.market;
        const from = Date.parse(payload.comparison_window.from_date),
          to = Date.parse(payload.comparison_window.to_date);
        if (from >= to || to > Date.now()) throw new Error("Invalid history window");
        if (live) setMarket(payload);
      } catch {
        if (live) setError(true);
      }
    })();
    return () => {
      live = false;
    };
  }, []);
  const saved = players
    .filter(
      (p) =>
        p.watched && p.watchedAt !== null && Number.isFinite(Date.parse(p.watchedAt)),
    )
    .sort((a, b) => Date.parse(b.watchedAt ?? "") - Date.parse(a.watchedAt ?? ""));
  const names = new Map(players.map((p) => [p.id, p.name]));
  const changes =
    market?.roster_deltas.filter(
      (p) => p.value_delta !== 0 && (names.has(p.sleeper_id) || p.player_name),
    ) ?? [];
  return (
    <div className="dg-workspace-history">
      <p>Saved forecasts, dated market captures and your watchlist additions.</p>
      {snapshots}
      <section
        className="dg-workspace-history__market"
        aria-label="Market price history"
      >
        <h2>Market prices we captured</h2>
        {market ? (
          <>
            <p>
              FantasyCalc Market Value, {date(market.comparison_window.from_date)} to{" "}
              {date(market.comparison_window.to_date)}. These captures are separate from
              the current ranking snapshot.
            </p>
            <p>
              Changes reflect broad market prices, including market-wide movement. Only
              players priced in both captures have a change to show.
            </p>
            {changes.length ? (
              <ul>
                {changes.map((p) => (
                  <li key={p.sleeper_id}>
                    <time dateTime={market.comparison_window.to_date}>
                      {date(market.comparison_window.to_date)}
                    </time>
                    <span>{names.get(p.sleeper_id) ?? p.player_name}</span>
                    <strong
                      className={
                        p.value_delta > 0
                          ? "dg-workspace-history__up"
                          : "dg-workspace-history__down"
                      }
                    >
                      {p.value_delta > 0 ? "+" : ""}
                      {p.value_delta.toLocaleString("en-US")}
                    </strong>
                  </li>
                ))}
              </ul>
            ) : (
              <p>No price changes for the roster players in this dated comparison.</p>
            )}
          </>
        ) : (
          <p role="status">
            {error
              ? "Dated market changes are unavailable. No price movement is inferred from the current snapshot."
              : "Loading dated market changes…"}
          </p>
        )}
      </section>
      <section aria-label="Your watchlist activity">
        <h2>Your moves</h2>
        {saved.length ? (
          <ul>
            {saved.map((p) => (
              <li key={p.id}>
                <time dateTime={p.watchedAt ?? undefined}>
                  {date(p.watchedAt ?? "")}
                </time>
                <span>{p.name} was added to your watchlist.</span>
              </li>
            ))}
          </ul>
        ) : (
          <p>No dated watchlist additions are saved in this browser.</p>
        )}
        <p>
          Shows players currently on your watchlist. Removed players and past
          comparisons are not stored as an activity history.
        </p>
      </section>
      <details>
        <summary>What is missing from this timeline?</summary>
        <p>
          Model revisions and depth-chart changes need a dated history before they can
          appear here. A date on the current forecast does not tell us when it changed.
        </p>
      </details>
    </div>
  );
}
