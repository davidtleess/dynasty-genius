"""RED — nflverse export must survive a late non-null `snapshot_id`.

THE LIVE FAILURE THIS ENCODES (2026-08-08, run nflverse-usage-20260808T0228465894550000):
the first scheduled-style run that included `contracts` wrote all thirteen source
Parquets and then died building the combined unresolved-identity frame:

    ComputeError: could not append value "nflverse-usage-...:contracts" of type str to
    the builder; make sure that all rows have the same schema or consider increasing
    `infer_schema_length`

MECHANISM: `pl.DataFrame(unresolved_frames)` infers column types from a BOUNDED window
of leading rows. Seasonal unresolved rows carry `snapshot_id=None`; snapshot-axis rows
(contracts) carry a string. When every row inside the inference window is null, Polars
builds a Null column and the first real string afterwards cannot be appended.

WHY THIS IS NOT A FORMATTING BUG: the failure lands AFTER the source Parquets are
written, so a partial run directory is left on disk while the ready marker still names
the previous good run. The store, the source bytes and the failed status marker are the
honest evidence of the attempt; an orphaned run directory that LOOKS like a completed
export is not.

Bounded to the export defect. No unrelated refactoring.
"""
from __future__ import annotations

import json
import pathlib

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

from src.dynasty_genius.nflverse_usage import (
    export_ready_marker_path,
    publish_export,
)

#: Polars infers from a bounded leading window; exceed it comfortably so the test pins
#: the CLASS of failure rather than one library version's exact window size.
SEASONAL_ROWS_BEFORE_SNAPSHOT = 400


def _unresolved_rows() -> list[dict]:
    """Seasonal rows (snapshot_id=None) then ONE snapshot row carrying a real string."""
    rows: list[dict] = []
    for i in range(SEASONAL_ROWS_BEFORE_SNAPSHOT):
        rows.append(
            {
                "stream": "ngs_passing",
                "source_id": f"src-{i}",
                "identity_kind": "gsis",
                "identity_status": "source_only",
                "capture_axis": "seasonal",
                "snapshot_id": None,
                "observed_at": None,
                "season": "2024",
                "player": f"Player {i}",
                "position": "QB",
            }
        )
    rows.append(
        {
            "stream": "contracts",
            "source_id": "src-contract-1",
            "identity_kind": "name",
            "identity_status": "source_only",
            "capture_axis": "snapshot",
            "snapshot_id": "nflverse-usage-20260808T0228465894550000:contracts",
            "observed_at": "2026-08-08T02:28:46+00:00",
            "season": None,
            "player": "Contract Player",
            "position": "WR",
        }
    )
    return rows


def test_unresolved_frame_survives_a_late_non_null_snapshot_id(tmp_path):
    """The exact live failure, reduced to its mechanism."""
    from src.dynasty_genius.nflverse_usage import build_unresolved_identity_frame

    frame = build_unresolved_identity_frame(_unresolved_rows())
    out = tmp_path / "unresolved_identity.parquet"
    frame.write_parquet(out)
    assert out.is_file()
    assert frame.height == SEASONAL_ROWS_BEFORE_SNAPSHOT + 1


#: F1 — the EXACT ordered schema. The measured Aug-5 artifact's seven-column prefix is
#: preserved and the three snapshot columns are APPENDED, so no positional consumer
#: break is smuggled in behind this repair. Every dtype is String, matching production.
EXPECTED_SCHEMA = (
    "stream", "source_id", "identity_kind", "identity_status", "season", "player",
    "position", "capture_axis", "snapshot_id", "observed_at",
)


def test_unresolved_frame_uses_an_explicit_ordered_all_string_schema():
    """Set equality permits arbitrary reorder; checking two dtypes permits eight to drift.

    Column ORDER is a consumer contract for anything reading positionally, and the
    measured prior artifact fixes the first seven. Append-only is the safe shape.
    """
    from src.dynasty_genius.nflverse_usage import (
        UNRESOLVED_IDENTITY_SCHEMA,
        build_unresolved_identity_frame,
    )

    assert tuple(UNRESOLVED_IDENTITY_SCHEMA) == EXPECTED_SCHEMA
    empty = build_unresolved_identity_frame([])
    assert tuple(empty.columns) == EXPECTED_SCHEMA
    populated = build_unresolved_identity_frame(_unresolved_rows())
    assert tuple(populated.columns) == EXPECTED_SCHEMA

    for frame, label in ((empty, "empty"), (populated, "populated")):
        for col in EXPECTED_SCHEMA:
            assert str(frame.schema[col]) == "String", (
                f"{label}: {col} must be String; production reads every one of these "
                f"from SQLite TEXT, got {frame.schema[col]}"
            )


