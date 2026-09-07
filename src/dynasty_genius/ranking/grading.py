"""Grading the ASSEMBLED value on withheld seasons (DG-178 round 1, review item 8).

The contract sums C_ij = max(0, E[points_ij] - R_j x E[games_ij]). Adapter tests prove the
arithmetic; only a grade against realised seasons says whether the number ranks players
well. This module takes a producer's historical per-player predictions with their realised
labels and grades:

* the predicted advantage C = max(0, e_points - reference expected points) against the realised
  advantage of the SAME ex-ante action: a retained player (C > 0) realises points - reference
  realised points, which can be negative — he cost you against the reference — and a replaced
  player realises 0. Losses are kept in the error: predicted +10, realised -10 is an error of 20;
* rank agreement (Spearman) between C and the realised contribution among started players,
  top-k overlap by position, RMSE, and the summed decision value against a baseline arm.

THE REFERENCE PROXY, stated. "The next who is actually available" needs the league's rosters
in the past season, which do not exist. The reference is instead the player at a declared
RANK by the training-only BASELINE arm's predicted points at that position and season —
chosen before the outcome, independent of the candidate, shared by both arms — and the rank
is a parameter whose sensitivity is part of the report. Default ranks are the midpoints of
the availability bar ranges measured on 51 daily snapshots (DG-171: QB33-37, RB39-45,
WR55-71, TE20-21). It is a proxy, not demonstrated waiver availability.

Round 3 (Codex pinned review, 2026-09-06): the reference's IDENTITY and realised outcome are
shared, but each arm subtracts its OWN forecast of that player — the live formula — so the
reference scores zero under both arms and no arm can predict value against itself; the
selected-policy evaluation reads policy_* columns only (a row without them is unavailable,
never a fold manufactured from the raw arm); and the k-season sum's origin is the FIRST
FORECAST SEASON on every producer, with the target seasons carried explicitly and a cell
refusing to mix them.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal, Mapping, NamedTuple, Optional, Sequence

import numpy as np

INTERVAL_MEANING = ("90% bootstrap over players, conditional on this observed cohort and its reference; "
                    "the shared reference error does not cancel when the arms' actions differ; not model, "
                    "selection, season or forecast uncertainty")

REG_WEEKS = 17
# Midpoints of the measured availability-bar rank ranges (DG-171, 51 snapshots).
DEFAULT_BAR_RANKS: dict[str, int] = {"QB": 35, "RB": 42, "WR": 63, "TE": 20}
DEFAULT_TOP_K: dict[str, int] = {"QB": 12, "RB": 24, "WR": 36, "TE": 12}


@dataclass(frozen=True)
class HistoricalReference:
    """The stated PROXY for 'the next actually available' in a past season: the player at a
    declared rank by the training-only BASELINE arm's predicted points — chosen before the
    outcome, independent of the candidate, and shared by both arms. Not demonstrated waiver
    availability."""
    position: str
    season: int
    rank: int
    player_id: str
    expected_points: float
    realised_points: float
    basis: str = "rank_by_baseline_arm_predicted_points"


@dataclass(frozen=True)
class Contribution:
    player_id: str
    position: str
    season: int
    predicted: float            # max(0, e_points - reference expected points)
    started: bool               # predicted > 0: the ex-ante action was RETAIN
    realised: float             # points - reference realised points if started, else 0 (replaced)
    realised_if_started: float  # points - reference realised points regardless of the action
    producer: Optional[str] = None


def historical_reference(baseline_rows: Iterable[Mapping], *, position: str, season: int, rank: int) -> HistoricalReference:
    pool = sorted((r for r in baseline_rows if r["position"] == position and int(r["season"]) == season),
                  key=lambda r: float(r["e_points"]), reverse=True)
    if rank < 1 or rank > len(pool):
        raise ValueError(f"{position} {season}: reference rank {rank} outside the {len(pool)}-player population")
    r = pool[rank - 1]
    return HistoricalReference(position=position, season=season, rank=rank, player_id=str(r["player_id"]),
                               expected_points=float(r["e_points"]), realised_points=float(r["points"]))


def contributions(rows: Iterable[Mapping], *, reference: Mapping | HistoricalReference) -> list[Contribution]:
    """Season-long replace/retain against one reference PLAYER: the arm's predicted advantage
    is the positive part of its own margin over its OWN forecast of that player; the realised
    advantage of the chosen action keeps a loss for a retained player and is 0 for a replaced
    one. The reference is an identity plus a realised outcome; the arm must carry a row for
    him, so he scores exactly zero under this arm."""
    ref_id = str(reference.player_id if isinstance(reference, HistoricalReference) else reference["player_id"])
    ref_r = float(reference.realised_points if isinstance(reference, HistoricalReference) else reference["points"])
    rows = list(rows)
    own = [r for r in rows if str(r["player_id"]) == ref_id]
    if len(own) != 1:
        raise ValueError(f"this arm carries {len(own)} rows for the reference player {ref_id}; exactly one is required")
    ref_e = float(own[0]["e_points"])
    out = []
    for r in rows:
        margin = float(r["e_points"]) - ref_e
        started = margin > 0.0
        raw = float(r["points"]) - ref_r
        out.append(Contribution(player_id=str(r["player_id"]), position=r["position"], season=int(r["season"]),
                                predicted=max(0.0, margin), started=started, realised=raw if started else 0.0,
                                realised_if_started=raw, producer=r.get("producer")))
    return out


def _spearman(a: Sequence[float], b: Sequence[float]) -> Optional[float]:
    if len(a) < 3:
        return None
    ra, rb = _ranks(np.asarray(a, dtype=float)), _ranks(np.asarray(b, dtype=float))
    if ra.std() == 0 or rb.std() == 0:
        return None
    return float(np.corrcoef(ra, rb)[0, 1])


def _ranks(x: np.ndarray) -> np.ndarray:
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(len(x), dtype=float)
    ranks[order] = np.arange(1, len(x) + 1, dtype=float)
    _, inv, counts = np.unique(x, return_inverse=True, return_counts=True)
    sums = np.zeros(len(counts))
    np.add.at(sums, inv, ranks)
    return sums[inv] / counts[inv]


def _ci(values: Sequence[float], rng: np.random.Generator, n_boot: int, stat) -> Optional[list[float]]:
    arr = np.asarray(values, dtype=float)
    if len(arr) < 3 or n_boot <= 0:
        return None
    draws = [stat(arr[rng.integers(0, len(arr), len(arr))]) for _ in range(n_boot)]
    return [float(np.percentile(draws, 5)), float(np.percentile(draws, 95))]


def grade(candidate: Sequence[Contribution], baseline: Sequence[Contribution], k: Optional[int] = None,
          n_boot: int = 0, seed: int = 20260906) -> dict:
    """Grade one cell (one position, one season). Both arms are graded against the SAME
    reference. Errors keep losses: predicted +10 and realised -10 is an error of 20."""
    cand = {c.player_id: c for c in candidate}
    base = {b.player_id: b for b in baseline}
    if set(cand) != set(base):
        raise ValueError("candidate and baseline grade different players")
    ids = sorted(cand)
    pred = [cand[i].predicted for i in ids]
    real = [cand[i].realised_if_started for i in ids]
    started = [i for i in ids if cand[i].started]
    k = k or max(1, min(12, len(ids) // 3))
    top_pred = set(sorted(ids, key=lambda i: cand[i].predicted, reverse=True)[:k])
    top_real = set(sorted(ids, key=lambda i: cand[i].realised_if_started, reverse=True)[:k])
    errors = [cand[i].predicted - cand[i].realised for i in ids]
    rng = np.random.default_rng(seed)
    diffs = [cand[i].realised - base[i].realised for i in ids]
    biases = [cand[i].predicted - cand[i].realised for i in started]
    return {
        "n": len(ids),
        "n_started": len(started),
        "interval_meaning": INTERVAL_MEANING,
        "spearman_pred_vs_realised": _spearman(pred, real),
        "spearman_among_started": _spearman([cand[i].predicted for i in started], [cand[i].realised for i in started]),
        "rmse": float(np.sqrt(np.mean(np.square(errors)))),
        "decision_value_sum": float(sum(cand[i].realised for i in ids)),
        "baseline_decision_value_sum": float(sum(base[i].realised for i in ids)),
        "baseline_n_started": sum(1 for i in ids if base[i].started),
        "decision_value_diff": float(sum(diffs)),
        "decision_value_diff_ci90": _ci(diffs, rng, n_boot, lambda a: float(a.sum())),
        "bias_among_started": (float(np.mean(biases)) if biases else None),
        "bias_ci90": _ci(biases, rng, n_boot, lambda a: float(a.mean())),
        "top_k_overlap": len(top_pred & top_real) / k,
        "k": k,
    }


def grade_by_cell(candidate_rows: Sequence[Mapping], baseline_rows: Sequence[Mapping], *,
                  rank_by_position: Mapping[str, int] = DEFAULT_BAR_RANKS,
                  top_k: Mapping[str, int] = DEFAULT_TOP_K, n_boot: int = 0) -> dict[tuple[str, int], dict]:
    """One grade per (position, season). The reference PLAYER is chosen from the BASELINE
    arm's predicted ranking; each arm then subtracts its own forecast of him."""
    cells: dict[tuple[str, int], dict] = {}
    keys = sorted({(r["position"], int(r["season"])) for r in candidate_rows})
    for pos, season in keys:
        rank = rank_by_position.get(pos)
        if rank is None:
            continue
        crows = [r for r in candidate_rows if r["position"] == pos and int(r["season"]) == season]
        brows = [r for r in baseline_rows if r["position"] == pos and int(r["season"]) == season]
        try:
            ref = historical_reference(brows, position=pos, season=season, rank=rank)
            cc, bc = contributions(crows, reference=ref), contributions(brows, reference=ref)
        except ValueError as exc:
            cells[(pos, season)] = {"skipped": str(exc), "n": len(crows)}
            continue
        g = grade(cc, bc, k=min(top_k.get(pos, 12), len(crows)), n_boot=n_boot)
        cand_ref_e = next(float(r["e_points"]) for r in crows if str(r["player_id"]) == ref.player_id)
        g["reference"] = {"player_id": ref.player_id, "rank": ref.rank, "expected_points": ref.expected_points,
                          "expected_points_by_arm": {"candidate": cand_ref_e, "baseline": ref.expected_points},
                          "realised_points": ref.realised_points, "basis": ref.basis,
                          "rule": "identity and outcome shared; each arm subtracts its own forecast of him"}
        cells[(pos, season)] = g
    return cells


