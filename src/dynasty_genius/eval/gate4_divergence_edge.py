"""Gate-4 divergence-edge validation — pure engine (T1).

Fixture-only, deterministic, no archive DB / file I/O / model calls. Implements the
locked, pre-registered methodology of
`docs/superpowers/specs/2026-06-23-gate4-divergence-edge-validation-design.md`
(pre-registration seal: spec commit 84531dc).

The functions here are the analysable core; the T2 runner wraps them with archive
ingestion + report emission. Keeping them pure makes the verdict logic and the
falsification battery exhaustively unit-testable on fixtures.
"""
from __future__ import annotations

import random
import statistics
from datetime import date, timedelta
from typing import Any, Optional

import numpy as np

# ── Locked parameters (mirror the pre-registered spec §3–§6) ──────────────────
HIGH_BAND = 20.0  # D >= +HIGH_BAND  -> MODEL_HIGH_MARKET_LOW
NEUTRAL_BAND = 5.0  # |D| <= NEUTRAL_BAND -> NEUTRAL (control); 5 < |D| < 20 excluded
MIN_STRATUM_SIDE = 5  # drop a stratum with < this many signal OR control obs
EFFECT_SIZE_FLOOR = 8.0  # min practical lift (within-position pct points)
MIN_EFFECTIVE_BLOCKS = 6  # < this many month blocks -> UNDERPOWERED
MIN_USABLE_T_DATES = 8  # per horizon
MIN_JOINED_OBS = 200
MIN_BUCKET_OBS = 30
MIN_IDENTITY_COVERAGE = 0.90
MAX_TOP_POSITION_SHARE = 0.50
SURVIVORSHIP_PERCENTILE = 5.0  # disappeared player -> 5th-pct cohort outcome
FORWARD_TOLERANCE_DAYS = 7

BUCKET_HIGH = "MODEL_HIGH_MARKET_LOW"
BUCKET_LOW = "MODEL_LOW_MARKET_HIGH"
BUCKET_NEUTRAL = "NEUTRAL"

CLAIM_TRADEABLE = "tradeable_historical_edge"
CLAIM_RETROSPECTIVE = "current_model_retrospective_diagnostic"


# ── 1. Within-position percentiles ────────────────────────────────────────────


def _percentile_rank(value: float, population: list[float]) -> float:
    """Percentile in [0, 100] = (# strictly less) / (n - 1) * 100. Single-member
    position -> 50.0 (neutral, undefined rank)."""
    n = len(population)
    if n <= 1:
        return 50.0
    strictly_less = sum(1 for v in population if v < value)
    return strictly_less / (n - 1) * 100.0


def compute_within_position_percentiles(
    rows: list[dict],
    *,
    model_value_key: str,
    market_value_key: str,
) -> list[dict]:
    """Add `model_pct` / `market_pct` = within-position percentile ranks.

    Within-position (not cross-position) neutralizes positional scale and
    market-wide inflation (spec §3.1)."""
    by_position: dict[Any, dict[str, list[float]]] = {}
    for row in rows:
        pos = row["position"]
        bucket = by_position.setdefault(pos, {"model": [], "market": []})
        bucket["model"].append(row[model_value_key])
        bucket["market"].append(row[market_value_key])

    scored: list[dict] = []
    for row in rows:
        pos = row["position"]
        out = dict(row)
        out["model_pct"] = _percentile_rank(row[model_value_key], by_position[pos]["model"])
        out["market_pct"] = _percentile_rank(row[market_value_key], by_position[pos]["market"])
        scored.append(out)
    return scored


# ── 2. Divergence bucketing (locked band edges) ───────────────────────────────


def classify_divergence(model_pct: float, market_pct: float) -> Optional[str]:
    """D = model_pct - market_pct. HIGH if D>=+20, LOW if D<=-20, NEUTRAL if
    |D|<=5; the 5<|D|<20 gray zone returns None (excluded from the test)."""
    d = model_pct - market_pct
    if d >= HIGH_BAND:
        return BUCKET_HIGH
    if d <= -HIGH_BAND:
        return BUCKET_LOW
    if abs(d) <= NEUTRAL_BAND:
        return BUCKET_NEUTRAL
    return None


# ── 3. Forward-only date resolver ─────────────────────────────────────────────


