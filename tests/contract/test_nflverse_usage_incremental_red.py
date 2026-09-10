"""DG-215 RED — a late feed must not cost us the feeds that ARE available.

David, 2026-09-10: *"What if snap counts take a longer time to calculate and therefore they won't
reach the 9am... we check if we have the data we ingest what we don't have only and then we
continue. We don't need to fail the pipeline."*

The observed failure, verbatim from `nflverse_usage_status_latest.json` after the 06:15 run:

    ConnectionError: Failed to download https://github.com/nflverse/nflverse-data/releases/
    download/snap_counts/snap_counts_2026.parquet: 404 Client Error: Not Found

Fifteen partitions had already landed. Every stream declared after `snap_counts` never ran, because
the capture re-raises. The existing classifier `_unpublished_season_bound` never saw this: it matches
a `ValueError` whose message reads "Season must be between X and Y", and this is a ConnectionError.

The danger in fixing it is swallowing errors we do not understand, which is how a season goes missing
quietly. So every test below that asserts we CONTINUE is paired with one that asserts we still STOP.
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from src.dynasty_genius.nflverse_usage import (
    NGS_PASSING,
    NGS_RECEIVING,
    NGS_RUSHING,
    SNAP_COUNTS,
    IdentityIndex,
    StreamSpec,
    UsageCaptureError,
    run_usage_capture,
    status_marker_path,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "nflverse_usage_2025_slice.json"

SPECS = (NGS_PASSING, NGS_RUSHING, NGS_RECEIVING, SNAP_COUNTS)

#: The real 404, reproduced exactly. The season appears in the asset filename, which is what makes a
#: narrow classifier possible: the refusal can be shown to be about THIS season's asset rather than
#: about the source being down.
RELEASE_404 = (
    "Failed to download https://github.com/nflverse/nflverse-data/releases/download/"
    "snap_counts/snap_counts_{season}.parquet: 404 Client Error: Not Found for url: "
    "https://github.com/nflverse/nflverse-data/releases/download/snap_counts/"
    "snap_counts_{season}.parquet"
)


@pytest.fixture(scope="module")
def fixture_payload() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def identity() -> IdentityIndex:
    return IdentityIndex.from_governed_crosswalk()


def _late(stream: str, late_season: int, payload):
    """A fetch where one stream-season is not published yet and everything else is healthy."""

    def fetch(spec: StreamSpec, season: int):
        if spec.name == stream and season == late_season:
            raise ConnectionError(RELEASE_404.format(season=season))
        # The HEALTHY streams must return rows labelled for the season being requested. Returning
        # the fixture's 2025 rows for a 2026 request makes them fail the partition-truth guard, so
        # every other partition errors and the test measures the wrong thing entirely.
        rows = payload[spec.name]
        if rows and "season" in rows[0]:
            return [{**row, "season": season} for row in rows]
        return rows

    return fetch


def _release_inventory(present_seasons=(2023, 2024, 2025), tag_ok=True):
    """Stand-in for the release-inventory probe.

    Root's ruling: classification must be EVIDENCE-BASED, not "the text said 404". The real probe
    asks the source whether the release tag exists and which assets it carries. It is injected so
    these tests assert the DECISION RULE without opening a socket; the live probe is rehearsed
    separately against the real source.
    """

    def probe(stream: str, season: int):
        if not tag_ok:
            raise ConnectionError("could not read the release inventory")
        return {
            "tag_exists": True,
            "assets": [f"{stream}_{y}.parquet" for y in present_seasons],
            "expected_asset": f"{stream}_{season}.parquet",
        }

    return probe


def _seasoned(payload, season: int):
    """Rows explicitly relabelled to the season being requested.

    Root: returning unmodified 2025 records for a 2026 request would let a successful response mark
    2026 ready, which is the same error class as stamping a fresh capture time over reused rows.
    Streams with no season column are returned untouched — that axis makes no season claim.
    """

    def fetch(spec: StreamSpec, requested):
        rows = payload[spec.name]
        if rows and "season" in rows[0]:
            return [{**row, "season": season} for row in rows]
        return rows

    return fetch


def _run(tmp_path: Path, fetch, identity, **overrides) -> dict[str, Any]:
    kwargs = {
        "seasons": [2025],
        "specs": SPECS,
        "identity": identity,
        "db_path": tmp_path / "usage.db",
        "raw_root": tmp_path / "runtime",
        "fetch": fetch,
        "release_inventory": _release_inventory(),
        **overrides,
    }
    return run_usage_capture(**kwargs)


def _partitions(status) -> dict[str, dict]:
    return {f"{p['stream']}:{p['season']}": p for p in status.get("partitions", [])}


# ----------------------------------------------------------------------------------------------
# 1. The pipeline continues
# ----------------------------------------------------------------------------------------------


def test_a_late_current_season_release_does_not_fail_the_run(tmp_path, fixture_payload, identity):
    """The whole ticket in one assertion."""
    from src.dynasty_genius.nflverse_usage import current_league_season

    now = current_league_season()
    status = _run(
        tmp_path, _late("snap_counts", now, fixture_payload), identity, seasons=[2025, now]
    )
    assert status["status"] in {"ok", "degraded"}, status.get("reason")
    assert status["status"] != "failed"


def test_streams_declared_after_the_late_one_still_capture(tmp_path, fixture_payload, identity):
    """The 06:15 harm was not the missing partition; it was the fourteen that never ran.

    `snap_counts` is declared LAST in SPECS here, so this drives the same order the live run had:
    the exception must not prevent the other three streams from landing their seasons.
    """
    from src.dynasty_genius.nflverse_usage import current_league_season

    now = current_league_season()
    order = (SNAP_COUNTS, NGS_PASSING, NGS_RUSHING, NGS_RECEIVING)
    status = _run(
        tmp_path,
        _late("snap_counts", now, fixture_payload),
        identity,
        specs=order,
        seasons=[2025, now],
    )
    landed = {(r["stream"], r["season"]) for r in status["results"] if not r.get("skipped")}
    for spec in (NGS_PASSING, NGS_RUSHING, NGS_RECEIVING):
        assert (spec.name, now) in landed, f"{spec.name} never ran after the late stream"


def test_the_waiting_partition_is_named_pending_not_ok(tmp_path, fixture_payload, identity):
    """Missing is waiting, not zero, and never a fresh label over absent data."""
    from src.dynasty_genius.nflverse_usage import current_league_season

    now = current_league_season()
    status = _run(
        tmp_path, _late("snap_counts", now, fixture_payload), identity, seasons=[2025, now]
    )
    part = _partitions(status)[f"snap_counts:{now}"]
    assert part["state"] == "pending"
    assert part["reason"] == "upstream_release_absent"
    assert part.get("rows_stored", 0) == 0
    assert part.get("data_observed_at") is None


# ----------------------------------------------------------------------------------------------
# 2. ...but it still stops for anything it does not understand
# ----------------------------------------------------------------------------------------------


def test_the_same_404_on_a_PAST_season_is_still_fatal(tmp_path, fixture_payload, identity):
    """A past season's asset not being there is not "not published yet"; it is data going missing."""
    from src.dynasty_genius.nflverse_usage import capture_is_healthy

    status = _run(tmp_path, _late("snap_counts", 2024, fixture_payload), identity, seasons=[2024, 2025])
    assert not capture_is_healthy(status)
    part = _partitions(status)["snap_counts:2024"]
    assert part["state"] == "error" and part.get("retryable") is not True


