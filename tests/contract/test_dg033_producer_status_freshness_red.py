"""DG-033 RED — a producer that aborts, or refuses, must not be graded fresh.

The two artifacts this ticket names are NOT symmetric, and treating them as if
they were is how the wrong fix gets shipped.

``pvo_refresh`` writes a terminal ``status`` on every abort path — all five sites
(run_pvo_refresh.py:345, :388, :429, :492, :558) reach a ``_persist`` that writes
the report. The evidence is on disk, freshly, and the gate simply never reads it:
the entry declares no ``status_field``, so ``read_report_artifact_facts`` never
even opens the file (system_health_models.py:694-700) and grading is ``stat()``
alone. Declaring the field is the whole fix. Measured: this has never fired —
``grep -c '"status": "aborted"' app/data/logs/pvo_refresh.out.log`` -> 0 against
126 ``ok`` — so it is insurance on the core_substrate artifact, not a live bug.

``feature_refresh`` is the opposite, and the one that has actually failed. Its
real failure mode writes NO report at all (run_feature_refresh.py:318/:342/:345/
:358 each ``return 1`` before any write, and the noop branch at
feature_refresh_runner.py:107-119 returns without writing). ``status_field``
cannot see a file nobody wrote, and declaring it would assert in config a
guarantee the model's own docstring forbids — "only a producer that writes a
terminal-state status on EVERY exit path may declare it"
(system_health_models.py:78-83).

Its live defect is the CLOCK. ``report_freshness.json`` registered it ``weekly``
while ``com.davidleess.dynasty-feature-refresh.plist`` carries no ``Weekday`` key
and therefore runs DAILY at 09:15. ``_freshness_window_start`` gives weekly a
six-day trailing window (:456-457), so a daily job can write nothing for six days
and still grade ``fresh``. Measured: 2 "refusing to publish" in 57 recorded runs,
both of which wrote nothing.

Correcting the cadence alone would cry wolf, because a healthy ``noop`` also
writes nothing — 4 of the last 20 runs. So the noop branch must stamp the report
it skips. That stamp MERGES: ``feature_refresh`` declares
``input_provenance_field: stream_provenance``, and dropping that block would make
the artifact degrade for an unrelated reason.
"""

from __future__ import annotations

import importlib
import json
import plistlib
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
REPO_ROOT = Path(__file__).resolve().parents[2]

# feature_refresh declares input_provenance_field, so the substance gate runs on
# every fact for it. A block that is absent or unreadable grades inputs_degraded
# (summarize_input_provenance:393-396) and would mask the verdict under test.
_HEALTHY_PROVENANCE = {
    "rosters": {
        "status": "loaded",
        "fallback_used": False,
        "effective_season": 2026,
        "error_type": None,
    }
}


def _models():
    import app.api.routes.system_health_models as models

    return models


def _live_config() -> dict[str, Any]:
    return json.loads((REPO_ROOT / "app/config/report_freshness.json").read_text())


def _entry(artifact_id: str) -> dict[str, Any]:
    for artifact in _live_config()["artifacts"]:
        if artifact["artifact_id"] == artifact_id:
            return artifact
    raise AssertionError(f"{artifact_id} is not registered in report_freshness.json")


def _artifact(models, body: dict[str, Any]):
    return models.ReportArtifactConfig.model_validate(body)


def _config(models, artifacts):
    return models.ReportFreshnessConfig.model_validate(
        {
            "config_version": 2,
            "timezone": "America/New_York",
            "artifacts": artifacts,
        }
    )


def _fact(models, **overrides):
    body = {
        "exists": True,
        "size_bytes": 256,
        "mtime": datetime(2026, 7, 9, 9, 35, tzinfo=NY),
        "embedded_timestamp_value": None,
        "status_value": "ok",
        "failure_reason": None,
    }
    body.update(overrides)
    return models.ReportArtifactFact.model_validate(body)


