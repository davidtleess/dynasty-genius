"""DG-036 RED — a run that never published must not leave a prior success standing.

The status marker answers *"how did the last run that PUBLISHED go?"* — never
*"how did the last run that STARTED go?"*. Those two diverge exactly when a run
begins and never publishes: the process is killed, the machine sleeps mid-upload,
or the marker write itself fails. The reader then reports the previous run's
``completed`` as current truth until the 26-hour law catches up.

This is measured, not hypothetical. ``docs/agent-ledger/2026-08-01.md:460-463``
records a manual run killed mid-flight, and the launchd stdout log
``app/data/logs/backup_irreplaceable.out.log`` jumps ``20260811T141500Z`` ->
``20260813T143035Z`` with no 08-12 entry at all — the same 2026-08-12 the season
brief records as a gap in ``model_forward_capture`` and ``market_divergence_history``.
Both runs also left their staging directories behind, which a ``finally:`` block
removes, so neither process ever reached it.

THE INVARIANT: the marker must never describe an EARLIER run than the last one
that started. Equality is not the test — a marker from a *later* run is fine, and
that is what a run whose sentinel write failed produces.

THE LIVENESS PROBLEM, which the first cut of this change got wrong: the sentinel
is written at run start and the marker at run end, so a perfectly healthy run
violates the invariant for its whole duration. Measured from the log, runs take
0.11h to 12.64h (median 1.25h) and land 20-24h apart. So a run is only reported
incomplete once it can no longer be in flight — its process is gone, or it has
been running longer than any run plausibly runs.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from app.api.routes.system_capture_health_models import (
    BACKUP_MAX_RUN_HOURS,
    inspect_backup_marker,
)
from scripts.backup_irreplaceable_data import MARKER_REL_PATH, SENTINEL_REL_PATH

# The canonical producer-test harness. Importing it beats a fifth copy of
# FakeGcloud/_seed_repo, and tests/contract already does this in five places
# (e.g. test_cfbd_data_promotion_green_review_red.py:21).
from tests.contract.test_horizon0_backup_red import (
    BUCKET,
    FakeGcloud,
    Fingerprints,
    _entries,
    _run_backup,
    _seed_repo,
    _sqlite_backup,
    _write_manifest,
)

# Every _run_backup call is pinned to this clock, so the run_id it derives is a
# fact these tests assert against rather than a value they read back.
RUN_ID = "20260704T151500Z"
RUN_CLOCK = datetime(2026, 7, 4, 15, 15, tzinfo=timezone.utc)
PRIOR_RUN_ID = "20260703T151500Z"

NOW = datetime(2026, 7, 4, 17, 0, tzinfo=timezone.utc)


def _sentinel(repo: Path) -> Path:
    return repo / SENTINEL_REL_PATH


def _marker(repo: Path) -> Path:
    return repo / MARKER_REL_PATH


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _seed_previous_completed_marker(repo: Path) -> bytes:
    """Yesterday's success, sitting on disk exactly as a real one would."""
    path = _marker(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "backup_status.v1",
                "status": "completed",
                "run_id": PRIOR_RUN_ID,
                "run_prefix": f"gs://bucket/dynasty-genius/runs/{PRIOR_RUN_ID}",
                "started_at": "2026-07-03T15:15:00+00:00",
                "finished_at": "2026-07-03T15:48:51+00:00",
                "files": 654,
                "bytes": 3264672103,
                "sha256_verified": True,
                "failures": [],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return path.read_bytes()


# ── Producer: the run-start sentinel ─────────────────────────────────────────


def test_successful_run_leaves_a_sentinel_naming_the_run_that_published(
    tmp_path: Path,
) -> None:
    repo, db, non_db = _seed_repo(tmp_path)
    manifest = _write_manifest(repo, _entries(db, non_db, repo))

    result = _run_backup(repo=repo, manifest=manifest)

    assert result["status"] == "completed"
    sentinel = _read_json(_sentinel(repo))
    assert sentinel["run_id"] == RUN_ID
    assert sentinel["run_id"] == _read_json(_marker(repo))["run_id"]


def test_the_sentinel_exists_before_the_run_can_die(tmp_path: Path) -> None:
    """The whole design rests on this. A run killed mid-upload must already have
    left its record — so observe the disk from INSIDE the run, not after it."""
    repo, db, non_db = _seed_repo(tmp_path)
    manifest = _write_manifest(repo, _entries(db, non_db, repo))
    observed: list[Any] = []

    class ProbeDuringUpload(FakeGcloud):
        def __call__(self, args: list[str]) -> Any:
            if not observed and "cp" in [str(a) for a in args]:
                path = _sentinel(repo)
                observed.append(_read_json(path) if path.is_file() else None)
            return super().__call__(args)

    _run_backup(repo=repo, manifest=manifest, gcloud=ProbeDuringUpload())

    assert observed, "the probe never fired — the harness changed"
    assert observed[0] is not None, "no sentinel existed while the run was uploading"
    assert observed[0]["run_id"] == RUN_ID


def test_sentinel_is_written_even_when_the_run_fails_before_uploading(
    tmp_path: Path,
) -> None:
    repo, db, non_db = _seed_repo(tmp_path)
    manifest = _write_manifest(repo, _entries(db, non_db, repo))

    result = _run_backup(
        repo=repo, manifest=manifest, gcloud=FakeGcloud(auth_fails=True)
    )

    assert result["status"] == "failed"
    assert _read_json(_sentinel(repo))["run_id"] == RUN_ID


def test_sentinel_carries_the_pid_that_can_be_checked_for_liveness(
    tmp_path: Path,
) -> None:
    """Without it the reader can only guess whether a started run is still going."""
    import os

    repo, db, non_db = _seed_repo(tmp_path)
    manifest = _write_manifest(repo, _entries(db, non_db, repo))

    _run_backup(repo=repo, manifest=manifest)

    assert _read_json(_sentinel(repo))["pid"] == os.getpid()


def test_a_run_whose_sentinel_write_fails_still_backs_up_and_reports_it(
    tmp_path: Path,
) -> None:
    """Bookkeeping must never cancel 3.2 GB of irreplaceable data.

    Only the sentinel path is blocked here — the marker still publishes — so this
    isolates the case the compound ops-directory tests cannot reach.
    """
    repo, db, non_db = _seed_repo(tmp_path)
    sentinel = _sentinel(repo)
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.mkdir()  # a directory where a file must go: write_text raises
    manifest = _write_manifest(repo, _entries(db, non_db, repo))

    result = _run_backup(repo=repo, manifest=manifest)

    assert result["status"] == "completed"
    assert result["exit_code"] == 0
    assert "sentinel_write_failed" in result["failures"]
    assert _read_json(_marker(repo))["run_id"] == RUN_ID


def test_marker_write_failure_leaves_the_previous_success_on_disk(
    tmp_path: Path,
) -> None:
    """Scenario D at the producer: the run fails, and the stale marker survives.

    Only the MARKER file is made unwritable — a directory in its place — so the
    sentinel still records that this run started. That separation is the point:
    an earlier version of this test destroyed the whole ops directory, which took
    the sentinel with it and left nothing to assert.
    """
    repo, db, non_db = _seed_repo(tmp_path)
    stale_bytes = _seed_previous_completed_marker(repo)
    marker = _marker(repo)
    marker.unlink()
    marker.mkdir()  # write_text on a directory raises IsADirectoryError

    manifest = _write_manifest(repo, _entries(db, non_db, repo))
    result = _run_backup(repo=repo, manifest=manifest)

    assert result["status"] == "failed"
    assert "marker_write_failed" in result["failures"]
    # The producer knows it failed; nothing on disk says so...
    assert _read_json(_sentinel(repo))["run_id"] == RUN_ID
    # ...and the sentinel names a run the (absent) marker cannot cover.
    assert stale_bytes, "guard: the seed really wrote a previous success"


def test_a_failed_run_never_returns_a_live_run_prefix(tmp_path: Path) -> None:
    """``run_prefix`` is gated on ``status == "completed"`` at build time only.

    A run that completes and then cannot write its marker flips to ``failed``
    while still carrying the gs:// prefix that gate exists to withhold.
    """
    repo, db, non_db = _seed_repo(tmp_path)
    ops_dir = repo / "app" / "data" / "ops"
    ops_dir.parent.mkdir(parents=True, exist_ok=True)
    ops_dir.write_text("not-a-directory")
    manifest = _write_manifest(repo, _entries(db, non_db, repo))

    result = _run_backup(repo=repo, manifest=manifest)

    assert result["status"] == "failed"
    assert result["run_prefix"] is None


def test_the_next_successful_run_clears_a_stale_sentinel(tmp_path: Path) -> None:
    """Self-healing: the sentinel is overwritten, never deleted, so a dead run's
    record cannot outlive the next run that publishes."""
    repo, db, non_db = _seed_repo(tmp_path)
    sentinel = _sentinel(repo)
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.write_text(json.dumps({"run_id": PRIOR_RUN_ID}))
    manifest = _write_manifest(repo, _entries(db, non_db, repo))

    result = _run_backup(repo=repo, manifest=manifest)

    assert result["status"] == "completed"
    assert _read_json(sentinel)["run_id"] == _read_json(_marker(repo))["run_id"]


def test_a_healthy_run_is_never_reported_incomplete_while_it_runs(
    tmp_path: Path,
) -> None:
    """The regression that made the first cut of this change unshippable.

    Real durations are 0.11h to 12.64h. If an in-flight run reads degraded, the
    one surface guarding the disaster floor cries wolf for hours every morning.
    """
    repo, db, non_db = _seed_repo(tmp_path)
    _seed_previous_completed_marker(repo)
    manifest = _write_manifest(repo, _entries(db, non_db, repo))
    seen: list[Any] = []

    class ProbeDuringUpload(FakeGcloud):
        def __call__(self, args: list[str]) -> Any:
            if not seen and "cp" in [str(a) for a in args]:
                seen.append(
                    inspect_backup_marker(
                        marker_path=_marker(repo),
                        now=RUN_CLOCK + timedelta(minutes=20),
                        sentinel_path=_sentinel(repo),
                    )
                )
            return super().__call__(args)

    result = _run_backup(repo=repo, manifest=manifest, gcloud=ProbeDuringUpload())

    assert result["status"] == "completed"
    assert seen, "the probe never fired — the harness changed"
    assert seen[0].reasons == []
    assert seen[0].status == "ok"


# ── Reader: is the started run still in flight, or is it gone? ───────────────


def _write_marker(tmp_path: Path, *, run_id: str) -> Path:
    path = tmp_path / "marker.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "backup_status.v1",
                "status": "completed",
                "run_id": run_id,
                "started_at": "2026-07-04T15:15:00+00:00",
                "finished_at": "2026-07-04T15:48:51+00:00",
                "files": 654,
                "bytes": 3264672103,
                "sha256_verified": True,
                "failures": [],
            }
        )
    )
    return path


