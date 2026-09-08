"""The roster-spot comparison (DG-182, 2026-09-07; David: "yes" to the roster-spot design).

"How does this available player compare with the player whose roster spot I am considering?"
David picks both. This module composes the two ACCEPTED inputs the research tabs already serve —
the audit report (`runs/<id>/dg178_audit/report.json`) and the available-player catalog bound to
it — into one source-bound pair of player collections. It fits nothing, infers nothing, rounds
nothing, reads no producer file and touches no mutable store.

* `available` = the catalog's unowned rows (default pool plus the separate cut / retired / unknown
  populations, each labelled); points are the producers' own annual expected points exactly as the
  catalog carries them, with `now` / `future` recomputed the catalog's way and required to EQUAL
  the catalog's stored fields.
* `roster` = David's roster from the report's five-year view. The report carries signed margins
  above a reference, not points, so a season's points are the full-precision `expected_margin`
  PLUS that season's reference from the `union_replacement` producer's per-position series (the
  same series `research_preview._view` shows). The top-level `report.replacement` (a legacy
  served per-game scenario) and the clipped `advantage` are never used; the per-row
  `reference_expected_points` is season 1 only.
* Identity is the Sleeper id on both sides. Names are never compared (the sources spell two of
  David's players differently); position and roster membership must agree.

Anything that cannot be verified is refused with `ComparisonSourceError` — a catalog that does not
bind the served report bytes, a mismatched snapshot, a divergent window, a non-finite or duplicated
value, a stored total that disagrees with its own seasons, a shared or duplicated identity. Never
an older or partial payload. An ABSENT season is missing (null, and a null future total), which
is different from a malformed one (a duplicate, foreign or non-integral year, or a present value
that is not finite).
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Optional

UNION_MODEL = "union_replacement"
REFERENCE_QUANTITY = "expected_season_points_same_window"
PATH_LENGTH = 5
COLD_START = "cold_start_candidate"
BASELINE = "baseline_research_candidate"
UNSUPPORTED = "unsupported"
# The research target this comparison is defined on (the accepted report's board_target). A report on
# another target is refused — its numbers would mean something else and the scoring note would lie.
ACCEPTED_TARGET = {"scope": "REG", "scoring": "PPR_nflverse_default", "window": "championship_week17",
                   "quantity": "season_points", "clock": "per_season"}
PLAYER_KEYS = ("sleeper_id", "name", "position", "team", "population", "status", "now_points", "future_points",
               "seasons", "starting_estimate", "missing_reason", "evidence_note", "taxi_or_reserve")

_SCORING_WORDS = {"PPR_nflverse_default": "nflverse default full-PPR"}
_WINDOW_WORDS = {"championship_week17": "the championship window through NFL week 17"}


class ComparisonSourceError(ValueError):
    """The two accepted inputs cannot be composed into one truthful payload; the message says why."""


# --- small validators ---------------------------------------------------------------------------


def _finite(v: Any, what: str) -> Optional[float]:
    """A present number must be a finite float; None stays None (absent). Booleans and strings are
    not numbers here — JSON `NaN` / `Infinity` parse without complaint, so finiteness is checked."""
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ComparisonSourceError(f"{what} is {v!r}, not a number")
    x = float(v)
    if not math.isfinite(x):
        raise ComparisonSourceError(f"{what} is {v!r}, not finite")
    return x


def _year(v: Any, what: str, years: list[int]) -> int:
    if isinstance(v, bool) or not isinstance(v, int):
        raise ComparisonSourceError(f"{what} names season {v!r}, not an integral year")
    if v not in years:
        raise ComparisonSourceError(f"{what} names season {v}, outside the forecast window {years[0]}–{years[-1]}")
    return v


def _sid(row: dict, what: str) -> str:
    sid = row.get("sleeper_id")
    if sid is None or str(sid).strip() == "":
        raise ComparisonSourceError(f"{what} has no sleeper_id; identity is the Sleeper id on both sides")
    return str(sid)


def _total(points: dict[int, Optional[float]], years: list[int], who: str) -> Optional[float]:
    """The later years summed exactly once each, the catalog's own way (`sum` in year order), only
    when every one is present; otherwise None — never zero, never partial. An overflow is refused."""
    later = [points.get(y) for y in years[1:]]
    if any(v is None for v in later):
        return None
    total = float(sum(later))
    if not math.isfinite(total):
        raise ComparisonSourceError(f"{who}: the future total over {years[1]}–{years[-1]} is not finite")
    return total


def _missing_years_reason(points: dict[int, Optional[float]], years: list[int]) -> Optional[str]:
    missing = [y for y in years[1:] if points.get(y) is None]
    if not missing:
        return None
    return f"{', '.join(str(y) for y in missing)} forecast missing: future total undefined, not zero"


# --- binding the two sources --------------------------------------------------------------------


def _parse_report(report_bytes: bytes) -> dict:
    try:
        report = json.loads(report_bytes.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as e:
        raise ComparisonSourceError(f"the report bytes are not readable JSON: {e}") from e
    if not isinstance(report, dict):
        raise ComparisonSourceError("the report is not a JSON object")
    return report


def _bind(report: dict, catalog: dict, report_sha: str, report_run: str, catalog_run: str) -> None:
    if str(catalog.get("run")) != catalog_run:
        raise ComparisonSourceError(f"the catalog names run {catalog.get('run')!r}, not the requested catalog {catalog_run!r}")
    if str(report.get("run")) != report_run:
        raise ComparisonSourceError(f"the report names run {report.get('run')!r}, not the requested run {report_run!r}")
    if str(catalog.get("source_report_run")) != report_run:
        raise ComparisonSourceError(f"the catalog's source_report_run is {catalog.get('source_report_run')!r}, not the served run {report_run!r}")
    sources = catalog.get("sources") or {}
    bound = str(sources.get("report_sha256") or "").lower()
    if bound != report_sha:
        raise ComparisonSourceError(f"the catalog's report_sha256 ({bound[:12] or 'absent'}…) is not the sha256 of the served report bytes ({report_sha[:12]}…)")
    report_snapshot = str(((report.get("inputs") or {}).get("snapshot") or {}).get("sha256") or "").lower()
    catalog_snapshot = str(sources.get("snapshot_sha256") or "").lower()
    if not report_snapshot or not catalog_snapshot:
        raise ComparisonSourceError("the league snapshot sha256 is not stated on both sides; the two collections cannot be shown to describe one league snapshot")
    if report_snapshot != catalog_snapshot:
        raise ComparisonSourceError(f"the catalog binds league snapshot {catalog_snapshot[:12]}… while the report read {report_snapshot[:12]}…; not one snapshot")


def _accepted_target(report: dict, years: list[int]) -> None:
    target = report.get("board_target") or {}
    for key, want in ACCEPTED_TARGET.items():
        got = target.get(key)
        if got != want:
            raise ComparisonSourceError(f"the report's board_target {key} is {got!r}, not the accepted {want!r}; this comparison is defined on the accepted target only")
    date = str(report.get("forecast_date") or "")
    if not date[:4].isdigit() or int(date[:4]) != years[0]:
        raise ComparisonSourceError(f"the report's forecast_date {report.get('forecast_date')!r} does not open the catalog's window at {years[0]}")


def _five_year_board(report: dict, years: list[int]) -> dict:
    """The board whose seasons are the whole window, resolved through the report's own view map."""
    views = report.get("comparable_views")
    key = views.get(f"h{len(years)}") if isinstance(views, dict) else None
    board = report.get(key) if isinstance(key, str) else None
    if not isinstance(board, dict):
        raise ComparisonSourceError(f"the report's comparable_views names no h{len(years)} board ({views!r}); the five-year view cannot be resolved")
    summed = board.get("horizons_summed")
    if summed != len(years):
        raise ComparisonSourceError(f"board {key!r} sums {summed!r} horizons, not the {len(years)} of the window (horizons_summed)")
    return board


