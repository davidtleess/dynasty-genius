"""RED — realized-outcome scorer production wiring and honest health semantics.

Authority
---------
Framing v3 (SHA ``71019940…``) plus the v4 scope/status correction (SHA
``77e92aed…``). Codex owns RED; Claude owns GREEN. This file deliberately tests only the
production wiring contract. The pure scorer's status-sensitive floor branch lives in
``tests/unit/test_realized_outcome_scorer.py``.

Falsification matrix (before GREEN)
-----------------------------------
nominal/boundary: declared loader + nonfinal day 14/15 + settlement week 33/34;
missing/empty: empty identity and zero observed grades; null/wrong-type/non-finite:
utilization and snap share; malformed: declaration, utilization JSON, gameday; duplicate/
conflict: JSON keys, crosswalk mappings, snap rows; cross-component: loader envelope through
bridge/outcomes/scorecard/marker; numeric: snap-share [0,1]; override: scheduled and explicit
targets share the nonfinal-overdue law. Synthetic live-provider calls, partial-coverage bands,
real finality-provider selection, scheduler installation, and ff_opportunity consumption are
explicitly out of scope.
"""

from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


def _cli():
    return importlib.import_module("scripts.run_realized_outcome_scoring")


def _write_declaration(path: Path, *, capture_date: str = "2026-08-05") -> None:
    path.write_text(
        json.dumps(
            {
                "seasons": {
                    "2026": {
                        "frozen_capture_date": capture_date,
                        "source": "model_pvo",
                        "declared_by": "David",
                        "declared_at": "2026-08-13T23:59:00-04:00",
                    }
                }
            }
        ),
        encoding="utf-8",
    )


