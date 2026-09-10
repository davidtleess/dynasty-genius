import { Link, useRouterState } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { type ReactNode } from "react";

import { LEAGUE } from "@/lib/dg/league";
import { healthQuery } from "@/lib/dg/queries";
import { PlayerDrawer } from "./PlayerDrawer";
import { PlayerPalette } from "./PlayerPalette";
import { savedDate } from "@/lib/dg/polish";
import "./polish.css";

const NAV = [
  { to: "/", label: "Roster" },
  { to: "/board", label: "Value board" },
  { to: "/league", label: "League" },
  { to: "/trades", label: "Compare" },
  { to: "/track-record", label: "Track record" },
] as const;

function SavedReading() {
  const { data, error, isPending } = useQuery(healthQuery);
  return (
    <div className="relative">
      <details className="dg-source-disclosure">
        <summary>
          {error ? "Reading unavailable" : isPending ? "Loading reading…" : "Current board"}
          <span aria-hidden="true">⌄</span>
        </summary>
        <div className="dg-source-panel text-sm">
          <p className="font-semibold">Current board reading</p>
          {data ? (
            <>
              <dl className="mt-3 space-y-2">
                <div>
                  <dt className="text-[var(--ink-dim)]">Our forecasts</dt>
                  <dd>{savedDate(data.snapshot.forecast_date)}</dd>
                </div>
                <div>
                  <dt className="text-[var(--ink-dim)]">FantasyCalc prices</dt>
                  <dd>{savedDate(data.snapshot.market_as_of)}</dd>
                </div>
                <div>
                  <dt className="text-[var(--ink-dim)]">League ownership</dt>
                  <dd>{savedDate(data.snapshot.ownership_as_of)}</dd>
                </div>
              </dl>
              <p className="mt-3">
                Both ranks use the same {data.coverage.common_players} players.
              </p>
              <p className="mt-2 text-[var(--ink-dim)]">
                These board values stay fixed until you reload. It does not show live changes.
              </p>
              <details className="mt-3">
                <summary className="cursor-pointer">How the numbers compare</summary>
                <p className="mt-2">{data.basis.summary}</p>
                <p className="mt-2">{data.basis.scoring_note}</p>
                <p className="mt-2">{data.basis.market_proxy_note}</p>
              </details>
            </>
          ) : (
            <p className="mt-2">
              {error ? "Saved data could not load. Reload to try again." : "Loading saved data…"}
            </p>
          )}
          <button
            type="button"
            className="mt-4 min-h-11 rounded border px-3"
            onClick={() => window.location.reload()}
          >
            Reload saved reading
          </button>
        </div>
      </details>
      {error ? (
        <p role="alert" className="mt-1 text-sm">
          Saved data could not load.
        </p>
      ) : null}
    </div>
  );
}

export function AppShell({ title, children }: { title: string; children: ReactNode }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  return (
    <div className="min-h-screen md:flex">
      <aside
        className="hidden shrink-0 flex-col justify-between border-r bg-[var(--rail)] md:flex"
        style={{ width: "var(--rail-width)" }}
      >
        <div>
          <div className="px-4 py-5">
            <p className="text-[15px] font-bold tracking-tight">Dynasty Genius</p>
            <p className="label-caps mt-1">{LEAGUE.myTeamName}</p>
          </div>
          <nav className="px-2">
            {NAV.map((item) => {
              const active = pathname === item.to;
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className="block rounded-md px-3 py-2 text-sm"
                  style={{
                    background: active ? "var(--surface-raised)" : "transparent",
                    color: active ? "var(--foreground)" : "var(--ink-dim)",
                    fontWeight: active ? 600 : 400,
                  }}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <p className="px-4 py-5 text-[12px] text-[var(--ink-dim)]">
          Your valuations.
          <br />
          The market beside them.
        </p>
      </aside>

      <main className="min-w-0 flex-1 pb-32 md:pb-0">
        <header className="sticky top-0 z-20 border-b bg-[var(--background)] px-4 py-3 md:px-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-[22px] font-bold tracking-tight">{title}</h1>
              <p className="mt-0.5 text-[12px] text-[var(--ink-dim)]">{LEAGUE.format}</p>
            </div>
            <div className="flex items-center gap-2">
              <PlayerPalette />
              <SavedReading />
            </div>
          </div>
        </header>
        <div className="px-4 py-5 md:px-8">{children}</div>
      </main>

      {/*
        The Lovable badge is fixed at bottom 12px, right 12px, 145×24, at z-index 1000000 — measured on
        the published app at 320 and 390 wide. It lands on top of the last two tabs and, being above
        everything, takes their taps. The badge is the platform's and stays; what changes is that the
        nav no longer puts anything under it.

        The reserve is padding inside the nav rather than lifting the nav off the bottom, so the rail's
        background still runs to the edge of the screen and the badge sits on it. Lifting the nav would
        leave a strip of scrolled content showing beneath it.
      */}
      <nav className="fixed bottom-0 left-0 right-0 z-30 flex border-t bg-[var(--rail)] pb-12 md:hidden">
        {NAV.map((item) => {
          const active = pathname === item.to;
          return (
            <Link
              key={item.to}
              to={item.to}
              className="flex-1 py-3 text-center text-[11px]"
              style={{
                color: active ? "var(--foreground)" : "var(--ink-faint)",
                fontWeight: active ? 600 : 400,
              }}
            >
              {item.label.split(" ")[0]}
            </Link>
          );
        })}
      </nav>

      <PlayerDrawer />
    </div>
  );
}