class HistoryRows(NamedTuple):
    """A producer's history on the common grading shape, with what could NOT be read: rows the
    selected policy never scored are `unavailable`, never folds manufactured from raw columns."""
    candidate: list[dict]
    baseline: list[dict]
    unavailable: int = 0
    mode: str = "policy"


ReadMode = Literal["policy", "legacy_arm"]


def _pred(rec: Mapping, j: int, mode: str, kind: str) -> Optional[float]:
    """The scoring arm's prediction for season j under the declared read mode: the selection
    POLICY's output (policy_*) only, or — explicitly — the raw arm's own columns."""
    col = f"{kind}_year{j}"
    return _f(rec.get(f"policy_{col}")) if mode == "policy" else _f(rec.get(col))


# ── Row builders: each producer's historical file onto the common grading shape ─────────
def _f(v) -> Optional[float]:
    if v is None or str(v).strip() == "":
        return None
    return float(v)


def veteran_history_rows(path, *, arm: Optional[str], horizon: int, mode: ReadMode = "policy") -> HistoryRows:
    """Lane 23481's historical_predictions.csv: one row per (horizon, [arm,] player, feature
    season). Season = forecast_season; labels points_year{h}/games_year{h}; the baseline arm's
    predictions ride on the same row. In policy mode a row whose policy_* columns are empty
    (a fold the selection policy never evaluated) is UNAVAILABLE and counted, not read from
    the raw arm columns; legacy_arm mode reads those columns and requires an arm column."""
    import csv
    from pathlib import Path

    cand, base, unavailable = [], [], 0
    with Path(path).open(newline="") as fh:
        reader = csv.DictReader(fh)
        has_arm = "arm" in (reader.fieldnames or [])
        if mode == "legacy_arm" and not has_arm:
            raise ValueError("legacy_arm mode reads raw arm columns and needs an arm column to name them")
        for rec in reader:
            if (has_arm and arm is not None and rec.get("arm") != arm) or int(rec.get("horizon") or 0) != horizon:
                continue
            j = horizon
            pts, gms = _f(rec.get(f"points_year{j}")), _f(rec.get(f"games_year{j}"))
            bp, bg = _f(rec.get(f"baseline_e_points_year{j}")), _f(rec.get(f"baseline_e_games_year{j}"))
            if None in (pts, gms, bp, bg):
                continue
            ep, eg = _pred(rec, j, mode, "e_points"), _pred(rec, j, mode, "e_games")
            if ep is None or eg is None:
                unavailable += 1
                continue
            common = {"player_id": rec["player_id"], "position": rec["position"].upper(),
                      "season": int(rec["forecast_season"]), "points": pts, "games": gms, "producer": "veteran"}
            cand.append({**common, "e_points": ep, "e_games": eg})
            base.append({**common, "e_points": bp, "e_games": bg})
    return HistoryRows(cand, base, unavailable, mode)


