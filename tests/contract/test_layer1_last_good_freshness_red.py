"""RED — a FAILED run must not erase what we know about the last GOOD one.

THE LIVE GAP (2026-08-08). After the nflverse export failed, the canonical aggregate
reported:

    nflverse_usage_capture   failed   last_success_at=null  age_days=null  freshness=unknown

`freshness=unknown` is FALSE. The explicitly configured last-good ready marker still
named the successful 2026-08-05 run, so the store's last good vintage was known the
whole time. The controller threw that away.

WHY IT MATTERS RATHER THAN BEING A COSMETIC FIELD: "the run failed" and "the data is
three days old" are DIFFERENT AXES. A reader who sees `unknown` cannot tell a route that
failed once over fresh data from one that has never succeeded at all — and those demand
different responses. Reporting `unknown` when the answer is on disk is the same class of
defect as reporting a failed marker as `current`: a status field asserting less, or more,
than the evidence supports.

Bounded to reporting. This does NOT authorize a directory scan or any inference from
source names: the prior marker must be named EXPLICITLY on the manifest entry, because a
scan silently changes meaning when a directory is reorganised.
"""
from __future__ import annotations

import importlib
import json

import pytest

MODULE = "src.dynasty_genius.sources.daily_control"

#: A command that genuinely EXISTS on this machine. `/bin/true` does not exist on
#: macOS, so the first draft's entries were refused by preflight and never reached the
#: runner — the test then failed for the FIXTURE's defect, not the code's.
_REAL_COMMAND = "/usr/bin/true"


def _mod():
    try:
        return importlib.import_module(MODULE)
    except ImportError as exc:  # pragma: no cover
        pytest.fail(f"{MODULE} is not implemented: {exc}", pytrace=False)


def _entry(m, primary, last_good):
    return m.ManifestEntry(
        source="nflverse_usage_capture",
        mode="automatic",
        refresh_target="daily",
        connection_method="public_file_release",
        command=(_REAL_COMMAND,),
        destination="app/data/nflverse_usage.db",
        success_marker=str(primary),
        last_good_marker=str(last_good),
        controller_owned=True,
    )


def test_manifest_entry_carries_an_explicit_last_good_marker():
    """The prior-success marker is DECLARED, never discovered.

    A directory scan would find whatever happens to be lying in an export root, and a
    source-name rule breaks the moment a source is renamed.
    """
    import dataclasses

    m = _mod()
    fields = {f.name for f in dataclasses.fields(m.ManifestEntry)}
    assert "last_good_marker" in fields

    entry = {e.source: e for e in m.build_manifest()}["nflverse_usage_capture"]
    # A substring like "ready" would accept any path containing that word. The consumer
    # commit point is one exact file; pin it.
    assert entry.last_good_marker == (
        "app/data/nflverse_usage/export/nflverse_usage.ready.json"
    ), f"expected the exact ready-marker path, got {entry.last_good_marker!r}"


def test_failed_run_still_reports_the_prior_success_time_and_age(tmp_path):
    """The exact live gap: failure and last-good freshness reported TOGETHER."""
    m = _mod()
    primary = tmp_path / "primary.json"
    primary.write_text(json.dumps({"status": "failed", "failed_stage": "export"}))
    last_good = tmp_path / "ready.json"
    last_good.write_text(json.dumps({
        "run_id": "nflverse-usage-20260805T1334216901700000",
        "captured_at": "2026-08-05T13:39:31.564907+00:00",
    }))

    entry = _entry(m, primary, last_good)

    def _runner(e):
        return m.SourceResult(source=e.source, state="failed", failed=True, detail="exit=1")

    result = m.execute(manifest=[entry], report_root=tmp_path, runner=_runner)
    r = result.by_source["nflverse_usage_capture"]

    assert r.failed is True, "the run outcome is still a failure"
    assert r.last_success_at == "2026-08-05T13:39:31.564907+00:00", (
        "the prior success is known from the last-good marker and must be reported"
    )
    assert r.age_days is not None and r.age_days > 0, (
        "an age computed from the prior success, not discarded"
    )
    assert r.freshness in ("due", "current"), (
        f"freshness must reflect the last-good vintage, not `unknown`; got {r.freshness!r}"
    )


