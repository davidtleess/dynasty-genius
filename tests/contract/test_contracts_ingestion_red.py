"""RED contract — `load_contracts` (Layer 1, board block C, stream 5 of 6).

Design cleared through THREE review rounds before any code was written:
  design v1 -> Codex NOT CLEAR · v2 -> NOT CLEAR (D1-D5) · v3 -> DESIGN CLEAR
  docs/agent-ledger/evidence/2026-08-05/contracts_design_note_claude_v3.md
  docs/agent-ledger/evidence/2026-08-05/contracts_design_clear_codex_v3.md
Generator: docs/agent-ledger/evidence/2026-08-05/build_contracts_fixture_claude_v1.py

DAVID'S RULING (obtained before the design was finalised): ACCUMULATE FROM CAPTURE ONE, WEEKLY.
Retention indefinite, no pruning. Cadence authorizes NO scheduler.

MEASURED LIVE 2026-08-05 (`nflreadpy 0.1.5`):
  51,808 source rows / 25 columns; NO season axis and the source MOVES (51,803 earlier the same
  session). 2,503 duplicate groups / 3,316 excess copies / 5,819 participating / max 9;
  48,492 + 3,316 = 51,808.
  POST-COLLAPSE census: 32,198 canonical_resolved + 12,196 source_only + 4,098 unknown = 48,492.
  First-snapshot unresolved artifact: 16,294 (EVERY non-canonical row, not just the unknowns).
  4,219 null `gsis_id` at SOURCE -> 4,098 stored; 121 null-ID excess copies collapse.
  `year_signed == 0` on 1,106 rows, preserved literally.
  All 45,875 non-null `cols` lists: numeric years ascending and unique, every list ending in
  exactly one non-numeric token 'Total'. `year` is NOT always numeric; never sort the list.

Imports are lazy: an unbuilt symbol at module level is a COLLECTION error and the standing
invariant is zero collection errors.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "contracts_slice.json"
MANIFEST = REPO_ROOT / "tests" / "fixtures" / "contracts_slice_manifest.json"

STREAM = "contracts"
EXPECTED_COLUMN_COUNT = 25
NESTED_FIELDS = (
    "year", "team", "base_salary", "prorated_bonus", "roster_bonus", "guaranteed_salary",
    "cap_number", "cap_percent", "cash_paid", "workout_bonus", "other_bonus",
    "per_game_roster_bonus", "option_bonus",
)
EXPECTED_INTEGERS = ("year_signed", "years", "otc_id", "draft_year", "draft_round",
                     "draft_overall")
EXPECTED_FLOATS = ("value", "apy", "guaranteed", "apy_cap_pct", "inflated_value",
                   "inflated_apy", "inflated_guaranteed")
EXPECTED_BOOLEANS = ("is_active",)
EXPECTED_STRINGS = ('player', 'position', 'team', 'player_page', 'gsis_id', 'date_of_birth', 'height', 'weight', 'college', 'draft_team')

#: Codex D3: a snapshot is counted ONCE under its own vocabulary, never as a stream-season.
SNAPSHOT_TOTAL_KEY = "stream_snapshots"


def _mod():
    from src.dynasty_genius import nflverse_usage

    return nflverse_usage


def _spec():
    spec = getattr(_mod(), "CONTRACTS", None)
    if spec is None:
        pytest.fail("CONTRACTS is not defined in nflverse_usage")
    return spec


@pytest.fixture(scope="module")
def rows() -> list[dict[str, Any]]:
    if not FIXTURE.exists():
        pytest.fail(f"missing fixture: {FIXTURE}")
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest() -> dict[str, Any]:
    if not MANIFEST.exists():
        pytest.fail(f"missing provenance manifest: {MANIFEST}")
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def identity():
    return _mod().IdentityIndex.from_governed_crosswalk()


#: Columns EXCLUDED from the content digest — capture and derived identity metadata only.
#: Pinned here so the test computes the oracle itself rather than calling production (S3).
#: T4: an ALLOW-LIST of the pinned 25 source columns, not a metadata deny-list. A deny-list
#: silently admits any new column the provider or our own pipeline adds.
DIGEST_COLUMNS = (
    "player", "position", "team", "is_active", "year_signed", "years", "value", "apy",
    "guaranteed", "apy_cap_pct", "inflated_value", "inflated_apy", "inflated_guaranteed",
    "player_page", "otc_id", "gsis_id", "date_of_birth", "height", "weight", "college",
    "draft_year", "draft_round", "draft_overall", "draft_team", "cols",
)


def _test_side_digest(row: dict) -> str:
    """SHA-256 over the canonical normalized SOURCE columns, computed in TEST code.

    S3: the earlier version called production `row_content_digest` as its own oracle, so the
    same wrong algorithm on both sides would agree. This reimplements it independently.
    """
    import hashlib

    payload = {k: row.get(k) for k in DIGEST_COLUMNS}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _source_digest(row: dict) -> str:
    """Stable identity for pairing a normalized row back to its SOURCE row (S1).

    The earlier version paired on six business fields. Measured on this fixture that yields 192
    keys for 195 rows, and one key — (30, 2016, 'Bears', 'C', 0.965, 0.965) — maps to TWO
    payloads differing in `guaranteed` and `inflated_guaranteed`, so `setdefault` silently
    compared one correct row against the wrong source.
    """
    import hashlib

    canonical = json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _capture(tmp_path: Path, identity, rows, **overrides):
    mod = _mod()
    kwargs = {
        "seasons": [],
        "specs": (_spec(),),
        "identity": identity,
        "db_path": tmp_path / "u.db",
        "raw_root": tmp_path / "rt",
        "fetch": lambda spec, season=None: [dict(r) for r in rows],
        **overrides,
    }
    return mod.run_usage_capture(**kwargs)


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def test_the_fixture_carries_checkable_provenance(rows, manifest) -> None:
    assert manifest["n_columns"] == EXPECTED_COLUMN_COUNT
    assert len(manifest["upstream_sha256"]) == 64
    assert manifest["nflreadpy_version"]
    assert manifest["upstream_rows"] > manifest["slice_rows"] == len(rows)


def test_the_fixture_exercises_every_contract_path(manifest) -> None:
    """Each of these guards a distinct clause of the design; without them it is untested."""
    assert manifest["exact_duplicate_excess"] >= 1, "collapse path untested"
    assert manifest["null_gsis_rows"] >= 1, "unknown-identity path untested"
    assert manifest["year_signed_zero_rows"] >= 1, "the 1,106 zero rows are unrepresented"
    assert manifest["null_cols_rows"] >= 1, "SQL-NULL cols path untested"
    assert manifest["every_list_ends_in_total"] is True


# ---------------------------------------------------------------------------
# The declared contract
# ---------------------------------------------------------------------------


def test_the_stream_is_registered_once_on_the_snapshot_axis() -> None:
    import nflreadpy

    built = _mod().build_streams()
    assert [s.name for s in built].count(STREAM) == 1
    spec = next(s for s in built if s.name == STREAM)
    assert spec.loader is nflreadpy.load_contracts
    assert spec.capture_axis == "snapshot"


def test_bind_preserves_the_capture_axis() -> None:
    """Codex D4-12. A flag `_bind` forgets has already bitten this batch once, on stream 2."""
    spec = next(s for s in _mod().build_streams() if s.name == STREAM)
    assert spec.capture_axis == "snapshot"


def test_every_other_stream_stays_on_the_seasonal_axis() -> None:
    """The new axis must default off; no existing stream may change behaviour."""
    for spec in _mod().build_streams():
        if spec.name != STREAM:
            assert spec.capture_axis == "seasonal", f"{spec.name} changed axis"


def test_the_snapshot_spec_declares_no_min_season() -> None:
    """Codex D4-8: a season floor is meaningless without a season axis."""
    assert _spec().min_season is None


def test_all_twenty_five_columns_are_type_pinned(rows) -> None:
    spec = _spec()
    assert set(spec.columns) == set(rows[0])
    assert len(spec.columns) == EXPECTED_COLUMN_COUNT
    assert set(spec.integer_columns) == set(EXPECTED_INTEGERS)
    assert set(spec.float_columns) == set(EXPECTED_FLOATS)
    assert set(spec.boolean_columns) == set(EXPECTED_BOOLEANS)
    assert "cols" in getattr(spec, "json_columns", ()), "the nested column must be declared JSON"


def test_the_emitted_parquet_reconciles_all_twenty_five_columns(
    tmp_path, rows, identity
) -> None:
    """R2: the declaration test pins the SPEC. This reads the EMITTED contracts.parquet and
    reconciles dtype AND non-null counts for every one of the 25 columns — the fixtures
    happened to carry the right Python types, so a declaration-only assertion cannot see a
    publisher that types correctly while dropping values."""
    import polars as pl

    result = _capture(tmp_path, identity, rows)
    run = sorted((tmp_path / "rt" / "export" / "runs").iterdir())[-1]
    frame = pl.read_parquet(run / "contracts.parquet")
    dtypes = dict(zip(frame.columns, frame.dtypes))
    stored = result["results"][0]["coverage"]["rows_total"]
    assert frame.height == stored

    for column in EXPECTED_INTEGERS:
        assert dtypes[column] == pl.Int64, f"{column} published as {dtypes[column]}"
    for column in EXPECTED_FLOATS:
        assert dtypes[column] == pl.Float64, f"{column} published as {dtypes[column]}"
    for column in EXPECTED_BOOLEANS:
        assert dtypes[column] == pl.Boolean, f"{column} published as {dtypes[column]}"
    assert dtypes["cols"] == pl.Utf8, "the nested column publishes as canonical JSON text"
    # T2: the ten strings were unpinned, so categorical/enum output carrying identical Python
    # values would pass. Metadata columns too.
    for column in EXPECTED_STRINGS:
        assert dtypes[column] == pl.Utf8, f"{column} published as {dtypes[column]}, not Utf8"
    for column in ("content_sha256", "snapshot_id", "observed_at"):
        assert dtypes[column] == pl.Utf8, f"{column} published as {dtypes[column]}, not Utf8"

    # S2: an earlier version checked 15 of 25 columns and only NON-NULL COUNTS, so replacing
    # every value with another non-null value passed. Reconcile EXACT VALUES for ALL 25.
    mod = _mod()
    normalized, _ = mod.normalize_rows(
        [dict(r) for r in rows], spec=_spec(), season=None, identity=identity
    )
    assert set(_spec().columns) <= set(frame.columns)
    by_digest = {r["content_sha256"]: r for r in normalized}
    emitted_rows = frame.to_dicts()
    assert len(emitted_rows) == len(by_digest)
    for emitted in emitted_rows:
        origin = by_digest[emitted["content_sha256"]]
        for column in _spec().columns:
            want, got = origin.get(column), emitted.get(column)
            if want is None:
                assert got is None, f"{column}: emitted {got!r} where source was null"
            elif isinstance(want, float):
                assert got == pytest.approx(want), f"{column}: {got!r} != {want!r}"
            else:
                assert got == want, f"{column}: {got!r} != {want!r}"


def test_identity_is_gsis(rows) -> None:
    spec = _spec()
    assert spec.identity_column == "gsis_id"
    assert spec.identity_kind == "gsis"


# ---------------------------------------------------------------------------
# D1 — the census, at the right pipeline stage
# ---------------------------------------------------------------------------


def test_the_census_is_measured_after_collapse_not_before(tmp_path, rows, identity) -> None:
    """The v2 defect: a source-stage count attached to a post-collapse claim."""
    result = _capture(tmp_path, identity, rows)
    entry = result["results"][0]
    coverage = entry["coverage"]
    collapsed = coverage["rows_collapsed_exact_duplicates"]
    assert coverage["rows_total"] + collapsed == len(rows)
    parts = ("rows_canonical_resolved", "rows_source_only", "rows_conflict", "rows_unknown")
    assert sum(coverage[k] for k in parts) == coverage["rows_total"]


def test_a_null_gsis_row_is_unknown_and_reaches_the_unresolved_artifact(
    tmp_path, rows, identity
) -> None:
    """The artifact carries EVERY non-canonical row, not only the unknowns."""
    import polars as pl

    mod = _mod()
    result = _capture(tmp_path, identity, rows)
    coverage = result["results"][0]["coverage"]
    assert coverage["rows_unknown"] >= 1

    run = sorted((tmp_path / "rt" / "export" / "runs").iterdir())[-1]
    unresolved = pl.read_parquet(run / "unresolved_identity.parquet")
    expected = sum(
        coverage[k] for k in ("rows_source_only", "rows_conflict", "rows_unknown")
    )
    assert unresolved.height == expected, (
        "the unresolved artifact must carry every non-canonical row"
    )
    assert unresolved.height != coverage["rows_unknown"] or coverage["rows_source_only"] == 0
    _ = mod


# ---------------------------------------------------------------------------
# D2 — snapshot context on the unresolved artifact
# ---------------------------------------------------------------------------


def test_unresolved_snapshot_rows_carry_snapshot_context(tmp_path, rows, identity) -> None:
    """Codex D2. Without this, 52 weekly snapshots of the same unresolved player are
    indistinguishable rows."""
    import polars as pl

    result = _capture(tmp_path, identity, rows)
    entry = result["results"][0]
    run = sorted((tmp_path / "rt" / "export" / "runs").iterdir())[-1]
    unresolved = pl.read_parquet(run / "unresolved_identity.parquet")
    for column in ("capture_axis", "snapshot_id", "observed_at"):
        assert column in unresolved.columns, f"unresolved artifact lacks {column}"
    # R9: presence is not enough — an all-null column would pass that. Require the EXACT
    # values from this run, non-null on every row.
    assert unresolved["capture_axis"].null_count() == 0
    assert unresolved["snapshot_id"].null_count() == 0
    assert unresolved["observed_at"].null_count() == 0
    assert set(unresolved["capture_axis"].to_list()) == {"snapshot"}
    assert set(unresolved["snapshot_id"].to_list()) == {entry["snapshot_id"]}
    assert set(unresolved["observed_at"].to_list()) == {entry["observed_at"]}


# ---------------------------------------------------------------------------
# D3 — totals and durable partition fields
# ---------------------------------------------------------------------------


def test_a_snapshot_is_counted_once_and_not_as_a_stream_season(
    tmp_path, rows, identity
) -> None:
    result = _capture(tmp_path, identity, rows, seasons=[2023, 2024, 2025])
    totals = result["totals"]
    assert totals[SNAPSHOT_TOTAL_KEY] == 1, (
        "one snapshot per RUN regardless of how many seasons the run requests"
    )
    assert totals["stream_seasons"] == 0, "a snapshot is not a stream-season"
    assert len([r for r in result["results"] if r["stream"] == STREAM]) == 1


def test_no_synthetic_season_is_invented(tmp_path, rows, identity) -> None:
    """Codex D3: never stuff snapshot_id into season, nor repurpose year_signed as one."""
    import sqlite3

    _capture(tmp_path, identity, rows)
    with sqlite3.connect(tmp_path / "u.db") as conn:
        columns = {r[1] for r in conn.execute("PRAGMA table_info(contracts)")}
    assert "snapshot_id" in columns and "observed_at" in columns
    # R6: an earlier draft ran SELECT season_ingested and asserted the values were empty —
    # which REQUIRES the seasonal column to exist, contradicting design v3. The snapshot table
    # must not carry the field at all.
    assert "season_ingested" not in columns, (
        "a snapshot table must not carry the seasonal partition field"
    )


def test_the_result_entry_uses_snapshot_partition_fields(tmp_path, rows, identity) -> None:
    result = _capture(tmp_path, identity, rows)
    entry = result["results"][0]
    assert entry["capture_axis"] == "snapshot"
    assert entry["snapshot_id"]
    assert entry["observed_at"]
    assert "season" not in entry or entry["season"] is None


# ---------------------------------------------------------------------------
# D4 — accumulation vs idempotence, the subtlest boundary in the design
# ---------------------------------------------------------------------------


def test_two_runs_with_identical_content_accumulate_two_observations(
    tmp_path, rows, identity
) -> None:
    """Codex's binding interpretation: different run-unique snapshot IDs are DIFFERENT
    observations. This is the defining property of accumulation and the one a content-keyed
    design most easily breaks — if it fails, weekly history silently deduplicates."""
    import sqlite3

    first = _capture(tmp_path, identity, rows)
    second = _capture(tmp_path, identity, rows)
    assert first["results"][0]["snapshot_id"] != second["results"][0]["snapshot_id"]
    with sqlite3.connect(tmp_path / "u.db") as conn:
        snapshots = conn.execute(
            "SELECT COUNT(DISTINCT snapshot_id) FROM contracts"
        ).fetchone()[0]
        total = conn.execute("SELECT COUNT(*) FROM contracts").fetchone()[0]
    assert snapshots == 2, "identical content across two runs must accumulate twice"
    assert total == 2 * first["results"][0]["coverage"]["rows_total"]


def _snapshot_args(**over):
    base = dict(
        snapshot_id="snap-1",
        observed_at="2026-08-05T00:00:00Z",
        raw_sha256="a" * 64,
        raw_snapshot="/durable/raw/snap-1.json",
    )
    base.update(over)
    return base


def _durable_state(db_path: Path) -> dict:
    """S4: reading three columns let a retry silently rewrite ingested_at, raw path/hash,
    coverage, projection, the snapshot digest or any other metadata and still pass. Capture
    EVERY column of EVERY row, plus the whole capture-ledger record."""
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = [dict(r) for r in conn.execute("SELECT * FROM contracts ORDER BY row_key")]
        # G6: this read nflverse_capture — the SEASONAL ledger, which a snapshot stream never
        # writes — so a retry could mutate the snapshot ledger and the comparison saw nothing.
        ledger = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM nflverse_snapshot_capture ORDER BY stream, snapshot_id"
            )
        ]
    return {"rows": rows, "ledger": ledger}


def test_reusing_a_snapshot_id_with_identical_everything_is_a_no_op(
    tmp_path, rows, identity
) -> None:
    """R4: the earlier version supplied NO provenance and inspected NO durable state, so
    'unchanged, no rewrite' was asserted on a return value alone."""
    mod = _mod()
    spec = _spec()
    store = mod.UsageStore(tmp_path / "u.db", (spec,))
    normalized, coverage = mod.normalize_rows(
        [dict(r) for r in rows], spec=spec, season=None, identity=identity
    )
    store.apply_snapshot(spec, rows=normalized, coverage=coverage, ingested_at="t0",
                         **_snapshot_args())
    before = _durable_state(tmp_path / "u.db")

    applied = store.apply_snapshot(spec, rows=normalized, coverage=coverage, ingested_at="t1",
                                   **_snapshot_args())
    assert applied == "unchanged"
    assert _durable_state(tmp_path / "u.db") == before, "a no-op rewrote durable state"


@pytest.mark.parametrize(
    "mutation",
    [
        {"observed_at": "2026-08-05T00:00:01Z"},
        {"raw_sha256": "b" * 64},
        {"raw_snapshot": "/durable/raw/other.json"},
    ],
)
def test_reusing_a_snapshot_id_with_changed_provenance_refuses(
    tmp_path, rows, identity, mutation
) -> None:
    """R4: same-ID retry is idempotent ONLY if observed_at, the row/coverage digest AND raw
    provenance all match. Each mutation is tested separately, and the first success must
    survive the refusal untouched."""
    mod = _mod()
    spec = _spec()
    store = mod.UsageStore(tmp_path / "u.db", (spec,))
    normalized, coverage = mod.normalize_rows(
        [dict(r) for r in rows], spec=spec, season=None, identity=identity
    )
    store.apply_snapshot(spec, rows=normalized, coverage=coverage, ingested_at="t0",
                         **_snapshot_args())
    before = _durable_state(tmp_path / "u.db")

    with pytest.raises(mod.UsageCaptureError):
        store.apply_snapshot(spec, rows=normalized, coverage=coverage, ingested_at="t1",
                             **_snapshot_args(**mutation))
    assert _durable_state(tmp_path / "u.db") == before, (
        "the refused retry mutated the first success"
    )


def test_reusing_a_snapshot_id_with_a_changed_row_payload_refuses(
    tmp_path, rows, identity
) -> None:
    mod = _mod()
    spec = _spec()
    store = mod.UsageStore(tmp_path / "u.db", (spec,))
    normalized, coverage = mod.normalize_rows(
        [dict(r) for r in rows], spec=spec, season=None, identity=identity
    )
    store.apply_snapshot(spec, rows=normalized, coverage=coverage, ingested_at="t0",
                         **_snapshot_args())
    before = _durable_state(tmp_path / "u.db")

    changed = [dict(r) for r in normalized][:-1]
    with pytest.raises(mod.UsageCaptureError):
        store.apply_snapshot(spec, rows=changed, coverage=coverage, ingested_at="t1",
                             **_snapshot_args())
    assert _durable_state(tmp_path / "u.db") == before


def test_reusing_a_snapshot_id_with_a_changed_collapse_count_refuses(
    tmp_path, rows, identity
) -> None:
    """The snapshot-level digest MUST include coverage, so a changed exact-duplicate count
    cannot hide behind an identical collapsed row-set."""
    mod = _mod()
    spec = _spec()
    store = mod.UsageStore(tmp_path / "u.db", (spec,))
    normalized, coverage = mod.normalize_rows(
        [dict(r) for r in rows], spec=spec, season=None, identity=identity
    )
    _, coverage2 = mod.normalize_rows(
        [*[dict(r) for r in rows], dict(rows[0])], spec=spec, season=None, identity=identity
    )
    assert coverage2["rows_collapsed_exact_duplicates"] > (
        coverage["rows_collapsed_exact_duplicates"]
    )
    store.apply_snapshot(spec, rows=normalized, coverage=coverage, ingested_at="t0",
                         **_snapshot_args())
    before = _durable_state(tmp_path / "u.db")
    with pytest.raises(mod.UsageCaptureError):
        store.apply_snapshot(spec, rows=normalized, coverage=coverage2, ingested_at="t1",
                             **_snapshot_args())
    assert _durable_state(tmp_path / "u.db") == before


def test_normalization_preserves_every_source_value_exactly(rows, identity) -> None:
    """T3: the publisher and digest tests both trust production-normalized values, so a
    normalization that mutated a scalar and then hashed the mutation would satisfy both. This
    reconciles the exact-unique 25-column SOURCE projection against the normalized rows first,
    independently of any digest."""
    mod = _mod()
    normalized, coverage = mod.normalize_rows(
        [dict(r) for r in rows], spec=_spec(), season=None, identity=identity
    )
    seen: dict[str, dict] = {}
    for row in rows:
        seen.setdefault(_source_digest(row), row)
    assert len(normalized) + coverage["rows_collapsed_exact_duplicates"] == len(rows)

    expected_projection = sorted(
        tuple(_normalized_view(r).get(c) for c in DIGEST_COLUMNS) for r in seen.values()
    )
    actual_projection = sorted(
        tuple(r.get(c) for c in DIGEST_COLUMNS) for r in normalized
    )
    assert actual_projection == expected_projection, (
        "normalization altered at least one source value before it was hashed or published"
    )


def test_the_row_digest_matches_a_test_side_oracle_for_every_row(
    tmp_path, rows, identity
) -> None:
    """S3: calling production `row_content_digest` as the oracle means the same wrong algorithm
    on both sides agrees. The expected value is computed in TEST code, over EVERY row."""
    mod = _mod()
    normalized, _ = mod.normalize_rows(
        [dict(r) for r in rows], spec=_spec(), season=None, identity=identity
    )
    assert normalized
    for row in normalized:
        assert row["content_sha256"] == _test_side_digest(row), (
            "content_sha256 does not match an independently computed SHA-256 over the "
            "canonical non-metadata columns"
        )


def test_a_change_confined_to_the_nested_column_changes_the_digest(rows, identity) -> None:
    """S3: without this, `cols` could be excluded from the digest and two contracts differing
    only in year-by-year cap detail would share an identity."""
    mod = _mod()
    spec = _spec()
    base, _ = mod.normalize_rows(
        [dict(r) for r in rows], spec=spec, season=None, identity=identity
    )
    mutated_rows = [dict(r) for r in rows]
    target = next(i for i, r in enumerate(mutated_rows) if r.get("cols"))
    changed = [dict(e) for e in mutated_rows[target]["cols"]]
    changed[0] = {**changed[0], "base_salary": (changed[0]["base_salary"] or 0) + 1.0}
    mutated_rows[target]["cols"] = changed
    mutated, _ = mod.normalize_rows(
        mutated_rows, spec=spec, season=None, identity=identity
    )
    assert {r["content_sha256"] for r in base} != {r["content_sha256"] for r in mutated}, (
        "a change confined to the nested column did not change any row digest"
    )


def test_the_row_key_is_snapshot_id_plus_content_digest(tmp_path, rows, identity) -> None:
    """S3: the composite key required by accumulation was never asserted."""
    import sqlite3

    result = _capture(tmp_path, identity, rows)
    snapshot_id = result["results"][0]["snapshot_id"]
    with sqlite3.connect(tmp_path / "u.db") as conn:
        sample = conn.execute(
            "SELECT row_key, snapshot_id, content_sha256 FROM contracts LIMIT 50"
        ).fetchall()
    assert sample
    for row_key, snap, digest in sample:
        assert snap == snapshot_id
        # T4: substring containment permitted extra coordinates. Pin the exact composition.
        assert row_key == f"{snap}|{digest}", (
            f"row_key {row_key!r} is not exactly snapshot_id|content_sha256"
        )


def test_the_snapshot_digest_is_distinct_from_every_row_digest(
    tmp_path, rows, identity
) -> None:
    """S3: the snapshot-level idempotence digest is a different thing from the per-row hash."""
    mod = _mod()
    spec = _spec()
    normalized, coverage = mod.normalize_rows(
        [dict(r) for r in rows], spec=spec, season=None, identity=identity
    )
    snapshot_digest = mod.snapshot_idempotence_digest(
        spec, rows=normalized, coverage=coverage,
        observed_at="2026-08-05T00:00:00Z", raw_sha256="a" * 64,
    )
    assert len(snapshot_digest) == 64
    assert snapshot_digest not in {r["content_sha256"] for r in normalized}

    # T4: a constant 64-char string would satisfy the above. Require STABILITY on identical
    # inputs and SENSITIVITY to each component.
    same = mod.snapshot_idempotence_digest(
        spec, rows=normalized, coverage=coverage,
        observed_at="2026-08-05T00:00:00Z", raw_sha256="a" * 64,
    )
    assert same == snapshot_digest, "the snapshot digest is not stable on identical inputs"

    variants = {
        "observed_at": dict(observed_at="2026-08-05T00:00:01Z", raw_sha256="a" * 64),
        "raw_sha256": dict(observed_at="2026-08-05T00:00:00Z", raw_sha256="b" * 64),
    }
    for label, kwargs in variants.items():
        assert mod.snapshot_idempotence_digest(
            spec, rows=normalized, coverage=coverage, **kwargs
        ) != snapshot_digest, f"the snapshot digest is insensitive to {label}"

    # G6: the v9 ruling put _projection_fingerprint into the snapshot digest and no test
    # exercised it. A projection change with identical rows and coverage must NOT read as the
    # same observation, or a retry would leave the stored projection stale.
    from dataclasses import replace as _replace

    widened = _replace(spec, columns=(*spec.columns,))
    assert mod.snapshot_idempotence_digest(
        widened, rows=normalized, coverage=coverage,
        observed_at="2026-08-05T00:00:00Z", raw_sha256="a" * 64,
    ) == snapshot_digest, "an identical projection must produce an identical digest"

    narrowed = _replace(spec, integer_columns=())
    assert mod.snapshot_idempotence_digest(
        narrowed, rows=normalized, coverage=coverage,
        observed_at="2026-08-05T00:00:00Z", raw_sha256="a" * 64,
    ) != snapshot_digest, "the snapshot digest is insensitive to the persisted projection"

    bumped = dict(coverage)
    bumped["rows_collapsed_exact_duplicates"] = (
        coverage["rows_collapsed_exact_duplicates"] + 1
    )
    assert mod.snapshot_idempotence_digest(
        spec, rows=normalized, coverage=bumped,
        observed_at="2026-08-05T00:00:00Z", raw_sha256="a" * 64,
    ) != snapshot_digest, "the snapshot digest is insensitive to the collapse count"


def test_the_row_digest_excludes_snapshot_identity(tmp_path, rows, identity) -> None:
    """R3: if snapshot_id leaked into the row hash, identical content in two snapshots would
    produce different digests and accumulation could never be deduplicated or compared."""
    first = _capture(tmp_path, identity, rows)
    second = _capture(tmp_path, identity, rows)
    assert first["results"][0]["snapshot_id"] != second["results"][0]["snapshot_id"]

    import sqlite3

    with sqlite3.connect(tmp_path / "u.db") as conn:
        by_snapshot: dict[str, set] = {}
        for snap, digest in conn.execute(
            "SELECT snapshot_id, content_sha256 FROM contracts"
        ):
            by_snapshot.setdefault(snap, set()).add(digest)
    assert len(by_snapshot) == 2
    digest_sets = list(by_snapshot.values())
    assert digest_sets[0] == digest_sets[1], (
        "identical content produced different row digests across snapshots — snapshot "
        "identity has leaked into the row hash"
    )


def test_an_unequal_payload_on_a_constant_digest_refuses(tmp_path, rows, identity) -> None:
    """A hash collision must fail loudly, never silently overwrite."""
    mod = _mod()
    spec = _spec()
    normalized, coverage = mod.normalize_rows(
        [dict(r) for r in rows], spec=spec, season=None, identity=identity
    )
    forged = [dict(r) for r in normalized]
    forged[1]["content_sha256"] = forged[0]["content_sha256"]
    store = mod.UsageStore(tmp_path / "u.db", (spec,))
    with pytest.raises(mod.UsageCaptureError, match="collision|digest"):
        store.apply_snapshot(
            spec, rows=forged, coverage=coverage, ingested_at="t0", **_snapshot_args()
        )


def test_the_default_fetcher_calls_a_snapshot_loader_with_no_arguments(
    tmp_path, rows, identity
) -> None:
    """R5: the earlier version injected a custom `fetch`, which BYPASSES the default fetcher —
    and the default fetcher is exactly where `seasons=[season]` historically broke
    `load_contracts`. Bind a spy loader onto the real spec and go through `fetch=None`."""
    from dataclasses import replace

    mod = _mod()
    calls: list[tuple] = []

    def spy(*args, **kwargs):
        calls.append((args, kwargs))
        return [dict(r) for r in rows]

    spec = replace(_spec(), loader=spy)
    mod.run_usage_capture(
        seasons=[2024, 2025], specs=(spec,), identity=identity,
        db_path=tmp_path / "u.db", raw_root=tmp_path / "rt",
        fetch=None,
    )
    assert len(calls) == 1, f"expected exactly one loader call per run, got {len(calls)}"
    args, kwargs = calls[0]
    assert args == (), f"a snapshot loader must take no positional arguments; got {args}"
    # S5: forbidding only plural `seasons` let spy(season=None) pass. The contract is ZERO
    # arguments — `load_contracts()` accepts none at all.
    assert kwargs == {}, f"a snapshot loader must be called with no arguments; got {kwargs}"


def _valid_snapshot_kwargs() -> dict:
    """One VALID snapshot spec. Each refusal test mutates exactly one forbidden field, so a
    failure names the field rather than confounding several (R7)."""
    return dict(
        name="probe", table="probe", identity_column="gsis_id", identity_kind="gsis",
        grain=(), columns=("otc_id",), loader=None, loader_kwargs={},
        capture_axis="snapshot",
    )


def test_the_valid_snapshot_probe_spec_constructs() -> None:
    """Control: if this fails, every refusal test below is passing for the wrong reason."""
    assert _mod().StreamSpec(**_valid_snapshot_kwargs()).capture_axis == "snapshot"


@pytest.mark.parametrize(
    "field,value,expect",
    [
        ("capture_axis", "quarterly", "capture_axis"),
        ("min_season", 2022, "min_season"),
        ("loader_kwargs", {"seasons": [2024]}, "seasons"),
        ("require_populated_grain", True, "seasonal"),
        ("nullable_grain_columns", ("otc_id",), "seasonal"),
        # S6: the valid probe now carries NO seasonal grain, so adding one is its own refusal.
        ("grain", ("otc_id",), "grain"),
    ],
)
def test_one_forbidden_field_at_a_time_refuses(field, value, expect) -> None:
    mod = _mod()
    kwargs = _valid_snapshot_kwargs()
    kwargs[field] = value
    with pytest.raises(mod.UsageCaptureError, match=expect):
        mod.StreamSpec(**kwargs)


def test_a_seasonal_spec_cannot_be_routed_through_the_snapshot_path(
    tmp_path, rows, identity
) -> None:
    """R7 cross-route, direction one."""
    mod = _mod()
    with pytest.raises(mod.UsageCaptureError):
        mod.capture_snapshot_stream(
            mod.NGS_PASSING, identity=identity, db_path=tmp_path / "u.db",
            raw_root=tmp_path / "rt", fetch=lambda spec, season=None: [],
        )


def test_a_snapshot_spec_cannot_be_routed_through_the_seasonal_path(
    tmp_path, rows, identity
) -> None:
    """R7 cross-route, direction two."""
    mod = _mod()
    with pytest.raises(mod.UsageCaptureError):
        mod.capture_seasonal_stream(
            _spec(), season=2024, identity=identity, db_path=tmp_path / "u.db",
            raw_root=tmp_path / "rt", fetch=lambda spec, season: [dict(r) for r in rows],
        )


def test_a_snapshot_only_run_with_empty_seasons_succeeds(tmp_path, rows, identity) -> None:
    result = _capture(tmp_path, identity, rows, seasons=[])
    assert result["status"] == "ok"
    assert result["totals"][SNAPSHOT_TOTAL_KEY] == 1


def test_an_empty_source_records_an_explicit_zero(tmp_path, identity) -> None:
    result = _capture(tmp_path, identity, [], fetch=lambda spec, season=None: [])
    assert result["status"] == "ok"
    coverage = result["results"][0]["coverage"]
    assert coverage["rows_total"] == 0
    assert coverage["rows_collapsed_exact_duplicates"] == 0


def test_a_mixed_run_keeps_both_axes_honest(tmp_path, rows, identity) -> None:
    """T6/T7. Two defects fixed here:

    T6 — the seasonal CONTENT claim was `SELECT COUNT(*)`, which any 169 rows satisfy. It now
    compares an exact content hash against a seasonal-ONLY reference capture.

    T7 — the seasonal unresolved assertions sat behind `if "ngs_passing" in by_stream`, which is
    PROVABLY UNREACHABLE: the NGS fixture normalizes to 169 canonical / 0 source_only /
    0 conflict / 0 unknown, so it never enters the unresolved artifact. The branch could never
    execute. One NGS row is now forced non-canonical so BOTH streams must appear, with no
    conditionals.
    """
    import hashlib
    import sqlite3

    import polars as pl

    mod = _mod()
    ngs_all = json.loads(
        (REPO_ROOT / "tests" / "fixtures" / "nflverse_usage_2025_slice.json").read_text()
    )
    ngs = [dict(r) for r in ngs_all["ngs_passing"]]
    # Force exactly one non-canonical seasonal row so the seasonal unresolved path is REAL.
    ngs[0] = {**ngs[0], "player_gsis_id": "00-9999999"}

    def content_hash(db: Path, table: str) -> str:
        with sqlite3.connect(db) as conn:
            payload = conn.execute(f'SELECT * FROM "{table}" ORDER BY row_key').fetchall()
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()

    # Reference: seasonal-only capture of the same content.
    ref = tmp_path / "ref"
    ref.mkdir()
    mod.run_usage_capture(
        seasons=[2025], specs=(mod.NGS_PASSING,), identity=identity,
        db_path=ref / "u.db", raw_root=ref / "rt",
        fetch=lambda spec, season: [dict(r) for r in ngs],
    )
    reference_hash = content_hash(ref / "u.db", "ngs_passing")

    seen: list[tuple] = []

    def fetch(spec, season=None):
        seen.append((spec.name, season))
        return [dict(r) for r in rows] if spec.name == STREAM else [dict(r) for r in ngs]

    mixed = tmp_path / "mixed"
    mixed.mkdir()
    result = mod.run_usage_capture(
        seasons=[2025], specs=(_spec(), mod.NGS_PASSING), identity=identity,
        db_path=mixed / "u.db", raw_root=mixed / "rt", fetch=fetch,
    )
    assert result["status"] == "ok"
    assert result["totals"][SNAPSHOT_TOTAL_KEY] == 1
    assert result["totals"]["stream_seasons"] == 1
    assert sorted(seen) == sorted([(STREAM, None), ("ngs_passing", 2025)]), seen

    # T6: exact content equality with the seasonal-only reference.
    assert content_hash(mixed / "u.db", "ngs_passing") == reference_hash, (
        "the seasonal stream's stored content differs in a mixed run"
    )

    # T7: both streams MUST appear in the unresolved artifact — no conditionals.
    run = sorted((mixed / "rt" / "export" / "runs").iterdir())[-1]
    unresolved = pl.read_parquet(run / "unresolved_identity.parquet").to_dicts()
    by_stream: dict[str, list] = {}
    for row in unresolved:
        by_stream.setdefault(row["stream"], []).append(row)
    assert "ngs_passing" in by_stream, (
        "the forced non-canonical seasonal row did not reach the unresolved artifact"
    )
    assert STREAM in by_stream, "the snapshot stream did not reach the unresolved artifact"

    seasonal_row = by_stream["ngs_passing"][0]
    assert seasonal_row.get("season") is not None, (
        "a seasonal unresolved row lost its season in the mixed artifact"
    )
    snapshot_row = by_stream[STREAM][0]
    assert snapshot_row.get("capture_axis") == "snapshot"
    assert snapshot_row.get("snapshot_id") == result["results"][0]["snapshot_id"]
    assert snapshot_row.get("observed_at") == result["results"][0]["observed_at"]


def test_an_empty_snapshot_is_durable_and_typed(tmp_path, identity) -> None:
    """R8: proving the returned zeros is not proving a durable empty snapshot. The table and a
    correctly-typed Parquet must exist so a consumer sees an empty vintage, not a missing one."""
    import sqlite3

    import polars as pl

    result = _capture(tmp_path, identity, [], fetch=lambda spec, season=None: [])
    assert result["status"] == "ok"
    with sqlite3.connect(tmp_path / "u.db") as conn:
        assert conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='contracts'"
        ).fetchone(), "no durable table for an empty snapshot"
    run = sorted((tmp_path / "rt" / "export" / "runs").iterdir())[-1]
    frame = pl.read_parquet(run / "contracts.parquet")
    assert frame.height == 0
    dtypes = dict(zip(frame.columns, frame.dtypes))
    # S8: typing only the six integers left 19 fields plus the metadata untested.
    for column in (*_spec().columns, "content_sha256", "snapshot_id", "observed_at"):
        assert column in frame.columns, f"an empty snapshot dropped the column {column}"
    for column in EXPECTED_INTEGERS:
        assert dtypes[column] == pl.Int64
    for column in EXPECTED_FLOATS:
        assert dtypes[column] == pl.Float64
    for column in EXPECTED_BOOLEANS:
        assert dtypes[column] == pl.Boolean
    assert dtypes["cols"] == pl.Utf8
    for column in EXPECTED_STRINGS:
        assert dtypes[column] == pl.Utf8, f"empty snapshot: {column} is {dtypes[column]}"
    for column in ("content_sha256", "snapshot_id", "observed_at"):
        assert dtypes[column] == pl.Utf8, f"empty metadata {column} is {dtypes[column]}"


def test_an_export_stage_failure_preserves_the_prior_snapshot_and_recovers(
    tmp_path, rows, identity, monkeypatch
) -> None:
    """R8: v3 required export-stage failure AND recovery; only fetch failure was covered."""
    import polars as pl

    mod = _mod()
    first_result = _capture(tmp_path, identity, rows)
    marker = mod.export_ready_marker_path(tmp_path / "rt" / "export")
    before = marker.read_bytes()

    real = pl.DataFrame.write_parquet
    calls = {"n": 0}

    def flaky(self, *a, **k):
        calls["n"] += 1
        if calls["n"] > 1:
            raise RuntimeError("induced export failure")
        return real(self, *a, **k)

    published_before = {
        f: f.read_bytes()
        for f in sorted((tmp_path / "rt" / "export").rglob("*"))
        if f.is_file()
    }

    monkeypatch.setattr(pl.DataFrame, "write_parquet", flaky)
    with pytest.raises(Exception):
        _capture(tmp_path, identity, rows)
    assert calls["n"] > 1, "the publisher was bypassed; the ordering contract was not exercised"
    assert marker.read_bytes() == before
    # U1: prior PUBLISHED FILES byte-for-byte, which is the cleared guarantee.
    for path, blob in published_before.items():
        assert path.read_bytes() == blob, f"a previously published file changed: {path}"

    # T8: requiring only "the recovery ID is present, counts equal among whatever remains,
    # old_length <= new_length" let a recovery that DELETED prior observations pass. Assert the
    # exact ID sets and per-ID content hashes, and that prior rows are byte-identical.
    import hashlib
    import sqlite3

    def snapshot_hashes(db: Path) -> dict[str, str]:
        with sqlite3.connect(db) as conn:
            conn.row_factory = sqlite3.Row
            out: dict[str, list] = {}
            for row in conn.execute("SELECT * FROM contracts ORDER BY row_key"):
                record = dict(row)
                out.setdefault(record["snapshot_id"], []).append(record)
        return {
            snap: hashlib.sha256(
                json.dumps(recs, sort_keys=True, default=str).encode()
            ).hexdigest()
            for snap, recs in out.items()
        }

    # U1: an earlier version required the failed run's snapshot to DISAPPEAR from the DB.
    # That rollback was never cleared — design v2 keeps failure semantics unchanged (prior READY
    # marker and files stand, the stage is named), and the PFR contract documents that DB writes
    # have already committed before the export begins. Demanding only {first_id} either invents
    # cross-resource rollback or deletes real captured data. INVENTORY instead of prescribing.
    after_failure_hashes = snapshot_hashes(tmp_path / "u.db")
    first_id = first_result["results"][0]["snapshot_id"]
    assert first_id in after_failure_hashes, (
        "the first snapshot must survive a later export failure"
    )

    monkeypatch.setattr(pl.DataFrame, "write_parquet", real)
    recovered = _capture(tmp_path, identity, rows)
    assert recovered["status"] == "ok", "the stream did not recover after an export failure"
    assert marker.read_bytes() != before, "recovery did not advance the marker"

    after_hashes = snapshot_hashes(tmp_path / "u.db")
    recovery_id = recovered["results"][0]["snapshot_id"]

    # Whatever survived the failure must be byte-identical afterwards, and the recovery adds to
    # it rather than replacing it. No claim about WHETHER the failed run's rows persisted.
    assert set(after_hashes) == set(after_failure_hashes) | {recovery_id}, (
        f"recovery changed the durable snapshot set: {sorted(after_failure_hashes)} -> "
        f"{sorted(after_hashes)}"
    )
    for snapshot_id, digest in after_failure_hashes.items():
        assert after_hashes[snapshot_id] == digest, (
            f"recovery mutated already-durable snapshot {snapshot_id}"
        )

    # And every durable snapshot must be fully exported.
    with sqlite3.connect(tmp_path / "u.db") as conn:
        per_snapshot = dict(
            conn.execute("SELECT snapshot_id, COUNT(*) FROM contracts GROUP BY 1")
        )
    assert set(per_snapshot) == set(after_hashes)
    emitted = pl.read_parquet(
        sorted((tmp_path / "rt" / "export" / "runs").iterdir())[-1] / "contracts.parquet"
    )
    assert set(emitted["snapshot_id"].to_list()) == set(per_snapshot), (
        "the recovered export does not cover every durable snapshot"
    )
    assert emitted.height == sum(per_snapshot.values()), (
        "the recovered export does not reflect every durable snapshot"
    )


def test_a_capture_failure_preserves_the_prior_snapshot(tmp_path, rows, identity) -> None:
    mod = _mod()
    _capture(tmp_path, identity, rows)
    marker = mod.export_ready_marker_path(tmp_path / "rt" / "export")
    before = marker.read_bytes()

    def boom(spec, season=None):
        raise RuntimeError("induced")

    with pytest.raises(Exception):
        _capture(tmp_path, identity, rows, fetch=boom)
    assert marker.read_bytes() == before


def test_observed_at_is_stamped_after_the_fetch_returns(tmp_path, rows, identity) -> None:
    """S7 / D4-2. Controlled clock: the fetch records the time it was ENTERED, so a stamp taken
    at run start would be <= it. `observed_at` must be strictly later."""
    from datetime import datetime, timezone

    marks: dict[str, str] = {}

    def slow_fetch(spec, season=None):
        import time

        # T5: an earlier version stamped ENTRY, so a timestamp taken 25ms into a 50ms fetch
        # passed a test named "after the fetch RETURNS". Stamp immediately before returning.
        time.sleep(0.05)
        payload = [dict(r) for r in rows]
        marks["returning"] = datetime.now(timezone.utc).isoformat()
        return payload

    result = _capture(tmp_path, identity, rows, fetch=slow_fetch)
    observed_at = result["results"][0]["observed_at"]
    assert observed_at > marks["returning"], (
        f"observed_at {observed_at} is not after the fetch RETURNED "
        f"({marks['returning']}) — it was stamped at run start or mid-fetch"
    )


def test_the_emitted_parquet_carries_the_snapshot_context(tmp_path, rows, identity) -> None:
    """S7 / D4-5: content_sha256, snapshot_id and observed_at must be STORED AND EMITTED."""
    import polars as pl

    result = _capture(tmp_path, identity, rows)
    entry = result["results"][0]
    run = sorted((tmp_path / "rt" / "export" / "runs").iterdir())[-1]
    frame = pl.read_parquet(run / "contracts.parquet")
    for column in ("content_sha256", "snapshot_id", "observed_at"):
        assert column in frame.columns, f"emitted Parquet lacks {column}"
        assert frame[column].null_count() == 0
    assert set(frame["snapshot_id"].to_list()) == {entry["snapshot_id"]}
    assert set(frame["observed_at"].to_list()) == {entry["observed_at"]}


def test_totals_carry_the_snapshot_vocabulary(tmp_path, rows, identity) -> None:
    """S7: by_stream_snapshot and durable coverage were untested."""
    result = _capture(tmp_path, identity, rows)
    totals = result["totals"]
    assert "by_stream_snapshot" in totals
    assert STREAM in totals["by_stream_snapshot"]
    assert totals["by_stream_snapshot"][STREAM]["rows_total"] == (
        result["results"][0]["coverage"]["rows_total"]
    )


def test_durable_coverage_records_named_snapshot_fields(tmp_path, rows, identity) -> None:
    """Codex v9: redirected to the SEPARATE success-only `nflverse_snapshot_capture` table and
    parsing `coverage_json`. My earlier version queried the shared seasonal ledger and expected
    a `coverage` column — renaming a reviewed column to satisfy my own test was backwards."""
    import sqlite3

    result = _capture(tmp_path, identity, rows)
    entry = result["results"][0]
    with sqlite3.connect(tmp_path / "u.db") as conn:
        conn.row_factory = sqlite3.Row
        ledger = [
            dict(r) for r in conn.execute("SELECT * FROM nflverse_snapshot_capture")
        ]
    assert ledger, "no durable snapshot capture record"
    record = ledger[0]
    assert record["stream"] == STREAM
    assert record["capture_axis"] == "snapshot"
    assert record["snapshot_id"] == entry["snapshot_id"]
    assert record["observed_at"] == entry["observed_at"]
    assert record["raw_sha256"] == entry["raw_sha256"]
    assert record["content_hash"]
    # Success-only by design: no status, no failure_reason, no season.
    assert "status" not in record and "failure_reason" not in record
    assert "season" not in record and "stream_season" not in record

    coverage_blob = json.loads(record["coverage_json"])
    assert coverage_blob["rows_total"] == entry["coverage"]["rows_total"]
    assert coverage_blob["rows_collapsed_exact_duplicates"] == (
        entry["coverage"]["rows_collapsed_exact_duplicates"]
    )

    # And the decoded reader.
    mod = _mod()
    store = mod.UsageStore(tmp_path / "u.db", (_spec(),))
    decoded = store.snapshot_captures()
    assert len(decoded) == 1
    assert decoded[0]["coverage"]["rows_total"] == entry["coverage"]["rows_total"]


def test_the_shared_seasonal_ledger_is_untouched_by_a_snapshot_stream(
    tmp_path, rows, identity
) -> None:
    """Codex v9 SEASONAL FREEZE, asserted narrowly: the shared table's schema is unchanged and
    it receives NO snapshot row, even in a mixed run."""
    import sqlite3

    mod = _mod()
    ngs = json.loads(
        (REPO_ROOT / "tests" / "fixtures" / "nflverse_usage_2025_slice.json").read_text()
    )

    def fetch(spec, season=None):
        return [dict(r) for r in rows] if spec.name == STREAM else ngs[spec.name]

    mod.run_usage_capture(
        seasons=[2025], specs=(_spec(), mod.NGS_PASSING), identity=identity,
        db_path=tmp_path / "u.db", raw_root=tmp_path / "rt", fetch=fetch,
    )
    with sqlite3.connect(tmp_path / "u.db") as conn:
        columns = [r[1] for r in conn.execute("PRAGMA table_info(nflverse_capture)")]
        streams = {r[0] for r in conn.execute("SELECT stream FROM nflverse_capture")}
    assert tuple(columns) == mod._CAPTURE_COLUMNS, (
        f"the shared seasonal ledger schema changed: {columns}"
    )
    assert STREAM not in streams, (
        "a snapshot stream wrote a row into the shared seasonal ledger"
    )
    assert "ngs_passing" in streams


def test_a_snapshot_failure_records_partition_context_and_prior_capture(
    tmp_path, identity, rows
) -> None:
    """U2: an earlier version completed one run, started a NEW run whose FIRST fetch failed, and
    expected that run's `captured_before_failure` to contain historical prior-run state. That
    field is CURRENT-run results, so an immediate first-fetch failure is honestly empty — the
    test demanded behaviour the design never cleared.

    Corrected to ONE MIXED RUN: the snapshot stream succeeds, then a later SEASONAL fetch fails,
    so the same run genuinely has a captured snapshot before its failure.
    """
    import json as _json

    mod = _mod()

    def fetch(spec, season=None):
        if spec.name == STREAM:
            return [dict(r) for r in rows]
        raise RuntimeError("induced seasonal failure after the snapshot succeeded")

    with pytest.raises(Exception):
        mod.run_usage_capture(
            seasons=[2025], specs=(_spec(), mod.NGS_PASSING), identity=identity,
            db_path=tmp_path / "u.db", raw_root=tmp_path / "rt", fetch=fetch,
        )

    marker = _json.loads(mod.status_marker_path(tmp_path / "rt").read_text())
    assert marker["status"] == "failed"
    assert marker["failed_stream"] == "ngs_passing"
    assert marker["failed_stage"] == "capture"

    captured = marker.get("captured_before_failure") or []
    assert captured, "the snapshot succeeded before the failure but was not recorded"
    snapshot_entries = [c for c in captured if c.get("stream") == STREAM]
    assert len(snapshot_entries) == 1, f"expected one snapshot entry, got {captured}"
    entry = snapshot_entries[0]
    assert entry["capture_axis"] == "snapshot"
    assert entry["snapshot_id"]
    assert entry["observed_at"]
    assert entry.get("season") in (None, ""), (
        "a snapshot entry must not carry a season partition"
    )

    import sqlite3

    with sqlite3.connect(tmp_path / "u.db") as conn:
        stored = {
            r[0] for r in conn.execute("SELECT DISTINCT snapshot_id FROM contracts")
        }
    assert stored == {entry["snapshot_id"]}, (
        "the marker's captured snapshot id does not match what is durable"
    )


# ---------------------------------------------------------------------------
# The nested column
# ---------------------------------------------------------------------------


def test_the_nested_column_round_trips_against_the_source_deeply(
    tmp_path, rows, identity
) -> None:
    """Deep-compares EVERY stored list against its SOURCE list, paired by full-source digest."""
    mod = _mod()
    source = [dict(r) for r in rows]
    normalized, _ = mod.normalize_rows(source, spec=_spec(), season=None, identity=identity)

    # T1: an earlier version `continue`d when pairing failed and asserted only compared >= 1,
    # so every other list could be corrupt and it passed. Every normalized row must pair
    # EXACTLY ONCE and the totals must reconcile.
    expected_by_digest: dict[str, dict] = {}
    for row in source:
        expected_by_digest.setdefault(_test_side_digest(_normalized_view(row)), row)

    matched = nulls = 0
    for row in normalized:
        origin = expected_by_digest.get(row["content_sha256"])
        assert origin is not None, (
            f"normalized row {row['content_sha256'][:12]} pairs to no source row"
        )
        expected, stored = origin.get("cols"), row["cols"]
        if expected is None:
            assert stored is None
            nulls += 1
            continue
        parsed = json.loads(stored)
        assert parsed == expected, "nested round-trip diverged"
        assert [e["year"] for e in parsed] == [e["year"] for e in expected]
        for got, want in zip(parsed, expected):
            assert set(got) == set(NESTED_FIELDS)
            for field in NESTED_FIELDS:
                assert got[field] == want[field]
                assert type(got[field]) is type(want[field])
        matched += 1

    assert matched + nulls == len(normalized), "not every normalized row was reconciled"
    assert matched >= 1 and nulls >= 1, "both the populated and null cols paths must run"


def _normalized_view(source_row: dict) -> dict:
    """The source row as the digest should see it: cols as canonical JSON, nothing else."""
    view = dict(source_row)
    if view.get("cols") is not None:
        view["cols"] = json.dumps(
            view["cols"], sort_keys=True, separators=(",", ":"), allow_nan=False
        )
    return view


def test_the_encoder_accepts_a_polars_series_not_only_a_python_list(rows) -> None:
    """R10: the fixture enters as a Python list, so the MEASURED failure path — polars handing
    a Series for a List column — is never exercised by the other tests."""
    import polars as pl

    mod = _mod()
    payload = next(r["cols"] for r in rows if r.get("cols"))
    series = pl.Series("cols", [payload]).explode()
    encoded = mod.encode_nested_json(series)
    assert json.loads(encoded) == payload, "Series conversion must preserve structure and order"


def test_the_encoder_refuses_a_non_json_scalar_rather_than_stringifying(rows) -> None:
    """No `default=` fallback anywhere. An unexpected type RAISES."""
    mod = _mod()
    payload = [dict(e) for e in next(r["cols"] for r in rows if r.get("cols"))]
    payload[0]["base_salary"] = object()
    with pytest.raises((mod.UsageCaptureError, TypeError)):
        mod.encode_nested_json(payload)


def test_a_null_nested_column_is_sql_null_not_the_string_null(
    tmp_path, rows, identity
) -> None:
    mod = _mod()
    normalized, _ = mod.normalize_rows(
        [dict(r) for r in rows], spec=_spec(), season=None, identity=identity
    )
    nulls = [r for r in normalized if r["cols"] is None]
    assert nulls, "the fixture must exercise a null cols row"
    assert not any(r["cols"] == "null" for r in normalized)


def test_a_nested_shape_that_is_not_thirteen_fields_refuses(rows, identity) -> None:
    """Codex: validate the plain value is a list of mappings with exactly 13 fields and
    JSON-compatible types, THEN strict JSON. No fallback coercion."""
    mod = _mod()
    mutated = [dict(r) for r in rows]
    target = next(i for i, r in enumerate(mutated) if r.get("cols"))
    mutated[target]["cols"] = [{"year": "2024"}]
    with pytest.raises(mod.UsageCaptureError, match="nested|cols"):
        mod.normalize_rows(mutated, spec=_spec(), season=None, identity=identity)


def test_a_non_json_compatible_nested_value_refuses(rows, identity) -> None:
    mod = _mod()
    mutated = [dict(r) for r in rows]
    target = next(i for i, r in enumerate(mutated) if r.get("cols"))
    mutated[target]["cols"] = "not a list"
    with pytest.raises(mod.UsageCaptureError, match="nested|cols"):
        mod.normalize_rows(mutated, spec=_spec(), season=None, identity=identity)


def test_year_signed_zero_is_preserved_literally(rows, identity) -> None:
    """1,106 live rows. Preserved, never coerced to null and never interpreted."""
    mod = _mod()
    normalized, _ = mod.normalize_rows(
        [dict(r) for r in rows], spec=_spec(), season=None, identity=identity
    )
    zeros = [r for r in normalized if r.get("year_signed") == 0]
    assert zeros, "the fixture must exercise a year_signed=0 row"


# ---------------------------------------------------------------------------
# Boundary
# ---------------------------------------------------------------------------


def test_landing_contracts_adds_no_engine_consumer() -> None:
    """Contracts are a CANDIDATE signal of UNESTABLISHED value. The prior 'guaranteed money is a
    team's revealed expectation of role' overclaim is exactly what must not recur."""
    # WORD-BOUNDARY matching, not substring. A plain `"CONTRACTS" in text` fired on
    # `HEAD_A_V3_FEATURE_CONTRACTS` in engine_a.py — an unrelated identifier. Codex's R8 pushed
    # the scan WIDER to kill false negatives; overshooting produces false positives, which are
    # just as useless because they train you to ignore the check.
    import re

    patterns = {
        "CONTRACTS": re.compile(r"(?<![A-Za-z0-9_])CONTRACTS(?![A-Za-z0-9_])"),
        "load_contracts": re.compile(r"(?<![A-Za-z0-9_])load_contracts(?![A-Za-z0-9_])"),
        "contracts-table": re.compile(r"""["']contracts["']"""),
    }
    adapter = (REPO_ROOT / "src" / "dynasty_genius" / "nflverse_usage.py").resolve()
    offenders: dict[str, list[str]] = {}
    for root in ("src", "scripts", "app"):
        base = REPO_ROOT / root
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if path.resolve() == adapter:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            hits = [name for name, rx in patterns.items() if rx.search(text)]
            if hits:
                offenders[path.relative_to(REPO_ROOT).as_posix()] = hits

    # POSITIVE CONTROL, both directions: the pattern must MISS the unrelated identifier and
    # HIT a bare reference. A scan that finds nothing is indistinguishable from a broken one.
    assert not patterns["CONTRACTS"].search("HEAD_A_V3_FEATURE_CONTRACTS = {}")
    assert patterns["CONTRACTS"].search("from x import CONTRACTS")
    assert patterns["load_contracts"].search("nflreadpy.load_contracts()")
    assert not offenders, f"contracts referenced outside the adapter: {offenders}"
