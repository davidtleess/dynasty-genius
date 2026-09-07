"""Reader for the AGREED annual target — one shape for both producers (DG-178 round 1).

Per player i and NFL season j (j = 1 is the forecast year, the contract's h = j - 1), a
producer exports on one event, appearance in season j:

    p_appear_year{j}                     P(A_j)
    e_points_year{j}_given_appear        E[REG PPR points | A_j]
    e_games_year{j}_given_appear         E[stat-row games | A_j]
    e_points_year{j}, e_games_year{j}    the unconditional pair, = p x conditional (0 when absent)

and the adapter builds the estimand

    C_ij = max(0, e_points_year{j} - R_j x e_games_year{j})

with R_j the replacement's expected REG points per stat-row game from the SAME producer's
unrostered rows. The file is typed from its manifest and refused if it is not the annual
target; the unconditional pair is checked against p x conditional on load, which is a
check that fails when a file has been edited by hand. Unresolved identities are a stated
absence, never 0.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Mapping, Optional, Union

from src.dynasty_genius.ranking.contract import (
    HorizonTerm,
    ProducerRef,
    ReplacementRef,
    ServedReference,
    TargetSpec,
    TermSet,
    annual_target,
    season_for_horizon,
)
from src.dynasty_genius.ranking.served_rows import ServedRow

RATE_QUANTITY = "expected_season_points_same_window"
POLICY_NAME = "best_available_expected_points"
# THE COUNTERFACTUAL (round 2). A season-long replace/retain comparison in ONE scoring
# window: signed margin = E[points_i] - E[points_ref], where the reference is the actual
# available player David's rule names. The sign chooses the ex-ante action (retain if the
# margin is positive, replace otherwise); the expected policy advantage is the positive part.
# The same player against himself is exactly 0. Two earlier forms were wrong for the same
# reason — they charged the focal player for his own games at a per-game or per-week rate
# while the reference's absences were free, so the named reference came out worth +58.61
# (Rattler) and +50.61 (Estime) against himself. This is a deliberately limited season-long
# policy, not optimal weekly substitution and not a championship probability.
REG_WEEKS = 17  # NFL team games in the regular season; informational, no longer a divisor
_REL_TOL = 1e-6


EVIDENCE_MEANING = ("source check: the scoring file, its history file and its evaluation file are the bytes the "
                    "manifest declares and describe one arm; this is file identity, not scientific validation "
                    "and not a statement about forecast accuracy")

HISTORY_FILE_NAMES = ("historical_predictions.csv", "out_of_time_predictions.csv")
EVALUATION_FILE_NAMES = ("results.json", "evaluation.json")


@dataclass(frozen=True)
class EvidenceRecord:
    """Affirmative identity of a producer's files, or the reason it could not be established.
    Verified means every declared byte matches: scoring CSV, history CSV and evaluation file."""
    verified: bool
    reason: str
    scoring_arm: Optional[str] = None
    graded_arm: Optional[str] = None
    declared_csv_sha256: Optional[str] = None
    bound_files: Optional[dict[str, str]] = None   # role -> file name whose bytes matched
    meaning: str = EVIDENCE_MEANING


@dataclass(frozen=True)
class EvaluationStatus:
    """A producer's own per-(position, season) historical evaluation status: how many outer
    folds were graded and what the producer's interval says, read from its machine-readable
    companion (lane 23481's <run>.evaluation_status.json or manifest.evaluation_status) only
    when that companion names the evaluation bytes read; or derived from a rookie
    evaluation.json's annual block. 'Evaluated' means the closed history sufficed to grade,
    never validated."""
    source: str
    positions: dict[str, dict[int, dict]]   # pos -> season j (1-based) -> {status, folds, improvement}
    meaning: dict[str, str]
    results_sha256: Optional[str] = None
    source_sha256: Optional[str] = None      # sha256 of the companion bytes read, so a report binds it

    def seasons(self) -> list[int]:
        return sorted({j for by_j in self.positions.values() for j in by_j})

    def per_season(self, j: int) -> dict[str, dict]:
        return {pos: by_j[j] for pos, by_j in sorted(self.positions.items()) if j in by_j}

    def season_summary(self, j: int) -> str:
        cells = self.per_season(j)
        if not cells:
            return "not evaluated: the producer reports no grading for this season"
        if all(c.get("status") == "no_evaluated_policy_fold" or not c.get("folds") for c in cells.values()):
            return "not evaluated: zero historical folds at every position"
        folds = max(int(c.get("folds") or 0) for c in cells.values())
        beats = [pos for pos, c in cells.items() if _improves(c.get("improvement"))]
        ungraded = [pos for pos, c in cells.items() if not c.get("folds")]
        point_only = all((c.get("improvement") or "").lower().startswith("rmse") for c in cells.values() if c.get("folds"))
        fold_word = "fold" if folds == 1 else "folds"
        if point_only:
            text = (f"evaluated on {folds} {fold_word}; RMSE below its training-only baseline at {len(beats)} of "
                    f"{len(cells)} positions (a point comparison, no interval)")
        else:
            text = (f"evaluated on {folds} {fold_word}; beats its training-only baseline within the 90% interval at "
                    f"{len(beats)} of {len(cells)} positions")
        if ungraded:
            text += f"; not graded at {', '.join(ungraded)}"
        if folds == 1:
            text += "; a single fold is not support"
        return text

    def to_json(self) -> dict:
        return {"source": self.source, "source_sha256": self.source_sha256, "results_sha256": self.results_sha256,
                "meaning": self.meaning,
                "seasons": {str(j): {"summary": self.season_summary(j), "positions": self.per_season(j)} for j in self.seasons()}}


def _improves(text: Optional[str]) -> bool:
    t = (text or "").lower()
    return t.startswith("within") or t.startswith("beats") or t.startswith("rmse below")


def _status_from_companion(doc: dict, source: str, source_sha256: Optional[str] = None) -> EvaluationStatus:
    positions: dict[str, dict[int, dict]] = {}
    for pos, by_year in (doc.get("positions") or {}).items():
        for key, cell in (by_year or {}).items():
            m = re.fullmatch(r"year(\d+)", str(key))
            if not m or not isinstance(cell, dict):
                continue
            positions.setdefault(str(pos).upper(), {})[int(m.group(1))] = {
                "status": cell.get("status"), "folds": int(cell.get("evaluated_folds") or 0),
                "improvement": cell.get("baseline_improvement"),
                "forecast_seasons_graded": cell.get("forecast_seasons_graded"),
                "calibration": {k: cell["calibration"].get(k) for k in ("ece", "reliability_slope", "n", "status")}
                if isinstance(cell.get("calibration"), dict) else None}
    meaning = {k: str(v) for k, v in (doc.get("meaning") or {}).items()}
    return EvaluationStatus(source=source, positions=positions, meaning=meaning, results_sha256=doc.get("results_sha256"),
                            source_sha256=source_sha256)


def _status_from_rookie_evaluation(res: dict, source: str) -> Optional[EvaluationStatus]:
    """Lane 24974's evaluation.json: annual["j"].e_points_year with forecast_years (one outer
    fold per forecast year) and by_position rmse against the training baseline."""
    annual = res.get("annual")
    if not isinstance(annual, dict):
        return None
    positions: dict[str, dict[int, dict]] = {}
    for key, block in annual.items():
        if not str(key).isdigit() or not isinstance(block, dict):
            continue
        j = int(key)
        ep = block.get("e_points_year") or {}
        folds = len(ep.get("forecast_years") or (block.get("p_qual_year") or {}).get("forecast_years") or [])
        by_pos = ep.get("by_position") if isinstance(ep.get("by_position"), dict) else {}
        pooled_ok = (ep.get("rmse") is not None and ep.get("rmse_training_baseline") is not None
                     and float(ep["rmse"]) < float(ep["rmse_training_baseline"]))
        for pos, cell in (by_pos or {"ALL": {}}).items():
            if isinstance(cell, dict) and cell.get("rmse") is not None and cell.get("rmse_training_baseline") is not None:
                improvement = ("rmse below training baseline (point comparison, no interval)"
                               if float(cell["rmse"]) < float(cell["rmse_training_baseline"]) else
                               "rmse not below training baseline")
            else:
                improvement = ("rmse below training baseline, pooled across positions (point comparison, no interval)"
                               if pooled_ok else "rmse not below training baseline (pooled)")
            positions.setdefault(str(pos).upper(), {})[j] = {"status": "evaluated" if folds else "no_evaluated_policy_fold",
                                                              "folds": folds, "improvement": improvement}
    if not positions:
        return None
    return EvaluationStatus(source=source, positions=positions,
                            meaning={"evaluated": "one outer fold per forecast year with cutoffs enforced; the policy "
                                                  "menu was refined after inspecting these years, so this is not "
                                                  "untouched independent confirmation",
                                     "improvement": "a point comparison of RMSE against the training-only baseline"})


@dataclass(frozen=True)
class AnnualRow:
    player_id: str
    sleeper_id: Optional[str]
    gsis_id: str
    name: str
    position: str
    identity_status: str
    p_appear: tuple[float, ...]
    e_points_given: tuple[float, ...]
    e_games_given: tuple[float, ...]
    e_points: tuple[float, ...]
    e_games: tuple[float, ...]
    draft_season: Optional[int] = None
    pick: Optional[int] = None

    @property
    def resolved(self) -> bool:
        return self.identity_status == "resolved" and len(self.p_appear) > 0

    def rate_given_appear(self, j: int) -> float:
        return self.e_points_given[j] / self.e_games_given[j]

    def expected_season_points(self, j: int) -> float:
        return self.e_points[j]


def _first(m: dict, *paths: str):
    """The first present value among dotted paths (`units.scoring_scope`, `scoring_scope`)."""
    for path in paths:
        node = m
        ok = True
        for part in path.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                ok = False
                break
        if ok and node not in (None, ""):
            return node
    return None


def _typed(field: str, raw, table: dict[str, str]) -> str:
    """Map a producer's literal or prose onto a typed value with a CLOSED table; anything
    the table does not recognise is refused, never guessed."""
    if raw is None:
        raise ValueError(f"manifest does not state {field}")
    text = str(raw).strip()
    if text in table.values():
        return text
    low = text.lower()
    for needle, value in table.items():
        if needle in low:
            return value
    raise ValueError(f"manifest {field} {text!r} is not a recognised value for the typed contract")


_SCOPE = {"all_games": "ALL_GAMES", "all games": "ALL_GAMES", "postseason included": "ALL_GAMES",
          "reg": "REG", "regular season": "REG", "regular-season": "REG"}
# Positive identifiers only. Scoring is read from fields that STATE scoring; a denominator
# note is never consulted, because prose there can negate ("NOT the served all-games ...").
_SCORING = {"nflverse_default_ppr_championship_window_v1": "PPR_nflverse_default",
            "nflverse default-ppr league window": "PPR_nflverse_default",
            "nflverse_default_ppr": "PPR_nflverse_default", "ppr_nflverse_default": "PPR_nflverse_default",
            "nflverse-default-ppr": "PPR_nflverse_default",
            "ppr_nflverse_weekly": "PPR_nflverse_weekly", "fantasy_points_ppr": "PPR_nflverse_weekly",
            "nflverse weekly": "PPR_nflverse_weekly"}
EXPOSURE_IN_WINDOW = "unique stat_record weeks within the outcome window"
_EXPOSURE = {"unique stat_record weeks within the outcome window": "stat_record_weeks_in_window",
             "stat_record_weeks_in_window": "stat_record_weeks_in_window",
             "stat_row_games": "stat_row_games", "weekly stat row": "stat_row_games", "stat-row game": "stat_row_games",
             "stat row": "stat_row_games", "all_games": "all_games", "all games": "all_games"}
_EVENT = {"appearance": "appearance", "appear": "appearance", "stat row": "appearance", "stat-row game": "appearance"}


def _labels_through(m: dict) -> int:
    """The last season whose labels the producer saw, from a label-window statement or the
    last completed season. Refused if absent: a forecast with no stated vintage cannot be
    checked against anything."""
    for path in ("labels_through", "forecast_date.labels_through", "label_window", "forecast_date.label_window"):
        raw = _first(m, path)
        if isinstance(raw, (str, int)):
            years = re.findall(r"\b(?:19|20)\d{2}\b", str(raw))
            if years:
                return int(years[0])
    last = _first(m, "last_completed_season", "last_complete_season", "forecast_date.last_completed_season",
                  "forecast_cutoff.feature_season", "forecast_date.last_complete_season")
    if last is not None:
        return int(last)
    raise ValueError("manifest does not state the label window (labels_through)")


_WINDOW = {"championship_week17": "championship_week17", "week17_championship": "championship_week17",
           "david_week17": "championship_week17", "all_reg_weeks": "all_reg_weeks", "all_reg": "all_reg_weeks",
           "regular season": "all_reg_weeks", "full regular season": "all_reg_weeks"}


CHAMPIONSHIP_PRESET = "nflverse_default_ppr_championship_window_v1"


def _outcome_block(m: dict) -> Optional[dict]:
    """The producer's binding to the shared outcome artifact: lane 24974 writes it under
    `outcomes` (plural), the provisional name was `outcome`; the actual file wins."""
    for key in ("outcomes", "outcome"):
        o = m.get(key)
        if isinstance(o, dict) and o:
            return o
    return None


def _window(m: dict) -> str:
    """The week window a file's season totals were summed over. An explicit window key is
    typed through the closed table (refused when unknown); otherwise a binding to the shared
    artifact whose scoring preset is the championship preset IS the championship window;
    otherwise the full regular season the first producer files used (a stated default)."""
    raw = _first(m, "window_id", "window.id", "window", "outcome.window.id", "outcome.window", "outcomes.window.id",
                 "label_window.id")
    if isinstance(raw, dict):
        raw = raw.get("id")
    if raw is not None:
        return _typed("window", raw, _WINDOW)
    o = _outcome_block(m)
    if o is not None and (o.get("scoring_preset") == CHAMPIONSHIP_PRESET or _first(m, "units.scoring_preset") == CHAMPIONSHIP_PRESET):
        return "championship_week17"
    return "all_reg_weeks"


def _outcome_identity(m: dict) -> Optional[dict]:
    """The SHARED outcome artifact a producer's file was labelled on (DG-179): its name, byte
    hashes, scoring id, window and closure, read from ``manifest.outcome``. None when the
    manifest binds no outcome artifact (the first producer files) — stated, never invented."""
    o = _outcome_block(m)
    if o is None:
        return None
    window = _first(o, "window.id", "window")
    if isinstance(window, dict):
        window = window.get("id")
    if window is None and o.get("scoring_preset") == CHAMPIONSHIP_PRESET:
        window = "championship_week17"
    coverage = _first(o, "coverage_status", "coverage.status", "coverage")
    closure = _first(o, "last_complete_season", "labels_through", "closure.labels_through", "closure")
    if closure is None and isinstance(o.get("covered_seasons"), list) and o["covered_seasons"]:
        closure = max(int(x) for x in o["covered_seasons"])
    return {
        # DG-179's own names first (schema dg179_league_season_outcomes_v1); provisional aliases second.
        "artifact": _first(o, "artifact", "csv", "file"),
        "outcomes_csv_sha256": _first(o, "outcomes_csv_sha256", "csv_sha256", "declared_outputs.outcomes.csv.sha256",
                                      "outputs.outcomes.csv.sha256", "sha256"),
        "manifest_sha256": _first(o, "manifest_sha256"),
        "target_identity": _first(o, "target_identity"),
        "scoring_identity": _first(o, "scoring_identity"),
        "window_identity": _first(o, "window_identity"),
        "scoring_preset": _first(o, "scoring_preset", "scoring_id", "scoring"),
        "window": _typed("window", window, _WINDOW) if window is not None else None,
        "last_complete_season": int(closure) if isinstance(closure, (int, float, str)) and str(closure).isdigit() else closure,
        # The artifact's coverage_status, read as a RESEARCH qualification: only DG-179's
        # 'qualified_research_game_complete_identified_rows' is affirmative; a download, a calendar
        # check, or a provisional word is not, and never becomes 'complete individual data'.
        "coverage_status": str(coverage) if isinstance(coverage, str) else None,
    }


AFFIRMATIVE_COVERAGE = frozenset({"qualified_research_game_complete_identified_rows"})


def assert_one_outcome_identity(candidates) -> Optional[dict]:
    """Every producer composed together must be labelled on the SAME outcome artifact: same
    hashes, scoring id, window and closure. A binding beside no binding is a mix too."""
    from src.dynasty_genius.ranking.outcome_artifact import (
        CORE_BINDING_FIELDS,
        bindings_disagree,
    )

    cands = list(candidates)
    ids = [c.outcome_identity for c in cands]
    if not ids:
        return None
    if all(i is None for i in ids):
        return None  # the first producer files: no artifact bound on either side, stated as such
    first = ids[0]
    for c, other in zip(cands[1:], ids[1:]):
        bad = bindings_disagree(first, other)
        if bad:
            detail = "; ".join(f"{x.model_version}: {({k: (x.outcome_identity or {}).get(k) for k in CORE_BINDING_FIELDS} if x.outcome_identity else None)}"
                               for x in cands)
            raise ValueError(f"producers are labelled on different outcome artifacts and cannot be composed together "
                             f"({', '.join(bad)} differ or missing): {detail}")
    return first


def _spec_from_manifest(m: dict) -> TargetSpec:
    o = _outcome_block(m) or {}
    bound_preset = o.get("scoring_preset") or _first(m, "units.scoring_preset")
    if bound_preset == CHAMPIONSHIP_PRESET:
        # a binding to the shared artifact fixes scope, scoring and exposure by construction
        scope, scoring = "REG", "PPR_nflverse_default"
        exposure = _typed("exposure", o.get("exposure_definition") or _first(m, "exposure_definition", "units.exposure_definition")
                          or EXPOSURE_IN_WINDOW, _EXPOSURE)
    else:
        scope = _typed("scoring_scope", _first(m, "scoring_scope.scope", "scoring_scope", "units.scoring_scope"), _SCOPE)
        scoring = _typed("scoring", _first(m, "scoring", "scoring_scope.scoring", "units.scoring", "units.scoring_scope"), _SCORING)
        exposure = _typed("exposure", _first(m, "exposure_definition", "units.exposure_definition"), _EXPOSURE)
    event = _typed("event", _first(m, "event", "definitions.appearance"), _EVENT)
    return TargetSpec(scope=scope, scoring=scoring, window=_window(m), exposure=exposure, event=event,
                      clock="per_season", quantity="season_points", labels_through=_labels_through(m))


_POSITIONS = ("QB", "RB", "WR", "TE")


def _note(model_rmse: float, base_rmse: float, bias: Optional[float] = None, pooled: bool = False) -> str:
    verdict = "beats" if model_rmse < base_rmse else "does not beat"
    text = (f"{verdict} the training-only baseline on unconditional points "
            f"(out-of-time RMSE {model_rmse:.1f} vs {base_rmse:.1f}")
    if bias is not None:
        text += f", bias {bias:+.1f} = mean predicted minus actual"
    return text + (", pooled across positions)" if pooled else ")")


def _evidence_notes(results: dict, arm: Optional[str]) -> dict[tuple[str, int], str]:
    """Per (position, season j): the producer's own out-of-time grading of unconditional points
    against its training-only baseline. Two file shapes are read; cells a file does not grade
    get no note.

    * lane 23481: results.historical[pos][year{j}][arm].pooled.points_unconditional.{model,baseline}.rmse
    * lane 24974: evaluation.annual["j"].e_points_year.{rmse, rmse_training_baseline, bias, by_position}
    """
    out: dict[tuple[str, int], str] = {}
    annual = results.get("annual")
    if isinstance(annual, dict):
        for jkey, block in annual.items():
            if not str(jkey).isdigit() or not isinstance(block, dict):
                continue
            j = int(jkey)
            cell = block.get("e_points_year") or {}
            pooled_ok = cell.get("rmse") is not None and cell.get("rmse_training_baseline") is not None
            for pos in _POSITIONS:
                bp = (cell.get("by_position") or {}).get(pos) or {}
                if bp.get("rmse") is not None and bp.get("rmse_training_baseline") is not None:
                    out[(pos, j)] = _note(bp["rmse"], bp["rmse_training_baseline"], bp.get("bias"))
                elif pooled_ok:
                    out[(pos, j)] = _note(cell["rmse"], cell["rmse_training_baseline"], cell.get("bias"), pooled=True)
        return out
    hist = results.get("historical") or {}
    for pos, years in hist.items():
        if not isinstance(years, dict):
            continue
        for ykey, cell_or_arms in years.items():
            mm = re.fullmatch(r"year(\d+)", str(ykey))
            if not mm or not isinstance(cell_or_arms, dict):
                continue
            j = int(mm.group(1))
            folds: Optional[int] = None
            pooled = cell_or_arms.get("pooled")
            if isinstance(pooled, dict) and isinstance(pooled.get("policy"), dict):
                # round-2 shape: the selection POLICY's grade sits under pooled.policy
                pu = pooled["policy"].get("points_unconditional") or {}
                seasons = cell_or_arms.get("evaluated_test_seasons")
                folds = len(seasons) if isinstance(seasons, list) else None
            else:
                cell = cell_or_arms.get(arm) if arm else (next(iter(cell_or_arms.values())) if len(cell_or_arms) == 1 else None)
                if not isinstance(cell, dict):
                    continue
                pu = ((cell.get("pooled") or {}).get("points_unconditional") or {})
                seasons = cell.get("evaluated_test_seasons")
                folds = len(seasons) if isinstance(seasons, list) else None
            model_rmse = (pu.get("model") or {}).get("rmse")
            base_rmse = (pu.get("baseline") or {}).get("rmse")
            if model_rmse is None or base_rmse is None:
                continue
            note = _note(model_rmse, base_rmse)
            if folds is not None:
                note += "; graded on ONE fold" if folds == 1 else f"; graded on {folds} folds"
            out[(str(pos).upper(), j)] = note
    return out


def _num(v: Optional[str]) -> Optional[float]:
    if v is None or str(v).strip() == "":
        return None
    return float(v)


class AnnualCandidate:
    def __init__(self, csv_path: Path, manifest_path: Path, csv_sha256: str, manifest_sha256: str,
                 model_version: str, forecast_year: int, spec: TargetSpec, seasons: int,
                 rows: dict[str, AnnualRow], evidence_notes: Optional[dict[tuple[str, int], str]] = None,
                 results_sha256: Optional[str] = None, grading_arm_note: Optional[str] = None,
                 evidence: Optional[EvidenceRecord] = None,
                 evaluation_status: Optional[EvaluationStatus] = None,
                 evaluation_status_note: Optional[str] = None,
                 outcome_identity: Optional[dict] = None) -> None:
        self.csv_path, self.manifest_path = csv_path, manifest_path
        self.csv_sha256, self.manifest_sha256 = csv_sha256, manifest_sha256
        self.model_version, self.forecast_year, self.spec, self.seasons = model_version, forecast_year, spec, seasons
        # (position, NFL season j) -> the producer's own out-of-time grading of unconditional
        # points against its training-only baseline. Derived from its results file, never prose.
        self.evidence_notes: dict[tuple[str, int], str] = evidence_notes or {}
        self.results_sha256 = results_sha256
        # Set when the grading file describes a different arm than the scoring file.
        self.grading_arm_note = grading_arm_note
        self.evidence = evidence or EvidenceRecord(False, "unverified: no evidence record built")
        # The producer's own per-season historical evaluation status (round 3): separate from
        # file identity. None when no bound companion or derivable block exists.
        self.evaluation_status = evaluation_status
        self.evaluation_status_note = evaluation_status_note
        # The shared outcome artifact this file was labelled on (None for the first files).
        self.outcome_identity = outcome_identity
        self._rows = rows
        self._by_sleeper = {r.sleeper_id: r for r in rows.values() if r.sleeper_id}
        # Pick number is unique within a draft year; position is an attribute (it can differ
        # between the draft table and the current roster), never part of the key.
        self._by_pick = {(r.draft_season, r.pick): r for r in rows.values()
                         if r.draft_season is not None and r.pick is not None}
        self._by_gsis = {r.gsis_id: r for r in rows.values() if r.gsis_id}

    @classmethod
    def load(cls, csv_path: Path | str, manifest_path: Path | str,
             results_path: Optional[Path | str] = None, window: str = "all_reg_weeks") -> "AnnualCandidate":
        """``window`` is the BOARD's week window; a file summed over another window is a
        different target and is refused here, never rescaled or mixed."""
        csv_p, man_p = Path(csv_path), Path(manifest_path)
        csv_bytes, man_bytes = csv_p.read_bytes(), man_p.read_bytes()
        m = json.loads(man_bytes)
        from src.dynasty_genius.ranking.grading import (
            _graded_arm,
            _scoring_arm,
            rookie_arm_consistency,
        )

        notes: dict[tuple[str, int], str] = {}
        results_sha: Optional[str] = None
        arm_note: Optional[str] = None
        csv_sha = hashlib.sha256(csv_bytes).hexdigest()
        # Evidence identity, fail closed: the manifest must declare the scoring arm AND the
        # sha256 of the CSV it describes; the grading file must name the arm it graded; the
        # arms must agree; the declared hash must match the bytes read.
        problems: list[str] = []
        scoring_arm = _scoring_arm(m)
        if scoring_arm is None:
            problems.append("manifest names no scoring arm (scoring_arm_id / model_policy / candidate_arm)")
        declared = None
        outputs = m.get("outputs_sha256")
        if isinstance(outputs, dict):
            declared = outputs.get(csv_p.name) or next((v for k, v in outputs.items() if str(k).endswith(csv_p.name)), None)
        if declared is None:
            problems.append("manifest declares no sha256 for the scoring CSV (outputs_sha256)")
        elif str(declared).lower() != csv_sha:
            problems.append(f"declared sha256 for {csv_p.name} does not match the bytes read")
        graded_arm = None
        bound: dict[str, str] = {}
        if declared is not None and str(declared).lower() == csv_sha:
            bound["scoring"] = csv_p.name
        outputs_map = outputs if isinstance(outputs, dict) else {}
        # Round 3: bind the HISTORY bytes and the EVALUATION bytes, not the scoring CSV alone.
        hist_declared = [(k, v) for k, v in outputs_map.items() if str(k) in HISTORY_FILE_NAMES]
        if not hist_declared:
            problems.append("manifest declares no sha256 for a history file (historical_predictions.csv / out_of_time_predictions.csv)")
        else:
            hname, hsha = hist_declared[0]
            hpath = csv_p.parent / hname
            if not hpath.exists():
                problems.append(f"declared history file {hname} is not beside the scoring CSV")
            elif hashlib.sha256(hpath.read_bytes()).hexdigest() != str(hsha).lower():
                problems.append(f"declared sha256 for the history file {hname} does not match the bytes read")
            else:
                bound["history"] = hname
        evaluation_status: Optional[EvaluationStatus] = None
        evaluation_status_note: Optional[str] = None
        if results_path is not None:
            res_p = Path(results_path)
            res_bytes = res_p.read_bytes()
            results_sha = hashlib.sha256(res_bytes).hexdigest()
            res = json.loads(res_bytes)
            notes = _evidence_notes(res, _first(m, "candidate_arm"))
            graded_arm = _graded_arm(res, expected=scoring_arm)
            ok, why = rookie_arm_consistency(m, res)
            if not ok:
                arm_note = why
                problems.append(why)
                if scoring_arm is not None and graded_arm is not None:  # two known arms that disagree
                    notes = {k: f"GRADING OF A DIFFERENT ARM: {why}; {v}" for k, v in notes.items()}
            ev_declared = outputs_map.get(res_p.name) or next((v for k, v in outputs_map.items()
                                                               if str(k) in EVALUATION_FILE_NAMES), None)
            if ev_declared is None:
                problems.append(f"manifest declares no sha256 for the evaluation file {res_p.name}")
            elif str(ev_declared).lower() != results_sha:
                problems.append(f"declared sha256 for the evaluation file {res_p.name} does not match the bytes read")
            else:
                bound["evaluation"] = res_p.name
            # The producer's own per-season evaluation status, bound to the evaluation bytes.
            companion = csv_p.parent.parent / f"{csv_p.parent.name}.evaluation_status.json"
            status_doc = None
            status_sha = None
            if companion.exists():
                companion_bytes = companion.read_bytes()
                status_doc, status_src = json.loads(companion_bytes), str(companion)
                status_sha = hashlib.sha256(companion_bytes).hexdigest()
            elif isinstance(m.get("evaluation_status"), dict) and m["evaluation_status"].get("positions"):
                status_doc, status_src = m["evaluation_status"], f"{man_p.name}#evaluation_status"
            if status_doc is not None:
                if str(status_doc.get("results_sha256") or "").lower() == results_sha:
                    evaluation_status = _status_from_companion(status_doc, status_src, status_sha)
                else:
                    evaluation_status_note = (f"evaluation status companion {status_src} names results sha "
                                              f"{str(status_doc.get('results_sha256'))[:12]}, not the evaluation bytes read; ignored")
            else:
                evaluation_status = _status_from_rookie_evaluation(res, f"{res_p.name}#annual")
                if evaluation_status is None:
                    evaluation_status_note = "no per-season evaluation status: no companion file and no annual block"
        else:
            problems.append("no grading file supplied")
        outcome_id = _outcome_identity(m)
        if outcome_id is not None and (outcome_id.get("coverage_status") or "").lower() not in AFFIRMATIVE_COVERAGE:
            problems.append("the shared outcome artifact's coverage is not affirmatively stated as verified/complete "
                            f"(coverage_status={outcome_id.get('coverage_status')!r}); a download is not coverage")
        evidence = EvidenceRecord(verified=not problems,
                                  reason=("verified: scoring, history and evaluation bytes match their declared sha256 "
                                          "and describe one arm" if not problems
                                          else "unverified: " + "; ".join(problems)),
                                  scoring_arm=scoring_arm, graded_arm=graded_arm,
                                  declared_csv_sha256=str(declared) if declared else None,
                                  bound_files=bound)
        spec = _spec_from_manifest(m)
        forecast_year = int(_first(m, "forecast_year", "forecast_date.forecast_year") or spec.labels_through + 1)
        model_version = _first(m, "model_version")
        if model_version is None:
            producer = _first(m, "producer")
            if producer is None:
                raise ValueError("manifest names neither model_version nor producer")
            arm = _first(m, "candidate_arm")
            model_version = f"{producer}:{arm}" if arm else str(producer)
        target = annual_target(date(forecast_year, 9, 1), window=window)  # type: ignore[arg-type]
        diffs = spec.mismatches(target)
        if diffs:
            raise ValueError(f"{man_p} is not the annual target for forecast year {forecast_year}: "
                             f"{', '.join(diffs)} differ ({', '.join(f'{f}={getattr(spec, f)!r}' for f in diffs)})")
        rows: dict[str, AnnualRow] = {}
        seasons_seen: set[int] = set()
        with csv_p.open(newline="") as fh:
            for rec in csv.DictReader(fh):
                js = sorted(int(mm.group(1)) for k in rec for mm in [re.fullmatch(r"p_appear_year(\d+)", k)] if mm)
                status = (rec.get("identity_status") or "resolved").strip()
                cols = {}
                for name in ("p_appear_year{j}", "e_points_year{j}_given_appear", "e_games_year{j}_given_appear",
                             "e_points_year{j}", "e_games_year{j}"):
                    cols[name] = [_num(rec.get(name.format(j=j))) for j in js]
                present = [v for vs in cols.values() for v in vs]
                if status != "resolved" or all(v is None for v in present):
                    upid = rec.get("player_id") or rec.get("sleeper_id") or rec.get("gsis_id") or rec.get("name")
                    row = AnnualRow(upid,
                                    rec.get("sleeper_id") or None, rec.get("gsis_id") or "", rec.get("name") or upid,
                                    rec["position"].upper(), status if status else "unresolved",
                                    (), (), (), (), (),
                                    draft_season=int(rec["draft_season"]) if rec.get("draft_season") else None,
                                    pick=int(rec["pick"]) if rec.get("pick") else None)
                    rows[row.player_id] = row
                    continue
                if any(v is None or not math.isfinite(v) for v in present):
                    raise ValueError(f"{rec.get('name')}: a resolved row carries a missing or non-finite quantity")
                p, epg, egg, ep, eg = (cols["p_appear_year{j}"], cols["e_points_year{j}_given_appear"],
                                       cols["e_games_year{j}_given_appear"], cols["e_points_year{j}"],
                                       cols["e_games_year{j}"])
                for j, (pj, epgj, eggj, epj, egj) in enumerate(zip(p, epg, egg, ep, eg), start=1):
                    if not 0.0 <= pj <= 1.0:
                        raise ValueError(f"{rec.get('name')}: p_appear_year{j}={pj} is not a probability")
                    if eggj <= 0:
                        raise ValueError(f"{rec.get('name')}: e_games_year{j}_given_appear must be positive")
                    for label, got, want in (("e_points", epj, pj * epgj), ("e_games", egj, pj * eggj)):
                        if abs(got - want) > _REL_TOL * max(1.0, abs(want)):
                            raise ValueError(f"{rec.get('name')}: {label}_year{j}={got} is not p_appear x conditional "
                                             f"({pj} x {want / pj if pj else 0.0} = {want})")
                pid = rec.get("player_id") or rec.get("sleeper_id") or rec.get("gsis_id")
                gsis = rec.get("gsis_id") or (pid if re.fullmatch(r"00-\d{7}", str(pid or "")) else "")
                row = AnnualRow(pid,
                                rec.get("sleeper_id") or None, gsis, rec.get("name") or pid,
                                rec["position"].upper(), "resolved",
                                tuple(p), tuple(epg), tuple(egg), tuple(ep), tuple(eg),
                                draft_season=int(rec["draft_season"]) if rec.get("draft_season") else None,
                                pick=int(rec["pick"]) if rec.get("pick") else None)
                if row.player_id in rows:
                    raise ValueError(f"duplicate player_id {row.player_id} in {csv_p}")
                rows[row.player_id] = row
                seasons_seen.add(len(js))
        if len(seasons_seen) > 1:
            raise ValueError(f"rows reach different numbers of seasons: {sorted(seasons_seen)}")
        seasons = int(m.get("seasons") or (seasons_seen.pop() if seasons_seen else 0))
        return cls(csv_p, man_p, csv_sha, hashlib.sha256(man_bytes).hexdigest(),
                   str(model_version), forecast_year, spec, seasons, rows, notes, results_sha, arm_note, evidence,
                   evaluation_status, evaluation_status_note, outcome_id)

    def get(self, *, sleeper_id: Optional[str] = None, player_id: Optional[str] = None,
            position: Optional[str] = None, draft_season: Optional[int] = None,
            pick: Optional[int] = None, gsis_id: Optional[str] = None) -> Optional[AnnualRow]:
        """Sleeper id first, then gsis, then the producer's player_id, then (draft season, pick)
        — unique within a draft year; the only key the served artifact and a rookie file share."""
        if sleeper_id is not None and str(sleeper_id) in self._by_sleeper:
            return self._by_sleeper[str(sleeper_id)]
        if gsis_id is not None and str(gsis_id) in self._by_gsis:
            return self._by_gsis[str(gsis_id)]
        if player_id is not None and str(player_id) in self._rows:
            return self._rows[str(player_id)]
        if draft_season is not None and pick is not None:
            return self._by_pick.get((int(draft_season), int(pick)))
        return None

    def rows(self) -> Iterable[AnnualRow]:
        return self._rows.values()


def _resolve_sleeper_id(row: AnnualRow, by_sleeper: dict, by_player: dict, by_pick: dict,
                        by_gsis: Optional[dict] = None) -> Optional[str]:
    by_gsis = by_gsis or {}
    """The artifact's Sleeper id for a producer row: direct, by the producer's player_id,
    or by (position, draft_season, pick). None when the artifact does not know him."""
    if row.sleeper_id and str(row.sleeper_id) in by_sleeper:
        return str(row.sleeper_id)
    if row.gsis_id and row.gsis_id in by_gsis:
        return by_gsis[row.gsis_id]
    if row.player_id in by_player:
        return by_player[row.player_id]
    if row.draft_season is not None and row.pick is not None:
        return by_pick.get((row.draft_season, row.pick))
    return None


def annual_replacement(candidates, rostered_ids: set[str], snapshot_id: str, band: int = 1,
                       positions: Optional[Iterable[str]] = None,
                       served_rows: Optional[Iterable[ServedRow]] = None,
                       unforecast_eligible: Optional[Mapping[str, Union[int, Mapping]]] = None) -> dict[str, list[ReplacementRef]]:
    """David's rule on the annual quantities, over the UNION of the producers' rows: at each
    position the best player nobody owns, ranked by unconditional expected season points in
    the forecast year (availability inside). The reference quantity for season j is HIS
    expected season points in that season, same scoring window — the season-long
    replace/retain counterfactual subtracts it whole. One ReplacementRef per season; his
    conditional per-game rate rides along as conditional_rate_ppg for the reader.

    Who is "nobody's" is decided on the artifact's Sleeper id, resolved through
    ``served_rows``; a producer row the artifact cannot identify is left out of the pool and
    counted. The pool is COMPLETE only if every unrostered player the artifact scores at the
    position is forecast by some producer; otherwise the bar is flagged and no comparable
    value is built on it.

    Round 3: the bar is the best among players WITH a forecast. ``unforecast_eligible`` is the
    eligible census per position — how many eligible unrostered players no producer forecast
    (an int, or {"count": n, "reasons": {...}}) — and travels with the reference so the copy
    states the scope; without a census the count is unknown, never zero.
    """
    if band < 1:
        raise ValueError("band must be >= 1")
    cands = list(candidates) if isinstance(candidates, (list, tuple)) else [candidates]
    assert_one_outcome_identity(cands)
    rostered = {str(x) for x in rostered_ids}
    served = list(served_rows or [])
    by_sleeper = {str(r.sleeper_id): r for r in served if r.sleeper_id is not None}
    by_player = {str(r.player_id): str(r.sleeper_id) for r in served if r.sleeper_id is not None}
    by_pick = {(r.draft_class, r.nfl_draft_pick): str(r.sleeper_id) for r in served
               if r.sleeper_id is not None and r.draft_class is not None and r.nfl_draft_pick is not None}
    by_gsis = {r.gsis_id: str(r.sleeper_id) for r in served if r.sleeper_id is not None and r.gsis_id}
    seasons = min(c.seasons for c in cands)
    all_rows = [(c, r) for c in cands for r in c.rows() if r.resolved]

    def current_position(r: AnnualRow) -> str:
        """The artifact's (Sleeper's) current position when the row resolves; the producer's
        otherwise. Position is an attribute that can differ between sources, never a key."""
        sid = _resolve_sleeper_id(r, by_sleeper, by_player, by_pick, by_gsis) if served else None
        return by_sleeper[sid].position if sid and sid in by_sleeper else r.position

    wanted = sorted(positions) if positions is not None else sorted({current_position(r) for _, r in all_rows})
    out: dict[str, list[ReplacementRef]] = {}
    for pos in wanted:
        pool, unidentified, covered_sids = [], 0, set()
        for c, r in all_rows:
            if current_position(r) != pos:
                continue
            sid = _resolve_sleeper_id(r, by_sleeper, by_player, by_pick, by_gsis) if served else (str(r.sleeper_id) if r.sleeper_id else None)
            if sid is None and served:
                unidentified += 1
                continue
            if sid is not None:
                covered_sids.add(sid)
            if sid in rostered or str(r.player_id) in rostered:
                continue
            pool.append(r)
        # completeness: every scored unrostered artifact player at this position must be forecast
        missing = [s for s in served if s.position == pos and s.served_rate_ppg is not None
                   and str(s.sleeper_id) not in rostered and str(s.sleeper_id) not in covered_sids]
        complete = not missing
        note = None if complete else (f"replacement pool incomplete: producers forecast none of {len(missing)} scored "
                                      f"unrostered {pos} (e.g. {missing[0].full_name})" if len(missing) == 1 else
                                      f"replacement pool incomplete: {len(missing)} scored unrostered {pos} not forecast "
                                      f"by any producer (e.g. {missing[0].full_name})")
        if unidentified:
            note = (note + "; " if note else "") + f"{unidentified} producer row(s) not identifiable in the artifact"
        census = (unforecast_eligible or {}).get(pos) if unforecast_eligible is not None else None
        if unforecast_eligible is None:
            n_unforecast, reasons, census_complete = None, None, None
            note = (note + "; " if note else "") + "eligible census not supplied: eligible unrostered players without a forecast are uncounted"
        else:
            if isinstance(census, Mapping):
                n_unforecast = int(census.get("count") or 0)
                reasons = {str(k): int(v) for k, v in (census.get("reasons") or {}).items()} or None
            else:
                n_unforecast, reasons = int(census or 0), None
            census_complete = n_unforecast == 0
            if n_unforecast:
                why = (" (" + ", ".join(f"{v} {k}" for k, v in sorted(reasons.items(), key=lambda kv: -kv[1])[:3]) + ")"
                       if reasons else "")
                note = (note + "; " if note else "") + (f"best among players with a forecast; {n_unforecast} eligible unrostered "
                                                        f"{pos} have no forecast{why} and may change the reference")
        if len(pool) < band:
            continue  # no bar can be set at this position; the caller sees the position missing
        ranked = sorted(pool, key=lambda r: r.e_points[0], reverse=True)
        top = ranked[:band]
        runner = ranked[band] if len(ranked) > band else None
        series = [sum(r.expected_season_points(j) for r in top) / len(top) for j in range(seasons)]
        runner_up = None
        sensitivity = None
        if runner is not None and band == 1:
            r_sid = _resolve_sleeper_id(runner, by_sleeper, by_player, by_pick, by_gsis) if served else None
            r_name = (by_sleeper[r_sid].full_name if r_sid and r_sid in by_sleeper and by_sleeper[r_sid].full_name else runner.name)
            r_series = [runner.expected_season_points(j) for j in range(seasons)]
            runner_up = {"player_id": runner.player_id, "name": r_name, "expected_points_by_season": r_series,
                         "season1_gap": series[0] - r_series[0]}
            later = [round(a_ - b_, 1) for a_, b_ in zip(series[1:], r_series[1:])]
            sensitivity = (f"same-available-player scenario: the {pos} reference is fixed for every future season on a "
                           f"season-1 gap of {series[0] - r_series[0]:.1f} points over the runner-up {r_name}; the later-season "
                           f"reference differences (bar minus runner-up) are {later}; a per-season best-available reference is "
                           f"the logged alternative, not applied this cycle")
        # Name the bar player from the artifact when the producer file carries no name column.
        top_sid = _resolve_sleeper_id(top[0], by_sleeper, by_player, by_pick, by_gsis) if served else None
        top_name = (by_sleeper[top_sid].full_name if top_sid and top_sid in by_sleeper and by_sleeper[top_sid].full_name
                    else top[0].name)
        top_status = by_sleeper[top_sid].nfl_status if top_sid and top_sid in by_sleeper else None
        if top_status and top_status.lower() == "inactive":
            note = (note + "; " if note else "") + (f"the reference player {top_name} is not on an NFL roster today "
                                                    f"(Sleeper status Inactive); he is still the best forecast player nobody owns")
        refs = []
        for j in range(seasons):
            rate = sum(r.expected_season_points(j) for r in top) / len(top)
            cond = sum(r.rate_given_appear(j) for r in top) / len(top)
            refs.append(ReplacementRef(
                position=pos, policy=POLICY_NAME, rate_ppg=rate, conditional_rate_ppg=cond,
                rate_quantity=RATE_QUANTITY, snapshot_id=snapshot_id,
                horizon_assumption="same_player_from_snapshot_per_season", band=band,
                player_id=top[0].player_id if band == 1 else None,
                player_name=top_name if band == 1 else None,
                pool_complete=complete, pool_note=note,
                unforecast_eligible=n_unforecast, unforecast_reasons=reasons, census_complete=census_complete,
                reference_nfl_status=top_status if band == 1 else None,
                reference_series=series, runner_up=runner_up, sensitivity_note=sensitivity,
            ))
        out[pos] = refs
    return out


def build_annual_term_set(row: ServedRow, replacement: list[ReplacementRef], candidate: AnnualCandidate, *,
                          forecast_date: date, horizons: Optional[int] = None) -> TermSet:
    if forecast_date.year != candidate.forecast_year:
        raise ValueError(f"annual candidate vintage {candidate.forecast_year} does not match the forecast date "
                         f"{forecast_date}: refused rather than shifted")
    served = ServedReference(dynasty_value_score=row.dynasty_value_score, dvs_engine=row.dvs_engine,
                             captured_at=row.captured_at)
    producer = ProducerRef(name=candidate.model_version,
                           version=f"csv:{candidate.csv_sha256[:12]};manifest:{candidate.manifest_sha256[:12]}",
                           estimate_class="candidate", evidence_verified=candidate.evidence.verified,
                           evidence_note=candidate.evidence.reason)
    common = dict(player_id=row.player_id, position=row.position, forecast_date=forecast_date, producer=producer,
                  replacement_ref=replacement[0] if replacement else None, full_name=row.full_name,
                  sleeper_id=row.sleeper_id, served=served)
    cand = candidate.get(sleeper_id=row.sleeper_id, gsis_id=row.gsis_id, player_id=row.player_id,
                         position=row.position, draft_season=row.draft_class, pick=row.nfl_draft_pick)
    if cand is None:
        return TermSet(terms=[], coverage="none", reason=f"no annual forecast in {candidate.model_version}", **common)
    if not cand.resolved:
        return TermSet(terms=[], coverage="none",
                       reason=f"identity {cand.identity_status} in {candidate.model_version}; no forecast", **common)
    if not replacement[0].pool_complete:
        return TermSet(terms=[], coverage="partial",
                       reason=f"{replacement[0].pool_note}; no comparable value can be built on an incomplete bar",
                       **common)
    n_seasons = min(candidate.seasons, len(replacement))
    terms = []
    for h in range(n_seasons):
        ref_points = replacement[h].rate_ppg
        margin = cand.e_points[h] - ref_points
        action = "retain" if margin > 0 else "replace"
        ev = max(0.0, margin)
        note = candidate.evidence_notes.get((row.position.upper(), h + 1))
        terms.append(HorizonTerm(
            h=h, season=season_for_horizon(forecast_date, h), ev_above_replacement=ev, spec=candidate.spec,
            expected_margin=margin, action=action,
            conditioning_event=(f"{candidate.model_version}: season-long replace/retain counterfactual, NFL season {h + 1}: "
                                f"signed margin E[points] - E[points_ref] = {cand.e_points[h]:.3f} - {ref_points:.3f} = "
                                f"{margin:+.3f}; action {action}; expected advantage = positive part; reference "
                                f"{replacement[h].player_name or 'band'} ({RATE_QUANTITY}); event = appearance, "
                                f"p_appear={cand.p_appear[h]:.3f}; not optimal weekly substitution, not championship probability"
                                + (f"; producer grading: {note}" if note else "; producer grading: not supplied")),
        ))
    want = n_seasons - 1 if horizons is None else horizons
    if want > n_seasons - 1:
        return TermSet(terms=terms, coverage="partial",
                       reason=f"annual candidate and its bar reach {n_seasons} seasons; the board sums {want + 1}",
                       **common)
    return TermSet(terms=terms, coverage="full", reason=None, **common)
