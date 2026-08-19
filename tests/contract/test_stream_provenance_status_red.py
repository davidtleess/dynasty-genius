"""DG-023 — the health gate labels good participation data "empty".

RED rows for the stream-provenance status defect.

``_load_stream_isolated`` derives ``status`` from ``seasons_present``, which
fuses two independent facts: *did rows load* and *is a season observable*.
``nflreadpy.load_participation`` returns a frame with **no ``season`` column**,
so 45,184 loaded rows are reported ``loaded_empty`` — and ``/api/health``
renders that as ``EMPTY: participation``.

Measured 2026-08-19 against the shipped artifacts, from both directions:

- ``app/data/features_runtime/feature_refresh_latest_report.json`` →
  ``participation.status == "loaded_empty"``, ``effective_season == null``.
- ``app/data/features_runtime/engine_b_features_runtime.csv``, 2025 inference
  season → ``route_participation`` / ``tprr`` / ``yprr`` each populated
  **498 / 505 (98.6%)**. The data loaded and reached the feature build.

A health signal that cries wolf on good data is worse than none, because a real
failure looks identical.

The ticket's "done looks like" — *the provenance reports what actually happened
— rows loaded and the season observed* — is unreachable while the block records
no row count: nothing in the artifact can tell "rows loaded, no season column"
from "genuinely zero rows". ``row_count`` is therefore part of this contract,
not a nicety.

Preserved from the F1 ruling and re-pinned here: ``effective_season`` is an
OBSERVED fact about returned rows and stays ``None`` when no season is
observable. This change decouples ``status`` from it; it does not weaken it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from run_feature_refresh import _load_stream_isolated  # noqa: E402


class _FakeNfl:
    """Minimal stand-in exposing one loader attribute, as the real client does."""

    def __init__(self, frame: pd.DataFrame) -> None:
        self._frame = frame

    def load_participation(self, seasons: list[int]) -> pd.DataFrame:  # noqa: ARG002
        return self._frame


def _participation_frame(rows: int) -> pd.DataFrame:
    """A participation-shaped frame: real rows, and NO ``season`` column.

    This is the shape the real loader returns, and the whole cause of the bug.
    """
    return pd.DataFrame(
        {
            "nflverse_player_id": [f"00-00{i:05d}" for i in range(rows)],
            "offense_snaps": [30 + i for i in range(rows)],
            "offense_pct": [0.75] * rows,
        }
    )


def test_rows_without_a_season_column_are_loaded_not_empty() -> None:
    """The defect. 45,184 rows with no ``season`` column are not an empty frame."""
    frame, prov = _load_stream_isolated(
        _FakeNfl(_participation_frame(3)), "load_participation", [2025]
    )

    assert len(frame) == 3
    assert prov["status"] == "loaded", (
        "a frame carrying rows must never be reported `loaded_empty` merely "
        "because no `season` column is present"
    )


def test_effective_season_stays_none_when_unobservable() -> None:
    """F1 is preserved: an unobservable season is reported as unobserved."""
    _, prov = _load_stream_isolated(
        _FakeNfl(_participation_frame(3)), "load_participation", [2025]
    )

    assert prov["effective_season"] is None, (
        "reporting a season that was never observed would assert coverage that "
        "does not exist — the original defect class"
    )


def test_a_genuinely_empty_frame_is_still_loaded_empty() -> None:
    """The negative control. Decoupling status must not blind the real signal."""
    _, prov = _load_stream_isolated(
        _FakeNfl(_participation_frame(0)), "load_participation", [2025]
    )

    assert prov["status"] == "loaded_empty"
    assert prov["effective_season"] is None


def test_rows_with_a_season_column_report_the_observed_season() -> None:
    """The nominal path is unchanged: observed season is the max of returned rows."""
    frame = _participation_frame(3)
    frame["season"] = [2023, 2025, 2024]

    _, prov = _load_stream_isolated(_FakeNfl(frame), "load_participation", [2025])

    assert prov["status"] == "loaded"
    assert prov["effective_season"] == 2025


@pytest.mark.parametrize("rows", [0, 3])
def test_provenance_reports_the_row_count(rows: int) -> None:
    """Without a count, "no season column" and "zero rows" are indistinguishable.

    That indistinguishability is what let a false label stand unexamined.
    """
    _, prov = _load_stream_isolated(
        _FakeNfl(_participation_frame(rows)), "load_participation", [2025]
    )

    assert prov["row_count"] == rows


def test_an_unavailable_stream_reports_no_rows_rather_than_zero() -> None:
    """A stream that never loaded has no row count — it is not a zero-row load.

    ``unavailable`` and ``loaded_empty`` are different facts and must stay so.
    """

    class _AlwaysFails:
        def load_participation(self, seasons: list[int]) -> pd.DataFrame:  # noqa: ARG002
            raise ConnectionError("upstream parquet missing")

    frame, prov = _load_stream_isolated(_AlwaysFails(), "load_participation", [2025])

    assert frame.empty
    assert prov["status"] == "unavailable"
    assert prov["error_type"] == "ConnectionError"
    assert prov["row_count"] is None