def _create_capture_db(path: Path, rows: list[dict[str, Any]]) -> None:
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE model_forward_prediction_snapshot (
                capture_date TEXT,
                source TEXT,
                semantic_output_hash TEXT,
                provenance_hash TEXT,
                player_key TEXT,
                projection_2y REAL,
                utilization TEXT,
                prediction_ppg_status TEXT,
                util_snapshot_status TEXT,
                schema_version INTEGER,
                source_hash TEXT,
                PRIMARY KEY (
                    capture_date, source, semantic_output_hash, provenance_hash, player_key
                )
            );
            CREATE TABLE model_forward_capture_joinable (
                capture_date TEXT,
                source TEXT,
                semantic_output_hash TEXT,
                provenance_hash TEXT,
                player_key TEXT,
                sleeper_id TEXT,
                dg_player_id TEXT,
                position TEXT,
                engine_path TEXT,
                PRIMARY KEY (
                    capture_date, source, semantic_output_hash, provenance_hash, player_key
                )
            );
            """
        )
        for index, supplied in enumerate(rows, start=1):
            row = {
                "capture_date": "2026-08-05",
                "source": "model_pvo",
                "semantic_output_hash": f"semantic-{index}",
                "provenance_hash": f"provenance-{index}",
                "player_key": f"player-{index}",
                "projection_2y": 10.0 + index,
                "utilization": json.dumps(
                    {
                        "snap_share": {"value": 0.5, "role": "model_input"},
                        "weighted_opportunity": {
                            "value": 0.3,
                            "role": "model_input",
                        },
                    }
                ),
                "prediction_ppg_status": "captured",
                "util_snapshot_status": "complete",
                "schema_version": 1,
                "source_hash": f"source-{index}",
                "sleeper_id": f"sid-{index}",
                "dg_player_id": f"dg-{index}",
                "position": "WR",
                "engine_path": "ENGINE_B",
                "joinable": True,
            }
            row.update(supplied)
            conn.execute(
                """
                INSERT INTO model_forward_prediction_snapshot VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    row["capture_date"],
                    row["source"],
                    row["semantic_output_hash"],
                    row["provenance_hash"],
                    row["player_key"],
                    row["projection_2y"],
                    row["utilization"],
                    row["prediction_ppg_status"],
                    row["util_snapshot_status"],
                    row["schema_version"],
                    row["source_hash"],
                ],
            )
            if row["joinable"]:
                conn.execute(
                    """
                    INSERT INTO model_forward_capture_joinable VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        row["capture_date"],
                        row["source"],
                        row["semantic_output_hash"],
                        row["provenance_hash"],
                        row["player_key"],
                        row["sleeper_id"],
                        row["dg_player_id"],
                        row["position"],
                        row["engine_path"],
                    ],
                )


def _configure_capture(monkeypatch, tmp_path: Path, rows: list[dict[str, Any]]):
    cli = _cli()
    declaration = tmp_path / "frozen.json"
    capture_db = tmp_path / "capture.db"
    _write_declaration(declaration)
    _create_capture_db(capture_db, rows)
    monkeypatch.setattr(cli, "FROZEN_PREDICTION_DECLARATION", declaration)
    monkeypatch.setattr(cli, "PREDICTION_CAPTURE_DB", capture_db)
    return cli, declaration, capture_db


def _prediction(index: int) -> dict[str, Any]:
    return {
        "capture_date": "2026-08-05",
        "sleeper_id": f"sid-{index}",
        "dg_player_id": f"dg-{index}",
        "player_key": f"player-{index}",
        "position": "WR",
        "projection_2y": 10.0 + index,
        "utilization": {
            "snap_share": {"value": 0.5, "role": "model_input"},
            "weighted_opportunity": {"value": 0.3, "role": "model_input"},
        },
    }


def _prediction_envelope(rows: list[dict[str, Any]], *, declared_count: int | None = None):
    declared = len(rows) if declared_count is None else declared_count
    return {
        "rows": rows,
        "coverage": {
            "declared_capture_date": "2026-08-05",
            "declared_count": declared,
            "eligible_count": len(rows),
            "prediction_status_counts": {"captured": len(rows)},
            "prediction_excluded_counts": {
                "capture_incomplete": max(0, declared - len(rows))
            },
        },
    }


def _identity_snapshots(count: int) -> list[dict[str, Any]]:
    return [
        {
            "timestamp": "2026-05-16T03:28:22Z",
            "source_sha256": "fixture-sha",
            "mapping_version": "ff_playerids_20260516",
            "mappings": {
                f"dg-{index}": {
                    "sleeper_id": f"sid-{index}",
                    "gsis_id": f"00-{index:04d}",
                    "pfr_id": f"Pfr{index:04d}",
                }
                for index in range(1, count + 1)
            },
        }
    ]


def _schedule(*, status: str = "final", gameday: str = "2026-09-10") -> dict[str, Any]:
    return {
        "season": 2026,
        "week": 1,
        "expected_game_count": 1,
        "games": [
            {
                "season": 2026,
                "week": 1,
                "game_id": "g1",
                "status": status,
                "gameday": gameday,
            }
        ],
    }


def _stat(index: int) -> dict[str, Any]:
    return {
        "player_id": f"00-{index:04d}",
        "season": 2026,
        "week": 1,
        "fantasy_points_ppr": 11.0 + index,
        "player_status": "active",
        "game_played": True,
    }


def test_prediction_loader_returns_dynamic_declared_coverage_parsed_util_and_provenance(
    monkeypatch,
    tmp_path,
) -> None:
    cli, _declaration, _capture_db = _configure_capture(
        monkeypatch,
        tmp_path,
        [
            {},
            {
                "prediction_ppg_status": "capture_incomplete",
                "util_snapshot_status": "missing_feature_row",
                "projection_2y": None,
                "engine_path": "ENGINE_A",
            },
            {"joinable": False},  # whole-snapshot noise is not the grading denominator
        ],
    )

    loaded = cli._default_prediction_loader(2026, 1)

    assert loaded["coverage"] == {
        "declared_capture_date": "2026-08-05",
        "declared_count": 2,
        "eligible_count": 1,
        "prediction_status_counts": {"capture_incomplete": 1, "captured": 1},
        "prediction_excluded_counts": {"capture_incomplete": 1},
    }
    assert len(loaded["rows"]) == 1
    row = loaded["rows"][0]
    assert row["dg_player_id"] == "dg-1"
    assert row["player_key"] == "player-1"
    assert row["source"] == "model_pvo"
    assert row["semantic_output_hash"] == "semantic-1"
    assert row["provenance_hash"] == "provenance-1"
    assert row["utilization"]["snap_share"] == {
        "value": 0.5,
        "role": "model_input",
    }
    assert row["source_hash"] == "source-1"
    assert row["schema_version"] == 1


@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        ("[]", "declaration_root_not_object"),
        ('{"seasons": []}', "declaration_seasons_not_object"),
        ('{"seasons": {"2026": []}}', "declaration_entry_not_object"),
        (
            json.dumps(
                {
                    "seasons": {
                        "2026": {
                            "frozen_capture_date": "08/05/2026",
                            "source": "model_pvo",
                            "declared_by": "David",
                            "declared_at": "2026-08-13T23:59:00-04:00",
                        }
                    }
                }
            ),
            "frozen_capture_date_invalid",
        ),
        (
            json.dumps(
                {
                    "seasons": {
                        "2026": {
                            "frozen_capture_date": "2026-08-05",
                            "source": "model_pvo",
                            "declared_by": "David",
                            "declared_at": "yesterday",
                        }
                    }
                }
            ),
            "declared_at_invalid",
        ),
        (
            '{"seasons":{"2026":{"frozen_capture_date":"2026-08-05",'
            '"source":"model_pvo","source":"other","declared_by":"David",'
            '"declared_at":"2026-08-13T23:59:00-04:00"}}}',
            "declaration_duplicate_json_key",
        ),
    ],
)
def test_declaration_shapes_types_formats_and_duplicate_keys_fail_named(
    monkeypatch,
    tmp_path,
    raw,
    reason,
) -> None:
    cli = _cli()
    path = tmp_path / "frozen.json"
    path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(cli, "FROZEN_PREDICTION_DECLARATION", path)

    with pytest.raises(Exception, match=reason):
        cli._load_frozen_declaration(2026)


@pytest.mark.parametrize(
    ("utilization", "reason"),
    [
        ("{broken", "utilization_invalid_json"),
        (json.dumps([]), "utilization_not_object"),
        (
            json.dumps({"snap_share": {"value": True, "role": "model_input"}}),
            "utilization_value_invalid",
        ),
        (
            json.dumps({"snap_share": {"value": 0.5, "role": "verdict"}}),
            "utilization_role_invalid",
        ),
    ],
)
def test_prediction_utilization_malformed_or_wrong_type_fails_named(
    monkeypatch,
    tmp_path,
    utilization,
    reason,
) -> None:
    cli, _declaration, _capture_db = _configure_capture(
        monkeypatch,
        tmp_path,
        [{"utilization": utilization}],
    )

    with pytest.raises(Exception, match=reason):
        cli._default_prediction_loader(2026, 1)


class _CrosswalkIndex(dict):
    duplicate_count: int = 0


def test_identity_loader_reuses_canonical_crosswalk_and_preserves_frozen_dg_id(
    monkeypatch,
    tmp_path,
) -> None:
    cli, _declaration, _capture_db = _configure_capture(monkeypatch, tmp_path, [{}])
    crosswalk = tmp_path / "ff_playerids_20260516.json"
    crosswalk.write_text(
        json.dumps(
            {
                "metadata": {
                    "source": "nflreadpy.load_ff_playerids",
                    "pull_timestamp": "2026-05-16T03:28:22Z",
                },
                "entries": [],
            }
        ),
        encoding="utf-8",
    )
    by_gsis = _CrosswalkIndex(
        {
            "00-0001": {
                "gsis_id": "00-0001",
                "sleeper_id": "sid-1",
                "pfr_id": "Pfr0001",
            }
        }
    )
    by_sleeper = _CrosswalkIndex({"sid-1": by_gsis["00-0001"]})
    by_gsis.duplicate_count = by_sleeper.duplicate_count = 1
    calls: list[Path] = []

    def canonical_loader(path):
        calls.append(Path(path))
        return by_gsis, by_sleeper

    monkeypatch.setattr(cli, "FF_PLAYERIDS_PATH", crosswalk, raising=False)
    monkeypatch.setattr(cli, "_load_ff_playerids", canonical_loader, raising=False)

    snapshots = cli._default_identity_snapshot_loader(2026, 1)

    assert calls == [crosswalk]
    assert len(snapshots) == 1
    snapshot = snapshots[0]
    assert snapshot["timestamp"] == "2026-05-16T03:28:22Z"
    assert snapshot["source_sha256"] == hashlib.sha256(crosswalk.read_bytes()).hexdigest()
    assert snapshot["mapping_version"] == "ff_playerids_20260516"
    assert snapshot["duplicate_count"] == 1
    assert snapshot["mappings"] == {
        "dg-1": {
            "sleeper_id": "sid-1",
            "gsis_id": "00-0001",
            "pfr_id": "Pfr0001",
        }
    }


@pytest.mark.parametrize("failure", ["empty", "conflict"])
def test_identity_loader_empty_or_conflicting_crosswalk_fails_named(
    monkeypatch,
    tmp_path,
    failure,
) -> None:
    cli, _declaration, _capture_db = _configure_capture(monkeypatch, tmp_path, [{}])
    crosswalk = tmp_path / "ff_playerids_20260516.json"
    crosswalk.write_text(
        json.dumps(
            {
                "metadata": {"pull_timestamp": "2026-05-16T03:28:22Z"},
                "entries": [],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "FF_PLAYERIDS_PATH", crosswalk, raising=False)
    if failure == "empty":
        monkeypatch.setattr(
            cli,
            "_load_ff_playerids",
            lambda _path: (_CrosswalkIndex(), _CrosswalkIndex()),
            raising=False,
        )
        reason = "identity_crosswalk_empty"
    else:
        def raise_conflict(_path):
            raise ValueError("ff_playerids_conflicting_sleeper_mapping")

        monkeypatch.setattr(cli, "_load_ff_playerids", raise_conflict, raising=False)
        reason = "ff_playerids_conflicting_sleeper_mapping"

    with pytest.raises(Exception, match=reason):
        cli._default_identity_snapshot_loader(2026, 1)


def _create_snap_db(path: Path, rows: list[tuple[str, str]]) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE player_snap_count (
                season TEXT, week TEXT, pfr_player_id TEXT, offense_pct TEXT
            )
            """
        )
        conn.executemany(
            "INSERT INTO player_snap_count VALUES ('2026', '1', ?, ?)", rows
        )


