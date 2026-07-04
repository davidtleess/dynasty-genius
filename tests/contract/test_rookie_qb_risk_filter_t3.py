"""Rookie-QB risk filter v2 prior-table wiring contract (T3 RED)."""

from __future__ import annotations

import importlib
import math
from pathlib import Path
from typing import Any

import pandas as pd
import pytest


def _module() -> Any:
    return importlib.import_module("src.dynasty_genius.features.qb_rookie_risk_filter")


def _inputs() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"player_id": "round1_qb", "position": "QB", "draft_number": 12, "age_at_entry": 21.4},
            {"player_id": "round2_qb", "position": "QB", "draft_number": 40, "age_at_entry": 22.0},
            {"player_id": "day3_qb", "position": "QB", "draft_number": 100, "age_at_entry": 23.1},
            {"player_id": "udfa_qb", "position": "QB", "draft_number": pd.NA, "age_at_entry": 22.8},
        ]
    )


def _prior_artifact() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    values = {
        "round_1_picks_1_32": {1: 0.81, 2: 0.71, 3: 0.72},
        "round_2_picks_33_64": {1: 0.75, 2: 0.25, 3: 0.33},
        "day3_picks_65_plus": {1: 0.186, 2: 0.023, 3: 0.030},
        "undrafted": {1: 0.014, 2: 0.014, 3: 0.0},
    }
    counts = {
        "round_1_picks_1_32": {1: 21, 2: 21, 3: 18},
        "round_2_picks_33_64": {1: 4, 2: 4, 3: 3},
        "day3_picks_65_plus": {1: 43, 2: 43, 3: 33},
        "undrafted": {1: 70, 2: 70, 3: 61},
    }
    for band, horizons in values.items():
        for horizon, rate in horizons.items():
            n = counts[band][horizon]
            rows.append(
                {
                    "capital_band": band,
                    "horizon": horizon,
                    "n": n,
                    "positives": round(rate * n),
                    "rate": rate,
                    "basis": {"games_and_snap": 0, "games_only": 0, "absent_role_row": n},
                }
            )
    return {
        "metadata": {
            "config_version": 2,
            "generated_at": "2026-07-04T13:42:39+00:00",
            "generation_command": "fixture",
            "machinery_repo_sha": "fixture",
            "source_caveat": "fixture",
            "cohort_entry_years": [2018, 2019, 2020, 2021, 2022, 2023],
            "max_available_role_season": 2025,
            "decision_supported": False,
        },
        "rows": rows,
        "diagnostics": {"structural_exclusions": [], "quarantined_entries": []},
        "prediction_check": {"status": "report_only", "gating": False, "checks": []},
        "decision_supported": False,
    }


def _write_table(tmp_path: Path, artifact: dict[str, Any] | str) -> Path:
    path = tmp_path / "rookie_qb_prior_table_v2.json"
    if isinstance(artifact, str):
        path.write_text(artifact)
    else:
        import json

        path.write_text(json.dumps(artifact))
    return path


def _rows(result: Any) -> pd.DataFrame:
    rows = result.rows
    assert isinstance(rows, pd.DataFrame)
    return rows.set_index("player_id")


def test_filter_uses_v2_h1_prior_by_finer_band_while_classifications_stay_stable(
    tmp_path: Path,
) -> None:
    module = _module()
    table = _prior_artifact()
    path = _write_table(tmp_path, table)

    rows = _rows(module.classify_rookie_qb_risk(_inputs(), prior_table_path=path))

    assert rows.loc["round1_qb", "risk_filter_classification"] == "capital_qualified"
    assert rows.loc["round2_qb", "risk_filter_classification"] == "capital_qualified"
    assert rows.loc["day3_qb", "risk_filter_classification"] == "day3_insufficient_capital"
    assert rows.loc["udfa_qb", "risk_filter_classification"] == "undrafted_insufficient_capital"

    assert rows.loc["round1_qb", "capital_band"] == "round_1_picks_1_32"
    assert rows.loc["round2_qb", "capital_band"] == "round_2_picks_33_64"
    assert rows.loc["day3_qb", "capital_band"] == "day3_picks_65_plus"
    assert rows.loc["udfa_qb", "capital_band"] == "undrafted"

    for player_id, band in rows["capital_band"].items():
        h1 = next(
            row["rate"]
            for row in table["rows"]
            if row["capital_band"] == band and row["horizon"] == 1
        )
        assert math.isclose(rows.loc[player_id, "base_rate_survival_prior"], h1)


