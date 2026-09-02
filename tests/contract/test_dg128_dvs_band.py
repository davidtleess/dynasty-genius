"""DG-128 (2026-09-01): the band ships with the number.

The form was pre-committed in the ticket (23:55Z, before any band was computed on a real player).
These tests pin that form and its constants' provenance. If a measured number ever makes the
form look wrong, the ticket is amended in a new dated section — the tests are not bent to a
second form.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from src.dynasty_genius.models.dvs_band import (
    DVS_SIGMA_A,
    DVS_SIGMA_B,
    ENGINE_A_SIGMA_RUN,
    ENGINE_B_SIGMA_RUN,
    assert_band_sigma_runs_match_served_models,
    dvs_band,
)
from src.dynasty_genius.models.engine_b_contract import ENGINE_B_P90_PPG
from src.dynasty_genius.scoring.engine_a import ENGINE_A_P90_PPG

ROOT = Path(__file__).resolve().parents[2]


def test_a_measured_player_carries_one_holdout_rmse_each_side() -> None:
    assert dvs_band(50.0, "WR", engine="B") == (30.0, 70.0)


def test_a_prior_only_player_carries_engine_a_s_own_error() -> None:
    assert dvs_band(50.0, "WR", engine="A") == (17.6, 82.4)


def test_the_blended_band_is_root_sum_square_of_b_error_and_the_unresolved_share() -> None:
    w_b, dvs_a, dvs_b = 0.5, 80.0, 60.0
    half = math.sqrt(20.0**2 + ((1 - w_b) * (32.4 + abs(dvs_a - dvs_b))) ** 2)
    low, high = dvs_band(70.0, "WR", engine="blend", w_b=w_b, dvs_a=dvs_a, dvs_b=dvs_b)
    assert low == round(70.0 - half, 1)
    assert high == 100.0  # 70 + 32.96 clamps like the score does


def test_the_blended_band_is_strictly_wider_than_measured_and_tends_to_it() -> None:
    measured_low, measured_high = dvs_band(50.0, "RB", engine="B")
    for w_b in (0.1, 0.5, 0.9):
        low, high = dvs_band(50.0, "RB", engine="blend", w_b=w_b, dvs_a=55.0, dvs_b=45.0)
        assert low < measured_low and high > measured_high
    assert dvs_band(50.0, "RB", engine="blend", w_b=1.0, dvs_a=55.0, dvs_b=45.0) == (
        measured_low,
        measured_high,
    )


def test_the_blended_band_narrows_as_the_sample_grows() -> None:
    widths = [
        high - low
        for low, high in (
            dvs_band(50.0, "TE", engine="blend", w_b=w_b, dvs_a=70.0, dvs_b=40.0)
            for w_b in (0.2, 0.4, 0.6, 0.8)
        )
    ]
    assert widths == sorted(widths, reverse=True)
    assert len(set(widths)) == 4


def test_no_score_means_no_band() -> None:
    assert dvs_band(None, "WR", engine="B") == (None, None)


def test_a_score_no_engine_produced_has_no_error_to_claim() -> None:
    # The assembler's caller-supplied seam (features["dynasty_value_score"], test/dev only —
    # the serving batch's feature rows carry no such column). dvs_engine None says why.
    assert dvs_band(85.0, "QB", engine=None) == (None, None)


def test_the_band_is_clamped_to_the_score_s_scale() -> None:
    assert dvs_band(5.0, "QB", engine="B") == (0.0, 27.4)
    assert dvs_band(95.0, "QB", engine="A") == (55.0, 100.0)


def test_a_blend_without_its_components_is_refused_not_guessed() -> None:
    with pytest.raises(ValueError, match="dvs_band_blend_components_missing"):
        dvs_band(50.0, "WR", engine="blend", w_b=0.5, dvs_a=None, dvs_b=60.0)


def test_a_position_without_a_published_error_is_refused_not_guessed() -> None:
    with pytest.raises(ValueError, match="dvs_band_sigma_missing"):
        dvs_band(50.0, "K", engine="B")


# ── Provenance: the pinned constants ARE the served models' published holdout error ─────


@pytest.mark.parametrize("position", ["QB", "RB", "WR", "TE"])
def test_sigma_b_is_the_engine_b_holdout_rmse_in_dvs_units(position: str) -> None:
    report = json.loads(
        (
            ROOT
            / "app/data/models/engine_b/runs"
            / ENGINE_B_SIGMA_RUN
            / f"validation_report_{position.lower()}.json"
        ).read_text()
    )
    assert DVS_SIGMA_B[position] == round(
        report["metrics_v2"]["rmse"] / ENGINE_B_P90_PPG[position] * 100.0, 1
    )


@pytest.mark.parametrize("position", ["QB", "RB", "WR", "TE"])
def test_sigma_a_is_the_engine_a_holdout_rmse_in_dvs_units(position: str) -> None:
    metadata = json.loads(
        (ROOT / "app/data/models/runs" / ENGINE_A_SIGMA_RUN / f"{position}_metadata.json").read_text()
    )
    assert DVS_SIGMA_A[position] == round(
        metadata["metrics"]["rmse"] / ENGINE_A_P90_PPG[position] * 100.0, 1
    )


def test_sigma_a_is_pinned_to_the_engine_a_run_the_blend_actually_serves() -> None:
    # score_prospect loads app/data/models/latest.json (tracked); the pin must follow it.
    latest = json.loads((ROOT / "app/data/models/latest.json").read_text())
    assert latest["model_version"] == ENGINE_A_SIGMA_RUN


# ── Serving time: the pins must be the runs the served models came from ──────────

STALE_RUN = "20260915T090000Z"


def _served_pointers(
    tmp_path: Path, *, b_run: str, a_run: str, rb_run: str | None = None
) -> tuple[Path, Path]:
    def artifact(pos: str) -> str:
        run = rb_run if (pos == "RB" and rb_run) else b_run
        return f"app/data/models/engine_b/runs/{run}/{pos.lower()}_v2.pkl"

    manifest_path = tmp_path / "v2_manifest.json"
    manifest = {pos: artifact(pos) for pos in ("QB", "RB", "WR", "TE")}
    manifest_path.write_text(json.dumps(manifest))
    latest_path = tmp_path / "latest.json"
    latest_path.write_text(
        json.dumps({"model_version": a_run, "run_dir": f"app/data/models/runs/{a_run}"})
    )
    return manifest_path, latest_path


def _aligned_pointers(tmp_path: Path, **overrides: str) -> tuple[Path, Path]:
    pins = {"b_run": ENGINE_B_SIGMA_RUN, "a_run": ENGINE_A_SIGMA_RUN, **overrides}
    return _served_pointers(tmp_path, **pins)


def test_band_pins_that_match_the_served_runs_pass(tmp_path: Path) -> None:
    manifest_path, latest_path = _aligned_pointers(tmp_path)
    assert (
        assert_band_sigma_runs_match_served_models(
            manifest_path=manifest_path, latest_path=latest_path
        )
        is None
    )


def test_a_manifest_promoting_one_position_to_another_run_is_refused(
    tmp_path: Path,
) -> None:
    # A retrain that moves RB and nobody moves the pin: the RB band would describe a
    # model no longer serving — DG-132's stale-figures defect in a new shape.
    manifest_path, latest_path = _aligned_pointers(tmp_path, rb_run=STALE_RUN)
    with pytest.raises(ValueError, match=f"^dvs_band_sigma_run_stale:RB:{STALE_RUN}$"):
        assert_band_sigma_runs_match_served_models(
            manifest_path=manifest_path, latest_path=latest_path
        )


def test_an_engine_a_pointer_at_another_run_is_refused(tmp_path: Path) -> None:
    manifest_path, latest_path = _aligned_pointers(tmp_path, a_run=STALE_RUN)
    with pytest.raises(ValueError, match=f"^dvs_band_sigma_run_stale:A:{STALE_RUN}$"):
        assert_band_sigma_runs_match_served_models(
            manifest_path=manifest_path, latest_path=latest_path
        )


def test_a_position_the_manifest_leaves_unpromoted_is_not_a_mismatch(
    tmp_path: Path,
) -> None:
    manifest_path, latest_path = _aligned_pointers(tmp_path)
    manifest = json.loads(manifest_path.read_text())
    manifest["TE"] = None  # no bundle → no B score → no TE band; nothing to be stale
    manifest_path.write_text(json.dumps(manifest))
    assert (
        assert_band_sigma_runs_match_served_models(
            manifest_path=manifest_path, latest_path=latest_path
        )
        is None
    )


def test_a_missing_pointer_is_refused_not_assumed(tmp_path: Path) -> None:
    _manifest_path, latest_path = _aligned_pointers(tmp_path)
    with pytest.raises(ValueError, match="^dvs_band_sigma_pointer_missing$"):
        assert_band_sigma_runs_match_served_models(
            manifest_path=tmp_path / "absent.json", latest_path=latest_path
        )


def test_the_default_pointers_are_the_tracked_ones_this_tree_serves_from() -> None:
    # Reads the real tracked latest.json and, where present, the (gitignored) served
    # manifest. Absent manifest → the check refuses, which is the right answer for a
    # tree that cannot serve Engine B at all.
    manifest = ROOT / "app/data/models/engine_b/v2_manifest.json"
    if not manifest.exists():
        with pytest.raises(ValueError, match="^dvs_band_sigma_pointer_missing$"):
            assert_band_sigma_runs_match_served_models()
        return
    assert assert_band_sigma_runs_match_served_models() is None