def test_an_unrecognised_error_is_never_waiting_and_never_retryable(tmp_path, fixture_payload, identity):
    """A capture that swallows errors it does not understand is how a season goes missing quietly.

    Note this asserts CONTINUE-BUT-NONZERO rather than raise. David's instruction is not to fail the
    pipeline, and root's contract is that real errors stay visible and nonzero *after* unaffected
    partitions progress. So the unrecognised error must cost us this one partition and nothing else,
    while being impossible to mistake for success and impossible to auto-retry.
    """
    from src.dynasty_genius.nflverse_usage import capture_is_healthy

    def broken(spec: StreamSpec, season: int):
        if spec.name == "snap_counts":
            raise RuntimeError("schema changed: column 'player' disappeared")
        return fixture_payload[spec.name]

    status = _run(tmp_path, broken, identity)
    assert not capture_is_healthy(status)
    part = _partitions(status)["snap_counts:2025"]
    assert part["state"] == "error"
    assert part.get("retryable") is not True
    # the other three streams still landed
    landed = {r["stream"] for r in status["results"] if not r.get("skipped")}
    assert {"ngs_passing", "ngs_rushing", "ngs_receiving"} <= landed


def test_no_path_sets_retryable_from_an_exception_alone(tmp_path, fixture_payload, identity):
    """M6' (reviewer). Retryability comes from a named accepted policy, never from exception text.

    This raises an exception whose message is WORD-FOR-WORD the real release 404 — the most
    persuasive text there is — while the inventory says the asset is present. Evidence beats text.
    """
    from src.dynasty_genius.nflverse_usage import current_league_season

    now = current_league_season()
    status = _run(
        tmp_path, _late("snap_counts", now, fixture_payload), identity, seasons=[now],
        release_inventory=_release_inventory(present_seasons=(2023, 2024, 2025, now)),
    )
    part = _partitions(status)[f"snap_counts:{now}"]
    assert part["state"] == "error", "the exception text alone was enough to claim waiting"
    assert part.get("retryable") is not True


def test_a_real_error_keeps_the_run_nonzero_even_though_others_progressed(
    tmp_path, fixture_payload, identity
):
    """Recoverable partitions continuing must not launder a genuine failure into a green run."""
    from src.dynasty_genius.nflverse_usage import (
        capture_is_healthy,
        current_league_season,
    )

    now = current_league_season()

    def mixed(spec: StreamSpec, season: int):
        if spec.name == "snap_counts" and season == now:
            raise ConnectionError(RELEASE_404.format(season=season))
        if spec.name == "ngs_rushing" and season == 2025:
            raise TimeoutError("the source stopped responding halfway through")
        return fixture_payload[spec.name]

    status = _run(tmp_path, mixed, identity, seasons=[2025, now])
    assert not capture_is_healthy(status), "a real failure was reported as healthy"
    parts = _partitions(status)
    assert parts["ngs_rushing:2025"]["state"] == "error"
    assert parts[f"snap_counts:{now}"]["state"] == "pending"
    # the genuine failure did not cost us the partitions that were fine
    assert parts["ngs_passing:2025"]["state"] in {"ok", "updated", "unchanged"}


# ----------------------------------------------------------------------------------------------
# 3. Never destroy what we already have
# ----------------------------------------------------------------------------------------------


def test_an_empty_feed_never_REACHES_apply_season(tmp_path, fixture_payload, identity, monkeypatch):
    """M1 (reviewer Claude54331). `apply_season` runs
    `DELETE FROM <table> WHERE season_ingested = ?` and re-inserts, so an empty row list erases the
    season outright. The guard therefore has to sit BEFORE apply_season, and this asserts it was not
    CALLED — asserting only that rows survived would keep passing if the guard were moved inside,
    which is one refactor away from losing the protection entirely.
    """
    from src.dynasty_genius.nflverse_usage import UsageStore

    db = tmp_path / "usage.db"
    _run(tmp_path, lambda spec, season: fixture_payload[spec.name], identity, db_path=db)
    before = UsageStore(db, SPECS).row_count(SNAP_COUNTS.table)
    assert before > 0

    calls: list[tuple[str, Any]] = []
    real = UsageStore.apply_season

    def spy(self, spec, *, season, rows, coverage, ingested_at):
        calls.append((spec.name, season))
        return real(self, spec, season=season, rows=rows, coverage=coverage, ingested_at=ingested_at)

    monkeypatch.setattr(UsageStore, "apply_season", spy)

    def empty_snaps(spec: StreamSpec, season: int):
        return [] if spec.name == "snap_counts" else fixture_payload[spec.name]

    try:
        _run(tmp_path, empty_snaps, identity, db_path=db)
    except Exception:
        pass

    assert ("snap_counts", 2025) not in calls, (
        "an empty feed reached apply_season, which deletes the season before re-inserting nothing"
    )
    assert UsageStore(db, SPECS).row_count(SNAP_COUNTS.table) == before


def test_a_pending_partition_does_not_erase_its_previous_observation_time(
    tmp_path, fixture_payload, identity
):
    """If we had 2026 snaps yesterday and the asset 404s today, that is an ERROR, not waiting."""
    from src.dynasty_genius.nflverse_usage import current_league_season

    now = current_league_season()
    db = tmp_path / "usage.db"
    # Seed with rows genuinely labelled for the current season, so the partition really does hold
    # data. Seeding with 2025-labelled rows would be rejected by the partition-truth guard, and the
    # test would then pass for the wrong reason.
    seeded = _run(tmp_path, _seasoned(fixture_payload, now), identity, db_path=db, seasons=[now])
    assert _partitions(seeded)[f"snap_counts:{now}"]["state"] in {"ok", "updated"}

    status = _run(
        tmp_path, _late("snap_counts", now, fixture_payload), identity,
        db_path=db, seasons=[now],
    )
    part = _partitions(status)[f"snap_counts:{now}"]
    assert part["state"] != "pending", (
        "a partition we already hold good rows for was reported as merely waiting"
    )


# ----------------------------------------------------------------------------------------------
# 4. Unchanged content costs nothing; a correction is a new revision
# ----------------------------------------------------------------------------------------------


def test_identical_seasonal_content_reuses_the_raw_revision(tmp_path, fixture_payload, identity):
    """The finished seasons come back byte-identical every morning. Re-normalising and rewriting
    the store to learn nothing is the cost this ticket removes — but the receipt must say a check
    happened, or "unchanged" is indistinguishable from "never looked"."""
    db = tmp_path / "usage.db"
    raw = tmp_path / "runtime"
    fetch = lambda spec, season: fixture_payload[spec.name]  # noqa: E731
    _run(tmp_path, fetch, identity, db_path=db, raw_root=raw)
    second = _run(tmp_path, fetch, identity, db_path=db, raw_root=raw)

    part = _partitions(second)["snap_counts:2025"]
    assert part["state"] == "unchanged"
    assert part.get("checked_at"), "an unchanged partition must still prove it was checked"
    assert part.get("raw_revision_reused") is True


