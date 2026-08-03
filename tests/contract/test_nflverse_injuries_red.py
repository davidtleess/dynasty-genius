"""RED contract for the nflverse injuries stream.

Every row here encodes something MEASURED against the live source on 2026-08-01
(17,882 rows, 2023-2025), not something assumed. The measurements that shaped
this contract:

  * `gsis_id` is 100% populated (0 null, 0 blank) — unlike PlayerProfiler, the
    identity problem does not exist here.
  * 86 `gsis_id`s carry more than one `full_name` (J.C./JC Latham, Brian Thomas
    /Brian Thomas Jr., Tariq/Riq Woolen). Name VARIANTS, not two humans — so the
    id is the key and the name never is.
  * The only two duplicate-key groups are REVISIONS, not conflicts: Cade Stover
    2024 wk15 HOU went Questionable (03:34 UTC) -> Out (14:17 UTC), differing
    only in `report_status` and `date_modified`. The injury report is revised
    through the week, so `date_modified` belongs in the grain. Collapsing it
    would silently discard the revision history.
  * THREE states exist, and the majority one is the easy one to lose: 8,333 rows
    carry a designation, 9,549 (53%) are on the report with NO designation, and
    a row that is absent entirely is NO INFORMATION — never "healthy".
  * The source has TWO 16-COLUMN SHAPES, not a 16-vs-17 difference. 2015-2024
    carry `date_modified`; 2025 carries `season_type` INSTEAD. One column was
    swapped for another. (Two earlier readings of this were wrong and are
    recorded rather than smoothed: first "66% null", an artifact of polars
    unioning schemas across a multi-season load; then "16 vs 17", corrected by
    Codex against the raw evidence.) Both columns are declared — each in its own
    era — and the table stores the union.
  * `practice_status` carries TWO distinct null tokens: 45 true nulls and 69
    whitespace strings ('\\n    ', a scrape artifact). Silently merging them is
    the PlayerProfiler `NA` defect repeating.

These tests make no network calls.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.dynasty_genius.nflverse_usage import (
    INJURIES,
    SCHEMA_VERSION,
    StreamSpec,
    UsageCaptureError,
    build_streams,
    normalize_rows,
)

SEASON = 2024


class _Identity:
    """Minimal identity index: gsis ids resolve to themselves."""

    def resolve(self, value, *, kind):  # pragma: no cover - shape varies by impl
        return value, "resolved"


def _row(**overrides):
    base = {
        "season": SEASON,
        "game_type": "REG",
        "team": "HOU",
        "week": 15,
        "gsis_id": "00-0039359",
        "position": "TE",
        "full_name": "Cade Stover",
        "first_name": "Cade",
        "last_name": "Stover",
        "report_primary_injury": "Illness",
        "report_secondary_injury": None,
        "report_status": "Out",
        "practice_primary_injury": "Illness",
        "practice_secondary_injury": None,
        "practice_status": "Did Not Participate In Practice",
        "date_modified": "2024-12-15T14:17:06+00:00",
    }
    base.update(overrides)
    return base


# ── The stream must exist and be registered ───────────────────────────────────


def test_injuries_stream_is_registered_in_build_streams():
    """A spec nobody binds is a spec nobody runs."""
    names = {spec.name for spec in build_streams()}
    assert "injuries" in names


def test_injuries_is_keyed_on_the_provider_id_not_the_name():
    """86 ids carry multiple name spellings; keying on name would split a player."""
    assert INJURIES.identity_column == "gsis_id"
    assert "full_name" not in INJURIES.grain
    assert "gsis_id" in INJURIES.grain


# ── Revisions are a time series, not a conflict ───────────────────────────────


def test_date_modified_is_part_of_the_grain():
    """Cade Stover went Questionable -> Out in eleven hours. Both are real."""
    assert "date_modified" in INJURIES.grain


def test_a_revision_is_preserved_not_collapsed():
    """Two designations for one player-week must both survive with distinct keys."""
    earlier = _row(report_status="Questionable", date_modified="2024-12-15T03:34:33+00:00")
    later = _row(report_status="Out", date_modified="2024-12-15T14:17:06+00:00")

    rows, _ = normalize_rows(
        [earlier, later], spec=INJURIES, season=SEASON, identity=_Identity()
    )

    assert len(rows) == 2, "a revision must not be collapsed into one row"
    assert len({r["row_key"] for r in rows}) == 2, (
        "the two revisions must have distinct row keys, or storage will "
        "last-wins one of them away"
    )
    assert {r["report_status"] for r in rows} == {"Questionable", "Out"}


# ── Scope field: game_type, never season_type ─────────────────────────────────


def test_season_type_is_declared_era_locally_not_globally():
    """`season_type` is real, but only in the single-observation era.

    The earlier version of this test asserted it was "not declared" at all, which
    described a default-era implementation detail rather than the contract and
    stayed green for the wrong reason (Codex B4).
    """
    assert "game_type" in INJURIES.grain
    spec = _bound_injuries()
    by_name = {era.name: era for era in spec.eras}
    assert "season_type" not in by_name["revisioned"].columns
    assert "season_type" in by_name["single_observation"].columns
    assert "date_modified" in by_name["revisioned"].columns
    assert "date_modified" not in by_name["single_observation"].columns
    assert "season_type" not in by_name["single_observation"].grain, (
        "season_type scopes the row; game_type is the grain coordinate"
    )
    assert "season_type" in spec.stored_columns, "the table stores the union"


# ── The three states ──────────────────────────────────────────────────────────


def test_on_report_without_a_designation_is_kept_and_distinguishable():
    """53% of live rows have report_status None. Dropping them loses half the report."""
    rows, _ = normalize_rows(
        [_row(report_status=None)], spec=INJURIES, season=SEASON, identity=_Identity()
    )

    assert len(rows) == 1, "an undesignated row is still an injury-report appearance"
    assert rows[0]["report_status"] is None, (
        "an absent designation must stay absent — never coerced to a status"
    )


def test_absent_players_are_never_synthesized_as_healthy():
    """A row that does not exist is NO INFORMATION, not a healthy designation."""
    rows, _ = normalize_rows(
        [_row(gsis_id="00-0039359")], spec=INJURIES, season=SEASON, identity=_Identity()
    )

    assert len(rows) == 1, (
        "normalization must return exactly the source rows; inventing a row for "
        "an unlisted player would assert health the source never reported"
    )


# ── Two null tokens ───────────────────────────────────────────────────────────


@pytest.mark.parametrize("blank", [None, "", "   ", "\n    "])
def test_both_null_tokens_normalize_to_a_single_absent_value(blank):
    """45 true nulls and 69 whitespace scrape artifacts must not read as different."""
    rows, _ = normalize_rows(
        [_row(practice_status=blank)], spec=INJURIES, season=SEASON, identity=_Identity()
    )

    assert rows[0]["practice_status"] is None, (
        f"{blank!r} must normalize to None; a whitespace scrape artifact and a "
        "true null are the same absence and must not be stored as two values"
    )


def test_a_real_practice_status_is_not_blanked():
    """The null-token rule must not eat real values (the inverse failure)."""
    rows, _ = normalize_rows(
        [_row(practice_status="Full Participation in Practice")],
        spec=INJURIES,
        season=SEASON,
        identity=_Identity(),
    )
    assert rows[0]["practice_status"] == "Full Participation in Practice"


# ── Row conservation and schema drift ─────────────────────────────────────────


def test_stored_rows_equal_source_rows():
    """The count check that caught four silently-dropped plays in PBP."""
    source = [
        _row(gsis_id="00-0039359"),
        _row(gsis_id="00-0034270", team="NYJ", full_name="Tyler Conklin"),
        _row(gsis_id="00-0034270", team="NYJ", full_name="Tyler Conklin",
             report_status="Questionable", date_modified="2024-12-14T20:55:19+00:00"),
    ]
    rows, _ = normalize_rows(
        source, spec=INJURIES, season=SEASON, identity=_Identity()
    )
    assert len(rows) == len(source)


def test_schema_drift_refuses_rather_than_storing_nulls():
    """nflverse renaming a field must surface as a refusal, not a column of empties."""
    broken = _row()
    broken.pop("report_status")

    with pytest.raises(UsageCaptureError, match="schema_drift|missing"):
        normalize_rows([broken], spec=INJURIES, season=SEASON, identity=_Identity())


def test_spec_declares_integer_columns_so_the_export_is_not_all_strings():
    """SQLite stores everything as TEXT; an untyped export ships week/season as Utf8."""
    assert isinstance(INJURIES, StreamSpec)
    assert "season" in INJURIES.integer_columns
    assert "week" in INJURIES.integer_columns


# ── Codex review rows 2/3/4: close the vacuities ──────────────────────────────
#
# Every test above uses the INJURIES constant. Codex reproduced that deleting
# `_bind`'s propagation of blank_as_null_columns leaves all of them green while
# the DEFAULT capture path silently loses the behaviour. These rows exercise the
# BOUND spec and the real store/export path instead.


def _bound_injuries() -> StreamSpec:
    """The spec production actually runs — not the module constant."""
    bound = {spec.name: spec for spec in build_streams()}
    assert "injuries" in bound
    return bound["injuries"]


def test_bound_spec_carries_every_declared_option_through_bind():
    """_bind reconstructs StreamSpec field by field; a new field is silently dropped."""
    spec = _bound_injuries()
    assert spec.loader is not None, "the bound spec must carry a real loader"
    assert spec.loader.__name__ == "load_injuries"
    assert spec.blank_as_null_columns == INJURIES.blank_as_null_columns
    assert spec.integer_columns == INJURIES.integer_columns
    assert spec.require_populated_grain is True
    assert spec.grain == INJURIES.grain


def test_blank_policy_is_pinned_to_the_measured_seven_columns():
    """Seven, not eight — season_type was removed and the count must not drift."""
    assert _bound_injuries().blank_as_null_columns == (
        "report_status",
        "report_primary_injury",
        "report_secondary_injury",
        "practice_status",
        "practice_primary_injury",
        "practice_secondary_injury",
        "position",
    )


@pytest.mark.parametrize("column", INJURIES.blank_as_null_columns)
def test_every_declared_blank_column_normalizes_whitespace(column):
    """Only practice_status was covered; removing any other column stayed green."""
    rows, _ = normalize_rows(
        [_row(**{column: "\n    "})],
        spec=_bound_injuries(),
        season=SEASON,
        identity=_Identity(),
    )
    assert rows[0][column] is None


def test_existing_streams_declare_no_blank_policy():
    """The opt-in must not have leaked into the four previously reviewed streams."""
    for spec in build_streams():
        if spec.name == "injuries":
            continue
        assert spec.blank_as_null_columns == (), spec.name
        assert spec.require_populated_grain is False, spec.name


@pytest.mark.parametrize("absent", [None, "", "   "])
def test_absent_date_modified_refuses(absent):
    """date_modified is the coordinate that makes revisions a time series."""
    with pytest.raises(UsageCaptureError, match="blank_grain"):
        normalize_rows(
            [_row(date_modified=absent)],
            spec=_bound_injuries(),
            season=SEASON,
            identity=_Identity(),
        )


# ── Codex review row 3: a test that actually STORES ───────────────────────────
#
# "stored rows == source rows" previously compared two in-memory list lengths.
# It could not see a dropped SQLite row, a lost export column, or a manifest
# disagreement — which is exactly how the unresolved-identity name loss (row 1)
# survived review. This drives the real capture, store and export path offline.


def test_end_to_end_capture_stores_exports_and_keeps_the_unresolved_name(tmp_path):
    import polars as pl

    from src.dynasty_genius.nflverse_usage import run_usage_capture

    spec = _bound_injuries()
    resolved_id = "00-0039359"
    source_only_id = "00-0000001"

    records = [
        # the real revision pair — two observations, one player-week
        _row(gsis_id=resolved_id, report_status="Questionable",
             date_modified="2024-12-15T03:34:33+00:00"),
        _row(gsis_id=resolved_id, report_status="Out",
             date_modified="2024-12-15T14:17:06+00:00"),
        # an unresolved player whose NAME must survive into the review artifact
        _row(gsis_id=source_only_id, full_name="Source Only Player",
             practice_status="\n    ", date_modified="2024-12-15T14:17:06+00:00"),
    ]

    # The REAL IdentityIndex, so resolution logic is exercised rather than stubbed:
    # a gsis id present in the governed universe resolves canonically, one absent
    # from it is held as source_only.
    from src.dynasty_genius.nflverse_usage import IdentityIndex

    index = IdentityIndex(
        gsis_ids=frozenset({resolved_id}),
        pfr_to_gsis={},
        pfr_conflicts={},
        names_by_gsis={resolved_id: "Cade Stover"},
    )

    result = run_usage_capture(
        seasons=[SEASON],
        specs=[spec],
        identity=index,
        db_path=tmp_path / "usage.db",
        raw_root=tmp_path / "raw",
        export_root=tmp_path / "export",
        fetch=lambda s, season: records,
    )
    assert result is not None

    # SQLite really holds all three rows — both revisions included
    import sqlite3

    conn = sqlite3.connect(tmp_path / "usage.db")
    try:
        stored = conn.execute(f"SELECT COUNT(*) FROM {spec.table}").fetchone()[0]
        statuses = {
            r[0] for r in conn.execute(
                f"SELECT report_status FROM {spec.table} WHERE gsis_id = ?", (resolved_id,)
            )
        }
        blanked = conn.execute(
            f"SELECT practice_status FROM {spec.table} WHERE gsis_id = ?", (source_only_id,)
        ).fetchone()[0]
    finally:
        conn.close()

    assert stored == len(records), "SQLite dropped a row the in-memory check could not see"
    assert statuses == {"Questionable", "Out"}, "a revision was lost in storage"
    assert blanked is None, "the normalized null did not persist to the store"

    # the exported projection carries the same rows
    export_run = sorted((tmp_path / "export").glob("**/injuries.parquet"))
    assert export_run, "no injuries parquet was exported"
    frame = pl.read_parquet(export_run[-1])
    assert frame.height == len(records)

    # ROW 1: the unresolved-identity artifact must keep the human name
    unresolved = sorted((tmp_path / "export").glob("**/unresolved_identity.parquet"))
    assert unresolved, "no unresolved-identity artifact was exported"
    uframe = pl.read_parquet(unresolved[-1])
    names = [n for n in uframe["player"].to_list() if n]
    assert "Source Only Player" in names, (
        "the unresolved-identity review artifact lost the player name; injuries "
        "carry full_name and the export fallback must include it"
    )

    # ── Row 6 residual: v3 must be LOCKED, not merely changed ────────────────
    # Reverting SCHEMA_VERSION to v2 previously left every focused test green,
    # so a four-stream artifact and a five-stream artifact could carry the same
    # label. Assert the value on every surface a consumer could read it from.
    import json as _json

    assert SCHEMA_VERSION == "nflverse_usage.v4"
    assert result["schema_version"] == SCHEMA_VERSION, "returned status"

    marker = _json.loads(
        (tmp_path / "raw" / "nflverse_usage_status_latest.json").read_text(encoding="utf-8")
    )
    assert marker["schema_version"] == SCHEMA_VERSION, "status marker"

    envelopes = [
        q for q in (tmp_path / "raw").glob("**/injuries_*.json")
    ]
    assert envelopes, "no raw envelope was written"
    envelope = _json.loads(envelopes[0].read_text(encoding="utf-8"))
    assert envelope["schema_version"] == SCHEMA_VERSION, "raw envelope"

    for name in ("nflverse_usage.ready.json", "manifest.json"):
        found = sorted((tmp_path / "export").glob(f"**/{name}"))
        assert found, f"{name} was not exported"
        payload = _json.loads(found[-1].read_text(encoding="utf-8"))
        assert payload["schema_version"] == SCHEMA_VERSION, name


# ── Codex review row 7: --summary must not be able to mutate ──────────────────


def test_summary_cannot_mutate_a_four_stream_store(tmp_path):
    """Adding a fifth spec made a read-only command CREATE a table (Codex reproduced).

    `UsageStore.__init__` runs CREATE TABLE IF NOT EXISTS for every spec it is
    handed, so `--summary` building a store from `build_streams()` wrote to an
    existing four-stream database. Intent is not a guarantee — this drives the
    real CLI in a subprocess and compares file bytes.
    """
    import hashlib
    import sqlite3
    import subprocess
    import sys

    from src.dynasty_genius.nflverse_usage import UsageStore

    db = tmp_path / "four_stream.db"
    UsageStore(db, [s for s in build_streams() if s.name != "injuries"])

    def digest() -> str:
        return hashlib.sha256(db.read_bytes()).hexdigest()

    def tables() -> set[str]:
        conn = sqlite3.connect(db)
        try:
            return {
                r[0]
                for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
        finally:
            conn.close()

    before, tables_before = digest(), tables()
    result = subprocess.run(
        [sys.executable, "scripts/run_nflverse_usage_capture.py",
         "--summary", "--db-path", str(db)],
        capture_output=True, text=True, cwd=str(Path(__file__).resolve().parents[2]),
    )

    assert result.returncode == 0, result.stderr
    assert digest() == before, "--summary changed the database file"
    assert tables() == tables_before, "--summary created a table in a read-only command"
    assert "nflverse_injury_report" not in tables(), (
        "the injury table must not appear in a four-stream store just because a "
        "fifth spec was registered"
    )


# ── Live-capture findings: two eras, and a source dtype that breaks filters ────
#
# The live capture stored 2020-2024 and REFUSED 2025. Both facts are real:
#
#   * 2025 SWAPS `date_modified` FOR `season_type` — same 16 columns, one traded
#     for the other. And 2025 has ZERO duplicate groups on the five-column key,
#     so that era cannot express a revision at all. Mapping one era onto the
#     other would either lose the revision semantics or invent them.
#   * THE 2020 FILE TYPES season/week AS Float64 while 2021+ types them Int32,
#     so the store held '2020.0' and '1.0'. A consumer filtering season == 2020
#     or week == 1 misses the entire season — the exact failure `integer_columns`
#     exists to prevent, missed because it is a source DTYPE difference rather
#     than a column difference.
#
# Eras are detected from the COLUMN SET, never the year — the PlayerProfiler
# discipline, where an unrecognised era refuses rather than being mapped onto a
# known one.


def _era_b_row(**overrides):
    """A 2025-shaped row: season_type present, date_modified absent."""
    row = _row(**overrides)
    row.pop("date_modified", None)
    row["season_type"] = "REG"
    return row


def test_revisioned_era_keys_on_date_modified():
    spec = _bound_injuries()
    rows, _ = normalize_rows(
        [
            _row(report_status="Questionable", date_modified="2024-12-15T03:34:33+00:00"),
            _row(report_status="Out", date_modified="2024-12-15T14:17:06+00:00"),
        ],
        spec=spec, season=2024, identity=_Identity(),
    )
    assert len(rows) == 2
    assert len({r["row_key"] for r in rows}) == 2
    assert {r["source_era"] for r in rows} == {"revisioned"}


def test_single_observation_era_is_accepted_without_date_modified():
    """2025 must ingest, not refuse — it is a different shape, not a broken one."""
    spec = _bound_injuries()
    rows, _ = normalize_rows(
        [_era_b_row()], spec=spec, season=2025, identity=_Identity()
    )
    assert len(rows) == 1
    assert rows[0]["source_era"] == "single_observation"
    assert rows[0].get("date_modified") is None


def test_era_is_detected_from_columns_not_the_year():
    """A season label must never decide the era; the column set must."""
    spec = _bound_injuries()
    # era-B shaped data carrying a 2021 label
    rows, _ = normalize_rows(
        [_era_b_row(season=2021)], spec=spec, season=2021, identity=_Identity()
    )
    assert rows[0]["source_era"] == "single_observation"


def test_unrecognised_column_shape_refuses():
    """Neither era: refuse rather than mapping onto whichever looks closest."""
    spec = _bound_injuries()
    broken = _row()
    broken.pop("date_modified")            # no date_modified
    # and no season_type either -> matches no declared era
    with pytest.raises(UsageCaptureError, match="era|schema_drift|missing"):
        normalize_rows([broken], spec=spec, season=2024, identity=_Identity())


def test_single_observation_era_still_refuses_a_duplicate_key():
    """Without date_modified the five-column key must still be unique."""
    spec = _bound_injuries()
    with pytest.raises(UsageCaptureError, match="grain_violation"):
        normalize_rows(
            [_era_b_row(), _era_b_row()], spec=spec, season=2025, identity=_Identity()
        )


@pytest.mark.parametrize(
    "raw,expected",
    [(2020.0, "2020"), ("2020.0", "2020"), (2020, "2020"), ("2020", "2020")],
)
def test_float_typed_season_is_normalized_for_storage(raw, expected):
    """'2020.0' in the store means `season == 2020` misses the whole season."""
    rows, _ = normalize_rows(
        [_row(season=raw)], spec=_bound_injuries(), season=2020, identity=_Identity()
    )
    assert str(rows[0]["season"]) == expected


@pytest.mark.parametrize("raw,expected", [(1.0, "1"), ("1.0", "1"), (13, "13")])
def test_float_typed_week_is_normalized_for_storage(raw, expected):
    rows, _ = normalize_rows(
        [_row(week=raw)], spec=_bound_injuries(), season=2020, identity=_Identity()
    )
    assert str(rows[0]["week"]) == expected


def test_a_genuinely_fractional_integer_column_refuses():
    """2020.5 is not a season; coercing it would invent a fact."""
    with pytest.raises(UsageCaptureError, match="integer|numeric"):
        normalize_rows(
            [_row(season=2020.5)], spec=_bound_injuries(), season=2020, identity=_Identity()
        )


def test_every_era_column_has_a_home_in_the_table():
    """An era column absent from stored_columns is dropped SILENTLY at insert.

    Measured: 2025's `season_type` was declared by its era and produced by
    normalization, then discarded because the table was created from the default
    era's column list. `row.get()` means no error — just missing data.
    """
    spec = _bound_injuries()
    stored = set(spec.stored_columns)
    for era in spec.eras:
        missing = [c for c in era.columns if c not in stored]
        assert not missing, f"era {era.name} columns with no column to land in: {missing}"
    assert "season_type" in stored
    assert "date_modified" in stored


def test_declared_integer_column_refuses_at_normalization_not_at_export():
    """The refusal for an integer column must happen BEFORE the season is stored.

    Codex M1: the export cast would refuse malformed text, but only after SQLite
    had already been rewritten. Normalization is the earlier, safer boundary.
    """
    with pytest.raises(UsageCaptureError, match="nflverse_non_integer"):
        normalize_rows(
            [_row(week="not-a-number")],
            spec=_bound_injuries(), season=SEASON, identity=_Identity(),
        )


# ── Codex post-live review: B3, B5, B6, M2 ────────────────────────────────────


def test_widening_the_projection_is_not_unchanged(tmp_path):
    """B3: same rows + a different persisted projection must NOT be `unchanged`.

    Hashing rows ALONE meant a schema widening returned `unchanged`, so the new
    columns stayed NULL and only a manual DELETE recovered it. The idempotence
    identity must include the projection the rows are persisted through.
    """
    from dataclasses import replace as _replace

    from src.dynasty_genius.nflverse_usage import UsageStore

    spec = _bound_injuries()
    narrow = _replace(spec, eras=(), columns=spec.columns, grain=spec.grain)
    rows, coverage = normalize_rows(
        [_row()], spec=spec, season=SEASON, identity=_Identity()
    )

    db = tmp_path / "widen.db"
    UsageStore(db, [narrow]).apply_season(
        narrow, season=SEASON, rows=rows, coverage=coverage, ingested_at="t0"
    )
    # widen the projection, then apply the IDENTICAL rows
    assert UsageStore.migrate_additive_columns(db, [spec])[spec.table]
    verdict = UsageStore(db, [spec]).apply_season(
        spec, season=SEASON, rows=rows, coverage=coverage, ingested_at="t1"
    )

    assert verdict != "unchanged", (
        "identical rows through a WIDER projection returned `unchanged`; the new "
        "columns would stay NULL until someone deleted the table by hand"
    )


def test_additive_migration_is_explicit_and_the_store_still_fails_closed(tmp_path):
    """B5: reproducible from code, but never silently on open.

    The deliberate fail-closed contract predates this work. Auto-widening on
    every store open would be the same silent-change class this module refuses.
    """
    import sqlite3

    from src.dynasty_genius.nflverse_usage import UsageStore

    spec = _bound_injuries()
    db = tmp_path / "old.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            f"CREATE TABLE {spec.table} (row_key TEXT PRIMARY KEY, season TEXT)"
        )

    with pytest.raises(UsageCaptureError, match="schema_mismatch"):
        UsageStore(db, [spec])

    added = UsageStore.migrate_additive_columns(db, [spec])
    assert "source_era" in added[spec.table]
    assert "season_type" in added[spec.table]
    UsageStore(db, [spec])  # now opens


def test_empty_stream_still_exports_the_declared_schema(tmp_path):
    """B6: consumer schema must not depend on whether the table happens to be empty."""
    import polars as pl

    from src.dynasty_genius.nflverse_usage import UsageStore, publish_export

    spec = _bound_injuries()
    store = UsageStore(tmp_path / "empty.db", [spec])
    publish_export(
        store, [spec], run_id="r1", captured_at="t0", export_root=tmp_path / "export"
    )

    found = sorted((tmp_path / "export").glob("**/injuries.parquet"))
    assert found, "no parquet exported for an empty stream"
    frame = pl.read_parquet(found[-1])
    assert frame.height == 0
    assert set(spec.stored_columns) <= set(frame.columns), (
        "an empty export dropped the declared columns; a zero-column Parquet "
        "makes the consumer contract depend on today's row count"
    )


def test_both_era_columns_survive_storage_and_export(tmp_path):
    """M2: a real store round-trip, not a membership assertion.

    The previous test checked `stored_columns` membership and would not have
    caught an insert/projection regression.
    """
    import polars as pl

    from src.dynasty_genius.nflverse_usage import IdentityIndex, run_usage_capture

    spec = _bound_injuries()
    era_b = _row(gsis_id="00-0000002", season=2025)
    era_b.pop("date_modified")
    era_b["season_type"] = "POST"

    index = IdentityIndex(
        gsis_ids=frozenset({"00-0039359", "00-0000002"}),
        pfr_to_gsis={}, pfr_conflicts={}, names_by_gsis={},
    )
    payload = {2024: [_row()], 2025: [era_b]}
    run_usage_capture(
        seasons=[2024, 2025], specs=[spec], identity=index,
        db_path=tmp_path / "u.db", raw_root=tmp_path / "raw",
        export_root=tmp_path / "export",
        fetch=lambda s, season: payload[season],
    )

    import sqlite3

    conn = sqlite3.connect(tmp_path / "u.db")
    try:
        stored = {
            r[0]: (r[1], r[2])
            for r in conn.execute(
                f"SELECT source_era, date_modified, season_type FROM {spec.table}"
            )
        }
    finally:
        conn.close()

    assert stored["revisioned"][0] is not None, "date_modified lost in storage"
    assert stored["revisioned"][1] is None
    assert stored["single_observation"][1] == "POST", "season_type lost in storage"
    assert stored["single_observation"][0] is None

    exported = sorted((tmp_path / "export").glob("**/injuries.parquet"))
    frame = pl.read_parquet(exported[-1])
    assert set(frame["season_type"].to_list()) == {None, "POST"}
    assert frame.height == 2


def test_an_additive_unknown_provider_column_refuses():
    """B1's actual reproducer: an otherwise-valid row with an EXTRA column.

    `requires`/`forbids` matching accepted it as `single_observation` and silently
    discarded the field — which is exactly how 2025's `season_type` was lost the
    first time. The earlier "unrecognised shape" test removed a column instead of
    adding one, so it matched no era under either implementation and could not
    distinguish them. Found because the positive control for this fix did not
    fail when the fix was reverted.
    """
    extra = _row(unexpected_provider_field="surprise")
    with pytest.raises(UsageCaptureError, match="unknown_era"):
        normalize_rows(
            [extra], spec=_bound_injuries(), season=SEASON, identity=_Identity()
        )


def test_ambiguous_era_declaration_refuses():
    """Two eras matching one column set must refuse, not take the first.

    Taking `next()` would make the contract depend on declaration ORDER.
    """
    from dataclasses import replace as _replace

    spec = _bound_injuries()
    twin = _replace(spec.eras[0], name="revisioned_twin")
    ambiguous = _replace(spec, eras=(spec.eras[0], twin))

    with pytest.raises(UsageCaptureError, match="ambiguous_era"):
        normalize_rows(
            [_row()], spec=ambiguous, season=SEASON, identity=_Identity()
        )


# ── Codex R2 re-review: the one-row positive control was itself vacuous ────────


def test_a_later_record_with_an_extra_column_refuses():
    """R2-B1: era validation must check EVERY record, not just records[0].

    The era was chosen from the first mapping and never re-checked, so a valid
    first row followed by one carrying an unexpected provider field was accepted
    and the field silently discarded. My B1 positive control used a ONE-ROW
    batch, so it could not distinguish the two implementations — the same
    guard-that-does-not-guard shape, one level down.
    """
    with pytest.raises(UsageCaptureError, match="heterogeneous_batch"):
        normalize_rows(
            [_row(), _row(gsis_id="00-0000002", unexpected_provider_field="x")],
            spec=_bound_injuries(), season=SEASON, identity=_Identity(),
        )


def test_a_later_record_missing_a_declared_column_refuses():
    """The other half of R2-B1: absence in a later row, not just addition."""
    short = _row(gsis_id="00-0000003")
    short.pop("report_primary_injury")
    with pytest.raises(UsageCaptureError, match="heterogeneous_batch"):
        normalize_rows(
            [_row(), short],
            spec=_bound_injuries(), season=SEASON, identity=_Identity(),
        )


def test_a_homogeneous_multi_row_batch_is_still_accepted():
    """The refusal must not fire on the normal case (the inverse failure)."""
    rows, _ = normalize_rows(
        [_row(), _row(gsis_id="00-0000004")],
        spec=_bound_injuries(), season=SEASON, identity=_Identity(),
    )
    assert len(rows) == 2


def test_schema_mismatch_error_names_the_real_migration_entry_point():
    """R2-B5: the message said widening was automatic. It is not, and was not."""
    import sqlite3

    from src.dynasty_genius.nflverse_usage import UsageStore

    spec = _bound_injuries()
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "old.db"
        with sqlite3.connect(db) as conn:
            conn.execute(
                f"CREATE TABLE {spec.table} (row_key TEXT PRIMARY KEY, season TEXT)"
            )
        with pytest.raises(UsageCaptureError) as exc:
            UsageStore(db, [spec])
    message = str(exc.value)
    assert "migrate_additive_columns" in message, (
        "the failure surface must name the real entry point"
    )
    assert "automatically" not in message, (
        "the message previously claimed automatic widening, which was false"
    )