def rookie_history_rows(path, *, season_j: int) -> HistoryRows:
    """Lane 24974's out_of_time_predictions.csv: one row per prospect. Season = forecast_year
    + j - 1; predictions e_points_year{j}/e_games_year{j}; labels points_{j}/games_{j}, absent
    when that season is not complete. Unlabelled rows are skipped, not zero-filled."""
    import csv
    from pathlib import Path

    cand, base = [], []
    with Path(path).open(newline="") as fh:
        for rec in csv.DictReader(fh):
            j = season_j
            ep, eg = _f(rec.get(f"e_points_year{j}")), _f(rec.get(f"e_games_year{j}"))
            pts, gms = _f(rec.get(f"points_{j}")), _f(rec.get(f"games_{j}"))
            bp, bg = _f(rec.get(f"baseline_e_points_year{j}")), _f(rec.get(f"baseline_e_games_year{j}"))
            if None in (ep, eg, pts, gms, bp, bg):
                continue
            common = {"player_id": rec["gsis_id"], "position": rec["position"].upper(),
                      "season": int(rec["forecast_year"]) + j - 1, "points": pts, "games": gms, "producer": "rookie"}
            cand.append({**common, "e_points": ep, "e_games": eg})
            base.append({**common, "e_points": bp, "e_games": bg})
    return HistoryRows(cand, base, 0, "policy")


