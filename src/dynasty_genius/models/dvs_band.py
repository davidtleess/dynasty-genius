"""The DVS band — how far to trust the number.

DG-128 (2026-09-01). David's condition: "the band ships with the number … a prior-dominated
estimate must not render with the same authority as a measured one." The form below was
pre-committed in the ticket at 23:55Z, before any band was computed on a real player, and its
constants are the SERVED models' own published holdout error — nothing fitted, nothing chosen by
looking at a ranking. If a measured number ever makes it look wrong, the ticket is amended in a
new dated section; this module is never bent to a second form to see which reads better.

Half-widths in DVS points, one holdout RMSE each:

    sigma_B[pos]    = rmse(validation_report_{pos}.json, ENGINE_B_SIGMA_RUN, metrics_v2) / DVS_SCALE_ANCHOR_PPG[pos] * 100
    sigma_A[pos]    = rmse({POS}_metadata.json,          ENGINE_A_SIGMA_RUN, metrics)    / DVS_SCALE_ANCHOR_PPG[pos] * 100
    sigma_A_v3[TE]  = oof_rmse(scripts/promote_head_a_te_v3.py, ENGINE_A_V3_SIGMA_RUN)   / DVS_SCALE_ANCHOR_PPG[TE]  * 100

DG-159 moved that denominator, and sigma is the member of this family most easily
forgotten: it is stored in SCORE points while the error it represents is a fact in
points per game. Leave it behind while the scale shrinks and the band silently
describes a scale that no longer exists — measured before the change, a tight-end
band left at 23.6 would have spanned 1.57x the whole replacement-to-best range.
Recomputed against the same denominator the score divides by, it is the same real
quantity and its share of the scale does not move at all.

The two engines' tight-end sigmas both used to read 23.6 and meant different
football — 2.2223 points a game against Engine B's old ceiling, 2.1520 against
Engine A's. One denominator separates them (11.1 and 10.7). The coincidence is
gone, which matters: identical stored values invite fixing one and copying it
across, and that would get Engine A wrong with nothing anywhere to reveal it.

    measured  (dvs_engine B):      DVS ± sigma_B
    prior     (dvs_engine A):      DVS ± sigma_A   — or sigma_A_v3 where the v3 TE head produced the number
    blended   (dvs_engine blend):  DVS ± sqrt( sigma_B² + ((1 − w_B) · (sigma_A + |DVS_A − DVS_B|))² )

Engine A is two heads, not one. The v2 ridge (pick/round/age) scores every position; the v3
TE head (Head A Ridge over draft slot + college features, promoted 2026-05-24) scores a TE
prospect whenever its college features are present, and the assembler tries it first. The
2026-09-01 pre-commitment named only the v2 error; the 22 v3-scored TE rookie cards would
have carried the v2 ridge's error around a number the v2 ridge did not produce. Amended
2026-09-02 (ticket, dated section): the v3 head carries its own out-of-fold error. Its
metadata JSON is unrecoverable (see reference notes); the promotion script that wrote it
records the RMSE it measured — 4-fold leave-one-class-out over the 2018-21 classes, target
best3of4_ppg — as a constant, and that constant is the surviving record.

Read: the measured model's error is always carried; on top of it, the share of the prior's error
and of the two engines' disagreement that the sample has not yet resolved, combined root-sum-square
as independent error terms conventionally are. By construction the blended band is strictly wider
than the measured band (w_B < 1), narrows monotonically as n grows, and tends to the measured band
as w_B → 1. It is a 1-RMSE band — roughly 68% if errors were normal — and it is NOT scaled by
P(plays), which leaves it wider than the arithmetic would give (conservative; P carries model error
of its own that this absorbs in part). A measured Engine B player sits at ±11–22 points of a
100-point scale, narrowest at tight end where the model is surest in points a game. That is the
served model's published error; the band's job is to show it.

Provenance is tested, not asserted: tests/contract/test_dg128_dvs_band.py recomputes every
pinned value from the tracked artifacts named here. And it is enforced at serving time, not only
at test time: assert_band_sigma_runs_match_served_models() reads the three pointers the scorers
load — engine_b/v2_manifest.json for B, models/latest.json for A, head_a/v3_manifest.json for
the v3 head — and refuses to build a batch whose band would describe a run other than the one
serving. A retrain that moves a manifest therefore stops the refresh until this pin (and the
constants above) move with it; the pins also ride in every PVO's source_versions so a stale
artifact is legible after the fact. A position the B manifest leaves at ``None`` is refused
too: EngineBService falls back to its v1 bundle there, the number still serves as dvs_engine
"B", and no error is pinned for v1 — the band would be drawn from a model that did not draw the
number.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ENGINE_B_SIGMA_RUN = "20260831T204458Z"
ENGINE_A_SIGMA_RUN = "20260502T153931Z"
ENGINE_A_V3_SIGMA_RUN = "20260524T140748Z"

# The `engine_used` the v3 head stamps on its result (scoring/engine_a.py, EngineAV3Scorer).
ENGINE_A_V3_HEAD = "engine_a_v3_head_a_ridge"

# The three pointers the scorers actually load; the pins above must name the same runs.
# The v3 pointer is optional to the scorer (absent → the v2 ridge serves every prospect)
# and so optional here; where it exists, every head it names must be the pinned run.
_ROOT = Path(__file__).resolve().parents[3]
ENGINE_B_MANIFEST_PATH = _ROOT / "app/data/models/engine_b/v2_manifest.json"
ENGINE_A_LATEST_PATH = _ROOT / "app/data/models/latest.json"
ENGINE_A_V3_MANIFEST_PATH = _ROOT / "app/data/models/head_a/v3_manifest.json"

# One holdout RMSE of E[points | plays] on the 2022-23 holdout, in DVS points.
# (4.5086 / 3.5856 / 2.8972 / 2.2223 points a game, over the 20.1 anchor.)
DVS_SIGMA_B: dict[str, float] = {
    "QB": 22.4,
    "RB": 17.8,
    "WR": 14.4,
    "TE": 11.1,
}

# One holdout RMSE of y24_ppg on the 2021 holdout (10-35 rows per position), in DVS points.
# (6.6720 / 2.9770 / 4.1120 / 2.1520 points a game, over the same anchor.)
DVS_SIGMA_A: dict[str, float] = {
    "QB": 33.2,
    "RB": 14.8,
    "WR": 20.5,
    "TE": 10.7,
}

# One out-of-fold RMSE of best3of4_ppg for the v3 TE head (2.7051 PPG, 4-fold LOOCV over the
# 2018-21 classes; scripts/promote_head_a_te_v3.py), in DVS points. Only the heads the v3
# pointer may name belong here; a promoted head with no entry is refused, not defaulted.
DVS_SIGMA_A_V3: dict[str, float] = {
    "TE": 13.5,
}


def dvs_band(
    dvs: float | None,
    position: str,
    *,
    engine: str | None,
    w_b: float | None = None,
    dvs_a: float | None = None,
    dvs_b: float | None = None,
    prior_head: str | None = None,
) -> tuple[float, float] | tuple[None, None]:
    """(low, high) around `dvs`, clamped to [0, 100] and rounded like the score (1 dp).

    `engine` is the value of `dvs_engine` — "B", "A" or "blend". For a blend, `dvs_a` and
    `dvs_b` are the two components EXACTLY as they entered the blend (B hurdle-adjusted and
    clamped) and `w_b` is the served weight. `prior_head` is the Engine A result's
    `engine_used` — which head produced the prior — and selects sigma_A_v3 for the v3 TE
    head; anything else (the v2 ridge, or no Engine A result) is the v2 error. No score, no
    band. A missing sigma or a blend without its components is refused rather than guessed:
    a bare number where a band was promised is the exact thing this module exists to prevent.

    `engine` None with a score is the assembler's caller-supplied seam
    (features["dynasty_value_score"]) — no engine produced the number, so no published error
    can be claimed for it and the band is null. The serving batch never takes that seam: its
    feature rows carry no such column.
    """
    if dvs is None or engine is None:
        return (None, None)
    pos = position.upper()
    sigma_a_by_head = DVS_SIGMA_A_V3 if prior_head == ENGINE_A_V3_HEAD else DVS_SIGMA_A
    if pos not in DVS_SIGMA_B or pos not in sigma_a_by_head:
        raise ValueError("dvs_band_sigma_missing")
    sigma_a = sigma_a_by_head[pos]

    if engine == "B":
        half = DVS_SIGMA_B[pos]
    elif engine == "A":
        half = sigma_a
    elif engine == "blend":
        if w_b is None or dvs_a is None or dvs_b is None:
            raise ValueError("dvs_band_blend_components_missing")
        unresolved = (1.0 - w_b) * (sigma_a + abs(dvs_a - dvs_b))
        half = math.sqrt(DVS_SIGMA_B[pos] ** 2 + unresolved**2)
    else:
        raise ValueError("dvs_band_engine_unknown")

    low = round(max(0.0, dvs - half), 1)
    high = round(min(100.0, dvs + half), 1)
    return (low, high)


def assert_band_sigma_runs_match_served_models(
    *,
    manifest_path: Path = ENGINE_B_MANIFEST_PATH,
    latest_path: Path = ENGINE_A_LATEST_PATH,
    v3_manifest_path: Path = ENGINE_A_V3_MANIFEST_PATH,
) -> None:
    """Refuse to band against a run the served models did not come from.

    Reads the same pointers the scorers load. A position the B manifest leaves at ``None``
    is refused: the service falls back to the v1 bundle there and no error is pinned for
    it. A missing or unreadable B or A pointer is refused, not assumed: a tree that cannot
    say what it serves cannot say how wide to draw the band either. The v3 pointer is the
    one the scorer itself treats as optional — absent, the v2 ridge serves every prospect
    and there is nothing to pin; present, every head it names must be the pinned run and
    must have a pinned error.
    """
    try:
        manifest: dict[str, str | None] = json.loads(manifest_path.read_text())
        latest: dict[str, object] = json.loads(latest_path.read_text())
    except (OSError, ValueError) as exc:
        raise ValueError("dvs_band_sigma_pointer_missing") from exc

    for position, artifact in manifest.items():
        if artifact is None:
            raise ValueError(f"dvs_band_sigma_run_unpromoted:{position}")
        served_run = Path(artifact).parent.name
        if served_run != ENGINE_B_SIGMA_RUN:
            raise ValueError(f"dvs_band_sigma_run_stale:{position}:{served_run}")

    served_a_run = latest.get("model_version")
    if served_a_run != ENGINE_A_SIGMA_RUN:
        raise ValueError(f"dvs_band_sigma_run_stale:A:{served_a_run}")

    if not v3_manifest_path.exists():
        return
    try:
        v3_manifest: dict[str, str] = json.loads(v3_manifest_path.read_text())
    except (OSError, ValueError) as exc:
        raise ValueError("dvs_band_sigma_pointer_missing") from exc
    for position, artifact in v3_manifest.items():
        if position not in DVS_SIGMA_A_V3:
            raise ValueError(f"dvs_band_sigma_missing:A_v3:{position}")
        served_run = Path(artifact).parent.name
        if served_run != ENGINE_A_V3_SIGMA_RUN:
            raise ValueError(f"dvs_band_sigma_run_stale:A_v3:{position}:{served_run}")
