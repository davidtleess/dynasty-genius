// DG-181 — Compare players (David's "yes" 2026-09-07; brief ROSTER-SPOT-COMPARISON-2026-09-07).
//
// "How does this available player compare with the player whose roster spot I am considering?"
// David picks both; nothing is nominated for him. Reads /api/research/comparison — the accepted
// research report and its bound catalog, composed read-only by the API — and shows each player's
// 2026 forecast and his 2027–2030 forecasts as two separate windows, never a trend. For two
// players at the same position the difference is said in words for the named period; across
// positions both forecasts are shown and no winner is named. Selection state belongs to the
// caller so it survives switching research tabs; nothing here is persisted.
import { useEffect, useId, useState } from "react";

import { PlayerIdentity } from "../ui/PlayerIdentity";
import { TableScroll } from "../ui/TableScroll";
import { formatAvailablePoints } from "./availableHelpers";
import {
  CAVEAT,
  type ComparisonPayload,
  type ComparisonPlayer,
  classWord,
  compareForecasts,
  findPlayer,
  finitePoints,
  formatSignedPoints,
  humanizeDate,
  type Period,
  periodsFor,
  searchPlayers,
  statusWord,
} from "./comparisonHelpers";
import "./RosterComparison.css";

export type ComparisonSelection = {
  availableId: string | null;
  rosterId: string | null;
};
export const EMPTY_SELECTION: ComparisonSelection = {
  availableId: null,
  rosterId: null,
};

type Side = "available" | "roster";
const SIDE_LABEL: Record<Side, string> = {
  available: "Available player",
  roster: "Your player",
};
const TAXI_LABEL = "Taxi / IR in saved roster";
const WORDS: Record<number, string> = {
  1: "one",
  2: "two",
  3: "three",
  4: "four",
  5: "five",
  6: "six",
};
const seasonsWord = (n: number) => WORDS[n] ?? String(n);

function Identity({ p }: { p: ComparisonPlayer }) {
  return (
    <>
      <PlayerIdentity
        name={p.name}
        team={p.team ?? ""}
        position={p.position}
        imageStatus="missing"
      />
      {p.taxi_or_reserve === true && (
        <span className="dg-compare__flag">{TAXI_LABEL}</span>
      )}
    </>
  );
}

