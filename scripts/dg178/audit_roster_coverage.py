"""DG-178 read-only audit: David's actual roster through the candidate ranking contract.

Reads (never writes) three inputs the caller names explicitly, records the sha256 and
vintage of each, composes every skill-position row in the served artifact through the
veteran adapter, and reports — for David's roster first, then his league, then the
universe — who gets a candidate value, who gets a stated blank, and why. The three players
DG-176 names are called out by name. Two postures are shown side by side; neither is David's.

Outputs go to a fresh run-scoped directory (``runs/<UTC>/dg178_audit/``) and nothing else.

    .venv/bin/python scripts/dg178/audit_roster_coverage.py \
        --artifact ~/dynasty-genius-product/app/data/valuation_runtime/universe_pvo_runtime.json \
        --snapshot ~/dynasty-genius-product/app/data/league_runtime/runs/league-20260906T130052Z/snapshot.json \
        --cells ~/dg-build/preserved/2026-09-06-dg164-survival-cells/retention_R_v3.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.dynasty_genius.ranking.adapters.annual_candidate import (  # noqa: E402
    AnnualCandidate,
    annual_replacement,
)
from src.dynasty_genius.ranking.adapters.rookie_candidate import (
    RookieCandidate,  # noqa: E402
)
from src.dynasty_genius.ranking.assembler import assemble  # noqa: E402
from src.dynasty_genius.ranking.audit_support import (  # noqa: E402
    reconcile_roster,
    replacement_pool_census,
    rows_by_sleeper_id,
)
from src.dynasty_genius.ranking.compose import (  # noqa: E402
    absent_annual_term_sets,
    compose_annual_term_sets,
    compose_term_sets,
)
from src.dynasty_genius.ranking.contract import Posture, annual_target  # noqa: E402
from src.dynasty_genius.ranking.league_settings import LeagueSettings  # noqa: E402
from src.dynasty_genius.ranking.lineup_gain import (  # noqa: E402
    Starter,
    active_lineup_pool,
    best_lineup,
    eligibility_nests,
)
from src.dynasty_genius.ranking.replacement import available_replacement  # noqa: E402
from src.dynasty_genius.ranking.served_rows import (  # noqa: E402
    SKILL_POSITIONS,
    ServedArtifact,
)
from src.dynasty_genius.ranking.survival_cells import RetentionCells  # noqa: E402

DG176_NAMES = ("Fernando Mendoza", "Ty Simpson", "Kenyon Sadiq")
# Two postures for inspection. Neither is David's: he has not declared one, and the
# assembler never infers it. d=1.0 is the rebuild extreme (DG-168's default); 0.6 is an
# illustrative contend lean chosen only to show the direction of the effect.
POSTURES = (Posture(label="rebuild (d=1.0, illustrative)", discount=1.0),
            Posture(label="contend (d=0.6, illustrative)", discount=0.6))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head() -> Optional[str]:
    import subprocess
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return None


def _git_dirty() -> Optional[bool]:
    import subprocess
    try:
        out = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=REPO,
                             capture_output=True, text=True, check=True).stdout
        return bool(out.strip())
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", required=True, type=Path)
    ap.add_argument("--snapshot", required=True, type=Path)
    ap.add_argument("--cells", required=True, type=Path)
    ap.add_argument("--rookie-csv", type=Path, default=None,
                    help="DG-165 candidate CSV (research output); Engine A rows route through it when given")
    ap.add_argument("--rookie-manifest", type=Path, default=None)
    ap.add_argument("--rookie-evaluation", type=Path, default=None,
                    help="DG-165 evaluation.json; defaults to the CSV's sibling when it exists")
    ap.add_argument("--comparison-csv", "--annual-csv", dest="annual_csv", type=Path, action="append", default=[],
                    help="a producer's ANNUAL-TARGET file (agreed shape); repeatable, one per producer")
    ap.add_argument("--comparison-manifest", "--annual-manifest", dest="annual_manifest", type=Path, action="append", default=[])
    ap.add_argument("--main-csv", "--horizon-csv", dest="horizon_csv", type=Path, action="append", default=[],
                    help="a LONGER-horizon producer file on the annual target (repeatable, one per producer); builds a second board view")
    ap.add_argument("--main-manifest", "--horizon-manifest", dest="horizon_manifest", type=Path, action="append", default=[])
    ap.add_argument("--comparison-grading", "--annual-grading", dest="annual_grading", type=Path, default=None,
                    help="grade_assembled_value.py report.json for the two-year producers; summarised onto the board")
    ap.add_argument("--main-grading", "--horizon-grading", dest="horizon_grading", type=Path, default=None,
                    help="grade_assembled_value.py report.json for the longer-horizon producers; summarised onto the board")
    ap.add_argument("--census-dir", type=Path, default=None,
                    help="an explicit immutable dg178_current_census run directory (never a 'latest' path): its bytes and "
                         "source identities are re-verified and bound; coverage is reported as separate populations")
    ap.add_argument("--universe", type=Path, default=None,
                    help="eligible_universe.csv from build_eligible_universe.py: counts eligible unrostered players no "
                         "producer forecast, per position, so the reference states its scope (round 3)")
    ap.add_argument("--eligibility", type=Path, default=None,
                    help="lane 24974's sleeper_eligibility.csv: places every artifact row at its Sleeper fantasy position "
                         "and carries the NFL roster status onto the reference")
    ap.add_argument("--identity-bridge", type=Path, default=None,
                    help="a producer's reconciliation CSV (sleeper_id,gsis_id,...) used to fill missing gsis ids before composing")
    ap.add_argument("--forecast-date", default=date.today().isoformat())
    ap.add_argument("--window", choices=["all_reg_weeks", "championship_week17"], default="all_reg_weeks",
                    help="the board's week window; every producer file must be summed over the SAME window or it is refused")
    ap.add_argument("--outcome-manifest", type=Path, default=None,
                    help="DG-179's shared outcome artifact manifest (schema dg179_league_season_outcomes_v1); with --outcome-csv, "
                         "the board target is derived from it and every MAIN producer must bind exactly this artifact")
    ap.add_argument("--outcome-csv", type=Path, default=None, help="the artifact's outcomes.csv (bytes checked against the manifest)")
    ap.add_argument("--band", type=int, default=1)
    ap.add_argument("--out-root", type=Path, default=REPO / "runs")
    a = ap.parse_args()
    forecast_date = date.fromisoformat(a.forecast_date)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = a.out_root / stamp / "dg178_audit"
    if out.exists():
        raise SystemExit(f"refusing to overwrite {out}")
    out.mkdir(parents=True)

    art = ServedArtifact.load(a.artifact)
    eligibility_meta = None
    if a.eligibility is not None:
        from src.dynasty_genius.ranking.served_rows import read_fantasy_eligibility
        elig = read_fantasy_eligibility(a.eligibility)
        plain_pos = {str(r.sleeper_id): r.position for r in art.rows if r.sleeper_id is not None} | dict(art.other_positions)
        # Placement happens BEFORE the population filter: a DB|WR the artifact lists as DB joins as a WR.
        art = ServedArtifact.load(a.artifact, eligibility=elig)
        moved = [(r.full_name, plain_pos.get(str(r.sleeper_id)), r.position) for r in art.rows
                 if r.sleeper_id is not None and plain_pos.get(str(r.sleeper_id)) not in (None, r.position)]
        eligibility_meta = {"path": str(a.eligibility), "sha256": hashlib.sha256(a.eligibility.read_bytes()).hexdigest(),
                            "rows": len(elig), "placed_from_sleeper": sum(1 for r in art.rows if r.placement_source),
                            "position_changed": len(moved), "position_changed_examples": moved[:12],
                            "joined_from_outside_the_skill_population": [n for n, o, _ in moved if o not in SKILL_POSITIONS]}
    bridge_meta = None
    if a.identity_bridge is not None:
        import csv as _csv

        from src.dynasty_genius.ranking.served_rows import apply_identity_bridge

        with a.identity_bridge.open(newline="") as fh:
            mapping = {str(r["sleeper_id"]): r.get("gsis_id") or "" for r in _csv.DictReader(fh) if r.get("sleeper_id")}
        before = sum(1 for r in art.rows if r.gsis_id)
        art = art.model_copy(update={"rows": apply_identity_bridge(art.rows, mapping)})
        bridge_meta = {"path": str(a.identity_bridge), "sha256": sha(a.identity_bridge),
                       "gsis_filled": sum(1 for r in art.rows if r.gsis_id) - before}
    snapshot_bytes = a.snapshot.read_bytes()  # ONE read: parsed and hashed from the same bytes
    snapshot_sha256 = hashlib.sha256(snapshot_bytes).hexdigest()
    snap_raw = json.loads(snapshot_bytes)
    snapshot_id = a.snapshot.parent.name
    settings = LeagueSettings.from_snapshot(snap_raw, snapshot_id=snapshot_id)
    cells = RetentionCells.load(a.cells)
    rookie = None
    if a.rookie_csv is not None:
        if a.rookie_manifest is None:
            raise SystemExit("--rookie-csv needs --rookie-manifest")
        ev = a.rookie_evaluation
        if ev is None and (a.rookie_csv.parent / "evaluation.json").exists():
            ev = a.rookie_csv.parent / "evaluation.json"
        rookie = RookieCandidate.load(a.rookie_csv, a.rookie_manifest, evaluation_path=ev)
    # Re-read the artifact hash at the end: a producer rewriting it mid-audit must show.
    art_sha_start = art.sha256

    rosters = snap_raw["rosters"]
    rostered = {str(pid) for r in rosters for pid in (r.get("players") or [])}
    david = next(r for r in rosters if r["roster_id"] == snap_raw["david_roster_id"])
    mine = [str(pid) for pid in (david.get("players") or [])]
    by_sid = rows_by_sleeper_id(art.rows)  # refuses duplicate Sleeper ids
    league_ids = [str(pid) for r in rosters for pid in (r.get("players") or [])]
    roster_of = {str(pid): int(r["roster_id"]) for r in rosters for pid in (r.get("players") or [])}
    my_rec = reconcile_roster(mine, art.rows, other_positions=art.other_positions)
    league_rec = reconcile_roster(league_ids, art.rows, other_positions=art.other_positions)
    pool = replacement_pool_census(art.rows, rostered_ids=rostered, positions=sorted(SKILL_POSITIONS))
    outcome_artifact = None
    if (a.outcome_manifest is None) != (a.outcome_csv is None):
        raise SystemExit("--outcome-manifest and --outcome-csv must be given together")
    if a.outcome_manifest is not None:
        from src.dynasty_genius.ranking.outcome_artifact import OutcomeArtifact
        outcome_artifact = OutcomeArtifact.load(a.outcome_manifest, a.outcome_csv)  # refuses on any failed check
        if a.window != "championship_week17":
            raise SystemExit("the shared outcome artifact is on the championship_week17 window; pass --window championship_week17")
        board = outcome_artifact.target_spec()
        if board.labels_through != forecast_date.year - 1:
            raise SystemExit(f"the artifact's last complete season {board.labels_through} is not the season before the "
                             f"forecast year {forecast_date.year}; labels outside admitted seasons are unknown, not zero")
    else:
        board = annual_target(forecast_date, window=a.window)

    replacement = available_replacement(art.rows, rostered_ids=rostered, snapshot_id=snapshot_id,
                                        band=a.band, positions=sorted(SKILL_POSITIONS))
    term_sets = compose_term_sets(art.rows, replacement, cells, rookie_candidate=rookie,
                                  forecast_date=forecast_date, horizons=cells.horizons)
    assert len(term_sets) == len(art.rows), "rows out != skill rows in"
    # Two postures x two board horizons: six seasons (the cells' reach) and five (the rookie
    # candidate's reach in its first run). Neither posture is David's.
    BOARDS = [(p, h) for h in (cells.horizons, cells.horizons - 1) for p in POSTURES]
    results = {f"{p.label}|h{h + 1}": assemble(term_sets, p, horizons=h, board=board) for p, h in BOARDS}
    # The comparable-only board: what could be ranked TODAY on the typed annual target.
    # Without an annual producer file every row is research-only and the board is empty.
    def grading_file(csv_p: Path):
        for name in ("results.json", "evaluation.json"):
            if (csv_p.parent / name).exists():
                return csv_p.parent / name
        return None

    # Plan T2 (2026-09-06): the reviewed dated census, bound by bytes and identities, read as separate populations.
    census_binding = None
    if a.census_dir is not None:
        from src.dynasty_genius.ranking.current_census_binding import CensusBinding
        snapshot_owned = {str(pid): int(r["roster_id"]) for r in (snap_raw.get("rosters") or []) for pid in (r.get("players") or [])}
        census_binding = CensusBinding.load(a.census_dir, season=forecast_date.year,
                                            league_snapshot_sha256=snapshot_sha256, snapshot_owned=snapshot_owned)

    # Round 3: the eligible census. Which eligible unrostered players did NO producer forecast,
    # per position, and why. Without it the reference says the count is unknown, never zero.
    unforecast_census = None
    stated_reasons: dict[str, str] = {}  # Sleeper id -> a producer's stated reason for not forecasting him
    if a.universe is not None:
        import csv as _csv
        from collections import Counter
        unforecast_census = {}
        with a.universe.open(newline="") as fh:
            for rec in _csv.DictReader(fh):
                if rec.get("sleeper_id") and not rec.get("forecast_by") and (rec.get("forecast_reason") or "").strip():
                    stated_reasons[str(rec["sleeper_id"])] = rec["forecast_reason"].strip()
                pos = (rec.get("position") or "").upper()
                if pos not in SKILL_POSITIONS or str(rec.get("rostered")).lower() == "true" or rec.get("forecast_by"):
                    continue
                cell = unforecast_census.setdefault(pos, {"count": 0, "reasons": Counter()})
                cell["count"] += 1
                reason = (rec.get("forecast_reason") or "no reason recorded").split(":")[-1].strip()
                cell["reasons"][reason] += 1
        unforecast_census = {pos: {"count": c["count"], "reasons": dict(c["reasons"].most_common())}
                             for pos, c in unforecast_census.items()}
        for pos in SKILL_POSITIONS:
            unforecast_census.setdefault(pos, {"count": 0, "reasons": {}})

    def grading_summary(path):
        """A compact, honest summary of my grading of the ASSEMBLED value on a producer's
        history (round 3 rules): per season, decision value against the training-only
        baseline by position with the fold count; per k-season sum, how many origins carry
        a positive / negative difference whose interval excludes zero. Never a superiority
        claim: the cells are reported, not pooled."""
        if path is None:
            return None
        g = json.loads(Path(path).read_text())
        out = {"run": g.get("run"), "report": str(path), "reference_rule": g.get("reference_rule"),
               "interval_meaning": g.get("interval_meaning"),
               "veteran_history_bound": (g.get("inputs", {}).get("veteran_history", {}).get("binding") or {}).get("bound"),
               "read_mode": g.get("inputs", {}).get("veteran_history", {}).get("read_mode"),
               "seasons": {}, "sums": {}}
        for key, block in g.get("grades", {}).items():
            if key.startswith("joint_season") or key.startswith("veteran_season"):
                h = int(key.rsplit("season", 1)[-1])
                kind = "joint" if key.startswith("joint") else "veteran"
                cells = block.get("cells") or {}
                per_pos = {}
                for cell_key, cell in cells.items():
                    if "skipped" in cell:
                        continue
                    pos = cell_key.split("|")[0]
                    agg = per_pos.setdefault(pos, {"folds": 0, "n": 0, "decision_value": 0.0, "baseline_decision_value": 0.0,
                                                   "folds_interval_above_zero": 0, "folds_interval_below_zero": 0,
                                                   "folds_interval_spanning_zero": 0})
                    agg["folds"] += 1
                    agg["n"] += cell.get("n", 0)
                    agg["decision_value"] += cell.get("decision_value_sum", 0.0)
                    agg["baseline_decision_value"] += cell.get("baseline_decision_value_sum", 0.0)
                    ci = cell.get("decision_value_diff_ci90")
                    if ci and ci[0] > 0:
                        agg["folds_interval_above_zero"] += 1
                    elif ci and ci[1] < 0:
                        agg["folds_interval_below_zero"] += 1
                    else:
                        agg["folds_interval_spanning_zero"] += 1
                out["seasons"].setdefault(str(h), {})[kind] = {
                    "status": block.get("status") or ("graded" if cells else "not graded"), "n": block.get("n"),
                    "unavailable_rows": block.get("unavailable_rows"), "by_position": per_pos}
            elif "_season_sum_" in key:
                k = int(key.split("_")[0])
                kind = "joint" if "joint" in key else "veteran"
                cells = block.get("cells") or {}
                pos_up, pos_down, pos_zero = 0, 0, 0
                for cell in cells.values():
                    ci = cell.get("decision_value_diff_ci90")
                    if "skipped" in cell or not ci:
                        continue
                    if ci[0] > 0:
                        pos_up += 1
                    elif ci[1] < 0:
                        pos_down += 1
                    else:
                        pos_zero += 1
                out["sums"].setdefault(str(k), {})[kind] = {
                    "status": block.get("status") or ("graded" if cells else "not graded"),
                    "origins": block.get("origins"), "n": block.get("n"),
                    "cells_interval_above_zero": pos_up, "cells_interval_below_zero": pos_down,
                    "cells_interval_spanning_zero": pos_zero}
        return out

    def build_sets(csvs, manifests, grading_path=None):
        """One set of per-season terms per player from these producers. Every horizon view is
        a PREFIX SUM of the same terms (Codex, round 3): same terms, reference, scoring and
        snapshot; the 2-year and 5-year numbers differ only in how many seasons are summed."""
        if len(csvs) != len(manifests):
            raise SystemExit("producer csv/manifest arguments must be given in pairs")
        sets_out, meta = [], []
        covered: set[str] = set()
        cands = [AnnualCandidate.load(csv_p, man_p, results_path=grading_file(csv_p), window=a.window)
                 for csv_p, man_p in zip(csvs, manifests)]
        if outcome_artifact is not None:
            from src.dynasty_genius.ranking.outcome_artifact import (
                producer_binding_matches,
            )
            for c in cands:
                bad = producer_binding_matches(c.outcome_identity, outcome_artifact)
                if bad:
                    raise SystemExit(f"{c.model_version} does not bind the shared outcome artifact exactly: {bad} differ")
        refs = annual_replacement(cands, rostered_ids=rostered, snapshot_id=snapshot_id, band=a.band,
                                  positions=sorted(SKILL_POSITIONS), served_rows=art.rows,
                                  unforecast_eligible=unforecast_census)
        for cand, csv_p in zip(cands, csvs):
            sets = compose_annual_term_sets([r for r in art.rows if r.player_id not in covered], refs, cand,
                                            forecast_date=forecast_date)
            sets_out.extend(t for t in sets if t.coverage != "none")
            covered |= {t.player_id for t in sets if t.coverage != "none"}
            meta.append({"model_version": cand.model_version, "csv": str(csv_p), "csv_sha256": cand.csv_sha256,
                         "manifest_sha256": cand.manifest_sha256, "seasons": cand.seasons,
                         "results_sha256": cand.results_sha256,
                         "evidence": {"verified": cand.evidence.verified, "reason": cand.evidence.reason,
                                      "meaning": cand.evidence.meaning, "bound_files": cand.evidence.bound_files,
                                      "scoring_arm": cand.evidence.scoring_arm, "graded_arm": cand.evidence.graded_arm},
                         "evaluation_status": cand.evaluation_status.to_json() if cand.evaluation_status else None,
                         "evaluation_status_note": cand.evaluation_status_note,
                         "evidence_notes": {f"{pos}|season{j}": n for (pos, j), n in sorted(cand.evidence_notes.items())}})
        meta.append({"model_version": "union_replacement", "seasons": min(c.seasons for c in cands),
                     "replacement": {pos: [r.model_dump(mode="json") for r in rr] for pos, rr in refs.items()},
                     "positions_without_a_bar": sorted(set(SKILL_POSITIONS) - set(refs))})
        meta.append({"model_version": "assembled_grading", "assembled_grading": grading_summary(grading_path)})
        uncovered = [r for r in art.rows if r.player_id not in covered]
        sets_out.extend(absent_annual_term_sets(uncovered, [c.model_version for c in cands], forecast_date=forecast_date,
                                                stated_reasons=stated_reasons))
        h = min(c.seasons for c in cands) - 1
        return sets_out, {t.player_id: t for t in sets_out}, meta, h

    def assemble_view(sets_out, h):
        return assemble(sets_out, POSTURES[0], horizons=h, board=board, comparable_only=True)

    def build_view(csvs, manifests, grading_path=None, horizons=None):
        sets_out, by_pid_sets, meta, h_max = build_sets(csvs, manifests, grading_path)
        h = h_max if horizons is None else min(horizons, h_max)
        return assemble_view(sets_out, h), by_pid_sets, meta, h

    annual_meta, annual_h = [], None
    if a.annual_csv:
        comparable, annual_by_pid, annual_meta, annual_h = build_view(a.annual_csv, a.annual_manifest, a.annual_grading)
    else:
        annual_by_pid = {}
        comparable = assemble(term_sets, POSTURES[0], horizons=cells.horizons, board=board, comparable_only=True)
    # Main producers: ONE set of terms, assembled as the 2-year prefix and the full reach.
    main_views: dict[int, tuple] = {}
    consistency = None
    if a.horizon_csv:
        main_sets, main_by_pid, main_meta, main_h = build_sets(a.horizon_csv, a.horizon_manifest, a.horizon_grading)
        for h in sorted({min(1, main_h), main_h}):
            main_views[h] = (assemble_view(main_sets, h), main_by_pid, main_meta, h)
        # Composition consistency, asserted: the first two seasons are the same terms on both views
        # and, with non-negative contributions, the longer sum never falls below the shorter one.
        if len(main_views) == 2:
            short, long_ = main_views[min(main_views)][0], main_views[max(main_views)][0]
            long_by = {v.player_id: v for v in long_.values}
            checked, violations = 0, []
            for v in short.values:
                w = long_by.get(v.player_id)
                if w is None or v.value is None or w.value is None:
                    continue
                checked += 1
                ts = main_by_pid.get(v.player_id)
                first_two = [t.ev_above_replacement for t in (ts.terms if ts else [])][:2]
                if w.value + 1e-9 < v.value or any(x < 0 for x in first_two):
                    violations.append((v.player_id, v.value, w.value))
            if violations:
                raise SystemExit(f"horizon views are not a prefix sum: {violations[:5]}")
            consistency = {"players_checked": checked, "violations": 0,
                           "rule": "same per-season terms, reference, scoring and snapshot; the longer view sums more of the same "
                                   "non-negative terms, so value(5) >= value(2) for every player"}
    horizon_view = main_views.get(max(main_views)) if main_views else None
    short_view = main_views.get(min(main_views)) if len(main_views) == 2 else None
    by_pid = {lab: {v.player_id: v for v in res.values} for lab, res in results.items()}
    lead = f"{POSTURES[0].label}|h{cells.horizons + 1}"

    def board_row(v, ts, h=None):
        """One comparable-board row with the per-season detail the preview shows (only the
        seasons this view sums)."""
        served_row = by_sid.get(v.sleeper_id)
        seasons = []
        terms = list(ts.terms) if ts is not None else []
        if h is not None:
            terms = [t for t in terms if t.h <= h]
        for t in terms:
            seasons.append({"season": t.season, "expected_margin": t.expected_margin, "action": t.action,
                            "advantage": t.ev_above_replacement})
        ref = ts.replacement_ref if ts is not None else None
        return {"player_id": v.player_id, "sleeper_id": v.sleeper_id, "name": v.full_name, "position": v.position,
                "team": served_row.team if served_row else None,
                "age": served_row.age if served_row else None,
                "value": v.value, "readiness": v.readiness, "reason": v.reason,
                "fantasy_positions": list(served_row.fantasy_positions) if served_row and served_row.fantasy_positions else None,
                "placement_source": served_row.placement_source if served_row else None,
                "nfl_status": served_row.nfl_status if served_row else None,
                "producer": v.producer.name, "estimate_class": v.producer.estimate_class,
                "evidence_verified": v.producer.evidence_verified,
                "served_dvs": v.served.dynasty_value_score if v.served else None,
                "reference_player": ref.player_name if ref else None,
                "reference_expected_points": ref.rate_ppg if ref else None,
                "seasons": seasons, "rostered_by": roster_of.get(v.sleeper_id),
                "on_davids_roster": v.sleeper_id in mine}

    def row_report(ts):
        rv = {lab: by_pid[lab][ts.player_id] for lab in by_pid}
        first = next(iter(rv.values()))
        return {
            "player_id": ts.player_id, "sleeper_id": ts.sleeper_id, "name": ts.full_name,
            "position": ts.position, "coverage": ts.coverage, "reason": ts.reason,
            "estimate_class": ts.producer.estimate_class, "producer": ts.producer.name,
            "readiness": first.readiness, "comparability_note": first.comparability_note,
            "unit": first.unit,
            "served_dvs": ts.served.dynasty_value_score if ts.served else None,
            "served_engine": ts.served.dvs_engine if ts.served else None,
            "ev_h": [t.ev_above_replacement for t in ts.terms],
            "value": {lab: v.value for lab, v in rv.items()},
            "replacement_rate_ppg": ts.replacement_ref.rate_ppg if ts.replacement_ref else None,
            "replacement_player": ts.replacement_ref.player_name if ts.replacement_ref else None,
            "horizons_used": first.horizons_used,
        }

    ts_by_sid = {t.sleeper_id: t for t in term_sets}
    roster_rows = []
    for sid in mine:
        t = ts_by_sid.get(sid)
        if t is None:
            roster_rows.append({"sleeper_id": sid, "name": None, "coverage": "absent_from_artifact",
                                "reason": "no row in the served artifact for this sleeper id"})
        else:
            roster_rows.append(row_report(t))

    # Marginal lineup gain for each of his ACTIVE players (taxi and IR cannot start), on
    # served h=0 rates, remove-one. A player outside the pool gets None, not 0.0.
    lineup_gain = {}
    active = active_lineup_pool(david)
    lineup_excluded = [s for s in mine if s not in active]
    if eligibility_nests(settings):
        starters = [Starter(player_id=r.sleeper_id, position=r.position, rate_ppg=r.served_rate_ppg)
                    for r in (by_sid.get(s) for s in active) if r is not None and r.served_rate_ppg is not None]
        full = best_lineup(starters, settings)
        for s in starters:
            without = best_lineup([x for x in starters if x.player_id != s.player_id], settings)
            lineup_gain[s.player_id] = round(full.total_ppg - without.total_ppg, 3)
        for row in roster_rows:
            row["marginal_lineup_gain_ppg"] = lineup_gain.get(row.get("sleeper_id"))
        lineup_assignment = full.assignment
        lineup_total = full.total_ppg
    else:
        lineup_assignment, lineup_total = None, None

    lead_values = by_pid[lead]

    def coverage_counts(sets, absent: int = 0, outside: int = 0):
        """Numerical coverage over EVERY id in the population: rows the artifact lacks are
        counted as `absent_from_artifact`, never dropped from the denominator."""
        c = Counter(t.coverage for t in sets)
        # Group on the stable head of the reason (before any ';' or ':'), so per-player
        # detail such as a quoted probability vector does not fragment the table.
        reasons = Counter((t.coverage, (t.reason or "").split(";")[0].split(":")[0]) for t in sets if t.coverage != "full")
        r = Counter(lead_values[t.player_id].readiness for t in sets)
        return {"denominator": len(sets) + absent + outside,
                "full": c.get("full", 0), "partial": c.get("partial", 0), "none": c.get("none", 0),
                "absent_from_artifact": absent, "outside_skill_population": outside,
                "readiness": {"comparable": r.get("comparable", 0), "research_only": r.get("research_only", 0),
                              "incomplete": r.get("incomplete", 0), "none": r.get("none", 0),
                              "absent_from_artifact": absent, "outside_skill_population": outside},
                "reasons": {f"{k[0]}|{k[1]}": n for k, n in reasons.most_common()}}

    league_sets = [t for t in term_sets if t.sleeper_id in rostered]
    dg176 = []
    for name in DG176_NAMES:
        hits = [t for t in term_sets if t.full_name == name]
        dg176.append({"name": name, "found": bool(hits),
                      "rows": [row_report(t) for t in hits],
                      "on_davids_roster": any(t.sleeper_id in mine for t in hits)})

    art_sha_end = sha(a.artifact)
    report = {
        "run": stamp, "forecast_date": forecast_date.isoformat(),
        # Exact provenance of this composition: the code that ran and the command it ran with.
        "provenance": {"git_head": _git_head(), "git_dirty": _git_dirty(), "argv": sys.argv[1:],
                       "script": str(Path(__file__).resolve().relative_to(REPO)),
                       "generated_at": datetime.now(timezone.utc).isoformat()},
        "inputs": {
            "artifact": {"path": str(a.artifact), "sha256": art_sha_start, "sha256_at_end": art_sha_end,
                         "captured_at": art.captured_at, "total_rows": art.total_rows,
                         "skill_rows": len(art.rows)},
            "snapshot": {"path": str(a.snapshot), "sha256": snapshot_sha256, "id": snapshot_id,
                         "captured_at": snap_raw.get("captured_at")},
            "cells": {"path": str(a.cells), "sha256": cells.source_sha256, "horizons": cells.horizons,
                      "bar_ranks": cells.bar_ranks},
        },
        "identity_bridge": bridge_meta,
        "league": settings.model_dump(),
        "replacement": {pos: ref.model_dump() for pos, ref in replacement.items()},
        "postures": [p.model_dump() for p in POSTURES],
        "boards": list(results.keys()),
        "rookie_candidate": (None if rookie is None else {
            "model_version": rookie.model_version, "csv": str(rookie.csv_path), "csv_sha256": rookie.csv_sha256,
            "manifest_sha256": rookie.manifest_sha256, "seasons_covered": rookie.seasons_covered,
            "qualifying_event": rookie.qualifying_event, "ppg_denominator_note": rookie.ppg_denominator_note,
            "evaluation_sha256": rookie.evaluation_sha256, "level_caveat": rookie.level_caveat,
            "level_bias_by_season": rookie.level_bias_by_season}),
        "board_target": board.model_dump(mode="json"),
        "outcome_artifact": outcome_artifact.identity() if outcome_artifact is not None else None,
        "current_census": None,
        "coverage": {"davids_roster": coverage_counts([t for t in term_sets if t.sleeper_id in mine],
                                                      absent=len(my_rec.absent_ids), outside=len(my_rec.outside_population)),
                     "league_rostered": coverage_counts(league_sets, absent=len(league_rec.absent_ids),
                                                        outside=len(league_rec.outside_population)),
                     "skill_universe": coverage_counts(term_sets)},
        "roster_reconciliation": {"davids_absent_ids": my_rec.absent_ids, "league_absent_ids": league_rec.absent_ids,
                                  "davids_outside_population": my_rec.outside_population,
                                  "league_outside_population": league_rec.outside_population,
                                  "davids_denominator": my_rec.denominator, "league_denominator": league_rec.denominator},
        "replacement_pool_census": pool,
        "fantasy_eligibility": eligibility_meta,
        "unforecast_eligible_census": unforecast_census,
        "comparable_views": ({f"h{short_view[3] + 1}": "comparable_board"} if short_view else
                             ({f"h{annual_h + 1}": "comparable_board"} if annual_h is not None else {}))
                            | ({f"h{horizon_view[3] + 1}": "horizon_board"} if horizon_view else {}),
        "model_comparisons": ({"legacy_annual_2y": "model_comparison_board"} if (short_view and annual_h is not None) else {}),
        "composition_consistency": consistency,
        "model_comparison_board": (None if not (short_view and annual_h is not None) else {
            "label": "Two-year impact from the legacy veteran model (shorter history; a different model, not a different horizon)",
            "n_comparable": comparable.readiness_counts.get("comparable", 0), "horizons_summed": annual_h + 1,
            "annual_producers": annual_meta, "readiness": comparable.readiness_counts,
            "davids_roster": [board_row(v, annual_by_pid.get(v.player_id)) for v in comparable.values if v.sleeper_id in mine],
            "league_rostered": [board_row(v, annual_by_pid.get(v.player_id)) for v in comparable.values if v.sleeper_id in rostered],
            "top": [board_row(v, annual_by_pid.get(v.player_id)) for v in comparable.ranked(comparable_only=True)[:60]],
            "all_inspectable": [board_row(v, annual_by_pid.get(v.player_id)) for v in comparable.values if v.readiness in ("comparable", "unverified")]}),
        "horizon_board": (None if horizon_view is None else {
            "n_comparable": horizon_view[0].readiness_counts.get("comparable", 0),
            "horizons_summed": horizon_view[3] + 1, "annual_producers": horizon_view[2],
            "readiness": horizon_view[0].readiness_counts,
            "davids_roster": [board_row(v, horizon_view[1].get(v.player_id), horizon_view[3]) for v in horizon_view[0].values if v.sleeper_id in mine],
            "league_rostered": [board_row(v, horizon_view[1].get(v.player_id), horizon_view[3]) for v in horizon_view[0].values if v.sleeper_id in rostered],
            "top": [board_row(v, horizon_view[1].get(v.player_id), horizon_view[3]) for v in horizon_view[0].ranked(comparable_only=True)[:60]],
            "all_inspectable": [board_row(v, horizon_view[1].get(v.player_id), horizon_view[3]) for v in horizon_view[0].values if v.readiness in ("comparable", "unverified")]}),
        "comparable_board": ({"n_comparable": short_view[0].readiness_counts.get("comparable", 0),
                              "horizons_summed": short_view[3] + 1, "annual_producers": short_view[2],
                              "readiness": short_view[0].readiness_counts,
                              "davids_roster": [board_row(v, short_view[1].get(v.player_id), short_view[3]) for v in short_view[0].values if v.sleeper_id in mine],
                              "league_rostered": [board_row(v, short_view[1].get(v.player_id), short_view[3]) for v in short_view[0].values if v.sleeper_id in rostered],
                              "top": [board_row(v, short_view[1].get(v.player_id), short_view[3]) for v in short_view[0].ranked(comparable_only=True)[:60]],
                              "all_inspectable": [board_row(v, short_view[1].get(v.player_id), short_view[3]) for v in short_view[0].values if v.readiness in ("comparable", "unverified")]}
                             if short_view else
                             {"n_comparable": comparable.readiness_counts.get("comparable", 0),
                              "horizons_summed": (annual_h + 1) if annual_h is not None else None,
                              "annual_producers": annual_meta,
                              "readiness": comparable.readiness_counts,
                              "davids_roster": [board_row(v, annual_by_pid.get(v.player_id))
                                                for v in comparable.values if v.sleeper_id in mine],
                              "league_rostered": [board_row(v, annual_by_pid.get(v.player_id))
                                                  for v in comparable.values if v.sleeper_id in rostered],
                              "top": [board_row(v, annual_by_pid.get(v.player_id))
                                      for v in comparable.ranked(comparable_only=True)[:60]],
                              "all_inspectable": [board_row(v, annual_by_pid.get(v.player_id))
                                                  for v in comparable.values if v.readiness in ("comparable", "unverified")]}),
        "davids_roster": roster_rows,
        "davids_best_lineup_served_h0": {"assignment": lineup_assignment, "total_ppg": lineup_total,
                                         "excluded_taxi_or_reserve": lineup_excluded,
                                         "scenario": "one week, active roster only, every active player at his served h=0 rate"},
        "dg176": dg176,
        "top_20_rebuild": [row_report(ts_by_sid[v.sleeper_id]) for v in results[lead].ranked()[:20]],
    }
    if census_binding is not None:
        main_board = report.get("horizon_board") or report.get("comparable_board") or {}
        has_estimate = {str(x["sleeper_id"]): (x.get("readiness") == "comparable")
                        for x in (main_board.get("all_inspectable") or []) if x.get("sleeper_id")}
        for x in (main_board.get("league_rostered") or []):
            if x.get("sleeper_id"):
                has_estimate[str(x["sleeper_id"])] = x.get("readiness") == "comparable"
        coverage = census_binding.coverage(has_estimate, owned_ids=rostered, positions=sorted(SKILL_POSITIONS))
        attachment = {}
        for m in main_board.get("annual_producers") or []:
            if m.get("model_version") == "union_replacement":
                for pos, refs in (m.get("replacement") or {}).items():
                    pid = refs[0].get("player_id")
                    sid = next((str(r.sleeper_id) for r in art.rows if str(r.player_id) == str(pid) or
                                (r.gsis_id and str(r.gsis_id) == str(pid))), None)
                    attachment[pos] = dict(census_binding.attachment(sid) if sid else
                                           {"status": "unverified", "basis": "absent", "note": "bar player has no Sleeper id in the artifact"},
                                           sleeper_id=sid)
        report["current_census"] = {**census_binding.to_json(), "coverage": coverage, "reference_attachment": attachment}
        report["provenance"]["census_run_id"] = census_binding.run_id
    (out / "report.json").write_text(json.dumps(report, indent=1, default=str))

    lines = [f"# DG-178 roster audit — run {stamp}, forecast date {forecast_date}", "",
             f"artifact {art.captured_at} sha {art_sha_start[:12]} (end {art_sha_end[:12]}); "
             f"snapshot {snapshot_id} sha {report['inputs']['snapshot']['sha256'][:12]}; "
             f"cells sha {cells.source_sha256[:12]}", "",
             f"league: {settings.name} {settings.season}, {settings.teams} teams, slots {settings.slots}, "
             f"full PPR={settings.full_ppr}, TE premium={settings.te_premium}", "",
             f"rookie candidate: {'none supplied — Engine A rows are stated blanks' if rookie is None else rookie.model_version + ' (' + str(rookie.seasons_covered) + ' seasons; csv sha ' + rookie.csv_sha256[:12] + ')'}", "",
             "replacement (best available, served rate, held constant):"]
    for pos, ref in replacement.items():
        lines.append(f"  {pos}: {ref.player_name} served {ref.rate_ppg:.3f} ppg, conditional {ref.conditional_rate_ppg:.3f}")
    lines += ["", "board target (typed): " + json.dumps(report["board_target"]), "",
              "coverage (numerical) and readiness (typed comparability), denominator = every roster id:"]
    for pop, cv in report["coverage"].items():
        lines.append(f"  {pop}: n={cv['denominator']} full={cv['full']} partial={cv['partial']} none={cv['none']} "
                     f"absent={cv['absent_from_artifact']} outside_population={cv['outside_skill_population']} | readiness {cv['readiness']}")
    if report["roster_reconciliation"]["league_outside_population"]:
        lines.append("  outside the skill population (artifact position): " + json.dumps(report["roster_reconciliation"]["league_outside_population"]))
    cb = report["comparable_board"]
    hb = report.get("horizon_board")
    if hb:
        lines += ["", f"longer-horizon board: {hb['n_comparable']} comparable on {hb['horizons_summed']} seasons; producers "
                      f"{[m['model_version'][:40] for m in hb['annual_producers'] if 'csv' in m]}; readiness {hb['readiness']}"]
        for m in hb["annual_producers"]:
            if "csv" in m:
                ev = m.get("evidence") or {}
                lines.append(f"  producer {m['model_version'][:50]}: evidence {'VERIFIED' if ev.get('verified') else 'UNVERIFIED'}")
                for k, n in (m.get("evidence_notes") or {}).items():
                    if k.endswith("season5") or k.endswith("season1"):
                        lines.append(f"    grading {k}: {n[:140]}")
    lines += ["", f"comparable-only board: {cb['n_comparable']} players can be ranked on the annual target today"
              + (f" ({cb['horizons_summed']} seasons summed; producers {[m['model_version'] for m in cb['annual_producers'] if 'csv' in m]}; readiness {cb['readiness']})" if cb["annual_producers"] else " (no annual producer file supplied)")]
    for m in cb["annual_producers"]:
        if m["model_version"] == "union_replacement":
            for pos, rr in m["replacement"].items():
                lines.append(f"  annual bar {pos}: {rr[0]['player_name']} R_1={rr[0]['rate_ppg']:.2f} ppg | pool complete={rr[0]['pool_complete']}"
                             + (f" | {rr[0]['pool_note']}" if rr[0]['pool_note'] else ""))
            if m["positions_without_a_bar"]:
                lines.append(f"  annual bar: no bar could be set at {m['positions_without_a_bar']}")
        elif "csv" in m:
            ev = m.get("evidence") or {}
            lines.append(f"  producer {m['model_version'][:50]}: evidence {'VERIFIED' if ev.get('verified') else 'UNVERIFIED'} — {ev.get('reason', '')[:160]}")
            for k, n in (m.get("evidence_notes") or {}).items():
                lines.append(f"    grading {k}: {n[:150]}")
    lines += ["",
              "", "replacement pool census (best SCORED available is not best OBTAINABLE):"]
    for pos, c in pool.items():
        lines.append(f"  {pos}: unrostered {c['unrostered']}, scored {c['scored']}, eligible {c['eligible']}, "
                     f"excluded unscored {c['excluded_unscored']} / clamped {c['excluded_clamped']} / no projection {c['excluded_no_projection']}")
    lines += ["",
              "David's roster (value = ppg-above-replacement season-equivalents; boards = posture|seasons, none is David's):"]
    for r in roster_rows:
        if r.get("coverage") == "absent_from_artifact":
            lines.append(f"  {r['sleeper_id']}: ABSENT FROM ARTIFACT")
            continue
        vals = " / ".join(f"{k.split(' ')[0]}{k.split('|')[1]} {v:.2f}" if v is not None else f"{k.split(' ')[0]}{k.split('|')[1]} —" for k, v in r["value"].items())
        lines.append(f"  {r['name'][:22]:22} {r['position']:2} served {str(r['served_dvs']):>6} {str(r['served_engine']):>4} | "
                     f"{r['coverage']:7} {r['readiness']:13} | {vals} | lineup gain {r.get('marginal_lineup_gain_ppg')} | {r['reason'] or ''}")
    if rookie is not None and rookie.level_caveat:
        lines += ["", f"rookie level caveat (on every rookie term): {rookie.level_caveat}"]
    lines += ["", "DG-176:"]
    for d in dg176:
        for r in d["rows"]:
            lines.append(f"  {d['name']}: {r['coverage']} — {r['reason']} (on David's roster: {d['on_davids_roster']})")
        if not d["found"]:
            lines.append(f"  {d['name']}: NOT FOUND in artifact")
    lines += ["", f"top 20 by {lead} — RESEARCH-ONLY inspection order (every value is research_only against the annual target):"]
    for i, r in enumerate(report["top_20_rebuild"], 1):
        lines.append(f"  {i:2d} {r['name'][:22]:22} {r['position']:2} {r['value'][lead]:.2f}")
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {out}/report.json and summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
