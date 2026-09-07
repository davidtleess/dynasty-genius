// DG-178 — Available players (plan T4, 2026-09-06; David: "ok go"; root's frontend review 2026-09-07).
//
// Who can David actually pick up, what does the model expect now and later, and what do we
// not yet know? Reads /api/research/available — the immutable catalog built from the SAME
// accepted report the research preview serves. Ownership and NFL status filter AVAILABILITY
// only; every value is the producer's own expected season points. Forecast coverage and
// "has a value for this ordering" are kept distinct; ties are named on the selected basis
// only; a nonzero value never prints as zero. No FAAB, no drop or lineup advice, no breakout
// probability; the watchlist is David's own local shortlist.
import { useCallback, useEffect, useMemo, useState } from "react";

import { PlayerIdentity } from "../ui/PlayerIdentity";
import { TableScroll } from "../ui/TableScroll";
import "./AvailablePlayers.css";
import {
  ALL_STATUSES,
  type AvailableRow,
  BASIS_LABELS,
  DEFAULT_STATUSES,
  filterAvailable,
  formatAvailablePoints,
  hasForecast,
  keyFor,
  loadWatchlist,
  POSITIONS,
  type SortBasis,
  saveWatchlist,
  sortAvailable,
  unresolvedRow,
  type Watchlist,
  watchStatus,
} from "./availableHelpers";

type Population = {
  total: number;
  with_forecast: number;
  without_forecast: number;
  with_now?: number;
  with_future_total?: number;
  incomplete_path?: number;
  by_class: Record<string, number>;
};
type Payload = {
  source: {
    catalog_run: string;
    report_run: string;
    pinned: boolean;
    census_run_id: string | null;
  };
  freshness: {
    ownership_as_of: string | null;
    nfl_status_as_of: string | null;
    caveat: string;
  };
  populations: Record<string, Population>;
  populations_note: string | null;
  disclosures: {
    uncovered_sleeper_ids?: number;
    unmatched_nfl_records?: number;
    contested_nfl_records?: number;
    archive_unforecast_by_position?: Record<string, number>;
    note?: string;
  };
  forecast_note: string | null;
  forecast_years: number[];
  future_years: number[];
  notes: Record<string, string>;
  starting_estimates?: {
    count: number;
    rows: { sleeper_id: string; gsis: string; classes: Record<string, string> }[];
    source: {
      run_dir?: string;
      manifest_sha256?: string;
      estimates_sha256?: string;
      schema_version?: string;
    } | null;
    evidence: {
      selected_per_horizon?: Record<string, string>;
      horizons?: Record<
        string,
        Record<string, { n?: number; rmse_points?: number; brier?: number }>
      >;
      caveats?: Record<string, string>;
      meaning?: string;
    } | null;
  };
  rows: (AvailableRow & {
    join_basis?: string;
    identity_conflict?: string | null;
    forecast:
      | (AvailableRow["forecast"] & { join_basis?: string; join_id?: string })
      | null;
  })[];
};
type Row = Payload["rows"][number];

const STATUS_WORDS: Record<string, string> = {
  active: "active",
  practice_squad: "practice squad",
  injured_reserve: "injured reserve",
  cut: "cut",
  retired: "retired",
  unknown: "unknown identity",
};
const COLUMNS: { basis: SortBasis; heading: string }[] = [
  { basis: "now", heading: "2026 projected points" },
  { basis: "future", heading: "2027–2030 projected points" },
  { basis: "impact2", heading: "Two-year impact" },
  { basis: "impact5", heading: "Five-year impact" },
];

function storageOrNull(): Storage | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export type WatchlistState = {
  entries: Watchlist;
  notice: string | null;
  toggle: (r: AvailableRow) => void;
};

