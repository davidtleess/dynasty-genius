// DG-203 — the value board, rebound to the accepted backend contract.
//
// The imported layout is kept: grouped by position, dense rows on desktop, a compact row on the phone.
// Four columns changed, each because the accepted source cannot support what the old one claimed:
//
//   Age            removed — not carried by the accepted source.
//   Rank margin    was a movement chip that printed "Level" for a null. Now a difference in places,
//                  computed from the interval edges of one common population, absent when absent.
//   Margin on worth removed — it subtracted our number from a price derived off the market's own curve.
//   Worth / Tier   split into our advantage and the market's price, each labelled in its own unit,
//                  never subtracted. Tier removed: the accepted source carries none.
//
// Selecting a player preserves the rest of the query string, so an in-flight comparison survives.
import { useNavigate } from "@tanstack/react-router";
import { useMemo } from "react";

import { say } from "@/lib/dg/copy";
import type { BoardRow } from "@/lib/dg/backend";
import {
  AdvantageCell,
  GapCell,
  Headshot,
  OwnershipCell,
  PointsCell,
  PriceCell,
  RankPair,
} from "./Cells";

const COLUMNS = "minmax(200px,2.2fr) 150px 130px 140px 140px 82px 82px";

export function BoardTable({
  rows,
  groupByPosition,
  emptyNote,
  nowLabel = "This season",
  futureLabel = "Future",
}: {
  rows: BoardRow[];
  groupByPosition?: boolean;
  emptyNote?: string;
  nowLabel?: string;
  futureLabel?: string;
}) {
  const groups = useMemo(() => {
    if (!groupByPosition) return [["All players", rows] as const];
    const known = ["QB", "RB", "WR", "TE"];
    const listed = known
      .map((pos) => [say(pos), rows.filter((r) => r.position === pos)] as const)
      .filter(([, list]) => list.length > 0);
    // Anyone whose position is not one of the four still appears, so no player can disappear
    // because of how the board chose to group.
    const rest = rows.filter((r) => !known.includes(r.position ?? ""));
    return rest.length ? [...listed, ["Other positions", rest] as const] : listed;
  }, [rows, groupByPosition]);

  if (!rows.length) {
    return (
      <p className="rounded-md border bg-[var(--surface)] p-4 text-sm text-[var(--ink-dim)]">
        {emptyNote ?? "No players in this view."}
      </p>
    );
  }

  return (
    <div className="space-y-6">
      {groups.map(([heading, list]) => (
        <section key={heading}>
          <div className="mb-1 flex items-baseline justify-between">
            <h2 className="text-[13px] font-semibold tracking-tight">{heading}</h2>
            <span className="label-caps">{list.length} players</span>
          </div>

          <div className="hidden min-[1400px]:block">
            <div
              className="row-grid label-caps"
              style={{ gridTemplateColumns: COLUMNS, minHeight: 34, gap: "0 12px" }}
            >
              <span>Player</span>
              <span>Rank ours / market</span>
              <span>Rank difference</span>
              <span>Our advantage</span>
              <span>Market price</span>
              <span>{nowLabel}</span>
              <span>{futureLabel}</span>
            </div>
            {list.map((row) => (
              <DesktopRow key={row.player_id} row={row} />
            ))}
          </div>

          <div className="min-[1400px]:hidden">
            {list.map((row) => (
              <PhoneRow key={row.player_id} row={row} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

/** Keeps every other search key, so opening a player never drops an in-flight comparison. */
function useOpenPlayer() {
  const navigate = useNavigate();
  return (playerId: string) =>
    navigate({
      to: ".",
      search: (prev: Record<string, unknown>) => ({ ...prev, player: playerId }),
    });
}

function NameCell({ row }: { row: BoardRow }) {
  return (
    <span className="flex min-w-0 items-center gap-2">
      <Headshot row={row} />
      <span className="min-w-0">
        <span className="block truncate text-[14px] font-semibold">{row.full_name}</span>
        <span className="label-caps">
          {row.position ?? "—"}
          {row.team ? ` · ${row.team}` : " · no NFL team"}
          {row.status ? ` · ${say(row.status)}` : ""}
        </span>
      </span>
    </span>
  );
}

function DesktopRow({ row }: { row: BoardRow }) {
  const open = useOpenPlayer();
  return (
    <button
      type="button"
      onClick={() => open(row.player_id)}
      className="row-grid w-full text-left hover:bg-[var(--surface)]"
      style={{ gridTemplateColumns: COLUMNS, gap: "0 12px" }}
      aria-label={`${row.full_name}. ${row.ownership}.`}
    >
      <NameCell row={row} />
      <RankPair ours={row.our_rank} market={row.market_rank} />
      <GapCell row={row} />
      <AdvantageCell row={row} />
      <PriceCell row={row} />
      <PointsCell value={row.now_points} startingEstimate={row.starting_estimate} />
      <PointsCell value={row.future_points} startingEstimate={row.starting_estimate} />
    </button>
  );
}

function PhoneRow({ row }: { row: BoardRow }) {
  const open = useOpenPlayer();
  return (
    <button
      type="button"
      onClick={() => open(row.player_id)}
      className="row-grid w-full text-left"
      style={{ gridTemplateColumns: "1fr auto", gap: "0 10px", minHeight: 44 }}
      aria-label={`${row.full_name}. ${row.ownership}.`}
    >
      <NameCell row={row} />
      <span className="flex flex-col items-end gap-0.5">
        <RankPair ours={row.our_rank} market={row.market_rank} />
        <GapCell row={row} />
      </span>
    </button>
  );
}

export { OwnershipCell };
