"""DG-178 — a LOCAL, READ-ONLY research preview of the candidate two-year board.

Reads the newest `runs/<id>/dg178_audit/report.json` under DG178_RUNS_ROOT (default: this
checkout's `runs/`), never the live valuation artifact, and says so in every payload. The
board it shows is a two-year impact comparison on the typed annual target: season points
above the actual available replacement, summed over the seasons both producers reach. It
is not complete dynasty value and the payload says that too. Reasons come back as
fantasy-language sentences with the raw reason kept beside them.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/research", tags=["research"])

_DEFAULT_RUNS = Path("runs")


def _runs_root() -> Path:
    return Path(os.environ.get("DG178_RUNS_ROOT") or _DEFAULT_RUNS)


def _latest_report(run: Optional[str]) -> tuple[str, dict, bool]:
    """The run to serve: ``?run=`` when given, else the run DG178_PREVIEW_RUN pins (the accepted
    comparator stays served while a new candidate is only reachable by its id), else the newest."""
    root = _runs_root()
    if not root.is_dir():
        raise HTTPException(status_code=404, detail="no research run found: the runs directory does not exist")
    pinned = os.environ.get("DG178_PREVIEW_RUN") or None
    wanted = run or pinned
    candidates = sorted(p for p in root.glob("*/dg178_audit/report.json") if wanted is None or p.parent.parent.name == wanted)
    if not candidates:
        raise HTTPException(status_code=404, detail=("no research run found under the runs directory" if wanted is None
                                                     else f"no research run named {wanted} under the runs directory"))
    path = candidates[-1]
    return path.parent.parent.name, json.loads(path.read_text()), (run is None and pinned is not None)


def _fmt1(v: float) -> str:
    return f"{v:.1f}"


def _zero_or_tie_sentence(row: dict, seasons_word: str) -> Optional[str]:
    """A 0.0 value is an ACTUAL forecast that does not exceed the selected reference in the
    seasons shown — never missing data, zero points or zero trade value. An exact tie in every
    season is named as such; a near-zero value quotes its signed one-decimal margins."""
    seasons = [s for s in (row.get("seasons") or []) if s.get("expected_margin") is not None]
    if not seasons or row.get("value") is None:
        return None
    pos = row.get("position") or "player"
    n = len(seasons)
    n_word = {1: "the one season", 2: "both seasons", 3: "all three seasons", 4: "all four seasons", 5: "all five seasons"}.get(n, f"all {n} seasons")
    if all(float(s["expected_margin"]) == 0.0 for s in seasons):
        return (f"Equal to the reference in {n_word} shown: his forecast matches the next available {pos} exactly, so the "
                f"impact is 0 by definition — not missing data, not zero points, not zero trade value.")
    if float(row["value"]) == 0.0:
        pairs = []
        for s in seasons:
            ref = s.get("reference_expected_points")
            his = s.get("player_expected_points")
            pairs.append(f"{s['season']}: {_fmt1(his)} vs {_fmt1(ref)}" if his is not None and ref is not None
                         else f"{s['season']}: {_fmt1(float(s['expected_margin']))} below")
        return (f"Zero impact on this board: an actual forecast that does not exceed the next available {pos} in "
                f"{n_word} shown ({'; '.join(pairs)}); the number is points above that reference, so it is 0 — "
                f"not missing data, not zero points, not zero trade value.")
    if all(abs(float(s["expected_margin"])) < 1.0 for s in seasons):
        margins = "; ".join(f"{s['season']}: {float(s['expected_margin']):+.1f}" for s in seasons)
        return (f"Within a point of the reference in {n_word} shown ({margins}): a research estimate of "
                f"{seasons_word}-year impact that is nearly level with the next available {pos}; not drop or trade advice.")
    return None


def _sentence(row: dict, *, seasons_word: str = "two", other_view: Optional[dict] = None) -> str:
    """Fantasy language for a row's status. `other_view` names another board view that DOES
    carry a number for this player, so a missing reason describes THIS view's model coverage
    instead of claiming no producer has a number."""
    reason = (row.get("reason") or "").lower()
    readiness = row.get("readiness")
    if readiness == "comparable":
        special = _zero_or_tie_sentence(row, seasons_word)
        if special:
            return special
        return f"Research estimate of {seasons_word}-year impact on the shared target; not drop or trade advice."
    if readiness == "unverified" or "unverified" in reason:
        return ("Shown for inspection only: this number's source files could not be checked against their "
                "declared identity (file hashes and model arm), so it is not counted as a research estimate.")
    if "position_outside_modelled_set" in reason and row.get("placement_source") == "sleeper_fantasy_positions":
        fps = "|".join(row.get("fantasy_positions") or [])
        src = reason.split("source position", 1)[-1].strip(" ()") if "source position" in reason else None
        return (f"Sleeper allows {row.get('position')} ({fps}), but the veteran model currently excludes his two-position "
                f"history{f' (its source position is {src.upper()})' if src else ''}; no forecast yet.")
    if "position_outside_modelled_set" in reason:
        return "No forecast yet: the veteran model excludes his position history; his league position is not verified."
    if "not forecast by any annual producer" in reason:
        stated = None
        if "the producer's stated reason:" in reason:
            stated = (row.get("reason") or "").split("the producer's stated reason:", 1)[1].strip()
        if other_view:
            return (f"No {seasons_word}-year number from the selected producers for this window"
                    + (f" (stated reason: {stated})" if stated else "; no reason stated")
                    + f". The {other_view['seasons_word']}-year view does carry him; see the {other_view['label']} view.")
        return ("No forecast from the selected producers for this window"
                + (f": {stated}." if stated else "; no reason stated by any producer. It is a missing forecast, not a zero."))
    if "identity" in reason and "unresolved" in reason:
        return "No forecast: his identity could not be matched across sources."
    if "replacement pool incomplete" in reason:
        return "No comparable number: the pool of available players at his position is not fully forecast."
    if "no replacement bar" in reason:
        return "No comparable number: no replacement could be set at his position."
    if "reaches" in reason and "board sums" in reason:
        return "No comparable number: the producer does not reach every season the board sums."
    return row.get("reason") or "No number."


SERVED_VALUE_LABEL = "Existing app score (0-100; a different scale, not comparable with the research estimate)"


def _seasons_with_points(row: dict, reference_series: Optional[list]) -> list[dict]:
    """Each season with the player's and the reference's expected points, derived from the
    full-precision signed margin plus the reference series only when both are finite; a season
    whose reference is absent keeps the fields absent — never derived from a rounded value."""
    out = []
    for i, s in enumerate(row.get("seasons") or []):
        s2 = dict(s)
        margin = s.get("expected_margin")
        ref = reference_series[i] if reference_series and i < len(reference_series) else None
        if isinstance(margin, (int, float)) and isinstance(ref, (int, float)) and math.isfinite(margin) and math.isfinite(ref):
            s2["reference_expected_points"] = float(ref)
            s2["player_expected_points"] = float(margin) + float(ref)
        else:
            s2["reference_expected_points"] = None
            s2["player_expected_points"] = None
        out.append(s2)
    return out


def _player(row: dict, *, seasons_word: str = "two", other_view: Optional[dict] = None,
            reference_series: Optional[list] = None) -> dict[str, Any]:
    row = dict(row, seasons=_seasons_with_points(row, reference_series))
    return {
        "player_id": row.get("player_id"), "sleeper_id": row.get("sleeper_id"), "name": row.get("name"),
        "position": row.get("position"), "team": row.get("team"), "age": row.get("age"),
        "value": row.get("value"), "readiness": row.get("readiness"),
        "status_sentence": _sentence(row, seasons_word=seasons_word, other_view=other_view), "raw_reason": row.get("reason"),
        "producer": row.get("producer"), "estimate_class": row.get("estimate_class"),
        "evidence_verified": bool(row.get("evidence_verified")),
        "served_value": row.get("served_dvs"), "served_value_label": SERVED_VALUE_LABEL,
        "other_view": other_view,
        "fantasy_positions": row.get("fantasy_positions"), "placement_source": row.get("placement_source"),
        "nfl_status": row.get("nfl_status"),
        "reference_player": row.get("reference_player"),
        "reference_expected_points": row.get("reference_expected_points"),
        "seasons": row.get("seasons") or [],
        "rostered_by": row.get("rostered_by"), "on_davids_roster": bool(row.get("on_davids_roster")),
    }


_WORDS = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six"}


def _coverage(report: dict, census: dict) -> Optional[dict]:
    """League-owned coverage first, then the dated listed-player coverage by verified NFL
    status, then the archive scope — three populations, never one percentage."""
    if not census:
        return None
    cov = dict(census.get("coverage") or {})
    archive = {pos: int((v or {}).get("count") or 0) for pos, v in (report.get("unforecast_eligible_census") or {}).items()}
    lo = cov.get("league_owned") or {}
    sentences = [f"Your league owns {lo.get('total', 0)} players; all {lo.get('in_census', 0)} are in the dated census"
                 + (f" ({lo.get('with_forecast', 0)} with a research estimate, {lo.get('without_forecast', 0)} without)"
                    if lo else "") + "."]
    if lo.get("in_census", 0) != lo.get("total", 0):
        sentences[0] = (f"Your league owns {lo.get('total', 0)} players; {lo.get('in_census', 0)} are in the dated census "
                        f"({lo.get('with_forecast', 0)} with a research estimate, {lo.get('without_forecast', 0)} without).")
    for pos, classes in sorted((cov.get("listed_unowned") or {}).get("by_position", {}).items()):
        total = sum(c["with_forecast"] + c["without_forecast"] for c in classes.values())
        with_f = sum(c["with_forecast"] for c in classes.values())
        without = {cls: c["without_forecast"] for cls, c in classes.items() if c["without_forecast"]}
        parts = ", ".join(f"{n} {cls.replace('_', ' ')}" for cls, n in sorted(without.items(), key=lambda kv: -kv[1]))
        sentences.append(f"{pos}: of the unowned players with a verified join to the {census.get('season', 2026)} NFL roster capture, {with_f} of {total} "
                         f"have a research estimate" + (f"; the {total - with_f} without are {parts}." if total - with_f else "."))
    if lo.get("absent_from_census"):
        sentences.append(f"{lo['absent_from_census']} league-owned id(s) are absent from the dated census: identity and NFL status unknown, "
                         "still counted above.")
    for pos, cell in sorted(((cov.get("unverified_unowned") or {}).get("by_position") or {}).items()):
        n = cell.get("with_forecast", 0) + cell.get("without_forecast", 0)
        if n:
            sentences.append(f"{pos}: {n} unowned census member(s) have NO verified NFL join (contested or unknown identity) — "
                             f"{cell.get('with_forecast', 0)} with a research estimate, {cell.get('without_forecast', 0)} without; "
                             "not counted as listed.")
    if cov.get("contested_nfl_records"):
        n = cov["contested_nfl_records"]
        sentences.append(f"{n} NFL record{'s are' if n != 1 else ' is'} contested by more than one Sleeper id and "
                         f"{'are' if n != 1 else 'is'} attributed to nobody until the identity is resolved.")
    um = cov.get("unmatched_nfl_records") or {}
    if um.get("count"):
        sentences.append(f"{um['count']} NFL skill records match no Sleeper player and are kept separate, counted in no denominator.")
    if archive:
        sentences.append("Archive scope (Sleeper-eligible ids including inactive and retired players, not a current waiver pool): "
                         + " · ".join(f"{p} {n} without a forecast" for p, n in sorted(archive.items())) + ".")
    return {**cov, "archive": archive,
            "archive_note": "Sleeper-eligible ids including inactive and retired players; not a current waiver pool",
            "census_run_id": census.get("run_id"), "identity_checks": census.get("identity_checks"),
            "census_csv_sha256": census.get("census_csv_sha256"), "sentences": sentences}


def _outcome_artifact_summary(art: Optional[dict]) -> Optional[dict]:
    """What the shared outcome artifact (DG-179) is, for the page: its research qualification in
    words, the exact-scoring gaps it discloses, and its identity hashes for the details. Never
    'complete individual data'."""
    if not art:
        return None
    gaps = art.get("exact_league_scoring_gaps") or {}
    return {
        "scoring_preset": art.get("scoring_preset"),
        "research_qualified": bool(art.get("research_qualified")),
        "coverage_status": art.get("coverage_status"),
        "qualification_sentence": (
            "Outcomes come from one shared research artifact whose game coverage is qualified (admitted games match the "
            "source and unattributed rows are quarantined and disclosed); that is not proof that every individual stat is "
            "perfect, and it is not David's exact league scoring."
            if art.get("research_qualified") else
            f"Outcomes come from one shared artifact whose game coverage is NOT yet research-qualified ({art.get('coverage_status')}); "
            "numbers built on it are inspection only."),
        "exact_scoring_gaps": [f"{k}: {v}" for k, v in gaps.items()],
        "admitted_seasons": art.get("admitted_seasons"),
        "last_complete_season": art.get("last_complete_season"),
        "identity": {k: art.get(k) for k in ("target_identity", "scoring_identity", "window_identity",
                                             "outcomes_csv_sha256", "manifest_sha256", "source_identity_sha256")},
        "limitations": art.get("source_validation_limitations"),
    }


def _scoring_window_sentence(target: dict) -> str:
    """What the season totals are summed over, from the board's typed target: the week window
    and the scoring's caveat. The Week-17 window is David's championship calendar (Week 16
    before 2021), equal weekly weighting, and still not his exact league scoring."""
    from src.dynasty_genius.ranking.contract import SCORING_CAVEATS, WINDOW_DESCRIPTIONS

    window = target.get("window") or "all_reg_weeks"
    scoring = target.get("scoring") or "PPR_nflverse_weekly"
    from src.dynasty_genius.ranking.contract import TARGET_IDS

    desc = WINDOW_DESCRIPTIONS.get(window, window)
    caveat = SCORING_CAVEATS.get(scoring, "not David's exact league scoring")
    preset = TARGET_IDS.get((scoring, window))
    if preset and window != "all_reg_weeks":
        caveat = f"{caveat} (research preset {preset})"
    if window == "all_reg_weeks":
        return (f"Forecasts cover {desc}; {caveat}. That is not yet a forecast of David's fantasy weeks: his league "
                "plays a 14-week regular season with playoffs from week 15 and a championship in NFL Week 17, and no "
                "forecast has been recomputed over that window.")
    return f"Forecasts are {desc}; {caveat}."


def _producer_word(name: Optional[str], seasons: Optional[int]) -> str:
    """Producer ids are provenance, not copy: name each by what it forecasts."""
    n = (name or "").lower()
    if "rookie" in n or "dg165" in n:
        return "rookie forecast"
    if "basic" in n or (seasons or 0) >= 5:
        return "veteran forecast (long history)"
    return "veteran forecast"


def _historical_evaluation(m: dict, horizons: Optional[int]) -> dict[str, Any]:
    """The producer's OWN per-season historical evaluation, separate from file identity."""
    status = m.get("evaluation_status") or {}
    seasons = status.get("seasons") or {}
    out = {"available": bool(seasons), "source": status.get("source"), "meaning": status.get("meaning") or {},
           "note": m.get("evaluation_status_note"), "by_season": {}}
    for j in range(1, (horizons or 0) + 1):
        cell = seasons.get(str(j))
        if cell is None:
            out["by_season"][str(j)] = {"status": "unknown", "summary": "the producer reports no grading for this season"}
            continue
        summary = cell.get("summary") or ""
        out["by_season"][str(j)] = {
            "status": "not_evaluated" if summary.startswith("not evaluated") else "evaluated",
            "summary": summary,
            "positions": {pos: {"folds": c.get("folds"), "improvement": c.get("improvement")}
                          for pos, c in (cell.get("positions") or {}).items()}}
    return out