def test_run_outcome_and_freshness_are_separate_axes_in_the_report(tmp_path):
    """A reader must be able to tell 'failed but data is recent' from 'never worked'."""
    m = _mod()
    primary = tmp_path / "p.json"
    primary.write_text(json.dumps({"status": "failed"}))
    last_good = tmp_path / "ready.json"
    last_good.write_text(json.dumps({
        "run_id": "nflverse-usage-20260805T1334216901700000",
        "captured_at": "2026-08-05T13:39:31.564907+00:00",
    }))

    def _runner(e):
        return m.SourceResult(source=e.source, state="failed", failed=True)

    m.execute(manifest=[_entry(m, primary, last_good)], report_root=tmp_path, runner=_runner)
    payload = json.loads((tmp_path / m.REPORT_FILENAME).read_text())
    row = payload["by_source"]["nflverse_usage_capture"]

    assert row["failed"] is True
    assert row["last_success_at"] is not None
    assert row["freshness"] != "unknown"


def test_never_succeeded_route_still_reports_unknown(tmp_path):
    """The counter-case: with NO prior success anywhere, `unknown` is the honest answer
    and must not be replaced by an invented one."""
    m = _mod()
    primary = tmp_path / "p.json"
    primary.write_text(json.dumps({"status": "failed"}))
    missing_last_good = tmp_path / "nope.json"

    def _runner(e):
        return m.SourceResult(source=e.source, state="failed", failed=True)

    result = m.execute(
        manifest=[_entry(m, primary, missing_last_good)],
        report_root=tmp_path, runner=_runner,
    )
    r = result.by_source["nflverse_usage_capture"]
    assert r.last_success_at is None
    assert r.freshness == "unknown"


def test_last_good_marker_never_overrides_a_current_primary_success(tmp_path):
    """A successful primary marker is the better evidence and must win."""
    m = _mod()
    primary = tmp_path / "p.json"
    primary.write_text(json.dumps({
        "status": "ok", "finished_at": "2026-08-08T02:00:00+00:00",
    }))
    last_good = tmp_path / "ready.json"
    last_good.write_text(json.dumps({
        "run_id": "nflverse-usage-20260805T1334216901700000",
        "captured_at": "2026-08-05T13:39:31.564907+00:00",
    }))

    entry = _entry(m, primary, last_good)
    assert m.marker_last_success(entry) == "2026-08-08T02:00:00+00:00", (
        "a fresher primary success must not be shadowed by an older last-good marker"
    )


@pytest.mark.parametrize(
    "payload,label",
    [
        ({"captured_at": "2026-08-05T13:39:31.564907+00:00"}, "no run_id"),
        ({"run_id": "", "captured_at": "2026-08-05T13:39:31.564907+00:00"}, "empty run_id"),
        ({"run_id": "some-run"}, "no captured_at"),
        ({"run_id": "some-run", "captured_at": ""}, "empty captured_at"),
    ],
)
def test_incomplete_last_good_marker_does_not_qualify_as_evidence(tmp_path, payload, label):
    """F4 — an arbitrary JSON carrying only `captured_at` must NOT pass as last-good.

    The ready marker's identity is a NONEMPTY `run_id` PLUS `captured_at`. Without both,
    the file is not the consumer commit point and cannot license a freshness claim. This
    stays a cheap syntactic contract — it does not require hashing Parquets during
    controller reporting.
    """
    m = _mod()
    primary = tmp_path / "p.json"
    primary.write_text(json.dumps({"status": "failed"}))
    last_good = tmp_path / "ready.json"
    last_good.write_text(json.dumps(payload))

    def _runner(e):
        return m.SourceResult(source=e.source, state="failed", failed=True)

    result = m.execute(
        manifest=[_entry(m, primary, last_good)], report_root=tmp_path, runner=_runner
    )
    r = result.by_source["nflverse_usage_capture"]
    assert r.last_success_at is None, f"{label}: must not qualify as last-good evidence"
    assert r.freshness == "unknown", f"{label}: freshness must stay unknown"