# ── Arm consistency: the graded arm must be the scoring arm ──────────────────────────────
def _scoring_identity(manifest: Mapping) -> tuple[Optional[str], Optional[str]]:
    """(policy, arm id) the SCORING file uses, from affirmative identifiers only."""
    policy = manifest.get("model_policy") if isinstance(manifest.get("model_policy"), str) else None
    arm = None
    for key in ("scoring_arm_id", "candidate_arm", "scoring_arm"):
        v = manifest.get(key)
        if isinstance(v, str) and v.strip():
            arm = v.strip()
            break
    if arm is None:
        decision = (manifest.get("trend_experiment") or {}).get("decision")
        if isinstance(decision, str) and decision.strip():
            arm = decision.strip()
    return policy, arm


def _scoring_arm(manifest: Mapping) -> Optional[str]:
    policy, arm = _scoring_identity(manifest)
    return arm or policy


def _graded_identity(evaluation: Mapping, expected_arm: Optional[str] = None) -> tuple[Optional[str], Optional[str], list[str]]:
    """(policy, arm id, arm ids) the grading file describes, from affirmative identifiers only."""
    policy = None
    for key in ("policy_id", "model_policy"):
        v = evaluation.get(key)
        if isinstance(v, str) and v.strip():
            policy = v.strip()
            break
    ev = evaluation.get("evaluation")
    if policy is None and isinstance(ev, dict) and isinstance(ev.get("policy_id"), str):
        policy = ev["policy_id"].strip()
    arm = None
    for key in ("scoring_arm_id", "arm"):
        v = evaluation.get(key)
        if isinstance(v, str) and v.strip():
            arm = v.strip()
            break
    if arm is None and isinstance(evaluation.get("trend"), bool):
        arm = "auto_trend" if evaluation["trend"] else "plain"
    arm_ids = [str(a) for a in evaluation.get("arm_ids", []) if isinstance(a, str)]
    # lane 23481's shape grades every arm side by side under historical[pos][year][arm]
    hist = evaluation.get("historical")
    if isinstance(hist, dict):
        arm_ids += sorted({a for years in hist.values() if isinstance(years, dict)
                           for cell in years.values() if isinstance(cell, dict) for a in cell})
        if arm is None and expected_arm in arm_ids:
            arm = expected_arm
        # round-2 shape: the selection policy's grade under year.pooled.policy names the scoring
        # arm's policy; the manifest's scoring arm is what it graded.
        if arm is None and expected_arm and any(
            isinstance(cell, dict) and isinstance(cell.get("pooled"), dict) and "policy" in cell["pooled"]
            for years in hist.values() if isinstance(years, dict) for cell in years.values()
        ):
            arm = expected_arm
    return policy, arm, arm_ids


