// DG-203 — one ranked board across a chosen scope. Ranks are intervals on one common population;
// nothing here subtracts our points from a market price.
import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";

import { AppShell } from "@/components/dg/AppShell";
import { BoardTable } from "@/components/dg/Board";
import { boardQuery, bundleQuery, type Scope } from "@/lib/dg/queries";
import { forecastLabels } from "@/lib/dg/backend";
import { validatePlayerSearch } from "@/lib/dg/search";

const SCOPES: { value: Scope; label: string }[] = [
  { value: "mine", label: "My roster" },
  { value: "league", label: "League rosters" },
  { value: "available", label: "Available" },
  { value: "universe", label: "Full universe" },
];

export const Route = createFileRoute("/board")({
  validateSearch: validatePlayerSearch,
  head: () => ({
    meta: [
      { title: "Value board — Dynasty Genius" },
      {
        name: "description",
        content: "Every player ranked in both lanes, on one shared population, best on the left.",
      },
    ],
  }),
  component: BoardPage,
});

function BoardPage() {
  const [scope, setScope] = useState<Scope>("universe");
  const [position, setPosition] = useState("all");
  const { data: bundle } = useQuery(bundleQuery);
  const labels = forecastLabels(bundle?.basis.years ?? []);
  const { data: rows, isPending, isError } = useQuery(boardQuery(scope));

  const all = rows ?? [];
  const filtered = all.filter((r) => position === "all" || r.position === position);
  // Ranks are intervals, so ordering reads the interval's start. A player with no rank sorts last
  // rather than being dropped or treated as rank zero.
  const sorted = [...filtered].sort(
    (a, b) =>
      (a.our_rank?.start ?? Number.POSITIVE_INFINITY) -
      (b.our_rank?.start ?? Number.POSITIVE_INFINITY),
  );
  const positions = [...new Set(all.map((r) => r.position).filter(Boolean))].sort();

  return (
    <AppShell title="Value board">
      <header>
        {bundle ? (
          <p className="label-caps mt-1">
            Saved reading · {bundle.coverage.common_players} players carry both numbers · our values{" "}
            {bundle.snapshot.forecast_date}
          </p>
        ) : null}
      </header>

      <div
        className="sticky z-10 mt-4 flex flex-wrap items-center gap-2 py-2"
        style={{ top: 0, background: "var(--background)" }}
        data-dg-owned="board-controls"
      >
        <label className="label-caps flex items-center gap-2">
          Scope
          <select
            className="rounded-sm border bg-transparent px-2 py-1 text-[13px]"
            style={{ borderColor: "var(--hairline)", minHeight: 44 }}
            value={scope}
            onChange={(e) => setScope(e.target.value as Scope)}
            aria-label="Scope"
          >
            {SCOPES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <label className="label-caps flex items-center gap-2">
          Position
          <select
            className="rounded-sm border bg-transparent px-2 py-1 text-[13px]"
            style={{ borderColor: "var(--hairline)", minHeight: 44 }}
            value={position}
            onChange={(e) => setPosition(e.target.value)}
            aria-label="Position"
          >
            <option value="all">All positions</option>
            {positions.map((p) => (
              <option key={p} value={p as string}>
                {p}
              </option>
            ))}
          </select>
        </label>
        <span className="label-caps">{sorted.length} players shown</span>
      </div>

      {isError ? (
        <p role="alert" className="mt-4 text-sm text-[var(--ink-dim)]">
          The saved reading could not be loaded.
        </p>
      ) : isPending ? (
        <p role="status" className="mt-4 text-sm text-[var(--ink-dim)]">
          Opening the saved reading…
        </p>
      ) : (
        <div className="mt-4">
          <BoardTable
            nowLabel={labels.current}
            futureLabel={labels.future}
            rows={sorted}
            groupByPosition={scope !== "universe"}
          />
        </div>
      )}
    </AppShell>
  );
}