// David's local shortlist: read once from storage; a save failure keeps the list in memory for
// the life of the owner and says so. Owned by the research preview so it outlives the tab.
export function useWatchlist(): WatchlistState {
  const [state, setState] = useState<{ entries: Watchlist; notice: string | null }>(
    () => {
      const storage = storageOrNull();
      if (!storage) {
        return {
          entries: new Map(),
          notice:
            "Watchlist storage is unavailable in this browser; the shortlist will not persist.",
        };
      }
      const loaded = loadWatchlist(storage);
      return { entries: loaded.entries, notice: loaded.notice };
    },
  );
  const toggle = useCallback((r: AvailableRow) => {
    setState((prev) => {
      const next: Watchlist = new Map(prev.entries);
      if (next.has(r.sleeper_id)) next.delete(r.sleeper_id);
      else
        next.set(r.sleeper_id, {
          name: r.name,
          position: r.league_position,
          team: r.nfl_team,
          watched_at: new Date().toISOString(),
        });
      const storage = storageOrNull();
      const saved = storage !== null && saveWatchlist(storage, next);
      return {
        entries: next,
        notice: saved
          ? prev.notice
          : "The watchlist could not be saved in this browser; it will last only for this page.",
      };
    });
  }, []);
  return { entries: state.entries, notice: state.notice, toggle };
}

const CLASS_WORDS: Record<string, string> = {
  cold_start_candidate: "cold-start candidate",
  baseline_research_candidate: "historical baseline",
  unsupported: "unsupported",
};
type Evidence = NonNullable<Payload["starting_estimates"]>["evidence"];

// The producer's own out-of-time evidence for a starting estimate, in words: which years come
// from the draft-capital candidate, which from the position's historical baseline, and on how
// many paired rows with what measured error. Never a per-player certainty.
function startingEvidence(r: Row, ev: Evidence): string {
  const classes = r.estimate_classes ?? {};
  const years = Object.keys(classes).sort();
  const first = years[0];
  const h = ev?.horizons ?? {};
  const fmt = (v: number | undefined, d: number) => (v == null ? "—" : v.toFixed(d));
  const parts: string[] = [];
  if (first && classes[first] === "cold_start_candidate") {
    const c = h["1"]?.candidate;
    const b = h["1"]?.b1;
    parts.push(
      `Starting estimate: year 1 from the draft-capital candidate, which beat the position baseline on ${c?.n ?? "—"} paired historical rows (RMSE ${fmt(c?.rmse_points, 1)} vs ${fmt(b?.rmse_points, 1)}; Brier ${fmt(c?.brier, 3)} vs ${fmt(b?.brier, 3)})`,
    );
  } else if (first) {
    parts.push(
      "Starting estimate: year 1 from the position's historical baseline (the candidate was not clearly better)",
    );
  }
  const baseline = years.filter((y) => classes[y] === "baseline_research_candidate");
  if (baseline.length > 0) {
    const ns = baseline
      .map((y) => h[String(years.indexOf(y) + 1)]?.b1?.n)
      .filter((n): n is number => typeof n === "number");
    parts.push(
      `${baseline.length === 1 ? baseline[0] : `${baseline[0]}–${baseline[baseline.length - 1]}`} use the position's historical baseline because the candidate was not clearly better there${ns.length > 0 ? ` (n ${ns.join(" / ")})` : ""}`,
    );
  }
  const unsupported = years.filter((y) => classes[y] === "unsupported");
  if (unsupported.length > 0)
    parts.push(
      `${unsupported.join(", ")} unsupported by the producer and left missing`,
    );
  const caveat = ev?.caveats?.population;
  const sentence = (t: string) => `${t.charAt(0).toUpperCase()}${t.slice(1)}`;
  return `${parts.join("; ")}. ${caveat ? `${sentence(caveat)}. ` : ""}${ev?.meaning ? sentence(ev.meaning) : ""}`.trim();
}

function Identity({ r, watched }: { r: Row; watched: boolean }) {
  const status = watchStatus(r, watched);
  return (
    <div className="dg-avail__cell" data-testid="avail-name">
      <PlayerIdentity
        name={r.name}
        team={r.nfl_team ?? ""}
        position={r.league_position}
        imageStatus="missing"
      />
      <span className="dg-avail__status">
        {STATUS_WORDS[r.availability_class] ?? r.availability_class.replace(/_/g, " ")}
        {r.owned_now ? " · owned in your league" : ""}
        {r.starting_estimate ? " · starting estimate" : ""}
        {status ? ` · ${status}` : ""}
      </span>
    </div>
  );
}

