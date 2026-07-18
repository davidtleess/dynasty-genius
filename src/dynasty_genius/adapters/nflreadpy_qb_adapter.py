"""nflreadpy QB professional-context adapter — and the QB-1 validation-study lane.

This adapter normalizes active-QB NFL telemetry for roster-facing context only.
It intentionally returns the narrow QB_CONTEXT_COLUMNS shape and does not
write to Engine A or Engine B feature matrices.

Single-adapter law (QB-1 spec v8, D1): this module is the repo's ONE nflreadpy
adapter, so the validation study's six-dataset ingestion lives here too, under
the ``validation_`` name prefix and the ``validation_study`` registry role
(``nflreadpy_qb_validation`` — a DISTINCT registry entry; the context lane and
its ``nflreadpy_qb_context`` definition are untouched). Study functions may be
CALLED only from ``src/dynasty_genius/eval/qb_validation/`` (the F33 wall);
they import nothing from that package. Raw snapshots are written BEFORE parse,
each with source timestamp + parser version + completeness status; stale,
empty, or column-drifted sources fail closed with a named reason — never a
silent substitution.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

import numpy as np
import pandas as pd

from src.dynasty_genius.models.engine_a_contract import QB_CONTEXT_COLUMNS

VALIDATION_PARSER_VERSION = "qb_validation_ingest.v2"

# Pinned per-dataset column sets (spec D1.1–D1.6). Every name below was
# verified against the LIVE nflreadpy 0.1.5 schema on 2026-07-17 (weekly/
# rosters/pbp probed on season 2024; players/draft_picks/ff_playerids full):
# weekly carries `passing_interceptions` (no bare `interceptions`) and the
# THREE split fumble columns (no aggregate `fumbles_lost`); players' name
# field is `display_name`; draft picks' name field is `pfr_player_name`
# (also proven by resources/prospect_fixtures/_frozen_2025/
# nflverse_draft_picks_2025_pin.json). The hash-pinned registration manifests
# remain the exhaustive authority; every pin is re-verified fail-closed
# against the live frame at ingestion, never substituted.
VALIDATION_DATASET_COLUMNS: dict[str, tuple[str, ...]] = {
    "weekly": (
        "player_id",
        "position",
        "team",
        "season",
        "week",
        "season_type",
        "attempts",
        "carries",
        "sacks_suffered",
        "passing_yards",
        "passing_tds",
        "passing_interceptions",
        "rushing_yards",
        "rushing_tds",
        "receptions",
        "receiving_yards",
        "receiving_tds",
        "sack_fumbles_lost",
        "rushing_fumbles_lost",
        "receiving_fumbles_lost",
        "passing_2pt_conversions",
        "rushing_2pt_conversions",
        "receiving_2pt_conversions",
    ),
    "players": ("gsis_id", "display_name", "birth_date", "college_name"),
    "rosters": ("season", "week", "gsis_id", "game_type", "status"),
    "ff_playerids": ("gsis_id", "sleeper_id", "name"),
    "draft_picks": (
        "season",
        "round",
        "pick",
        "gsis_id",
        "pfr_player_name",
        "age",
        "college",
    ),
    "pbp": ("pass", "pass_oe", "posteam", "season", "week", "season_type"),
}

# Parse-step renames, exposed so the registry's allowed_fields can carry the
# consumed (post-parse) names alongside the source pins.
VALIDATION_PARSED_RENAMES: dict[str, dict[str, str]] = {
    "pbp": {"posteam": "offense_team"},
}

# Registered temporal scopes (spec D1: weekly/rosters/pbp seasons 2015-2025;
# draft-picks coverage 1980-2025). Enforced fail-closed at the loader.
VALIDATION_SEASON_RANGE = (2015, 2025)
VALIDATION_DRAFT_COVERAGE = (1980, 2025)

# Snapshot-before-parse is MANDATORY (spec D1): when no explicit directory is
# injected (hermetic tests), snapshots land under the governed study root.
# adapter file → adapters → dynasty_genius → src → repo root.
_DEFAULT_SNAPSHOT_ROOT = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "data"
    / "backtest"
    / "qb_validation"
    / "raw"
)


class ValidationIngestError(Exception):
    """Named fail-closed refusal from the validation-study ingestion lane.

    ``reason`` mirrors the study package's failure vocabulary
    (``source_unavailable``, ``manifest_column_missing``, ``snapshot_write_failed``)
    without importing it — the F33 wall runs in one direction only.
    """

    def __init__(self, reason: str, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason}: {detail}" if detail else reason)


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


# --------------------------------------------------------------------------
# QB-1 validation-study ingestion lane (spec v8 D1; role: validation_study).
# --------------------------------------------------------------------------


def _validate_study_seasons(dataset: str, seasons: list[int]) -> list[int]:
    """Refuse season requests outside the registered 2015-2025 scope (spec D1).

    Season keys are exact integers: a non-int request (including a fractional
    float like 2024.9) is refused, never truncated — lossy coercion of an
    external temporal key changes the request silently (round-2 H1).
    """
    if not seasons:
        raise ValidationIngestError(
            "season_out_of_scope", f"{dataset}: empty seasons request"
        )
    low, high = VALIDATION_SEASON_RANGE
    bad: list[Any] = []
    cleaned: list[int] = []
    for season in seasons:
        if (
            isinstance(season, bool)
            or not isinstance(season, int)
            or not (low <= season <= high)
        ):
            bad.append(season)
        else:
            cleaned.append(season)
    if bad:
        raise ValidationIngestError(
            "season_out_of_scope",
            f"{dataset}: {bad!r} not exact integers inside the registered "
            f"{low}-{high} scope",
        )
    return cleaned


def _verify_row_seasons(
    dataset: str, frame: pd.DataFrame, expected_seasons: list[int]
) -> None:
    """Fetched rows must carry exactly the requested seasons (round-2 H1).

    A source returning rows outside the requested scope is corruption, not
    surplus — fail closed, never silently keep or drop.
    """
    values = pd.to_numeric(frame["season"], errors="coerce")
    # Finiteness FIRST: NaN covers unparseable, ±inf would otherwise escape as
    # a raw pandas IntCastingNaNError on astype (round-3 H2).
    if not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValidationIngestError(
            "season_out_of_scope",
            f"{dataset}: unparseable or non-finite season values in fetched rows",
        )
    if (values != values.astype(int)).any():
        raise ValidationIngestError(
            "season_out_of_scope", f"{dataset}: non-integral season values in fetched rows"
        )
    unexpected = sorted(set(values.astype(int)) - set(expected_seasons))
    if unexpected:
        raise ValidationIngestError(
            "season_out_of_scope",
            f"{dataset}: fetched rows carry seasons {unexpected} outside the "
            f"requested {sorted(expected_seasons)}",
        )


def _ingest_validation_dataset(
    dataset: str,
    fetch: Callable[[], Any],
    *,
    snapshot_dir: Path | str | None,
    parse: Callable[[pd.DataFrame], pd.DataFrame] | None = None,
    expected_seasons: list[int] | None = None,
) -> dict[str, Any]:
    """Shared D1 discipline: fetch → raw snapshot → pinned-column check → parse.

    Returns ``{"status": "ok", "frame": <parsed>, "metadata": {...}}`` on
    success; every failure raises :class:`ValidationIngestError` with a named
    reason. The raw snapshot is MANDATORY and written BEFORE any column
    verification or parse, so a failed build stays replayable; when no
    directory is injected it lands under the governed study root
    (``app/data/backtest/qb_validation/raw/``).
    """
    fetched_at = datetime.now(timezone.utc).isoformat()
    try:
        raw = _to_pandas(fetch())
    except ValidationIngestError:
        raise
    except Exception as exc:
        raise ValidationIngestError(
            "source_unavailable", f"{dataset}: fetch failed ({exc}) — fail_closed"
        ) from exc
    if raw.empty:
        raise ValidationIngestError(
            "source_unavailable", f"{dataset}: empty frame — fail_closed, no parsed rows"
        )

    target = Path(snapshot_dir) if snapshot_dir is not None else _DEFAULT_SNAPSHOT_ROOT
    try:
        target.mkdir(parents=True, exist_ok=True)
        stamp = fetched_at.replace(":", "").replace("+", "Z")
        path = target / f"{dataset}-{stamp}.parquet"
        raw.to_parquet(path)
        snapshot_path = str(path)
    except Exception as exc:
        raise ValidationIngestError("snapshot_write_failed", f"{dataset}: {exc}") from exc

    pinned = VALIDATION_DATASET_COLUMNS[dataset]
    absent = [column for column in pinned if column not in raw.columns]
    if absent:
        raise ValidationIngestError(
            "manifest_column_missing", f"{dataset}: {', '.join(absent)}"
        )
    if expected_seasons is not None:
        _verify_row_seasons(dataset, raw, expected_seasons)

    parsed = parse(raw) if parse is not None else raw
    return {
        "status": "ok",
        "frame": parsed,
        "metadata": {
            "dataset": dataset,
            "source": "nflreadpy_qb_validation",
            "source_timestamp": fetched_at,
            "parser_version": VALIDATION_PARSER_VERSION,
            "rows": int(len(parsed)),
            "rows_dropped_at_parse": int(len(raw) - len(parsed)),
            "pinned_columns_verified": list(pinned),
            "raw_snapshot_path": snapshot_path,
            "completeness": "ok",
        },
    }


def _filter_regular_season(dataset: str) -> Callable[[pd.DataFrame], pd.DataFrame]:
    """REG-only parse filter (spec D1.1/D1.6); the raw snapshot keeps all rows."""

    def _parse(frame: pd.DataFrame) -> pd.DataFrame:
        kept = frame[frame["season_type"] == "REG"].copy()
        if kept.empty:
            raise ValidationIngestError(
                "source_unavailable",
                f"{dataset}: zero regular-season rows after the REG filter",
            )
        return kept

    return _parse


def load_validation_weekly_stats(
    seasons: list[int],
    *,
    loader: Callable[[], Any] | None = None,
    snapshot_dir: Path | str | None = None,
) -> dict[str, Any]:
    """D1.1 — weekly regular-season player stats, ALL-POSITION by law.

    Team aggregates are computed from this full frame BEFORE any QB filter;
    the QB filter applies only at matrix build.
    """

    scoped = _validate_study_seasons("weekly", list(seasons))

    def _fetch() -> Any:
        if loader is not None:
            return loader()
        import nflreadpy as nfl

        return nfl.load_player_stats(scoped, summary_level="week")

    return _ingest_validation_dataset(
        "weekly",
        _fetch,
        snapshot_dir=snapshot_dir,
        parse=_filter_regular_season("weekly"),
        expected_seasons=scoped,
    )


def load_validation_players(
    *,
    loader: Callable[[], Any] | None = None,
    snapshot_dir: Path | str | None = None,
) -> dict[str, Any]:
    """D1.2 — player identity attributes (birth date → age_at_season_start).

    Draft fields here are cross-check only, never the draft-capital source.
    """

    def _fetch() -> Any:
        if loader is not None:
            return loader()
        import nflreadpy as nfl

        return nfl.load_players()

    return _ingest_validation_dataset("players", _fetch, snapshot_dir=snapshot_dir)


def load_validation_rosters(
    seasons: list[int],
    *,
    loader: Callable[[], Any] | None = None,
    snapshot_dir: Path | str | None = None,
) -> dict[str, Any]:
    """D1.3 — season roster presence (any REG row, any status; pinned inclusive)."""

    scoped = _validate_study_seasons("rosters", list(seasons))

    def _fetch() -> Any:
        if loader is not None:
            return loader()
        import nflreadpy as nfl

        return nfl.load_rosters(scoped)

    return _ingest_validation_dataset(
        "rosters", _fetch, snapshot_dir=snapshot_dir, expected_seasons=scoped
    )


def load_validation_ff_playerids(
    *,
    loader: Callable[[], Any] | None = None,
    snapshot_dir: Path | str | None = None,
) -> dict[str, Any]:
    """D1.4 — the nflverse gsis↔sleeper crosswalk (static-join input, no PIT claim)."""

    def _fetch() -> Any:
        if loader is not None:
            return loader()
        import nflreadpy as nfl

        return nfl.load_ff_playerids()

    return _ingest_validation_dataset("ff_playerids", _fetch, snapshot_dir=snapshot_dir)


def load_validation_draft_picks(
    *,
    loader: Callable[[], Any] | None = None,
    snapshot_dir: Path | str | None = None,
) -> dict[str, Any]:
    """D1.5 — the authoritative drafted list / draft-capital source (1980–2025)."""

    def _fetch() -> Any:
        if loader is not None:
            return loader()
        import nflreadpy as nfl

        return nfl.load_draft_picks()

    def _coverage_filter(frame: pd.DataFrame) -> pd.DataFrame:
        low, high = VALIDATION_DRAFT_COVERAGE
        seasons_numeric = pd.to_numeric(frame["season"], errors="coerce")
        # Corrupt temporal keys fail closed; only valid integers may be
        # range-dropped (round-2 H1; round-3 H2: finiteness before astype —
        # NaN covers unparseable, ±inf would raise raw IntCastingNaNError).
        if not np.isfinite(seasons_numeric.to_numpy(dtype=float)).all():
            raise ValidationIngestError(
                "season_out_of_scope",
                "draft_picks: unparseable or non-finite season values",
            )
        if (seasons_numeric != seasons_numeric.astype(int)).any():
            raise ValidationIngestError(
                "season_out_of_scope", "draft_picks: non-integral season values"
            )
        kept = frame[(seasons_numeric >= low) & (seasons_numeric <= high)].copy()
        if kept.empty:
            raise ValidationIngestError(
                "source_unavailable",
                f"draft_picks: zero rows inside the pinned {low}-{high} coverage",
            )
        return kept

    return _ingest_validation_dataset(
        "draft_picks", _fetch, snapshot_dir=snapshot_dir, parse=_coverage_filter
    )


def load_validation_pbp(
    seasons: list[int],
    *,
    loader: Callable[[], Any] | None = None,
    snapshot_dir: Path | str | None = None,
) -> dict[str, Any]:
    """D1.6 — play-by-play for team_proe; ``posteam`` renamed ``offense_team`` at parse.

    The context lane's ``load_pbp`` path above is untouched; the study path
    snapshots separately under the validation_study role.
    """

    scoped = _validate_study_seasons("pbp", list(seasons))

    def _fetch() -> Any:
        if loader is not None:
            return loader()
        import nflreadpy as nfl

        return nfl.load_pbp(scoped)

    reg_filter = _filter_regular_season("pbp")

    def _parse(frame: pd.DataFrame) -> pd.DataFrame:
        return reg_filter(frame).rename(columns=VALIDATION_PARSED_RENAMES["pbp"])

    return _ingest_validation_dataset(
        "pbp", _fetch, snapshot_dir=snapshot_dir, parse=_parse, expected_seasons=scoped
    )