def _evaluate(models, artifact, fact, now: datetime):
    reports = models.evaluate_report_freshness(
        config=_config(models, [artifact]),
        artifact_facts={artifact.artifact_id: fact},
        now=now,
    )
    assert len(reports) == 1
    return reports[0]


# ── pvo_refresh: the abort it already writes must be read ────────────────────


def test_pvo_refresh_declares_the_status_the_producer_already_writes() -> None:
    """Registration, read from the REAL config — an inline fixture would pass
    forever while the shipped file said nothing."""
    entry = _entry("pvo_refresh")

    assert entry["status_field"] == "status"
    assert entry["success_status"] == "ok"
    # run_pvo_refresh.py:347, :390, :431, :494, :560 all name `aborted_reason`.
    # A wrong key silently degrades to `producer_failure:unreported` (:521-522)
    # and throws away the cause the producer took the trouble to state.
    assert entry["failure_reason_field"] == "aborted_reason"


def test_an_aborted_pvo_refresh_is_graded_producer_failed_not_fresh() -> None:
    """The defect, end to end: a fresh mtime is exactly what failure looks like
    on disk, because the aborting run rewrites its own report."""
    models = _models()
    artifact = _artifact(models, _entry("pvo_refresh"))

    report = _evaluate(
        models,
        artifact,
        _fact(
            models,
            status_value="aborted",
            failure_reason="refresh stage raised",
            mtime=datetime(2026, 7, 9, 9, 31, tzinfo=NY),
        ),
        now=datetime(2026, 7, 9, 10, 0, tzinfo=NY),
    )

    assert report.status == "producer_failed"
    assert report.basis == "producer_failure:refresh stage raised"


def test_an_aborted_core_substrate_run_degrades_the_whole_rollup() -> None:
    models = _models()
    artifact = _artifact(models, _entry("pvo_refresh"))
    report = _evaluate(
        models,
        artifact,
        _fact(models, status_value="aborted", failure_reason="publish stage raised"),
        now=datetime(2026, 7, 9, 10, 0, tzinfo=NY),
    )

    overall, worst_tier = models.rollup_health_status(reports=[report])

    assert overall == "degraded"
    assert worst_tier == "core_substrate"


def test_a_healthy_pvo_refresh_is_still_fresh() -> None:
    """The other half of every gate: it must stay quiet when nothing is wrong."""
    models = _models()
    artifact = _artifact(models, _entry("pvo_refresh"))

    report = _evaluate(
        models,
        artifact,
        _fact(models, status_value="ok", mtime=datetime(2026, 7, 9, 9, 31, tzinfo=NY)),
        now=datetime(2026, 7, 9, 10, 0, tzinfo=NY),
    )

    assert report.status == "fresh"
    assert models.rollup_health_status(reports=[report]) == ("ok", None)


def test_a_pvo_report_with_an_unreadable_status_is_not_treated_as_success() -> None:
    """Fail-closed, matching the DG-034 posture in the sibling capture-health
    file: a declared status field that yields no string is not evidence of health."""
    models = _models()
    artifact = _artifact(models, _entry("pvo_refresh"))

    report = _evaluate(
        models,
        artifact,
        _fact(models, status_value=None),
        now=datetime(2026, 7, 9, 10, 0, tzinfo=NY),
    )

    assert report.status == "corrupt_or_empty"
    assert report.basis == "malformed_status:status"


# ── feature_refresh: the clock, not the status ───────────────────────────────


def test_feature_refresh_cadence_matches_the_schedule_it_actually_runs_on() -> None:
    """The live defect. A weekly registration buys a six-day trailing window
    (_freshness_window_start:456-457); the job runs every morning — since SR-09
    as a step of the daily chain, whose plist now carries the schedule."""
    plist = plistlib.loads(
        (
            REPO_ROOT / "ops/launchd/com.davidleess.dynasty-daily-chain.plist"
        ).read_bytes()
    )
    schedule = plist["StartCalendarInterval"]

    assert "Weekday" not in schedule, "plist changed — re-derive the cadence"
    assert _entry("feature_refresh")["cadence"] == "daily"


