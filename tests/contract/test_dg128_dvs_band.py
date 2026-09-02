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
