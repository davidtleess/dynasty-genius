"""The DVS band — how far to trust the number.

DG-128 (2026-09-01). David's condition: "the band ships with the number … a prior-dominated
estimate must not render with the same authority as a measured one." The form below was
pre-committed in the ticket at 23:55Z, before any band was computed on a real player, and its
constants are the SERVED models' own published holdout error — nothing fitted, nothing chosen by
looking at a ranking. If a measured number ever makes it look wrong, the ticket is amended in a
new dated section; this module is never bent to a second form to see which reads better.

Half-widths in DVS points, one holdout RMSE each:

    sigma_B[pos] = rmse(validation_report_{pos}.json, ENGINE_B_SIGMA_RUN, metrics_v2) / ENGINE_B_P90_PPG[pos] * 100
    sigma_A[pos] = rmse({POS}_metadata.json,          ENGINE_A_SIGMA_RUN, metrics)    / ENGINE_A_P90_PPG[pos] * 100

    measured  (dvs_engine B):      DVS ± sigma_B
    prior     (dvs_engine A):      DVS ± sigma_A
    blended   (dvs_engine blend):  DVS ± sqrt( sigma_B² + ((1 − w_B) · (sigma_A + |DVS_A − DVS_B|))² )

Read: the measured model's error is always carried; on top of it, the share of the prior's error
and of the two engines' disagreement that the sample has not yet resolved, combined root-sum-square
as independent error terms conventionally are. By construction the blended band is strictly wider
than the measured band (w_B < 1), narrows monotonically as n grows, and tends to the measured band
as w_B → 1. It is a 1-RMSE band — roughly 68% if errors were normal — and it is NOT scaled by
P(plays), which leaves it wider than the arithmetic would give (conservative; P carries model error
of its own that this absorbs in part). A measured Engine B player sits at ±20–23 points of a
100-point scale. That is the served model's published error; the band's job is to show it.

Provenance is tested, not asserted: tests/contract/test_dg128_dvs_band.py recomputes every pinned
value from the tracked artifacts named here and checks ENGINE_A_SIGMA_RUN against the tracked
latest.json pointer score_prospect loads. ENGINE_B_SIGMA_RUN is the run v2_manifest.json pointed at
on 2026-09-01; a retrain that moves the manifest must move this pin (the pin rides in every PVO's
source_versions so the mismatch is visible, not silent).
"""

from __future__ import annotations

import math

ENGINE_B_SIGMA_RUN = "20260831T204458Z"
ENGINE_A_SIGMA_RUN = "20260502T153931Z"

# One holdout RMSE of E[points | plays] on the 2022-23 holdout, in DVS points.
DVS_SIGMA_B: dict[str, float] = {
    "QB": 22.4,
    "RB": 22.8,
    "WR": 20.0,
    "TE": 23.6,
}

# One holdout RMSE of y24_ppg on the 2021 holdout (10-35 rows per position), in DVS points.
DVS_SIGMA_A: dict[str, float] = {
    "QB": 40.0,
    "RB": 20.4,
    "WR": 32.4,
    "TE": 23.6,
}


def dvs_band(
    dvs: float | None,
    position: str,
    *,
    engine: str | None,
    w_b: float | None = None,
    dvs_a: float | None = None,
    dvs_b: float | None = None,
) -> tuple[float, float] | tuple[None, None]:
    """(low, high) around `dvs`, clamped to [0, 100] and rounded like the score (1 dp).

    `engine` is the value of `dvs_engine` — "B", "A" or "blend". For a blend, `dvs_a` and
    `dvs_b` are the two components EXACTLY as they entered the blend (B hurdle-adjusted and
    clamped) and `w_b` is the served weight. No score, no band. A missing sigma or a blend
    without its components is refused rather than guessed: a bare number where a band was
    promised is the exact thing this module exists to prevent.

    `engine` None with a score is the assembler's caller-supplied seam
    (features["dynasty_value_score"]) — no engine produced the number, so no published error
    can be claimed for it and the band is null. The serving batch never takes that seam: its
    feature rows carry no such column.
    """
    if dvs is None or engine is None:
        return (None, None)
    pos = position.upper()
    if pos not in DVS_SIGMA_B or pos not in DVS_SIGMA_A:
        raise ValueError("dvs_band_sigma_missing")

    if engine == "B":
        half = DVS_SIGMA_B[pos]
    elif engine == "A":
        half = DVS_SIGMA_A[pos]
    elif engine == "blend":
        if w_b is None or dvs_a is None or dvs_b is None:
            raise ValueError("dvs_band_blend_components_missing")
        unresolved = (1.0 - w_b) * (DVS_SIGMA_A[pos] + abs(dvs_a - dvs_b))
        half = math.sqrt(DVS_SIGMA_B[pos] ** 2 + unresolved**2)
    else:
        raise ValueError("dvs_band_engine_unknown")

    low = round(max(0.0, dvs - half), 1)
    high = round(min(100.0, dvs + half), 1)
    return (low, high)