def test_every_weekly_artifact_is_weekly_because_its_plist_says_so() -> None:
    """Guards the whole class, not just the one instance DG-033 found.

    roster_capacity and league_opportunity carry Weekday 2 and are correctly
    weekly; feature_refresh carried none and was not. A future edit to either
    side now has to keep them honest.
    """
    plists = {
        "feature_refresh": "com.davidleess.dynasty-daily-chain.plist",
        "roster_capacity": "com.davidleess.dynasty-roster-capacity-audit.plist",
        "league_opportunity": "com.davidleess.dynasty-league-opportunity-map.plist",
    }
    for artifact_id, plist_name in plists.items():
        path = REPO_ROOT / "ops/launchd" / plist_name
        if not path.is_file():
            continue
        schedule = plistlib.loads(path.read_bytes())["StartCalendarInterval"]
        weekday_pinned = "Weekday" in schedule
        cadence = _entry(artifact_id)["cadence"]
        assert (cadence == "weekly") == weekday_pinned, (
            f"{artifact_id}: config says {cadence!r} but its plist "
            f"{'pins a weekday' if weekday_pinned else 'runs daily'}"
        )


def test_a_feature_refresh_that_wrote_nothing_today_goes_stale_within_the_day() -> None:
    """The measured failure: 'refusing to publish' returns 1 before any write,
    so yesterday's report survives untouched. Under the old weekly window this
    graded fresh for up to six days."""
    models = _models()
    artifact = _artifact(models, _entry("feature_refresh"))

    report = _evaluate(
        models,
        artifact,
        _fact(
            models,
            status_value="ok",  # yesterday's success, never overwritten
            embedded_timestamp_value="2026-07-08T09:15:00-04:00",
            mtime=datetime(2026, 7, 8, 9, 15, tzinfo=NY),
            input_provenance=_HEALTHY_PROVENANCE,
        ),
        now=datetime(2026, 7, 9, 13, 0, tzinfo=NY),
    )

    assert report.status == "stale"


def test_a_healthy_feature_refresh_today_is_fresh() -> None:
    models = _models()
    artifact = _artifact(models, _entry("feature_refresh"))

    report = _evaluate(
        models,
        artifact,
        _fact(
            models,
            embedded_timestamp_value="2026-07-09T09:15:00-04:00",
            mtime=datetime(2026, 7, 9, 9, 15, tzinfo=NY),
            input_provenance=_HEALTHY_PROVENANCE,
        ),
        now=datetime(2026, 7, 9, 13, 0, tzinfo=NY),
    )

    assert report.status == "fresh"


def test_a_failed_pvo_run_still_says_when_it_failed() -> None:
    """The producer_failed branch takes observed_at ONLY from an embedded
    timestamp (system_health_models.py:523-524) and never falls back to mtime the
    way the freshness branch does (:558-561). pvo_refresh has no timestamp_field,
    so declaring status_field would make every failure row render "no observable
    timestamp" — David could not tell a run that died 20 minutes ago from one
    that died 20 days ago. The mtime is right there in the fact."""
    models = _models()
    artifact = _artifact(models, _entry("pvo_refresh"))

    report = _evaluate(
        models,
        artifact,
        _fact(
            models,
            status_value="aborted",
            failure_reason="publish stage raised",
            mtime=datetime(2026, 7, 9, 9, 31, tzinfo=NY),
        ),
        now=datetime(2026, 7, 9, 10, 0, tzinfo=NY),
    )

    assert report.status == "producer_failed"
    assert report.observed_at is not None, "a failure with no clock cannot be triaged"
    assert "timestamp_source:mtime_fallback" in report.disclosures


# ── feature_refresh: `blocked` IS a write-on-failure path ────────────────────


