"""DG-141 RED: ``provenance_hash`` no longer hashes the league snapshot's capture timestamp.

The vintage is the PAIR ``(semantic_output_hash, provenance_hash)``. Until DG-141 the
lineage subset that feeds ``provenance_hash`` carried ``source_snapshot_captured_at`` — the
microsecond timestamp of the Sleeper league run the PVO was built from — so the hash was
new on every morning the league run re-stamped it, whether or not anything the hash exists
to detect had moved. Measured on the live store 2026-09-03: a new vintage pair on 47 of 47
consecutive capture dates since the daily league run began 2026-07-16 (52 of 69 across the
whole store; the 17 unchanged pairs all predate the daily run). The driver's own docstring
said dates were excluded; the subset hashed one.

David's ruling (Q11, 2026-09-03 06:22 ET): "take the timestamp out". Option (a): the
timestamp leaves the hashed subset, ``semantic_output_hash`` is untouched, no backfill.

These tests pin:
  * the hashed subset carries no ``source_snapshot_captured_at`` key at all;
  * two mornings that read the same models, features and producer — differing only in
    the league snapshot's clock and the artifact's own volatile fields — share one
    ``provenance_hash`` and the second reports ``vintage_changed: false``;
  * the refresh runner's ``provenance_changed`` is likewise false when a refresh only
    re-stamps the snapshot clock (it is the same subset, hashed at both hash sites);
  * a rerun on the SAME snapshot clock whose content changed still reports a new
    vintage — the 2026-09-02 pair, where 208 rows changed content (team labels) and no
    score moved — because the semantic half carries it;
  * the audit-only provenance block still records the timestamp, outside the hash;
  * and the other half, on David's ruling "B" (2026-09-04 08:11 ET): ``lineage``'s
    ``sleeper_snapshot_hash`` leaves the semantic projection too, so two mornings that
    differ only in the league run's Sleeper player-list hash share a vintage and the
    receipt can read quiet. ONLY that field: ``governance_version`` stays inside the hash
    (the provenance subset excludes row lineage, so nothing else would catch a bump), and
    the whole block stays REQUIRED per model-supported row and recorded in
    ``provenance.row_lineage`` — a row missing it still aborts before any write.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.dynasty_genius.capture import model_forward_capture_driver as driver
from src.dynasty_genius.capture.model_forward_capture_driver import (
    capture_model_pvo_snapshot,
)
from src.dynasty_genius.capture.model_forward_capture_store import (
    MODEL_PVO_SOURCE,
    ModelForwardCaptureStore,
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


def test_a_rerun_on_the_same_snapshot_clock_whose_content_changed_still_reports_a_new_vintage(
    tmp_path: Path,
) -> None:
    """The 2026-09-02 counter-example: same snapshot clock, 208 rows changed content
    (team labels), no score moved. The driver keys ``vintage_changed`` on the pair, never
    on the date, so the second capture's day is incidental."""
    base = _artifact_bytes(
        {PVO_PATH: _json_bytes(_pvo_artifact(source_snapshot_captured_at=_MORNING_ONE))}
    )
    rerun_pvo = _pvo_artifact(volatile_suffix="b", source_snapshot_captured_at=_MORNING_ONE)
    rerun_pvo["players"][0]["player"]["team"] = "PHI"
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


def test_two_mornings_that_differ_only_in_the_sleeper_list_hash_share_a_vintage(
    tmp_path: Path,
) -> None:
    """The other half, David's ruling "B" (2026-09-04 08:11 ET). Every PVO row carries
    ``lineage.sleeper_snapshot_hash`` (the league run's ``sleeper_players_hash``), and
    Sleeper renews its player list daily — three different hashes on the 09-01, 09-02 and
    09-03 runs. Hashing it into the content half made ``semantic_output_hash`` new every
    morning too: on 09-02 -> 09-03, swapping only that hash back reconciles 11,581 of
    12,226 rows. Lineage is provenance, not content, so it leaves the projection."""
    base = _artifact_bytes(
        {PVO_PATH: _json_bytes(_pvo_artifact(source_snapshot_captured_at=_MORNING_ONE))}
    )
    next_pvo = _pvo_artifact(
        captured_at="2026-06-24T12:00:00+00:00",
        volatile_suffix="b",
        source_snapshot_captured_at=_MORNING_TWO,
    )
    for row in next_pvo["players"]:
        row["lineage"]["sleeper_snapshot_hash"] = "sleeper-snapshot-v2"
    next_morning = {**base, PVO_PATH: _json_bytes(next_pvo)}

    first = _capture(tmp_path, base, day=24, git_sha="git-sha-a")
    second = _capture(tmp_path, next_morning, day=25, git_sha="git-sha-b")

    assert first["provenance_hash"] == second["provenance_hash"]
    assert first["semantic_output_hash"] == second["semantic_output_hash"]
    assert second["vintage_changed"] is False
    # Still RECORDED per row in the audit block; only the vintage ignores it.
    recorded = {e["player_key"]: e["lineage"] for e in second["provenance"]["row_lineage"]}
    assert recorded["sleeper:9509"]["sleeper_snapshot_hash"] == "sleeper-snapshot-v2"


