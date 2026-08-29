"""DG-050 RED — replay-reproducibility harness (Master Proposal 3 §6.2).

Written test-first 2026-08-28, before ``src/dynasty_genius/replay/`` existed.
The §6.2 guarantee under test: replaying a raw snapshot with the same parser
version must reproduce the normalized content the store holds. Ticket:
~/dg-build/tickets/DG-050-replay-reproducibility-harness-prove-snapshot-parser-version.md

Everything here is hermetic: scratch SQLite stores, scratch raw roots, scratch
league runtime trees. The harness under test must be READ-ONLY against every
store it replays — one test proves it cannot even create a missing database.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

from src.dynasty_genius.capture.fc_forward_capture_driver import (
    map_fantasycalc_payload_to_entries,
)
from src.dynasty_genius.capture.fc_forward_capture_store import FCForwardCaptureStore
from src.dynasty_genius.nflverse_usage import (
    StreamSpec,
    UsageStore,
    normalize_rows,
    write_raw_snapshot,
)
from src.dynasty_genius.replay.replay_harness import (
    RECEIPT_SCHEMA_VERSION,
    replay_fc_forward,
    replay_league_snapshot,
    replay_nflverse_seasonal,
    replay_nflverse_snapshot,
    run_replay,
    write_receipt,
)
from src.dynasty_genius.sleeper_universe import (
    build_coverage_report,
    build_universe_snapshot,
)
from src.dynasty_genius.team_posture import build_team_posture_artifact

CAPTURED_AT = "2026-08-01T10:00:00.000000+00:00"
OBSERVED_AT = "2026-08-01T10:00:05.000000+00:00"


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


def _seasonal_spec() -> StreamSpec:
    return StreamSpec(
        name="toy_stream",
        table="toy_stream",
        identity_column="",
        identity_kind="",
        grain=("season", "week", "player"),
        columns=("season", "week", "player", "yards"),
        loader=None,
        loader_kwargs={},
        integer_columns=("season", "week", "yards"),
        identity_applicable=False,
    )


def _snapshot_spec() -> StreamSpec:
    return StreamSpec(
        name="toy_snap",
        table="toy_snap",
        identity_column="",
        identity_kind="",
        grain=(),
        columns=("item", "amount"),
        loader=None,
        loader_kwargs={},
        integer_columns=("amount",),
        identity_applicable=False,
        capture_axis="snapshot",
    )


def _capture_seasonal(tmp_path: Path) -> tuple[StreamSpec, Path, Path, Path]:
    """One real seasonal capture into scratch: raw file + store, linked by time."""
    spec = _seasonal_spec()
    raw_root = tmp_path / "nflverse_usage"
    db_path = tmp_path / "nflverse_usage.db"
    records = [
        {"season": 2025, "week": 1, "player": "A. Adams", "yards": 10},
        {"season": 2025, "week": 2, "player": "A. Adams", "yards": 20},
        {"season": 2025, "week": 1, "player": "B. Brown", "yards": 5},
    ]
    raw_path = write_raw_snapshot(
        records, stream=spec.name, season=2025,
        captured_at=CAPTURED_AT, raw_root=raw_root,
    )
    rows, coverage = normalize_rows(records, spec=spec, season=2025, identity=None)
    store = UsageStore(db_path, (spec,))
    outcome = store.apply_season(
        spec, season=2025, rows=rows, coverage=coverage, ingested_at=CAPTURED_AT
    )
    assert outcome == "inserted"
    return spec, db_path, raw_root, raw_path


def _capture_snapshot(tmp_path: Path) -> tuple[StreamSpec, Path, Path, Path]:
    spec = _snapshot_spec()
    raw_root = tmp_path / "nflverse_usage"
    db_path = tmp_path / "nflverse_usage.db"
    records = [{"item": "alpha", "amount": 1}, {"item": "beta", "amount": 2}]
    raw_path = write_raw_snapshot(
        records, stream=spec.name, season=None,
        captured_at=CAPTURED_AT, raw_root=raw_root,
        partition={
            "capture_axis": "snapshot",
            "snapshot_id": "run1:toy_snap",
            "observed_at": OBSERVED_AT,
        },
    )
    raw_sha256 = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    rows, coverage = normalize_rows(records, spec=spec, season=None, identity=None)
    store = UsageStore(db_path, (spec,))
    outcome = store.apply_snapshot(
        spec, rows=rows, coverage=coverage, ingested_at=CAPTURED_AT,
        snapshot_id="run1:toy_snap", observed_at=OBSERVED_AT,
        raw_sha256=raw_sha256, raw_snapshot=str(raw_path),
    )
    assert outcome == "inserted"
    return spec, db_path, raw_root, raw_path


def _fc_payload() -> list[dict]:
    return [
        {
            "player": {"id": 101, "sleeperId": "4034", "name": "P One",
                       "position": "RB"},
            "value": 7000, "overallRank": 1, "positionRank": 1,
            "trend30Day": 12, "maybeMovingStandardDeviation": 3.5,
        },
        {
            "player": {"id": 102, "sleeperId": "6786", "name": "P Two",
                       "position": "WR"},
            "value": 6500, "overallRank": 2, "positionRank": 1,
            "trend30Day": -4,
        },
        {
            # No sleeperId: survivorship-complete raw row, absent from joinable.
            "player": {"id": 103, "sleeperId": None, "name": "P Three",
                       "position": "QB"},
            "value": 100, "overallRank": 3, "positionRank": 1,
            "trend30Day": 0,
        },
    ]


def _capture_fc(tmp_path: Path) -> Path:
    from datetime import datetime, timezone

    db_path = tmp_path / "fc_forward_capture.db"
    entries = map_fantasycalc_payload_to_entries(
        _fc_payload(),
        retrieved_at=datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc),
    )
    counts = FCForwardCaptureStore(db_path).append_entries(entries)
    assert counts == {"raw_entries_written": 3, "joinable_rows_written": 2}
    return db_path


def _league_snapshot() -> dict:
    league = {
        "name": "Toy League", "season": "2026",
        "roster_positions": ["QB", "RB"],
        "scoring_settings": {"rec": 1.0},
        "settings": {"draft_rounds": 3},
    }
    players = {
        "p1": {"full_name": "P One", "position": "RB", "team": "SF",
               "age": 24, "years_exp": 2, "status": "Active"},
        "p2": {"full_name": "P Two", "position": "WR", "team": "KC",
               "age": 26, "years_exp": 4, "status": "Active"},
    }
    rosters = [
        {"roster_id": 1, "owner_id": "u1", "players": ["p1"],
         "starters": ["p1"], "taxi": [], "reserve": []},
        {"roster_id": 2, "owner_id": "u2", "players": ["p2"],
         "starters": ["p2"], "taxi": [], "reserve": []},
    ]
    users = [
        {"user_id": "u1", "display_name": "David"},
        {"user_id": "u2", "display_name": "Rival"},
    ]
    return build_universe_snapshot(
        league_id="L1", league=league, players=players, rosters=rosters,
        users=users, traded_picks=[], draft_state={}, draft_picks=[],
        captured_at=CAPTURED_AT, david_roster_id=1,
    )


def _team_matrix() -> dict:
    def team(roster_id: int, name: str, strength: float) -> dict:
        return {
            "roster_id": roster_id,
            "owner": {"display_name": name},
            "team_value_views": {"starter_weighted_xvar": strength},
            "future_picks": {"owned": [], "outgoing": []},
            "players": [],
        }

    return {
        "schema_version": "team_value_matrix.v1",
        "league_id": "L1",
        "captured_at": CAPTURED_AT,
        "teams": [team(1, "David", 12.0), team(2, "Rival", 8.0)],
    }


def _write_league_run(tmp_path: Path) -> Path:
    """A run dir + marker exactly as league_capture.run_capture serializes them."""
    runtime_root = tmp_path / "league_runtime"
    run_id = "league-20260801T100000Z"
    run_dir = runtime_root / "runs" / run_id
    run_dir.mkdir(parents=True)

    snapshot = _league_snapshot()
    matrix = _team_matrix()
    contents = {
        "snapshot.json": snapshot,
        "coverage.json": build_coverage_report(snapshot),
        "team_posture.json": build_team_posture_artifact(
            matrix, captured_at=CAPTURED_AT
        ),
        "team_value_matrix.json": matrix,
        "roster_cut_report.json": {"decision_supported": False},
        "provenance.json": {"decision_supported": False},
    }
    digests = {}
    for name, payload in contents.items():
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        (run_dir / name).write_bytes(body)
        digests[name] = hashlib.sha256(body).hexdigest()
    marker = {
        "run_id": run_id,
        "source_captured_at": CAPTURED_AT,
        "artifacts": sorted(contents),
        "sha256": digests,
        "unresolved_count": 0,
    }
    (runtime_root / "ready_latest.json").write_text(
        json.dumps(marker, sort_keys=True), encoding="utf-8"
    )
    return runtime_root


def _by_check(results: list) -> dict[str, object]:
    index: dict[str, object] = {}
    for result in results:
        index[f"{result.stream}/{result.check}"] = result
    return index


# ---------------------------------------------------------------------------
# nflverse seasonal
# ---------------------------------------------------------------------------


def test_seasonal_replay_reproduces_the_stored_digest(tmp_path):
    spec, db_path, raw_root, raw_path = _capture_seasonal(tmp_path)
    results = replay_nflverse_seasonal(
        db_path=db_path, raw_root=raw_root, specs=(spec,), identity=None
    )
    assert len(results) == 1
    result = results[0]
    assert result.stream == "nflverse:toy_stream"
    assert result.check == "seasonal_digest"
    assert result.status == "reproduced"
    assert result.evidence["raw_snapshot"] == str(raw_path)
    assert result.evidence["ledger_content_hash"] == (
        result.evidence["replayed_content_hash"]
    )
    assert result.evidence["rows_total"] == 3


def test_seasonal_replay_detects_a_tampered_raw_snapshot(tmp_path):
    spec, db_path, raw_root, raw_path = _capture_seasonal(tmp_path)
    envelope = json.loads(raw_path.read_text(encoding="utf-8"))
    envelope["records"][0]["yards"] = 999
    raw_path.write_text(json.dumps(envelope), encoding="utf-8")
    results = replay_nflverse_seasonal(
        db_path=db_path, raw_root=raw_root, specs=(spec,), identity=None
    )
    assert results[0].status == "mismatch"
    assert results[0].evidence["ledger_content_hash"] != (
        results[0].evidence["replayed_content_hash"]
    )


def test_seasonal_replay_refuses_a_different_parser_version(tmp_path):
    spec, db_path, raw_root, raw_path = _capture_seasonal(tmp_path)
    envelope = json.loads(raw_path.read_text(encoding="utf-8"))
    envelope["schema_version"] = "nflverse_usage.v0"
    raw_path.write_text(json.dumps(envelope), encoding="utf-8")
    results = replay_nflverse_seasonal(
        db_path=db_path, raw_root=raw_root, specs=(spec,), identity=None
    )
    assert results[0].status == "parser_version_mismatch"
    assert results[0].evidence["raw_schema_version"] == "nflverse_usage.v0"


def test_seasonal_replay_is_readonly_and_reports_a_missing_store(tmp_path):
    spec = _seasonal_spec()
    db_path = tmp_path / "absent.db"
    results = replay_nflverse_seasonal(
        db_path=db_path, raw_root=tmp_path / "raw", specs=(spec,), identity=None
    )
    assert [r.status for r in results] == ["no_snapshot"]
    # READ-ONLY posture: probing a missing store must not create it.
    assert not db_path.exists()


# ---------------------------------------------------------------------------
# nflverse snapshot axis
# ---------------------------------------------------------------------------


def test_snapshot_replay_reproduces_raw_hash_and_digest(tmp_path):
    spec, db_path, raw_root, raw_path = _capture_snapshot(tmp_path)
    results = replay_nflverse_snapshot(db_path=db_path, specs=(spec,))
    index = _by_check(results)
    assert index["nflverse:toy_snap/raw_sha256"].status == "reproduced"
    assert index["nflverse:toy_snap/snapshot_digest"].status == "reproduced"
    assert index["nflverse:toy_snap/snapshot_digest"].evidence[
        "snapshot_id"
    ] == "run1:toy_snap"


def test_snapshot_replay_detects_tampered_raw_bytes(tmp_path):
    spec, db_path, raw_root, raw_path = _capture_snapshot(tmp_path)
    body = raw_path.read_text(encoding="utf-8").replace('"alpha"', '"gamma"')
    raw_path.write_text(body, encoding="utf-8")
    results = replay_nflverse_snapshot(db_path=db_path, specs=(spec,))
    index = _by_check(results)
    assert index["nflverse:toy_snap/raw_sha256"].status == "mismatch"
    # The digest check must NOT claim reproduction from unproven bytes.
    assert "nflverse:toy_snap/snapshot_digest" not in index


# ---------------------------------------------------------------------------
# fc forward capture
# ---------------------------------------------------------------------------


def test_fc_replay_reproduces_hashes_and_joinable_projection(tmp_path):
    db_path = _capture_fc(tmp_path)
    results = replay_fc_forward(db_path=db_path)
    index = _by_check(results)
    payload = index["fc_forward_capture/payload_hash"]
    joinable = index["fc_forward_capture/joinable_projection"]
    assert payload.status == "reproduced"
    assert payload.evidence["rows_total"] == 3
    assert joinable.status == "reproduced"
    assert joinable.evidence["joinable_rows"] == 2


def test_fc_replay_detects_tampered_rows(tmp_path):
    db_path = _capture_fc(tmp_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE fc_forward_capture_raw SET value = 1 "
            "WHERE player_key = 'sleeper:4034'"
        )
    results = replay_fc_forward(db_path=db_path)
    index = _by_check(results)
    assert index["fc_forward_capture/payload_hash"].status == "mismatch"
    assert "sleeper:4034" in (
        index["fc_forward_capture/payload_hash"].evidence["mismatched_player_keys"]
    )
    # The raw row now disagrees with the joinable copy too.
    assert index["fc_forward_capture/joinable_projection"].status == "mismatch"


def test_fc_content_address_survives_sqlite_type_roundtrip(tmp_path):
    """The 2026-08-28 live finding: FantasyCalc sends integral volatilities as
    ints; the REAL column returns them as floats, so the capture-time hash was
    unreproducible from the store. The mapping must serialize what SQLite will
    give back (172/474 live rows failed replay before this fix)."""
    from datetime import datetime, timezone

    payload = [
        {
            "player": {"id": 201, "sleeperId": "9999", "name": "Int Vol",
                       "position": "WR"},
            # int volatility + float-integral rank: both storage-normalizable.
            "value": 55.0, "overallRank": 3.0, "positionRank": 1,
            "trend30Day": 0, "maybeMovingStandardDeviation": 2,
        },
    ]
    entries = map_fantasycalc_payload_to_entries(
        payload,
        retrieved_at=datetime(2026, 8, 28, 13, 0, 0, tzinfo=timezone.utc),
    )
    db_path = tmp_path / "fc_forward_capture.db"
    FCForwardCaptureStore(db_path).append_entries(entries)
    results = replay_fc_forward(db_path=db_path)
    index = _by_check(results)
    assert index["fc_forward_capture/payload_hash"].status == "reproduced"
    assert index["fc_forward_capture/joinable_projection"].status == "reproduced"


def test_fc_replay_names_the_legacy_integral_volatility_vintage(tmp_path):
    """Rows captured BEFORE the mapping fix are immutable and their int-shape
    hashes can never be re-derived from the REAL column naively. The harness
    must classify them as the documented legacy vintage — named and counted,
    neither a false alarm nor a silent pass."""
    from datetime import datetime, timezone

    from src.dynasty_genius.capture.fc_forward_capture_driver import (
        _content_hash,
    )

    payload = [
        {
            "player": {"id": 301, "sleeperId": "8888", "name": "Legacy Row",
                       "position": "RB"},
            "value": 100, "overallRank": 9, "positionRank": 4,
            "trend30Day": 1, "maybeMovingStandardDeviation": 4,
        },
    ]
    entries = map_fantasycalc_payload_to_entries(
        payload,
        retrieved_at=datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc),
    )
    # Recreate the pre-fix capture exactly: int volatility in the stored row
    # AND in the hashed content shape.
    legacy = dict(entries[0])
    legacy["market_volatility"] = 4
    legacy["payload_hash"] = _content_hash(
        {
            "sleeper_id": "8888", "player_name": "Legacy Row",
            "position": "RB", "value": 100, "overall_rank": 9,
            "position_rank": 4, "trend_30day": 1, "market_volatility": 4,
            "market_volatility_status": "captured",
        }
    )
    db_path = tmp_path / "fc_forward_capture.db"
    FCForwardCaptureStore(db_path).append_entries([legacy])
    results = replay_fc_forward(db_path=db_path)
    index = _by_check(results)
    payload_check = index["fc_forward_capture/payload_hash"]
    assert payload_check.status == "legacy_content_shape"
    assert payload_check.evidence["rows_legacy_integral_volatility"] == 1
    assert payload_check.evidence["rows_mismatched"] == 0


# ---------------------------------------------------------------------------
# league snapshot
# ---------------------------------------------------------------------------


def test_league_replay_reproduces_all_four_checks(tmp_path):
    runtime_root = _write_league_run(tmp_path)
    results = replay_league_snapshot(runtime_root=runtime_root)
    index = _by_check(results)
    for check in (
        "artifact_digests", "lineage_hashes", "coverage_rederive",
        "posture_rederive",
    ):
        assert index[f"league_snapshot/{check}"].status == "reproduced", check


def test_league_replay_detects_artifact_and_derive_drift(tmp_path):
    runtime_root = _write_league_run(tmp_path)
    marker = json.loads(
        (runtime_root / "ready_latest.json").read_text(encoding="utf-8")
    )
    run_dir = runtime_root / "runs" / marker["run_id"]

    # Drift the DERIVED artifact while keeping the marker digest honest — the
    # simulation of a parser that no longer reproduces its stored output.
    coverage = json.loads((run_dir / "coverage.json").read_text(encoding="utf-8"))
    coverage["total_players"] = coverage["total_players"] + 1
    body = json.dumps(coverage, sort_keys=True).encode("utf-8")
    (run_dir / "coverage.json").write_bytes(body)
    marker["sha256"]["coverage.json"] = hashlib.sha256(body).hexdigest()
    (runtime_root / "ready_latest.json").write_text(
        json.dumps(marker, sort_keys=True), encoding="utf-8"
    )

    results = replay_league_snapshot(runtime_root=runtime_root)
    index = _by_check(results)
    assert index["league_snapshot/artifact_digests"].status == "reproduced"
    assert index["league_snapshot/coverage_rederive"].status == "mismatch"

    # Now corrupt the artifact bytes without fixing the marker: integrity fails.
    (run_dir / "coverage.json").write_bytes(body + b" ")
    results = replay_league_snapshot(runtime_root=runtime_root)
    index = _by_check(results)
    assert index["league_snapshot/artifact_digests"].status == "mismatch"


def test_league_replay_reports_a_missing_marker(tmp_path):
    results = replay_league_snapshot(runtime_root=tmp_path / "league_runtime")
    assert [r.status for r in results] == ["no_snapshot"]


# ---------------------------------------------------------------------------
# receipt + runner
# ---------------------------------------------------------------------------


def test_run_replay_writes_a_dated_receipt(tmp_path):
    repo_root = tmp_path / "repo"
    (repo_root / "app" / "data").mkdir(parents=True)
    _capture_fc(repo_root / "app" / "data")
    league_root = _write_league_run(repo_root / "app" / "data")

    receipt = run_replay(repo_root=repo_root)
    assert receipt["schema_version"] == RECEIPT_SCHEMA_VERSION
    assert receipt["verdict"] == "reproduced"
    assert receipt["generated_at"].endswith("+00:00")
    statuses = {c["status"] for c in receipt["checks"]}
    assert "mismatch" not in statuses and "error" not in statuses
    assert league_root.name == "league_runtime"

    ops_root = repo_root / "app" / "data" / "ops"
    latest, dated = write_receipt(receipt, ops_root=ops_root)
    assert latest == ops_root / "replay_reproducibility_latest.json"
    assert dated.parent == ops_root / "replay_reproducibility" / "runs"
    assert json.loads(latest.read_text(encoding="utf-8")) == receipt
    assert json.loads(dated.read_text(encoding="utf-8")) == receipt


def test_run_replay_with_nothing_to_replay_says_so(tmp_path):
    repo_root = tmp_path / "empty_repo"
    (repo_root / "app" / "data").mkdir(parents=True)
    receipt = run_replay(repo_root=repo_root)
    assert receipt["verdict"] == "nothing_replayed"
    assert all(c["status"] == "no_snapshot" for c in receipt["checks"])


def _script():
    """Load scripts/run_replay_reproducibility.py as a module (scripts/ is
    no package) — same pattern as the DG-044 contract tests."""
    import importlib.util
    import sys

    name = "run_replay_reproducibility"
    if name in sys.modules:
        return sys.modules[name]
    path = REPO_ROOT / "scripts" / "run_replay_reproducibility.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        del sys.modules[name]
        raise
    return module


def test_script_exit_codes_and_receipt(tmp_path, capsys):
    repo_root = tmp_path / "repo"
    (repo_root / "app" / "data").mkdir(parents=True)
    _capture_fc(repo_root / "app" / "data")
    _write_league_run(repo_root / "app" / "data")

    code = _script().main(["--repo-root", str(repo_root)])
    assert code == 0
    out = capsys.readouterr().out
    assert "verdict: reproduced" in out
    latest = repo_root / "app" / "data" / "ops" / (
        "replay_reproducibility_latest.json"
    )
    assert latest.is_file()
    receipt = json.loads(latest.read_text(encoding="utf-8"))
    assert receipt["verdict"] == "reproduced"

    empty = tmp_path / "empty"
    (empty / "app" / "data").mkdir(parents=True)
    assert _script().main(["--repo-root", str(empty)]) == 2


def test_duplicate_receipt_within_one_second_is_config_exit_not_false_alarm(
    tmp_path, monkeypatch
):
    """Pre-land review minor: write_receipt's overwrite refusal escaped main()
    as an unhandled FileExistsError → exit 1, the code reserved for a REAL
    §6.2 failure. A same-second duplicate run must exit 2 (environment), never
    masquerade as not_reproduced."""
    import scripts.run_replay_reproducibility as cli

    def fake_run_replay(**_kwargs):
        return {"checks": [], "verdict": "reproduced", "totals": {},
                "run_id": "replay-20260828T000000Z",
                "generated_at": "2026-08-28T00:00:00+00:00"}

    monkeypatch.setattr(cli, "run_replay", fake_run_replay)

    def fake_write_receipt(_receipt, *, ops_root):
        raise FileExistsError("run receipt already exists, refusing to overwrite")

    monkeypatch.setattr(cli, "write_receipt", fake_write_receipt)
    rc = cli.main(["--repo-root", str(tmp_path), "--ops-root", str(tmp_path)])
    assert rc == 2