def test_feature_refresh_declares_the_one_status_it_does_write_on_failure() -> None:
    """The scoping premise was incomplete. Four exit paths write nothing, but a
    validation-failed publish writes `blocked` to the very file the gate watches
    (feature_publish.py:130 into _REPORT_NAME at :28), and the runner then stamps
    a fresh generated_at over it (feature_refresh_runner.py:168). Declaring the
    status is what catches that.

    `success_status` is the LIST form, the shape realized_outcome already uses:
    `noop` is a healthy terminal state, and it is only safe to enumerate because
    the noop branch now stamps that word into the report.
    """
    entry = _entry("feature_refresh")

    assert entry["status_field"] == "status"
    assert entry["success_status"] == ["ok", "noop"]
    # `candidate_ready` is deliberately absent: run_feature_refresh.py:394 always
    # supplies publish_fn, so the T1 branch that writes it is unreachable from the
    # CLI. Enumerating a value the file cannot carry would be dead config.


def test_a_blocked_publish_is_caught_even_while_inputs_are_degraded() -> None:
    """Why this half matters TODAY. The status gate runs BEFORE the substance gate
    (system_health_models.py:517 then :526), and feature_refresh's live provenance
    is degraded right now — so evaluation short-circuits at `inputs_degraded` and
    never reaches the freshness window. The cadence fix therefore cannot bite
    until the streams go live in September; the status gate bites immediately.
    """
    models = _models()
    artifact = _artifact(models, _entry("feature_refresh"))

    report = _evaluate(
        models,
        artifact,
        _fact(
            models,
            status_value="blocked",
            failure_reason="candidate failed validation",
            embedded_timestamp_value="2026-07-09T09:15:00-04:00",
            mtime=datetime(2026, 7, 9, 9, 15, tzinfo=NY),
            input_provenance={"pbp": {"status": "loaded_empty"}},  # degraded
        ),
        now=datetime(2026, 7, 9, 13, 0, tzinfo=NY),
    )

    assert report.status == "producer_failed"


def test_a_stamped_noop_is_a_success_not_a_failure() -> None:
    """The list form earns its place: without `noop` in success_status, every
    healthy unchanged-source day would now read producer_failed — a far worse
    false alarm than the staleness one the stamp was added to prevent."""
    models = _models()
    artifact = _artifact(models, _entry("feature_refresh"))

    report = _evaluate(
        models,
        artifact,
        _fact(
            models,
            status_value="noop",
            embedded_timestamp_value="2026-07-09T09:15:00-04:00",
            mtime=datetime(2026, 7, 9, 9, 15, tzinfo=NY),
            input_provenance=_HEALTHY_PROVENANCE,
        ),
        now=datetime(2026, 7, 9, 13, 0, tzinfo=NY),
    )

    assert report.status == "fresh"


# ── the noop stamp: a healthy skip must not read as silence ──────────────────


def _runner():
    # The house idiom: tests/contract/test_feature_refresh_runner.py:84 imports it
    # under the `src.` package prefix.
    return importlib.import_module("src.dynasty_genius.features.feature_refresh_runner")


def test_a_noop_run_stamps_the_report_it_skips(tmp_path: Path) -> None:
    """Without this, correcting the cadence turns a healthy unchanged-source day
    into a false alarm — 4 of the last 20 recorded runs were noops."""
    runner = _runner()
    runtime_dir = tmp_path / "features_runtime"
    runtime_dir.mkdir(parents=True)
    report_path = runtime_dir / "feature_refresh_latest_report.json"
    report_path.write_text(
        json.dumps(
            {
                "status": "ok",
                "source_hash": "abc123",
                "generated_at": "2026-07-08T09:15:00+00:00",
                "stream_provenance": {"pbp": {"status": "cached"}},
                "validation": {"rows": 12},
            },
            sort_keys=True,
        )
    )

    result = runner.run_feature_refresh(
        runtime_dir=runtime_dir,
        read_fns={},
        assemble_fn=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("a noop must not assemble")
        ),
        seed_path=tmp_path / "seed.csv",
        source_inputs={"source_hash": "abc123"},
        now_fn=lambda: datetime(2026, 7, 9, 9, 15, tzinfo=NY),
    )

    assert result["status"] == "noop"
    stamped = json.loads(report_path.read_text())
    assert stamped["generated_at"] == "2026-07-09T09:15:00-04:00"
    assert stamped["status"] == "noop"
    # MERGE, not overwrite. feature_refresh declares
    # input_provenance_field: stream_provenance, so dropping it would make the
    # artifact degrade as inputs_degraded for an entirely unrelated reason.
    assert stamped["stream_provenance"] == {"pbp": {"status": "cached"}}
    assert stamped["source_hash"] == "abc123"
    assert stamped["validation"] == {"rows": 12}