def test_failed_export_leaves_the_previous_ready_marker_byte_identical(tmp_path, monkeypatch):
    """Failure injection AFTER at least one Parquet write.

    The ready marker is the consumer commit point. A failed export must never advance
    it, and must never corrupt it — a consumer reading mid-failure would otherwise be
    handed a run that does not exist.
    """
    import polars as pl

    export_root = tmp_path / "export"
    export_root.mkdir(parents=True)
    marker = export_ready_marker_path(export_root)
    sentinel = json.dumps({"run_id": "previous-good-run"}, indent=1).encode()
    marker.write_bytes(sentinel)

    calls = {"n": 0}
    original = pl.DataFrame.write_parquet

    def _fail_after_first(self, *a, **k):
        calls["n"] += 1
        if calls["n"] > 1:
            raise OSError("synthetic export failure after the first Parquet write")
        return original(self, *a, **k)

    monkeypatch.setattr(pl.DataFrame, "write_parquet", _fail_after_first)

    store, specs, _, _ = _real_store(tmp_path)
    with pytest.raises(OSError, match="synthetic export failure"):
        publish_export(
            store, specs, run_id="synthetic-run",
            captured_at="2026-08-08T00:00:00+00:00", export_root=export_root,
        )

    # Prove the INJECTED boundary was reached. Bare Exception would let a fixture
    # blowup BEFORE the first write pass this test for the wrong reason.
    assert calls["n"] > 1, "the injected post-first-write boundary was never reached"
    assert marker.read_bytes() == sentinel, (
        "a failed export must leave the previous ready marker byte-identical"
    )


def test_failed_export_does_not_leave_a_consumer_looking_run_directory(tmp_path, monkeypatch):
    """An orphaned run directory of Parquets, with no manifest and no promotion, looks
    like a completed export to anything that lists the runs directory. The store, the
    source bytes and the failed status marker are the evidence of the attempt."""
    import polars as pl

    export_root = tmp_path / "export"
    export_root.mkdir(parents=True)

    calls = {"n": 0}
    original = pl.DataFrame.write_parquet

    def _fail_after_first(self, *a, **k):
        calls["n"] += 1
        if calls["n"] > 1:
            raise OSError("synthetic export failure")
        return original(self, *a, **k)

    monkeypatch.setattr(pl.DataFrame, "write_parquet", _fail_after_first)

    store, specs, _, _ = _real_store(tmp_path)
    with pytest.raises(OSError, match="synthetic export failure"):
        publish_export(
            store, specs, run_id="orphan-run",
            captured_at="2026-08-08T00:00:00+00:00", export_root=export_root,
        )

    assert calls["n"] > 1, "the injected post-first-write boundary was never reached"
    orphan = export_root / "runs" / "orphan-run"
    assert not orphan.exists(), (
        "the partial run directory must be cleaned up; a directory of Parquets with no "
        "manifest and no ready promotion reads as a completed export"
    )


def test_successful_export_publishes_every_required_artifact(tmp_path):
    """All source Parquets, the identity artifact, a manifest, and an advanced marker."""
    export_root = tmp_path / "export"
    store, specs, _, _ = _real_store(tmp_path)
    manifest = publish_export(
        store, specs, run_id="good-run",
        captured_at="2026-08-08T00:00:00+00:00", export_root=export_root,
    )
    run_dir = export_root / "runs" / "good-run"
    assert (run_dir / "manifest.json").is_file()
    assert (run_dir / "unresolved_identity.parquet").is_file()
    for spec in specs:
        assert (run_dir / f"{spec.name}.parquet").is_file(), f"{spec.name} not exported"

    marker = json.loads(export_ready_marker_path(export_root).read_text())
    assert marker.get("run_id") == "good-run", "the ready marker must advance on success"

    # F2: a substring check on the manifest proved nothing. Prove the POPULATED stream.
    import polars as pl

    assert manifest["files"]["contracts"]["rows"] > 0, (
        "contracts must export ROWS, not merely appear as a key"
    )
    contracts_df = pl.read_parquet(run_dir / "contracts.parquet")
    assert contracts_df.height > 0, "contracts.parquet is empty"

    unresolved = pl.read_parquet(run_dir / "unresolved_identity.parquet")
    contracts_unresolved = unresolved.filter(pl.col("stream") == "contracts")
    assert contracts_unresolved.height > 0, (
        "the contracts row must appear in the unresolved identity artifact — that row "
        "carrying a non-null snapshot_id after 400 null seasonal rows IS the live failure"
    )
    assert contracts_unresolved["snapshot_id"].null_count() == 0, (
        "the contracts unresolved row must carry its non-null snapshot id"
    )