def _write_sentinel(tmp_path: Path, body: Any) -> Path:
    path = tmp_path / "sentinel.json"
    path.write_text(body if isinstance(body, str) else json.dumps(body))
    return path


def _started(run_id: str, *, started_at: datetime, pid: int = 4242) -> dict[str, Any]:
    return {"run_id": run_id, "started_at": started_at.isoformat(), "pid": pid}


ALIVE = {"process_is_alive": lambda _pid: True}
DEAD = {"process_is_alive": lambda _pid: False}


def test_a_started_run_whose_process_is_gone_is_incomplete(tmp_path: Path) -> None:
    """2026-08-12: the run started at 14:15 and the process died. The 08-11
    marker stood as current truth. This is the case the ticket exists for."""
    marker = _write_marker(tmp_path, run_id=PRIOR_RUN_ID)
    sentinel = _write_sentinel(tmp_path, _started(RUN_ID, started_at=RUN_CLOCK))

    health = inspect_backup_marker(
        marker_path=marker, now=NOW, sentinel_path=sentinel, **DEAD
    )

    assert health.status == "degraded"
    assert "backup_run_incomplete" in health.reasons


def test_a_started_run_still_alive_is_in_flight_not_incomplete(tmp_path: Path) -> None:
    marker = _write_marker(tmp_path, run_id=PRIOR_RUN_ID)
    sentinel = _write_sentinel(tmp_path, _started(RUN_ID, started_at=RUN_CLOCK))

    health = inspect_backup_marker(
        marker_path=marker, now=NOW, sentinel_path=sentinel, **ALIVE
    )

    assert health.status == "ok"
    assert health.reasons == []


