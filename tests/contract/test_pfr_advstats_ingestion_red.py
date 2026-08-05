"""RED contract — PFR advanced stats ingestion (Layer 1, board block C, stream 1 of 6).

Framing:     docs/agent-ledger/evidence/2026-08-04/six_loader_batch_framing_claude_v1.md
Disposition: docs/agent-ledger/evidence/2026-08-04/six_loader_batch_disposition_claude_v2.md
Codex CLEAR: docs/agent-ledger/evidence/2026-08-04/six_loader_batch_framing_clear_codex_v3.md
Codex R1-R10: docs/agent-ledger/evidence/2026-08-04/pfr_advstats_red_contract_challenge_codex_v1.md
Fixture generator: docs/agent-ledger/evidence/2026-08-04/build_pfr_fixture_claude_v1.py

WHY THE IMPORTS ARE LAZY. Every symbol under test is unbuilt at RED time. A module-level import of
a missing name is a COLLECTION error, and this repo's standing invariant is ZERO collection errors.
So the module imports lazily inside each test: an unbuilt contract fails as a named test failure and
the tree stays collectable throughout.

MEASURED BASIS (live, `nflreadpy 0.1.5`, 2026-08-04):
  * 2018-2025, four stat types, 121,954 rows.
  * Grain `(game_id, pfr_player_id)`: ZERO duplicate groups, ZERO nulls, all four types.
  * Identity 2018-2025: 121,688 canonical_resolved · 266 source_only · 0 conflict · 0 unknown.
  * Three PFR conflict ids exist in the governed crosswalk GLOBALLY — CartKy01, HarrAl00,
    MillSt00 — and NONE occurs in any 2018-2025 PFR row. This contract pins ZERO conflict rows.
  * Column counts identical in EVERY season 2018-2025: pass 24 · rush 16 · rec 17 · def 29.
    This stream has no eras.

REVISION v2 — Codex contract challenge R1-R10, all accepted. Four of the original tests could not
fail (R4 checked declarations while claiming to check emitted Parquet; R6 was a tautology; R7 caught
any incidental exception; R10 accepted two incompatible semantics). Those are corrected here rather
than argued with.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "pfr_advstats_2024_slice.json"
FIXTURE_MANIFEST = REPO_ROOT / "tests" / "fixtures" / "pfr_advstats_2024_slice_manifest.json"
NGS_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "nflverse_usage_2025_slice.json"
INJURY_SEED = REPO_ROOT / "tests" / "fixtures" / "nflverse_injuries_2024_seed.json"

STREAM_NAMES = ("pfr_pass", "pfr_rush", "pfr_rec", "pfr_def")

#: The five streams already live. S2: an earlier version seeded only the three NGS tables and
#: then filtered on an `ngs_` prefix, so `player_snap_count` and `nflverse_injury_report` were
#: never created OR fingerprinted — two ratified existing-table gates left vacuous while the
#: wire message claimed all five were covered.
EXISTING_STREAM_NAMES = (
    "ngs_passing",
    "ngs_rushing",
    "ngs_receiving",
    "snap_counts",
    "injuries",
)
EXISTING_TABLES = (
    "ngs_passing",
    "ngs_rushing",
    "ngs_receiving",
    "player_snap_count",
    "nflverse_injury_report",
)

EXPECTED_STAT_TYPE = {
    "pfr_pass": "pass",
    "pfr_rush": "rush",
    "pfr_rec": "rec",
    "pfr_def": "def",
}

SHARED_COLUMNS = (
    "game_id",
    "pfr_game_id",
    "season",
    "week",
    "game_type",
    "team",
    "opponent",
    "pfr_player_name",
    "pfr_player_id",
)

#: R9: pinned INDEPENDENTLY from the live measurement, never derived from the fixture under test.
#: A contract that reads its expectation out of the artifact it is validating proves only that the
#: artifact equals itself.
EXPECTED_COLUMNS: dict[str, tuple[str, ...]] = {
    "pfr_pass": SHARED_COLUMNS
    + (
        "passing_drops",
        "passing_drop_pct",
        "receiving_drop",
        "receiving_drop_pct",
        "passing_bad_throws",
        "passing_bad_throw_pct",
        "times_sacked",
        "times_blitzed",
        "times_hurried",
        "times_hit",
        "times_pressured",
        "times_pressured_pct",
        "def_times_blitzed",
        "def_times_hurried",
        "def_times_hitqb",
    ),
    "pfr_rush": SHARED_COLUMNS
    + (
        "carries",
        "rushing_yards_before_contact",
        "rushing_yards_before_contact_avg",
        "rushing_yards_after_contact",
        "rushing_yards_after_contact_avg",
        "rushing_broken_tackles",
        "receiving_broken_tackles",
    ),
    "pfr_rec": SHARED_COLUMNS
    + (
        "rushing_broken_tackles",
        "receiving_broken_tackles",
        "passing_drops",
        "passing_drop_pct",
        "receiving_drop",
        "receiving_drop_pct",
        "receiving_int",
        "receiving_rat",
    ),
    "pfr_def": SHARED_COLUMNS
    + (
        "def_ints",
        "def_targets",
        "def_completions_allowed",
        "def_completion_pct",
        "def_yards_allowed",
        "def_yards_allowed_per_cmp",
        "def_yards_allowed_per_tgt",
        "def_receiving_td_allowed",
        "def_passer_rating_allowed",
        "def_adot",
        "def_air_yards_completed",
        "def_yards_after_catch",
        "def_times_blitzed",
        "def_times_hurried",
        "def_times_hitqb",
        "def_sacks",
        "def_pressures",
        "def_tackles_combined",
        "def_missed_tackles",
        "def_missed_tackle_pct",
    ),
}

EXPECTED_COLUMN_COUNT = {"pfr_pass": 24, "pfr_rush": 16, "pfr_rec": 17, "pfr_def": 29}

KNOWN_GLOBAL_PFR_CONFLICT_IDS = {"CartKy01", "HarrAl00", "MillSt00"}

#: R5: the GOVERNED coverage vocabulary, read from `_coverage` at nflverse_usage.py:711-741.
#: An earlier draft invented `rows_ingested` / `rows_canonically_identified` / `rows_conflicted` /
#: `rows_unknown_identity` and would have forced an unauthorized batch-wide rename.
COVERAGE_TOTAL = "rows_total"
COVERAGE_PARTS = (
    "rows_canonical_resolved",
    "rows_source_only",
    "rows_conflict",
    "rows_unknown",
)


def _mod():
    from src.dynasty_genius import nflverse_usage

    return nflverse_usage


def _spec(name: str):
    mod = _mod()
    attr = name.upper()
    spec = getattr(mod, attr, None)
    if spec is None:
        pytest.fail(
            f"{attr} is not defined in nflverse_usage. The PFR advanced-stats contract "
            f"declares four StreamSpecs: {', '.join(n.upper() for n in STREAM_NAMES)}."
        )
    return spec


def _specs() -> tuple[Any, ...]:
    return tuple(_spec(n) for n in STREAM_NAMES)


@pytest.fixture(scope="module")
def fixture_payload() -> dict[str, list[dict[str, Any]]]:
    if not FIXTURE.exists():
        pytest.fail(f"missing real fixture slice: {FIXTURE}")
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fixture_manifest() -> dict[str, Any]:
    if not FIXTURE_MANIFEST.exists():
        pytest.fail(
            f"missing fixture provenance manifest: {FIXTURE_MANIFEST}. Regenerate with "
            "docs/agent-ledger/evidence/2026-08-04/build_pfr_fixture_claude_v1.py"
        )
    return json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def identity():
    return _mod().IdentityIndex.from_governed_crosswalk()


@pytest.fixture()
def harness(fixture_payload):
    def fetch(spec, season: int):
        return fixture_payload[spec.name]

    return fetch


def _run(tmp_path: Path, harness, identity, **overrides) -> dict[str, Any]:
    kwargs = {
        "seasons": [2024],
        "specs": _specs(),
        "identity": identity,
        "db_path": tmp_path / "usage.db",
        "raw_root": tmp_path / "runtime",
        "fetch": harness,
        **overrides,
    }
    return _mod().run_usage_capture(**kwargs)


def _table_fingerprints(db_path: Path) -> dict[str, tuple[int, str]]:
    """Row count plus a content hash for every table — counts alone miss a mutation."""
    out: dict[str, tuple[int, str]] = {}
    with sqlite3.connect(db_path) as conn:
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ]
        for table in tables:
            rows = conn.execute(f'SELECT * FROM "{table}"').fetchall()
            blob = json.dumps(rows, sort_keys=True, default=str).encode("utf-8")
            out[table] = (len(rows), hashlib.sha256(blob).hexdigest())
    return out


# ---------------------------------------------------------------------------
# Premise — the fixture is real AND its provenance is checkable (R9)
# ---------------------------------------------------------------------------


def test_the_fixture_carries_generator_provenance_not_just_self_agreement(
    fixture_payload, fixture_manifest
) -> None:
    """R9: an earlier version asserted 'the fixture is real' by checking its own counts and id
    prefixes — self-referential. The manifest records upstream row counts, an upstream sha256,
    the selection rule's outcome, and the identity census per stream.
    """
    assert set(fixture_manifest) == set(STREAM_NAMES)
    for name in STREAM_NAMES:
        entry = fixture_manifest[name]
        assert entry["stat_type"] == EXPECTED_STAT_TYPE[name]
        assert entry["season"] == 2024
        assert len(entry["upstream_sha256"]) == 64
        assert entry["upstream_rows"] > entry["slice_rows"], "a slice must be a subset"
        assert entry["n_columns"] == EXPECTED_COLUMN_COUNT[name]
        assert entry["slice_rows"] == len(fixture_payload[name]), (
            f"{name}: manifest and fixture disagree on row count"
        )


def test_the_slice_selection_rule_is_recorded_including_the_appended_rows(
    fixture_payload, fixture_manifest
) -> None:
    """R9: the prose said 'two whole games per stat type'. That was FALSE for two streams —
    `pfr_def` carries an appended row from 2024_01_PIT_ATL and `pfr_rec` one from
    2024_02_CIN_KC, added so the unresolved-identity path is exercised. The rule is now
    recorded per stream and asserted rather than described.
    """
    for name in STREAM_NAMES:
        entry = fixture_manifest[name]
        observed_games = {r["game_id"] for r in fixture_payload[name]}
        expected_games = set(entry["base_games"])
        appended = entry["appended_unresolved_row_from_game"]
        if appended:
            expected_games.add(appended)
        assert observed_games == expected_games, (
            f"{name}: games in the slice do not match the recorded selection rule"
        )
        # If a row was appended, it must be the reason: an unresolved id must be present.
        if appended:
            assert entry["identity_census"].get("source_only", 0) >= 1


def test_the_fixture_rows_are_real_not_synthetic(fixture_payload) -> None:
    for name in STREAM_NAMES:
        rows = fixture_payload[name]
        assert rows, f"{name} slice is empty"
        assert len(rows[0]) == EXPECTED_COLUMN_COUNT[name]
        assert all(r["game_id"].startswith("2024_") for r in rows)
        assert all(r["pfr_player_id"] for r in rows)


# ---------------------------------------------------------------------------
# The declared contract
# ---------------------------------------------------------------------------


def test_four_streams_are_declared_one_per_stat_type() -> None:
    specs = _specs()
    assert len({s.name for s in specs}) == 4
    assert len({s.table for s in specs}) == 4, "each stat type needs its own table"


def test_the_default_build_streams_registers_all_four_exactly_once() -> None:
    """R1 — THE HOLE THAT LET EVERYTHING ELSE PASS.

    Every other test injects `specs=_specs()`. The module constants could therefore be perfect
    while `build_streams()` (nflverse_usage.py:510-537) never discovers or binds them, so the
    real capture path would ingest nothing and the suite would stay green.
    """
    import nflreadpy

    built = _mod().build_streams()
    names = [s.name for s in built]
    for name in STREAM_NAMES:
        assert names.count(name) == 1, (
            f"{name} is registered {names.count(name)} times by build_streams(); expected "
            "exactly once"
        )
    by_name = {s.name: s for s in built}
    for name in STREAM_NAMES:
        spec = by_name[name]
        # S1: `loader is not None` was too weak — a GREEN binding all four to
        # `load_nextgen_stats` would have passed while the test claimed binding was proved.
        assert spec.loader is nflreadpy.load_pfr_advstats, (
            f"{name} is bound to {getattr(spec.loader, '__name__', spec.loader)!r}; "
            "expected nflreadpy.load_pfr_advstats"
        )
        assert spec.loader_kwargs.get("stat_type") == EXPECTED_STAT_TYPE[name]


def test_the_default_registration_does_not_displace_the_existing_streams() -> None:
    """Adding four specs must not drop, rename, OR duplicate the five already live.

    S1: an earlier version reduced names to a set, so a duplicate existing registration was
    invisible. Count them.
    """
    names = [s.name for s in _mod().build_streams()]
    for existing in EXISTING_STREAM_NAMES:
        assert names.count(existing) == 1, (
            f"build_streams() registers the existing stream {existing} "
            f"{names.count(existing)} times; expected exactly once"
        )


def test_each_stream_declares_its_stat_type_explicitly() -> None:
    """The loader DEFAULTS `stat_type`; an omitted kwarg silently loads the wrong stream —
    exactly how NGS receiving once shipped passing rows (`nflverse_usage.py:386-389`)."""
    for name in STREAM_NAMES:
        spec = _spec(name)
        assert spec.loader_kwargs.get("stat_type") == EXPECTED_STAT_TYPE[name], (
            f"{name} must pin stat_type={EXPECTED_STAT_TYPE[name]!r}; "
            f"got {dict(spec.loader_kwargs)!r}"
        )


def test_the_declared_grain_is_game_id_and_player() -> None:
    for name in STREAM_NAMES:
        assert _spec(name).grain == ("game_id", "pfr_player_id")


def test_identity_is_the_pfr_bridge_not_a_gsis_assumption() -> None:
    for name in STREAM_NAMES:
        spec = _spec(name)
        assert spec.identity_column == "pfr_player_id"
        assert spec.identity_kind == "pfr"


def test_declared_columns_match_the_independently_pinned_live_shape() -> None:
    """R9: expectations come from `EXPECTED_COLUMNS`, measured live and written here — NOT read
    out of the fixture this suite is also validating."""
    for name in STREAM_NAMES:
        spec = _spec(name)
        assert set(spec.columns) == set(EXPECTED_COLUMNS[name]), (
            f"{name} declared columns diverge from the pinned live shape: "
            f"undeclared {sorted(set(EXPECTED_COLUMNS[name]) - set(spec.columns))}, "
            f"extra {sorted(set(spec.columns) - set(EXPECTED_COLUMNS[name]))}"
        )


def test_the_pinned_shape_still_matches_the_committed_fixture(fixture_payload) -> None:
    """Cross-check in the other direction: if upstream moves, this fails and names it."""
    for name in STREAM_NAMES:
        assert set(fixture_payload[name][0]) == set(EXPECTED_COLUMNS[name]), (
            f"{name}: the committed fixture no longer matches the pinned live shape; "
            "regenerate with build_pfr_fixture_claude_v1.py and re-review"
        )


def test_season_and_week_are_declared_as_integers() -> None:
    for name in STREAM_NAMES:
        spec = _spec(name)
        assert "season" in spec.integer_columns
        assert "week" in spec.integer_columns


def test_every_metric_column_is_declared_with_a_type() -> None:
    for name in STREAM_NAMES:
        spec = _spec(name)
        typed = set(spec.integer_columns) | set(spec.float_columns)
        metrics = set(spec.columns) - set(SHARED_COLUMNS)
        assert metrics <= typed, f"{name} leaves {sorted(metrics - typed)} untyped"


# ---------------------------------------------------------------------------
# Identity — the corrected census
# ---------------------------------------------------------------------------


def test_no_pfr_row_in_this_range_carries_conflict_status(fixture_payload, identity) -> None:
    mod = _mod()
    for name in STREAM_NAMES:
        for row in fixture_payload[name]:
            _, status = identity.resolve(row["pfr_player_id"], kind="pfr")
            assert status != mod.CONFLICT, (
                f"{name}: {row['pfr_player_id']} resolved to CONFLICT; the measured "
                "2018-2025 range carries zero conflict rows"
            )


def test_the_global_bridge_conflicts_exist_but_do_not_appear_here(
    fixture_payload, identity
) -> None:
    assert set(identity.pfr_conflicts) == KNOWN_GLOBAL_PFR_CONFLICT_IDS
    observed = {r["pfr_player_id"] for n in STREAM_NAMES for r in fixture_payload[n]}
    assert not (observed & KNOWN_GLOBAL_PFR_CONFLICT_IDS)


def test_an_unresolved_player_is_source_only_never_silently_canonical(
    fixture_payload, identity
) -> None:
    mod = _mod()
    seen = False
    for name in STREAM_NAMES:
        for row in fixture_payload[name]:
            resolved, status = identity.resolve(row["pfr_player_id"], kind="pfr")
            if status == mod.SOURCE_ONLY:
                seen = True
                assert resolved is None
    assert seen, "fixture must exercise the unresolved path, not just the happy one"


def test_coverage_uses_the_governed_vocabulary_and_reconciles(
    tmp_path, harness, identity
) -> None:
    """R5: assert against the EXISTING keys from `_coverage` (:711-741), not invented ones."""
    result = _run(tmp_path, harness, identity)
    for entry in result["results"]:
        cov = entry["coverage"]
        missing = [k for k in (COVERAGE_TOTAL, *COVERAGE_PARTS) if k not in cov]
        assert not missing, f"{entry['stream']} coverage lacks governed keys {missing}"
        assert sum(cov[k] for k in COVERAGE_PARTS) == cov[COVERAGE_TOTAL], (
            f"{entry['stream']} coverage does not reconcile: {cov}"
        )
        assert cov["rows_conflict"] == 0
        assert cov["rows_not_canonically_identified"] == (
            cov["rows_source_only"] + cov["rows_conflict"] + cov["rows_unknown"]
        )


# ---------------------------------------------------------------------------
# Falsification matrix — refusals
# ---------------------------------------------------------------------------


def test_a_duplicate_at_the_declared_grain_refuses(fixture_payload, identity) -> None:
    mod = _mod()
    spec = _spec("pfr_rec")
    rows = list(fixture_payload["pfr_rec"])
    with pytest.raises(mod.UsageCaptureError, match="duplicate"):
        mod.normalize_rows([*rows, dict(rows[0])], spec=spec, season=2024, identity=identity)


def test_a_missing_declared_column_refuses_by_name(fixture_payload, identity) -> None:
    mod = _mod()
    spec = _spec("pfr_rush")
    stripped = [
        {k: v for k, v in row.items() if k != "carries"}
        for row in fixture_payload["pfr_rush"]
    ]
    with pytest.raises(mod.UsageCaptureError, match="carries"):
        mod.normalize_rows(stripped, spec=spec, season=2024, identity=identity)


def test_an_additive_provider_column_refuses_rather_than_being_dropped(
    fixture_payload, identity
) -> None:
    """G1, verified at `nflverse_usage.py:571` and `:618`. Exact column-set equality runs ONLY
    when `spec.eras` is non-empty; a non-era spec checks for MISSING columns then projects the
    declared ones, so a NEW upstream field is accepted and silently discarded."""
    mod = _mod()
    spec = _spec("pfr_rec")
    augmented = [{**row, "receiving_air_yards": 1.0} for row in fixture_payload["pfr_rec"]]
    with pytest.raises(mod.UsageCaptureError, match="receiving_air_yards"):
        mod.normalize_rows(augmented, spec=spec, season=2024, identity=identity)


def test_a_heterogeneous_batch_refuses(fixture_payload, identity) -> None:
    mod = _mod()
    spec = _spec("pfr_rec")
    rows = [dict(r) for r in fixture_payload["pfr_rec"]]
    rows[-1]["unexpected_late_field"] = 1
    with pytest.raises(mod.UsageCaptureError):
        mod.normalize_rows(rows, spec=spec, season=2024, identity=identity)


def test_an_empty_loader_result_records_an_explicit_zero_per_stream(
    tmp_path, identity
) -> None:
    """R6 — the previous assertion was a TAUTOLOGY: after asserting every row count was zero it
    allowed `status == ok` whenever ANY row was zero, so it always passed.

    Contract chosen and stated: an all-empty capture SUCCEEDS but must record an EXPLICIT zero
    for every stream, with the governed coverage keys present. 'Silence is not success' means the
    zero is legible per stream — not that the run must fail.
    """
    def empty_fetch(spec, season):
        return []

    result = _run(tmp_path, empty_fetch, identity)

    # S5: the chosen semantics said "succeeds", but nothing asserted the status, so a failed or
    # degraded run carrying four component zeros would have passed. Pin it.
    assert result.get("status") == "ok", (
        f"the chosen contract is that an all-empty capture SUCCEEDS; got {result.get('status')!r}"
    )
    reported = {e["stream"] for e in result["results"]}
    assert reported == set(STREAM_NAMES), (
        f"an empty capture must still report every stream; got {sorted(reported)}"
    )
    for entry in result["results"]:
        cov = entry["coverage"]
        assert cov[COVERAGE_TOTAL] == 0
        for key in COVERAGE_PARTS:
            assert key in cov, f"{entry['stream']} drops {key} when empty"
            assert cov[key] == 0
        # The derived governed count, not only its components (S5).
        assert cov["rows_not_canonically_identified"] == 0


def test_a_wrong_record_type_refuses_with_the_defined_boundary_error(
    tmp_path, identity
) -> None:
    """R7 — the previous version accepted a bare AttributeError/TypeError with no reason, so any
    incidental crash passed it. Pin the module's own boundary exception and a deterministic
    reason naming the offending shape."""
    mod = _mod()

    def bad_fetch(spec, season):
        return ["not a mapping", 42]

    with pytest.raises(mod.UsageCaptureError, match="record"):
        _run(tmp_path, bad_fetch, identity)


def test_a_non_finite_metric_refuses(fixture_payload, identity) -> None:
    """R10 — the previous version accepted refusal OR a lossy null, two incompatible semantics,
    so it could not fail. REFUSAL is chosen: the export contract already refuses loss of non-null
    values (`nflverse_usage.py:1223-1247`), so silently nulling an inf here would contradict it.
    Nulling would need explicit loss accounting and its own authority.
    """
    mod = _mod()
    spec = _spec("pfr_rec")
    for bad in (float("inf"), float("-inf"), float("nan")):
        rows = [dict(r) for r in fixture_payload["pfr_rec"]]
        rows[0]["receiving_rat"] = bad
        with pytest.raises(mod.UsageCaptureError):
            mod.normalize_rows(rows, spec=spec, season=2024, identity=identity)


# ---------------------------------------------------------------------------
# Provenance (Codex C6 / G2)
# ---------------------------------------------------------------------------


def test_the_raw_snapshot_is_recorded_with_a_sha256_not_only_a_path(
    tmp_path, harness, identity
) -> None:
    """The reduced per-stream gate requires 'raw snapshot + manifest/hash'. Today
    `write_raw_snapshot` returns a path and the result records only that path (:1524-1548), so
    export hashes never prove the PRE-PARSE snapshot."""
    result = _run(tmp_path, harness, identity)
    for entry in result["results"]:
        assert "raw_sha256" in entry, (
            f"{entry['stream']} records no raw_sha256 — the reduced gate requires a "
            "manifest/hash over the pre-parse snapshot"
        )
        digest = hashlib.sha256(Path(entry["raw_snapshot"]).read_bytes()).hexdigest()
        assert entry["raw_sha256"] == digest


# ---------------------------------------------------------------------------
# Emitted artifact typing (R4) — the Parquet itself, not the declaration
# ---------------------------------------------------------------------------


def test_the_emitted_parquet_is_typed_at_runtime_not_merely_declared(
    tmp_path, harness, identity, fixture_payload
) -> None:
    """R4 — the previous test inspected `spec.integer_columns` while the matrix claimed the
    EMITTED Parquet is never Utf8. Declaration is not emission; that test passed for the wrong
    reason. This reads the four published Parquet files and asserts their runtime dtypes.
    """
    import polars as pl

    raw_root = tmp_path / "runtime"
    _run(tmp_path, harness, identity, raw_root=raw_root)

    export_root = raw_root / "export"
    parquets = {p.stem: p for p in export_root.rglob("*.parquet")}
    for name in STREAM_NAMES:
        spec = _spec(name)
        candidates = [k for k in parquets if name in k or spec.table in k]
        assert candidates, (
            f"no published Parquet found for {name}; saw {sorted(parquets)}"
        )
        frame = pl.read_parquet(parquets[candidates[0]])
        dtypes = dict(zip(frame.columns, frame.dtypes))
        for column in spec.integer_columns:
            assert dtypes.get(column) == pl.Int64, (
                f"{name}.{column} published as {dtypes.get(column)}, expected Int64"
            )
        for column in spec.float_columns:
            assert dtypes.get(column) == pl.Float64, (
                f"{name}.{column} published as {dtypes.get(column)}, expected Float64"
            )

        # S4: reconciling only `season`/`week` let a publisher emit correctly-typed Float64
        # metric columns while nulling every metric VALUE. Compare EXACT non-null counts
        # against the source for every declared numeric column. Exact counts, not
        # "must be non-null": the fixture legitimately carries some all-null metric columns,
        # and demanding non-emptiness would bake a false expectation into the contract.
        source_rows = fixture_payload[name]
        for column in (*spec.integer_columns, *spec.float_columns):
            expected_non_null = sum(
                1 for row in source_rows if row.get(column) is not None
            )
            emitted_non_null = frame.height - frame[column].null_count()
            assert emitted_non_null == expected_non_null, (
                f"{name}.{column} published {emitted_non_null} non-null values but the "
                f"source carries {expected_non_null} — the cast lost or invented data"
            )


# ---------------------------------------------------------------------------
# Durability — last-good survives BOTH failure stages (R3)
# ---------------------------------------------------------------------------


def _seed_existing_streams(identity, db_path: Path, raw_root: Path):
    """Populate ALL FIVE pre-existing tables so 'unchanged' is a real claim (S2).

    The NGS fixture supplies four streams; injuries has its own real seed generated by
    `build_pfr_fixture_claude_v1.py`. Injuries is captured in a second run because its rows are
    2024 while the NGS slice is 2025 — one run has one season list.
    """
    mod = _mod()
    payload = json.loads(NGS_FIXTURE.read_text(encoding="utf-8"))
    injuries = json.loads(INJURY_SEED.read_text(encoding="utf-8"))

    mod.run_usage_capture(
        seasons=[2025],
        specs=(mod.NGS_PASSING, mod.NGS_RUSHING, mod.NGS_RECEIVING, mod.SNAP_COUNTS),
        identity=identity,
        db_path=db_path,
        raw_root=raw_root,
        fetch=lambda spec, season: payload[spec.name],
    )
    mod.run_usage_capture(
        seasons=[2024],
        specs=(mod.INJURIES,),
        identity=identity,
        db_path=db_path,
        raw_root=raw_root,
        fetch=lambda spec, season: injuries,
    )


def test_landing_pfr_leaves_all_five_existing_tables_byte_identical(
    tmp_path, harness, identity
) -> None:
    """R2/S2 — board block C makes 'existing-table counts unchanged' a per-stream gate.

    Every earlier version ran PFR against an EMPTY database, so the gate was never exercised;
    the first revision then covered only three of the five tables. All five are now seeded with
    real rows, each asserted non-empty first so the guard cannot pass vacuously, and compared by
    row count AND content hash.
    """
    db_path = tmp_path / "usage.db"
    raw_root = tmp_path / "runtime"

    _seed_existing_streams(identity, db_path, raw_root)
    before = _table_fingerprints(db_path)

    seeded = {t: before[t] for t in EXISTING_TABLES if t in before}
    missing = [t for t in EXISTING_TABLES if t not in before]
    assert not missing, f"seeding did not create {missing} — the guard would be vacuous"
    for table, (count, _) in seeded.items():
        assert count > 0, f"{table} seeded empty — its preservation check proves nothing"

    _run(tmp_path, harness, identity, db_path=db_path, raw_root=raw_root)

    after = _table_fingerprints(db_path)
    for table, fingerprint in seeded.items():
        assert table in after, f"landing PFR dropped the existing table {table}"
        assert after[table] == fingerprint, (
            f"landing PFR mutated the existing table {table}: "
            f"{fingerprint} -> {after[table]}"
        )


def test_a_capture_stage_failure_preserves_the_prior_ready_marker_and_files(
    tmp_path, harness, identity
) -> None:
    mod = _mod()
    db_path = tmp_path / "usage.db"
    raw_root = tmp_path / "runtime"
    _run(tmp_path, harness, identity, db_path=db_path, raw_root=raw_root)

    export_root = raw_root / "export"
    marker = mod.export_ready_marker_path(export_root)
    before_marker = marker.read_bytes()
    before_files = {p: p.read_bytes() for p in sorted(export_root.rglob("*")) if p.is_file()}

    def failing_fetch(spec, season):
        if spec.name == "pfr_def":
            raise RuntimeError("induced upstream failure")
        return harness(spec, season)

    with pytest.raises(Exception):
        _run(tmp_path, failing_fetch, identity, db_path=db_path, raw_root=raw_root)

    assert marker.read_bytes() == before_marker
    after_files = {p: p.read_bytes() for p in sorted(export_root.rglob("*")) if p.is_file()}
    for path, blob in before_files.items():
        assert path in after_files, f"a previously published file vanished: {path}"
        assert after_files[path] == blob, f"a published file changed bytes: {path}"


def test_an_export_stage_failure_preserves_the_prior_ready_marker_and_files(
    tmp_path, harness, identity, monkeypatch
) -> None:
    """R3 — disposition v2 required BOTH stages and the RED only induced a fetch failure. An
    export-stage failure is the more dangerous one: every DB write has already committed."""
    mod = _mod()
    db_path = tmp_path / "usage.db"
    raw_root = tmp_path / "runtime"
    _run(tmp_path, harness, identity, db_path=db_path, raw_root=raw_root)

    export_root = raw_root / "export"
    marker = mod.export_ready_marker_path(export_root)
    before_marker = marker.read_bytes()
    before_files = {p: p.read_bytes() for p in sorted(export_root.rglob("*")) if p.is_file()}

    # S3: replacing `publish_export` wholesale meant NO export work ran, so the ordering
    # contract — "the ready marker is written LAST, after every Parquet for the run has
    # landed" — was never exercised. Fail INSIDE the real publisher instead: let the first
    # Parquet write succeed, then raise. A partial run directory now exists on disk, which is
    # precisely the state in which a wrongly-ordered publisher would already have clobbered
    # the marker.
    import polars as pl

    real_write = pl.DataFrame.write_parquet
    calls = {"n": 0}

    def flaky_write(self, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] > 1:
            raise RuntimeError("induced export failure after the first artifact landed")
        return real_write(self, *args, **kwargs)

    monkeypatch.setattr(pl.DataFrame, "write_parquet", flaky_write)

    with pytest.raises(Exception):
        _run(tmp_path, harness, identity, db_path=db_path, raw_root=raw_root)

    assert calls["n"] > 1, (
        "the induced failure never reached a second artifact write — the publisher was "
        "bypassed and the ordering contract was not exercised"
    )
    assert marker.read_bytes() == before_marker, "the prior ready marker changed"
    after_files = {p: p.read_bytes() for p in sorted(export_root.rglob("*")) if p.is_file()}
    for path, blob in before_files.items():
        assert path in after_files, f"a previously published file vanished: {path}"
        assert after_files[path] == blob, f"a published file changed bytes: {path}"


def test_normalization_is_deterministic_on_replay(fixture_payload, identity) -> None:
    mod = _mod()
    spec = _spec("pfr_rec")
    rows_a, cov_a = mod.normalize_rows(
        [dict(r) for r in fixture_payload["pfr_rec"]],
        spec=spec,
        season=2024,
        identity=identity,
    )
    rows_b, cov_b = mod.normalize_rows(
        [dict(r) for r in fixture_payload["pfr_rec"]],
        spec=spec,
        season=2024,
        identity=identity,
    )
    assert rows_a == rows_b
    assert cov_a == cov_b


# ---------------------------------------------------------------------------
# Boundary — substrate_only
# ---------------------------------------------------------------------------


def test_landing_pfr_adds_no_engine_consumer() -> None:
    """R8 — the previous scan looked for uppercase constants only, so a consumer reading the
    `pfr_rec` SQL table, a `pfr_pass.parquet` file, or calling `load_pfr_advstats` directly all
    passed it. Scan the concrete lowercase identifiers and the loader name too.

    Pure Python on purpose: an earlier draft shelled out to `rg`, absent from CI.
    """
    symbols = (
        *(n.upper() for n in STREAM_NAMES),
        *STREAM_NAMES,
        "load_pfr_advstats",
    )
    adapter = (REPO_ROOT / "src" / "dynasty_genius" / "nflverse_usage.py").resolve()

    offenders: dict[str, list[str]] = {}
    for root in ("src", "scripts", "app"):
        base = REPO_ROOT / root
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if path.resolve() == adapter:
                continue  # ONLY the exact adapter is exempt
            text = path.read_text(encoding="utf-8", errors="ignore")
            hits = [s for s in symbols if s in text]
            if hits:
                offenders[path.relative_to(REPO_ROOT).as_posix()] = hits

    assert not offenders, (
        f"PFR identifiers are referenced outside the adapter: {offenders}. This stream is "
        "substrate_only and no consumer is authorized."
    )