def _support_sentence(producers: list[dict], horizons: Optional[int]) -> str:
    """The adjacent, plain statement of what has historical support on this view."""
    parts = []
    for m in producers:
        word = _producer_word(m.get("model_version"), m.get("seasons"))
        ev = _historical_evaluation(m, horizons)
        evaluated = [j for j, c in ev["by_season"].items() if c["status"] == "evaluated"]
        not_ev = [j for j, c in ev["by_season"].items() if c["status"] != "evaluated"]
        if not ev["available"]:
            parts.append(f"The {word} carries no per-season historical evaluation on this file.")
            continue
        if not_ev and evaluated:
            parts.append(f"The {word}: season{'s' if len(evaluated) > 1 else ''} {', '.join(evaluated)} "
                         f"{'have' if len(evaluated) > 1 else 'has'} some historical support; season{'s' if len(not_ev) > 1 else ''} "
                         f"{', '.join(not_ev)} {'are' if len(not_ev) > 1 else 'is'} experimental and has not been evaluated.")
        elif not evaluated:
            parts.append(f"The {word} has not been historically evaluated on any season shown.")
        else:
            single = [j for j, c in ev["by_season"].items() if "single fold" in (c.get("summary") or "")]
            solid = [j for j in evaluated if j not in single]
            if single:
                parts.append(f"The {word} has some historical support on season{'s' if len(solid) > 1 else ''} "
                             f"{', '.join(solid)}; season {', '.join(single)} rests on one fold, which is not support.")
            else:
                parts.append(f"The {word} has some historical support on every season shown.")
    return " ".join(parts)