def test_a_changed_governance_version_still_trips_the_vintage(tmp_path: Path) -> None:
    """David ruled on the Sleeper player-list hash, not on the whole lineage block. The
    block also carries ``governance_version`` — the rule set the rows were produced under —
    and nothing else hashes it: ``resolve_provenance_subset`` excludes row lineage by its
    own docstring. If the whole block left the projection, a governance bump would ship
    with ``vintage_changed: false``, which is the exact failure this ticket exists to end."""
    base = _artifact_bytes(
        {PVO_PATH: _json_bytes(_pvo_artifact(source_snapshot_captured_at=_MORNING_ONE))}
    )
    bumped = _pvo_artifact(
        captured_at="2026-06-24T12:00:00+00:00",
        volatile_suffix="b",
        source_snapshot_captured_at=_MORNING_TWO,
    )
    for row in bumped["players"]:
        row["lineage"]["governance_version"] = "2.0.0"
    next_morning = {**base, PVO_PATH: _json_bytes(bumped)}

    first = _capture(tmp_path, base, day=24, git_sha="git-sha-a")
    second = _capture(tmp_path, next_morning, day=25, git_sha="git-sha-b")

    assert first["provenance_hash"] == second["provenance_hash"]
    assert first["semantic_output_hash"] != second["semantic_output_hash"]
    assert second["vintage_changed"] is True


def test_a_row_whose_lineage_block_is_missing_is_still_refused(tmp_path: Path) -> None:
    """Dropping lineage from the hash must not drop the REQUIREMENT: a model-supported row
    without its snapshot hash still aborts the whole capture before any write (spec §4)."""
    pvo = _pvo_artifact(source_snapshot_captured_at=_MORNING_ONE)
    del pvo["players"][0]["lineage"]["sleeper_snapshot_hash"]
    artifacts = _artifact_bytes({PVO_PATH: _json_bytes(pvo)})

    report = _capture(tmp_path, artifacts, day=24, git_sha="git-sha-a")

    assert report["status"] == "aborted"
    assert "row_lineage_sleeper_snapshot_hash" in report["aborted_reason"]
    store = ModelForwardCaptureStore(tmp_path / "model_forward.db")
    assert store.get_raw_entries("2026-06-24", MODEL_PVO_SOURCE, "any", "any") == []


def test_a_refresh_that_only_brings_a_new_sleeper_list_reports_semantic_unchanged(
    tmp_path: Path,
) -> None:
    runner = refresh_fixtures._load_runner()
    pvo, coverage = refresh_fixtures._write_pair(tmp_path)

    def refresh_with_a_new_sleeper_list(
        *, pvo_artifact_path: Path, coverage_artifact_path: Path
    ) -> None:
        payload = json.loads(pvo_artifact_path.read_text())
        payload["source_snapshot_captured_at"] = _MORNING_TWO
        for row in payload["players"]:
            row["lineage"]["sleeper_snapshot_hash"] = "sleeper-snapshot-v2"
        pvo_artifact_path.write_text(json.dumps(payload, sort_keys=True))
        coverage_artifact_path.write_text(coverage_artifact_path.read_text())

    report = runner.run_pvo_refresh(
        pvo_artifact_path=pvo,
        coverage_artifact_path=coverage,
        report_path=None,
        refresh_fn=refresh_with_a_new_sleeper_list,
        capture_fn=None,
        read_artifact=refresh_fixtures._fixture_reader(pvo, coverage),
        feature_source=refresh_fixtures._fixture_feature_source(),
    )

    assert report["status"] == "ok"
    assert report["semantic_changed"] is False
    assert report["provenance_changed"] is False


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
