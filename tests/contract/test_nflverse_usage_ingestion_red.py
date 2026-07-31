"""RED contract for nflverse usage ingestion — Next Gen Stats + snap counts (TW30N, layer 1).

Every assertion runs against a REAL nflreadpy capture (2025) and the REAL governed ff_playerids
crosswalk. No synthetic player, no invented id.

Two defects that live data exposed and a synthetic fixture would not have:

1. **`nflreadpy.load_nextgen_stats` defaults `stat_type="passing"`.** The receiving stream was
   declared without the kwarg and silently loaded passing rows under a receiving label. Caught on
   the first live run by the schema guard, and locked here.
2. **The governed crosswalk's PFR bridge is not one-to-one.** Three PFR ids each map to two
   different players. A bridge that picked the first row would attach real snap counts to the
   wrong player.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from src.dynasty_genius.nflverse_usage import (
    CANONICAL_RESOLVED,
    CONFLICT,
    NGS_PASSING,
    NGS_RECEIVING,
    NGS_RUSHING,
    SNAP_COUNTS,
    SOURCE_ONLY,
    UNKNOWN,
    IdentityIndex,
    StreamSpec,
    UsageCaptureError,
    UsageStore,
    normalize_rows,
    run_usage_capture,
    status_marker_path,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "nflverse_usage_2025_slice.json"

#: Measured from the governed crosswalk: one PFR id, two different players.
KNOWN_PFR_CONFLICTS = {"CartKy01", "HarrAl00", "MillSt00"}

#: Measured from the live 2025 snap counts: skill-position players the governed crosswalk
#: does not carry. Small, real, and named rather than folded into a percentage.
UNRESOLVED_SKILL_PFR = {
    "MartAd00",
    "CartNa00",
    "WelcTr00",
    "HortZa00",
    "WhitCo05",
    "JoneJa16",
    "HoliJi00",
}

SPECS = (NGS_PASSING, NGS_RUSHING, NGS_RECEIVING, SNAP_COUNTS)


@pytest.fixture(scope="module")
def fixture_payload() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def identity() -> IdentityIndex:
    return IdentityIndex.from_governed_crosswalk()


@pytest.fixture()
def harness(fixture_payload):
    def fetch(spec: StreamSpec, season: int):
        return fixture_payload[spec.name]

    return fetch


def _run(tmp_path: Path, harness, identity, **overrides) -> dict[str, Any]:
    kwargs = {
        "seasons": [2025],
        "specs": SPECS,
        "identity": identity,
        "db_path": tmp_path / "usage.db",
        "raw_root": tmp_path / "runtime",
        "fetch": harness,
        **overrides,
    }
    return run_usage_capture(**kwargs)


# --------------------------------------------------------------------------
# Premise
# --------------------------------------------------------------------------


def test_fixture_is_a_real_nflverse_capture(fixture_payload) -> None:
    assert fixture_payload["season"] == 2025
    for stream in ("ngs_passing", "ngs_rushing", "ngs_receiving", "snap_counts"):
        assert fixture_payload[stream], f"{stream} slice is empty"
    # Real NGS carries the season-aggregate week 0 alongside real weeks.
    weeks = {int(r["week"]) for r in fixture_payload["ngs_receiving"]}
    assert 0 in weeks and weeks & {1, 2, 3, 4}
    # Real snap counts carry offensive linemen, who are correctly absent from a fantasy crosswalk.
    assert {r["position"] for r in fixture_payload["snap_counts"]} & {"T", "G", "C", "OL", "LS"}


# --------------------------------------------------------------------------
# REGRESSION 1 — the stat_type default
# --------------------------------------------------------------------------


def test_each_ngs_stream_declares_its_stat_type_explicitly() -> None:
    """`load_nextgen_stats` defaults to passing; an omitted kwarg silently mislabels a stream."""
    assert NGS_PASSING.loader_kwargs.get("stat_type") == "passing"
    assert NGS_RUSHING.loader_kwargs.get("stat_type") == "rushing"
    assert NGS_RECEIVING.loader_kwargs.get("stat_type") == "receiving"


def test_receiving_stream_holds_receiving_metrics_not_passing_ones(
    tmp_path, harness, identity
) -> None:
    _run(tmp_path, harness, identity)
    with sqlite3.connect(tmp_path / "usage.db") as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(ngs_receiving)")}
    assert {"avg_separation", "avg_cushion", "avg_yac_above_expectation"} <= cols
    assert "avg_time_to_throw" not in cols, "passing metrics leaked into the receiving stream"


def test_a_stream_whose_columns_are_absent_refuses_by_name(identity, fixture_payload) -> None:
    """The exact failure that caught the stat_type bug on the first live run."""
    wrong_shape = fixture_payload["ngs_passing"]
    with pytest.raises(UsageCaptureError) as exc:
        normalize_rows(wrong_shape, spec=NGS_RECEIVING, season=2025, identity=identity)
    assert "nflverse_schema_drift" in str(exc.value)
    assert "avg_separation" in str(exc.value), "the failure must name the missing columns"


# --------------------------------------------------------------------------
# REGRESSION 2 — the PFR bridge is not one-to-one
# --------------------------------------------------------------------------


def test_the_governed_crosswalk_really_does_contain_pfr_conflicts(identity) -> None:
    """If this stops being true, the conflict handling is merely correct rather than needed."""
    assert set(identity.pfr_conflicts) == KNOWN_PFR_CONFLICTS
    for pfr_id, gsis_ids in identity.pfr_conflicts.items():
        assert len(gsis_ids) > 1, pfr_id


def test_a_conflicting_pfr_id_resolves_to_conflict_never_to_a_player(identity) -> None:
    for pfr_id in KNOWN_PFR_CONFLICTS:
        dg_player_id, status = identity.resolve(pfr_id, kind="pfr")
        assert status == CONFLICT, pfr_id
        assert dg_player_id is None, (
            f"{pfr_id} was resolved to {dg_player_id} despite mapping to two players — "
            "this attaches real snaps to the wrong man"
        )
        assert pfr_id not in identity.pfr_to_gsis, "a conflicting id leaked into the bridge"


def test_conflict_is_distinct_from_unknown(identity) -> None:
    """Both are 'not resolved'; they are not the same problem and must not be merged."""
    _, unknown_status = identity.resolve("NoSuchGuy99", kind="pfr")
    assert unknown_status == SOURCE_ONLY
    _, empty_status = identity.resolve("", kind="pfr")
    assert empty_status == UNKNOWN
    _, conflict_status = identity.resolve(sorted(KNOWN_PFR_CONFLICTS)[0], kind="pfr")
    assert len({unknown_status, empty_status, conflict_status}) == 3


# --------------------------------------------------------------------------
# Identity outcome is never rounded to resolved
# --------------------------------------------------------------------------


def test_coverage_reconciles_and_carries_no_single_reassuring_count(
    tmp_path, harness, identity
) -> None:
    status = _run(tmp_path, harness, identity)
    for block in status["totals"]["by_stream_season"].values():
        assert (
            block["rows_canonical_resolved"] + block["rows_not_canonically_identified"]
            == block["rows_total"]
        )
        assert block["rows_not_canonically_identified"] == (
            block["rows_source_only"] + block["rows_conflict"] + block["rows_unknown"]
        )
        assert "rows_unresolved" not in block, "an ambiguous single count must not appear"


def test_ngs_resolves_canonically_because_gsis_is_our_canonical_id(
    tmp_path, harness, identity
) -> None:
    status = _run(tmp_path, harness, identity)
    for stream in ("ngs_passing", "ngs_rushing", "ngs_receiving"):
        block = status["totals"]["by_stream_season"][f"{stream}:2025"]
        assert block["rows_total"] > 0
        assert block["rows_not_canonically_identified"] == 0, (
            f"{stream} lost identity despite being keyed on gsis: {block}"
        )


def test_unresolved_snap_rows_are_offensive_line_not_hidden_skill_players(
    tmp_path, harness, identity
) -> None:
    """18% of snap rows do not resolve, and that number alone would be alarming or ignorable.

    Broken out, it is almost entirely linemen and long snappers who are correctly absent from a
    fantasy crosswalk — and a small NAMED set of skill players who are a real gap.
    """
    _run(tmp_path, harness, identity)
    with sqlite3.connect(tmp_path / "usage.db") as conn:
        conn.row_factory = sqlite3.Row
        rows = [
            dict(r)
            for r in conn.execute(
                "SELECT position, pfr_player_id, identity_status FROM player_snap_count"
            )
        ]
    unresolved = [r for r in rows if r["identity_status"] != CANONICAL_RESOLVED]
    assert unresolved, "the fixture retains unresolved rows on purpose"
    assert all(r["identity_status"] == SOURCE_ONLY for r in unresolved)

    skill = {r["pfr_player_id"] for r in unresolved if r["position"] in {"QB", "RB", "WR", "TE"}}
    assert skill == UNRESOLVED_SKILL_PFR, (
        "the named skill-position identity gap changed; re-measure before trusting coverage"
    )
    linemen = [r for r in unresolved if r["position"] in {"T", "G", "C", "OL", "LS"}]
    assert len(linemen) > len(skill), "unresolved rows should be dominated by linemen"


def test_totals_name_the_stream_seasons_that_carry_a_gap(tmp_path, harness, identity) -> None:
    status = _run(tmp_path, harness, identity)
    assert status["totals"]["stream_seasons_with_unresolved"] == ["snap_counts:2025"]


def test_the_run_reports_the_conflicts_it_is_holding(tmp_path, harness, identity) -> None:
    status = _run(tmp_path, harness, identity)
    bridge = status["identity_bridge"]
    assert set(bridge["pfr_conflict_ids"]) == KNOWN_PFR_CONFLICTS
    assert bridge["pfr_conflicts_held"] == len(KNOWN_PFR_CONFLICTS)
    assert bridge["gsis_universe"] > 0


# --------------------------------------------------------------------------
# Idempotence by content, and reconciliation
# --------------------------------------------------------------------------


def test_recapturing_identical_content_mutates_nothing(tmp_path, harness, identity) -> None:
    first = _run(tmp_path, harness, identity)
    store = UsageStore(tmp_path / "usage.db", SPECS)
    fingerprint = store.content_fingerprint()
    assert {r["applied"] for r in first["results"]} == {"inserted"}

    second = _run(tmp_path, harness, identity)
    assert {r["applied"] for r in second["results"]} == {"unchanged"}
    assert store.content_fingerprint() == fingerprint, "a no-op re-capture rewrote rows"


def test_a_row_withdrawn_upstream_does_not_survive_as_a_phantom(
    tmp_path, harness, identity, fixture_payload
) -> None:
    _run(tmp_path, harness, identity)
    store = UsageStore(tmp_path / "usage.db", SPECS)
    before = store.row_count("ngs_receiving")

    trimmed = dict(fixture_payload)
    trimmed["ngs_receiving"] = fixture_payload["ngs_receiving"][:-5]

    def fetch(spec: StreamSpec, season: int):
        return trimmed[spec.name]

    second = _run(tmp_path, fetch, identity)
    applied = {f"{r['stream']}": r["applied"] for r in second["results"]}
    assert applied["ngs_receiving"] == "updated"
    assert store.row_count("ngs_receiving") == before - 5


def test_a_store_from_an_earlier_schema_fails_closed_by_name(tmp_path) -> None:
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE ngs_passing (row_key TEXT PRIMARY KEY, season TEXT)")
    with pytest.raises(UsageCaptureError) as exc:
        UsageStore(path, SPECS)
    assert "schema_mismatch" in str(exc.value)


def test_duplicate_rows_at_the_declared_grain_refuse(identity, fixture_payload) -> None:
    """A grain that silently collapses rows is the four-draft-pick defect in another costume."""
    doubled = fixture_payload["ngs_passing"] + fixture_payload["ngs_passing"][:3]
    with pytest.raises(UsageCaptureError) as exc:
        normalize_rows(doubled, spec=NGS_PASSING, season=2025, identity=identity)
    assert "nflverse_grain_violation" in str(exc.value)


# --------------------------------------------------------------------------
# Failure is loud and named
# --------------------------------------------------------------------------


def test_a_failed_stream_does_not_leave_the_previous_success_standing(
    tmp_path, harness, identity
) -> None:
    marker = status_marker_path(tmp_path / "runtime")
    _run(tmp_path, harness, identity)
    assert json.loads(marker.read_text())["status"] == "ok"

    def exploding(spec: StreamSpec, season: int):
        if spec.name == "ngs_rushing":
            raise RuntimeError("nflverse 503")
        return harness(spec, season)

    with pytest.raises(Exception):
        _run(tmp_path, harness, identity, fetch=exploding)

    after = json.loads(marker.read_text())
    assert after["status"] == "failed", "a failed run must not inherit the prior ok"
    assert after["failed_stream"] == "ngs_rushing"
    assert after["failed_season"] == 2025
    assert "nflverse 503" in after["reason"]
    assert [c["stream"] for c in after["captured_before_failure"]] == ["ngs_passing"]


def test_a_failed_stream_season_is_recorded_in_the_store(tmp_path, harness, identity) -> None:
    def exploding(spec: StreamSpec, season: int):
        if spec.name == "ngs_rushing":
            raise RuntimeError("nflverse 503")
        return harness(spec, season)

    with pytest.raises(Exception):
        _run(tmp_path, harness, identity, fetch=exploding)

    captures = {c["stream"]: c for c in UsageStore(tmp_path / "usage.db", SPECS).captures()}
    assert captures["ngs_passing"]["status"] == "ok"
    assert captures["ngs_rushing"]["status"] == "failed"
    assert "nflverse 503" in captures["ngs_rushing"]["failure_reason"]
    assert "ngs_receiving" not in captures, "a stream never reached must not appear as captured"


def test_a_start_record_is_written_before_any_fetch(tmp_path, harness, identity) -> None:
    marker = status_marker_path(tmp_path / "runtime")
    seen: list[dict[str, Any]] = []

    def observing(spec: StreamSpec, season: int):
        seen.append(json.loads(marker.read_text()))
        return harness(spec, season)

    _run(tmp_path, harness, identity, fetch=observing)
    assert seen[0]["status"] == "running"
    assert seen[0]["run_id"]


def test_the_raw_snapshot_is_written_before_parsing(tmp_path, harness, identity) -> None:
    """`01` §Source Adapter Rules. Proven by a run that fails IN parsing and still leaves it."""
    def bad_shape(spec: StreamSpec, season: int):
        if spec.name == "ngs_rushing":
            return [{"season": 2025, "week": 1}]  # real key, missing every metric
        return harness(spec, season)

    with pytest.raises(UsageCaptureError):
        _run(tmp_path, harness, identity, fetch=bad_shape)

    snapshots = sorted((tmp_path / "runtime" / "raw").glob("ngs_rushing_2025_*.json"))
    assert snapshots, "the raw payload was lost when parsing failed"
    assert json.loads(snapshots[0].read_text())["rows"] == 1


def test_an_empty_governed_crosswalk_refuses(tmp_path) -> None:
    path = tmp_path / "empty.json"
    path.write_text(json.dumps({"metadata": {}, "entries": []}), encoding="utf-8")
    with pytest.raises(UsageCaptureError) as exc:
        IdentityIndex.from_governed_crosswalk(path)
    assert "governed_crosswalk_empty" in str(exc.value)


# --------------------------------------------------------------------------
# Codex findings (TW30N three-pane review) — each reproduced before being fixed
# --------------------------------------------------------------------------


def test_a_failed_retry_leaves_the_last_successful_capture_untouched(
    tmp_path, harness, identity
) -> None:
    """Codex's finding, and Codex's fix. My first version overwrote the row and wiped
    `content_hash`, so the next good run could not recognise unchanged content and would
    rewrite everything. A row in this table means a real success and nothing else."""
    _run(tmp_path, harness, identity)
    store = UsageStore(tmp_path / "usage.db", SPECS)
    ok_row = next(c for c in store.captures() if c["stream"] == "ngs_passing")
    assert ok_row["status"] == "ok" and ok_row["content_hash"]

    store.record_failure("ngs_passing", 2025, "nflverse 503", "2026-08-01T00:00:00+00:00")
    after = next(c for c in store.captures() if c["stream"] == "ngs_passing")
    assert after == ok_row, "a failed retry disturbed the last-good row"


def test_a_failure_with_no_prior_success_is_recorded_so_the_season_is_not_absent(
    tmp_path, harness, identity
) -> None:
    """The other half of the invariant: never silently absent, never a lie."""
    store = UsageStore(tmp_path / "usage.db", SPECS)
    store.record_failure("ngs_passing", 2019, "nflverse 503", "2026-08-01T00:00:00+00:00")
    row = next(c for c in store.captures() if c["season"] == "2019")
    assert row["status"] == "failed"
    assert row["failure_reason"] == "nflverse 503"
    assert row["content_hash"] is None


def test_idempotence_survives_a_failed_attempt_in_between(tmp_path, harness, identity) -> None:
    """The consequence the lost hash would have caused, tested end to end."""
    _run(tmp_path, harness, identity)
    store = UsageStore(tmp_path / "usage.db", SPECS)
    fingerprint_before = store.content_fingerprint()

    store.record_failure("ngs_passing", 2025, "nflverse 503", "2026-08-01T00:00:00+00:00")
    recovered = _run(tmp_path, harness, identity)

    applied = {r["stream"]: r["applied"] for r in recovered["results"]}
    assert applied["ngs_passing"] == "unchanged", (
        "a failure in between forced a full rewrite of unchanged content"
    )
    assert store.content_fingerprint() == fingerprint_before


def test_the_run_marker_is_what_reports_the_failing_attempt(tmp_path, harness, identity) -> None:
    """Because the store holds only successes, the marker must name the failure precisely."""
    marker = status_marker_path(tmp_path / "runtime")
    _run(tmp_path, harness, identity)

    def exploding(spec: StreamSpec, season: int):
        if spec.name == "ngs_rushing":
            raise RuntimeError("nflverse 503")
        return harness(spec, season)

    with pytest.raises(Exception):
        _run(tmp_path, harness, identity, fetch=exploding)

    after = json.loads(marker.read_text())
    assert after["status"] == "failed"
    assert after["failed_stream"] == "ngs_rushing"
    assert after["failed_season"] == 2025
    assert "nflverse 503" in after["reason"]
