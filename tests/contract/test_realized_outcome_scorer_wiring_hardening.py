"""Green-review round-1 hardening contracts (G1–G4) — Claude-authored, offered to the RED
owner (Codex) for adoption into the pinned contract set at round 2.

Covers the three BLOCKERs + timestamp WARN from
``realized_outcome_scorer_green_review_codex_v1.md`` (``d2861125…``): the external schedule
shape boundary must fail CLOSED with a terminal marker; an ambiguous PFR identity must never
be assigned; prediction-time utilization rejects non-finite and out-of-range numerics; a
declaration timestamp is a timestamp, not a date.
"""

from __future__ import annotations

import importlib
import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest


def _cli():
    return importlib.import_module("scripts.run_realized_outcome_scoring")


def _prediction(index: int) -> dict[str, Any]:
    return {
        "capture_date": "2026-08-05",
        "sleeper_id": f"sid-{index}",
        "position": "WR",
        "projection_2y": 10.0 + index,
    }


# ── G1: malformed returned schedule shapes fail closed with a terminal marker ──


@pytest.mark.parametrize(
    "schedule",
    [
        [],  # non-dict root
        {"season": 2026, "week": 1, "expected_game_count": 1, "games": "bad"},
        {"season": 2026, "week": 1, "expected_game_count": 1, "games": [None]},
        # R2-B1: a MISSING or null `games` is provider breakage, not an empty off-season —
        # smoothing either to [] would report healthy while the source is malformed.
        {"season": 2026, "week": 1, "expected_game_count": 1},
        {"season": 2026, "week": 1, "expected_game_count": 1, "games": None},
        # R3-B1: an empty WRONG-TYPE collection keeps the list guard mutation-sensitive —
        # a mutant deleting the isinstance(list) check would accept a tuple silently.
        {"season": 2026, "week": 1, "expected_game_count": 1, "games": ()},
    ],
)
def test_malformed_schedule_shape_fails_named_and_writes_terminal_marker(
    tmp_path, schedule
) -> None:
    cli = _cli()
    marker = tmp_path / "marker.json"
    result = cli.run_scoring(
        season=2026,
        week=1,
        report_path=tmp_path / "scorecard.json",
        marker_path=marker,
        schedule_loader=lambda *_args: schedule,
        stat_loader=lambda *_args: pytest.fail("malformed schedule must not load stats"),
        util_loader=lambda *_args: pytest.fail("malformed schedule must not load util"),
        prediction_loader=lambda *_args: [_prediction(1)],
        identity_snapshot_loader=lambda *_args: pytest.fail(
            "malformed schedule must not load identity"
        ),
    )
    assert result["status"] == "failed"
    assert result["failure_reason"] == "schedule_shape_invalid"
    marker_body = json.loads(marker.read_text())
    assert marker_body["status"] == "failed"
    assert marker_body["failure_reason"] == "schedule_shape_invalid"
    assert not (tmp_path / "scorecard.json").exists()


# ── R2-B2: malformed prediction envelopes fail closed with a terminal marker ──


def _valid_schedule() -> dict[str, Any]:
    return {
        "season": 2026,
        "week": 1,
        "expected_game_count": 1,
        "games": [
            {
                "season": 2026,
                "week": 1,
                "game_id": "g1",
                "status": "final",
                "gameday": "2026-09-10",
            }
        ],
    }


@pytest.mark.parametrize(
    "loaded",
    [
        {"coverage": {}},  # rows key missing
        {"rows": None, "coverage": {}},  # rows null
        {"rows": "abc", "coverage": {}},  # rows wrong type
        {"rows": [1], "coverage": {}},  # non-dict row
        {"rows": [{"sleeper_id": "sid-1"}], "coverage": "bad"},  # coverage wrong type
        None,  # loader returned nothing at all
        # R3-B1: empty wrong-type rows collection — keeps the rows list guard
        # mutation-sensitive (a tuple-accepting mutant passes every other row here).
        {"rows": (), "coverage": {}},
    ],
)
def test_malformed_prediction_envelope_fails_named_and_writes_terminal_marker(
    tmp_path, loaded
) -> None:
    cli = _cli()
    marker = tmp_path / "marker.json"
    result = cli.run_scoring(
        season=2026,
        week=1,
        report_path=tmp_path / "scorecard.json",
        marker_path=marker,
        schedule_loader=lambda *_args: pytest.fail(
            "malformed envelope must not load schedule"
        ),
        stat_loader=lambda *_args: pytest.fail("malformed envelope must not load stats"),
        util_loader=lambda *_args: pytest.fail("malformed envelope must not load util"),
        prediction_loader=lambda *_args: loaded,
        identity_snapshot_loader=lambda *_args: pytest.fail(
            "malformed envelope must not load identity"
        ),
    )
    assert result["status"] == "failed"
    assert result["failure_reason"] == "prediction_envelope_invalid"
    marker_body = json.loads(marker.read_text())
    assert marker_body["status"] == "failed"
    assert marker_body["failure_reason"] == "prediction_envelope_invalid"
    assert not (tmp_path / "scorecard.json").exists()


def test_valid_empty_mapping_envelope_noops_as_no_predictions(tmp_path) -> None:
    # R3-B1 positive control: a WELL-FORMED envelope with zero rows is the honest
    # "nothing to grade" state, not a malformed envelope.
    cli = _cli()
    result = cli.run_scoring(
        season=2026,
        week=1,
        report_path=tmp_path / "scorecard.json",
        marker_path=tmp_path / "marker.json",
        schedule_loader=lambda *_args: _valid_schedule(),
        stat_loader=lambda *_args: [],
        util_loader=lambda *_args: [],
        prediction_loader=lambda *_args: {"rows": [], "coverage": {}},
        identity_snapshot_loader=lambda *_args: [],
    )
    assert result["status"] == "noop"
    assert result["noop_reason"] == "no_predictions_for_target"