# --------------------------------------------------------------------- fixtures


def _real_store(tmp_path):
    """A REAL UsageStore seeded through the PRODUCTION path.

    F2: the unseeded bound is withdrawn. A vacuous success path cannot prove the exact
    live failure, which needed a POPULATED seasonal stream followed by a POPULATED
    contracts snapshot. Seeding goes through `normalize_rows(..., season=None)` +
    `apply_snapshot()` — the same route the contracts contract tests use.
    """
    from src.dynasty_genius.nflverse_usage import (
        CONTRACTS,
        IdentityIndex,
        UsageStore,
        build_streams,
        normalize_rows,
    )

    seasonal = next(s for s in build_streams() if s.capture_axis == "seasonal")
    snapshot = CONTRACTS
    assert snapshot.name == "contracts", "the snapshot stream under test must be contracts"

    specs = [seasonal, snapshot]
    store = UsageStore(tmp_path / "store.db", specs)
    identity = IdentityIndex.from_governed_crosswalk()

    # Satisfy the seasonal spec's declared column contract exactly, for the same
    # reason: a row the normalizer refuses tests nothing.
    seasonal_raw = [
        {
            **{col: None for col in seasonal.columns},
            # DISTINCT per row: an empty id for all 400 collides at the declared grain
            # (nflverse_grain_violation). A value that is unique BUT unresolvable gives
            # 400 genuine unresolved rows, which is what the defect needs.
            seasonal.identity_column: f"NOMATCH-{i:04d}",
            "player_display_name": f"Player {i}",
            "position": "QB",
        }
        for i in range(SEASONAL_ROWS_BEFORE_SNAPSHOT)
    ]
    s_norm, s_cov = normalize_rows(
        [dict(r) for r in seasonal_raw], spec=seasonal, season=2024, identity=identity
    )
    store.apply_season(
        seasonal, season=2024, rows=s_norm, coverage=s_cov,
        ingested_at="2026-08-08T00:00:00+00:00",
    )

    # Use the REAL contracts fixture: normalize_rows enforces the full source column
    # contract and rejects a hand-built row (nflverse_schema_drift). A fixture that the
    # production normalizer refuses proves nothing about production.
    fixture = _REPO_ROOT / "tests" / "fixtures" / "contracts_slice.json"
    contracts_raw = json.loads(fixture.read_text(encoding="utf-8"))
    c_norm, c_cov = normalize_rows(
        [dict(r) for r in contracts_raw], spec=snapshot, season=None, identity=identity
    )
    store.apply_snapshot(
        snapshot, rows=c_norm, coverage=c_cov,
        ingested_at="2026-08-08T00:00:00+00:00",
        snapshot_id="good-run:contracts",
        observed_at="2026-08-08T00:00:00+00:00",
        raw_sha256="a" * 64,
        raw_snapshot="/durable/raw/good-run-contracts.json",
    )
    return store, specs, seasonal_raw, contracts_raw




def test_cleanup_failure_is_raised_not_silently_swallowed(tmp_path, monkeypatch):
    """`ignore_errors=True` silently left behind the very orphan the guard prevents.

    If the partial run directory cannot be removed, the caller must be told — a quiet
    lie about the export root's state is worse than a loud failure.
    """
    import shutil

    import polars as pl

    from src.dynasty_genius import nflverse_usage as nu

    export_root = tmp_path / "export"
    export_root.mkdir(parents=True)
    store, specs, _, _ = _real_store(tmp_path)

    calls = {"n": 0}
    original = pl.DataFrame.write_parquet

    def _fail_after_first(self, *a, **k):
        calls["n"] += 1
        if calls["n"] > 1:
            raise OSError("synthetic export failure")
        return original(self, *a, **k)

    def _cleanup_boom(*a, **k):
        raise OSError("synthetic cleanup failure")

    monkeypatch.setattr(pl.DataFrame, "write_parquet", _fail_after_first)
    monkeypatch.setattr(shutil, "rmtree", _cleanup_boom)

    with pytest.raises(nu.UsageCaptureError, match="nflverse_export_cleanup_failed"):
        publish_export(
            store, specs, run_id="cleanup-fail-run",
            captured_at="2026-08-08T00:00:00+00:00", export_root=export_root,
        )
    assert calls["n"] > 1, "the injected post-first-write boundary was never reached"
