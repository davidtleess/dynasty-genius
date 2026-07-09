"""War Room #2 T1 RED: pure Daily What-Changed diff engine.

T1 is a pure read/diff layer over injected fixture stores and an injected current
Sleeper snapshot path. It deliberately does not emit the overwrite-latest report,
assemble structural context, expose the API, or touch frontend code.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.dynasty_genius.capture.fc_forward_capture_store import FCForwardCaptureStore
from src.dynasty_genius.capture.model_forward_capture_store import (
    MODEL_PVO_SOURCE,
    ModelForwardCaptureStore,
)
from src.dynasty_genius.what_changed.daily_diff import build_daily_what_changed_diff

FC_SOURCE = "fc_native"
SETTINGS_HASH = "sf_ppr_12"
MODEL_SOURCE = MODEL_PVO_SOURCE


def _fc_entry(
    *,
    snapshot_date: str,
    player_key: str,
    sleeper_id: str,
    player_name: str,
    position: str,
    value: int,
    overall_rank: int,
    position_rank: int,
) -> dict:
    return {
        "snapshot_date": snapshot_date,
        "source": FC_SOURCE,
        "settings_hash": SETTINGS_HASH,
        "player_key": player_key,
        "sleeper_id": sleeper_id,
        "player_name": player_name,
        "position": position,
        "value": value,
        "overall_rank": overall_rank,
        "position_rank": position_rank,
        "trend_30day": 0,
        "retrieved_at": f"{snapshot_date}T13:00:00+00:00",
        "payload_hash": f"{player_key}:{snapshot_date}:{value}",
        # Phase-0b: the store requires every entry to declare what its volatility
        # field means. These fixtures carry no volatility, which is `source_omitted`.
        "market_volatility": None,
        "market_volatility_status": "source_omitted",
    }


def _model_entry(
    *,
    capture_date: str,
    player_key: str,
    sleeper_id: str,
    player_name: str,
    position: str,
    dynasty_value_score: float,
    dvs_pct: float,
    xvar: float,
    semantic_output_hash: str = "semantic-v1",
    provenance_hash: str = "provenance-v1",
) -> dict:
    return {
        "capture_date": capture_date,
        "source": MODEL_SOURCE,
        "semantic_output_hash": semantic_output_hash,
        "provenance_hash": provenance_hash,
        "player_key": player_key,
        "sleeper_id": sleeper_id,
        "dg_player_id": f"dg_{sleeper_id}",
        "player_name": player_name,
        "position": position,
        "engine_path": "ENGINE_B",
        "dynasty_value_score": dynasty_value_score,
        "dvs_pct": dvs_pct,
        "xvar": xvar,
        "model_grade": "MODEL",
        "model_version": "engine_b_v2",
        "artifact_vintage": f"{capture_date}T14:00:00+00:00",
        "row_index": 0,
        "semantic_row_hash": f"row:{player_key}:{dynasty_value_score}",
        "payload_hash": f"row:{player_key}:{dynasty_value_score}",
    }


def _write_current_sleeper_snapshot(tmp_path: Path, *, roster_players: list[str]) -> Path:
    path = tmp_path / "sleeper_universe_snapshot_latest.json"
    path.write_text(
        json.dumps(
            {
                "captured_at": "2026-06-24T13:17:20+00:00",
                "david_roster_id": 1,
                "rosters": [
                    {
                        "roster_id": 1,
                        "players": roster_players,
                    },
                    {
                        "roster_id": 2,
                        "players": ["9999"],
                    },
                ],
            },
            sort_keys=True,
        )
    )
    return path


def _seed_fc_store(db_path: Path) -> None:
    store = FCForwardCaptureStore(db_path)
    store.append_entries(
        [
            _fc_entry(
                snapshot_date="2026-06-23",
                player_key="sleeper:9509",
                sleeper_id="9509",
                player_name="Bijan Robinson",
                position="RB",
                value=10000,
                overall_rank=5,
                position_rank=2,
            ),
            _fc_entry(
                snapshot_date="2026-06-23",
                player_key="sleeper:6786",
                sleeper_id="6786",
                player_name="CeeDee Lamb",
                position="WR",
                value=9000,
                overall_rank=4,
                position_rank=1,
            ),
            _fc_entry(
                snapshot_date="2026-06-23",
                player_key="sleeper:1111",
                sleeper_id="1111",
                player_name="Exited Player",
                position="RB",
                value=7000,
                overall_rank=30,
                position_rank=10,
            ),
        ]
    )
    store.append_entries(
        [
            _fc_entry(
                snapshot_date="2026-06-24",
                player_key="sleeper:9509",
                sleeper_id="9509",
                player_name="Bijan Robinson",
                position="RB",
                value=10250,
                overall_rank=3,
                position_rank=1,
            ),
            _fc_entry(
                snapshot_date="2026-06-24",
                player_key="sleeper:6786",
                sleeper_id="6786",
                player_name="CeeDee Lamb",
                position="WR",
                value=8600,
                overall_rank=8,
                position_rank=3,
            ),
            _fc_entry(
                snapshot_date="2026-06-24",
                player_key="sleeper:2222",
                sleeper_id="2222",
                player_name="Entered Player",
                position="TE",
                value=5000,
                overall_rank=80,
                position_rank=8,
            ),
        ]
    )


def _seed_model_store_one_date(db_path: Path) -> None:
    store = ModelForwardCaptureStore(db_path)
    store.append_entries(
        [
            _model_entry(
                capture_date="2026-06-24",
                player_key="sleeper:9509",
                sleeper_id="9509",
                player_name="Bijan Robinson",
                position="RB",
                dynasty_value_score=98.5,
                dvs_pct=99.2,
                xvar=21.4,
            )
        ]
    )


def _seed_model_store_two_dates_same_vintage(db_path: Path) -> None:
    store = ModelForwardCaptureStore(db_path)
    for capture_date in ("2026-06-23", "2026-06-24"):
        store.append_entries(
            [
                _model_entry(
                    capture_date=capture_date,
                    player_key="sleeper:9509",
                    sleeper_id="9509",
                    player_name="Bijan Robinson",
                    position="RB",
                    dynasty_value_score=98.5,
                    dvs_pct=99.2,
                    xvar=21.4,
                    semantic_output_hash="semantic-flat",
                    provenance_hash="provenance-flat",
                )
            ]
        )


def _seed_model_store_two_dates_new_provenance_without_score_delta(db_path: Path) -> None:
    store = ModelForwardCaptureStore(db_path)
    store.append_entries(
        [
            _model_entry(
                capture_date="2026-06-23",
                player_key="sleeper:9509",
                sleeper_id="9509",
                player_name="Bijan Robinson",
                position="RB",
                dynasty_value_score=98.5,
                dvs_pct=99.2,
                xvar=21.4,
                semantic_output_hash="semantic-same",
                provenance_hash="provenance-old",
            )
        ]
    )
    store.append_entries(
        [
            _model_entry(
                capture_date="2026-06-24",
                player_key="sleeper:9509",
                sleeper_id="9509",
                player_name="Bijan Robinson",
                position="RB",
                dynasty_value_score=98.5,
                dvs_pct=99.2,
                xvar=21.4,
                semantic_output_hash="semantic-same",
                provenance_hash="provenance-new",
            )
        ]
    )


def test_market_day_over_day_uses_latest_prior_window_and_focused_slices(tmp_path) -> None:
    fc_db = tmp_path / "fc_forward.db"
    model_db = tmp_path / "model_forward.db"
    sleeper_snapshot = _write_current_sleeper_snapshot(
        tmp_path,
        roster_players=["9509", "6786"],
    )
    _seed_fc_store(fc_db)
    _seed_model_store_one_date(model_db)

    result = build_daily_what_changed_diff(
        fc_db_path=fc_db,
        model_db_path=model_db,
        sleeper_snapshot_path=sleeper_snapshot,
        top_n=1,
    )

    assert result["decision_supported"] is False
    assert result["market"]["status"] == "ok"
    assert result["market"]["comparison_window"] == {
        "from_date": "2026-06-23",
        "to_date": "2026-06-24",
    }

    roster_by_sleeper = {
        row["sleeper_id"]: row for row in result["market"]["roster_deltas"]
    }
    assert set(roster_by_sleeper) == {"9509", "6786"}
    assert roster_by_sleeper["9509"]["value_delta"] == 250
    assert roster_by_sleeper["9509"]["value_delta_direction"] == "rose"
    assert roster_by_sleeper["9509"]["overall_rank_delta"] == -2
    assert roster_by_sleeper["9509"]["overall_rank_delta_direction"] == "improved"
    assert roster_by_sleeper["6786"]["value_delta"] == -400
    assert roster_by_sleeper["6786"]["value_delta_direction"] == "fell"
    assert roster_by_sleeper["6786"]["overall_rank_delta"] == 4
    assert roster_by_sleeper["6786"]["overall_rank_delta_direction"] == "declined"

    assert result["market"]["total_movers_count"] == 2
    assert len(result["market"]["top_movers"]) == 1
    assert result["market"]["top_movers"][0]["sleeper_id"] == "6786"
    assert "all_movers" not in result["market"]
    # Increment-1 worklist #2: entered/exited rows carry identity (name /
    # position / team_id) so the UI renders people, not bare ids. team_id is
    # None here because this fixture supplies no roster team map.
    assert result["market"]["entered"] == [
        {
            "sleeper_id": "2222",
            "player_key": "sleeper:2222",
            "player_name": "Entered Player",
            "position": "TE",
            "team_id": None,
        }
    ]
    assert result["market"]["exited"] == [
        {
            "sleeper_id": "1111",
            "player_key": "sleeper:1111",
            "player_name": "Exited Player",
            "position": "RB",
            "team_id": None,
        }
    ]


def test_partial_source_degradation_market_emits_while_model_has_insufficient_history(
    tmp_path,
) -> None:
    fc_db = tmp_path / "fc_forward.db"
    model_db = tmp_path / "model_forward.db"
    sleeper_snapshot = _write_current_sleeper_snapshot(tmp_path, roster_players=["9509"])
    _seed_fc_store(fc_db)
    _seed_model_store_one_date(model_db)

    result = build_daily_what_changed_diff(
        fc_db_path=fc_db,
        model_db_path=model_db,
        sleeper_snapshot_path=sleeper_snapshot,
        top_n=25,
    )

    assert result["market"]["status"] == "ok"
    assert result["model"]["status"] == "insufficient_history"
    assert result["model"]["comparison_window"] == {"status": "insufficient_history"}
    assert result["model"]["deltas"] == []
    assert result["overall_status"] == "degraded"


def test_model_quiet_state_uses_semantic_and_provenance_pair(tmp_path) -> None:
    fc_db = tmp_path / "fc_forward.db"
    sleeper_snapshot = _write_current_sleeper_snapshot(tmp_path, roster_players=["9509"])
    _seed_fc_store(fc_db)

    flat_model_db = tmp_path / "model_flat.db"
    _seed_model_store_two_dates_same_vintage(flat_model_db)
    flat = build_daily_what_changed_diff(
        fc_db_path=fc_db,
        model_db_path=flat_model_db,
        sleeper_snapshot_path=sleeper_snapshot,
        top_n=25,
    )
    assert flat["model"]["status"] == "baseline_holding"
    assert flat["model"]["vintage_changed"] is False
    assert flat["model"]["deltas"] == []

    provenance_changed_db = tmp_path / "model_provenance_changed.db"
    _seed_model_store_two_dates_new_provenance_without_score_delta(
        provenance_changed_db
    )
    provenance_changed = build_daily_what_changed_diff(
        fc_db_path=fc_db,
        model_db_path=provenance_changed_db,
        sleeper_snapshot_path=sleeper_snapshot,
        top_n=25,
    )
    assert provenance_changed["model"]["status"] == "vintage_changed_no_score_delta"
    assert provenance_changed["model"]["vintage_changed"] is True
    assert provenance_changed["model"]["comparison_window"] == {
        "from_date": "2026-06-23",
        "to_date": "2026-06-24",
        "from_vintage": {
            "semantic_output_hash": "semantic-same",
            "provenance_hash": "provenance-old",
        },
        "to_vintage": {
            "semantic_output_hash": "semantic-same",
            "provenance_hash": "provenance-new",
        },
    }
    assert provenance_changed["model"]["deltas"] == []


def test_missing_current_sleeper_snapshot_fails_closed_without_output_side_effects(
    tmp_path,
) -> None:
    fc_db = tmp_path / "fc_forward.db"
    model_db = tmp_path / "model_forward.db"
    missing_snapshot = tmp_path / "missing_snapshot.json"
    _seed_fc_store(fc_db)
    _seed_model_store_one_date(model_db)

    result = build_daily_what_changed_diff(
        fc_db_path=fc_db,
        model_db_path=model_db,
        sleeper_snapshot_path=missing_snapshot,
        top_n=25,
    )

    assert result["overall_status"] == "unavailable"
    assert result["market"]["status"] == "unavailable"
    assert result["market"]["aborted_reason"] == "missing_sleeper_snapshot"
    assert result["model"]["status"] == "insufficient_history"
    assert result["decision_supported"] is False
    assert not (tmp_path / "what_changed_latest_report.json").exists()


def _seed_model_store_same_date_multi_vintage(db_path: Path) -> None:
    """A prior clean date + a latest date carrying TWO distinct vintage pairs.

    The store key includes (semantic_output_hash, provenance_hash), so a same-day
    manual re-capture after a model/feature change legitimately produces two vintage
    rows for one player on one date.
    """
    store = ModelForwardCaptureStore(db_path)
    store.append_entries(
        [
            _model_entry(
                capture_date="2026-06-23",
                player_key="sleeper:9509",
                sleeper_id="9509",
                player_name="Bijan Robinson",
                position="RB",
                dynasty_value_score=98.5,
                dvs_pct=99.2,
                xvar=21.4,
                semantic_output_hash="sem-prior",
                provenance_hash="prov-prior",
            )
        ]
    )
    # Two vintages on the same latest date (separate appends -> distinct PKs).
    store.append_entries(
        [
            _model_entry(
                capture_date="2026-06-24",
                player_key="sleeper:9509",
                sleeper_id="9509",
                player_name="Bijan Robinson",
                position="RB",
                dynasty_value_score=99.0,
                dvs_pct=99.4,
                xvar=21.6,
                semantic_output_hash="sem-new-a",
                provenance_hash="prov-new-a",
            )
        ]
    )
    store.append_entries(
        [
            _model_entry(
                capture_date="2026-06-24",
                player_key="sleeper:9509",
                sleeper_id="9509",
                player_name="Bijan Robinson",
                position="RB",
                dynasty_value_score=100.0,
                dvs_pct=99.6,
                xvar=21.8,
                semantic_output_hash="sem-new-b",
                provenance_hash="prov-new-b",
            )
        ]
    )


def test_model_same_date_multi_vintage_degrades_without_inconsistent_delta(
    tmp_path,
) -> None:
    """A capture date with >1 vintage pair must not yield a window/delta mismatch."""
    fc_db = tmp_path / "fc_forward.db"
    sleeper_snapshot = _write_current_sleeper_snapshot(tmp_path, roster_players=["9509"])
    _seed_fc_store(fc_db)

    multi_vintage_db = tmp_path / "model_multi_vintage.db"
    _seed_model_store_same_date_multi_vintage(multi_vintage_db)

    result = build_daily_what_changed_diff(
        fc_db_path=fc_db,
        model_db_path=multi_vintage_db,
        sleeper_snapshot_path=sleeper_snapshot,
        top_n=25,
    )

    assert result["model"]["status"] == "model_multi_vintage_ambiguous"
    assert result["model"]["deltas"] == []
    assert result["model"]["comparison_window"]["status"] == "model_multi_vintage_ambiguous"
    assert "2026-06-24" in result["model"]["comparison_window"]["ambiguous_dates"]
    # No clean single-vintage determination is possible, so no boolean is asserted.
    assert "vintage_changed" not in result["model"]
    # Market is fine; the ambiguous model section degrades the overall report.
    assert result["market"]["status"] == "ok"
    assert result["overall_status"] == "degraded"
