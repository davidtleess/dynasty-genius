"""RED contract — ff_opportunity ingestion (Layer 1, board block C, stream 2 of 6).

Batch framing/disposition: `docs/agent-ledger/evidence/2026-08-04/six_loader_batch_*`
Generator: `docs/agent-ledger/evidence/2026-08-04/build_ff_opportunity_fixture_claude_v1.py`

SCOPE. The shared capture mechanism (raw hashing, export typing, last-good preservation across both
failure stages, replay determinism, duplicate/missing/heterogeneous refusal) is already contracted by
`test_pfr_advstats_ingestion_red.py` and is not re-litigated here. This file contracts what is
DISTINCTIVE to `ff_opportunity`:

  * TWO ROW CLASSES, and the exclusion/reconciliation of the residual class.
  * A GSIS-keyed identity (PFR's stream resolves through the PFR bridge instead).
  * A 159-column contract whose `season` is String and `week` Float64 upstream.

MEASURED LIVE 2026-08-04 (`nflreadpy 0.1.5`), seasons 2023-2025 — reproduced in a staging capture:
  18,140 source rows = 16,860 PLAYER rows stored + 1,280 RESIDUAL rows excluded, exactly.
  Player grain `(game_id, player_id)`: zero duplicates. Identity: 16,834 canonical_resolved /
  26 source_only / 0 conflict / 0 unknown.
  Residual rows are exactly ONE per `(game_id, posteam)`; 1,274 of 1,280 carry a nonzero
  `rec_attempt` but ZERO realized production, contributing exactly 0.0 of 143,269.2 total
  fantasy points (0.000%).

Imports are lazy for the same reason as the PFR RED: a module-level import of an unbuilt symbol is a
COLLECTION error, and the standing invariant is zero collection errors.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "ff_opportunity_2024_slice.json"
FIXTURE_MANIFEST = REPO_ROOT / "tests" / "fixtures" / "ff_opportunity_2024_slice_manifest.json"

STREAM = "ff_opportunity"
EXPECTED_COLUMN_COUNT = 159
KEY_COLUMNS = (
    "season",
    "week",
    "game_id",
    "posteam",
    "player_id",
    "full_name",
    "position",
)
COVERAGE_TOTAL = "rows_total"
COVERAGE_PARTS = (
    "rows_canonical_resolved",
    "rows_source_only",
    "rows_conflict",
    "rows_unknown",
)
EXCLUDED_KEY = "rows_excluded_unidentified"


def _mod():
    from src.dynasty_genius import nflverse_usage

    return nflverse_usage


def _spec():
    spec = getattr(_mod(), "FF_OPPORTUNITY", None)
    if spec is None:
        pytest.fail("FF_OPPORTUNITY is not defined in nflverse_usage")
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


def _player_rows(rows):
    return [r for r in rows if str(r.get("player_id") or "").strip()]


def _residual_rows(rows):
    return [r for r in rows if not str(r.get("player_id") or "").strip()]


# ---------------------------------------------------------------------------
# Fixture provenance
# ---------------------------------------------------------------------------


def test_the_fixture_carries_checkable_provenance(rows, manifest) -> None:
    assert manifest["n_columns"] == EXPECTED_COLUMN_COUNT
    assert len(manifest["upstream_sha256"]) == 64
    assert manifest["nflreadpy_version"]
    assert manifest["upstream_rows"] > manifest["slice_rows"]
    assert manifest["slice_rows"] == len(rows)
    assert manifest["player_rows"] == len(_player_rows(rows))
    assert manifest["residual_rows"] == len(_residual_rows(rows))


def test_the_fixture_carries_both_row_classes(rows) -> None:
    """A fixture with only player rows would leave the exclusion path untested — and the
    exclusion path is the whole distinctive contract of this stream."""
    assert _player_rows(rows), "no player rows in the slice"
    assert _residual_rows(rows), "no residual rows in the slice — exclusion untested"


def test_the_residual_rows_are_one_per_game_and_team(rows, manifest) -> None:
    residual = _residual_rows(rows)
    pairs = {(r["game_id"], r["posteam"]) for r in residual}
    assert len(pairs) == len(residual)
    assert manifest["residual_is_one_per_game_posteam"] is True


def test_the_residual_rows_carry_no_realized_production(rows) -> None:
    """Measured across 2023-2025: residual rows contribute exactly 0.0 of 143,269.2 total
    fantasy points. They are an expected-value residual for unattributed targets, NOT lost
    player production — which is what makes excluding them from the player projection honest.
    """
    for row in _residual_rows(rows):
        assert (row.get("total_fantasy_points") or 0) == 0
        assert (row.get("total_yards_gained") or 0) == 0
        assert row.get("full_name") is None
        assert row.get("position") is None


# ---------------------------------------------------------------------------
# The declared contract
# ---------------------------------------------------------------------------


def test_the_stream_is_registered_once_and_bound_to_its_own_loader() -> None:
    import nflreadpy

    built = _mod().build_streams()
    names = [s.name for s in built]
    assert names.count(STREAM) == 1, f"{STREAM} registered {names.count(STREAM)} times"
    spec = next(s for s in built if s.name == STREAM)
    assert spec.loader is nflreadpy.load_ff_opportunity, (
        f"bound to {getattr(spec.loader, '__name__', spec.loader)!r}"
    )


def test_the_registered_spec_keeps_its_declared_behaviour_flags() -> None:
    """`build_streams()` rebuilds each spec field by field, so a flag added to StreamSpec but
    not copied there is silently lost — measured live: `exclude_unidentified_rows` was dropped
    exactly this way and the first staging capture died on a blank grain.
    """
    spec = next(s for s in _mod().build_streams() if s.name == STREAM)
    assert spec.exclude_unidentified_rows is True
    assert spec.refuse_non_finite is True
    assert spec.require_populated_grain is True
    assert spec.eras, "the additive-column refusal depends on a declared era"


def test_the_declared_grain_and_identity() -> None:
    spec = _spec()
    assert spec.grain == ("game_id", "player_id")
    assert spec.identity_column == "player_id"
    assert spec.identity_kind == "gsis", "player_id is a GSIS id, our canonical key"


def test_the_declared_columns_match_the_live_shape(rows) -> None:
    spec = _spec()
    observed = set(rows[0])
    assert len(spec.columns) == EXPECTED_COLUMN_COUNT
    assert set(spec.columns) == observed, (
        f"undeclared {sorted(observed - set(spec.columns))}, "
        f"absent {sorted(set(spec.columns) - observed)}"
    )
    for column in KEY_COLUMNS:
        assert column in spec.columns


def test_season_and_week_are_declared_integers_despite_upstream_types() -> None:
    """Upstream ships `season` as String and `week` as Float64. Declared as integers so the
    store does not hold '2024.0' — the exact defect that made `season == 2020` miss a season."""
    spec = _spec()
    assert "season" in spec.integer_columns
    assert "week" in spec.integer_columns


def test_every_metric_column_is_typed() -> None:
    spec = _spec()
    typed = set(spec.integer_columns) | set(spec.float_columns)
    metrics = set(spec.columns) - set(KEY_COLUMNS)
    assert metrics <= typed, f"untyped: {sorted(metrics - typed)}"
    assert len(spec.float_columns) == 152


# ---------------------------------------------------------------------------
# The exclusion contract — reconciled, never silent
# ---------------------------------------------------------------------------


def test_residual_rows_are_excluded_and_counted_not_silently_dropped(rows, identity) -> None:
    mod = _mod()
    normalized, coverage = mod.normalize_rows(
        [dict(r) for r in rows], spec=_spec(), season=2024, identity=identity
    )
    expected_players = len(_player_rows(rows))
    expected_residual = len(_residual_rows(rows))

    assert len(normalized) == expected_players
    assert coverage[COVERAGE_TOTAL] == expected_players
    assert EXCLUDED_KEY in coverage, (
        "an excluded row that is not counted is a silent drop; the coverage must reconcile"
    )
    assert coverage[EXCLUDED_KEY] == expected_residual
    # THE RECONCILIATION: stored + excluded == what the source handed us.
    assert coverage[COVERAGE_TOTAL] + coverage[EXCLUDED_KEY] == len(rows)


def test_no_stored_row_has_a_blank_identity(rows, identity) -> None:
    mod = _mod()
    normalized, _ = mod.normalize_rows(
        [dict(r) for r in rows], spec=_spec(), season=2024, identity=identity
    )
    for row in normalized:
        assert str(row.get("player_id") or "").strip(), "a residual row survived exclusion"


def test_identity_resolves_on_the_gsis_universe_with_no_conflicts(rows, identity) -> None:
    mod = _mod()
    _, coverage = mod.normalize_rows(
        [dict(r) for r in rows], spec=_spec(), season=2024, identity=identity
    )
    assert coverage["rows_conflict"] == 0
    assert coverage["rows_unknown"] == 0
    assert sum(coverage[k] for k in COVERAGE_PARTS) == coverage[COVERAGE_TOTAL]
    assert coverage["rows_source_only"] >= 1, (
        "the slice is built to carry an unresolved player; if this is zero the "
        "source_only path is untested"
    )


def test_an_unidentified_row_is_excluded_rather_than_refused(identity) -> None:
    """Positive control on the exclusion itself: a batch of ONLY residual rows must produce a
    clean empty result with the count reconciled, not a blank-grain refusal and not a crash."""
    mod = _mod()
    residual = _residual_rows(json.loads(FIXTURE.read_text(encoding="utf-8")))
    normalized, coverage = mod.normalize_rows(
        [dict(r) for r in residual], spec=_spec(), season=2024, identity=identity
    )
    assert normalized == []
    assert coverage[COVERAGE_TOTAL] == 0
    assert coverage[EXCLUDED_KEY] == len(residual)


# ---------------------------------------------------------------------------
# Refusals that are specific to this stream's shape
# ---------------------------------------------------------------------------


def test_an_additive_provider_column_refuses(rows, identity) -> None:
    mod = _mod()
    augmented = [{**r, "expected_points_v2": 1.0} for r in rows]
    with pytest.raises(mod.UsageCaptureError, match="expected_points_v2"):
        mod.normalize_rows(augmented, spec=_spec(), season=2024, identity=identity)


def test_a_duplicate_player_at_the_declared_grain_refuses(rows, identity) -> None:
    mod = _mod()
    players = _player_rows(rows)
    with pytest.raises(mod.UsageCaptureError, match="duplicate|grain_violation"):
        mod.normalize_rows(
            [*[dict(r) for r in rows], dict(players[0])],
            spec=_spec(),
            season=2024,
            identity=identity,
        )


def test_a_non_finite_metric_refuses(rows, identity) -> None:
    mod = _mod()
    for bad in (float("inf"), float("nan")):
        mutated = [dict(r) for r in rows]
        target = next(i for i, r in enumerate(mutated) if str(r.get("player_id") or "").strip())
        mutated[target]["total_fantasy_points_exp"] = bad
        with pytest.raises(mod.UsageCaptureError):
            mod.normalize_rows(mutated, spec=_spec(), season=2024, identity=identity)


# ---------------------------------------------------------------------------
# Boundary — substrate_only
# ---------------------------------------------------------------------------


def test_landing_ff_opportunity_adds_no_engine_consumer() -> None:
    """`ff_opportunity` is a THIRD-PARTY MODEL OUTPUT (expected fantasy points), not raw fact.
    Any use as a feature needs its own validation, so nothing may consume it on landing.
    """
    symbols = ("FF_OPPORTUNITY", "ff_opportunity", "load_ff_opportunity")
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
    assert not offenders, (
        f"ff_opportunity is referenced outside the adapter: {offenders}. substrate_only."
    )