def test_changed_seasonal_content_becomes_a_new_revision(tmp_path, fixture_payload, identity):
    """An upstream correction must be observed, not skipped as 'we already have 2025'."""
    db = tmp_path / "usage.db"
    raw = tmp_path / "runtime"
    _run(tmp_path, lambda s, y: fixture_payload[s.name], identity, db_path=db, raw_root=raw)

    def corrected(spec: StreamSpec, season: int):
        rows = [dict(r) for r in fixture_payload[spec.name]]
        if spec.name == "snap_counts" and rows:
            rows[0] = {**rows[0], "offense_snaps": (rows[0].get("offense_snaps") or 0) + 1}
        return rows

    second = _run(tmp_path, corrected, identity, db_path=db, raw_root=raw)
    part = _partitions(second)["snap_counts:2025"]
    assert part["state"] == "updated"
    assert part.get("raw_revision_reused") is not True


# ----------------------------------------------------------------------------------------------
# 5. The retry-only entrypoint
# ----------------------------------------------------------------------------------------------


def test_the_marker_publishes_a_retry_block_the_guard_can_read(tmp_path, fixture_payload, identity):
    """Contract agreed with DG-216 (Claude54281): capture.retry.v1, aware UTC, due = retryable only."""
    from datetime import datetime

    from src.dynasty_genius.nflverse_usage import current_league_season

    now = current_league_season()
    _run(tmp_path, _late("snap_counts", now, fixture_payload), identity, seasons=[2025, now])
    marker = json.loads(status_marker_path(tmp_path / "runtime").read_text())

    retry = marker["retry"]
    assert retry["schema_version"] == "capture.retry.v1"
    for stamp in (retry["next_retry_at"],):
        assert datetime.fromisoformat(stamp).utcoffset() is not None, "naive stamp"
    due = {d["partition"]: d for d in retry["due"]}
    assert f"snap_counts:{now}" in due
    entry = due[f"snap_counts:{now}"]
    assert entry["retryable"] is True
    assert entry["reason"] == "upstream_release_absent"
    assert entry["attempt"] >= 1 and entry["attempt_id"]


def test_nothing_pending_publishes_no_retry_key(tmp_path, fixture_payload, identity):
    """Absence is nothing due — DG-216 must keep working against today's receipts unchanged."""
    _run(tmp_path, lambda s, y: fixture_payload[s.name], identity)
    marker = json.loads(status_marker_path(tmp_path / "runtime").read_text())
    assert "retry" not in marker or not marker["retry"].get("due")


def test_retry_only_keeps_the_full_partition_truth(tmp_path, fixture_payload, identity):
    """Root's warning: the obvious implementation clobbers the original status with a subset 'ok'."""
    from src.dynasty_genius.nflverse_usage import current_league_season, run_usage_retry

    now = current_league_season()
    db, raw = tmp_path / "usage.db", tmp_path / "runtime"
    first = _run(
        tmp_path, _late("snap_counts", now, fixture_payload), identity,
        db_path=db, raw_root=raw, seasons=[2025, now],
    )
    before = _partitions(first)
    assert len(before) > 1

    later = datetime.now(timezone.utc) + timedelta(hours=1, minutes=1)
    after = run_usage_retry(
        specs=SPECS, identity=identity, db_path=db, raw_root=raw,
        fetch=_seasoned(fixture_payload, now), now_fn=lambda: later,
    )
    got = _partitions(after)
    for key, was in before.items():
        assert key in got, f"retry-only dropped {key} from the receipt"
        if key == f"snap_counts:{now}":
            continue
        # A current-season partition IS legitimately re-checked, so `updated` becoming `unchanged`
        # is the revision check working. What must never happen is a partition that held data coming
        # back as error or pending, or vanishing — that is the subset-"ok" clobber this guards.
        assert got[key]["state"] in {"ok", "updated", "unchanged"}, (
            f"retry-only degraded {key} from {was['state']} to {got[key]['state']}"
        )


def test_retry_only_leaves_an_UNSELECTED_partition_byte_identical(
    tmp_path, fixture_payload, identity
):
    """The strictest form of "the receipt is never narrowed": a partition the run was told not to
    touch must come back exactly as it was, timestamps included."""
    from src.dynasty_genius.nflverse_usage import current_league_season, run_usage_retry

    now = current_league_season()
    db, raw = tmp_path / "usage.db", tmp_path / "runtime"
    first = _run(tmp_path, _late("snap_counts", now, fixture_payload), identity,
                 db_path=db, raw_root=raw, seasons=[2025, now])
    before = _partitions(first)

    later = datetime.now(timezone.utc) + timedelta(hours=1, minutes=1)
    after = _partitions(
        run_usage_retry(specs=SPECS, identity=identity, db_path=db, raw_root=raw,
                        fetch=_seasoned(fixture_payload, now), now_fn=lambda: later,
                        only=[f"snap_counts:{now}"])
    )
    for key, was in before.items():
        if key == f"snap_counts:{now}":
            continue
        assert after[key] == was, f"an unselected partition was rewritten: {key}"


def test_retry_only_does_not_recapture_snapshot_streams(tmp_path, fixture_payload, identity):
    """Snapshot axis accumulates point-in-time on its own schedule; a retry must not add a duplicate."""
    from src.dynasty_genius.nflverse_usage import current_league_season, run_usage_retry

    now = current_league_season()
    db, raw = tmp_path / "usage.db", tmp_path / "runtime"
    _run(
        tmp_path, _late("snap_counts", now, fixture_payload), identity,
        db_path=db, raw_root=raw, seasons=[2025, now],
    )
    touched: list[str] = []

    def watch(spec: StreamSpec, season):
        touched.append(spec.name)
        return fixture_payload[spec.name]

    later = datetime.now(timezone.utc) + timedelta(hours=1, minutes=1)
    run_usage_retry(specs=SPECS, identity=identity, db_path=db, raw_root=raw, fetch=watch,
                    now_fn=lambda: later)
    assert touched, "retry-only fetched nothing at all"
    for spec in SPECS:
        if spec.capture_axis == "snapshot":
            assert spec.name not in touched, f"retry-only recaptured snapshot stream {spec.name}"


def test_a_late_arrival_lands_on_retry(tmp_path, fixture_payload, identity):
    """The point of the whole mechanism: when the asset appears, the partition fills in."""
    from src.dynasty_genius.nflverse_usage import current_league_season, run_usage_retry

    now = current_league_season()
    db, raw = tmp_path / "usage.db", tmp_path / "runtime"
    _run(
        tmp_path, _late("snap_counts", now, fixture_payload), identity,
        db_path=db, raw_root=raw, seasons=[2025, now],
    )
    # An hour later, and not one second before: the partition's own due time governs.
    later = datetime.now(timezone.utc) + timedelta(hours=1, minutes=1)
    after = run_usage_retry(
        specs=SPECS, identity=identity, db_path=db, raw_root=raw,
        fetch=_seasoned(fixture_payload, now), now_fn=lambda: later,
    )
    part = _partitions(after)[f"snap_counts:{now}"]
    assert part["state"] in {"updated", "ok"}
    assert part.get("data_observed_at")