def test_util_loader_maps_pfr_to_gsis_and_emits_snap_share_only(
    monkeypatch,
    tmp_path,
) -> None:
    cli = _cli()
    db = tmp_path / "usage.db"
    _create_snap_db(db, [("Pfr0001", "0.75"), ("Unknown00", "0.25")])
    by_gsis = _CrosswalkIndex(
        {
            "00-0001": {
                "gsis_id": "00-0001",
                "sleeper_id": "sid-1",
                "pfr_id": "Pfr0001",
            }
        }
    )
    monkeypatch.setattr(cli, "NFLVERSE_USAGE_DB", db, raising=False)
    monkeypatch.setattr(
        cli,
        "_load_ff_playerids",
        lambda _path: (by_gsis, _CrosswalkIndex()),
        raising=False,
    )
    monkeypatch.setattr(cli, "FF_PLAYERIDS_PATH", tmp_path / "ff.json", raising=False)

    rows = cli._default_util_loader(2026, 1)

    assert rows == [
        {
            "player_id": "00-0001",
            "season": 2026,
            "week": 1,
            "snap_share_realized": 0.75,
        }
    ]
    assert "route_participation_realized" not in rows[0]
    assert "target_share_nfl_realized" not in rows[0]
    assert "weighted_opportunity" not in rows[0]


