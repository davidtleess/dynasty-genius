"""Contract — depth charts ingestion (Layer 1, board block C, stream 4 of 6).

TWO ERAS WITH DIFFERENT GRAINS. Measured live 2026-08-04 (`nflreadpy 0.1.5`):

  * 2020-2024 WEEKLY era — 15 columns, ~37k rows/season.
  * 2025+ DAILY era      — 12 columns, 554,215 rows in 2025 alone; nflverse swapped to a daily
    snapshot (`dt`) with ESPN position slots.

The boundary is PER SEASON and clean. An earlier framing called the eras "disjoint, sharing
almost no columns, with 554,215 null-season rows" — that was an artifact of unioning schemas
across a MULTI-SEASON load, not a property of the data. Loaded one season at a time each era is
internally complete. Recorded because the wrong reading nearly justified new era machinery that
`StreamEra` already provides (Codex C3).

WEEKLY GRAIN: `game_type` is load-bearing — week 19 exists as BOTH `REG` and `WC`, so without it
a wildcard row collides with the week-19 regular-season row. `week` is NULL for exactly the
`SBBYE` (Super Bowl bye) rows, 214-257 per season — a real category, not corruption.

EXACT DUPLICATES: 790 of 186,074 weekly rows (2020-2024) are exact full-row repeats, and after
collapsing them there are ZERO semantic collisions on the declared grain (Codex C8's distinction:
exact repeats and semantic collisions are different failure classes).

DAILY GRAIN uses `espn_id`, not `gsis_id`: `(dt, team, espn_id, pos_grp, pos_slot, pos_rank)` is
554,215/554,215 unique with ZERO nulls, while `gsis_id` is null on 5,577 rows. Identity still
resolves on `gsis_id` — grain and identity are different questions, and those 5,577 honestly
become `unknown`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "tests" / "fixtures"
WEEKLY = FIXTURES / "depth_charts_weekly_2024_slice.json"
WEEKLY_MANIFEST = FIXTURES / "depth_charts_weekly_2024_slice_manifest.json"
DAILY = FIXTURES / "depth_charts_daily_2025_slice.json"
DAILY_MANIFEST = FIXTURES / "depth_charts_daily_2025_slice_manifest.json"

STREAM = "depth_charts"


def _mod():
    from src.dynasty_genius import nflverse_usage

    return nflverse_usage


def _spec():
    spec = getattr(_mod(), "DEPTH_CHARTS", None)
    if spec is None:
        pytest.fail("DEPTH_CHARTS is not defined in nflverse_usage")
    return spec


def _load(path: Path):
    if not path.exists():
        pytest.fail(f"missing fixture: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def weekly() -> list[dict[str, Any]]:
    return _load(WEEKLY)


@pytest.fixture(scope="module")
def daily() -> list[dict[str, Any]]:
    return _load(DAILY)


@pytest.fixture(scope="module")
def weekly_manifest() -> dict[str, Any]:
    return _load(WEEKLY_MANIFEST)


@pytest.fixture(scope="module")
def daily_manifest() -> dict[str, Any]:
    return _load(DAILY_MANIFEST)


@pytest.fixture(scope="module")
def identity():
    return _mod().IdentityIndex.from_governed_crosswalk()


# ---------------------------------------------------------------------------
# Provenance — both eras must be represented
# ---------------------------------------------------------------------------


def test_both_era_fixtures_carry_checkable_provenance(
    weekly, daily, weekly_manifest, daily_manifest
) -> None:
    for manifest, rows, n_cols in (
        (weekly_manifest, weekly, 15),
        (daily_manifest, daily, 12),
    ):
        assert len(manifest["upstream_sha256"]) == 64
        assert manifest["nflreadpy_version"]
        assert manifest["n_columns"] == n_cols
        assert manifest["upstream_rows"] > manifest["slice_rows"] == len(rows)


def test_the_weekly_fixture_exercises_duplicates_and_the_null_week(weekly_manifest) -> None:
    """Without both, the collapse contract and the SBBYE contract are untested."""
    assert weekly_manifest["exact_duplicate_rows"] >= 1
    assert weekly_manifest["null_week_rows"] >= 1
    assert "SBBYE" in weekly_manifest["game_types"]


def test_the_daily_fixture_exercises_the_unresolved_identity_path(daily_manifest) -> None:
    assert daily_manifest["grain_is_unique"] is True
    assert daily_manifest["null_gsis_rows"] >= 1


# ---------------------------------------------------------------------------
# Declared contract
# ---------------------------------------------------------------------------


def test_the_stream_is_registered_once_and_bound_to_its_own_loader() -> None:
    import nflreadpy

    built = _mod().build_streams()
    assert [s.name for s in built].count(STREAM) == 1
    spec = next(s for s in built if s.name == STREAM)
    assert spec.loader is nflreadpy.load_depth_charts


def test_the_registered_spec_keeps_its_behaviour_flags() -> None:
    """Third time this guard earns its place: `_bind` rebuilds specs field by field and has
    now silently dropped a new flag once for real (stream 2)."""
    spec = next(s for s in _mod().build_streams() if s.name == STREAM)
    assert spec.collapse_exact_duplicates is True
    assert spec.require_populated_grain is False, "SBBYE rows legitimately carry a null week"
    assert spec.identity_column == "gsis_id" and spec.identity_kind == "gsis"
    assert len(spec.eras) == 2


def test_the_two_eras_declare_different_shapes_and_different_grains() -> None:
    spec = _spec()
    by_name = {e.name: e for e in spec.eras}
    assert set(by_name) == {"weekly", "daily"}
    assert len(by_name["weekly"].columns) == 15
    assert len(by_name["daily"].columns) == 12
    assert by_name["weekly"].grain != by_name["daily"].grain
    assert "game_type" in by_name["weekly"].grain, (
        "week 19 exists as both REG and WC; without game_type they collide"
    )
    assert by_name["daily"].grain == ("dt", "team", "espn_id", "pos_grp", "pos_slot", "pos_rank")


def test_each_era_matches_its_own_live_shape_and_not_the_other(weekly, daily) -> None:
    by_name = {e.name: e for e in _spec().eras}
    assert set(by_name["weekly"].columns) == set(weekly[0])
    assert set(by_name["daily"].columns) == set(daily[0])
    assert not by_name["weekly"].matches(set(daily[0]))
    assert not by_name["daily"].matches(set(weekly[0]))


def test_the_table_holds_the_union_of_both_eras() -> None:
    """An era-specific column with nowhere to go is dropped SILENTLY at insert time."""
    stored = set(_spec().stored_columns)
    for era in _spec().eras:
        assert set(era.columns) <= stored, f"{era.name} columns have nowhere to go"
    assert "source_era" in stored


# ---------------------------------------------------------------------------
# Era resolution
# ---------------------------------------------------------------------------


def test_each_era_resolves_to_itself_and_stamps_the_row(weekly, daily, identity) -> None:
    mod = _mod()
    for rows, expected, season in ((weekly, "weekly", 2024), (daily, "daily", 2025)):
        normalized, _ = mod.normalize_rows(
            [dict(r) for r in rows], spec=_spec(), season=season, identity=identity
        )
        assert normalized, f"{expected} era produced no rows"
        assert {r["source_era"] for r in normalized} == {expected}


def test_a_shape_matching_neither_era_refuses(weekly, identity) -> None:
    mod = _mod()
    mutated = [{**r, "an_unexpected_column": 1} for r in weekly]
    with pytest.raises(mod.UsageCaptureError, match="unknown_era|heterogeneous"):
        mod.normalize_rows(mutated, spec=_spec(), season=2024, identity=identity)


# ---------------------------------------------------------------------------
# Exact-duplicate collapse (Codex C8)
# ---------------------------------------------------------------------------


def test_exact_duplicates_collapse_and_are_counted_never_silently(weekly, identity) -> None:
    mod = _mod()
    normalized, coverage = mod.normalize_rows(
        [dict(r) for r in weekly], spec=_spec(), season=2024, identity=identity
    )
    key = "rows_collapsed_exact_duplicates"
    assert key in coverage, "a collapse that is not counted is a silent drop"
    assert coverage[key] >= 1
    # THE RECONCILIATION: stored + collapsed == what the source handed us.
    assert coverage["rows_total"] + coverage[key] == len(weekly)
    assert len(normalized) == coverage["rows_total"]


def test_the_collapse_count_is_reported_even_when_zero(daily, identity) -> None:
    """An absent key cannot be distinguished from a run where nothing collapsed."""
    mod = _mod()
    _, coverage = mod.normalize_rows(
        [dict(r) for r in daily], spec=_spec(), season=2025, identity=identity
    )
    assert coverage["rows_collapsed_exact_duplicates"] == 0


def test_a_semantic_collision_still_refuses_and_is_not_collapsed(weekly, identity) -> None:
    """The collapse must ONLY absorb byte-identical content. Two rows differing in any declared
    column are a genuine grain violation and must still refuse — otherwise the mechanism built
    to tidy provider noise would quietly swallow real conflicting observations."""
    mod = _mod()
    rows = [dict(r) for r in weekly]
    twin = dict(rows[0])
    twin["jersey_number"] = "99" if twin.get("jersey_number") != "99" else "98"
    with pytest.raises(mod.UsageCaptureError, match="grain_violation"):
        mod.normalize_rows([*rows, twin], spec=_spec(), season=2024, identity=identity)


def test_collapsing_is_deterministic_on_replay(weekly, identity) -> None:
    mod = _mod()
    a, ca = mod.normalize_rows(
        [dict(r) for r in weekly], spec=_spec(), season=2024, identity=identity
    )
    b, cb = mod.normalize_rows(
        [dict(r) for r in weekly], spec=_spec(), season=2024, identity=identity
    )
    assert a == b and ca == cb


# ---------------------------------------------------------------------------
# The SBBYE null week
# ---------------------------------------------------------------------------


def test_the_super_bowl_bye_row_survives_its_null_week(weekly, identity) -> None:
    """214-257 rows/season carry game_type SBBYE and a null week. Refusing them would discard a
    real category; `game_type` in the grain keeps them distinguishable."""
    mod = _mod()
    normalized, _ = mod.normalize_rows(
        [dict(r) for r in weekly], spec=_spec(), season=2024, identity=identity
    )
    sbbye = [r for r in normalized if r.get("game_type") == "SBBYE"]
    assert sbbye, "the SBBYE row was dropped"
    assert all(r.get("week") is None for r in sbbye)


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


def test_a_daily_row_without_a_gsis_id_is_unknown_not_canonical(daily, identity) -> None:
    mod = _mod()
    normalized, coverage = mod.normalize_rows(
        [dict(r) for r in daily], spec=_spec(), season=2025, identity=identity
    )
    assert coverage["rows_unknown"] >= 1
    for row in normalized:
        if not str(row.get("gsis_id") or "").strip():
            assert row["identity_status"] == mod.UNKNOWN
            assert row["dg_player_id"] is None
    assert coverage["identity_applicable_rows"] == coverage["rows_total"]


def test_coverage_reconciles_across_both_eras(weekly, daily, identity) -> None:
    mod = _mod()
    parts = ("rows_canonical_resolved", "rows_source_only", "rows_conflict", "rows_unknown")
    for rows, season in ((weekly, 2024), (daily, 2025)):
        _, coverage = mod.normalize_rows(
            [dict(r) for r in rows], spec=_spec(), season=season, identity=identity
        )
        assert sum(coverage[k] for k in parts) == coverage["rows_total"]


# ---------------------------------------------------------------------------
# Boundary
# ---------------------------------------------------------------------------


def test_landing_depth_charts_adds_no_engine_consumer() -> None:
    symbols = ("DEPTH_CHARTS", "depth_charts", "load_depth_charts")
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
    assert not offenders, f"depth_charts referenced outside the adapter: {offenders}"