def test_a_retry_before_the_hour_fetches_NOTHING(tmp_path, fixture_payload, identity):
    """Planning happens before fetching: a partition that is not due costs no network call."""
    from src.dynasty_genius.nflverse_usage import current_league_season, run_usage_retry

    now = current_league_season()
    db, raw = tmp_path / "usage.db", tmp_path / "runtime"
    _run(
        tmp_path, _late("snap_counts", now, fixture_payload), identity,
        db_path=db, raw_root=raw, seasons=[2025, now],
    )
    touched: list[str] = []

    def watch(spec: StreamSpec, season):
        touched.append(spec.name)
        return fixture_payload[spec.name]

    soon = datetime.now(timezone.utc) + timedelta(minutes=5)
    run_usage_retry(specs=SPECS, identity=identity, db_path=db, raw_root=raw,
                    fetch=watch, now_fn=lambda: soon)
    assert touched == [], f"a not-due retry still went to the source: {touched}"


def test_a_future_or_malformed_stamp_never_grants_an_immediate_retry(tmp_path, fixture_payload, identity):
    """Independent review of DG-216, finding 3. Clock skew must not become a licence to retry."""
    from src.dynasty_genius.nflverse_usage import partition_is_due

    now = datetime.now(timezone.utc)
    base = {"state": "pending", "retryable": True}
    assert not partition_is_due({**base, "last_attempt_at": (now + timedelta(hours=5)).isoformat()}, now=now)
    assert not partition_is_due({**base, "last_attempt_at": "not-a-timestamp"}, now=now)
    assert not partition_is_due({**base, "last_attempt_at": "2026-09-10T09:00:00"}, now=now)  # naive
    assert partition_is_due({**base, "last_attempt_at": (now - timedelta(hours=2)).isoformat()}, now=now)


# ----------------------------------------------------------------------------------------------
# 6. The lock, which a 15-minute guard will now hammer
# ----------------------------------------------------------------------------------------------