def test_malformed_last_good_marker_stays_unknown(tmp_path):
    """F4 counter-case: unparseable JSON is not evidence of anything."""
    m = _mod()
    primary = tmp_path / "p.json"
    primary.write_text(json.dumps({"status": "failed"}))
    last_good = tmp_path / "ready.json"
    last_good.write_text("{not json")

    def _runner(e):
        return m.SourceResult(source=e.source, state="failed", failed=True)

    result = m.execute(
        manifest=[_entry(m, primary, last_good)], report_root=tmp_path, runner=_runner
    )
    r = result.by_source["nflverse_usage_capture"]
    assert r.last_success_at is None
    assert r.freshness == "unknown"


@pytest.mark.parametrize("bad", ["not-a-timestamp", "2026-13-45T99:99:99", "   ", "2026-08-32"])
def test_unparseable_declared_timestamp_is_unknown_not_current(tmp_path, bad):
    """FAIL CLOSED. An `ok` marker whose declared time cannot be parsed previously fell
    back to FILE MTIME and reported `current` — asserting more than the evidence
    supports, the same class as reading a failed marker as a success."""
    m = _mod()
    primary = tmp_path / "p.json"
    primary.write_text(json.dumps({"status": "ok", "finished_at": bad}))
    entry = _entry(m, primary, tmp_path / "absent.json")
    assert m.marker_freshness(entry) != "current", (
        f"an unparseable declared timestamp ({bad!r}) must never read as current"
    )
    assert m.marker_age_days(entry) is None
    # The value itself must NOT be serialized. Failing only the age closed still let
    # `last_success_at: "not-a-timestamp"` reach the report beside freshness=unknown.
    assert m.marker_last_success(entry) is None, (
        f"an invalid declared timestamp ({bad!r}) must not be returned as a success"
    )


def test_failed_primary_with_invalid_last_good_reports_no_success(tmp_path):
    """The direct reproduction: BOTH evidence sources unusable.

    A failed primary falls back to the last-good marker; if THAT carries an invalid
    captured_at, there is no success anywhere and the report must say so — not
    serialize the bad literal.
    """
    m = _mod()
    primary = tmp_path / "p.json"
    primary.write_text(json.dumps({"status": "failed"}))
    last_good = tmp_path / "ready.json"
    last_good.write_text(json.dumps({"run_id": "r1", "captured_at": "not-a-timestamp"}))

    entry = _entry(m, primary, last_good)
    assert m.marker_last_success(entry) is None
    assert m.marker_age_days(entry) is None
    assert m.marker_freshness(entry) == "unknown"

    def _runner(e):
        return m.SourceResult(source=e.source, state="failed", failed=True)

    result = m.execute(manifest=[entry], report_root=tmp_path, runner=_runner)
    r = result.by_source["nflverse_usage_capture"]
    assert r.failed is True
    assert r.last_success_at is None
    assert r.freshness == "unknown"

    payload = json.loads((tmp_path / m.REPORT_FILENAME).read_text())
    assert payload["by_source"]["nflverse_usage_capture"]["last_success_at"] is None, (
        "an invalid timestamp must never be serialized into the canonical report"
    )


def test_invalid_primary_falls_through_to_a_valid_last_good(tmp_path):
    """An unparseable primary must not shadow a GOOD last-good marker."""
    m = _mod()
    primary = tmp_path / "p.json"
    primary.write_text(json.dumps({"status": "ok", "finished_at": "not-a-timestamp"}))
    last_good = tmp_path / "ready.json"
    last_good.write_text(json.dumps({
        "run_id": "r1", "captured_at": "2026-08-05T13:39:31.564907+00:00",
    }))
    entry = _entry(m, primary, last_good)
    assert m.marker_last_success(entry) == "2026-08-05T13:39:31.564907+00:00"


def test_absent_completion_key_still_falls_back_to_mtime(tmp_path):
    """The counter-case, so the fix above is not over-applied.

    An EMPTY completion key means the marker declares no semantic time — that is
    ABSENCE, and the approved design falls back to file mtime. An INVALID non-empty
    value is a different thing: it asserts a time that cannot be true. Collapsing the
    two would discard a legitimate signal in the name of fixing a bogus one.
    """
    m = _mod()
    primary = tmp_path / "p.json"
    primary.write_text(json.dumps({"status": "ok", "finished_at": ""}))
    entry = _entry(m, primary, tmp_path / "absent.json")
    assert m.marker_last_success(entry) is not None
    assert m.marker_freshness(entry) == "current"
