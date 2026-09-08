// DG-187 — the workspace shell.
//
// David authorized implementing the Claude Design workspace on 2026-09-07 ("Implement: Dynasty
// Genius Workspace.dc.html"). This is the imported composition — top bar, neutral rail, source
// strip, one search, main region — converted to the repository's own React, tokens and primitives.
//
// What did NOT come across, deliberately: the design's sample team and league names, its sample
// dates and percentages, and its design-review chrome (the mode toggles, the phone mock frame and
// the "values are sample data" note). Those are the artefacts of a review deck, not of a product.
// Every date and count on this screen arrives as a prop; an unknown count renders as nothing at
// all rather than as a zero, because "we do not know yet" and "none" are different facts.
//
// The frame renders NO h1: the view it frames owns the heading, so a screen has exactly one.
import "./WorkspaceFrame.css";
import { humanizeDate } from "../research/comparisonHelpers";
import type { WorkspaceFrameProps, WorkspaceView } from "./types";

const DESTINATIONS: { view: WorkspaceView; label: string }[] = [
  { view: "today", label: "Today" },
  { view: "roster", label: "Roster" },
  { view: "available", label: "Available" },
  { view: "watchlist", label: "Watchlist" },
  { view: "compare", label: "Compare" },
  { view: "history", label: "What changed" },
];

/**
 * The calendar day a capture belongs to. A date-only value has no time in it, so none is shown;
 * inventing "00:00" would be a precision the source never claimed.
 */
function dayLabel(value: string): string {
  const parsed = Date.parse(value.length === 10 ? `${value}T12:00:00Z` : value);
  if (Number.isNaN(parsed)) return value;
  return new Date(parsed).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

/** The precise instant when the source carries one, the day when it does not. */
function preciseLabel(value: string): string {
  return value.length === 10 ? dayLabel(value) : humanizeDate(value);
}

function countFor(
  view: WorkspaceView,
  counts: WorkspaceFrameProps["counts"],
): number | null {
  if (view === "roster") return counts.roster;
  if (view === "available") return counts.available;
  if (view === "watchlist") return counts.watchlist;
  return null;
}

export function WorkspaceFrame({
  view,
  onNavigate,
  query,
  onQuery,
  counts,
  source,
  children,
  sourceActions,
}: WorkspaceFrameProps) {
  return (
    <div className="dg-workspace">
      <a className="dg-workspace__skip" href="#dg-workspace-main">
        Skip to main content
      </a>

      <header className="dg-workspace__topbar">
        <span className="dg-workspace__wordmark">Dynasty Genius</span>
      </header>

      <div className="dg-workspace__body">
        {/* Neutral chrome: the rail is furniture and never wears a lane hue. */}
        <nav className="dg-workspace__rail" aria-label="Workspace">
          <ul className="dg-workspace__rail-list">
            {DESTINATIONS.map((destination) => {
              const count = countFor(destination.view, counts);
              return (
                <li key={destination.view}>
                  <button
                    type="button"
                    className="dg-workspace__nav"
                    aria-current={view === destination.view ? "page" : undefined}
                    onClick={() => onNavigate(destination.view)}
                  >
                    <span>{destination.label}</span>
                    {/* A real space: without it the accessible name reads "Roster27". */}
                    {count !== null && (
                      <>
                        {" "}
                        <span className="dg-workspace__count">{count}</span>
                      </>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
          {/* The league's settings are fixed and verified against the saved snapshot; the team and
              league NAMES in the design file are sample data and are not reproduced. */}
          <div className="dg-workspace__league">
            <span className="dg-workspace__league-name">David's league</span>
            <span className="dg-workspace__league-rules">
              12-team · Superflex · full PPR
            </span>
            <span className="dg-workspace__league-rules">
              no tight-end premium · title in week 17
            </span>
          </div>
        </nav>

        <main className="dg-workspace__main" id="dg-workspace-main" tabIndex={-1}>
          {/* The compact strip IS the summary, so a phone gets one line and the full sentences
              stay one press away. Furniture, not a reading. */}
          <details className="dg-workspace__source">
            <summary className="dg-workspace__source-strip">
              {source === null ? (
                <span>Source dates are not available on this screen yet.</span>
              ) : (
                <>
                  <span>Our values · {dayLabel(source.forecastDate)}</span>
                  <span>Market prices · {dayLabel(source.marketDate)}</span>
                  <span>{source.commonPlayers} players carry both numbers</span>
                </>
              )}
            </summary>
            {source !== null && (
              <ul className="dg-workspace__source-facts">
                <li>
                  Our values are the forecast dated {preciseLabel(source.forecastDate)}.
                </li>
                <li>
                  Market prices are the FantasyCalc capture dated{" "}
                  {preciseLabel(source.marketDate)}.
                </li>
                <li>
                  League ownership is the roster capture dated{" "}
                  {preciseLabel(source.ownershipDate)}.
                </li>
                <li>
                  {source.commonPlayers} players carry both a rank from us and a rank
                  from the market, and only those two ranks are ever compared.
                </li>
              </ul>
            )}
            {sourceActions}
          </details>

          <div className="dg-workspace__search">
            <label className="dg-workspace__search-label" htmlFor="dg-workspace-search">
              Find a player
            </label>
            <input
              id="dg-workspace-search"
              className="dg-workspace__search-input"
              type="search"
              value={query}
              placeholder="Name, team, or position"
              autoComplete="off"
              onChange={(event) => onQuery(event.target.value)}
            />
          </div>

          {children}
        </main>
      </div>
    </div>
  );
}