def _window(catalog: dict) -> list[int]:
    years = catalog.get("forecast_years")
    if (not isinstance(years, list) or len(years) != PATH_LENGTH
            or any(isinstance(y, bool) or not isinstance(y, int) for y in years)
            or any(b - a != 1 for a, b in zip(years, years[1:]))):
        raise ComparisonSourceError(f"the catalog's forecast_years {years!r} is not a {PATH_LENGTH}-year consecutive window")
    future = catalog.get("future_years")
    if future != years[1:]:
        raise ComparisonSourceError(f"the catalog's future_years {future!r} is not the window after {years[0]} ({years[1:]})")
    return list(years)


def _reference_series(board: dict, years: list[int]) -> dict[str, list[float]]:
    """Per position, the reference's expected SEASON POINTS for each season of the window, from the
    board's single union_replacement producer. Every entry must say it is season points on the same
    window, and the series must be exactly one entry per season of the window."""
    unions = [m for m in board.get("annual_producers") or [] if m.get("model_version") == UNION_MODEL]
    if len(unions) != 1:
        raise ComparisonSourceError(f"the board declares {len(unions)} {UNION_MODEL} producers, not exactly 1; the reference series is ambiguous or absent")
    out: dict[str, list[float]] = {}
    for pos, entries in (unions[0].get("replacement") or {}).items():
        entries = entries or []
        if len(entries) != len(years):
            raise ComparisonSourceError(f"{pos} reference series has {len(entries)} seasons, not the {len(years)} of the window")
        series = []
        for i, e in enumerate(entries):
            if str(e.get("rate_quantity")) != REFERENCE_QUANTITY:
                raise ComparisonSourceError(f"{pos} reference season {i + 1} has rate_quantity {e.get('rate_quantity')!r}, not {REFERENCE_QUANTITY!r}; refusing to add it to a season margin")
            v = _finite(e.get("rate_ppg"), f"{pos} reference season {i + 1} rate_ppg")
            if v is None:
                raise ComparisonSourceError(f"{pos} reference season {i + 1} is absent")
            series.append(v)
        out[pos] = series
    return out


