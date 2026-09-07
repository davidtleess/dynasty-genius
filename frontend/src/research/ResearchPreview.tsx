// DG-178 — a LOCAL, READ-ONLY research preview of the candidate board.
//
// URL-only surface (?surface=research-preview): no rail button, no palette command,
// exactly like the asset-primitive capture page. It reads /api/research/preview, which
// serves a local run report from this checkout's runs/ directory — never the live
// valuation artifact — and the page says so in its first line.
//
// What the number is: season points above the reference player at the position (the
// best player with a forecast whom nobody in the league owns), season-long replace or
// retain, summed over the seasons a view shows (two or five). It is a research estimate
// of N-year impact, not complete dynasty value and not drop or trade advice; the header
// says so in those words. File identity ("source check") and historical evaluation are
// stated as two separate facts; producer ids and hashes live only inside a row's "Why".
import { useEffect, useState } from "react";
import { PlayerIdentity } from "../ui/PlayerIdentity";
import { TableScroll } from "../ui/TableScroll";
import { AvailablePlayers, useWatchlist } from "./AvailablePlayers";
import type { AvailableRow } from "./availableHelpers";
import "./ResearchPreview.css";
import {
  type ComparisonSelection,
  EMPTY_SELECTION,
  RosterComparison,
} from "./RosterComparison";
import {
  filterLeague,
  formatMargin,
  formatPoints,
  marginLabel,
} from "./researchHelpers";

type Season = {
  season: number;
  expected_margin: number | null;
  action: string | null;
  advantage: number | null;
  player_expected_points?: number | null;
  reference_expected_points?: number | null;
};
type OtherView = {
  view: string;
  label: string;
  seasons_word: string;
  value: number | null;
};
type PreviewPlayer = {
  player_id: string;
  sleeper_id: string | null;
  name: string;
  position: string;
  team: string | null;
  age: number | null;
  value: number | null;
  readiness: string;
  status_sentence: string;
  raw_reason: string | null;
  producer: string | null;
  estimate_class: string | null;
  evidence_verified: boolean;
  served_value: number | null;
  served_value_label?: string;
  other_view?: OtherView | null;
  reference_player: string | null;
  reference_expected_points: number | null;
  seasons: Season[];
  rostered_by: number | null;
  on_davids_roster: boolean;
};
type Basis = {
  label: string;
  horizons_summed: number | null;
  seasons: number[];
  estimand: string;
  is_complete_dynasty_value: boolean;
  scoring_window: string;
  evidence_framing?: string;
  advice_note?: string;
  outcome_artifact?: {
    scoring_preset: string | null;
    research_qualified: boolean;
    coverage_status: string | null;
    qualification_sentence: string;
    exact_scoring_gaps: string[];
    admitted_seasons: number[] | null;
    last_complete_season: number | null;
  } | null;
};
type SeasonEvaluation = { status: string; summary: string };
type Producer = {
  name: string;
  label?: string;
  seasons: number;
  evidence_verified: boolean;
  evidence_reason: string | null;
  identity?: { verified: boolean; reason: string | null; meaning: string };
  historical_evaluation?: {
    available: boolean;
    by_season: Record<string, SeasonEvaluation>;
  };
};
type Reference = Record<
  string,
  {
    player: string | null;
    expected_points_by_season: (number | null)[];
    pool_complete: boolean | null;
    note: string | null;
    scope?: string;
    unforecast_eligible?: number | null;
    census_complete?: boolean | null;
    nfl_status?: string | null;
    sleeper_status?: string | null;
    nfl_attachment?: {
      status: string;
      basis: string;
      nfl_team?: string | null;
      note: string;
    } | null;
    horizon_note?: string | null;
    sensitivity_note?: string | null;
  }
>;
type Coverage = {
  sentences: string[];
  census_run_id?: string | null;
  archive_note?: string;
};
export type PreviewView = {
  key: string;
  basis: Basis;
  producers: Producer[];
  support_sentence?: string;
  evidence_sentences: string[];
  assembled_grading_sentences?: string[];
  reference: Reference;
  coverage?: Coverage | null;
  cross_view_note?: string | null;
  readiness_counts: Record<string, number>;
  roster: PreviewPlayer[];
  league: PreviewPlayer[];
  top: PreviewPlayer[];
};
export type PreviewPayload = {
  source: {
    kind: string;
    run: string;
    pinned?: boolean;
    forecast_date: string;
    artifact_captured_at: string | null;
    snapshot: string | null;
    note: string;
  };
  basis: Basis;
  producers: Producer[];
  reference: Reference;
  readiness_counts: Record<string, number>;
  roster: PreviewPlayer[];
  league: PreviewPlayer[];
  top: PreviewPlayer[];
  views?: PreviewView[];
  composition?: {
    rule: string;
    consistency: { players_checked: number; violations: number; rule: string } | null;
  };
  model_comparisons?: (PreviewView & { label?: string; kind?: string })[];
};

