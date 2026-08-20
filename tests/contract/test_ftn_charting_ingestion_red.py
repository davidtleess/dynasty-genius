"""RED contract — FTN charting ingestion (Layer 1, board block C, stream 3 of 6).

Fixture generator: `tests/fixture_generators/build_ftn_charting_fixture.py`

SCOPE. Shared capture mechanics are contracted by the PFR RED and not re-litigated. This file
contracts the two things unique to FTN:

  1. IDENTITY IS NOT APPLICABLE. This stream is play-grain and has NO player column of any kind.
     Codex C7: a nullable identity column alone would report all 143,572 plays as unresolved
     PLAYERS and bury the real unresolved-player artifact. Non-applicable rows must therefore
     carry a status distinct from `unknown`, report `identity_applicable_rows = 0`, must NOT
     inflate `rows_not_canonically_identified`, and must NOT enter `unresolved_identity.parquet`.
  2. BOOLEANS MUST SURVIVE THE ROUND TRIP. 15 of 29 columns are Boolean. SQLite has no Boolean
     type and holds them as TEXT '0'/'1' (measured), and polars refuses Utf8 -> Boolean outright.
     Published as text, `"false"` is a TRUTHY string — that is how a charting flag silently
     inverts.

MEASURED LIVE 2026-08-04 (`nflreadpy 0.1.5`): 2022-2025, 29 columns in every season (charting
begins 2022). Grain `(nflverse_game_id, nflverse_play_id)` 143,572/143,572 unique with zero nulls
over 2023-2025. Staging capture of 2023-2024: 96,256 rows, unresolved_identity.parquet EMPTY,
is_motion published Boolean 61,158 False / 35,098 True, 10 genuine source nulls in is_trick_play
(the export's non-null reconciliation did not fire, proving they are source nulls not cast loss).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "ftn_charting_2024_slice.json"
FIXTURE_MANIFEST = REPO_ROOT / "tests" / "fixtures" / "ftn_charting_2024_slice_manifest.json"

STREAM = "ftn_charting"
EXPECTED_COLUMN_COUNT = 29
EXPECTED_BOOLEAN_COUNT = 15
PLAYER_COLUMN_NAMES = ("gsis_id", "player_id", "pfr_player_id", "player", "player_name",
                       "player_display_name", "full_name")


def _mod():
    from src.dynasty_genius import nflverse_usage

    return nflverse_usage


def _spec():
    spec = getattr(_mod(), "FTN_CHARTING", None)
    if spec is None:
        pytest.fail("FTN_CHARTING is not defined in nflverse_usage")
    return spec


@pytest.fixture(scope="module")
def rows() -> list[dict[str, Any]]:
    if not FIXTURE.exists():
        pytest.fail(f"missing real fixture slice: {FIXTURE}")
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest() -> dict[str, Any]:
    if not FIXTURE_MANIFEST.exists():
        pytest.fail(f"missing provenance manifest: {FIXTURE_MANIFEST}")
    return json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def identity():
    return _mod().IdentityIndex.from_governed_crosswalk()


# ---------------------------------------------------------------------------
# Provenance and premise
# ---------------------------------------------------------------------------


def test_the_fixture_carries_checkable_provenance(rows, manifest) -> None:
    assert manifest["n_columns"] == EXPECTED_COLUMN_COUNT
    assert len(manifest["upstream_sha256"]) == 64
    assert manifest["nflreadpy_version"]
    assert manifest["upstream_rows"] > manifest["slice_rows"] == len(rows)
    assert manifest["grain_is_unique"] is True
    assert manifest["boolean_column_count"] == EXPECTED_BOOLEAN_COUNT


def test_the_source_really_has_no_player_column(rows, manifest) -> None:
    """The premise of the whole identity-applicability contract. If this ever becomes false,
    the stream should gain a real identity column rather than keep the exemption."""
    assert manifest["has_no_player_column"] is True
    for name in PLAYER_COLUMN_NAMES:
        assert name not in rows[0], f"{name} exists — the exemption is no longer justified"


def test_the_fixture_exercises_both_boolean_values(manifest) -> None:
    """A slice that is all-False would let an inverted cast pass unnoticed."""
    counts = manifest["value_counts_is_motion"]
    assert counts.get("True", 0) > 0 and counts.get("False", 0) > 0


# ---------------------------------------------------------------------------
# The declared contract
# ---------------------------------------------------------------------------


def test_the_stream_is_registered_once_and_bound_to_its_own_loader() -> None:
    import nflreadpy

    built = _mod().build_streams()
    names = [s.name for s in built]
    assert names.count(STREAM) == 1
    spec = next(s for s in built if s.name == STREAM)
    assert spec.loader is nflreadpy.load_ftn_charting


def test_the_registered_spec_keeps_its_identity_and_boolean_flags() -> None:
    """`build_streams()._bind()` rebuilds specs field by field; a flag it forgets to copy is
    silently lost. That defect happened for real on stream 2."""
    spec = next(s for s in _mod().build_streams() if s.name == STREAM)
    assert spec.identity_applicable is False
    assert len(spec.boolean_columns) == EXPECTED_BOOLEAN_COUNT
    assert spec.require_populated_grain is True
    assert spec.eras


def test_the_declared_grain_is_the_play_not_a_player() -> None:
    spec = _spec()
    assert spec.grain == ("nflverse_game_id", "nflverse_play_id")


def test_the_spec_declares_no_identity_column() -> None:
    spec = _spec()
    assert spec.identity_applicable is False
    assert spec.identity_column == ""
    assert spec.identity_kind == ""


def test_declared_columns_match_the_live_shape(rows) -> None:
    spec = _spec()
    assert len(spec.columns) == EXPECTED_COLUMN_COUNT
    assert set(spec.columns) == set(rows[0])


def test_every_boolean_column_is_declared_boolean_not_float(rows) -> None:
    spec = _spec()
    source_bools = {c for c in rows[0] if c.startswith("is_")}
    assert source_bools == set(spec.boolean_columns)
    assert not (set(spec.boolean_columns) & set(spec.float_columns))
    assert not (set(spec.boolean_columns) & set(spec.integer_columns))


# ---------------------------------------------------------------------------
# C7 — identity applicability, fail-closed
# ---------------------------------------------------------------------------


def test_a_half_declared_identity_is_refused() -> None:
    """Codex C7 asked for fail-closed CONSTRUCTOR combinations, not a nullable column."""
    mod = _mod()
    base = dict(
        name="probe", table="probe", grain=("a",), columns=("a",),
        loader=None, loader_kwargs={},
    )
    # applicable but no column declared
    with pytest.raises(mod.UsageCaptureError, match="identity"):
        mod.StreamSpec(identity_column="", identity_kind="", identity_applicable=True, **base)
    # not applicable yet still naming a column
    with pytest.raises(mod.UsageCaptureError, match="must not name one"):
        mod.StreamSpec(
            identity_column="gsis_id", identity_kind="gsis", identity_applicable=False, **base
        )
    # exclusion policy for rows that were never identified
    with pytest.raises(mod.UsageCaptureError, match="no meaning"):
        mod.StreamSpec(
            identity_column="", identity_kind="", identity_applicable=False,
            exclude_unidentified_rows=True, **base
        )


def test_not_applicable_is_a_distinct_status_from_unknown() -> None:
    mod = _mod()
    assert mod.NOT_APPLICABLE not in (mod.UNKNOWN, mod.SOURCE_ONLY, mod.CONFLICT,
                                      mod.CANONICAL_RESOLVED)


def test_every_row_is_not_applicable_never_unknown(rows, identity) -> None:
    mod = _mod()
    normalized, _ = mod.normalize_rows(
        [dict(r) for r in rows], spec=_spec(), season=2024, identity=identity
    )
    assert len(normalized) == len(rows)
    for row in normalized:
        assert row["identity_status"] == mod.NOT_APPLICABLE
        assert row["dg_player_id"] is None


def test_coverage_states_zero_applicable_and_does_not_inflate_unidentified(
    rows, identity
) -> None:
    """The C7 requirement in numbers: report the zero, and do not let it read as failure."""
    mod = _mod()
    _, coverage = mod.normalize_rows(
        [dict(r) for r in rows], spec=_spec(), season=2024, identity=identity
    )
    assert coverage["rows_total"] == len(rows)
    assert coverage["identity_applicable_rows"] == 0
    assert coverage["rows_not_canonically_identified"] == 0
    for key in ("rows_canonical_resolved", "rows_source_only", "rows_conflict", "rows_unknown"):
        assert coverage[key] == 0
    # The invariant that holds for BOTH kinds of stream.
    assert coverage["identity_applicable_rows"] == sum(
        coverage[k]
        for k in ("rows_canonical_resolved", "rows_source_only", "rows_conflict", "rows_unknown")
    )


def test_an_identity_bearing_stream_still_reports_applicable_rows(identity) -> None:
    """Positive control: the new field must not read zero for every stream."""
    mod = _mod()
    payload = json.loads(
        (REPO_ROOT / "tests" / "fixtures" / "nflverse_usage_2025_slice.json").read_text()
    )
    _, coverage = mod.normalize_rows(
        [dict(r) for r in payload["ngs_passing"]],
        spec=mod.NGS_PASSING, season=2025, identity=identity,
    )
    assert coverage["identity_applicable_rows"] == coverage["rows_total"] > 0


def test_no_ftn_play_enters_the_unresolved_identity_artifact(tmp_path, rows, identity) -> None:
    """The artifact exists so a human can chase missing PLAYERS. 143,572 plays that never had
    one would bury the 53,994 that did."""
    import polars as pl

    mod = _mod()
    raw_root = tmp_path / "runtime"
    mod.run_usage_capture(
        seasons=[2024], specs=(_spec(),), identity=identity,
        db_path=tmp_path / "usage.db", raw_root=raw_root,
        fetch=lambda spec, season: rows,
    )
    run = sorted((raw_root / "export" / "runs").iterdir())[-1]
    unresolved = pl.read_parquet(run / "unresolved_identity.parquet")
    assert unresolved.height == 0, (
        f"{unresolved.height} FTN plays leaked into unresolved_identity.parquet"
    )


# ---------------------------------------------------------------------------
# Boolean round trip through SQLite
# ---------------------------------------------------------------------------


def test_booleans_survive_the_round_trip_as_booleans_not_text(
    tmp_path, rows, identity
) -> None:
    """SQLite holds these as TEXT '0'/'1'. Published as text, `"false"` is TRUTHY."""
    import polars as pl

    mod = _mod()
    spec = _spec()
    raw_root = tmp_path / "runtime"
    mod.run_usage_capture(
        seasons=[2024], specs=(spec,), identity=identity,
        db_path=tmp_path / "usage.db", raw_root=raw_root,
        fetch=lambda s, season: rows,
    )
    run = sorted((raw_root / "export" / "runs").iterdir())[-1]
    frame = pl.read_parquet(run / f"{spec.name}.parquet")
    dtypes = dict(zip(frame.columns, frame.dtypes))

    for column in spec.boolean_columns:
        assert dtypes[column] == pl.Boolean, (
            f"{column} published as {dtypes[column]}, not Boolean"
        )
        # Value-level reconciliation against the source, so an all-True or all-null cast fails.
        expected_true = sum(1 for r in rows if r.get(column) is True)
        emitted_true = int(frame[column].sum() or 0)
        assert emitted_true == expected_true, (
            f"{column}: {emitted_true} True in the export vs {expected_true} in the source"
        )
    for column in spec.integer_columns:
        assert dtypes[column] == pl.Int64, f"{column} published as {dtypes[column]}"


# ---------------------------------------------------------------------------
# Boundary
# ---------------------------------------------------------------------------


def test_landing_ftn_adds_no_engine_consumer() -> None:
    symbols = ("FTN_CHARTING", "ftn_charting", "load_ftn_charting")
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
            hits = [s for s in symbols if s in text]
            if hits:
                offenders[path.relative_to(REPO_ROOT).as_posix()] = hits
    assert not offenders, f"ftn_charting referenced outside the adapter: {offenders}"