# --- words ----------------------------------------------------------------------------------------


def _scoring_note(report: dict) -> str:
    target = report.get("board_target") or {}
    scoring = _SCORING_WORDS.get(str(target.get("scoring")), str(target.get("scoring") or "the research scoring"))
    window = _WINDOW_WORDS.get(str(target.get("window")), str(target.get("window") or "the research window"))
    exact = bool((report.get("outcome_artifact") or {}).get("league_scoring_exact"))
    tail = ("this matches your league's scoring" if exact
            else "this is not your league's exact scoring, so compare players on this shared basis rather than reading them as lineup points")
    return f"Points are expected season fantasy points under the research scoring ({scoring}, {window}); {tail}."


def _producer_word(name: Optional[str]) -> str:
    n = str(name or "")
    if "cold-start" in n or "cold_start" in n:
        return "the cold-start starting estimate"
    if "veteran annual" in n:
        return "the veteran annual forecast"
    if "rookie_capital" in n:
        return "the rookie draft-capital forecast"
    return n or "the selected producer"


def _starting_note(classes: dict[int, Optional[str]]) -> str:
    cold = [y for y, c in classes.items() if c == COLD_START]
    base = [y for y, c in classes.items() if c == BASELINE]
    parts = []
    if cold:
        parts.append(f"{', '.join(map(str, cold))} from the draft-capital cold-start candidate")
    if base:
        span = f"{base[0]}–{base[-1]}" if len(base) > 1 else str(base[0])
        parts.append(f"{span} from the position's historical baseline")
    return ("Starting estimate, not an accepted forecast: " + "; ".join(parts)
            + "; not conditioned on staying on a roster; not a breakout probability; no impact number.")


def _roster_missing_words(reason: Optional[str]) -> str:
    r = str(reason or "")
    if "not forecast by any annual producer" in r:
        stated = r.split("the producer's stated reason:", 1)[1].strip() if "the producer's stated reason:" in r else None
        return ("No forecast from the selected producers for this window"
                + (f" (stated reason: {stated})" if stated else "") + "; a missing forecast, not a zero.")
    if "unverified" in r or "could not be verified" in r:
        return "Shown without a number: the forecast's source files could not be verified against their declared identity."
    return f"No forecast on the research board: {r}" if r else "No forecast on the research board; a missing forecast, not a zero."


