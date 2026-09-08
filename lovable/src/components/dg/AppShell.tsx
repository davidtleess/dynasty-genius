import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

import { LEAGUE } from "@/lib/dg/league";
import { healthQuery, searchQuery } from "@/lib/dg/queries";
import { PlayerDrawer } from "./PlayerDrawer";

const NAV = [
  { to: "/", label: "Roster" },
  { to: "/board", label: "Value board" },
  { to: "/league", label: "League" },
  { to: "/trades", label: "Trades" },
  { to: "/track-record", label: "Track record" },
] as const;

function PlayerSearch() {
  const [term, setTerm] = useState("");
  const navigate = useNavigate();
  const { data } = useQuery(searchQuery(term));
  return (
    <div className="relative">
      <input
        value={term}
        onChange={(e) => setTerm(e.target.value)}
        aria-label="Find a player"
        placeholder="Find a player…"
        className="w-full rounded-md border bg-[var(--input)] px-3 py-2 text-sm outline-none placeholder:text-[var(--ink-faint)] focus:border-[var(--ring)]"
      />
      {!!data?.length && term.trim().length >= 2 && (
        <ul className="absolute z-30 mt-1 max-h-72 w-full overflow-auto rounded-md border bg-[var(--popover)] shadow-xl">
          {data.map((p) => (
            <li key={p.player_id}>
              <button
                className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-[var(--accent)]"
                onClick={() => {
                  setTerm("");
                  navigate({ to: ".", search: () => ({ player: p.player_id }) });
                }}
              >
                <span>{p.full_name}</span>
                <span className="label-caps">
                  {p.position ?? "—"}
                  {p.team ? ` · ${p.team}` : ""}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function HealthLine() {
  const { data, error, isPending } = useQuery(healthQuery);
  return (
    <div className="border-t px-4 py-3">
      <span className="label-caps">Saved research snapshot</span>
      {error ? (
        <p role="alert" className="mt-1 text-sm">
          Our saved data could not be loaded. Reload to try again.
        </p>
      ) : isPending ? (
        <p className="mt-1 text-sm">Loading saved data…</p>
      ) : (
        <>
          <p className="mt-1 text-[12px] text-[var(--ink-dim)]">
            Forecasts {data?.snapshot.forecast_date}. Market{" "}
            {data?.snapshot.market_as_of.slice(0, 10)}. Rosters{" "}
            {data?.snapshot.ownership_as_of.slice(0, 10)}.
          </p>
          <p className="mt-1 text-[11px] text-[var(--ink-dim)]">
            {data?.coverage.common_players} players in both rank lists.
          </p>
          <details className="mt-2 text-[12px]">
            <summary className="cursor-pointer">How these numbers compare</summary>
            <p className="mt-2">{data?.basis.summary}</p>
            <p className="mt-2">{data?.basis.scoring_note}</p>
            <p className="mt-2">{data?.basis.market_proxy_note}</p>
          </details>
        </>
      )}
      <button
        type="button"
        className="mt-3 rounded border px-2 py-1 text-[12px]"
        onClick={() => window.location.reload()}
      >
        Reload saved snapshot
      </button>
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
          <div className="px-4 pb-4">
            <PlayerSearch />
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
        <HealthLine />
      </aside>

      <main className="min-w-0 flex-1 pb-20 md:pb-0">
        <header className="sticky top-0 z-20 border-b bg-[var(--background)]/95 px-4 py-3 backdrop-blur md:px-8">
          <h1 className="text-[19px] font-bold">{title}</h1>
          <p className="label-caps mt-0.5">{LEAGUE.format} · Saved research</p>
          <div className="mt-3 md:hidden">
            <PlayerSearch />
          </div>
        </header>
        <div className="px-4 py-5 md:px-8">{children}</div>
        <div className="md:hidden">
          <HealthLine />
        </div>
      </main>

      <nav className="fixed bottom-0 left-0 right-0 z-30 flex border-t bg-[var(--rail)] md:hidden">
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
