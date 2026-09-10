// DG-203 — board cells, rebound to the accepted backend contract.
//
// The imported design is kept. What changed is what the cells are allowed to say, and every change
// answers a finding from the DG-203 value-integrity review of the live app:
//
//   · TierChip is gone. The accepted source carries no tier. The names David ratified in July were
//     real, but the cutoffs behind them were hardcoded percentiles, which is the thing he ruled out.
//   · MarginCell is gone. Its input was a worth margin computed against a value read off the market's
//     own curve, so it restated the rank disagreement rather than corroborating it.
//   · MoveChip rendered "Level" for a null. That is the Rasheen Ali defect: a player the market does
//     not price at all was shown as agreeing with us. Absence now reads as absence, everywhere.
//   · Ranks are intervals, so a tie is drawn as the span it is. Formatting is delegated to the
//     backend's rankLabel and gapLabel so this file cannot drift from the contract.
//
// Our number and the market's are different units and are never subtracted.
import { useState } from "react";

import {
  gapLabel,
  rankLabel,
  pointsLabel,
  type BoardRow,
  type RankInterval,
} from "@/lib/dg/backend";

/**
 * Points above replacement over five seasons — our unit. Never a price.
 *
 * `compact` drops the trailing unit because a table states it once in the header; every standalone
 * use, the drawer included, keeps it. The unit never disappears from the screen, it only stops
 * repeating on every row.
 */
export function AdvantageCell({ row, compact = false }: { row: BoardRow; compact?: boolean }) {
  // A player can carry a forecast and still carry no valuation, so this says only what is absent.
  // The reason belongs in the drawer, at length; a board cell has room for the fact alone.
  if (row.projected_advantage == null) return <span className="label-caps">No valuation</span>;
  return (
    <span className="num text-[13px]" style={{ color: "var(--ours)" }}>
      {row.model_zero_tie ? "0 · floor" : row.projected_advantage.toFixed(1)}
      {compact ? null : (
        <span className="label-caps ml-1" style={{ color: "var(--ink-faint)" }}>
          pts over replacement
        </span>
      )}
    </span>
  );
}

/**
 * A FantasyCalc price. A different unit from ours, and labelled as one.
 *
 * It is a number on FantasyCalc's own scale, not money, so it never carries a currency mark and is
 * never differenced against our points.
 */
export function PriceCell({ row, compact = false }: { row: BoardRow; compact?: boolean }) {
  if (row.market_value == null) return <span className="label-caps">Not priced</span>;
  return (
    <span className="num text-[13px]" style={{ color: "var(--market)" }}>
      {Math.round(row.market_value).toLocaleString()}
      {compact ? null : (
        <span className="label-caps ml-1" style={{ color: "var(--ink-faint)" }}>
          FantasyCalc price
        </span>
      )}
    </span>
  );
}

/** Both ranks, on the one common population. Ties keep their span. */
export function RankPair({
  ours,
  market,
}: {
  ours: RankInterval | null;
  market: RankInterval | null;
}) {
  return (
    <span className="num flex items-baseline gap-2 whitespace-nowrap text-[13px]">
      <span style={{ color: "var(--ours)" }}>{rankLabel(ours)}</span>
      <span style={{ color: "var(--ink-faint)" }}>/</span>
      <span style={{ color: "var(--market)" }}>{rankLabel(market)}</span>
    </span>
  );
}

/**
 * The rank difference, in places, from the interval edges. Colour never carries the direction:
 * the word does. An unavailable pair says so and never borrows an equality word.
 */
export function GapCell({ row }: { row: BoardRow }) {
  const unavailable = row.comparison.direction === "unavailable";
  return (
    <span
      className={unavailable ? "label-caps" : "num text-[13px]"}
      style={{ color: unavailable ? "var(--ink-dim)" : "var(--foreground)" }}
    >
      {gapLabel(row)}
    </span>
  );
}

/** A season total. Absent is absent; a real zero prints as a zero. */
export function PointsCell({
  value,
  startingEstimate = false,
  compact = false,
}: {
  value: number | null;
  startingEstimate?: boolean;
  compact?: boolean;
}) {
  if (value == null) return <span className="label-caps">No forecast</span>;
  return (
    <span className="num text-[13px]" style={{ color: "var(--foreground)" }}>
      {pointsLabel(value)}
      {/* A starting estimate is a qualification, not a unit, so it survives compact mode. It is
          marked with a dot rather than the full phrase where the row has no width for it. */}
      {startingEstimate ? (
        <span className="label-caps ml-1" style={{ color: "var(--ink-faint)" }}>
          {compact ? "est" : "starting estimate"}
        </span>
      ) : null}
    </span>
  );
}

/** Ownership as the capture recorded it, stated once. */
export function OwnershipCell({ row }: { row: BoardRow }) {
  return <span className="label-caps whitespace-nowrap">{row.ownership}</span>;
}

export function PositionBadge({
  position,
  team,
}: {
  position: string | null;
  team: string | null;
}) {
  return (
    <span className="label-caps whitespace-nowrap">
      {position ?? "—"}
      {team ? ` · ${team}` : ""}
    </span>
  );
}

/** Two letters from the player's own name, for when no photo resolves. */
export function initials(fullName: string): string {
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "?";
  const first = parts[0]?.[0] ?? "";
  const last = parts.length > 1 ? (parts.at(-1)?.[0] ?? "") : "";
  return (first + last).toUpperCase() || "?";
}

/**
 * Two ways a face is absent, and both end at initials.
 *
 * Locally every row carries a URL and the case that happens is one that 404s or times out, which
 * renders as a broken image unless the error is caught. In hosted mode a player the release does not
 * carry has no URL at all, so there is nothing to request: asking anyway would spend a round trip to
 * be told what the manifest already said.
 */
export function Headshot({ row, size = 28 }: { row: BoardRow; size?: number }) {
  const [failed, setFailed] = useState(false);
  const url = failed ? null : row.headshot_url;
  return (
    <span
      className="inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full"
      style={{ width: size, height: size, background: "var(--hairline)" }}
    >
      {url === null ? (
        <span className="label-caps" style={{ color: "var(--ink-dim)" }}>
          {initials(row.full_name)}
        </span>
      ) : (
        <img
          src={url}
          alt=""
          width={size}
          height={size}
          loading="lazy"
          decoding="async"
          onError={() => setFailed(true)}
          style={{ width: size, height: size, objectFit: "cover" }}
        />
      )}
    </span>
  );
}