# --- the two collections ---------------------------------------------------------------------------


def _taxi_or_reserve_ids(report: dict, roster_ids: set[str]) -> Optional[set[str]]:
    """The Sleeper ids the report's saved-lineup scenario excluded as taxi or reserve — a factual
    label about the saved roster, not lineup eligibility and not a storage type. None when the
    report does not state the list (then the label is unknown, never False)."""
    lineup = report.get("davids_best_lineup_served_h0")
    if not isinstance(lineup, dict) or "excluded_taxi_or_reserve" not in lineup:
        return None
    listed = lineup.get("excluded_taxi_or_reserve")
    if not isinstance(listed, list):
        raise ComparisonSourceError(f"excluded_taxi_or_reserve is {listed!r}, not a list of Sleeper ids")
    ids = {str(x) for x in listed}
    foreign = sorted(ids - roster_ids)
    if foreign:
        raise ComparisonSourceError(f"excluded_taxi_or_reserve names Sleeper id(s) {', '.join(foreign)} that are not on David's roster view")
    return ids


def _available_player(row: dict, years: list[int]) -> dict[str, Any]:
    sid = _sid(row, "a catalog row")
    who = f"catalog row {sid} ({row.get('name')})"
    forecast = row.get("forecast")
    points: dict[int, Optional[float]] = {}
    if forecast:
        for s in forecast.get("seasons") or []:
            y = _year(s.get("season"), who, years)
            if y in points:
                raise ComparisonSourceError(f"{who}: season {y} is listed twice")
            points[y] = _finite(s.get("e_points"), f"{who} season {y} e_points")
    now = points.get(years[0])
    future = _total(points, years, who)
    stored_now = _finite(row.get("now_points"), f"{who} now_points")
    stored_future = _finite(row.get("future_points"), f"{who} future_points")
    if stored_now != now:
        raise ComparisonSourceError(f"{who}: stored now_points {stored_now!r} is not the {years[0]} expected points {now!r}")
    if stored_future != future:
        raise ComparisonSourceError(f"{who}: stored future_points {stored_future!r} is not the sum of the named future years {future!r}")
    starting = bool(row.get("starting_estimate"))
    declared = {}
    for k, v in (row.get("estimate_classes") or {}).items():
        try:
            declared[int(k)] = v
        except (TypeError, ValueError) as e:
            raise ComparisonSourceError(f"{who}: estimate_classes names season {k!r}") from e
    future_reason = str(row.get("future_reason") or "")
    classes: dict[int, Optional[str]] = {}
    for y in years:
        if y in points and points[y] is not None:
            classes[y] = declared.get(y) if starting else None
        else:
            classes[y] = UNSUPPORTED if f"{y} unsupported by the producer" in future_reason else None
    missing_reason = row.get("missing_reason") if forecast is None or now is None else None
    if missing_reason is None and future is None:
        missing_reason = row.get("future_reason") or _missing_years_reason(points, years)
    if missing_reason is None and now is None:
        missing_reason = f"{years[0]} forecast missing; a missing forecast, not a zero"
    if forecast is None:
        note = f"No accepted forecast: {row.get('missing_reason') or 'no forecast from the selected producers'}."
        if row.get("identity_conflict"):
            note += f" Identity: {row['identity_conflict']}."
    elif starting:
        note = _starting_note({y: c for y, c in classes.items() if points.get(y) is not None})
    else:
        note = (f"Accepted research forecast from {_producer_word(forecast.get('producer'))}"
                + (", recovered from the producer file by verified identity" if row.get("recovered") else "")
                + "; expected season points under the research scoring, not exact league scoring.")
    return {
        "sleeper_id": sid, "name": row.get("name"), "position": row.get("league_position"), "team": row.get("nfl_team"),
        "population": row.get("population"), "status": row.get("availability_class"),
        "now_points": now, "future_points": future,
        "seasons": [{"season": y, "points": points.get(y), "estimate_class": classes[y]} for y in years],
        "starting_estimate": starting, "missing_reason": missing_reason, "evidence_note": note,
        "taxi_or_reserve": None,
    }


