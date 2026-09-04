"""DG-141 RED: ``provenance_hash`` no longer hashes the league snapshot's capture timestamp.

The vintage is the PAIR ``(semantic_output_hash, provenance_hash)``. Until DG-141 the
lineage subset that feeds ``provenance_hash`` carried ``source_snapshot_captured_at`` — the
microsecond timestamp of the Sleeper league run the PVO was built from — so the hash was
new on every morning by construction and ``vintage_changed`` could never be false across
days. Measured on the live store 2026-09-03: a new vintage pair on 19 of 19 consecutive
capture dates. The driver's own docstring said dates were excluded; the subset hashed one.

David's ruling (Q11, 2026-09-03 06:22 ET): "take the timestamp out". Option (a): the
timestamp leaves the hashed subset, ``semantic_output_hash`` is untouched, no backfill.

These tests pin:
  * the hashed subset carries no ``source_snapshot_captured_at`` key at all;
  * two mornings that read the same models, features and producer — differing only in
    the league snapshot's clock and the artifact's own volatile fields — share one
    ``provenance_hash`` and the second reports ``vintage_changed: false``;
  * the refresh runner's ``provenance_changed`` is likewise false when a refresh only
    re-stamps the snapshot clock (it is the same subset, hashed at both hash sites);
  * a same-day rerun on the SAME snapshot whose content changed still reports a new
    vintage — the 2026-09-02 counter-example — because the semantic half carries it;
  * the audit-only provenance block still records the timestamp, outside the hash.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.dynasty_genius.capture import model_forward_capture_driver as driver
from src.dynasty_genius.capture.model_forward_capture_driver import (
    capture_model_pvo_snapshot,
)
from tests.contract import test_pvo_refresh_runner as refresh_fixtures
from tests.contract.test_model_forward_capture_driver import (
    COVERAGE_PATH,
    PVO_PATH,
    _artifact_bytes,
    _fixture_feature_source,
    _json_bytes,
    _now,
    _pvo_artifact,
    _reader,
)

_MORNING_ONE = "2026-06-23T13:00:46.389713+00:00"
_MORNING_TWO = "2026-06-24T13:00:45.589670+00:00"


def _capture(tmp_path: Path, artifacts: dict[Path, bytes], *, day: int, git_sha: str) -> dict:
    return capture_model_pvo_snapshot(
        db_path=tmp_path / "model_forward.db",
        report_path=None,
        pvo_artifact_path=PVO_PATH,
        coverage_artifact_path=COVERAGE_PATH,
        read_artifact=_reader(artifacts),
        now_fn=_now(day),
        git_sha_fn=lambda: git_sha,
        feature_source=_fixture_feature_source(),
    )


# ── the hashed subset ────────────────────────────────────────────────────────────────


def test_the_hashed_subset_carries_no_snapshot_timestamp() -> None:
    pvo = _pvo_artifact(source_snapshot_captured_at=_MORNING_ONE)
    subset = driver.resolve_provenance_subset(
        pvo,
        read_artifact=_reader(_artifact_bytes()),
        feature_source=_fixture_feature_source(),
    )

    assert "source_snapshot_captured_at" not in subset
    # The rest of the lineage subset is still there — this is a removal, not a rewrite.
    assert subset["pvo_schema_version"] == "universe_pvo_batch.v1"
    assert subset["pvo_producer_hash"]
    assert subset["engine_b"]["feature_csv_sha256"]
    assert subset["engine_a"]["pointer_sha256"]


# ── the capture driver, across two mornings ──────────────────────────────────────────


def test_two_mornings_on_unchanged_inputs_share_a_provenance_hash_and_no_new_vintage(
    tmp_path: Path,
) -> None:
    base = _artifact_bytes(
        {PVO_PATH: _json_bytes(_pvo_artifact(source_snapshot_captured_at=_MORNING_ONE))}
    )
    next_morning = {
        **base,
        PVO_PATH: _json_bytes(
            _pvo_artifact(
                captured_at="2026-06-24T12:00:00+00:00",
                volatile_suffix="b",
                source_snapshot_captured_at=_MORNING_TWO,
            )
        ),
    }

    first = _capture(tmp_path, base, day=24, git_sha="git-sha-a")
    second = _capture(tmp_path, next_morning, day=25, git_sha="git-sha-b")

    assert first["status"] == "ok" and second["status"] == "ok"
    assert first["artifact_sha256"] != second["artifact_sha256"]
    assert first["semantic_output_hash"] == second["semantic_output_hash"]
    assert first["provenance_hash"] == second["provenance_hash"]
    assert first["vintage_changed"] is True
    assert second["vintage_changed"] is False


def test_a_same_day_rerun_whose_content_changed_still_reports_a_new_vintage(
    tmp_path: Path,
) -> None:
    """The 2026-09-02 counter-example: same snapshot clock, 208 rows re-scored."""
    base = _artifact_bytes(
        {PVO_PATH: _json_bytes(_pvo_artifact(source_snapshot_captured_at=_MORNING_ONE))}
    )
    rerun_pvo = _pvo_artifact(volatile_suffix="b", source_snapshot_captured_at=_MORNING_ONE)
    rerun_pvo["players"][0]["valuation"]["dynasty_value_score"] = 97.0
    rerun = {**base, PVO_PATH: _json_bytes(rerun_pvo)}

    first = _capture(tmp_path, base, day=24, git_sha="git-sha-a")
    second = _capture(tmp_path, rerun, day=24, git_sha="git-sha-a")

    assert first["provenance_hash"] == second["provenance_hash"]
    assert first["semantic_output_hash"] != second["semantic_output_hash"]
    assert second["vintage_changed"] is True


def test_the_audit_block_still_records_the_snapshot_timestamp_outside_the_hash(
    tmp_path: Path,
) -> None:
    artifacts = _artifact_bytes(
        {PVO_PATH: _json_bytes(_pvo_artifact(source_snapshot_captured_at=_MORNING_ONE))}
    )

    report = _capture(tmp_path, artifacts, day=24, git_sha="git-sha-a")

    assert report["provenance"]["source_snapshot_captured_at"] == _MORNING_ONE


# ── the refresh runner, which hashes the same subset at both hash sites ──────────────


def test_a_refresh_that_only_restamps_the_snapshot_clock_reports_provenance_unchanged(
    tmp_path: Path,
) -> None:
    runner = refresh_fixtures._load_runner()
    pvo, coverage = refresh_fixtures._write_pair(tmp_path)

    def refresh_restamping_the_clock(
        *, pvo_artifact_path: Path, coverage_artifact_path: Path
    ) -> None:
        payload = json.loads(pvo_artifact_path.read_text())
        assert payload["source_snapshot_captured_at"] == "2026-06-23T11:30:00+00:00"
        payload["source_snapshot_captured_at"] = _MORNING_TWO
        payload["captured_at"] = "2026-06-24T12:00:00+00:00-new"
        for row in payload["players"]:
            row["captured_at"] = "volatile-new"
            row["pipeline_run_id"] = "run-new"
        pvo_artifact_path.write_text(json.dumps(payload, sort_keys=True))
        coverage_artifact_path.write_text(coverage_artifact_path.read_text())

    report = runner.run_pvo_refresh(
        pvo_artifact_path=pvo,
        coverage_artifact_path=coverage,
        report_path=None,
        refresh_fn=refresh_restamping_the_clock,
        capture_fn=None,
        read_artifact=refresh_fixtures._fixture_reader(pvo, coverage),
        feature_source=refresh_fixtures._fixture_feature_source(),
    )

    assert report["status"] == "ok"
    assert report["pre"]["artifact_sha256"] != report["post"]["artifact_sha256"]
    assert report["pre"]["semantic_output_hash"] == report["post"]["semantic_output_hash"]
    assert report["pre"]["provenance_hash"] == report["post"]["provenance_hash"]
    assert report["semantic_changed"] is False
    assert report["provenance_changed"] is False
