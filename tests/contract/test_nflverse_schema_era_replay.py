"""Schema-era replay: drive EVERY archived real shape through the real pipeline.

This closes the ceiling both lanes independently named. A positive control proves
a guard fires for a case someone thought of; a property test explores values
inside a hand-chosen invariant; a mutation tool kills survivors in code that
exists. **None of them can discover a source era the fixtures do not contain.**
2025 swapping `date_modified` for `season_type`, and 2020 typing `season`/`week`
as Float64, were each found only by running against reality.

So this replays the pinned real shapes — captured from archived raw snapshots by
`scripts/build_nflverse_era_fixtures.py` — through the ACTUAL
capture -> normalize -> store -> export path. If nflverse changes shape again, the
fingerprint check fails and names it instead of a downstream column quietly
going NULL.

No network: every row here came out of a snapshot already on disk.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from src.dynasty_genius.nflverse_usage import (
    IdentityIndex,
    UsageCaptureError,
    build_streams,
    normalize_rows,
    run_usage_capture,
)

FIXTURES = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "fixtures"
    / "nflverse_eras"
    / "era_fingerprints.json"
)


def _bundle() -> dict:
    assert FIXTURES.exists(), (
        f"{FIXTURES} is missing — run scripts/build_nflverse_era_fixtures.py"
    )
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


def _spec(stream: str):
    return {spec.name: spec for spec in build_streams()}[stream]


def _identity_for(records) -> IdentityIndex:
    """Resolve whatever identity column the stream actually uses."""
    ids = {
        str(r.get("gsis_id") or r.get("player_gsis_id") or "")
        for r in records
    }
    return IdentityIndex(
        gsis_ids=frozenset(i for i in ids if i),
        pfr_to_gsis={
            str(r.get("pfr_player_id")): str(r.get("pfr_player_id"))
            for r in records
            if r.get("pfr_player_id")
        },
        pfr_conflicts={},
        names_by_gsis={},
    )


def _shapes():
    return [(s["stream"], tuple(s["seasons"]), s) for s in _bundle()["shapes"]]


def test_every_archived_shape_is_pinned():
    """A shape with no fingerprint is a source change nobody measured."""
    bundle = _bundle()
    assert bundle["shapes"], "no shapes pinned"
    for shape in bundle["shapes"]:
        assert shape["fingerprint"], shape["stream"]
        assert shape["fixture_rows"], f"{shape['stream']} has no replay rows"


def test_the_injury_era_boundary_is_pinned_as_two_distinct_shapes():
    """The specific transition that cost this session, recorded as evidence."""
    injuries = [s for s in _bundle()["shapes"] if s["stream"] == "injuries"]
    assert len(injuries) == 2, "the 2025 era swap must be pinned as its own shape"

    by_season = {min(s["seasons"]): s for s in injuries}
    early, late = by_season[min(by_season)], by_season[max(by_season)]

    assert "date_modified" in early["columns"]
    assert "season_type" not in early["columns"]
    assert "season_type" in late["columns"]
    assert "date_modified" not in late["columns"]
    assert len(early["columns"]) == len(late["columns"]) == 16, (
        "two 16-column shapes with one column swapped — not a 16-vs-17 difference"
    )
    # The 2020 Float64 defect, pinned rather than remembered.
    assert "float" in early["dtype_kinds"]["season"]
    assert "int" in early["dtype_kinds"]["season"]


@pytest.mark.parametrize(
    "stream,seasons,shape", _shapes(), ids=lambda v: str(v) if isinstance(v, str) else ""
)
def test_each_archived_shape_replays_end_to_end(stream, seasons, shape, tmp_path):
    """EVERY archived shape through capture -> normalize -> store -> export.

    The first version only NORMALIZED five of six shapes and reserved the real
    store/export path for the two injury eras, while claiming to drive every
    shape through the pipeline (Codex T3). Normalizing is not storing: the
    silently-dropped era column was invisible to normalization and only appeared
    when a query hit a table that had no such column.
    """
    import polars as pl

    spec = _spec(stream)
    records = shape["fixture_rows"]
    season = seasons[0]

    run_usage_capture(
        seasons=[season],
        specs=[spec],
        identity=_identity_for(records),
        db_path=tmp_path / "replay.db",
        raw_root=tmp_path / "raw",
        export_root=tmp_path / "export",
        fetch=lambda s, yr: records,
    )

    conn = sqlite3.connect(tmp_path / "replay.db")
    try:
        stored = conn.execute(f"SELECT COUNT(*) FROM {spec.table}").fetchone()[0]
        keys = conn.execute(
            f"SELECT COUNT(DISTINCT row_key) FROM {spec.table}"
        ).fetchone()[0]
    finally:
        conn.close()

    assert stored == len(records), f"{stream}: rows dropped between normalize and store"
    assert keys == len(records), f"{stream}: row_key collision in the real store"

    exported = sorted((tmp_path / "export").glob(f"**/{spec.name}.parquet"))
    assert exported, f"{stream}: no export produced"
    frame = pl.read_parquet(exported[-1])
    assert frame.height == len(records), f"{stream}: rows lost in export"
    # Compare against what the SPEC declares, not the raw source column set. The
    # NGS specs deliberately project a subset (ngs_passing persists 25 of 29
    # source columns, dropping player_first_name / player_last_name /
    # player_short_name / player_jersey_number). That is selection, not loss —
    # asserting on source columns made this test fail on correct behaviour.
    missing = [c for c in spec.columns if c not in frame.columns]
    assert not missing, f"{stream}: declared columns absent from export: {missing}"
    unexpected = [
        c for c in shape["columns"]
        if c in frame.columns and c not in spec.stored_columns
    ]
    assert not unexpected, f"{stream}: exported an undeclared column: {unexpected}"


def test_injury_eras_replay_end_to_end_through_store_and_export(tmp_path):
    """capture -> normalize -> store -> export, over BOTH real injury eras."""
    import polars as pl

    spec = _spec("injuries")
    shapes = {
        min(s["seasons"]): s
        for s in _bundle()["shapes"]
        if s["stream"] == "injuries"
    }
    early_season, late_season = min(shapes), max(shapes)
    payload = {
        early_season: shapes[early_season]["fixture_rows"],
        late_season: shapes[late_season]["fixture_rows"],
    }
    all_records = payload[early_season] + payload[late_season]

    run_usage_capture(
        seasons=[early_season, late_season],
        specs=[spec],
        identity=_identity_for(all_records),
        db_path=tmp_path / "replay.db",
        raw_root=tmp_path / "raw",
        export_root=tmp_path / "export",
        fetch=lambda s, season: payload[season],
    )

    conn = sqlite3.connect(tmp_path / "replay.db")
    try:
        eras = dict(
            conn.execute(
                f"SELECT source_era, COUNT(*) FROM {spec.table} GROUP BY 1"
            )
        )
        stored = conn.execute(f"SELECT COUNT(*) FROM {spec.table}").fetchone()[0]
    finally:
        conn.close()

    assert stored == len(all_records), "a row was dropped in the real store path"
    assert set(eras) == {"revisioned", "single_observation"}, (
        f"both real eras must survive storage; got {eras}"
    )

    exported = sorted((tmp_path / "export").glob("**/injuries.parquet"))
    assert exported, "no export produced"
    frame = pl.read_parquet(exported[-1])
    assert frame.height == len(all_records)
    # Era-local columns must both survive the projection.
    assert "date_modified" in frame.columns
    assert "season_type" in frame.columns


def test_a_shape_the_contract_has_never_seen_refuses():
    """The point of pinning: an unpinned shape must fail loudly, not silently.

    This is the case a property test and a mutation tool structurally cannot
    reach — it is about data that does not exist in the codebase yet.
    """
    spec = _spec("injuries")
    shape = next(s for s in _bundle()["shapes"] if s["stream"] == "injuries")
    mutated = [dict(r, unseen_provider_column="future") for r in shape["fixture_rows"]]

    with pytest.raises(UsageCaptureError, match="unknown_era|heterogeneous_batch"):
        normalize_rows(
            mutated, spec=spec, season=shape["seasons"][0],
            identity=_identity_for(mutated),
        )


def test_every_pinned_season_has_witness_rows():
    """T4: a dtype variant with no archived rows is metadata, not evidence.

    The 2020-2024 injuries fixture originally carried 2020 rows only, so the
    int variant that appears from 2021 was pinned but never replayed.
    """
    for shape in _bundle()["shapes"]:
        by_season = shape.get("fixture_rows_by_season", {})
        for season in shape["seasons"]:
            assert by_season.get(str(season)), (
                f"{shape['stream']} season {season} is pinned but has no witness rows"
            )


def test_source_snapshots_are_content_hashed():
    """T6: provenance must not rest on a mutable directory name."""
    for shape in _bundle()["shapes"]:
        sources = shape.get("source_snapshots", {})
        assert sources, f"{shape['stream']} has no source provenance"
        for season, files in sources.items():
            for entry in files:
                assert len(entry["sha256"]) == 64, (season, entry["file"])
                assert "/" not in entry["file"], "no paths, only file names"


def test_every_pinned_dtype_variant_has_a_witness_row():
    """R3-T3: a pinned (column, kind) with no archived row is metadata, not evidence.

    Codex measured 64 uncovered variants when witness rows were "first five rows
    of the first snapshot" — while the generator docstring claimed every variant
    was replayable. The generator now builds a deterministic GREEDY cover — complete over every
    observed (column, kind) pair, and deliberately not called minimal.
    """
    def kind(value):
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, int):
            return "int"
        if isinstance(value, float):
            return "float"
        return "str"

    uncovered = []
    for shape in _bundle()["shapes"]:
        for season, profile in shape["dtype_kinds_by_season"].items():
            seen = {
                (column, kind(value))
                for row in shape["fixture_rows_by_season"].get(season, [])
                for column, value in row.items()
            }
            uncovered += [
                (shape["stream"], season, column, k)
                for column, kinds in profile.items()
                for k in kinds
                if (column, k) not in seen
            ]
    assert not uncovered, (
        f"{len(uncovered)} pinned dtype variants have no archived witness row; "
        f"examples {uncovered[:5]}"
    )


# ── Codex R3-T2 addendum: lock the provenance transitions ────────────────────
#
# The --check verdict was corrected twice, and each correction was proven only
# by a hand-run positive control. A manual check proves a behaviour once; these
# prove it every run, offline, without rebuilding from 266 snapshots.
#
# The helpers were also nested inside main() and therefore unreachable — the
# same shape as the preflight's unreachable _verdict (R3-T4). They are module
# level now, and `test_main_routes_through_the_hoisted_verdict` exists so
# hoisting them cannot quietly turn them into dead code that tests pass against
# while main() keeps its own private copy.

import importlib.util
import sys

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build_nflverse_era_fixtures.py"


def _generator():
    spec = importlib.util.spec_from_file_location("era_fixtures", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["era_fixtures"] = module
    spec.loader.exec_module(module)
    return module


GEN = _generator()

_PINNED = {("injuries", "2024", "a.json"): "aa", ("injuries", "2024", "b.json"): "bb"}


def test_an_added_snapshot_passes_because_capturing_is_normal():
    """The transition the FIRST version got wrong: it read as contract drift, so
    --check failed every time anyone ran a capture."""
    live = dict(_PINNED) | {("injuries", "2024", "c.json"): "cc"}
    ok, detail = GEN.provenance_verdict(live, _PINNED)
    assert ok
    assert detail["added"] == [("injuries", "2024", "c.json")]
    assert len(detail["verified"]) == 2


def test_a_removed_snapshot_fails_and_is_never_counted_verified():
    """The transition the SECOND version got wrong: exit 0, and the success line
    reported the absent file among "content-verified" snapshots."""
    live = {k: v for k, v in _PINNED.items() if k[2] != "b.json"}
    ok, detail = GEN.provenance_verdict(live, _PINNED)
    assert not ok, "deleting pinned evidence must not pass"
    assert detail["removed"] == [("injuries", "2024", "b.json")]
    assert ("injuries", "2024", "b.json") not in detail["verified"]
    assert len(detail["verified"]) == 1, "only files actually read may be counted"


def test_tampered_content_fails():
    ok, detail = GEN.provenance_verdict(dict(_PINNED) | {("injuries", "2024", "a.json"): "ZZ"}, _PINNED)
    assert not ok
    assert detail["tampered"] == [("injuries", "2024", "a.json")]


def test_removal_is_not_masked_by_a_simultaneous_addition():
    """A capture that adds files while an old one is deleted must still fail —
    set sizes match, so a count-based check would pass."""
    live = {k: v for k, v in _PINNED.items() if k[2] != "b.json"}
    live[("injuries", "2024", "new.json")] = "nn"
    ok, detail = GEN.provenance_verdict(live, _PINNED)
    assert not ok and detail["removed"] and detail["added"]


def test_main_routes_through_the_hoisted_verdict(monkeypatch):
    """Guard against the helper becoming dead code that only tests exercise."""
    import inspect

    # Strip comments and docstring prose: the first version of this guard matched
    # its own explanatory comment ("NOT len(pinned_sources)") and failed on
    # correct code. A source check that cannot tell code from prose is not a check.
    code = "\n".join(
        line.split("#")[0]
        for line in inspect.getsource(GEN.main).splitlines()
    )
    assert "provenance_verdict(" in code, (
        "main() must call the hoisted verdict, not carry a private copy"
    )
    assert "len(pinned_sources)" not in code, (
        "the verified count must come from files actually matched"
    )


def test_the_metadata_describes_the_algorithm_that_actually_runs():
    """R3-T3: the bundle claimed `rows_per_era_per_season: 5` while real counts
    vary, and called a greedy cover "minimal". Durable metadata that overstates
    is the defect class this whole session kept surfacing."""
    bundle = _bundle()
    assert "rows_per_era_per_season" not in bundle
    assert bundle["witness_selection"] == "deterministic_greedy_column_kind_cover"
    counts = {
        len(rows)
        for shape in bundle["shapes"]
        for rows in shape["fixture_rows_by_season"].values()
    }
    assert len(counts) > 1, (
        "witness counts genuinely vary — a fixed-count field would be false"
    )


# ── Mutation-pilot survivors: two guards the suite did not actually pin ───────
#
# A bounded 12-mutant census over `matches`, `stored_columns` and
# `_projection_fingerprint` (cosmic-ray 8.4.6) returned 10 KILLED / 2 SURVIVED.
# Both survivors were real coverage holes in load-bearing code, and both are
# closed here. This is what the pilot was for.


def test_an_era_refuses_a_TRUNCATED_column_set_not_only_an_additive_one():
    """Survivor: `available == set(self.columns)` mutated to `<=` and SURVIVED.

    For sets `<=` is subset, so the mutant still refuses an ADDITIVE column —
    which is all the B1 positive control ever exercised. Nothing pinned the other
    half of the declared contract, that a MISSING column also refuses.

    SCOPE, corrected by Codex and then measured exhaustively. This is an
    exact-resolver / error-taxonomy gap, NOT silent data loss. Driving all 16
    single-column truncations of the revisioned era through `normalize_rows`
    with `matches` replaced by subset matching yields ZERO acceptances: 15 raise
    `nflverse_heterogeneous_batch` and 1 (`date_modified`, the only deletion that
    leaves a subset of both eras) raises `nflverse_ambiguous_era`. The pipeline
    was already fail-closed for truncation. What the mutant changes is WHICH
    guard refuses and under which name — the resolver calls a subset a known era
    instead of issuing `nflverse_unknown_era`.

    The test still earns its place: `matches` documents EXACT column-set equality
    and that promise deserves a direct lock at the resolver, rather than resting
    on downstream guards that happen to catch the consequence.
    """
    era = next(e for e in _spec("injuries").eras)
    full = set(era.columns)
    assert era.matches(full), "the real era must still match its own column set"

    for dropped in sorted(full):
        truncated = full - {dropped}
        assert not era.matches(truncated), (
            f"a fetch missing {dropped!r} matched era {era.name!r} — a subset is "
            "not an exact column set and must not be classified as a known era"
        )


def test_the_projection_fingerprint_is_pinned_to_a_golden_digest():
    """Survivor: `json.dumps(..., sort_keys=True)` mutated to `False` and SURVIVED.

    The fingerprint folds into capture identity. Without sorted keys the digest
    depends on the order the payload dict literal happens to be written in, so a
    later edit that merely reorders those lines would silently change the identity
    of every capture — with no test noticing. Pinning the digest makes key order
    load-bearing instead of incidental.
    """
    from src.dynasty_genius.nflverse_usage import _projection_fingerprint

    assert _projection_fingerprint(_spec("injuries")) == (
        "cb0d7df32ec14d115161577561f48a33795a5ba2ec15b9a6e71173ae8458285a"
    ), (
        "the injuries projection fingerprint moved — if this was a deliberate "
        "projection change, re-pin it; if not, capture identity just shifted"
    )