// One chooser: a search box over a fixed list with the matches as plain buttons (keyboard-
// reachable with nothing custom), collapsing to the chosen identity plus "Change" once picked.
// The list is alphabetical, so it never ranks anyone.
function PlayerPicker({
  side,
  players,
  selected,
  onPick,
  allWhenEmpty,
  changing,
  onChanging,
}: {
  side: Side;
  players: ComparisonPlayer[];
  selected: ComparisonPlayer | null;
  onPick: (id: string) => void;
  allWhenEmpty: boolean;
  /** The page owns "which side is being changed": once both players are chosen the chooser is
   *  not rendered at all and each card's Change reopens it, so the pair leads on a phone. */
  changing: boolean;
  onChanging: (changing: boolean) => void;
}) {
  const label = SIDE_LABEL[side];
  const inputId = useId();
  const [query, setQuery] = useState("");
  const open = selected === null || changing;
  if (!open && selected) {
    // Only reached before the pair exists (the other side is still unchosen): one line that says
    // who is picked, with his dated status, and a way to change it.
    return (
      <div className="dg-compare__picker">
        <div className="dg-compare__chosen">
          <span className="dg-research__search-label">{label}</span>
          <span className="dg-compare__chosen-name">{selected.name}</span>
          <span className="dg-compare__status">
            {selected.position}
            {selected.team ? ` ${selected.team}` : ""}
          </span>
          <span className="dg-compare__status">{statusWord(selected, side)}</span>
          <button
            type="button"
            className="dg-research__why"
            aria-label={`Change ${label}`}
            onClick={() => onChanging(true)}
          >
            Change
          </button>
        </div>
      </div>
    );
  }
  const q = query.trim();
  const { matches, total } = searchPlayers(players, query, { allWhenEmpty });
  const lower = label.toLowerCase();
  let hint: string;
  if (!q && !allWhenEmpty) hint = `Type to search the ${players.length} ${lower}s.`;
  else if (!q && matches.length < total)
    hint = `Showing ${matches.length} of ${total}, A to Z; search to find the rest.`;
  else if (!q) hint = `${total} listed, A to Z.`;
  else if (total === 0) hint = `No ${lower} matches "${q}".`;
  else if (matches.length < total)
    hint = `${matches.length} of ${total} match; keep typing to narrow.`;
  else hint = `${total} ${total === 1 ? "match" : "matches"}.`;
  return (
    <div className="dg-compare__picker">
      <div className="dg-research__search">
        <label className="dg-research__search-label" htmlFor={inputId}>
          {label}
        </label>
        <input
          id={inputId}
          className="dg-research__search-input"
          type="search"
          value={query}
          placeholder="Name, team or position"
          autoComplete="off"
          onChange={(e) => setQuery(e.target.value)}
        />
        <p className="dg-research__search-hint" role="status">
          {hint}
        </p>
      </div>
      {matches.length > 0 && (
        <ul className="dg-compare__options" aria-label={`${label}s`}>
          {matches.map((p) => (
            <li key={p.sleeper_id}>
              <button
                type="button"
                className="dg-compare__option"
                aria-label={`Choose ${p.name}`}
                aria-pressed={selected?.sleeper_id === p.sleeper_id}
                onClick={() => {
                  onPick(p.sleeper_id);
                  onChanging(false);
                  setQuery("");
                }}
              >
                <Identity p={p} />
                <span className="dg-compare__status">{statusWord(p, side)}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Num({
  label,
  value,
  missingReason,
}: {
  label: string;
  value: number | null;
  missingReason: string | null;
}) {
  const v = finitePoints(value);
  return (
    <div className="dg-compare__num">
      <span className="dg-compare__num-label">{label}</span>
      <span className="dg-compare__num-value">
        {v === null ? "—" : formatAvailablePoints(v)}
      </span>
      {v === null && (
        <small className="dg-compare__num-note">{missingReason ?? "no value"}</small>
      )}
    </div>
  );
}

function SideCard({
  p,
  side,
  now,
  future,
  onChange,
}: {
  p: ComparisonPlayer;
  side: Side;
  now: Period;
  future: Period;
  onChange: () => void;
}) {
  return (
    // biome-ignore lint/a11y/useSemanticElements: a player card is a named non-form grouping; a fieldset would describe it as form controls and bring the fieldset min-content width quirk.
    <div
      className="dg-compare__side"
      data-side={side}
      role="group"
      aria-label={`${SIDE_LABEL[side]}: ${p.name}`}
    >
      <div className="dg-compare__side-head">
        <Identity p={p} />
        <button
          type="button"
          className="dg-research__why"
          aria-label={`Change ${SIDE_LABEL[side]}`}
          onClick={onChange}
        >
          Change
        </button>
      </div>
      <span className="dg-compare__status">{statusWord(p, side)}</span>
      <div className="dg-compare__nums">
        <Num label={now.label} value={p.now_points} missingReason={p.missing_reason} />
        <Num
          label={future.label}
          value={p.future_points}
          missingReason={p.missing_reason}
        />
      </div>
    </div>
  );
}

function seasonCell(p: ComparisonPlayer, year: number) {
  const s = p.seasons.find((x) => x.season === year);
  const v = finitePoints(s?.points);
  const cls = classWord(s?.estimate_class);
  return (
    <>
      {v === null ? "—" : formatAvailablePoints(v)}
      {cls && <small>{cls}</small>}
    </>
  );
}

function comparisonUrl(): string {
  const page = new URLSearchParams(window.location.search);
  const q = new URLSearchParams();
  for (const k of ["run", "catalog"]) {
    const v = page.get(k);
    if (v) q.set(k, v);
  }
  const qs = q.toString();
  return qs ? `/api/research/comparison?${qs}` : "/api/research/comparison";
}

export function RosterComparison({
  selection,
  onSelect,
}: {
  selection: ComparisonSelection;
  onSelect: (next: ComparisonSelection) => void;
}) {
  const [data, setData] = useState<ComparisonPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Which side David is re-choosing, if any. Once both players are chosen the choosers leave
  // the page and only come back one at a time from a card's Change, so the pair leads.
  const [changing, setChanging] = useState<Side | null>(null);
  useEffect(() => {
    let live = true;
    (async () => {
      try {
        const res = await fetch(comparisonUrl());
        if (!res.ok) {
          const body = (await res.json().catch(() => ({}))) as { detail?: string };
          throw new Error(body.detail ?? `HTTP ${res.status}`);
        }
        const json = (await res.json()) as ComparisonPayload;
        if (live) setData(json);
      } catch (e) {
        if (live) setError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      live = false;
    };
  }, []);

  if (error) {
    return (
      <section className="dg-compare" aria-label="Compare players section">
        <p className="dg-research__empty">No comparison to show: {error}</p>
      </section>
    );
  }
  if (!data) {
    return (
      <section className="dg-compare" aria-label="Compare players section">
        <p className="dg-research__empty">Loading the comparison…</p>
      </section>
    );
  }
  const emptyWhich =
    data.available.length === 0 && data.roster.length === 0
      ? "both lists"
      : data.available.length === 0
        ? "the available list"
        : data.roster.length === 0
          ? "your roster list"
          : null;
  if (emptyWhich) {
    return (
      <section className="dg-compare" aria-label="Compare players section">
        <p className="dg-research__empty">
          The comparison has no players to offer: {emptyWhich} is empty in this catalog.
        </p>
      </section>
    );
  }

  // Everything below is derived from the two ids on every render, so a changed pick can never
  // leave the previous player's numbers standing under a new name.
  const defaultPool = data.available.filter((p) => p.population === "default");
  const a = findPlayer(data.available, selection.availableId);
  const b = findPlayer(data.roster, selection.rosterId);
  const unresolvedAvailable = selection.availableId !== null && a === null;
  const { now, future } = periodsFor(data);
  const verdictNow = a && b ? compareForecasts(a, b, now) : null;
  const verdictFuture = a && b ? compareForecasts(a, b, future) : null;
  const samePosition = a !== null && b !== null && a.position === b.position;

  const bothChosen = a !== null && b !== null;
  const showAvailablePicker = !bothChosen || changing === "available";
  const showRosterPicker = !bothChosen || changing === "roster";
  const futureCount = seasonsWord(data.future_years.length);

  return (
    <section className="dg-compare" aria-label="Compare players section">
      {bothChosen ? (
        <p className="dg-research__lede">
          {now.label} is one season's forecast; {future.label} is {futureCount} seasons
          added together.
        </p>
      ) : (
        <p className="dg-research__lede">
          Pick one available player and one player you own. Their {now.label} forecast
          and their {future.label} forecasts are shown separately — one season and{" "}
          {futureCount} future seasons are different windows, not a trend.
        </p>
      )}
      {unresolvedAvailable && (
        <p className="dg-compare__notice" role="status">
          That player is not an available choice in this catalog (owned in your league,
          or identity unresolved). Pick an available player.
        </p>
      )}
      {(showAvailablePicker || showRosterPicker) && (
        <div className="dg-compare__pickers">
          {showAvailablePicker && (
            <PlayerPicker
              side="available"
              players={defaultPool}
              selected={a}
              allWhenEmpty={false}
              changing={changing === "available"}
              onChanging={(c) => setChanging(c ? "available" : null)}
              onPick={(id) => onSelect({ ...selection, availableId: id })}
            />
          )}
          {showRosterPicker && (
            <PlayerPicker
              side="roster"
              players={data.roster}
              selected={b}
              allWhenEmpty={true}
              changing={changing === "roster"}
              onChanging={(c) => setChanging(c ? "roster" : null)}
              onPick={(id) => onSelect({ ...selection, rosterId: id })}
            />
          )}
        </div>
      )}

      {(a === null) !== (b === null) && (
        <p className="dg-research__lede">
          Pick the other player to see the two forecasts together.
        </p>
      )}

      {a && b && verdictNow && verdictFuture && (
        <div className="dg-compare__board">
          {/* biome-ignore lint/a11y/useSemanticElements: the pair is a named non-form grouping of two cards, not a set of form controls. */}
          <div
            className="dg-compare__pair"
            role="group"
            aria-label="The two players side by side"
          >
            <SideCard
              p={a}
              side="available"
              now={now}
              future={future}
              onChange={() => setChanging("available")}
            />
            <SideCard
              p={b}
              side="roster"
              now={now}
              future={future}
              onChange={() => setChanging("roster")}
            />
          </div>
          <p className="dg-compare__headline" role="status">
            {verdictNow.kind === "cross_position" ? (
              verdictNow.sentence
            ) : (
              <>
                <span>{verdictNow.sentence}</span> <span>{verdictFuture.sentence}</span>
              </>
            )}
          </p>
          <p className="dg-compare__caveat">{CAVEAT}</p>

          <TableScroll label="Season by season">
            <table className="dg-research__table dg-compare__seasons">
              <thead>
                <tr>
                  <th scope="col">Season</th>
                  <th scope="col">{a.name}</th>
                  <th scope="col">{b.name}</th>
                  {samePosition && (
                    <th scope="col">
                      Difference{" "}
                      <small>
                        {a.name} minus {b.name}
                      </small>
                    </th>
                  )}
                </tr>
              </thead>
              <tbody>
                {data.forecast_years.map((yr) => {
                  const av = finitePoints(
                    a.seasons.find((s) => s.season === yr)?.points,
                  );
                  const bv = finitePoints(
                    b.seasons.find((s) => s.season === yr)?.points,
                  );
                  return (
                    <tr key={yr}>
                      <th scope="row">{yr}</th>
                      <td>{seasonCell(a, yr)}</td>
                      <td>{seasonCell(b, yr)}</td>
                      {samePosition && (
                        <td>
                          {av !== null && bv !== null && Number.isFinite(av - bv)
                            ? formatSignedPoints(av - bv)
                            : "—"}
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </TableScroll>

          <details className="dg-research__details">
            <summary>What these forecasts are, and what is missing</summary>
            <ul className="dg-research__facts">
              {[a, b].map((p) => (
                <li key={p.sleeper_id}>
                  {p.name}: {p.evidence_note}
                  {p.missing_reason ? ` Missing: ${p.missing_reason}.` : ""}
                </li>
              ))}
              <li>{data.scoring_note}</li>
              <li>
                Ownership as of {humanizeDate(data.source.ownership_as_of)}; NFL status
                as of {humanizeDate(data.source.nfl_status_as_of)}. Both may have
                changed since.
              </li>
              <li>
                <span className="dg-research__provenance-id">
                  Research run {data.source.report_run} · catalog{" "}
                  {data.source.catalog_run} · report{" "}
                  {data.source.report_sha256.slice(0, 12)}…
                </span>
              </li>
            </ul>
          </details>
        </div>
      )}
    </section>
  );
}