def test_a_noop_survives_a_report_it_cannot_stamp(tmp_path: Path) -> None:
    """The stamp is bookkeeping. It must never cancel the run.

    Before DG-033 the noop branch wrote nothing, so it could not fail on a write.
    Adding the stamp introduced a path where a read-only report file turns a
    healthy skip into a PermissionError — and via run_feature_refresh.py's exit
    code, into a reported producer failure. The same rule DG-036 applied to the
    backup sentinel applies here: record what you can, never cancel the work.
    Losing the stamp is already self-punishing — the report goes stale, which is
    exactly the true signal.
    """
    runner = _runner()
    runtime_dir = tmp_path / "features_runtime"
    runtime_dir.mkdir(parents=True)
    report_path = runtime_dir / "feature_refresh_latest_report.json"
    report_path.write_text(
        json.dumps({"status": "ok", "source_hash": "abc123"}, sort_keys=True)
    )
    report_path.chmod(0o400)  # readable, not writable
    try:
        result = runner.run_feature_refresh(
            runtime_dir=runtime_dir,
            seed_path=tmp_path / "seed.csv",
            read_fns={},
            assemble_fn=lambda **_kwargs: (_ for _ in ()).throw(
                AssertionError("a noop must not assemble")
            ),
            source_inputs={"source_hash": "abc123"},
            now_fn=lambda: datetime(2026, 7, 9, 9, 15, tzinfo=NY),
        )
    finally:
        report_path.chmod(0o600)

    assert result["status"] == "noop"


def test_a_stamped_noop_still_lets_the_next_run_noop(tmp_path: Path) -> None:
    """The noop gate reads last_status and refuses to skip after 'blocked'
    (feature_refresh_runner.py:103-107). Stamping 'noop' must not poison that."""
    runner = _runner()
    runtime_dir = tmp_path / "features_runtime"
    runtime_dir.mkdir(parents=True)
    report_path = runtime_dir / "feature_refresh_latest_report.json"
    report_path.write_text(
        json.dumps({"status": "noop", "source_hash": "abc123"}, sort_keys=True)
    )

    result = runner.run_feature_refresh(
        runtime_dir=runtime_dir,
        read_fns={},
        assemble_fn=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("a noop must not assemble")
        ),
        seed_path=tmp_path / "seed.csv",
        source_inputs={"source_hash": "abc123"},
        now_fn=lambda: datetime(2026, 7, 9, 9, 15, tzinfo=NY),
    )

    assert result["status"] == "noop"


def test_a_blocked_prior_state_still_refuses_to_noop(tmp_path: Path) -> None:
    """Regression guard on the noop-poisoning protection the stamp sits beside."""
    runner = _runner()
    runtime_dir = tmp_path / "features_runtime"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "feature_refresh_latest_report.json").write_text(
        json.dumps({"status": "blocked", "source_hash": "abc123"}, sort_keys=True)
    )
    assembled: list[bool] = []

    def _assemble(**_kwargs):
        assembled.append(True)
        raise RuntimeError("stop after proving the skip did not happen")

    try:
        runner.run_feature_refresh(
            runtime_dir=runtime_dir,
            read_fns={},
            assemble_fn=_assemble,
            seed_path=tmp_path / "seed.csv",
            source_inputs={"source_hash": "abc123"},
            now_fn=lambda: datetime(2026, 7, 9, 9, 15, tzinfo=NY),
        )
    except RuntimeError:
        pass

    assert assembled, "a blocked prior state must not be allowed to noop"