def test_a_killed_capture_does_not_brick_every_later_capture(tmp_path, fixture_payload, identity):
    """`O_EXCL` + unlink-in-finally means SIGKILL leaves the file and every later capture refuses
    FOREVER. Once DG-216 invokes this every 15 minutes that is a permanent wedge, not an annoyance."""
    import os
    import signal
    import subprocess
    import sys
    import textwrap
    import time

    db = tmp_path / "usage.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    holder = textwrap.dedent(f"""
        import sys, time
        sys.path.insert(0, {str(REPO_ROOT)!r})
        from src.dynasty_genius.nflverse_usage import _exclusive_capture_lock
        with _exclusive_capture_lock({str(db)!r}):
            print("HELD", flush=True)
            time.sleep(60)
    """)
    proc = subprocess.Popen([sys.executable, "-c", holder], stdout=subprocess.PIPE, text=True)
    try:
        assert proc.stdout.readline().strip() == "HELD"
        os.kill(proc.pid, signal.SIGKILL)
        proc.wait(timeout=10)
        time.sleep(0.2)
        from src.dynasty_genius.nflverse_usage import _exclusive_capture_lock

        with _exclusive_capture_lock(db):
            pass  # must be acquirable: the previous owner is dead
    finally:
        if proc.poll() is None:
            proc.kill()


def test_two_paths_to_the_same_store_take_the_same_lock(tmp_path, fixture_payload, identity):
    """The docstring says the lock keys on "the canonical DB path", but `Path(db_path)` is not
    resolved, so a symlink alias takes a DIFFERENT lock over the SAME sqlite file."""
    from src.dynasty_genius.nflverse_usage import _exclusive_capture_lock

    real_dir = tmp_path / "real"
    real_dir.mkdir()
    db = real_dir / "usage.db"
    db.write_bytes(b"")
    alias_dir = tmp_path / "alias"
    alias_dir.symlink_to(real_dir)
    alias = alias_dir / "usage.db"

    with _exclusive_capture_lock(db):
        with pytest.raises(UsageCaptureError, match="nflverse_capture_lock_held"):
            with _exclusive_capture_lock(alias):
                pass

    # ...and the same must hold for a symlink on the FINAL COMPONENT. Resolving only the parent
    # canonicalises the directory while following nothing on the file itself, so this alias took a
    # different lock over the same sqlite store.
    file_alias = tmp_path / "usage-link.db"
    file_alias.symlink_to(db)
    with _exclusive_capture_lock(db):
        with pytest.raises(UsageCaptureError, match="nflverse_capture_lock_held"):
            with _exclusive_capture_lock(file_alias):
                pass


def test_an_inventory_probe_failure_is_a_real_error_not_a_wait(tmp_path, fixture_payload, identity):
    """Fail closed. If we cannot get evidence that the asset is merely unpublished, we do not get to
    call it waiting — an auth failure, a rate limit or an outage must stay a real error."""
    from src.dynasty_genius.nflverse_usage import (
        capture_is_healthy,
        current_league_season,
    )

    now = current_league_season()
    status = _run(
        tmp_path, _late("snap_counts", now, fixture_payload), identity,
        seasons=[now], release_inventory=_release_inventory(tag_ok=False),
    )
    assert not capture_is_healthy(status)
    part = _partitions(status)[f"snap_counts:{now}"]
    assert part["state"] == "error" and part.get("retryable") is not True


def test_a_renamed_dataset_is_a_real_error_not_a_wait(tmp_path, fixture_payload, identity):
    """If the historical filename pattern is GONE from the release, the dataset was renamed or
    withdrawn. That is not "this season is late"; it is a source change we must notice."""
    from src.dynasty_genius.nflverse_usage import (
        capture_is_healthy,
        current_league_season,
    )

    now = current_league_season()
    status = _run(
        tmp_path, _late("snap_counts", now, fixture_payload), identity,
        seasons=[now], release_inventory=_release_inventory(present_seasons=()),
    )
    assert not capture_is_healthy(status)
    part = _partitions(status)[f"snap_counts:{now}"]
    assert part["state"] == "error" and part.get("retryable") is not True


# ----------------------------------------------------------------------------------------------
# 7. The same problem one week later: a file that already exists, missing last night's game
# ----------------------------------------------------------------------------------------------


def test_a_late_week_is_found_in_a_file_that_already_exists(tmp_path, fixture_payload, identity):
    """Root's scope correction, and it is David's problem recurring rather than a new feature.

    Waiting-only retries fix the FIRST publication of a season. Once snap_counts_2026.parquet exists
    carrying week 1, an unchanged check would mark the partition ready and clear the queue — so a
    week 2 that lands at 09:30 on a Tuesday is not seen until the next daily run. The three steps
    below are the whole acceptance pair:

      1. week 1 lands and the partition is available;
      2. an hour later the file is byte-identical because week 2 is late — this must cost NOTHING:
         no raw revision, no store rewrite, and no claim of more coverage than we have;
      3. an hour after that week 2 has appeared, and it is ingested.
    """
    from src.dynasty_genius.nflverse_usage import current_league_season, run_usage_retry

    now = current_league_season()
    db, raw = tmp_path / "usage.db", tmp_path / "runtime"
    week1 = [r for r in fixture_payload["snap_counts"] if int(r.get("week") or 0) <= 1]
    assert week1, "fixture carries no week 1 snap rows"

    def feed(rows):
        def fetch(spec: StreamSpec, season):
            source = rows if spec.name == "snap_counts" else fixture_payload[spec.name]
            if source and "season" in source[0]:
                return [{**r, "season": now} for r in source]
            return source
        return fetch

    # 1 — week 1 is in.
    first = _run(tmp_path, feed(week1), identity, db_path=db, raw_root=raw, seasons=[now])
    part = _partitions(first)[f"snap_counts:{now}"]
    assert part["state"] in {"ok", "updated"}
    # ...and being available does NOT mean we stop looking.
    assert part.get("recheck") is True, "a successful current-season partition must stay due"

    raw_files = lambda: sorted(p.name for p in raw.rglob("snap_counts_*.json"))  # noqa: E731
    after_first = raw_files()

    # 2 — an hour later, byte-identical because week 2 has not been published yet.
    hour = datetime.now(timezone.utc) + timedelta(hours=1, minutes=1)
    second = run_usage_retry(specs=SPECS, identity=identity, db_path=db, raw_root=raw,
                             fetch=feed(week1), now_fn=lambda: hour)
    part = _partitions(second)[f"snap_counts:{now}"]
    assert part["state"] == "unchanged"
    assert part.get("raw_revision_reused") is True
    assert raw_files() == after_first, "an unchanged recheck wrote a new raw revision"
    assert part.get("recheck") is True, "it must remain due; week 2 is still coming"

    # 3 — two hours later week 2 has landed, and it is ingested.
    week2 = [r for r in fixture_payload["snap_counts"] if int(r.get("week") or 0) <= 2]
    assert len(week2) > len(week1), "fixture has no week 2 rows to discover"
    later = datetime.now(timezone.utc) + timedelta(hours=2, minutes=2)
    third = run_usage_retry(specs=SPECS, identity=identity, db_path=db, raw_root=raw,
                            fetch=feed(week2), now_fn=lambda: later)
    part = _partitions(third)[f"snap_counts:{now}"]
    assert part["state"] == "updated", "the late week was never ingested"
    assert part["rows_stored"] == len(week2)


def test_an_archive_season_is_never_rechecked_hourly(tmp_path, fixture_payload, identity):
    """Corrections to completed seasons arrive on the ordinary daily run. Hourly rechecks of 2023
    would be pure cost, and the recheck policy is deliberately current-season only."""
    status = _run(tmp_path, lambda s, y: fixture_payload[s.name], identity, seasons=[2025])
    part = _partitions(status)["snap_counts:2025"]
    assert part.get("recheck") is not True
    assert "retry" not in status or not status["retry"]["due"]


def test_a_recheck_entry_never_claims_the_partition_is_missing(tmp_path, fixture_payload, identity):
    """Membership in `due` means "look again", never "there is no data here"."""
    from src.dynasty_genius.nflverse_usage import current_league_season

    now = current_league_season()
    status = _run(tmp_path, _seasoned(fixture_payload, now), identity, seasons=[now])
    due = {d["partition"]: d for d in status["retry"]["due"]}
    entry = due[f"snap_counts:{now}"]
    assert entry["reason"] == "current_season_revision_check"
    assert entry["data_available"] is True
    assert entry["state"] in {"ok", "updated", "unchanged"}


# ----------------------------------------------------------------------------------------------
# 8. A killed run must not take the pending queue with it
# ----------------------------------------------------------------------------------------------


def test_a_killed_capture_leaves_the_pending_queue_readable(tmp_path, fixture_payload, identity):
    """Root's hole, and the lock fix alone does not close it.

    The DB lock now recovers from process death, but that only means a LATER capture can start. If
    the running marker carried partitions and no `retry` block, DG-216 reads a missing `retry` key as
    "nothing due" — so a SIGKILL between discovering that snap_counts is waiting and finishing the
    run would hide the pending queue until the next daily full run. The partition state is
    checkpointed after every partition precisely so that window does not exist.

    This drives a REAL capture in a subprocess and kills it mid-run, rather than hand-writing a
    marker: a hand-written fixture would prove the reader works and say nothing about the writer.
    """
    import json as _json
    import os
    import signal
    import subprocess
    import sys
    import textwrap

    raw = tmp_path / "runtime"
    db = tmp_path / "usage.db"
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(json.dumps(fixture_payload), encoding="utf-8")
    ready = tmp_path / "ready.flag"

    script = textwrap.dedent(f"""
        import json, sys, time
        sys.path.insert(0, {str(REPO_ROOT)!r})
        from src.dynasty_genius.nflverse_usage import (
            run_usage_capture, NGS_PASSING, NGS_RUSHING, NGS_RECEIVING, SNAP_COUNTS,
            current_league_season, IdentityIndex,
        )
        payload = json.load(open({str(payload_path)!r}))
        now = current_league_season()
        order = (SNAP_COUNTS, NGS_PASSING, NGS_RUSHING, NGS_RECEIVING)

        def inventory(stream, season):
            return {{"tag_exists": True,
                     "assets": [f"{{stream}}_{{y}}.parquet" for y in (2023, 2024, 2025)],
                     "expected_asset": f"{{stream}}_{{season}}.parquet"}}

        def fetch(spec, season):
            if spec.name == "snap_counts" and season == now:
                raise ConnectionError(
                    "Failed to download https://github.com/nflverse/nflverse-data/releases/"
                    f"download/snap_counts/snap_counts_{{season}}.parquet: 404 Client Error: "
                    "Not Found"
                )
            if spec.name == "ngs_rushing":
                # The pending partition has been recorded by now. Hang here so the kill lands
                # AFTER the checkpoint and BEFORE the run could finish.
                open({str(ready)!r}, "w").write("now")
                time.sleep(120)
            rows = payload[spec.name]
            if rows and "season" in rows[0]:
                return [{{**r, "season": season}} for r in rows]
            return rows

        run_usage_capture(
            seasons=[now], specs=order, identity=IdentityIndex.from_governed_crosswalk(),
            db_path={str(db)!r}, raw_root={str(raw)!r}, fetch=fetch,
            release_inventory=inventory,
        )
    """)
    proc = subprocess.Popen([sys.executable, "-c", script])
    try:
        for _ in range(600):
            if ready.exists():
                break
            time.sleep(0.1)
        assert ready.exists(), "the capture never reached the hang point"
        os.kill(proc.pid, signal.SIGKILL)
        proc.wait(timeout=15)
    finally:
        if proc.poll() is None:
            proc.kill()

    from src.dynasty_genius.nflverse_usage import (
        current_league_season,
        status_marker_path,
    )

    now = current_league_season()
    marker = _json.loads(status_marker_path(raw).read_text())
    assert marker["status"] == "running", "the killed run should still read as running"

    # The queue survived the kill. Without the per-partition checkpoint this key is simply absent,
    # and DG-216 reads that as nothing to do.
    assert "retry" in marker, "a killed run hid the pending queue until the next daily run"
    due = {d["partition"] for d in marker["retry"]["due"]}
    assert f"snap_counts:{now}" in due
    assert marker["retry"]["schema_version"] == "capture.retry.v1"

    # ...and the lock was released by the kernel, so work can actually resume.
    from src.dynasty_genius.nflverse_usage import (
        _exclusive_capture_lock,
        partition_is_due,
    )

    with _exclusive_capture_lock(db):
        pass

    # Root's condition for DG-216's approval, and the half a surviving queue does NOT give you.
    # The attempt is stamped BEFORE the fetch, so a kill mid-fetch cannot hand the next run a free
    # attempt: the partition that was being fetched carries a fresh last_attempt_at and is not due
    # again until its hour has passed. Without the attempt-start write, the stamp here would be the
    # PREVIOUS attempt's (or absent) and this partition would read as due immediately.
    by_key = {p["partition"]: p for p in marker["partitions"]}
    in_progress = [p for p in marker["partitions"] if p.get("attempt_in_progress")]
    assert in_progress, "the partition being fetched when the kill landed was never stamped"
    killed = in_progress[0]
    # An interruption is not evidence of an error: the partition was never classified, so it is
    # retryable and does not have to wait for tomorrow's daily run.
    assert killed["state"] == "interrupted"
    assert killed["retryable"] is True
    stamped = datetime.fromisoformat(killed["last_attempt_at"])
    assert stamped.utcoffset() is not None, "an aware stamp is the agreed contract"
    assert not partition_is_due(killed, now=stamped + timedelta(minutes=59)), (
        "a run killed mid-fetch granted an immediate extra attempt, skipping the hourly floor"
    )
    assert partition_is_due(killed, now=stamped + timedelta(hours=1, minutes=1))

    # The waiting partition recorded before the kill kept its own stamp and is likewise floored.
    waiting = by_key[f"snap_counts:{now}"]
    waiting_stamp = datetime.fromisoformat(waiting["last_attempt_at"])
    assert not partition_is_due(waiting, now=waiting_stamp + timedelta(minutes=30))


def test_a_failure_after_the_fetch_is_an_error_not_an_interruption(
    tmp_path, fixture_payload, identity
):
    """Root's integration finding: the two must never be confused.

    `interrupted` exists for process death — nothing classified the partition, so retrying is safe.
    But a malformed row is caught AFTER the fetch returns, by `normalize_rows`, which raises past the
    per-partition handler to the outer except. If the start-of-attempt record survived as
    `interrupted`, a deterministic, perfectly reproducible schema error would be retried every hour
    forever. It must settle to a real error instead, and it must not cost the other partitions their
    place in the queue.
    """
    from src.dynasty_genius.nflverse_usage import (
        current_league_season,
        status_marker_path,
    )

    now = current_league_season()
    raw = tmp_path / "runtime"

    def malformed(spec: StreamSpec, season):
        if spec.name == "snap_counts" and season == now:
            raise ConnectionError(RELEASE_404.format(season=season))
        if spec.name == "ngs_rushing":
            # A real response whose rows are the wrong shape entirely.
            return [{"not_a_column": object()} for _ in range(3)]
        rows = fixture_payload[spec.name]
        return [{**r, "season": season} for r in rows] if rows and "season" in rows[0] else rows

    # F2 (reviewer Claude54331): a malformed column must cost its OWN partition and nothing else.
    # It previously propagated to the outer handler and re-raised, so a bad column in an early
    # stream took every later stream with it — the 06:15 harm through a different door, and
    # indistinguishable from it on David's screen.
    from src.dynasty_genius.nflverse_usage import capture_is_healthy

    entered: list[str] = []

    def watched(spec: StreamSpec, season):
        entered.append(spec.name)
        return malformed(spec, season)

    status = _run(tmp_path, watched, identity, seasons=[now],
                  specs=(SNAP_COUNTS, NGS_PASSING, NGS_RUSHING, NGS_RECEIVING))
    assert not capture_is_healthy(status)

    # Measured by ENTRY into the capture, not by reading the marker: the marker merges records
    # carried forward from previous runs, so it is the wrong instrument for "did this stream run".
    assert "ngs_receiving" in entered, (
        f"a malformed column in ngs_rushing cost every later stream its run: entered={entered}"
    )

    marker = json.loads(status_marker_path(raw).read_text())
    parts = {p["partition"]: p for p in marker["partitions"]}

    broken = parts[f"ngs_rushing:{now}"]
    assert broken["state"] == "error", "a schema error was left looking like process death"
    assert broken["retryable"] is False
    assert broken.get("attempt_in_progress") is not True

    due = {d["partition"] for d in (marker.get("retry") or {}).get("due", [])}
    assert f"ngs_rushing:{now}" not in due, "a deterministic parse error was queued for hourly retry"
    # ...and the partition that was genuinely waiting kept its place.
    assert f"snap_counts:{now}" in due, "a real error cost the pending queue its entry"


def test_a_raw_header_never_predates_the_fetch_it_describes(tmp_path, fixture_payload, identity):
    """`captured_at` in a raw envelope is a retrieval time, so it must not be stamped at run start.

    On a run with several slow streams the gap is minutes, and a header that predates its own fetch
    misstates cutoff eligibility while the check receipt beside it says something else entirely.
    """
    import time as _time

    raw = tmp_path / "runtime"
    started: dict[str, str] = {}

    def slow(spec: StreamSpec, season):
        if not started:
            started["at"] = datetime.now(timezone.utc).isoformat()
            _time.sleep(0.05)
        return fixture_payload[spec.name]

    _run(tmp_path, slow, identity, raw_root=raw, seasons=[2025])
    envelopes = sorted(raw.rglob("snap_counts_2025_*.json"))
    assert envelopes, "no raw envelope was written"
    envelope = json.loads(envelopes[0].read_text(encoding="utf-8"))
    captured = datetime.fromisoformat(envelope["captured_at"])
    assert captured >= datetime.fromisoformat(started["at"]), (
        "the raw header is stamped before the fetch that produced it"
    )


# ----------------------------------------------------------------------------------------------
# 9. Four guards that had no test watching them fail
# ----------------------------------------------------------------------------------------------


def test_a_non_404_failure_is_an_error_even_when_the_asset_IS_absent(
    tmp_path, fixture_payload, identity
):
    """The TRIGGER half of the classification, which the evidence half cannot cover.

    An auth failure, a 500 or a PermissionError raised while this season's asset also happens to be
    unpublished would satisfy the inventory proof perfectly — and the proof would be about a
    different question than the one that failed. Both conditions are necessary: a 404 naming this
    partition's declared asset licenses the probe, and only the inventory decides the answer.
    """
    from src.dynasty_genius.nflverse_usage import (
        capture_is_healthy,
        current_league_season,
    )

    now = current_league_season()

    def forbidden(spec: StreamSpec, season):
        if spec.name == "snap_counts" and season == now:
            raise PermissionError("401 Unauthorized: bad credentials")
        rows = fixture_payload[spec.name]
        return [{**r, "season": season} for r in rows] if rows and "season" in rows[0] else rows

    status = _run(tmp_path, forbidden, identity, seasons=[now])
    part = _partitions(status)[f"snap_counts:{now}"]
    assert part["state"] == "error", "a 401 was classified as waiting because the asset was absent"
    assert part.get("retryable") is not True
    assert not capture_is_healthy(status)

    # The sharpest case, and the one that actually exercises the status check: a 500 on the SAME
    # declared canonical URL. Everything about it matches the absence pattern except the status
    # code, and the inventory would still prove the asset absent. Only the trigger separates them.
    def server_error(spec: StreamSpec, season):
        if spec.name == "snap_counts" and season == now:
            raise ConnectionError(
                "Failed to download https://github.com/nflverse/nflverse-data/releases/download/"
                f"snap_counts/snap_counts_{season}.parquet: 500 Server Error: Internal Server Error"
            )
        rows = fixture_payload[spec.name]
        return [{**r, "season": season} for r in rows] if rows and "season" in rows[0] else rows

    status = _run(tmp_path / "second", server_error, identity, seasons=[now])
    part = _partitions(status)[f"snap_counts:{now}"]
    assert part["state"] == "error", "a 500 on the declared URL was classified as waiting"
    assert part.get("retryable") is not True


def test_an_early_next_retry_at_cannot_waive_the_hourly_floor(tmp_path):
    """An explicit time may DELAY a partition; it may never bring it forward.

    Otherwise a receipt carrying an early stamp — hand-edited, clock-skewed, or written by a future
    bug — authorises a hot loop against the source at whatever rate the guard ticks.
    """
    from src.dynasty_genius.nflverse_usage import partition_is_due

    now = datetime.now(timezone.utc)
    record = {
        "state": "pending",
        "retryable": True,
        "last_attempt_at": (now - timedelta(minutes=5)).isoformat(),
        "next_retry_at": (now - timedelta(minutes=1)).isoformat(),  # says "due already"
    }
    assert not partition_is_due(record, now=now), "an early next_retry_at waived the hourly floor"
    # ...and a LATER explicit time is still honoured, because delaying is legitimate.
    record["next_retry_at"] = (now + timedelta(hours=6)).isoformat()
    assert not partition_is_due(record, now=now + timedelta(hours=2))


def test_reuse_is_refused_when_the_STORE_disagrees_with_the_receipt(
    tmp_path, fixture_payload, identity
):
    """A matching sidecar is not evidence that the store still holds those rows.

    An emptied or replaced database under a newer receipt would otherwise be skipped as "unchanged",
    and the partition would report data it no longer has. Reuse is bound to the store's own
    transactional content_hash, which already covers projection and coverage.
    """
    import sqlite3

    db, raw = tmp_path / "usage.db", tmp_path / "runtime"
    fetch = lambda s, y: fixture_payload[s.name]  # noqa: E731
    _run(tmp_path, fetch, identity, db_path=db, raw_root=raw)

    # The store moves underneath the receipt: same row count, different content digest.
    with sqlite3.connect(db) as conn:
        conn.execute(
            "UPDATE nflverse_capture SET content_hash = ? WHERE stream = ?",
            ("0" * 64, "snap_counts"),
        )

    second = _run(tmp_path, fetch, identity, db_path=db, raw_root=raw)
    part = _partitions(second)["snap_counts:2025"]
    assert part.get("raw_revision_reused") is not True, (
        "reuse was granted by the sidecar alone while the store disagreed"
    )
    assert part["state"] in {"updated", "unchanged"}


def test_rows_labelled_another_season_are_refused(tmp_path, fixture_payload, identity):
    """A partition may only be marked ready on evidence about THAT partition.

    Returning 2025 rows for a 2026 request is the same error class as stamping a fresh capture time
    over reused rows: the run succeeded, so something must look current. Streams carrying no season
    column are untouched by this — that axis makes no season claim to contradict.
    """
    from src.dynasty_genius.nflverse_usage import (
        capture_is_healthy,
        current_league_season,
    )

    now = current_league_season()
    # Unmodified 2025-labelled rows returned for a current-season request.
    status = _run(tmp_path, lambda s, y: fixture_payload[s.name], identity, seasons=[now])
    part = _partitions(status)[f"snap_counts:{now}"]
    assert part["state"] == "error", "another season's rows were stored as this season's"
    assert not capture_is_healthy(status)
    assert "labelled" in part.get("detail", "")


def test_a_store_failure_stays_fatal(tmp_path, fixture_payload, identity, monkeypatch):
    """The other side of the F2 boundary, asserted so it cannot drift.

    Source-data problems are isolated. A STORE failure is not: it means the database may be in an
    unknown state mid-transaction, and writing further partitions into a store we no longer
    understand is worse than stopping. The boundary is drawn by what kind of problem it is.
    """
    from src.dynasty_genius.nflverse_usage import UsageStore

    def broken_apply(self, spec, *, season, rows, coverage, ingested_at):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(UsageStore, "apply_season", broken_apply)
    with pytest.raises(Exception):
        _run(tmp_path, lambda s, y: fixture_payload[s.name], identity, seasons=[2025])


def test_EVERY_marker_write_carries_the_retry_queue(tmp_path, fixture_payload, identity, monkeypatch):
    """F1 (reviewer Claude54331): the checkpoint was fixed, the FIRST running-marker write was not.

    That write stands during `IdentityIndex.from_governed_crosswalk()` and `UsageStore` construction
    — a real window. A death inside it left status=running with partitions carried forward and no
    `retry` key, which DG-216 reads as nothing due: the same bug this checkpointing removes, through
    a narrower door.

    Asserted over EVERY marker write rather than the first, because "which write is the risky one"
    is exactly the kind of detail that changes when someone reorders this function later.
    """
    import src.dynasty_genius.nflverse_usage as mod
    from src.dynasty_genius.nflverse_usage import (
        current_league_season,
        status_marker_path,
    )

    now = current_league_season()
    db, raw = tmp_path / "usage.db", tmp_path / "runtime"
    late = _late("snap_counts", now, fixture_payload)
    # Seed a marker that legitimately carries a retry block, so a later run has something to lose.
    _run(tmp_path, late, identity, db_path=db, raw_root=raw, seasons=[now])
    assert json.loads(status_marker_path(raw).read_text())["retry"]["due"]

    writes: list[tuple[bool, str]] = []
    original = mod._atomic_write_json

    def spy(path, payload):
        if str(path).endswith("nflverse_usage_status_latest.json"):
            writes.append(("retry" in payload, payload.get("status")))
        return original(path, payload)

    monkeypatch.setattr(mod, "_atomic_write_json", spy)
    _run(tmp_path, late, identity, db_path=db, raw_root=raw, seasons=[now])

    assert writes, "no marker write was observed"
    without = [i for i, (has_retry, _) in enumerate(writes, 1) if not has_retry]
    assert not without, (
        f"marker write(s) {without} of {len(writes)} dropped the retry queue; a crash there hides "
        "the pending partitions until the next daily run"
    )


# ----------------------------------------------------------------------------------------------
# 10. F4 — the three guards that had no test at all
# ----------------------------------------------------------------------------------------------


def test_a_missing_recheck_decision_is_REFUSED(tmp_path, fixture_payload, identity):
    """(A) The guard exists so a future write site cannot silently drop a partition from the queue.

    Reviewer's point stands: a guard with no test is one edit from gone, which is the whole reason A
    was raised. This calls `_partition_record` directly, because the guard has to fire for a write
    site that does not exist yet.
    """
    from src.dynasty_genius.nflverse_usage import (
        UsageCaptureError,
        _partition_record,
        current_league_season,
    )

    now = current_league_season()
    with pytest.raises(UsageCaptureError, match="without a recheck decision"):
        _partition_record(SNAP_COUNTS, now, state="updated", reason=None, prior={},
                          now=datetime.now(timezone.utc))


def test_an_explicit_recheck_opt_out_is_honoured_and_leaves_one_field(tmp_path):
    """(A/B) The opt-out branch was never exercised, and both flags must be popped.

    Two fields for one fact can disagree in a receipt, which is how a reader ends up trusting the
    wrong one.
    """
    from src.dynasty_genius.nflverse_usage import (
        _partition_record,
        current_league_season,
    )

    now = current_league_season()
    record = _partition_record(
        SNAP_COUNTS, now, state="updated", reason=None, prior={},
        now=datetime.now(timezone.utc), recheck_opt_out=True,
    )
    assert record.get("recheck") is not True
    assert "recheckable" not in record
    assert "recheck_opt_out" not in record


def test_an_unreadable_retry_stamp_is_reported_with_a_reason(tmp_path, fixture_payload, identity):
    """(D) A partition that is quietly not due, with nothing saying why, looks exactly like a queue
    that is simply empty. Both the ordinary path and the no-due path must say so."""
    from src.dynasty_genius.nflverse_usage import (
        current_league_season,
        run_usage_retry,
        status_marker_path,
    )

    now = current_league_season()
    db, raw = tmp_path / "usage.db", tmp_path / "runtime"
    _run(tmp_path, _late("snap_counts", now, fixture_payload), identity,
         db_path=db, raw_root=raw, seasons=[now])

    marker_path = status_marker_path(raw)
    marker = json.loads(marker_path.read_text())
    for part in marker["partitions"]:
        if part["partition"] == f"snap_counts:{now}":
            part["last_attempt_at"] = "not-a-timestamp"
    marker_path.write_text(json.dumps(marker), encoding="utf-8")

    # The no-due path: nothing is eligible precisely BECAUSE the stamp cannot be read.
    status = run_usage_retry(specs=SPECS, identity=identity, db_path=db, raw_root=raw,
                             fetch=lambda s, y: fixture_payload[s.name])
    reported = {u["partition"]: u["reason"] for u in status.get("unusable_attempt_stamps", [])}
    assert f"snap_counts:{now}" in reported, (
        "a partition was silently not due with no reason given anywhere in the status"
    )
    assert "unreadable" in reported[f"snap_counts:{now}"]
    # ...and it says the condition clears itself, so nobody reads it as a permanent wedge.
    assert "next ordinary write" in reported[f"snap_counts:{now}"]

    # The TERMINAL path too, not only the no-due one. Here a second partition IS due, so the capture
    # actually runs and writes a full status — which must still report the unreadable stamp beside
    # the work it did, or the reason is visible only on the quietest possible run.
    marker = json.loads(marker_path.read_text())
    for part in marker["partitions"]:
        if part["partition"] == f"snap_counts:{now}":
            part["last_attempt_at"] = "not-a-timestamp"
        else:
            part["last_attempt_at"] = (
                datetime.now(timezone.utc) - timedelta(hours=3)
            ).isoformat()
            part["next_retry_at"] = (
                datetime.now(timezone.utc) - timedelta(hours=2)
            ).isoformat()
    marker_path.write_text(json.dumps(marker), encoding="utf-8")

    status = run_usage_retry(specs=SPECS, identity=identity, db_path=db, raw_root=raw,
                             fetch=_seasoned(fixture_payload, now))
    assert status.get("retry_selected") != [], "nothing ran, so this is still the no-due path"
    reported = {u["partition"]: u["reason"] for u in status.get("unusable_attempt_stamps", [])}
    assert f"snap_counts:{now}" in reported, (
        "a real run reported no reason for a partition whose stamp cannot be read"
    )
    assert json.loads(marker_path.read_text()).get("unusable_attempt_stamps"), (
        "the reason reached the return value but never the marker on disk"
    )


# ----------------------------------------------------------------------------------------------
# 11. The CLI is the real path, and it is the one that was inert
# ----------------------------------------------------------------------------------------------


def test_the_CLI_supplies_a_release_inventory_on_BOTH_paths(monkeypatch, tmp_path):
    """Root's critical finding, and the shape is one worth naming.

    Every test in this file injects `release_inventory`, so every test passed while the CLI — the
    only path that runs in production — passed nothing. The classifier then had no evidence to work
    from, so a real absent `snap_counts_2026.parquet` would be recorded as an error and never reach
    the retry queue. The whole feature was inert exactly where it matters, and a suite of injected
    fixtures could not see it.

    The API default stays None so tests remain offline by construction; the CLI supplies the real
    provider. That split is the point, which is why it is asserted rather than assumed.
    """
    import sys

    import src.dynasty_genius.nflverse_usage as mod

    seen: dict[str, Any] = {}

    def fake_capture(**kwargs):
        seen["full"] = kwargs
        return {"status": "ok", "partitions": [], "totals": {}}

    def fake_retry(**kwargs):
        seen["retry"] = kwargs
        return {"status": "ok", "partitions": []}

    import scripts.run_nflverse_usage_capture as cli

    monkeypatch.setattr(cli, "run_usage_capture", fake_capture)
    monkeypatch.setattr(cli, "run_usage_retry", fake_retry)

    monkeypatch.setattr(sys, "argv", ["prog", "--db-path", str(tmp_path / "u.db")])
    cli.main()
    monkeypatch.setattr(sys, "argv", ["prog", "--retry-only", "--db-path", str(tmp_path / "u.db")])
    cli.main()

    for path in ("full", "retry"):
        provider = seen[path].get("release_inventory")
        assert provider is mod.default_release_inventory, (
            f"the CLI's {path} path passes no release inventory, so a real 404 can never be "
            "classified as waiting and the retry queue stays empty in production"
        )


def test_the_CLI_survives_a_status_with_no_totals(monkeypatch, tmp_path, capsys):
    """A no-due retry, and a marker left by a crashed run, legitimately carry no `totals`.

    Indexing it unconditionally turned "there was nothing to do" into a KeyError — the CLI crashing
    on the quietest possible outcome.
    """
    import sys

    import scripts.run_nflverse_usage_capture as cli

    monkeypatch.setattr(cli, "run_usage_retry", lambda **kw: {"status": "ok", "retry_selected": []})
    monkeypatch.setattr(sys, "argv", ["prog", "--retry-only", "--db-path", str(tmp_path / "u.db")])
    assert cli.main() == 0
    printed = json.loads(capsys.readouterr().out)
    # Absent stays absent: an invented empty totals block would read as a healthy run that
    # captured nothing, which is a different and false claim.
    assert "totals" not in printed


def test_an_interrupted_partition_keeps_the_export_from_claiming_ready(
    tmp_path, fixture_payload, identity
):
    """Root: `ready` excluded error and pending but not `interrupted`.

    A partition left interrupted by a crash, sitting untouched beside a narrower successful retry,
    would otherwise let the export declare itself ready while carrying no data for it at all.
    """
    from src.dynasty_genius.nflverse_usage import (
        current_league_season,
        read_last_good_export,
        run_usage_retry,
        status_marker_path,
    )

    now = current_league_season()
    db, raw = tmp_path / "usage.db", tmp_path / "runtime"
    _run(tmp_path, _seasoned(fixture_payload, now), identity, db_path=db, raw_root=raw,
         seasons=[now])

    # A crash left one partition interrupted, and a later narrower retry never touches it.
    marker_path = status_marker_path(raw)
    marker = json.loads(marker_path.read_text())
    for part in marker["partitions"]:
        if part["partition"] == f"snap_counts:{now}":
            part.update(state="interrupted", reason="attempt_interrupted", retryable=True,
                        attempt_in_progress=True)
        else:
            part["last_attempt_at"] = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
            part["next_retry_at"] = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    marker_path.write_text(json.dumps(marker), encoding="utf-8")

    run_usage_retry(specs=SPECS, identity=identity, db_path=db, raw_root=raw,
                    fetch=_seasoned(fixture_payload, now),
                    only=[f"ngs_passing:{now}"])

    manifest = read_last_good_export(raw / "export")
    assert manifest["ready"] is False, (
        "an untouched interrupted partition let the export declare itself ready"
    )