def _graded_arm(evaluation: Mapping, expected: Optional[str] = None) -> Optional[str]:
    policy, arm, _ = _graded_identity(evaluation, expected)
    return arm or policy


def rookie_arm_consistency(manifest: Mapping, evaluation: Mapping,
                           evaluation_sha256: Optional[str] = None) -> tuple[bool, str]:
    """True only when the files name their identity affirmatively AND agree:
    * a policy named on both sides must match;
    * the scoring arm id must equal the graded arm id, or be among the evaluation's arm ids;
    * a sha256 the manifest declares for the evaluation file must match the bytes read.
    Absence of any identifier is unverified, never agreement: ({}, {}) is False."""
    s_policy, s_arm = _scoring_identity(manifest)
    g_policy, g_arm, g_arms = _graded_identity(evaluation, s_arm)
    if s_arm is None and s_policy is None:
        return False, "unverified: no affirmative identifier for manifest scoring arm"
    if g_arm is None and g_policy is None and not g_arms:
        return False, "unverified: no affirmative identifier for evaluation graded arm"
    if s_policy is not None and g_policy is not None and s_policy != g_policy:
        return False, (f"the evaluation describes policy {g_policy} but the scoring file uses policy {s_policy}; "
                       "this grading is not evidence about the board's values")
    if s_arm is not None:
        if g_arm is not None and g_arm != s_arm and s_arm not in g_arms:
            return False, (f"the evaluation graded the {g_arm} arm but the scoring file uses the {s_arm} arm; "
                           "this grading is not evidence about the board's values")
        if g_arm is None and g_arms and s_arm not in g_arms:
            return False, f"the scoring arm {s_arm} is not among the evaluation's graded arm ids {g_arms}"
    # The identifiers each side names must have something in common: a manifest naming only
    # an arm and an evaluation naming only a policy agree only if those names coincide.
    scoring_ids = {x for x in (s_policy, s_arm) if x}
    graded_ids = {x for x in (g_policy, g_arm) if x} | set(g_arms)
    if not (scoring_ids & graded_ids):
        return False, (f"no shared identity: scoring names {sorted(scoring_ids)}, the evaluation names "
                       f"{sorted(graded_ids)}; this grading is not evidence about the board's values")
    if evaluation_sha256 is not None:
        declared = (manifest.get("outputs_sha256") or {}).get("evaluation.json") if isinstance(manifest.get("outputs_sha256"), dict) else None
        if declared is not None and str(declared).lower() != evaluation_sha256.lower():
            return False, "the manifest's declared sha256 for evaluation.json does not match the bytes read"
    named = s_arm or s_policy
    return True, f"grading and scoring describe the same identity ({named})"