function Why({
  r,
  notes,
  colSpan,
  evidence,
}: {
  r: Row;
  notes: Record<string, string>;
  colSpan: number;
  evidence?: Evidence | undefined;
}) {
  const fc = r.forecast;
  const classes = r.estimate_classes ?? {};
  return (
    <tr className="dg-research__detail">
      <td colSpan={colSpan}>
        <div className="dg-avail__prose">
          {fc ? (
            <p>
              Season by season, the producer's expected points and appearance
              probability:{" "}
              {fc.seasons
                .map(
                  (s) =>
                    `${s.season}: ${formatAvailablePoints(s.e_points)} pts, P(appears) ${s.p_appear == null ? "—" : s.p_appear.toFixed(2)}${classes[String(s.season)] ? ` (${CLASS_WORDS[classes[String(s.season)] ?? ""] ?? classes[String(s.season)]})` : ""}`,
                )
                .join(" · ")}
              . {notes.appearance}
            </p>
          ) : (
            <p>{r.missing_reason ?? "No forecast."}</p>
          )}
          {r.future_reason && <p>{r.future_reason}.</p>}
          {r.starting_estimate && <p>{startingEvidence(r, evidence ?? null)}</p>}
          {r.recovered && (
            <p>
              Recovered from the producer's frozen file under the census's verified NFL
              identity; not among the accepted board rows, so it has no impact number
              here.
            </p>
          )}
          <p className="dg-research__provenance">
            NFL status {r.nfl_status_raw ?? "—"}
            {r.nfl_team ? ` with ${r.nfl_team}` : ""} · league placement{" "}
            {r.league_position} (Sleeper eligibility {r.fantasy_positions || "—"})
            {r.join_basis ? ` · census join ${r.join_basis}` : ""}
            {fc?.join_basis
              ? ` · identity join ${fc.join_basis} ${fc.join_id ?? ""}`
              : ""}
            {r.identity_conflict ? ` · ${r.identity_conflict}` : ""}
            {fc ? ` · source ${fc.producer}` : ""}
          </p>
        </div>
      </td>
    </tr>
  );
}

// DG-181: "Compare" hands the row to the research page, which opens the comparison with this
// available player chosen and leaves the roster choice to David.
function CompareButton({
  r,
  onCompare,
}: {
  r: Row;
  onCompare: ((r: AvailableRow) => void) | undefined;
}) {
  if (!onCompare) return null;
  return (
    <>
      <button
        type="button"
        className="dg-research__why"
        aria-label={`Compare ${r.name}`}
        onClick={() => onCompare(r)}
      >
        Compare
      </button>{" "}
    </>
  );
}

function ValueRow({
  r,
  basis,
  tied,
  watched,
  onWatch,
  onCompare,
  notes,
  evidence,
}: {
  r: Row;
  basis: SortBasis;
  tied: string[];
  watched: boolean;
  onWatch: (r: Row) => void;
  onCompare?: ((r: AvailableRow) => void) | undefined;
  notes: Record<string, string>;
  evidence?: Evidence | undefined;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <tr data-population={r.population}>
        <td>
          <Identity r={r} watched={watched} />
        </td>
        {COLUMNS.map((c) => (
          <td key={c.basis} className="dg-avail__num">
            <span className={c.basis === basis ? "dg-avail__focal" : undefined}>
              {formatAvailablePoints(keyFor(r, c.basis))}
            </span>
            {c.basis === basis && tied.length > 0 && (
              <small className="dg-avail__tie">tied with {tied.length}</small>
            )}
          </td>
        ))}
        <td className="dg-avail__actions">
          <button
            type="button"
            className="dg-research__why"
            aria-pressed={watched}
            aria-label={`${watched ? "Unwatch" : "Watch"} ${r.name}`}
            onClick={() => onWatch(r)}
          >
            {watched ? "Unwatch" : "Watch"}
          </button>{" "}
          <CompareButton r={r} onCompare={onCompare} />
          <button
            type="button"
            className="dg-research__why"
            aria-expanded={open}
            onClick={(e) => {
              // a phone reader tapped Why at the right edge of a scrolled table: bring the row back to the left
              const scroller = e.currentTarget.closest(".dg-table-scroll");
              if (scroller && typeof scroller.scrollTo === "function")
                scroller.scrollTo({ left: 0 });
              setOpen((o) => !o);
            }}
          >
            {open ? "Hide" : "Why"}
          </button>
        </td>
      </tr>
      {open && (
        <Why r={r} notes={notes} colSpan={COLUMNS.length + 2} evidence={evidence} />
      )}
    </>
  );
}