@pytest.mark.parametrize(
    ("rows", "reason"),
    [
        ([("Pfr0001", "nan")], "snap_share_invalid"),
        ([("Pfr0001", "1.1")], "snap_share_out_of_range"),
        (
            [("Pfr0001", "0.5"), ("Pfr0001", "0.6")],
            "snap_share_duplicate",
        ),
    ],
)
def test_util_loader_invalid_numeric_or_duplicate_rows_fail_named(
    monkeypatch,
    tmp_path,
    rows,
    reason,
) -> None:
    cli = _cli()
    db = tmp_path / "usage.db"
    _create_snap_db(db, rows)
    by_gsis = _CrosswalkIndex(
        {"00-0001": {"gsis_id": "00-0001", "pfr_id": "Pfr0001"}}
    )
    monkeypatch.setattr(cli, "NFLVERSE_USAGE_DB", db, raising=False)
    monkeypatch.setattr(
        cli,
        "_load_ff_playerids",
        lambda _path: (by_gsis, _CrosswalkIndex()),
        raising=False,
    )
    monkeypatch.setattr(cli, "FF_PLAYERIDS_PATH", tmp_path / "ff.json", raising=False)

    with pytest.raises(Exception, match=reason):
        cli._default_util_loader(2026, 1)


def test_outcome_builder_seeds_stat_absent_frozen_player_with_explicit_unavailable_week(
    tmp_path,
) -> None:
    cli = _cli()

    outcomes = cli._build_outcomes(
        2026,
        1,
        schedule_loader=lambda *_args: _schedule(),
        stat_loader=lambda *_args: [],
        util_loader=lambda *_args: [],
        frozen_players=[{"gsis_id": "00-0001"}],
    )

    entry = outcomes["players"]["00-0001"]
    assert entry["outcome"]["games_played"] == 0
    assert entry["outcome"]["ppg_to_date"] is None
    assert entry["outcome"]["player_status"] == "status_unverified"
    assert entry["weekly_util"] == [
        {
            "season": 2026,
            "week": 1,
            "snap_share_realized": {"value": None, "status": "unavailable"},
            "route_participation_realized": {
                "value": None,
                "status": "unavailable",
            },
            "target_share_nfl_realized": {
                "value": None,
                "status": "unavailable",
            },
        }
    ]