# ── The two-season SUM from one forecast origin ─────────────────────────────────────────
def grade_multi_season_by_origin(candidate_rows: Sequence[Mapping], baseline_rows: Sequence[Mapping], *,
                                 seasons: int, rank_by_position: Mapping[str, int] = DEFAULT_BAR_RANKS,
                                 n_boot: int = 0, seed: int = 20260906) -> dict[tuple[str, int], dict]:
    """The k-season SUM from one origin per player, one reference PLAYER per origin, chosen by
    the baseline arm's season-1 forecast; each arm subtracts its own forecast of him in every
    season. Rows carry origin (the FIRST forecast season), target_seasons, e_points_s and
    points_s for s = 1..k; a cell whose rows disagree on target seasons is refused."""
    out: dict[tuple[str, int], dict] = {}
    keys = sorted({(r["position"], int(r["origin"])) for r in candidate_rows})
    rng = np.random.default_rng(seed)
    ks = list(range(1, seasons + 1))
    for pos, origin in keys:
        rank = rank_by_position.get(pos)
        if rank is None:
            continue
        crows = [r for r in candidate_rows if r["position"] == pos and int(r["origin"]) == origin]
        brows = {r["player_id"]: r for r in baseline_rows if r["position"] == pos and int(r["origin"]) == origin}
        if set(brows) != {r["player_id"] for r in crows}:
            raise ValueError(f"{pos} {origin}: candidate and baseline carry different players")
        targets = {tuple(int(x) for x in r.get("target_seasons") or ()) for r in crows} | \
                  {tuple(int(x) for x in r.get("target_seasons") or ()) for r in brows.values()}
        if len(targets) != 1:
            raise ValueError(f"{pos} {origin}: rows disagree on their target seasons {sorted(targets)}; "
                             "a k-season sum combines one set of actual seasons only")
        target_seasons = list(next(iter(targets))) or [origin + s - 1 for s in ks]
        if len(target_seasons) != seasons:
            raise ValueError(f"{pos} {origin}: target seasons {target_seasons} do not span {seasons} seasons")
        pool = sorted(brows.values(), key=lambda r: float(r["e_points_1"]), reverse=True)
        if rank < 1 or rank > len(pool):
            out[(pos, origin)] = {"skipped": f"reference rank {rank} outside the {len(pool)}-player population", "n": len(crows)}
            continue
        ref = pool[rank - 1]
        ref_id = str(ref["player_id"])
        cand_ref = next(r for r in crows if str(r["player_id"]) == ref_id)
        ref_r = [float(ref[f"points_{s}"]) for s in ks]
        ref_e_by_arm = {"candidate": [float(cand_ref[f"e_points_{s}"]) for s in ks],
                        "baseline": [float(ref[f"e_points_{s}"]) for s in ks]}

        def value(row: Mapping, ref_e: list[float]) -> tuple[float, float, list[str]]:
            pred, real, actions = 0.0, 0.0, []
            for s in ks:
                margin = float(row[f"e_points_{s}"]) - ref_e[s - 1]
                retain = margin > 0.0
                actions.append("retain" if retain else "replace")
                pred += max(0.0, margin)
                real += (float(row[f"points_{s}"]) - ref_r[s - 1]) if retain else 0.0
            return pred, real, actions

        players, diffs, errors = [], [], []
        for r in crows:
            cp, cr, ca = value(r, ref_e_by_arm["candidate"])
            bp, br, _ = value(brows[r["player_id"]], ref_e_by_arm["baseline"])
            players.append({"player_id": r["player_id"], "producer": r.get("producer"), "predicted": cp, "realised": cr,
                            "actions": ca, "baseline_predicted": bp, "baseline_realised": br})
            diffs.append(cr - br)
            errors.append(cp - cr)
        pred = [p["predicted"] for p in players]
        real = [p["realised"] for p in players]
        out[(pos, origin)] = {
            "n": len(players), "seasons": seasons, "target_seasons": target_seasons,
            "interval_meaning": INTERVAL_MEANING,
            "n_retained_any": sum(1 for p in players if "retain" in p["actions"]),
            "spearman_pred_vs_realised": _spearman(pred, real),
            "rmse": float(np.sqrt(np.mean(np.square(errors)))),
            "decision_value_sum": float(sum(real)),
            "baseline_decision_value_sum": float(sum(p["baseline_realised"] for p in players)),
            "decision_value_diff": float(sum(diffs)),
            "decision_value_diff_ci90": _ci(diffs, rng, n_boot, lambda a: float(a.sum())),
            "reference": {"player_id": ref_id, "rank": rank, "expected_points": ref_e_by_arm["baseline"],
                          "expected_points_by_arm": ref_e_by_arm, "realised_points": ref_r,
                          "basis": "rank_by_baseline_arm_year1_predicted_points_at_origin",
                          "rule": "identity and outcome shared; each arm subtracts its own forecast of him"},
            "players": players,
        }
    return out