def _roster_player(row: dict, owned: dict[str, dict], series: dict[str, list[float]], years: list[int],
                   rostered_by: Any, taxi_or_reserve: Optional[bool]) -> dict[str, Any]:
    sid = _sid(row, "a roster row")
    who = f"roster row {sid} ({row.get('name')})"
    if row.get("on_davids_roster") is not True:
        raise ComparisonSourceError(f"{who}: on_davids_roster is {row.get('on_davids_roster')!r} on the roster view")
    if row.get("rostered_by") != rostered_by:
        raise ComparisonSourceError(f"{who}: rostered_by {row.get('rostered_by')!r} differs from the roster's {rostered_by!r}")
    position = str(row.get("position") or "")
    status_row = owned.get(sid)
    if status_row is None:
        raise ComparisonSourceError(f"{who}: the catalog has no owned row for this Sleeper id; the two collections do not describe one roster")
    if str(status_row.get("league_position")) != position:
        raise ComparisonSourceError(f"{who}: position {position!r} on the board but {status_row.get('league_position')!r} in the catalog")
    if status_row.get("roster_id") != rostered_by:
        raise ComparisonSourceError(f"{who}: the catalog places him on roster {status_row.get('roster_id')!r}, the board on roster {rostered_by!r}")
    margins: dict[int, Optional[float]] = {}
    for s in row.get("seasons") or []:
        y = _year(s.get("season"), who, years)
        if y in margins:
            raise ComparisonSourceError(f"{who}: season {y} is listed twice")
        margins[y] = _finite(s.get("expected_margin"), f"{who} season {y} expected_margin")
    accepted = row.get("readiness") == "comparable" and row.get("evidence_verified") is True
    if margins and not accepted:
        # a number whose sources were not verified, or that is not comparable with the board target,
        # is withheld with its reason — never labelled an accepted forecast
        reason = row.get("reason") or (f"readiness {row.get('readiness')!r}" if row.get("readiness") != "comparable"
                                       else "the forecast's source files could not be verified against their declared identity")
        return {
            "sleeper_id": sid, "name": row.get("name"), "position": position, "team": status_row.get("nfl_team"),
            "population": status_row.get("population"), "status": status_row.get("availability_class"),
            "now_points": None, "future_points": None,
            "seasons": [{"season": y, "points": None, "estimate_class": None} for y in years],
            "starting_estimate": False,
            "missing_reason": _roster_missing_words(reason if "verified" in reason or "unverified" in reason else f"unverified: {reason}"
                                                    if row.get("evidence_verified") is not True else reason),
            "evidence_note": f"Not an accepted forecast: {reason}.",
            "taxi_or_reserve": taxi_or_reserve,
        }
    reference = series.get(position)
    if margins and reference is None:
        raise ComparisonSourceError(f"{who}: the board has no {position} reference series")
    points: dict[int, Optional[float]] = {}
    for i, y in enumerate(years):
        m = margins.get(y)
        points[y] = None if m is None else m + reference[i]
        if points[y] is not None and not math.isfinite(points[y]):
            raise ComparisonSourceError(f"{who}: season {y} points are not finite")
    now = points.get(years[0])
    future = _total(points, years, who)
    if not margins:
        missing_reason = _roster_missing_words(row.get("reason"))
        note = f"No accepted forecast on your research board ({row.get('reason') or 'no reason stated'})."
    else:
        missing_reason = _missing_years_reason(points, years) if future is None else None
        if now is None:
            missing_reason = f"{years[0]} forecast missing; a missing forecast, not a zero"
        ref_name = row.get("reference_player")
        note = (f"Accepted research forecast from {_producer_word(row.get('producer'))} on your research board; each season is the "
                f"board's signed margin plus that season's {ref_name or 'reference'} reference, at full precision; research scoring, "
                f"not exact league scoring.")
    return {
        "sleeper_id": sid, "name": row.get("name"), "position": position, "team": status_row.get("nfl_team"),
        "population": status_row.get("population"), "status": status_row.get("availability_class"),
        "now_points": now, "future_points": future,
        "seasons": [{"season": y, "points": points.get(y), "estimate_class": None} for y in years],
        "starting_estimate": False, "missing_reason": missing_reason, "evidence_note": note,
        "taxi_or_reserve": taxi_or_reserve,
    }