def _evidence_sentences(producers: list[dict], horizons: Optional[int] = None) -> list[str]:
    """The producers' own grading per season, folded into sentences a manager can read: which
    seasons are supported on many folds and which rest on one. Prefers the producer's
    machine-readable evaluation status; falls back to the results-file notes."""
    out: list[str] = []
    for m in producers:
        word = _producer_word(m.get("model_version"), m.get("seasons"))
        ev = _historical_evaluation(m, horizons or m.get("seasons"))
        if ev["available"]:
            for j, cell in ev["by_season"].items():
                out.append(f"{word}: season {j} {cell['summary']}.")
            continue
        notes = m.get("evidence_notes") or {}
        by_season: dict[int, list[str]] = {}
        for key, note in notes.items():
            try:
                j = int(str(key).split("season")[-1])
            except ValueError:
                continue
            by_season.setdefault(j, []).append(note)
        for j in sorted(by_season):
            ns = by_season[j]
            once = any("ONE fold" in n for n in ns)
            beats = sum(1 for n in ns if n.startswith("beats"))
            folds = next((n.split("graded on ")[-1].split(";")[0] for n in ns if "graded on" in n), None)
            if once:
                out.append(f"{word}: season {j} is a forecast graded once (one historical fold); treat it as unsupported.")
            else:
                out.append(f"{word}: season {j} beats its training-only baseline at {beats} of {len(ns)} positions"
                           + (f", graded on {folds}." if folds else "."))
    return out


