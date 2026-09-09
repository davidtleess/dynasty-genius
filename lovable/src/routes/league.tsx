import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/dg/AppShell";
import { BoardTable } from "@/components/dg/Board";
import { boardQuery } from "@/lib/dg/queries";
import { validatePlayerSearch } from "@/lib/dg/search";

export const Route = createFileRoute("/league")({
  validateSearch: validatePlayerSearch,
  head: () => ({ meta: [{ title: "Your league — Dynasty Genius" }] }),
  component: League,
});
function League() {
  const { data, isPending, isError } = useQuery(boardQuery("league"));
  const [query, setQuery] = useState("");
  const [ownership, setOwnership] = useState("all");
  const [position, setPosition] = useState("all");
  const [shown, setShown] = useState(25);
  const rows = [...(data ?? [])]
    .filter(
      (row) =>
        row.full_name.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()) &&
        (position === "all" || row.position === position) &&
        (ownership === "all" || (ownership === "mine" ? row.on_roster : !row.on_roster)),
    )
    .sort(
      (a, b) =>
        (b.projected_advantage ?? -Infinity) - (a.projected_advantage ?? -Infinity) ||
        a.full_name.localeCompare(b.full_name),
    );
  return (
    <AppShell title="Your league">
      {isError ? (
        <p role="alert">League players could not load. Reload the current board to try again.</p>
      ) : isPending ? (
        <p role="status">Opening league rosters…</p>
      ) : (
        <>
          <p className="text-[18px] font-semibold">
            {data?.length ?? 0} rostered players. See how we value the competition.
          </p>
          <p className="mt-2 text-sm text-[var(--ink-dim)]">
            Browse players on your roster and other teams. Select anyone to inspect his values and
            compare an alternative.
          </p>
          <div className="my-5 flex flex-wrap items-end gap-3">
            <label className="flex min-w-40 flex-1 flex-col gap-1 text-[12px]">
              Find a rostered player
              <input
                type="search"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setShown(25);
                }}
                placeholder="Player name"
                className="min-h-11 rounded border bg-transparent px-3 text-sm"
              />
            </label>
            <label className="flex flex-col gap-1 text-[12px]">
              Roster
              <select
                aria-label="Roster"
                value={ownership}
                onChange={(e) => {
                  setOwnership(e.target.value);
                  setShown(25);
                }}
                className="min-h-11 rounded border bg-[var(--background)] px-3 text-sm"
              >
                <option value="all">All rosters</option>
                <option value="mine">Your roster</option>
                <option value="others">Other rosters</option>
              </select>
            </label>
            <label className="flex flex-col gap-1 text-[12px]">
              Position
              <select
                aria-label="Position"
                value={position}
                onChange={(e) => {
                  setPosition(e.target.value);
                  setShown(25);
                }}
                className="min-h-11 rounded border bg-[var(--background)] px-3 text-sm"
              >
                <option value="all">All positions</option>
                {["QB", "RB", "WR", "TE"].map((p) => (
                  <option key={p}>{p}</option>
                ))}
              </select>
            </label>
          </div>
          <p className="mb-3 text-[12px] text-[var(--ink-dim)]">
            Ordered by our five-year points above replacement. Equal values remain tied; names only
            order their display.
          </p>
          <BoardTable
            rows={rows.slice(0, shown)}
            showSeasonForecasts={false}
            emptyNote="No rostered players match these filters."
          />
          <p className="mt-3 text-[12px] text-[var(--ink-dim)]">
            This view compares dynasty ranks and values. Season forecasts are included for your
            roster and the available pool; other teams' season forecasts are not included.
          </p>
          <p className="mt-4 text-[12px] text-[var(--ink-dim)]">
            Showing {Math.min(shown, rows.length)} of {rows.length} matching players.
          </p>
          {shown < rows.length ? (
            <button
              type="button"
              className="mt-2 min-h-11 rounded border px-4 text-sm"
              onClick={() => setShown((n) => n + 25)}
            >
              Show 25 more
            </button>
          ) : null}
          <details className="mt-5 text-sm text-[var(--ink-dim)]">
            <summary className="min-h-11 cursor-pointer">What is included</summary>
            <p>
              Ownership is from the current board's dated league snapshot. Team names and standings
              are not included. Individual player values do not measure lineup strength. Season
              forecasts are currently included for your roster; other teams' missing season
              forecasts remain unfilled.
            </p>
          </details>
        </>
      )}
    </AppShell>
  );
}