def resolve_forward_date(
    start_date: date,
    horizon_days: int,
    available_dates: list[date],
) -> Optional[date]:
    """Earliest snapshot date in [start+horizon, start+horizon+7] (spec §3.3).

    Forward-only: a date *before* `start+horizon` is never returned (the existing
    ±7 `_resolve_date` could shorten the horizon — forbidden)."""
    target = start_date + timedelta(days=horizon_days)
    window_end = target + timedelta(days=FORWARD_TOLERANCE_DAYS)
    candidates = sorted(d for d in available_dates if target <= d <= window_end)
    return candidates[0] if candidates else None


# ── 4. Forward outcome + survivorship rule ────────────────────────────────────


def compute_forward_outcomes(
    start_rows: list[dict],
    future_rows: list[dict],
    *,
    horizon_days: int,
) -> list[dict]:
    """fwdΔ = market_pct(T+N) − market_pct(T) for survivors; a player absent at
    T+N gets the 5th-percentile forward outcome of its position cohort (spec §3.4
    — disappearance is a strongly negative outcome, never silently dropped)."""
    future_pct = {r["player_id"]: r["market_pct"] for r in future_rows}

    # Cohort = position × horizon × snapshot_date (spec §3.4) — the survivorship
    # penalty for a disappeared player is the 5th-pct forward outcome of OTHER
    # players in its exact cohort, not pooled across dates.
    observed_by_cohort: dict[tuple, list[float]] = {}
    interim: list[dict] = []
    for row in start_rows:
        out = dict(row)
        out["horizon_days"] = horizon_days
        cohort = (row["position"], horizon_days, row["snapshot_date"])
        pid = row["player_id"]
        if pid in future_pct:
            delta = future_pct[pid] - row["market_pct"]
            out["fwd_delta"] = delta
            out["outcome_status"] = "observed"
            observed_by_cohort.setdefault(cohort, []).append(delta)
        else:
            out["fwd_delta"] = None
            out["outcome_status"] = "survivorship_penalty"
        interim.append(out)

    penalty_by_cohort: dict[tuple, float] = {
        cohort: float(np.percentile(deltas, SURVIVORSHIP_PERCENTILE))
        for cohort, deltas in observed_by_cohort.items()
    }
    for out in interim:
        if out["outcome_status"] == "survivorship_penalty":
            cohort = (out["position"], horizon_days, out["snapshot_date"])
            out["fwd_delta"] = penalty_by_cohort.get(cohort, 0.0)
    return interim


# ── 5. Matched stratified lift (regression-to-mean control) ───────────────────