def _assembled_grading_sentences(g: Optional[dict], horizons: Optional[int] = None) -> list[str]:
    """My grading of the ASSEMBLED value on the producers' histories, in sentences: per season
    the decision value against the training-only baseline by position, and for each k-season
    sum the count of origins whose interval sits above, below or across zero."""
    if not g:
        return ["The assembled value has not been graded on this view's producer histories."]
    out = []
    def fold_text(agg: dict) -> str:
        up, down = agg.get("folds_interval_above_zero", 0), agg.get("folds_interval_below_zero", 0)
        span = agg.get("folds_interval_spanning_zero", 0)
        rel = "above" if agg["decision_value"] > agg["baseline_decision_value"] else "below"
        return (f"{rel} baseline in total over {agg['folds']} fold{'s' if agg['folds'] != 1 else ''}"
                f" ({up} clearly above, {down} clearly below, {span} indistinguishable)")

    for h, kinds in sorted(g.get("seasons", {}).items(), key=lambda kv: int(kv[0])):
        if horizons is not None and int(h) > horizons:
            continue  # only the seasons this view sums
        for kind, who in (("joint", "both forecasts together"), ("veteran", "the veteran forecast alone")):
            cell = kinds.get(kind)
            if not cell:
                continue
            if cell.get("status", "").startswith("not graded") or not cell.get("by_position"):
                if kind == "joint":
                    why = cell.get("status") or ""
                    if why in ("", "not graded"):  # the joint block carries no reason; the veteran block does
                        why = (kinds.get("veteran") or {}).get("status") or "not graded"
                    out.append(f"Season {h}: the assembled value could not be graded ({why}).")
                continue
            parts = [f"{pos} {fold_text(agg)}" for pos, agg in sorted(cell["by_position"].items())]
            out.append(f"Season {h}, {who}, replace-or-retain decision value against the training-only baseline: "
                       + "; ".join(parts) + ".")
    for k, kinds in sorted(g.get("sums", {}).items(), key=lambda kv: int(kv[0])):
        if horizons is not None and int(k) > horizons:
            continue
        cell = kinds.get("joint") or kinds.get("veteran")
        if not cell:
            continue
        if cell.get("status", "").startswith("not graded") or not cell.get("origins"):
            out.append(f"The {k}-season sum from one origin cannot be graded on this file ({cell.get('status')}).")
            continue
        out.append(f"The {k}-season sum from one origin, {len(cell['origins'])} origin{'s' if len(cell['origins']) != 1 else ''}: "
                   f"{cell['cells_interval_above_zero']} cells above baseline, {cell['cells_interval_below_zero']} below, "
                   f"{cell['cells_interval_spanning_zero']} indistinguishable (intervals conditional on the observed cohort).")
    if g.get("interval_meaning"):
        out.append(f"Intervals: {g['interval_meaning']}.")
    return out