def test_filter_discloses_v2_prior_basis_and_available_horizons(tmp_path: Path) -> None:
    module = _module()
    path = _write_table(tmp_path, _prior_artifact())

    rows = _rows(module.classify_rookie_qb_risk(_inputs(), prior_table_path=path))

    for row in rows.itertuples():
        assert row.prior_basis == {
            "source": "app/config/rookie_qb_prior_table_v2.json",
            "config_version": 2,
        }
        assert row.survival_priors_by_horizon == {
            1: pytest.approx(row.base_rate_survival_prior),
            2: pytest.approx(row.survival_priors_by_horizon[2]),
            3: pytest.approx(row.survival_priors_by_horizon[3]),
        }
    assert rows.loc["round2_qb", "survival_priors_by_horizon"][1] == pytest.approx(0.75)
    assert rows.loc["round2_qb", "survival_priors_by_horizon"][2] == pytest.approx(0.25)


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda artifact: {**artifact, "rows": [*artifact["rows"], artifact["rows"][0]]}, "duplicate"),
        (
            lambda artifact: {
                **artifact,
                "rows": [
                    {**row, "n": 0, "positives": 0, "rate": None}
                    if row["capital_band"] == "undrafted" and row["horizon"] == 1
                    else row
                    for row in artifact["rows"]
                ],
            },
            "runtime-consumed H1",
        ),
        (lambda artifact: {**artifact, "metadata": {**artifact["metadata"], "config_version": 1}}, "config_version"),
    ],
)
def test_filter_fails_closed_on_invalid_v2_table(
    tmp_path: Path,
    mutate: Any,
    expected: str,
) -> None:
    module = _module()
    path = _write_table(tmp_path, mutate(_prior_artifact()))

    with pytest.raises(ValueError, match=expected):
        module.classify_rookie_qb_risk(_inputs(), prior_table_path=path)


def test_filter_fails_closed_on_missing_or_malformed_v2_table(tmp_path: Path) -> None:
    module = _module()
    missing = tmp_path / "missing.json"
    malformed = _write_table(tmp_path, "{not-json")

    with pytest.raises(ValueError, match="prior table.*missing|No such file"):
        module.classify_rookie_qb_risk(_inputs(), prior_table_path=missing)
    with pytest.raises(ValueError, match="prior table.*malformed|JSON"):
        module.classify_rookie_qb_risk(_inputs(), prior_table_path=malformed)


def test_filter_keeps_exact_set_input_wall_and_no_engine_b_columns(tmp_path: Path) -> None:
    module = _module()
    path = _write_table(tmp_path, _prior_artifact())

    with pytest.raises(ValueError, match="NFL usage|leakage"):
        module.classify_rookie_qb_risk(
            _inputs().assign(ppg_t=12.0),
            prior_table_path=path,
        )
    rows = module.classify_rookie_qb_risk(_inputs(), prior_table_path=path).rows
    forbidden = {"ppg_t", "snap_share", "epa_per_dropback", "games_t", "draft_capital_prior"}
    assert not forbidden & set(rows.columns)


def test_filter_removes_or_quarantines_v1_scalar_constants() -> None:
    module = _module()
    source = module.__loader__.get_source(module.__name__)
    assert source is not None
    assert "registered_capital_band_prior_v1" not in source
    assert "BASE_RATE_SURVIVAL_PRIOR_V1" not in source