def build_comparison(report_bytes: bytes, catalog: dict, *, report_run: str, catalog_run: str) -> dict[str, Any]:
    """Compose the payload from the served report BYTES (hashed and parsed here, the same buffer) and
    the catalog document already verified against its companion record by the route's loader."""
    report = _parse_report(report_bytes)
    report_sha = hashlib.sha256(report_bytes).hexdigest()
    _bind(report, catalog, report_sha, report_run, catalog_run)
    years = _window(catalog)
    _accepted_target(report, years)
    board = _five_year_board(report, years)
    series = _reference_series(board, years)

    owned: dict[str, dict] = {}
    unowned: list[dict] = []
    seen: set[str] = set()
    for row in catalog.get("rows_detail") or []:
        sid = _sid(row, "a catalog row")
        if sid in seen:
            raise ComparisonSourceError(f"catalog row {sid} ({row.get('name')}) is a duplicate Sleeper id")
        seen.add(sid)
        if row.get("population") == "owned":
            if row.get("owned_now") is not True:
                raise ComparisonSourceError(f"catalog row {sid} ({row.get('name')}) is in population 'owned' with owned_now {row.get('owned_now')!r}")
            owned[sid] = row
        elif row.get("owned_now"):
            raise ComparisonSourceError(f"catalog row {sid} ({row.get('name')}) is flagged owned_now inside population {row.get('population')!r}")
        else:
            unowned.append(row)

    roster_rows = board.get("davids_roster") or []
    if not roster_rows:
        raise ComparisonSourceError("the board carries no roster rows for David; refusing to serve an empty roster as a fact")
    rostered_by = roster_rows[0].get("rostered_by")
    roster_ids: set[str] = set()
    for row in roster_rows:
        sid = _sid(row, "a roster row")
        if sid in roster_ids:
            raise ComparisonSourceError(f"roster row {sid} ({row.get('name')}) is a duplicate Sleeper id")
        roster_ids.add(sid)
    # full membership, both ways: the catalog's owned rows on David's roster id are exactly the board's roster
    catalog_roster = {sid for sid, row in owned.items() if row.get("roster_id") == rostered_by}
    if catalog_roster != roster_ids:
        only_board = sorted(roster_ids - catalog_roster)
        only_catalog = sorted(catalog_roster - roster_ids)
        raise ComparisonSourceError("the board's roster and the catalog's owned rows for roster "
                                    f"{rostered_by!r} disagree: on the board only {only_board or 'none'}, in the catalog only {only_catalog or 'none'}")
    parked = _taxi_or_reserve_ids(report, roster_ids)
    roster: list[dict] = []
    for row in roster_rows:
        sid = str(row.get("sleeper_id"))
        roster.append(_roster_player(row, owned, series, years, rostered_by, None if parked is None else sid in parked))

    available: list[dict] = []
    for row in unowned:
        sid = _sid(row, "a catalog row")
        if sid in roster_ids:
            raise ComparisonSourceError(f"Sleeper id {sid} ({row.get('name')}) is on David's roster and in the unowned population {row.get('population')!r}")
        available.append(_available_player(row, years))

    return {
        "source": {"report_run": report_run, "catalog_run": catalog_run, "report_sha256": report_sha,
                   "catalog_content_sha256": hashlib.sha256(json.dumps(catalog, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()).hexdigest(),
                   "ownership_as_of": catalog.get("ownership_as_of"), "nfl_status_as_of": catalog.get("nfl_status_as_of")},
        "forecast_years": years, "future_years": years[1:],
        "scoring_note": _scoring_note(report),
        "available": available, "roster": roster,
    }