def _view(key: str, board: dict, report: dict, others: Optional[dict[str, dict]] = None) -> dict[str, Any]:
    producers = [m for m in board.get("annual_producers") or [] if "csv" in m]
    union = next((m for m in board.get("annual_producers") or [] if m.get("model_version") == "union_replacement"), {})
    grading = next((m.get("assembled_grading") for m in board.get("annual_producers") or []
                    if m.get("model_version") == "assembled_grading"), None)
    reference = {}
    for pos, refs in (union.get("replacement") or {}).items():
        r0 = refs[0]
        reference[pos] = {"player": r0.get("player_name"),
                          "expected_points_by_season": [r.get("rate_ppg") for r in refs],
                          "pool_complete": r0.get("pool_complete"), "note": r0.get("pool_note"),
                          "scope": r0.get("reference_scope") or "best among players with a forecast",
                          "unforecast_eligible": r0.get("unforecast_eligible"),
                          "unforecast_reasons": r0.get("unforecast_reasons"),
                          "census_complete": r0.get("census_complete"),
                          "nfl_status": r0.get("reference_nfl_status"),
                          "horizon_note": r0.get("horizon_note"),
                          "runner_up": r0.get("runner_up"),
                          "sensitivity_note": r0.get("sensitivity_note")}
    # The reference is chosen from THIS view's producers, so the same season's reference can
    # differ between views; a player's swing between views can come from the reference, not
    # his forecast. Say so when it happens.
    cross_view = None
    for okey, oboard in (others or {}).items():
        if okey == key:
            continue
        ounion = next((m for m in oboard.get("annual_producers") or [] if m.get("model_version") == "union_replacement"), {})
        diffs = []
        for pos, refs in (ounion.get("replacement") or {}).items():
            mine = reference.get(pos)
            if mine and refs and refs[0].get("player_name") != mine["player"]:
                diffs.append(f"{pos} {mine['player']} here vs {refs[0].get('player_name')} on the "
                             f"{oboard.get('horizons_summed')}-year view")
        if diffs:
            cross_view = ("The reference player is chosen from this view's own forecasts, so it differs between views: "
                          + "; ".join(diffs) + ". A player who reads differently on the two views may owe the swing to "
                          "the reference, not to his forecast.")
    horizons = board.get("horizons_summed")
    forecast_year = int(str(report.get("forecast_date", "2026"))[:4])
    seasons = [forecast_year + h for h in range(horizons or 0)]
    label = f"{_WORDS.get(horizons, str(horizons))}-year impact (research preview)"
    seasons_word = _WORDS.get(horizons, str(horizons)).lower()

    def other_for(row: dict) -> Optional[dict]:
        """Another view that carries a number for this player, when this one does not."""
        if row.get("readiness") != "none":
            return None
        for okey, oboard in (others or {}).items():
            if okey == key:
                continue
            for section in ("davids_roster", "league_rostered", "all_inspectable"):
                hit = next((r for r in oboard.get(section) or [] if r.get("player_id") == row.get("player_id")
                            and r.get("readiness") == "comparable"), None)
                if hit:
                    h = oboard.get("horizons_summed")
                    return {"view": okey, "label": f"{h}-year", "seasons_word": _WORDS.get(h, str(h)).lower(),
                            "value": hit.get("value")}
        return None

    ref_series = {pos: r["expected_points_by_season"] for pos, r in reference.items()}
    census = report.get("current_census") or {}
    attach = census.get("reference_attachment") or {}
    for pos, r in reference.items():
        r["sleeper_status"] = r.get("nfl_status")  # Sleeper's flag, named as Sleeper's
        r["nfl_attachment"] = attach.get(pos) or {"status": "unverified", "basis": "no census bound",
                                                   "note": "no dated census bound to this run; NFL attachment unknown"}

    def player(row: dict) -> dict:
        return _player(row, seasons_word=seasons_word, other_view=other_for(row),
                       reference_series=ref_series.get(row.get("position")))

    return {
        "key": key,
        "basis": {"label": label, "horizons_summed": horizons, "seasons": seasons,
                  "estimand": ("season points above the actual available replacement at his position, "
                               "season-long replace-or-retain, summed over the seasons shown"),
                  "is_complete_dynasty_value": False,
                  "scoring_window": _scoring_window_sentence(report.get("board_target") or {}),
                  "evidence_framing": ("Forecast evidence is a retrospective historical evaluation with forecast cutoffs "
                                       "enforced, not an independent confirmation; the rookie forecast's policy menu was "
                                       "refined after historical inspection."),
                  "target": report.get("board_target"),
                  "outcome_artifact": _outcome_artifact_summary(report.get("outcome_artifact")),
                  "advice_note": ("Above or below reference is a season-points counterfactual against the reference "
                                  "player, not a recommendation to drop, trade or start anyone: trade value, future "
                                  "options and weekly lineups are outside this number.")},
        "producers": [{"name": m.get("model_version"), "label": _producer_word(m.get("model_version"), m.get("seasons")),
                       "seasons": m.get("seasons"),
                       "evidence_verified": bool((m.get("evidence") or {}).get("verified")),
                       "evidence_reason": (m.get("evidence") or {}).get("reason"),
                       "identity": {"verified": bool((m.get("evidence") or {}).get("verified")),
                                    "reason": (m.get("evidence") or {}).get("reason"),
                                    "meaning": (m.get("evidence") or {}).get("meaning")
                                    or "source check: file identity, not scientific validation",
                                    "bound_files": (m.get("evidence") or {}).get("bound_files")},
                       "historical_evaluation": _historical_evaluation(m, horizons)} for m in producers],
        "support_sentence": _support_sentence(producers, horizons),
        "evidence_sentences": _evidence_sentences(producers, horizons),
        "assembled_grading": grading,
        "assembled_grading_sentences": _assembled_grading_sentences(grading, horizons),
        "reference": reference,
        "coverage": _coverage(report, census),
        "cross_view_note": cross_view,
        "readiness_counts": board.get("readiness") or {},
        "roster": [player(r) for r in board.get("davids_roster") or []],
        "league": [player(r) for r in board.get("league_rostered") or []],
        "top": [player(r) for r in board.get("top") or []],
    }