function NoValueRow({
  r,
  reason,
  watched,
  onWatch,
  onCompare,
  notes,
  evidence,
}: {
  r: Row;
  reason: string;
  watched: boolean;
  onWatch: (r: Row) => void;
  onCompare?: ((r: AvailableRow) => void) | undefined;
  notes: Record<string, string>;
  evidence?: Evidence | undefined;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <tr data-population={r.population}>
        <td>
          <Identity r={r} watched={watched} />
        </td>
        <td className="dg-avail__reason">{reason}</td>
        <td className="dg-avail__num">{formatAvailablePoints(r.now_points)}</td>
        <td className="dg-avail__num">{formatAvailablePoints(r.future_points)}</td>
        <td className="dg-avail__actions">
          <button
            type="button"
            className="dg-research__why"
            aria-pressed={watched}
            aria-label={`${watched ? "Unwatch" : "Watch"} ${r.name}`}
            onClick={() => onWatch(r)}
          >
            {watched ? "Unwatch" : "Watch"}
          </button>{" "}
          <CompareButton r={r} onCompare={onCompare} />
          <button
            type="button"
            className="dg-research__why"
            aria-expanded={open}
            onClick={(e) => {
              // a phone reader tapped Why at the right edge of a scrolled table: bring the row back to the left
              const scroller = e.currentTarget.closest(".dg-table-scroll");
              if (scroller && typeof scroller.scrollTo === "function")
                scroller.scrollTo({ left: 0 });
              setOpen((o) => !o);
            }}
          >
            {open ? "Hide" : "Why"}
          </button>
        </td>
      </tr>
      {open && <Why r={r} notes={notes} colSpan={5} evidence={evidence} />}
    </>
  );
}

