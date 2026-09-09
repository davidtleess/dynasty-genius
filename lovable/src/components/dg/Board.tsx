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

const COLUMNS = "minmax(180px,2fr) 128px 168px 112px 108px 88px 96px";
const VALUE_COLUMNS = "minmax(180px,2fr) 128px 168px 140px 128px";

/** The caller's label may already name its unit; appending one blindly reads "2026 points points". */
const withPoints = (label: string) => (/points?$/i.test(label.trim()) ? label : `${label} points`);

/** Right-aligned, tabular, so a column of numbers can be compared down the page. */
const figure: React.CSSProperties = {
  textAlign: "right",
  fontVariantNumeric: "tabular-nums",
  justifySelf: "end",
};

export function BoardTable({
  rows,
  groupByPosition,
  emptyNote,
  nowLabel = "This season",
  futureLabel = "Future",
  showSeasonForecasts = true,
}: {
  rows: BoardRow[];
  groupByPosition?: boolean;
  emptyNote?: string;
  nowLabel?: string;
  futureLabel?: string;
  showSeasonForecasts?: boolean;
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
              style={{
                gridTemplateColumns: showSeasonForecasts ? COLUMNS : VALUE_COLUMNS,
                minHeight: 34,
                gap: "0 12px",
              }}
            >
              {/* The unit is stated once, here, so it stops repeating on every row below. */}
              <span>Player</span>
              <span style={figure}>Rank ours / market</span>
              <span style={figure}>Rank difference</span>
              <span style={figure}>Our points over replacement</span>
              <span style={figure}>FantasyCalc price</span>
              {showSeasonForecasts ? (
                <>
                  <span style={figure}>{withPoints(nowLabel)}</span>
                  <span style={figure}>{withPoints(futureLabel)}</span>
                </>
              ) : null}
            </div>
            {list.map((row) => (
              <DesktopRow key={row.player_id} row={row} showSeasonForecasts={showSeasonForecasts} />
            ))}
          </div>

          <div className="min-[1400px]:hidden">
            {list.map((row) => (
              <PhoneRow
                key={row.player_id}
                row={row}
                nowLabel={nowLabel}
                futureLabel={futureLabel}
                showSeasonForecasts={showSeasonForecasts}
              />
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

function DesktopRow({ row, showSeasonForecasts }: { row: BoardRow; showSeasonForecasts: boolean }) {
  const open = useOpenPlayer();
  return (
    <button
      type="button"
      onClick={() => open(row.player_id)}
      className="row-grid w-full text-left hover:bg-[var(--surface)]"
      style={{ gridTemplateColumns: showSeasonForecasts ? COLUMNS : VALUE_COLUMNS, gap: "0 12px" }}
      aria-label={`${row.full_name}. ${row.ownership}.`}
    >
      <NameCell row={row} />
      <span style={figure}>
        <RankPair ours={row.our_rank} market={row.market_rank} />
      </span>
      {/* The one focal number on the row: how far apart the two readings are. */}
      <span style={{ ...figure, fontWeight: 600 }}>
        <GapCell row={row} />
      </span>
      <span style={figure}>
        <AdvantageCell row={row} compact />
      </span>
      <span style={figure}>
        <PriceCell row={row} compact />
      </span>
      {showSeasonForecasts ? (
        <>
          <span style={figure}>
            <PointsCell value={row.now_points} startingEstimate={row.starting_estimate} compact />
          </span>
          <span style={figure}>
            <PointsCell
              value={row.future_points}
              startingEstimate={row.starting_estimate}
              compact
            />
          </span>
        </>
      ) : null}
    </button>
  );
}

function PhoneRow({
  row,
  nowLabel,
  futureLabel,
  showSeasonForecasts,
}: {
  row: BoardRow;
  nowLabel: string;
  futureLabel: string;
  showSeasonForecasts: boolean;
}) {
  const open = useOpenPlayer();
  return (
    <button
      type="button"
      onClick={() => open(row.player_id)}
      className="w-full rounded-md border p-3 text-left"
      style={{ borderColor: "var(--hairline)", minHeight: 44 }}
      aria-label={`${row.full_name}. ${row.ownership}.`}
    >
      <span className="flex items-start justify-between gap-3 max-[360px]:flex-col max-[360px]:gap-2">
        <NameCell row={row} />
        <span className="flex shrink-0 flex-col items-end gap-0.5 max-[360px]:w-full">
          <span className="label-caps">Ranks: ours / market</span>
          <RankPair ours={row.our_rank} market={row.market_rank} />
          <span className="text-[13px] font-semibold">
            <GapCell row={row} />
          </span>
        </span>
      </span>
      {/* Each value names its own unit here, because a card has no header to carry it. */}
      <span className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1">
        <PhoneValue label="Our points over replacement">
          <AdvantageCell row={row} compact />
        </PhoneValue>
        <PhoneValue label="FantasyCalc price">
          <PriceCell row={row} compact />
        </PhoneValue>
        {showSeasonForecasts ? (
          <>
            <PhoneValue label={withPoints(nowLabel)}>
              <PointsCell value={row.now_points} startingEstimate={row.starting_estimate} compact />
            </PhoneValue>
            <PhoneValue label={withPoints(futureLabel)}>
              <PointsCell value={row.future_points} compact />
            </PhoneValue>
          </>
        ) : null}
      </span>
    </button>
  );
}

function PhoneValue({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <span className="flex items-baseline justify-between gap-2">
      <span className="label-caps">{label}</span>
      <span style={{ fontVariantNumeric: "tabular-nums" }}>{children}</span>
    </span>
  );
}

export { OwnershipCell };