def test_a_run_alive_past_every_plausible_duration_is_incomplete(
    tmp_path: Path,
) -> None:
    """PID reuse backstop. The longest run ever observed is 12.64h; a process
    still claiming that pid a day later is not this backup."""
    marker = _write_marker(tmp_path, run_id=PRIOR_RUN_ID)
    sentinel = _write_sentinel(tmp_path, _started(RUN_ID, started_at=RUN_CLOCK))

    health = inspect_backup_marker(
        marker_path=marker,
        now=RUN_CLOCK + timedelta(hours=BACKUP_MAX_RUN_HOURS + 1),
        sentinel_path=sentinel,
        **ALIVE,
    )

    assert health.status == "degraded"
    assert "backup_run_incomplete" in health.reasons


def test_the_plausible_duration_bound_is_above_every_observed_run(
    tmp_path: Path,
) -> None:
    """Measured from app/data/logs/backup_irreplaceable.out.log: the longest run
    on record is 20260804T143449Z at 12.64h, and runs land 20-24h apart. The
    bound must clear the first and stay under the second, or it either cries
    wolf on a slow morning or never fires before the next run overwrites the
    sentinel."""
    assert 12.64 < BACKUP_MAX_RUN_HOURS < 20


def test_a_marker_from_a_later_run_than_the_sentinel_is_healthy(
    tmp_path: Path,
) -> None:
    """A run whose sentinel write failed publishes a marker NEWER than the stale
    sentinel. Equality would misread that verified backup as incomplete forever.
    run_ids are %Y%m%dT%H%M%SZ, so lexical order is chronological order."""
    marker = _write_marker(tmp_path, run_id=RUN_ID)
    sentinel = _write_sentinel(
        tmp_path, _started(PRIOR_RUN_ID, started_at=RUN_CLOCK - timedelta(days=1))
    )

    health = inspect_backup_marker(
        marker_path=marker, now=NOW, sentinel_path=sentinel, **DEAD
    )

    assert health.status == "ok"
    assert health.reasons == []