export function AvailablePlayers({
  watchlist,
  onCompare,
}: {
  watchlist?: WatchlistState;
  /** DG-181: when given, every row offers "Compare {name}" and hands back the row. */
  onCompare?: ((r: AvailableRow) => void) | undefined;
} = {}) {
  const [data, setData] = useState<Payload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [positions, setPositions] = useState<string[]>([]);
  const [statuses, setStatuses] = useState<string[]>([...DEFAULT_STATUSES]);
  const [basis, setBasis] = useState<SortBasis>("now");
  const [watchedOnly, setWatchedOnly] = useState(false);
  const [missingOnly, setMissingOnly] = useState(false);
  // The watchlist lives with the caller when one is given (the research preview owns it across
  // its internal tabs, so an in-memory fallback survives a tab switch); standalone use keeps its own.
  const own = useWatchlist();
  const wl = watchlist ?? own;
  const watched = wl.entries;
  const storageNotice = wl.notice;
  const toggleWatch = wl.toggle;

  useEffect(() => {
    let live = true;
    (async () => {
      try {
        const run = new URLSearchParams(window.location.search).get("run");
        const res = await fetch(
          run
            ? `/api/research/available?run=${encodeURIComponent(run)}`
            : "/api/research/available",
        );
        if (!res.ok) {
          const body = (await res.json().catch(() => ({}))) as { detail?: string };
          throw new Error(body.detail ?? `HTTP ${res.status}`);
        }
        const json = (await res.json()) as Payload;
        if (live) setData(json);
      } catch (e) {
        if (live) setError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      live = false;
    };
  }, []);

  const view = useMemo(() => {
    if (!data) return null;
    const byId = new Map(data.rows.map((r) => [r.sleeper_id, r]));
    let filtered: Row[];
    if (watchedOnly) {
      // every watched id stays visible: owned, out of the pool, or absent from the census (unresolved)
      const base: Row[] = [...watched.keys()].map(
        (id) =>
          byId.get(id) ??
          (unresolvedRow(
            id,
            watched.get(id) ?? {
              name: null,
              position: null,
              team: null,
              watched_at: null,
            },
          ) as Row),
      );
      // watched-only never status-filters: an owned row may carry a status outside the unowned classes
      filtered = filterAvailable(base, {
        query,
        positions,
        statuses: [...new Set(base.map((r) => r.availability_class))],
      }) as Row[];
    } else {
      filtered = filterAvailable(
        data.rows.filter((r) => !r.owned_now),
        { query, positions, statuses, missingOnly },
      ) as Row[];
    }
    const sorted = sortAvailable(filtered, basis);
    const withForecast = filtered.filter(hasForecast).length;
    return {
      filtered,
      sorted,
      withForecast,
      withoutForecast: filtered.length - withForecast,
    };
  }, [data, query, positions, statuses, basis, watchedOnly, missingOnly, watched]);

  if (error) {
    return (
      <section className="dg-avail" aria-label="Available players section">
        <p className="dg-research__empty">
          No available-player catalog to show: {error}
        </p>
      </section>
    );
  }
  if (!data || !view) {
    return (
      <section className="dg-avail" aria-label="Available players section">
        <p className="dg-research__empty">Loading available players…</p>
      </section>
    );
  }
  const pool: Population = data.populations.default ?? {
    total: 0,
    with_forecast: 0,
    without_forecast: 0,
    by_class: {},
  };
  const searching = query.trim().length > 0;
  const statusEmpty = !watchedOnly && statuses.length === 0;
  const defaultStatuses =
    statuses.length === DEFAULT_STATUSES.length &&
    DEFAULT_STATUSES.every((s) => statuses.includes(s));
  const plainDefault =
    defaultStatuses && positions.length === 0 && !searching && !missingOnly;
  const n = view.filtered.length;
  const startingShown = view.filtered.filter((r) => r.starting_estimate).length;
  const startingWord =
    startingShown > 0
      ? ` (${startingShown} of them ${startingShown === 1 ? "a starting estimate" : "starting estimates"})`
      : "";
  let countLine: string;
  if (watchedOnly) {
    countLine = `${n} watched player${n === 1 ? "" : "s"} shown; owned, out-of-pool and unresolved ids stay listed with their status.`;
  } else if (plainDefault) {
    countLine = `${view.withForecast} of ${pool.total} in the default pool shown with a forecast${startingWord}; ${view.withoutForecast} without.`;
  } else {
    countLine = `${view.withForecast} with a forecast${startingWord} and ${view.withoutForecast} without match the current filters (default pool ${pool.total}: ${pool.with_forecast} with a forecast, ${pool.without_forecast} without).`;
  }
  if (view.sorted.missing.length !== view.withoutForecast) {
    countLine += ` ${view.sorted.missing.length} listed apart with no value for this ordering.`;
  }
  const tiedIds = new Map(
    view.sorted.ranked.map((x) => [x.row.sleeper_id, x.tied_with]),
  );

  return (
    <section className="dg-avail" aria-label="Available players section">
      <p className="dg-research__lede">
        Players nobody in your league owned in the dated snapshot, with the model's
        projected points for 2026 and for 2027–2030 summed. The watchlist is your own
        shortlist, saved in this browser.
      </p>
      <p className="dg-avail__dates">
        Ownership as of {data.freshness.ownership_as_of ?? "—"}; NFL status as of{" "}
        {data.freshness.nfl_status_as_of ?? "—"}. Both may have changed since.
      </p>
      {storageNotice && <p className="dg-avail__notice">{storageNotice}</p>}

      <div className="dg-avail__controls">
        <div className="dg-research__search">
          <label className="dg-research__search-label" htmlFor="dg-avail-search">
            Find an available player
          </label>
          <input
            id="dg-avail-search"
            className="dg-research__search-input"
            type="search"
            value={query}
            placeholder="Name, team or position"
            autoComplete="off"
            onChange={(e) => setQuery(e.target.value)}
          />
          {searching && (
            <button
              type="button"
              className="dg-research__why"
              aria-label="Clear the available-player search"
              onClick={() => setQuery("")}
            >
              Clear
            </button>
          )}
        </div>
        <fieldset className="dg-avail__group">
          <legend>Position</legend>
          {POSITIONS.map((p) => (
            <label key={p} className="dg-avail__check">
              <input
                type="checkbox"
                checked={positions.includes(p)}
                onChange={(e) =>
                  setPositions((cur) =>
                    e.target.checked ? [...cur, p] : cur.filter((x) => x !== p),
                  )
                }
              />{" "}
              {p}
            </label>
          ))}
        </fieldset>
        <fieldset className="dg-avail__group">
          <legend>NFL status (dated census)</legend>
          {ALL_STATUSES.map((s) => (
            <label key={s} className="dg-avail__check">
              <input
                type="checkbox"
                disabled={watchedOnly}
                checked={statuses.includes(s)}
                onChange={(e) =>
                  setStatuses((cur) =>
                    e.target.checked ? [...cur, s] : cur.filter((x) => x !== s),
                  )
                }
              />{" "}
              {STATUS_WORDS[s]}
            </label>
          ))}
          {watchedOnly && (
            <p className="dg-avail__ignored">
              NFL status and missing-forecast filters are ignored while Watched only is
              on; every watched player is listed with his current status. Search and
              position still apply.
            </p>
          )}
        </fieldset>
        <fieldset className="dg-avail__group">
          <legend>Show and order</legend>
          <label className="dg-avail__check">
            <input
              type="checkbox"
              checked={watchedOnly}
              onChange={(e) => setWatchedOnly(e.target.checked)}
            />{" "}
            Watched only
          </label>
          <label className="dg-avail__check">
            <input
              type="checkbox"
              disabled={watchedOnly}
              checked={missingOnly}
              onChange={(e) => setMissingOnly(e.target.checked)}
            />{" "}
            Missing forecast only
          </label>
          <label className="dg-avail__check dg-avail__sort" htmlFor="dg-avail-sort">
            Sort by{" "}
            <select
              id="dg-avail-sort"
              value={basis}
              onChange={(e) => setBasis(e.target.value as SortBasis)}
            >
              {(Object.keys(BASIS_LABELS) as SortBasis[]).map((b) => (
                <option key={b} value={b}>
                  {BASIS_LABELS[b]}
                </option>
              ))}
            </select>
          </label>
        </fieldset>
      </div>
      <p className="dg-research__search-hint" role="status">
        {statusEmpty
          ? "No NFL status is selected; tick at least one status to list players."
          : searching && n === 0
            ? `No available player matches "${query.trim()}" with the current filters.`
            : countLine}{" "}
        Sorted by {view.sorted.basis_label}; raw points are not cross-position dynasty
        value and no overall rank is claimed.
      </p>

      {!statusEmpty && view.sorted.ranked.length > 0 && (
        <TableScroll label="Available players">
          <table className="dg-research__table">
            <thead>
              <tr>
                <th scope="col">Player</th>
                {COLUMNS.map((c) => (
                  <th
                    key={c.basis}
                    scope="col"
                    aria-sort={c.basis === basis ? "descending" : undefined}
                  >
                    {c.heading}
                  </th>
                ))}
                <th scope="col">
                  {onCompare ? "Watch / Compare / Why" : "Watch / Why"}
                </th>
              </tr>
            </thead>
            <tbody>
              {view.sorted.ranked.map((x) => (
                <ValueRow
                  key={x.row.sleeper_id}
                  r={x.row as Row}
                  basis={basis}
                  tied={tiedIds.get(x.row.sleeper_id) ?? []}
                  watched={watched.has(x.row.sleeper_id)}
                  onWatch={toggleWatch}
                  onCompare={onCompare}
                  notes={data.notes}
                  evidence={data.starting_estimates?.evidence ?? null}
                />
              ))}
            </tbody>
          </table>
        </TableScroll>
      )}
      {!statusEmpty && view.sorted.missing.length > 0 && (
        <TableScroll
          label={
            basis === "name"
              ? "Players without a forecast"
              : "No value for this ordering"
          }
        >
          <table className="dg-research__table">
            <thead>
              <tr>
                <th scope="col">Player</th>
                <th scope="col">
                  {basis === "name"
                    ? "Why no forecast"
                    : `Why no value for ${view.sorted.basis_label}`}
                </th>
                <th scope="col">2026 projected points</th>
                <th scope="col">2027–2030 projected points</th>
                <th scope="col">
                  {onCompare ? "Watch / Compare / Why" : "Watch / Why"}
                </th>
              </tr>
            </thead>
            <tbody>
              {view.sorted.missing.map((m) => (
                <NoValueRow
                  key={m.row.sleeper_id}
                  r={m.row as Row}
                  reason={m.reason}
                  watched={watched.has(m.row.sleeper_id)}
                  onWatch={toggleWatch}
                  onCompare={onCompare}
                  notes={data.notes}
                  evidence={data.starting_estimates?.evidence ?? null}
                />
              ))}
            </tbody>
          </table>
        </TableScroll>
      )}

      <details className="dg-research__details">
        <summary>What these numbers are, who is counted, and what is not shown</summary>
        <ul className="dg-research__facts">
          <li>{data.freshness.caveat}</li>
          <li>{data.notes.ownership}</li>
          <li>{data.notes.now}</li>
          <li>{data.notes.future}</li>
          <li>{data.notes.appearance}</li>
          <li>{data.notes.sorting}</li>
          <li>{data.notes.watchlist}</li>
          {data.notes.starting_estimate && <li>{data.notes.starting_estimate}</li>}
          {(data.starting_estimates?.count ?? 0) > 0 && (
            <li>
              Starting estimates: {data.starting_estimates?.count} players from the
              root-accepted DG-165 cold-start sidecar{" "}
              {data.starting_estimates?.source?.run_dir ?? ""} (schema{" "}
              {data.starting_estimates?.source?.schema_version ?? "—"}); year classes
              are the producer's own selection; none carries an impact number.
            </li>
          )}
          <li>{data.forecast_note}</li>
          <li>{data.populations_note}</li>
          {Object.entries(data.populations).map(([name, p]) =>
            name === "owned" ? (
              <li key={name}>
                {p.total} owned identities carried for watch-status tracking only; their
                forecasts are on the research board.
              </li>
            ) : (
              <li key={name}>
                {name === "default"
                  ? "Default pool (verified active, practice squad, injured reserve)"
                  : (STATUS_WORDS[name] ?? name)}
                : {p.total} players, {p.with_forecast} with a forecast,{" "}
                {p.without_forecast} without
                {name === "default"
                  ? ` (${Object.entries(p.by_class)
                      .map(([c, k]) => `${STATUS_WORDS[c] ?? c} ${k}`)
                      .join(", ")})`
                  : ""}
                {p.incomplete_path
                  ? `; ${p.incomplete_path} with an incomplete season path`
                  : ""}
                .
              </li>
            ),
          )}
          <li>
            Disclosures, counts only and never pickup candidates here:{" "}
            {data.disclosures.uncovered_sleeper_ids ?? 0} Sleeper ids with no verified
            join to the captured roster; {data.disclosures.unmatched_nfl_records ?? 0}{" "}
            NFL records with no Sleeper identity;{" "}
            {data.disclosures.contested_nfl_records ?? 0} contested identity record(s);
            archive scope (Sleeper-eligible ids incl. inactive and retired) without a
            forecast:{" "}
            {Object.entries(data.disclosures.archive_unforecast_by_position ?? {})
              .map(([p, k]) => `${p} ${k}`)
              .join(" · ") || "—"}
            .
          </li>
          <li>
            Not weekly start advice, not a breakout probability, not cross-position
            dynasty value, and no pickup, FAAB, drop or lineup recommendation.
          </li>
          <li>
            Catalog run {data.source.catalog_run} from research run{" "}
            {data.source.report_run}
            {data.source.pinned ? " (pinned)" : ""}; census{" "}
            {data.source.census_run_id ?? "—"}.
          </li>
        </ul>
      </details>
    </section>
  );
}