def _stratum_key(row: dict) -> tuple:
    """position × initial market_pct decile × snapshot_date (spec §3.5)."""
    decile = int(row["initial_market_pct"] // 10)
    return (row["position"], decile, row["snapshot_date"])


def compute_matched_lift(
    rows: list[dict],
    *,
    signal_bucket: str,
    control_bucket: str,
) -> dict:
    """Pooled, sample-weighted median-difference lift within matched strata.

    A stratum is dropped if it has < MIN_STRATUM_SIDE signal OR < MIN_STRATUM_SIDE
    control observations (Codex C2 — `OR`, so a 1-signal/80-control stratum cannot
    survive). Holding position × initial-market-pct × date fixed controls for
    mean-reversion (spec §3.5/§3.6)."""
    strata: dict[tuple, dict[str, list[float]]] = {}
    for row in rows:
        b = row["bucket"]
        if b not in (signal_bucket, control_bucket):
            continue
        s = strata.setdefault(_stratum_key(row), {"signal": [], "control": []})
        side = "signal" if b == signal_bucket else "control"
        s[side].append(row["fwd_delta"])

    kept_diffs: list[tuple[float, int]] = []  # (median_diff, weight)
    kept = dropped = n_signal = n_control = 0
    for s in strata.values():
        if len(s["signal"]) < MIN_STRATUM_SIDE or len(s["control"]) < MIN_STRATUM_SIDE:
            dropped += 1
            continue
        kept += 1
        n_signal += len(s["signal"])
        n_control += len(s["control"])
        diff = statistics.median(s["signal"]) - statistics.median(s["control"])
        kept_diffs.append((diff, len(s["signal"]) + len(s["control"])))

    if kept_diffs:
        total_w = sum(w for _, w in kept_diffs)
        lift = sum(d * w for d, w in kept_diffs) / total_w
    else:
        lift = 0.0
    return {
        "lift": lift,
        "kept_strata": kept,
        "dropped_strata": dropped,
        "n_signal": n_signal,
        "n_control": n_control,
    }


# ── 6. Month-block bootstrap + non-overlapping sensitivity ────────────────────


def _month_index(d: date) -> int:
    return d.year * 12 + d.month


def month_block_bootstrap_ci(
    rows: list[dict],
    *,
    signal_bucket: str,
    control_bucket: str,
    n_resamples: int,
    rng_seed: int,
) -> dict:
    """Block bootstrap blocking by calendar month (Codex C5 — overlapping weekly
    windows are serially correlated, so per-date clustering alone understates the
    CI). Each resample draws whole month blocks with replacement and RECOMPUTES the
    locked §3.5/§3.6 matched-stratified lift on the unioned rows (so the <5 signal
    OR <5 control stratum-drop is honored inside the bootstrap, not bypassed).

    The point estimate is the pooled sample-weighted matched lift on the full data
    (NOT an unweighted month mean)."""
    by_month: dict[int, list[dict]] = {}
    for row in rows:
        by_month.setdefault(_month_index(row["snapshot_date"]), []).append(row)

    # Effective blocks = months that contribute at least one kept matched stratum.
    effective_months = [
        mi
        for mi, mrows in by_month.items()
        if compute_matched_lift(mrows, signal_bucket=signal_bucket, control_bucket=control_bucket)[
            "kept_strata"
        ]
        > 0
    ]
    effective = len(effective_months)
    point = compute_matched_lift(rows, signal_bucket=signal_bucket, control_bucket=control_bucket)[
        "lift"
    ]

    rng = random.Random(rng_seed)
    stats: list[float] = []
    if effective_months:
        for _ in range(n_resamples):
            drawn = [rng.choice(effective_months) for _ in effective_months]
            union: list[dict] = []
            for mi in drawn:
                union.extend(by_month[mi])
            stats.append(
                compute_matched_lift(
                    union, signal_bucket=signal_bucket, control_bucket=control_bucket
                )["lift"]
            )
    if stats:
        lo = float(np.percentile(stats, 2.5))
        hi = float(np.percentile(stats, 97.5))
    else:
        lo = hi = 0.0
    return {"effective_month_block_count": effective, "lift": point, "ci95": (lo, hi)}


def non_overlapping_sensitivity(
    rows: list[dict],
    *,
    horizon_days: int,
    signal_bucket: str,
    control_bucket: str,
) -> dict:
    """Sensitivity over T-dates spaced ≥ the horizon apart (Codex C5 secondary).

    Spacing is enforced by EXACT day distance: a date is selected only if it is at
    least `horizon_days` after the previously selected date, so forward windows do
    not overlap; the lift sign must agree with the primary."""
    distinct = sorted({row["snapshot_date"] for row in rows})
    selected: list[date] = []
    for d in distinct:
        if not selected or (d - selected[-1]).days >= horizon_days:
            selected.append(d)

    selected_set = set(selected)
    signal = [r["fwd_delta"] for r in rows if r["bucket"] == signal_bucket and r["snapshot_date"] in selected_set]
    control = [r["fwd_delta"] for r in rows if r["bucket"] == control_bucket and r["snapshot_date"] in selected_set]
    lift = (statistics.median(signal) if signal else 0.0) - (statistics.median(control) if control else 0.0)
    sign = "positive" if lift > 0 else "negative" if lift < 0 else "zero"
    return {"selected_dates": selected, "sign": sign}


# ── 7. Claim level (no-look-ahead guard) ──────────────────────────────────────


def derive_claim_level(test_dates: list[date], *, training_cutoff: Optional[date]) -> str:
    """`tradeable_historical_edge` ONLY if the model's training cutoff ≤ every test
    date (true vintage); otherwise the fail-safe `current_model_retrospective_
    diagnostic` (spec §3.1 — re-scoring a model trained on post-T outcomes still
    leaks the future)."""
    if training_cutoff is None or not test_dates:
        return CLAIM_RETROSPECTIVE
    if all(training_cutoff <= td for td in test_dates):
        return CLAIM_TRADEABLE
    return CLAIM_RETROSPECTIVE


# ── 8. Verdict logic ──────────────────────────────────────────────────────────


def _ci_excludes_zero(ci: tuple[float, float]) -> bool:
    lo, hi = ci
    return not (lo <= 0.0 <= hi)


def _horizon_passes(res: dict) -> bool:
    return (
        res["lift_HIGH"] > 0.0
        and res["lift_LOW"] > 0.0
        and _ci_excludes_zero(res["ci_HIGH"])
        and _ci_excludes_zero(res["ci_LOW"])
        and res["effect_size_HIGH"] >= EFFECT_SIZE_FLOOR
        and res["non_overlapping_sensitivity_sign"] == "positive"
    )


def evaluate_verdict(
    *,
    horizon_results: dict[int, dict],
    coverage: dict,
    stability: dict,
    source_family_status: str,
    pit_model_status: str,
) -> dict:
    """Pre-registered verdict (spec §4/§6). Fail-closed gates precede power gates,
    which precede the statistical PASS/FAIL. `decision_supported` is always False."""
    verdict = _resolve_verdict(
        horizon_results=horizon_results,
        coverage=coverage,
        stability=stability,
        source_family_status=source_family_status,
        pit_model_status=pit_model_status,
    )
    return {"verdict": verdict, "decision_supported": False}


def _resolve_verdict(
    *,
    horizon_results: dict[int, dict],
    coverage: dict,
    stability: dict,
    source_family_status: str,
    pit_model_status: str,
) -> str:
    # Fail-closed gates (order: source -> PIT -> identity coverage).
    if source_family_status != "single_source":
        return "SOURCE_INADEQUATE"
    if pit_model_status != "ok":
        return "MODEL_PIT_INADEQUATE"
    if coverage["identity_coverage"] < MIN_IDENTITY_COVERAGE:
        return "IDENTITY_COVERAGE_INADEQUATE"

    # Power / coverage floors -> UNDERPOWERED.
    if coverage["joined_observations"] < MIN_JOINED_OBS:
        return "UNDERPOWERED"
    usable = coverage["usable_t_dates_by_horizon"]
    for res in horizon_results.values():
        if res["effective_month_block_count"] < MIN_EFFECTIVE_BLOCKS:
            return "UNDERPOWERED"
        for n in res["n_by_bucket"].values():
            if n < MIN_BUCKET_OBS:
                return "UNDERPOWERED"
    for h in horizon_results:
        if usable.get(h, 0) < MIN_USABLE_T_DATES:
            return "UNDERPOWERED"

    # Statistical PASS requires both horizons + global stability.
    horizons_pass = all(_horizon_passes(res) for res in horizon_results.values())
    stability_pass = (
        all(s == "positive" for s in stability["leave_one_month_out_high_signs"])
        and stability["top_position_contribution"] <= MAX_TOP_POSITION_SHARE
        and stability["top_position_excluded_high_sign"] == "positive"
    )
    return "PASS" if (horizons_pass and stability_pass) else "FAIL"


# ── 9. Falsification helpers ──────────────────────────────────────────────────


def bucket_counts(rows: list[dict], *, group_by: list[str]) -> dict:
    """Per-group bucket multiset (used to prove a label shuffle preserves counts)."""
    out: dict[tuple, dict[str, int]] = {}
    for row in rows:
        key = tuple(row[g] for g in group_by)
        grp = out.setdefault(key, {})
        grp[row["bucket"]] = grp.get(row["bucket"], 0) + 1
    return out


def shuffle_labels_within_date_position(rows: list[dict], *, rng_seed: int) -> list[dict]:
    """Permute bucket labels within each (snapshot_date, position) group — the
    null model: counts per group are preserved, assignments are destroyed. A real
    edge must vanish under this shuffle (spec §5)."""
    rng = random.Random(rng_seed)
    groups: dict[tuple, list[int]] = {}
    for idx, row in enumerate(rows):
        groups.setdefault((row["snapshot_date"], row["position"]), []).append(idx)

    out = [dict(row) for row in rows]
    for indices in groups.values():
        labels = [rows[i]["bucket"] for i in indices]
        rng.shuffle(labels)
        for i, label in zip(indices, labels):
            out[i]["bucket"] = label
    return out


def assert_no_bucket_lookahead(*, bucket_snapshot_date: date, feature_as_of: date) -> None:
    """Guard: features used to assign a `T` bucket must not postdate `T` (spec §5
    date-leakage guard)."""
    if feature_as_of > bucket_snapshot_date:
        raise ValueError(
            "look-ahead: bucket feature_as_of "
            f"{feature_as_of} postdates snapshot {bucket_snapshot_date}"
        )


def assert_single_source_family(rows: list[dict]) -> None:
    """A verdict must be computed from a single market source family (spec §2/§5)."""
    sources = {row["source"] for row in rows}
    if len(sources) > 1:
        raise ValueError(f"single source family required, got {sorted(sources)}")