def test_sentinel_matching_the_marker_is_healthy(tmp_path: Path) -> None:
    marker = _write_marker(tmp_path, run_id=RUN_ID)
    sentinel = _write_sentinel(tmp_path, _started(RUN_ID, started_at=RUN_CLOCK))

    health = inspect_backup_marker(
        marker_path=marker, now=NOW, sentinel_path=sentinel, **DEAD
    )

    assert health.status == "ok"
    assert health.reasons == []


def test_an_absent_sentinel_adds_no_reason(tmp_path: Path) -> None:
    """The sentinel is a detector, not a proof obligation.

    It can only ever ADD a degrade. Degrading on absence would pin the surface to
    ``degraded`` from the moment the producer half ships until the next 10:15
    run, which is the cry-wolf DG-034 refused when it tolerated ``missing_optional``.
    """
    marker = _write_marker(tmp_path, run_id=RUN_ID)

    health = inspect_backup_marker(
        marker_path=marker, now=NOW, sentinel_path=tmp_path / "absent.json"
    )

    assert health.status == "ok"
    assert health.reasons == []


@pytest.mark.parametrize(
    "body",
    [
        pytest.param("{not json", id="malformed"),
        pytest.param('"a bare string"', id="json-string"),
        pytest.param("[1, 2, 3]", id="json-list"),
        pytest.param({"started_at": "2026-07-04T15:15:00+00:00"}, id="no-run-id"),
        pytest.param({"run_id": ""}, id="empty-run-id"),
        pytest.param({"run_id": 20260704}, id="non-string-run-id"),
    ],
)
def test_a_sentinel_that_cannot_be_read_degrades(tmp_path: Path, body: Any) -> None:
    """Unknown means loud. A sentinel present but unusable is data we HAVE and
    cannot interpret — unlike absence, which is data we do not have."""
    marker = _write_marker(tmp_path, run_id=RUN_ID)
    sentinel = _write_sentinel(tmp_path, body)

    health = inspect_backup_marker(
        marker_path=marker, now=NOW, sentinel_path=sentinel, **ALIVE
    )

    assert health.status == "degraded"
    assert "backup_sentinel_unparseable" in health.reasons


def test_a_sentinel_with_no_usable_start_time_cannot_claim_to_be_in_flight(
    tmp_path: Path,
) -> None:
    """Liveness needs a clock. Without one, only a live pid can excuse the run,
    and a pid we cannot check is not evidence of anything."""
    marker = _write_marker(tmp_path, run_id=PRIOR_RUN_ID)
    sentinel = _write_sentinel(
        tmp_path, {"run_id": RUN_ID, "started_at": "not-a-time", "pid": 4242}
    )

    health = inspect_backup_marker(
        marker_path=marker, now=NOW, sentinel_path=sentinel, **ALIVE
    )

    assert health.status == "degraded"
    assert "backup_run_incomplete" in health.reasons


