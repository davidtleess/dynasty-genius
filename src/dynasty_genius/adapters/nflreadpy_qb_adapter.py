"""nflreadpy QB professional-context adapter.

This adapter normalizes active-QB NFL telemetry for roster-facing context only.
It intentionally returns the narrow QB_CONTEXT_COLUMNS shape and does not
write to Engine A or Engine B feature matrices.
"""
from __future__ import annotations

from typing import Any, Iterable

import pandas as pd

from src.dynasty_genius.models.engine_a_contract import QB_CONTEXT_COLUMNS


def _empty_result() -> dict[str, Any]:
    return {field: None for field in QB_CONTEXT_COLUMNS}


def load_pbp(seasons: list[int]):
    """Load nflreadpy play-by-play lazily so tests can mock without nflreadpy."""
    import nflreadpy as nfl

    return nfl.load_pbp(seasons)


def _to_pandas(frame: Any) -> pd.DataFrame:
    if frame is None:
        return pd.DataFrame()
    if isinstance(frame, pd.DataFrame):
        return frame.copy()
    if hasattr(frame, "to_pandas"):
        return frame.to_pandas()
    return pd.DataFrame(frame)


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _first_existing(columns: Iterable[str], df: pd.DataFrame) -> str | None:
    for column in columns:
        if column in df.columns:
            return column
    return None


def _round_or_none(value: float | None) -> float | None:
    if value is None or pd.isna(value):
        return None
    return round(float(value), 4)


def fetch_qb_nfl_stats(gsis_id: str, seasons: list[int]) -> dict[str, Any]:
    """Fetch and aggregate QB EPA/CPOE context for one GSIS id and seasons list."""
    df = _to_pandas(load_pbp(list(seasons)))
    if df.empty:
        return _empty_result()

    player_id_column = _first_existing(["passer_player_id", "player_id", "gsis_id"], df)
    if not player_id_column or "qb_dropback" not in df.columns:
        return _empty_result()

    player_rows = df[df[player_id_column] == gsis_id].copy()
    if player_rows.empty:
        return {
            "epa_per_dropback": None,
            "cpoe": None,
            "dakota": None,
            "dropback_count": 0,
            "pass_attempts": 0,
        }

    dropbacks = player_rows[_numeric(player_rows["qb_dropback"]).fillna(0) > 0].copy()
    dropback_count = int(len(dropbacks))

    pass_attempts = 0
    if "pass_attempt" in player_rows.columns:
        pass_attempts = int(_numeric(player_rows["pass_attempt"]).fillna(0).sum())

    if dropback_count == 0:
        return {
            "epa_per_dropback": None,
            "cpoe": None,
            "dakota": None,
            "dropback_count": 0,
            "pass_attempts": pass_attempts,
        }

    epa_per_dropback = None
    if "epa" in dropbacks.columns:
        epa_total = _numeric(dropbacks["epa"]).sum(min_count=1)
        if not pd.isna(epa_total):
            epa_per_dropback = float(epa_total) / dropback_count

    cpoe = None
    if "cpoe" in dropbacks.columns:
        cpoe_mean = _numeric(dropbacks["cpoe"]).dropna().mean()
        if not pd.isna(cpoe_mean):
            cpoe = float(cpoe_mean)

    dakota = None
    if epa_per_dropback is not None and cpoe is not None:
        dakota = (epa_per_dropback * 0.7) + ((cpoe / 100.0) * 0.3)

    return {
        "epa_per_dropback": _round_or_none(epa_per_dropback),
        "cpoe": _round_or_none(cpoe),
        "dakota": _round_or_none(dakota),
        "dropback_count": dropback_count,
        "pass_attempts": pass_attempts,
    }
