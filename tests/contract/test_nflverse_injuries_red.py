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
  * `season_type` exists ONLY in 2025 — 16 columns for 2015-2024, 17 for 2025.
    A first reading called it "66% null"; that was an artifact of polars unioning
    schemas across a multi-season load. Declaring it would make every pre-2025
    single-season load refuse on schema drift, so it is deliberately absent.
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


def test_scope_uses_game_type_and_season_type_is_not_declared():
    """season_type exists only in 2025; declaring it breaks every earlier season."""
    assert "game_type" in INJURIES.grain
    assert "season_type" not in INJURIES.grain
    assert "season_type" not in INJURIES.columns, (
        "a 2025-only column must not be declared, or 2015-2024 loads refuse"
    )


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

    assert SCHEMA_VERSION == "nflverse_usage.v3"
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