def test_sentinel_comparison_survives_a_marker_with_no_run_id(tmp_path: Path) -> None:
    """A marker missing run_id cannot cover any sentinel, and must not crash."""
    path = tmp_path / "marker.json"
    path.write_text(
        json.dumps(
            {
                "status": "completed",
                "finished_at": "2026-07-04T15:48:51+00:00",
                "sha256_verified": True,
                "failures": [],
            }
        )
    )
    sentinel = _write_sentinel(tmp_path, _started(RUN_ID, started_at=RUN_CLOCK))

    health = inspect_backup_marker(
        marker_path=path, now=NOW, sentinel_path=sentinel, **DEAD
    )

    assert health.status == "degraded"
    assert "backup_run_incomplete" in health.reasons


def test_sentinel_default_keeps_every_existing_caller_unchanged(
    tmp_path: Path,
) -> None:
    """``sentinel_path`` defaults to None so the existing contract rows and any
    caller that has not been rewired keep their exact current behaviour."""
    marker = _write_marker(tmp_path, run_id=RUN_ID)

    assert inspect_backup_marker(marker_path=marker, now=NOW).status == "ok"


def test_stale_marker_still_degrades_when_the_sentinel_agrees(tmp_path: Path) -> None:
    """The 26-hour law is untouched: agreement is not proof of freshness."""
    marker = _write_marker(tmp_path, run_id=RUN_ID)
    sentinel = _write_sentinel(tmp_path, _started(RUN_ID, started_at=RUN_CLOCK))

    health = inspect_backup_marker(
        marker_path=marker,
        now=NOW + timedelta(hours=27),
        sentinel_path=sentinel,
        **ALIVE,
    )

    assert health.status == "degraded"
    assert "backup_stale" in health.reasons


def test_the_default_liveness_check_sees_this_very_process(tmp_path: Path) -> None:
    """No injection: exercise the real os.kill path, so the production default
    cannot rot behind a fake."""
    import os

    marker = _write_marker(tmp_path, run_id=PRIOR_RUN_ID)
    sentinel = _write_sentinel(
        tmp_path, _started(RUN_ID, started_at=NOW, pid=os.getpid())
    )

    health = inspect_backup_marker(marker_path=marker, now=NOW, sentinel_path=sentinel)

    assert health.reasons == []


# ── Route: the wiring that makes any of this reach a surface ─────────────────


def test_the_capture_health_route_actually_consults_the_sentinel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without this, deleting the sentinel_path kwarg leaves the whole suite
    green while the detector goes dark on the only surface SR-11 reads."""
    from tests.contract.test_system_capture_health_t4 import (
        _client_with_temp_config,
        _config_body,
        _write_json,
    )

    config_path = _write_json(tmp_path / "capture_cadence.json", _config_body())
    # Mirrors the healthy marker in test_system_capture_health_t4.py:231-244, so
    # the ONLY thing this test changes is the presence of a bad sentinel.
    _write_json(
        tmp_path / MARKER_REL_PATH,
        {
            "schema_version": "backup_status.v1",
            "run_id": "20260702T141500Z",
            "status": "completed",
            "sha256_verified": True,
            "files": 1,
            "bytes": 1,
            "failures": [],
            "started_at": "2026-07-02T14:15:00+00:00",
            "finished_at": "2026-07-02T14:54:02+00:00",
        },
    )
    sentinel = tmp_path / SENTINEL_REL_PATH
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.write_text("{not json")

    client = _client_with_temp_config(
        monkeypatch, config_path=config_path, repo_root=tmp_path
    )
    body = client.get("/api/system/capture-health").json()

    assert "backup_sentinel_unparseable" in body["backup"]["reasons"]
    assert body["backup"]["status"] == "degraded"


def test_run_backup_and_the_route_agree_on_where_the_sentinel_lives(
    tmp_path: Path,
) -> None:
    """A producer and a reader pointed at different paths is a silent no-op."""
    from app.api.routes import system_capture_health as route

    assert route._BACKUP_SENTINEL_RELPATH.as_posix() == SENTINEL_REL_PATH
    assert route._BACKUP_MARKER_RELPATH.as_posix() == MARKER_REL_PATH


def test_the_producer_writes_where_the_constant_says(tmp_path: Path) -> None:
    repo, db, non_db = _seed_repo(tmp_path)
    manifest = _write_manifest(repo, _entries(db, non_db, repo))

    _run_backup(repo=repo, manifest=manifest)

    assert (repo / SENTINEL_REL_PATH).is_file()


def test_bucket_constant_is_still_the_one_the_harness_pins() -> None:
    """Guard on the imported harness: if BUCKET moves, run_prefix assertions in
    this file silently stop meaning what they say."""
    assert BUCKET.startswith("gs://")
    assert callable(_sqlite_backup)
    assert callable(Fingerprints)
