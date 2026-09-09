// DG-203 — the roster, and the path David actually walks: his players by position, then one player,
// then an unowned alternative at that position, then an explicit comparison of the two.
//
// The saved reading is stated as a saved reading. Nothing here claims to be live, and the three
// as-of dates are shown separately because they genuinely differ.
import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";

import { AppShell } from "@/components/dg/AppShell";
import { BoardTable } from "@/components/dg/Board";
import { boardQuery, bundleQuery } from "@/lib/dg/queries";
import { forecastLabels } from "@/lib/dg/backend";
import { validatePlayerSearch } from "@/lib/dg/search";

export const Route = createFileRoute("/")({
  validateSearch: validatePlayerSearch,
  head: () => ({
    meta: [
      { title: "Your roster — Dynasty Genius" },
      {
        name: "description",
        content:
          "Your roster by position, with our rank beside the market's on one shared population, and the receipts one press away.",
      },
    ],
  }),
  component: RosterPage,
});

function RosterPage() {
  const [position, setPosition] = useState("all");
  const { data: bundle } = useQuery(bundleQuery);
  const labels = forecastLabels(bundle?.basis.years ?? []);
  const { data: rows, isPending, isError } = useQuery(boardQuery("mine"));

  const roster = rows ?? [];
  const filtered = roster.filter((r) => position === "all" || r.position === position);
  const paired = roster.filter((r) => r.comparison.direction !== "unavailable").length;
  const positions = [...new Set(roster.map((r) => r.position).filter(Boolean))].sort();
  const composition = positions.map(
    (position) => [position, roster.filter((r) => r.position === position).length] as const,
  );

  return (
    <AppShell title="Your roster">
      <header>
        {bundle ? (
          <>
            <p className="mt-1 text-sm text-[var(--ink-dim)]">
              {roster.length} players. {paired} carry both our rank and a market rank, among the{" "}
              {bundle.coverage.common_players} players who carry both numbers.
            </p>
            {/* Counted from the roster on screen, never a fixed shape. A position with nobody in it
                is simply absent rather than shown as a zero. */}
            <p className="label-caps mt-1">
              {composition.map(([position, count]) => `${count} ${position}`).join(" · ")}
            </p>
            <p className="label-caps mt-1">
              Saved reading · our values {bundle.snapshot.forecast_date} · market prices{" "}
              {bundle.snapshot.market_as_of.slice(0, 10)} · ownership{" "}
              {bundle.snapshot.ownership_as_of.slice(0, 10)}
            </p>
          </>
        ) : null}
        <p className="label-caps mt-2">
          Select a player to see the difference and compare an unowned alternative at his position.
        </p>
      </header>

      {/* Sticky so the position controls stay reachable down a long roster. The existing 44px
          targets are unchanged; nothing here shrinks a tap target. */}
      <div
        className="sticky z-10 mt-4 flex flex-wrap items-center gap-2 py-2"
        style={{ top: 0, background: "var(--background)" }}
        data-dg-owned="board-controls"
      >
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
            rows={filtered}
            groupByPosition
            emptyNote="No players on your roster in this saved reading."
          />
        </div>
      )}
    </AppShell>
  );
}