@pytest.mark.parametrize("scheduled_path", [False, True])
@pytest.mark.parametrize(
    ("age_days", "status", "reason"),
    [
        (14, "noop", "week_not_finalized"),
        (15, "failed", "week_nonfinal_overdue"),
    ],
)
def test_nonfinal_age_boundary_applies_to_explicit_and_scheduled_paths(
    tmp_path,
    scheduled_path,
    age_days,
    status,
    reason,
) -> None:
    cli = _cli()
    gameday = "2026-09-10"
    now = datetime(2026, 9, 10 + age_days, 12, tzinfo=timezone.utc)
    marker = tmp_path / "marker.json"

    result = cli.run_scoring(
        season=2026,
        week=1,
        report_path=tmp_path / "scorecard.json",
        marker_path=marker,
        enforce_target_freshness=scheduled_path,
        now_fn=lambda: now,
        schedule_loader=lambda *_args: _schedule(status="scheduled", gameday=gameday),
        stat_loader=lambda *_args: pytest.fail("nonfinal path must not load stats"),
        util_loader=lambda *_args: pytest.fail("nonfinal path must not load util"),
        prediction_loader=lambda *_args: _prediction_envelope([_prediction(1)]),
        identity_snapshot_loader=lambda *_args: pytest.fail(
            "nonfinal path must not load identity"
        ),
    )

    assert result["status"] == status
    assert result[f"{'noop' if status == 'noop' else 'failure'}_reason"] == reason
    assert result["week_status"] == "not_finalized"
    if status == "failed":
        assert result["gameday"] == gameday
    marker_body = json.loads(marker.read_text())
    assert marker_body["status"] == status
    assert marker_body[f"{'noop' if status == 'noop' else 'failure'}_reason"] == reason


@pytest.mark.parametrize(
    "games",
    [
        [{"season": 2026, "week": 1, "status": "scheduled", "gameday": "bad"}],
        [
            {
                "season": 2026,
                "week": 1,
                "status": "scheduled",
                "gameday": "2026-09-10",
            },
            {"season": 2026, "week": 1, "status": "scheduled", "gameday": None},
        ],
    ],
)
def test_nonfinal_missing_or_mixed_malformed_gamedays_fail_loud(tmp_path, games) -> None:
    cli = _cli()
    result = cli.run_scoring(
        season=2026,
        week=1,
        report_path=tmp_path / "scorecard.json",
        now_fn=lambda: datetime(2026, 10, 1, tzinfo=timezone.utc),
        schedule_loader=lambda *_args: {
            "season": 2026,
            "week": 1,
            "expected_game_count": len(games),
            "games": games,
        },
        stat_loader=lambda *_args: [],
        util_loader=lambda *_args: [],
        prediction_loader=lambda *_args: _prediction_envelope([_prediction(1)]),
        identity_snapshot_loader=lambda *_args: [],
    )

    assert result["status"] == "failed"
    assert result["failure_reason"] == "nonfinal_age_indeterminate"
    assert result["week_status"] == "not_finalized"


