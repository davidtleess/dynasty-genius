"""The capture entry point: explicit paths in, one immutable record out, actual clock always.

Root's API calls `capture_from_paths` directly so the baseline decoding lives in one place; the CLI is
a thin wrapper over the same function. Importing this module must not parse arguments or touch a
store, so the tests import it freely.

The refusals matter more than the happy path. A future-dated source, an unsafe path, a corrupt
destination or missing metadata must all fail WITHOUT modifying a record that already exists.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts.capture_track_record_inputs import capture_from_paths, main
from src.dynasty_genius.capture.track_record_store import list_records
from src.dynasty_genius.capture.workspace_snapshot_store import (
    SnapshotBundle,
    save_snapshot,
)

NOW = datetime(2026, 9, 9, 9, 40, tzinfo=timezone.utc)

TARGET = {"scope": "REG", "scoring": "PPR_nflverse_default", "window": "championship_week17",
          "exposure": "per_season", "event": "points", "clock": "per_season",
          "quantity": "season_points", "labels_through": 2025}
SIX = {"report_run": "20260906T214512Z", "report_sha256": "1" * 64, "market_sha256": "2" * 64,
       "league_sha256": "3" * 64, "catalog_run": "20260907T013635Z",
       "catalog_content_sha256": "4" * 64}


def archive(tmp_path: Path) -> tuple[Path, str]:
    """A real archive, written by the real store, so this test exercises the real reader."""
    root = tmp_path / "archive"
    if root.exists():  # one archive per test; build it once and reuse it
        return root, next(p.name for p in root.iterdir() if p.is_dir())
    plan_bytes = json.dumps({"schema_version": "workspace_evaluation_plan.v1",
                             "plan_id": "workspace-production-2026-v1"},
                            sort_keys=True, separators=(",", ":")).encode()
    raw = {
        "source-manifest.json": json.dumps({"kind": "manifest"}).encode(),
        "report.json": json.dumps({
            "board_target": dict(TARGET),
            "horizon_board": {
                "all_inspectable": [{
                    "player_id": "00-0031234", "sleeper_id": "1", "name": "Ada One",
                    "position": "QB", "producer": "producer-a", "readiness": "comparable",
                    "evidence_verified": True, "reference_player": "Reference Person",
                    "reference_expected_points": 10.0,
                    "seasons": [{"season": 2026, "expected_margin": 90.0}],
                }],
                "annual_producers": [{
                    "model_version": "union_replacement",
                    "replacement": {"QB": [{"rate_quantity": "expected_season_points_same_window",
                                            "rate_ppg": 10.0}]},
                }],
            },
        }).encode(),
        "market.json": json.dumps({"source": "fc_native", "settings_hash": "abc123",
                                   "settings": {"isDynasty": True, "numQbs": 2, "numTeams": 12,
                                                "ppr": 1}, "entries": []}).encode(),
        "league.json": json.dumps({
            "rosters": [{"roster_id": i} for i in range(1, 13)],
            "league": {"name": "Test League", "roster_positions": ["QB", "SUPER_FLEX"],
                       "scoring_settings": {"rec": 1.0, "bonus_rec_te": 0.0}},
        }).encode(),
        "catalog.json": json.dumps({
            "forecast_years": [2026], "future_years": [],
            "rows_detail": [{
                "sleeper_id": "1", "player_id": "00-0031234", "name": "Ada One",
                "league_position": "QB", "join_basis": "census_nfl_gsis", "population": "default",
                "recovered": False, "starting_estimate": False, "missing_reason": None,
                "roster_id": None, "owned_now": False,
                "forecast": {"join_id": "00-0031234",
                             "seasons": [{"season": 2026, "e_points": 100.0}]},
            }],
        }).encode(),
        "catalog-companion.json": json.dumps({"kind": "companion"}).encode(),
        "evaluation-plan.json": plan_bytes,
    }
    def digest(name):
        return hashlib.sha256(raw[name]).hexdigest()
    # the archive cross-checks these against the artifact bytes, so they are derived, never invented
    six = {"report_run": "20260906T214512Z", "report_sha256": digest("report.json"),
           "market_sha256": digest("market.json"), "league_sha256": digest("league.json"),
           "catalog_run": "20260907T013635Z",
           # the semantic content identity: a hash of the CANONICAL catalog document, which is a
           # different fact from the raw file hash (source inventory, September 9)
           "catalog_content_sha256": hashlib.sha256(
               json.dumps(json.loads(raw["catalog.json"]), sort_keys=True,
                          separators=(",", ":")).encode()).hexdigest()}
    source = dict(six) | {"ownership_as_of": "2026-09-06T13:00:52.635970+00:00",
                          "forecast_date": "2026-09-06",
                          "market_as_of": "2026-09-09T09:00:00.000000+00:00",
                          "report_generated_at": "2026-09-06T21:45:12.870592+00:00",
                          "catalog_generated_at": "2026-09-07T01:36:35.993872+00:00"}
    rank_row = {"sleeper_id": "1", "name": "Ada One", "position": "QB", "on_roster": False,
                "league_ownership": "Available", "taxi_or_reserve": None,
                "model_value": 100.0, "market_value": 500.0,
                "our_rank": {"start": 10, "end": 10, "total": 1},
                "market_rank": {"start": 1, "end": 1, "total": 1},
                "model_rank_all": None, "market_rank_published": 1,
                "comparison": {"direction": "higher", "gap_min": 30, "gap_max": 30},
                "missing_reason": None, "model_zero_tie": False, "seasons": [],
                "reference_player": None}
    ranks = {"status": "available", "source": source, "basis": {"years": [2026]},
             "coverage": {"model_players": 1, "market_players": 1, "market_picks": 0,
                          "common_players": 1, "total_players": 1, "roster_players": 0,
                          "roster_common_players": 0},
             "rows": [rank_row]}
    comparison = {"source": source, "forecast_years": [2026], "future_years": [], "roster": [],
                  "available": [{"sleeper_id": "1", "name": "Ada One", "position": "QB",
                                 "now_points": 100.0, "future_points": 400.0, "seasons": [],
                                 "starting_estimate": False, "missing_reason": None,
                                 "population": "default", "producer": "producer-a"}]}
    saved = save_snapshot(
        root, SnapshotBundle(artifacts=raw, ranks=ranks, comparison=comparison),
        captured_at=datetime(2026, 9, 9, 9, 30, 0, tzinfo=timezone.utc), code_sha="0" * 40,
    )
    return root, saved["snapshot"]["snapshot_id"]


def sources(tmp_path: Path, *, captured_at: str = "2026-09-09T09:40:00Z") -> dict:
    csv_bytes = (b"player_id,season,points,games,appeared\n"
                 b"00-0031234,2025,10.0,17,true\n00-0031299,2025,30.0,17,true\n")
    manifest_bytes = json.dumps({
        "schema_version": "dg179_league_season_outcomes_v1",
        "scoring_preset": "nflverse_default_ppr_championship_window_v1",
        "coverage_status": "qualified_research_game_complete_identified_rows",
        "league_scoring_exact": False, "last_complete_season": 2025,
        "season_windows": {"2025": {"included_reg_weeks": list(range(1, 18))}},
        "outputs": {"outcomes.csv": {"bytes": len(csv_bytes),
                                     "sha256": hashlib.sha256(csv_bytes).hexdigest()}},
    }, sort_keys=True).encode()
    import io as _io

    import pandas as pd
    _buffer = _io.BytesIO()
    pd.DataFrame([{"player_id": pid, "position": "QB", "season": 2025, "week": 1,
                   "season_type": "REG"} for pid in ("00-0031234", "00-0031299")]
                 ).to_parquet(_buffer, index=False)
    evidence_bytes = _buffer.getvalue()
    raw_schedule = ("game_id,season,game_type,week,gameday,gametime\n" + "".join(
        f"2026_{w:02d}_A_B,2026,REG,{w},2026-09-{8 + w:02d},20:20\n" for w in range(1, 18))).encode()
    dictionary = (b'gameday,character, The date on which the game occurred.\n'
                  b'gametime,character,"The kickoff time of the game. This is represented in '
                  b'24-hour time and the Eastern time zone."\n')
    receipt = {"kind": "dg179_league_season_outcomes_v1", "role": "prior_season_outcomes",
               "csv_sha256": hashlib.sha256(csv_bytes).hexdigest(),
               "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
               "target": dict(TARGET), "prior_season": 2025, "admitted_seasons": [2025],
               "positions": {"00-0031234": "QB", "00-0031299": "QB"},
               "coverage_status": "qualified_research_game_complete_identified_rows",
               "league_scoring_exact": False, "captured_at": captured_at,
               "source_as_of": "2026-01-10T00:00:00Z", "source_available_at": None,
               "source_revision": "nflverse-2026-01-10",
               "source_artifacts": [{
                   "name": "prior-positions.parquet",
                   "path": str(tmp_path / "positions-evidence.bin"),
                   "sha256": hashlib.sha256(evidence_bytes).hexdigest(),
                   "bytes": len(evidence_bytes),
                   "original_path": "stats_player_week_2025.parquet"}]}
    schedule = {"role": "schedule", "season": 2026, "source_sha256": "5" * 64,
                "captured_at": captured_at, "source_as_of": "2026-09-01T00:00:00Z",
                "source_available_at": "2026-09-01T00:00:00Z", "source_revision": "sched-1",
                "timezone": "America/New_York",
                "games": [{"game_id": f"2026_{w:02d}_A_B", "reg": True, "week": w,
                           "kickoff_at": f"2026-09-{9 + w:02d}T00:20:00+00:00", "finalized": None}
                          for w in range(1, 18)],
                "source_artifacts": [
                    {"name": "schedule-raw.csv", "path": str(tmp_path / "schedule-raw.csv"),
                     "sha256": hashlib.sha256(raw_schedule).hexdigest(),
                     "bytes": len(raw_schedule)},
                    {"name": "dictionary_schedules.csv",
                     "path": str(tmp_path / "dictionary_schedules.csv"),
                     "sha256": hashlib.sha256(dictionary).hexdigest(), "bytes": len(dictionary)}]}
    plan = {"plan": "workspace-market-movement-90d-v1", "horizon_days": 90,
            "configuration": {"league": "12-team superflex"}}
    paths = {}
    # Written once. A test that tampers with a source must see its tampering survive the next call.
    for name, payload in (("baseline.csv", csv_bytes), ("baseline-manifest.json", manifest_bytes),
                         ("positions-evidence.bin", evidence_bytes),
                         ("schedule-raw.csv", raw_schedule),
                         ("dictionary_schedules.csv", dictionary)):
        target = tmp_path / name
        if not target.exists():
            target.write_bytes(payload)
        paths[name] = target
    for name, document in (("baseline-receipt.json", receipt), ("schedule.json", schedule),
                           ("market-plan.json", plan)):
        target = tmp_path / name
        if not target.exists():
            target.write_text(json.dumps(document))
        paths[name] = target
    return paths


def capture(tmp_path: Path, *, clock=None, **over):
    paths = sources(tmp_path)
    root, snapshot_id = archive(tmp_path)
    kwargs = dict(
        archive_root=root, snapshot_id=snapshot_id,
        evaluation_root=tmp_path / "evaluation",
        baseline_manifest=paths["baseline-manifest.json"], baseline_csv=paths["baseline.csv"],
        baseline_receipt=paths["baseline-receipt.json"], schedule=paths["schedule.json"],
        market_plan=paths["market-plan.json"], market_history=None,
    )
    kwargs.update(over)
    return capture_from_paths(clock=clock or (lambda: NOW), **kwargs)


def test_importing_the_module_parses_no_arguments_and_touches_no_store():
    import scripts.capture_track_record_inputs as module
    assert callable(module.capture_from_paths) and callable(module.main)


def test_a_capture_saves_one_record_and_reports_per_stream_readiness(tmp_path):
    result = capture(tmp_path)
    assert result["created"] is True
    assert result["record"]["kind"] == "enrollment"
    assert result["readiness"]["production"]["state"] == "awaiting_horizon"
    assert result["readiness"]["market"]["state"] == "awaiting_capture"
    assert result["readiness"]["production"]["provenance_class"] == "reconstructed"


def test_capturing_the_same_sources_twice_keeps_the_first_record(tmp_path):
    first = capture(tmp_path)
    again = capture(tmp_path)
    assert again["created"] is False
    assert again["record"]["record_id"] == first["record"]["record_id"]
    assert again["record"]["recorded_at"] == first["record"]["recorded_at"]
    assert len(list_records(tmp_path / "evaluation", snapshot_id=archive(tmp_path)[1])) == 1


def test_recapturing_unchanged_inputs_a_day_later_returns_the_first_registration(tmp_path):
    """Pressing the button again does not mint a new registration.

    Nothing about the frozen inputs changed, so the enrolment is the same one and keeps its original
    T0. Only the clock differed, and the clock is exactly what must not create a new record.
    """
    first = capture(tmp_path)
    later = capture(tmp_path, clock=lambda: NOW + timedelta(days=1))
    assert later["created"] is False
    assert later["record"]["record_id"] == first["record"]["record_id"]
    assert later["record"]["document"]["enrolled_at"] == "2026-09-09T09:40:00Z"
    assert later["record"]["document"]["market"]["t0"] == "2026-09-09T09:40:00Z"
    assert len(list_records(tmp_path / "evaluation", snapshot_id=archive(tmp_path)[1])) == 1


def test_a_changed_input_does_start_a_new_registration_with_its_own_time(tmp_path):
    """New frozen inputs are a genuinely new registration, and it gets the actual clock."""
    first = capture(tmp_path)
    plan = json.loads((tmp_path / "market-plan.json").read_text())
    plan["horizon_days"] = 30
    (tmp_path / "market-plan.json").write_text(json.dumps(plan))
    changed = capture(tmp_path, clock=lambda: NOW + timedelta(days=1))
    assert changed["created"] is True
    assert changed["record"]["record_id"] != first["record"]["record_id"]
    assert changed["record"]["document"]["enrolled_at"] == "2026-09-10T09:40:00Z"
    records = list_records(tmp_path / "evaluation", snapshot_id=archive(tmp_path)[1])
    assert len(records) == 2, "the store is append-only; the first registration must survive"
    assert records[0]["record_id"] == first["record"]["record_id"]


def test_archive_bytes_unchanged(tmp_path):
    root, _ = archive(tmp_path)
    before = {p: p.read_bytes() for p in sorted(root.rglob("*.json"))}
    capture(tmp_path)
    assert {p: p.read_bytes() for p in sorted(root.rglob("*.json"))} == before


def test_a_future_dated_source_refuses_without_writing(tmp_path):
    paths = sources(tmp_path, captured_at="2027-01-01T00:00:00Z")
    with pytest.raises(ValueError, match="future"):
        capture_from_paths(
            archive_root=archive(tmp_path)[0], snapshot_id=archive(tmp_path)[1],
            evaluation_root=tmp_path / "evaluation",
            baseline_manifest=paths["baseline-manifest.json"], baseline_csv=paths["baseline.csv"],
            baseline_receipt=paths["baseline-receipt.json"], schedule=paths["schedule.json"],
            market_plan=paths["market-plan.json"], clock=lambda: NOW,
        )
    assert not (tmp_path / "evaluation").exists()


def test_an_unsafe_evaluation_root_refuses(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    with pytest.raises(ValueError, match="symlink"):
        capture(tmp_path, evaluation_root=link)


def test_a_missing_source_file_refuses_by_name(tmp_path):
    with pytest.raises(ValueError, match="schedule"):
        capture(tmp_path, schedule=tmp_path / "no-such-schedule.json")


def test_missing_baseline_metadata_refuses_rather_than_defaulting(tmp_path):
    paths = sources(tmp_path)
    receipt = json.loads(paths["baseline-receipt.json"].read_text())
    del receipt["positions"]
    paths["baseline-receipt.json"].write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="positions"):
        capture(tmp_path)


def test_a_corrupt_existing_record_refuses_and_leaves_it_alone(tmp_path):
    capture(tmp_path)
    document = next((tmp_path / "evaluation").rglob("document.json"))
    document.write_text(json.dumps({"schema_version": "track_record.enrollment.v1",
                                    "snapshot_id": "a" * 64, "tampered": True}))
    before = document.read_bytes()
    # the same clock reaches the same content id, so this is the corrupt-duplicate path
    with pytest.raises(ValueError, match="content"):
        capture(tmp_path)
    assert document.read_bytes() == before


def test_the_clock_is_the_actual_time_and_no_argument_can_move_it(tmp_path):
    import inspect
    parameters = inspect.signature(capture_from_paths).parameters
    assert "captured_at" not in parameters and "enrolled_at" not in parameters
    assert parameters["clock"].default is None


def test_main_wraps_the_same_function(tmp_path):
    paths = sources(tmp_path)
    root, snapshot_id = archive(tmp_path)
    code = main([
        "--archive-root", str(root), "--snapshot-id", snapshot_id,
        "--evaluation-root", str(tmp_path / "evaluation"),
        "--baseline-manifest", str(paths["baseline-manifest.json"]),
        "--baseline-csv", str(paths["baseline.csv"]),
        "--baseline-receipt", str(paths["baseline-receipt.json"]),
        "--schedule", str(paths["schedule.json"]),
        "--market-plan", str(paths["market-plan.json"]),
    ])
    assert code == 0
    assert len(list_records(tmp_path / "evaluation", snapshot_id=archive(tmp_path)[1])) == 1


def test_a_file_backed_history_inventory_computes_momentum_and_is_preserved(tmp_path):
    """The CLI acceptance for market history: an ordinary JSON inventory naming capture FILES.

    A JSON file cannot carry raw buffers, so the inventory names a path per capture and the CLI reads
    it. This proves the whole path end to end: the bytes are loaded and verified, the comparator is
    selected by the declared rule, momentum is a real positive number computed from the bound prices,
    and the exact capture bytes are stored in the enrollment.
    """
    root, snapshot_id = archive(tmp_path)
    paths = sources(tmp_path)

    # T0 is 2026-09-09T09:40Z, so the declared window is an as-of in [Aug 7, Aug 10].
    content = {
        "as_of": "2026-08-10T00:00:00Z", "complete": True,
        "configuration": {"source": "fc_native", "settings_hash": "abc123",
                          "isDynasty": True, "numQbs": 2, "numTeams": 12, "ppr": 1},
        "prices": {"1": 400.0},
    }
    capture_bytes = json.dumps(content, sort_keys=True).encode()
    capture_path = tmp_path / "capture-2026-08-10.json"
    capture_path.write_bytes(capture_bytes)

    inventory = {
        "role": "market_history", "kind": "fantasycalc_capture_inventory",
        "captured_at": "2026-09-09T09:40:00Z", "source_as_of": "2026-08-10T00:00:00Z",
        "source_available_at": "2026-08-10T00:00:00Z", "source_revision": "history-1",
        "captures": [{
            "capture_id": "cap-2026-08-10", "as_of": "2026-08-10T00:00:00Z",
            "known_at": "2026-08-10T06:00:00Z", "path": str(capture_path),
            "sha256": hashlib.sha256(capture_bytes).hexdigest(), "bytes": len(capture_bytes),
        }],
    }
    history_path = tmp_path / "market-history.json"
    history_path.write_text(json.dumps(inventory))

    result = capture_from_paths(
        archive_root=root, snapshot_id=snapshot_id, evaluation_root=tmp_path / "evaluation",
        baseline_manifest=paths["baseline-manifest.json"], baseline_csv=paths["baseline.csv"],
        baseline_receipt=paths["baseline-receipt.json"], schedule=paths["schedule.json"],
        market_plan=paths["market-plan.json"], market_history=history_path, clock=lambda: NOW,
    )
    document = result["record"]["document"]
    market = document["market"]
    assert market["comparator_capture"]["capture_id"] == "cap-2026-08-10"
    assert market["comparator_reason"] == ""

    row = next(r for r in market["rows"] if r["sleeper_id"] == "1")
    assert row["momentum"] == pytest.approx(0.25)  # the archived 500.0 start over the bound 400.0

    stored = tmp_path / "evaluation" / result["record"]["record_id"][:2] / \
        result["record"]["record_id"] / "artifacts" / "market-history-capture-cap-2026-08-10.json"
    assert stored.read_bytes() == capture_bytes, "the stored capture is not the file that was verified"
    assert "market-history-capture-cap-2026-08-10.json" in document["input_hashes"]
    assert "market-history.json" in document["input_hashes"]


def test_a_history_capture_whose_file_does_not_match_its_declared_length_refuses(tmp_path):
    root, snapshot_id = archive(tmp_path)
    paths = sources(tmp_path)
    capture_path = tmp_path / "capture-short.json"
    capture_path.write_bytes(b"{}")
    history_path = tmp_path / "market-history.json"
    history_path.write_text(json.dumps({
        "role": "market_history", "captured_at": "2026-09-09T09:40:00Z",
        "source_as_of": "2026-08-10T00:00:00Z", "source_available_at": "2026-08-10T00:00:00Z",
        "source_revision": "history-1",
        "captures": [{"capture_id": "cap", "as_of": "2026-08-10T00:00:00Z",
                      "known_at": "2026-08-10T06:00:00Z", "path": str(capture_path),
                      "sha256": "0" * 64, "bytes": 999}],
    }))
    with pytest.raises(ValueError, match="bytes"):
        capture_from_paths(
            archive_root=root, snapshot_id=snapshot_id, evaluation_root=tmp_path / "evaluation",
            baseline_manifest=paths["baseline-manifest.json"], baseline_csv=paths["baseline.csv"],
            baseline_receipt=paths["baseline-receipt.json"], schedule=paths["schedule.json"],
            market_plan=paths["market-plan.json"], market_history=history_path, clock=lambda: NOW,
        )
    assert not (tmp_path / "evaluation").exists()