@router.get("/preview")
def research_preview(run: Optional[str] = Query(default=None)) -> dict[str, Any]:
    run_id, report, pinned = _latest_report(run)
    views_map = report.get("comparable_views") or {"h2": "comparable_board"}
    boards = {key: report.get(section) for key, section in views_map.items() if report.get(section)}
    views = []
    for key, board in sorted(boards.items(), key=lambda kv: int(kv[0].lstrip("h") or 0)):
        views.append(_view(key, board, report, others=boards))
    if not views:
        views.append(_view("h2", report.get("comparable_board") or {}, report))
    # A model comparison is a DIFFERENT MODEL on the same target, shown in the research
    # details, never as a horizon toggle: the horizon views are prefix sums of one term set.
    comparisons = []
    for key, section in (report.get("model_comparisons") or {}).items():
        board = report.get(section)
        if not board:
            continue
        cmp_view = _view(key, board, report, others=None)
        cmp_view["label"] = board.get("label") or key
        cmp_view["kind"] = "model_comparison"
        comparisons.append(cmp_view)
    lead = views[0]
    return {
        "source": {"kind": "local_research_run", "run": run_id, "pinned": pinned, "forecast_date": report.get("forecast_date"),
                   "artifact_captured_at": (report.get("inputs") or {}).get("artifact", {}).get("captured_at"),
                   "snapshot": (report.get("inputs") or {}).get("snapshot", {}).get("id"),
                   "note": "candidate research values from a local run; the live served values are untouched and shown beside them"},
        # the first view stays at the top level for the two-year page contract
        "basis": lead["basis"], "producers": lead["producers"], "reference": lead["reference"],
        "readiness_counts": lead["readiness_counts"], "roster": lead["roster"], "league": lead["league"], "top": lead["top"],
        "views": views,
        "composition": {"rule": ("every horizon view is a prefix sum of ONE set of per-season terms: same forecasts, "
                                 "reference, scoring and snapshot; the longer view sums more of the same non-negative terms"),
                        "consistency": report.get("composition_consistency")},
        "model_comparisons": comparisons,
    }