def multi_season_rows_from_single_file(path, *, seasons: int, id_col: str, origin_col: str, pred_prefix: str,
                                       base_prefix: str, label_prefix: str, producer: str,
                                       horizon_col: Optional[str] = None, horizon_value: Optional[int] = None,
                                       position_col: str = "position", origin_offset: int = 0) -> HistoryRows:
    """Rows that already carry seasons 1..k for one origin. The ORIGIN is the first forecast
    season: a rookie row's forecast_year is that season (offset 0); a veteran row keyed on its
    feature season needs origin_offset=1. Rows missing any label are skipped."""
    import csv
    from pathlib import Path

    cand, base = [], []
    with Path(path).open(newline="") as fh:
        for rec in csv.DictReader(fh):
            if horizon_col and horizon_value is not None and int(rec.get(horizon_col) or 0) != horizon_value:
                continue
            vals = {}
            ok = True
            for s in range(1, seasons + 1):
                e, b, y = _f(rec.get(f"{pred_prefix}{s}")), _f(rec.get(f"{base_prefix}{s}")), _f(rec.get(f"{label_prefix}{s}"))
                if None in (e, b, y):
                    ok = False
                    break
                vals[s] = (e, b, y)
            if not ok:
                continue
            origin = int(rec[origin_col]) + origin_offset
            common = {"player_id": rec[id_col], "position": rec[position_col].upper(), "origin": origin,
                      "target_seasons": [origin + s - 1 for s in range(1, seasons + 1)],
                      "producer": producer, **{f"points_{s}": vals[s][2] for s in vals}}
            cand.append({**common, **{f"e_points_{s}": vals[s][0] for s in vals}})
            base.append({**common, **{f"e_points_{s}": vals[s][1] for s in vals}})
    return HistoryRows(cand, base, 0, "policy")


def grade_two_season_by_origin(candidate_rows: Sequence[Mapping], baseline_rows: Sequence[Mapping], *,
                               rank_by_position: Mapping[str, int] = DEFAULT_BAR_RANKS,
                               n_boot: int = 0, seed: int = 20260906) -> dict[tuple[str, int], dict]:
    """The two-season case of grade_multi_season_by_origin, kept as the named entry point."""
    return grade_multi_season_by_origin(candidate_rows, baseline_rows, seasons=2, rank_by_position=rank_by_position,
                                        n_boot=n_boot, seed=seed)


def _grade_two_season_by_origin_legacy(candidate_rows: Sequence[Mapping], baseline_rows: Sequence[Mapping], *,
                               rank_by_position: Mapping[str, int] = DEFAULT_BAR_RANKS,
                               n_boot: int = 0, seed: int = 20260906) -> dict[tuple[str, int], dict]:
    """Grade V = C_1 + C_2 for each player from ONE forecast origin, per (position, origin).

    Rows carry e_points_1/points_1 and e_points_2/points_2 for the same player and origin.
    The reference is chosen ONCE at the origin — the rank-N player by the baseline arm's
    year-1 predicted points — and his own year-2 expected and realised points serve season 2,
    so both seasons share one ex-ante reference and its error. Per player, predicted V is the
    sum of positive margins (each season's own retain/replace action); realised V is the sum
    of each action's outcome, losses kept. Folds are reported separately with counts;
    nothing here pools folds into a superiority claim.
    """
    out: dict[tuple[str, int], dict] = {}
    keys = sorted({(r["position"], int(r["origin"])) for r in candidate_rows})
    rng = np.random.default_rng(seed)
    for pos, origin in keys:
        rank = rank_by_position.get(pos)
        if rank is None:
            continue
        crows = [r for r in candidate_rows if r["position"] == pos and int(r["origin"]) == origin]
        brows = {r["player_id"]: r for r in baseline_rows if r["position"] == pos and int(r["origin"]) == origin}
        if set(brows) != {r["player_id"] for r in crows}:
            raise ValueError(f"{pos} {origin}: candidate and baseline carry different players")
        pool = sorted(brows.values(), key=lambda r: float(r["e_points_1"]), reverse=True)
        if rank < 1 or rank > len(pool):
            out[(pos, origin)] = {"skipped": f"reference rank {rank} outside the {len(pool)}-player population", "n": len(crows)}
            continue
        ref = pool[rank - 1]
        ref_e = [float(ref["e_points_1"]), float(ref["e_points_2"])]
        ref_r = [float(ref["points_1"]), float(ref["points_2"])]

        def value(row: Mapping) -> tuple[float, float, list[str]]:
            pred, real, actions = 0.0, 0.0, []
            for s in (1, 2):
                margin = float(row[f"e_points_{s}"]) - ref_e[s - 1]
                retain = margin > 0.0
                actions.append("retain" if retain else "replace")
                pred += max(0.0, margin)
                real += (float(row[f"points_{s}"]) - ref_r[s - 1]) if retain else 0.0
            return pred, real, actions

        players, diffs, errors = [], [], []
        for r in crows:
            cp, cr, ca = value(r)
            bp, br, _ = value(brows[r["player_id"]])
            players.append({"player_id": r["player_id"], "producer": r.get("producer"), "predicted": cp, "realised": cr,
                            "actions": ca, "baseline_predicted": bp, "baseline_realised": br})
            diffs.append(cr - br)
            errors.append(cp - cr)
        pred = [p["predicted"] for p in players]
        real = [p["realised"] for p in players]
        out[(pos, origin)] = {
            "n": len(players),
            "n_retained_any": sum(1 for p in players if "retain" in p["actions"]),
            "spearman_pred_vs_realised": _spearman(pred, real),
            "rmse": float(np.sqrt(np.mean(np.square(errors)))),
            "decision_value_sum": float(sum(real)),
            "baseline_decision_value_sum": float(sum(p["baseline_realised"] for p in players)),
            "decision_value_diff": float(sum(diffs)),
            "decision_value_diff_ci90": _ci(diffs, rng, n_boot, lambda a: float(a.sum())),
            "reference": {"player_id": str(ref["player_id"]), "rank": rank, "expected_points": ref_e,
                          "realised_points": ref_r, "basis": "rank_by_baseline_arm_year1_predicted_points_at_origin"},
            "players": players,
        }
    return out