def test_legacy_bare_empty_list_still_noops_as_no_predictions(tmp_path) -> None:
    cli = _cli()
    marker = tmp_path / "marker.json"
    result = cli.run_scoring(
        season=2026,
        week=1,
        report_path=tmp_path / "scorecard.json",
        marker_path=marker,
        schedule_loader=lambda *_args: _valid_schedule(),
        stat_loader=lambda *_args: [],
        util_loader=lambda *_args: [],
        prediction_loader=lambda *_args: [],
        identity_snapshot_loader=lambda *_args: [],
    )
    assert result["status"] == "noop"
    assert result["noop_reason"] == "no_predictions_for_target"


# ── G2: an ambiguous PFR id is never assigned; unambiguous rows still attribute ──


def test_ambiguous_pfr_id_is_never_assigned_and_unambiguous_rows_still_attribute(
    monkeypatch, tmp_path
) -> None:
    cli = _cli()
    db = tmp_path / "usage.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE player_snap_count ("
            "season TEXT, week TEXT, pfr_player_id TEXT, offense_pct TEXT)"
        )
        conn.executemany(
            "INSERT INTO player_snap_count VALUES ('2026', '1', ?, ?)",
            [("CartKy01", "0.75"), ("SafePf01", "0.50")],
        )
    by_gsis = {
        # Two distinct GSIS identities claim the same PFR id — the real pinned
        # crosswalk carries exactly this class (CartKy01 / HarrAl00 / MillSt00).
        "00-0032430": {"gsis_id": "00-0032430", "pfr_id": "CartKy01"},
        "00-0032606": {"gsis_id": "00-0032606", "pfr_id": "CartKy01"},
        "00-0009999": {"gsis_id": "00-0009999", "pfr_id": "SafePf01"},
    }
    monkeypatch.setattr(cli, "NFLVERSE_USAGE_DB", db, raising=False)
    monkeypatch.setattr(
        cli, "_load_ff_playerids", lambda _path: (by_gsis, {}), raising=False
    )
    monkeypatch.setattr(cli, "FF_PLAYERIDS_PATH", tmp_path / "ff.json", raising=False)

    rows = cli._default_util_loader(2026, 1)

    assert rows == [
        {
            "player_id": "00-0009999",
            "season": 2026,
            "week": 1,
            "snap_share_realized": 0.5,
        }
    ]
    attributed = {row["player_id"] for row in rows}
    assert "00-0032430" not in attributed
    assert "00-0032606" not in attributed


# ── G3: non-finite and out-of-range utilization numerics fail named ──


@pytest.mark.parametrize(
    ("value", "reason"),
    [
        (float("nan"), "utilization_value_nonfinite"),
        (float("inf"), "utilization_value_nonfinite"),
        (-0.1, "utilization_snap_share_out_of_range"),
        (1.1, "utilization_snap_share_out_of_range"),
    ],
)
def test_prediction_utilization_numeric_edges_fail_named(value, reason) -> None:
    cli = _cli()
    with pytest.raises(Exception, match=reason):
        cli._parse_prediction_utilization(
            {"snap_share": {"value": value, "role": "model_input"}}
        )


def test_prediction_utilization_nonfinite_rejected_on_any_field() -> None:
    cli = _cli()
    with pytest.raises(Exception, match="utilization_value_nonfinite"):
        cli._parse_prediction_utilization(
            {"weighted_opportunity": {"value": float("inf"), "role": "model_input"}}
        )


# ── G4: declared_at must be a timezone-aware date-time, never a bare date ──


@pytest.mark.parametrize(
    "declared_at",
    [
        "2026-08-13",  # date-only
        "2026-08-13T23:59:00",  # timezone-naive
    ],
)
def test_declared_at_date_only_or_naive_fails_named(
    monkeypatch, tmp_path, declared_at
) -> None:
    cli = _cli()
    path = tmp_path / "frozen.json"
    path.write_text(
        json.dumps(
            {
                "seasons": {
                    "2026": {
                        "frozen_capture_date": "2026-08-05",
                        "source": "model_pvo",
                        "declared_by": "David",
                        "declared_at": declared_at,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "FROZEN_PREDICTION_DECLARATION", path)
    with pytest.raises(Exception, match="declared_at_invalid"):
        cli._load_frozen_declaration(2026)


def test_declared_at_timezone_aware_passes(monkeypatch, tmp_path) -> None:
    cli = _cli()
    path = tmp_path / "frozen.json"
    path.write_text(
        json.dumps(
            {
                "seasons": {
                    "2026": {
                        "frozen_capture_date": "2026-08-05",
                        "source": "model_pvo",
                        "declared_by": "David",
                        "declared_at": "2026-08-13T23:59:00-04:00",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "FROZEN_PREDICTION_DECLARATION", path)
    entry = cli._load_frozen_declaration(2026)
    assert entry["frozen_capture_date"] == "2026-08-05"


# ── the real declaration file must itself satisfy the hardened contract ──


def test_committed_declaration_passes_hardened_validation() -> None:
    cli = _cli()
    declaration = Path("app/config/realized_outcome_frozen_predictions.json")
    if not declaration.exists():
        pytest.skip("declaration not present in this tree")
    entry = cli._load_frozen_declaration(2026)
    assert entry["frozen_capture_date"] == "2026-08-05"
    assert entry["source"] == "model_pvo"