def test_score_derived_default_schedule_never_certifies_finality(monkeypatch) -> None:
    cli = _cli()
    pd = pytest.importorskip("pandas")
    frame = pd.DataFrame(
        [
            {
                "season": 2026,
                "week": 1,
                "game_id": "g1",
                "home_score": 24,
                "away_score": 17,
                "gameday": "2026-09-10",
            }
        ]
    )
    monkeypatch.setitem(
        sys.modules,
        "nflreadpy",
        SimpleNamespace(load_schedules=lambda _seasons: SimpleNamespace(to_pandas=lambda: frame)),
    )

    schedule = cli._default_schedule_loader(2026, 1)

    assert schedule["games"][0]["status"] == "result_observed_unverified"
    assert cli.week_status(2026, 1, schedule=schedule) == "not_finalized"


def test_zero_graded_fails_and_catastrophic_partial_only_discloses_counts(tmp_path) -> None:
    cli = _cli()
    rows = [_prediction(1), _prediction(2)]
    envelope = _prediction_envelope(rows, declared_count=3)

    zero_marker = tmp_path / "zero-marker.json"
    zero = cli.run_scoring(
        season=2026,
        week=1,
        report_path=tmp_path / "zero-scorecard.json",
        marker_path=zero_marker,
        schedule_loader=lambda *_args: _schedule(),
        stat_loader=lambda *_args: [],
        util_loader=lambda *_args: [],
        prediction_loader=lambda *_args: envelope,
        identity_snapshot_loader=lambda *_args: _identity_snapshots(2),
    )
    assert zero["status"] == "failed"
    assert zero["failure_reason"] == "zero_graded_predictions"
    assert zero["coverage"] == {
        "declared_count": 3,
        "eligible_count": 2,
        "resolved_count": 2,
        "outcome_present_count": 2,
        "graded_count": 0,
        "rank_eligible_count": 0,
        "prediction_excluded_counts": {"capture_incomplete": 1},
        "identity_excluded_counts": {},
    }
    assert not (tmp_path / "zero-scorecard.json").exists()
    assert json.loads(zero_marker.read_text())["coverage"] == zero["coverage"]

    partial_marker = tmp_path / "partial-marker.json"
    partial_report = tmp_path / "partial-scorecard.json"
    partial = cli.run_scoring(
        season=2026,
        week=1,
        report_path=partial_report,
        marker_path=partial_marker,
        schedule_loader=lambda *_args: _schedule(),
        stat_loader=lambda *_args: [_stat(1)],
        util_loader=lambda *_args: [],
        prediction_loader=lambda *_args: envelope,
        identity_snapshot_loader=lambda *_args: _identity_snapshots(2),
    )
    assert partial["status"] == "ok"
    assert partial["coverage"]["graded_count"] == 1
    assert partial["coverage"]["eligible_count"] == 2
    assert "coverage_status" not in partial["coverage"]  # no invented partial bands
    assert json.loads(partial_report.read_text())["coverage"] == partial["coverage"]
    assert json.loads(partial_marker.read_text())["coverage"] == partial["coverage"]


def test_source_database_loaders_are_pinned_to_sqlite_read_only_mode() -> None:
    cli = _cli()
    for loader in (
        cli._default_prediction_loader,
        cli._default_identity_snapshot_loader,
        cli._default_util_loader,
    ):
        source = inspect.getsource(loader)
        assert "mode=ro" in source, f"{loader.__name__} is not pinned read-only"
        assert "uri=True" in source, f"{loader.__name__} does not enable SQLite URI mode"


def test_ff_opportunity_symbol_stays_out_of_the_scorer_wiring() -> None:
    text = Path("scripts/run_realized_outcome_scoring.py").read_text(encoding="utf-8")
    assert "ff_opportunity" not in text