def veteran_two_season_rows(path, *, arm: Optional[str], mode: ReadMode = "policy") -> HistoryRows:
    """The two-season case of veteran_multi_season_rows, kept as the named entry point."""
    return veteran_multi_season_rows(path, seasons=2, arm=arm, mode=mode)


def rookie_two_season_rows(path) -> HistoryRows:
    """Lane 24974's out-of-time rows already carry year 1 and 2 from one origin (the draft
    class, forecast_year = the first forecast season); rows without both labels are skipped."""
    return multi_season_rows_from_single_file(path, seasons=2, id_col="gsis_id", origin_col="forecast_year",
                                              pred_prefix="e_points_year", base_prefix="baseline_e_points_year",
                                              label_prefix="points_", producer="rookie")


def veteran_multi_season_rows(path, *, seasons: int, arm: Optional[str] = None, mode: ReadMode = "policy") -> HistoryRows:
    """k-season origin rows from a history that carries each season on its own horizon row:
    join h = 1..k on (player_id, feature_season). The ORIGIN is the first forecast season
    (the h=1 row's forecast_season, = feature_season + 1), so a veteran row and a rookie row
    with the same origin sum the same actual seasons. Only origins with every season's
    policy forecast and label count; an origin missing a policy forecast is unavailable."""
    import csv
    from pathlib import Path

    by_key: dict[tuple[str, int], dict[int, dict]] = {}
    with Path(path).open(newline="") as fh:
        reader = csv.DictReader(fh)
        has_arm = "arm" in (reader.fieldnames or [])
        if mode == "legacy_arm" and not has_arm:
            raise ValueError("legacy_arm mode reads raw arm columns and needs an arm column to name them")
        for rec in reader:
            if has_arm and arm is not None and rec.get("arm") != arm:
                continue
            h = int(rec.get("horizon") or 0)
            if 1 <= h <= seasons:
                by_key.setdefault((rec["player_id"], int(rec["feature_season"])), {})[h] = rec
    cand, base, unavailable = [], [], 0
    for (pid, feature_season), rows in by_key.items():
        if any(h not in rows for h in range(1, seasons + 1)):
            continue
        ok, missing_policy, ev, bv, yv = True, False, {}, {}, {}
        for h in range(1, seasons + 1):
            rec = rows[h]
            b, y = _f(rec.get(f"baseline_e_points_year{h}")), _f(rec.get(f"points_year{h}"))
            if None in (b, y):
                ok = False
                break
            e = _pred(rec, h, mode, "e_points")
            if e is None:
                missing_policy = True
                break
            ev[h], bv[h], yv[h] = e, b, y
        if missing_policy:
            unavailable += 1
            continue
        if not ok:
            continue
        origin = int(rows[1]["forecast_season"]) if rows[1].get("forecast_season") else feature_season + 1
        common = {"player_id": pid, "position": rows[1]["position"].upper(), "origin": origin,
                  "target_seasons": [origin + h - 1 for h in range(1, seasons + 1)], "producer": "veteran",
                  **{f"points_{h}": yv[h] for h in yv}}
        cand.append({**common, **{f"e_points_{h}": ev[h] for h in ev}})
        base.append({**common, **{f"e_points_{h}": bv[h] for h in bv}})
    return HistoryRows(cand, base, unavailable, mode)