function pts(v: number | null | undefined): string {
  return v == null ? "—" : Math.round(v).toString();
}
const WORDS: Record<number, string> = {
  1: "one",
  2: "two",
  3: "three",
  4: "four",
  5: "five",
  6: "six",
};
function seasonsWord(n: number): string {
  return WORDS[n] ?? String(n);
}

// The chip is football-readable; the audit detail lives behind "Why".
function readinessWord(r: string): string {
  switch (r) {
    case "comparable":
      return "Research estimate";
    case "unverified":
      return "Inspection only";
    case "incomplete":
      return "Incomplete";
    case "none":
      return "No number";
    default:
      return r;
  }
}

// Producer ids are provenance, not copy: name each source by what it forecasts.
function producerWord(name: string | null | undefined, seasons?: number): string {
  const n = (name ?? "").toLowerCase();
  if (n.includes("rookie") || n.includes("dg165")) return "rookie forecast";
  if (n.includes("basic") || (seasons ?? 0) >= 5)
    return "veteran forecast (long history)";
  return "veteran forecast";
}

function PlayerRow({
  p,
  seasons,
  reference,
}: {
  p: PreviewPlayer;
  seasons: number[];
  reference: Reference;
}) {
  const [open, setOpen] = useState(false);
  const bySeason = new Map(p.seasons.map((s) => [s.season, s]));
  const ref = reference[p.position];
  return (
    <>
      <tr className="dg-research__row" data-readiness={p.readiness}>
        <td>
          <PlayerIdentity
            name={p.name}
            position={p.position}
            team={p.team ?? ""}
            imageStatus="missing"
          />
          {p.age != null && <span className="dg-research__age">age {p.age}</span>}
          {!p.on_davids_roster && p.rostered_by != null && (
            <span className="dg-research__owner">rostered elsewhere</span>
          )}
        </td>
        <td>
          <span className="dg-research__focal">
            {p.value == null ? "—" : pts(p.value)}
          </span>
        </td>
        {seasons.map((yr) => {
          const s = bySeason.get(yr);
          return (
            <td key={yr} className="dg-research__season">
              {s ? (
                <span className="dg-research__margin" data-action={s.action ?? ""}>
                  {formatMargin(s.expected_margin)}{" "}
                  <small>{marginLabel(s.expected_margin)}</small>
                </span>
              ) : (
                "—"
              )}
            </td>
          );
        })}
        <td className="dg-research__status">
          <span className="dg-research__chip" data-readiness={p.readiness}>
            {readinessWord(p.readiness)}
          </span>
          <button
            type="button"
            className="dg-research__why"
            aria-expanded={open}
            onClick={() => setOpen((o) => !o)}
          >
            {open ? "Hide" : "Why"}
          </button>
        </td>
      </tr>
      {open && (
        <tr className="dg-research__detail">
          <td colSpan={3 + seasons.length}>
            <p>{p.status_sentence}</p>
            {p.seasons.some((s) => s.player_expected_points != null) && (
              <p>
                Season by season, his expected points vs the reference's:{" "}
                {p.seasons
                  .map((s) =>
                    s.player_expected_points != null &&
                    s.reference_expected_points != null
                      ? `${s.season}: ${formatPoints(s.player_expected_points)} vs ${formatPoints(s.reference_expected_points)} (${formatMargin(s.expected_margin)})`
                      : `${s.season}: reference not stated`,
                  )
                  .join(" · ")}
                .
              </p>
            )}
            {p.reference_player && (
              <p>
                Measured against {p.reference_player}, the best {p.position} with a
                forecast whom nobody in the league owns
                {p.reference_expected_points != null
                  ? ` (expected ${pts(p.reference_expected_points)} points next season)`
                  : ""}
                .
                {ref?.nfl_attachment
                  ? ref.nfl_attachment.status === "unverified"
                    ? ` His NFL roster attachment is unverified in the dated census (${ref.nfl_attachment.note}).`
                    : ` The dated census lists him ${ref.nfl_attachment.status.replace(/_/g, " ")}${ref.nfl_attachment.nfl_team ? ` with ${ref.nfl_attachment.nfl_team}` : ""}.`
                  : ""}
                {ref?.horizon_note ? ` ${ref.horizon_note}` : ""}
              </p>
            )}
            {p.served_value != null && (
              <p>
                {p.served_value_label ??
                  "Existing app score (0-100; a different scale)"}
                : {p.served_value.toFixed(1)}.
              </p>
            )}
            {p.producer && (
              <p className="dg-research__provenance">
                Source: {producerWord(p.producer)} · source check{" "}
                {p.evidence_verified ? "passed" : "not passed"} (file identity, not
                validation)
                {p.raw_reason ? ` · ${p.raw_reason}` : ""}
                <br />
                <span className="dg-research__provenance-id">
                  {p.producer}
                  {p.estimate_class ? ` · ${p.estimate_class}` : ""}
                </span>
              </p>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

function PlayerTable({
  players,
  seasons,
  reference,
  label,
}: {
  players: PreviewPlayer[];
  seasons: number[];
  reference: Reference;
  label: string;
}) {
  return (
    <TableScroll label={label}>
      <table className="dg-research__table">
        <thead>
          <tr>
            <th scope="col">Player</th>
            <th scope="col">{seasons.length}-year impact</th>
            {seasons.map((yr) => (
              <th scope="col" key={yr}>
                {yr} vs. reference
              </th>
            ))}
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {players.map((p) => (
            <PlayerRow
              key={p.player_id}
              p={p}
              seasons={seasons}
              reference={reference}
            />
          ))}
        </tbody>
      </table>
    </TableScroll>
  );
}

function viewFromLegacy(data: PreviewPayload): PreviewView {
  return {
    key: "h2",
    basis: data.basis,
    producers: data.producers,
    evidence_sentences: [],
    reference: data.reference,
    readiness_counts: data.readiness_counts,
    roster: data.roster,
    league: data.league,
    top: data.top,
  };
}

type Tab = "board" | "available" | "compare";
function tabFromUrl(): Tab {
  const t = new URLSearchParams(window.location.search).get("tab");
  return t === "available" || t === "compare" ? t : "board";
}

export function ResearchPreview() {
  const [data, setData] = useState<PreviewPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [viewKey, setViewKey] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  // Three views of the same accepted run: the research board (unchanged), the available
  // players catalog built from it, and (DG-181) the roster-spot comparison. ?tab=available and
  // ?tab=compare open the second and third directly. The watchlist and the comparison choices
  // are owned here so both survive switching tabs; neither is persisted by this page.
  const watchlist = useWatchlist();
  const [tab, setTab] = useState<Tab>(() => tabFromUrl());
  const [comparison, setComparison] = useState<ComparisonSelection>(EMPTY_SELECTION);
  // A row's "Compare" chooses that available player and leaves the roster choice to David.
  const openComparison = (r: AvailableRow) => {
    setComparison((c) => ({ ...c, availableId: r.sleeper_id }));
    setTab("compare");
  };
  useEffect(() => {
    let live = true;
    (async () => {
      try {
        // ?run=<id> opens a candidate run for QA; without it the API serves the pinned
        // comparator (or the newest run when nothing is pinned).
        const run = new URLSearchParams(window.location.search).get("run");
        const res = await fetch(
          run
            ? `/api/research/preview?run=${encodeURIComponent(run)}`
            : "/api/research/preview",
        );
        if (!res.ok) {
          const body = (await res.json().catch(() => ({}))) as { detail?: string };
          throw new Error(body.detail ?? `HTTP ${res.status}`);
        }
        const json = (await res.json()) as PreviewPayload;
        if (live) setData(json);
      } catch (e) {
        if (live) setError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      live = false;
    };
  }, []);

  const tabs = (
    <div className="dg-research__views" role="tablist" aria-label="Research views">
      <button
        type="button"
        role="tab"
        aria-selected={tab === "board"}
        className="dg-research__view"
        onClick={() => setTab("board")}
      >
        Research board
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={tab === "available"}
        className="dg-research__view"
        onClick={() => setTab("available")}
      >
        Available players
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={tab === "compare"}
        className="dg-research__view"
        onClick={() => setTab("compare")}
      >
        Compare players
      </button>
    </div>
  );
  if (tab === "available") {
    return (
      <section className="dg-research" aria-label="Research preview">
        <header className="dg-research__header">
          <p className="dg-research__kicker">
            Research preview · available players · local catalog · not the live board
          </p>
          {tabs}
          <h1 className="dg-research__title">Available players</h1>
        </header>
        <AvailablePlayers watchlist={watchlist} onCompare={openComparison} />
      </section>
    );
  }
  if (tab === "compare") {
    return (
      <section className="dg-research" aria-label="Research preview">
        <header className="dg-research__header">
          <p className="dg-research__kicker">
            Research preview · compare players · local catalog · not the live board
          </p>
          {tabs}
          <h1 className="dg-research__title">Compare players</h1>
        </header>
        <RosterComparison selection={comparison} onSelect={setComparison} />
      </section>
    );
  }
  if (error) {
    return (
      <section className="dg-research" aria-label="Research preview">
        <p className="dg-research__empty">No research run to show: {error}</p>
      </section>
    );
  }
  if (!data) {
    return (
      <section className="dg-research" aria-label="Research preview">
        <p className="dg-research__empty">Loading the research preview…</p>
      </section>
    );
  }
  const views: PreviewView[] =
    data.views && data.views.length > 0 ? data.views : [viewFromLegacy(data)];
  const view: PreviewView =
    views.find((v) => v.key === viewKey) ?? views[0] ?? viewFromLegacy(data);
  const roster = [...view.roster].sort((a, b) => (b.value ?? -1) - (a.value ?? -1));
  const missing = roster.filter((p) => p.value == null);
  const matches = filterLeague(view.league, query);
  const searching = query.trim().length > 0;
  const counts = view.readiness_counts;
  const n = view.basis.seasons.length;
  const word = seasonsWord(n);
  const failedCheck = view.producers.filter((pr) => !pr.evidence_verified);
  const first = view.basis.seasons[0];
  const last = view.basis.seasons[n - 1];
  return (
    <section className="dg-research" aria-label="Research preview">
      <header className="dg-research__header">
        <p className="dg-research__kicker">
          Research preview · local run {data.source.run}
          {data.source.pinned ? " (accepted comparator)" : ""} · not the live board
        </p>
        {tabs}
        <h1 className="dg-research__title">{view.basis.label}</h1>
        {views.length > 1 && (
          <div
            className="dg-research__views"
            role="tablist"
            aria-label="Seasons summed"
          >
            {views.map((v) => (
              <button
                key={v.key}
                type="button"
                role="tab"
                aria-selected={v.key === view.key}
                className="dg-research__view"
                onClick={() => setViewKey(v.key)}
              >
                {v.basis.seasons.length}-year
              </button>
            ))}
          </div>
        )}
        <p className="dg-research__lede">
          A research estimate of the points a player adds over {first}–{last} against
          the best player at his position who has a forecast and whom nobody in the
          league owns. It is {word}-year impact, not complete dynasty value, and not
          drop or trade advice.
        </p>
        <p className="dg-research__support">
          {view.support_sentence ??
            "Historical support for these forecasts is stated per producer inside the details below."}
          {failedCheck.length > 0
            ? ` Source check not passed for the ${failedCheck
                .map((pr) => producerWord(pr.name, pr.seasons))
                .join(" and the ")}; those rows are shown for inspection only.`
            : ""}
        </p>
        <details className="dg-research__details">
          <summary>What this number is, and how much to trust it</summary>
          <ul className="dg-research__facts">
            <li>{view.basis.scoring_window}</li>
            {view.basis.advice_note && <li>{view.basis.advice_note}</li>}
            {view.basis.outcome_artifact && (
              <li>
                {view.basis.outcome_artifact.qualification_sentence}
                {view.basis.outcome_artifact.exact_scoring_gaps.length > 0
                  ? ` Scoring components not attributed: ${view.basis.outcome_artifact.exact_scoring_gaps.join("; ")}.`
                  : ""}
              </li>
            )}
            {view.basis.evidence_framing && <li>{view.basis.evidence_framing}</li>}
            {view.producers.map((pr) => (
              <li key={pr.name}>
                {producerWord(pr.name, pr.seasons)}: source check{" "}
                {pr.evidence_verified ? "passed" : "not passed"} (file identity, not
                validation).
                {pr.historical_evaluation?.available
                  ? ` Historical evaluation: ${Object.entries(
                      pr.historical_evaluation.by_season,
                    )
                      .map(([j, c]) => `season ${j} ${c.summary}`)
                      .join("; ")}.`
                  : " No per-season historical evaluation on this file."}
              </li>
            ))}
            {(view.assembled_grading_sentences ?? []).length > 0 && (
              <li>
                <details className="dg-research__details">
                  <summary>How the assembled number graded on past seasons</summary>
                  <ul className="dg-research__facts">
                    {(view.assembled_grading_sentences ?? []).map((s) => (
                      <li key={s}>{s}</li>
                    ))}
                  </ul>
                </details>
              </li>
            )}
            {view.coverage?.sentences?.map((s) => (
              <li key={s}>{s}</li>
            ))}
            <li>
              Reference players today (best among players with a forecast):{" "}
              {Object.entries(view.reference)
                .map(
                  ([pos, r]) =>
                    `${pos} ${r.player ?? "—"} (${pts(r.expected_points_by_season[0])} pts` +
                    (r.nfl_attachment
                      ? r.nfl_attachment.status === "unverified"
                        ? ", NFL attachment unverified"
                        : `, ${r.nfl_attachment.status.replace(/_/g, " ")}`
                      : "") +
                    ")",
                )
                .join(" · ")}
              . Unowned listed players without a forecast could change a reference; see
              the coverage lines above.
              {Object.values(view.reference)[0]?.horizon_note
                ? ` ${Object.values(view.reference)[0]?.horizon_note}`
                : ""}
            </li>
            {Object.values(view.reference).some((r) => r.sensitivity_note) && (
              <li>
                <details className="dg-research__details">
                  <summary>
                    How much the reference depends on one player (logged, not changed)
                  </summary>
                  <ul className="dg-research__facts">
                    {Object.entries(view.reference)
                      .filter(([, r]) => r.sensitivity_note)
                      .map(([pos, r]) => (
                        <li key={pos}>{r.sensitivity_note}</li>
                      ))}
                  </ul>
                </details>
              </li>
            )}
            {data.composition && (
              <li>
                {data.composition.rule}
                {data.composition.consistency
                  ? ` Checked on ${data.composition.consistency.players_checked} players, ${data.composition.consistency.violations} violations.`
                  : ""}
              </li>
            )}
            {(data.model_comparisons ?? []).map((cmp) => (
              <li key={cmp.key}>
                Model comparison, research only: {cmp.label ?? cmp.key}. Your roster on
                that model:{" "}
                {[...cmp.roster]
                  .filter((p) => p.value != null)
                  .sort((a, b) => (b.value ?? 0) - (a.value ?? 0))
                  .slice(0, 8)
                  .map((p) => `${p.name} ${pts(p.value)}`)
                  .join(" · ")}
                . {cmp.support_sentence ?? ""}
              </li>
            ))}
            {view.cross_view_note && <li>{view.cross_view_note}</li>}
            <li>
              Research estimates {counts.comparable ?? 0} · inspection only{" "}
              {counts.unverified ?? 0} · no number {counts.none ?? 0} across the
              league's skill players.
            </li>
          </ul>
        </details>
      </header>

      <h2 className="dg-research__heading">Your roster</h2>
      <PlayerTable
        players={roster}
        seasons={view.basis.seasons}
        reference={view.reference}
        label="Your roster on the research board"
      />

      <h2 className="dg-research__heading" id="dg-research-league-heading">
        Find any league player
      </h2>
      <div className="dg-research__search">
        <label className="dg-research__search-label" htmlFor="dg-research-search">
          Find a league player
        </label>
        <input
          id="dg-research-search"
          className="dg-research__search-input"
          type="search"
          value={query}
          placeholder={`Name, team or position — all ${view.league.length} league-owned players`}
          aria-controls="dg-research-search-results"
          aria-describedby="dg-research-search-hint"
          autoComplete="off"
          onChange={(e) => setQuery(e.target.value)}
        />
        {searching && (
          <button
            type="button"
            className="dg-research__why"
            aria-label="Clear the player search"
            onClick={() => setQuery("")}
          >
            Clear
          </button>
        )}
        <p
          id="dg-research-search-hint"
          className="dg-research__search-hint"
          role="status"
        >
          {searching
            ? matches.length === 0
              ? `No league-owned player matches "${query.trim()}".`
              : `${matches.length} of ${view.league.length} league-owned players match; ordered by ${word}-year impact.`
            : `Searches the ${view.league.length} league-owned players on this board, including everyone outside the leaders below.`}
        </p>
      </div>
      <div id="dg-research-search-results" className="dg-research__results">
        {searching && matches.length > 0 && (
          <PlayerTable
            players={matches}
            seasons={view.basis.seasons}
            reference={view.reference}
            label="League players matching your search"
          />
        )}
      </div>

      {missing.length > 0 && (
        <>
          <h2 className="dg-research__heading">Not shown with a number</h2>
          <ul className="dg-research__missing">
            {missing.map((p) => (
              <li key={p.player_id}>
                <strong>{p.name}</strong> ({p.position}): {p.status_sentence}
              </li>
            ))}
          </ul>
        </>
      )}

      <h2 className="dg-research__heading">League leaders on this board</h2>
      <PlayerTable
        players={view.top.slice(0, 40)}
        seasons={view.basis.seasons}
        reference={view.reference}
        label="League leaders on the research board"
      />
    </section>
  );
}
