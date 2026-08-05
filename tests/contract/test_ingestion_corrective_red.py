"""Corrective RED — five defects Codex reproduced in the committed streams 2 and 3.

Targets: `da00235` (ff_opportunity) and `edf05e9` (ftn_charting). Those commits are NOT amended;
this closes the defects forward, per Codex's disposition.

Two of the five are Codex's own reproducers, carried here VERBATIM as positive controls. I
reproduced both independently before accepting them.

WHAT EACH DEFECT HAS IN COMMON: a safety property I asserted in prose and never exercised. The
Boolean claim ("anything that is neither '0' nor '1' becomes null and is caught by the
reconciliation") was simply false. The exclusion premise ("residual rows carry ZERO realized
production") was measured once and then never enforced by the code that depends on it.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "tests" / "fixtures"


def _mod():
    from src.dynasty_genius import nflverse_usage

    return nflverse_usage


@pytest.fixture(scope="module")
def identity():
    return _mod().IdentityIndex.from_governed_crosswalk()


@pytest.fixture(scope="module")
def opp_rows():
    return json.loads((FIXTURES / "ff_opportunity_2024_slice.json").read_text())


@pytest.fixture(scope="module")
def ftn_rows():
    return json.loads((FIXTURES / "ftn_charting_2024_slice.json").read_text())


def _residual_index(rows) -> int:
    return next(i for i, r in enumerate(rows) if not str(r.get("player_id") or "").strip())


# ---------------------------------------------------------------------------
# da00235-1 — exclusion runs before schema validation
# ---------------------------------------------------------------------------


def test_schema_drift_on_an_excluded_row_is_still_refused(opp_rows, identity) -> None:
    """The residual filter ran BEFORE era/per-record validation, so drift confined to a row that
    was about to be excluded was accepted and dropped. An upstream shape change is a contract
    breach wherever it appears — including on a row we do not intend to store."""
    mod = _mod()
    rows = [dict(r) for r in opp_rows]
    rows[_residual_index(rows)]["a_new_upstream_column"] = 1
    with pytest.raises(mod.UsageCaptureError):
        mod.normalize_rows(rows, spec=mod.FF_OPPORTUNITY, season=2024, identity=identity)


def test_a_missing_column_on_an_excluded_row_is_still_refused(opp_rows, identity) -> None:
    mod = _mod()
    rows = [dict(r) for r in opp_rows]
    rows[_residual_index(rows)].pop("total_fantasy_points")
    with pytest.raises(mod.UsageCaptureError):
        mod.normalize_rows(rows, spec=mod.FF_OPPORTUNITY, season=2024, identity=identity)


# ---------------------------------------------------------------------------
# da00235-2 and -3 — RESOLVED BY RETIRING THE MECHANISM, NOT BY GUARDING IT
#
# Codex's reproducer showed a blank-id row with 10 real fantasy points being silently
# excluded. I first added a guard that REFUSED such a row. Running it against the live
# source immediately proved the premise false in production: season 2022 carries a residual
# row with 21.4 fantasy points, 84 yards and 2 touchdowns, so the guard blocked the whole
# season — and the committed landing (da00235) HAD silently discarded that row.
#
# The real fix is that nothing needs excluding: (game_id, posteam, player_id) is unique in
# EVERY season 2018-2025 including residuals. The mechanism is retired for this stream.
# Codex's reproducer is kept below in OUTCOME form — the safety property it protects still
# has to hold even though the code path it targeted is gone.
#
# da00235-3 (a changed excluded-count must invalidate the capture) is covered by the
# collapse-count probe at the end of this file: the same coverage-fingerprint defect,
# exercised through the mechanism that is still in use.
# ---------------------------------------------------------------------------


def test_a_blank_id_row_with_real_production_is_never_discarded(opp_rows, identity) -> None:
    """CODEX'S REPRODUCER, in outcome form. The original asserted a refusal; the correct
    behaviour turned out to be stronger — the row is KEPT."""
    mod = _mod()
    rows = [dict(r) for r in opp_rows]
    i = _residual_index(rows)
    rows[i]["total_fantasy_points"] = 10.0
    rows[i]["full_name"] = "Unidentified Producer"

    normalized, _ = mod.normalize_rows(
        rows, spec=mod.FF_OPPORTUNITY, season=2024, identity=identity
    )
    assert len(normalized) == len(rows), "no row may be dropped"
    kept = [r for r in normalized if r.get("total_fantasy_points") == 10.0]
    assert kept, "the row carrying real production was discarded"
    assert kept[0]["identity_status"] == mod.UNKNOWN


def test_the_live_2022_production_row_shape_is_preserved(identity) -> None:
    """The specific real row the committed landing lost, reconstructed from the live
    measurement so it cannot regress without this test naming it."""
    mod = _mod()
    rows = [dict(r) for r in json.loads((FIXTURES / "ff_opportunity_2024_slice.json").read_text())]
    i = _residual_index(rows)
    rows[i].update(
        {"total_fantasy_points": 21.4, "total_yards_gained": 84.0, "total_touchdown": 2.0}
    )
    normalized, _ = mod.normalize_rows(
        rows, spec=mod.FF_OPPORTUNITY, season=2024, identity=identity
    )
    assert any(r.get("total_fantasy_points") == 21.4 for r in normalized)


def test_the_exclusion_mechanism_is_no_longer_armed_on_any_stream() -> None:
    """A mechanism whose premise failed on real data must not be left armed on some other
    stream where nobody has checked the premise either."""
    mod = _mod()
    armed = [s.name for s in mod.build_streams() if s.exclude_unidentified_rows]
    assert not armed, f"exclude_unidentified_rows is still armed on {armed}"


# ---------------------------------------------------------------------------
# edf05e9-1 — the Boolean cast is not fail-closed (Codex's reproducer)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", ["2", "-1", "true", "yes", "1.5"])
def test_a_non_boolean_source_value_refuses_rather_than_becoming_true(
    ftn_rows, identity, bad
) -> None:
    """CODEX'S REPRODUCER, GENERALISED.

    `is_motion='2'` published `status ok` with dtype Boolean and value True. The Int64
    intermediate accepts ANY integer and polars maps nonzero to true, so the non-null
    reconciliation cannot see it — it only counts nulls. My commit message claimed such a value
    "becomes null under strict=False and is then caught by the reconciliation". That was false.
    """
    mod = _mod()
    rows = [dict(r) for r in ftn_rows]
    rows[0]["is_motion"] = bad
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        with pytest.raises(mod.UsageCaptureError):
            mod.run_usage_capture(
                seasons=[2024], specs=(mod.FTN_CHARTING,), identity=identity,
                db_path=td / "u.db", raw_root=td / "rt",
                fetch=lambda s, season: rows,
            )


def test_genuine_boolean_values_still_publish_correctly(ftn_rows, identity) -> None:
    """The guard must not break real data — including genuine nulls."""
    import polars as pl

    mod = _mod()
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        mod.run_usage_capture(
            seasons=[2024], specs=(mod.FTN_CHARTING,), identity=identity,
            db_path=td / "u.db", raw_root=td / "rt",
            fetch=lambda s, season: [dict(r) for r in ftn_rows],
        )
        run = sorted((td / "rt" / "export" / "runs").iterdir())[-1]
        frame = pl.read_parquet(run / "ftn_charting.parquet")
        assert frame["is_motion"].dtype == pl.Boolean
        expected_true = sum(1 for r in ftn_rows if r.get("is_motion") is True)
        assert int(frame["is_motion"].sum() or 0) == expected_true


# ---------------------------------------------------------------------------
# edf05e9-2 — min_season/skip has no regression coverage
# ---------------------------------------------------------------------------


def test_min_season_is_declared_and_survives_binding() -> None:
    mod = _mod()
    bound = {s.name: s for s in mod.build_streams()}
    assert bound["ftn_charting"].min_season == 2022
    assert all(
        s.min_season is None for n, s in bound.items() if n != "ftn_charting"
    ), "min_season must not leak to streams that have no floor"


def test_a_season_below_the_floor_is_never_fetched(identity) -> None:
    """The whole point: the loader RAISES below its floor, so the fetch must not happen."""
    mod = _mod()
    attempted: list[int] = []

    def fetch(spec, season):
        attempted.append(season)
        return []

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        mod.run_usage_capture(
            seasons=[2020, 2021, 2022], specs=(mod.FTN_CHARTING,), identity=identity,
            db_path=td / "u.db", raw_root=td / "rt", fetch=fetch,
        )
    assert attempted == [2022], f"fetched below the floor: {attempted}"


def test_skips_are_recorded_exactly_and_the_run_still_succeeds(identity) -> None:
    """Recorded out-of-domain skips are SUCCESS, and are excluded from the count of
    stream-seasons actually ingested."""
    mod = _mod()
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        result = mod.run_usage_capture(
            seasons=[2020, 2021, 2022], specs=(mod.FTN_CHARTING,), identity=identity,
            db_path=td / "u.db", raw_root=td / "rt",
            fetch=lambda s, season: [],
        )
    assert result["status"] == "ok"
    skipped = [r for r in result["results"] if r.get("skipped")]
    assert [r["season"] for r in skipped] == [2020, 2021]
    assert all(r["skipped"] == "before_min_season" for r in skipped)
    assert all(r["min_season"] == 2022 for r in skipped)
    totals = result["totals"]
    assert totals["stream_seasons"] == 1, "skips must not inflate stream-seasons ingested"
    assert totals["stream_seasons_skipped"] == ["ftn_charting:2020", "ftn_charting:2021"]


def test_a_fully_skipped_run_still_writes_a_terminal_ok_marker(identity) -> None:
    """The `_totals` KeyError left the marker stuck at `running` — complete data, lying
    operational state. Assert the terminal marker directly."""
    mod = _mod()
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        raw_root = td / "rt"
        mod.run_usage_capture(
            seasons=[2020, 2021], specs=(mod.FTN_CHARTING,), identity=identity,
            db_path=td / "u.db", raw_root=raw_root,
            fetch=lambda s, season: [],
        )
        marker = json.loads(mod.status_marker_path(raw_root).read_text())
    assert marker["status"] == "ok", f"terminal marker says {marker['status']!r}"


# ---------------------------------------------------------------------------
# TRANSFER CHECK — the same defect class in stream 4, found by looking rather than
# by being told. depth_charts does not use exclusion or Booleans or min_season, but it
# DOES use collapse_exact_duplicates, so da00235-3 applies to it verbatim.
# ---------------------------------------------------------------------------


def test_a_changed_collapse_count_is_not_reported_as_unchanged(identity) -> None:
    """Stream 4 analogue of Codex da00235-3.

    Two captures with identical STORED rows but a different number of collapsed exact
    duplicates are different facts about the upstream. Before the coverage fingerprint they
    hashed the same and the second returned `unchanged`, leaving durable coverage stale.
    """
    mod = _mod()
    spec = mod.DEPTH_CHARTS
    rows = json.loads((FIXTURES / "depth_charts_weekly_2024_slice.json").read_text())

    with tempfile.TemporaryDirectory() as td:
        store = mod.UsageStore(Path(td) / "u.db", (spec,))
        first_rows, first_cov = mod.normalize_rows(
            [dict(r) for r in rows], spec=spec, season=2024, identity=identity
        )
        store.apply_season(spec, season=2024, rows=first_rows, coverage=first_cov,
                           ingested_at="t0")

        # One more exact duplicate: stored rows identical, collapse count +1.
        second_rows, second_cov = mod.normalize_rows(
            [*[dict(r) for r in rows], dict(rows[0])],
            spec=spec, season=2024, identity=identity,
        )
        assert second_cov["rows_collapsed_exact_duplicates"] == (
            first_cov["rows_collapsed_exact_duplicates"] + 1
        )
        assert len(second_rows) == len(first_rows), "stored rows must be identical"

        applied = store.apply_season(spec, season=2024, rows=second_rows,
                                     coverage=second_cov, ingested_at="t1")
        assert applied != "unchanged", (
            "the collapse count changed but the capture reported unchanged"
        )


# ===========================================================================
# ROUND 2 — Codex's four blockers on 7de9357 and 7654a19
# ===========================================================================


def _depth_weekly():
    return json.loads((FIXTURES / "depth_charts_weekly_2024_slice.json").read_text())


def _depth_daily():
    return json.loads((FIXTURES / "depth_charts_daily_2025_slice.json").read_text())


# --- 7de9357-1 / 7654a19-1: nullability is PER COLUMN and PER ERA, not all-or-nothing ---


def test_ff_refuses_a_null_posteam_while_still_permitting_a_null_player_id(
    opp_rows, identity
) -> None:
    """CODEX'S REPRODUCER. `require_populated_grain=False` permitted null player_id — and
    silently permitted null game_id and posteam too, keying a row as
    `game_id=...|posteam=None|player_id=None`. Only player_id is legitimately nullable."""
    mod = _mod()
    rows = [dict(r) for r in opp_rows]
    rows[_residual_index(rows)]["posteam"] = None
    with pytest.raises(mod.UsageCaptureError, match="blank_grain"):
        mod.normalize_rows(rows, spec=mod.FF_OPPORTUNITY, season=2024, identity=identity)


def test_ff_refuses_a_null_game_id(opp_rows, identity) -> None:
    mod = _mod()
    rows = [dict(r) for r in opp_rows]
    rows[0]["game_id"] = None
    with pytest.raises(mod.UsageCaptureError, match="blank_grain"):
        mod.normalize_rows(rows, spec=mod.FF_OPPORTUNITY, season=2024, identity=identity)


def test_ff_still_accepts_the_null_player_id_residuals(opp_rows, identity) -> None:
    """The nullable declaration must not break the real data it exists for."""
    mod = _mod()
    normalized, _ = mod.normalize_rows(
        [dict(r) for r in opp_rows], spec=mod.FF_OPPORTUNITY, season=2024, identity=identity
    )
    assert len(normalized) == len(opp_rows)


def test_the_daily_depth_era_permits_no_null_grain_coordinate(identity) -> None:
    """CODEX'S REPRODUCER. The weekly era's SBBYE null week forced
    `require_populated_grain=False` at SPEC level, which also disabled every check on the
    DAILY era — so a daily row with a null `pos_rank` was accepted."""
    mod = _mod()
    rows = [dict(r) for r in _depth_daily()]
    rows[0]["pos_rank"] = None
    with pytest.raises(mod.UsageCaptureError, match="blank_grain"):
        mod.normalize_rows(rows, spec=mod.DEPTH_CHARTS, season=2025, identity=identity)


def test_the_weekly_depth_era_still_permits_the_sbbye_null_week(identity) -> None:
    mod = _mod()
    rows = [dict(r) for r in _depth_weekly()]
    normalized, _ = mod.normalize_rows(
        rows, spec=mod.DEPTH_CHARTS, season=2024, identity=identity
    )
    assert any(r.get("game_type") == "SBBYE" and r.get("week") is None for r in normalized)


def test_the_weekly_depth_era_still_refuses_other_null_coordinates(identity) -> None:
    """`week` is nullable; `club_code` is not."""
    mod = _mod()
    rows = [dict(r) for r in _depth_weekly()]
    rows[0]["club_code"] = None
    with pytest.raises(mod.UsageCaptureError, match="blank_grain"):
        mod.normalize_rows(rows, spec=mod.DEPTH_CHARTS, season=2024, identity=identity)


def test_nullability_is_declared_per_era_not_per_spec() -> None:
    mod = _mod()
    bound = {s.name: s for s in mod.build_streams()}
    depth = bound["depth_charts"]
    assert depth.require_populated_grain is True
    by_era = {e.name: e.nullable_grain_columns for e in depth.eras}
    assert by_era == {"weekly": ("week", "depth_position"), "daily": ()}, (
        "weekly permits `week` (SBBYE) and `depth_position` (the '\\n    ' scrape artifact, "
        "3,964 rows 2018-2024); daily permits nothing"
    )
    assert bound["ff_opportunity"].nullable_grain_columns == ("player_id",)


# --- 7de9357-2: Boolean domain checked on the RAW value ---


@pytest.mark.parametrize("bad", ["01", "+1", "yes", "2", "-1", "1.0", " 1"])
def test_boolean_domain_is_checked_on_the_raw_value_not_a_coerced_integer(
    identity, bad
) -> None:
    """CODEX'S REPRODUCER, EXTENDED. My first guard coerced to Int64 and checked {0,1}, so
    '01' and '+1' both parsed to 1 and published True, while non-numeric values fell through
    to the generic cast-lost-values error rather than a Boolean-specific one."""
    mod = _mod()
    rows = [dict(r) for r in json.loads((FIXTURES / "ftn_charting_2024_slice.json").read_text())]
    rows[0]["is_motion"] = bad
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        with pytest.raises(mod.UsageCaptureError, match="boolean_out_of_domain"):
            mod.run_usage_capture(
                seasons=[2024], specs=(mod.FTN_CHARTING,), identity=identity,
                db_path=td / "u.db", raw_root=td / "rt", fetch=lambda s, season: rows,
            )


# --- 7654a19-2: the LIVE export dtypes, per era ---


@pytest.mark.parametrize(
    "fixture_name,season,expected_ints",
    [
        ("weekly", 2024, ("season", "week")),
        ("daily", 2025, ("pos_slot", "pos_rank")),
    ],
)
def test_depth_chart_integers_publish_as_int64_in_both_era_exports(
    identity, fixture_name, season, expected_ints
) -> None:
    """CODEX'S FINDING. The live Parquet published `week`, `pos_rank` and `pos_slot` as String
    because only `season` was declared. The fixtures happened to carry ints, so a
    fixture-level assertion could not see it — this reads the EMITTED file, per era."""
    import polars as pl

    mod = _mod()
    rows = _depth_weekly() if fixture_name == "weekly" else _depth_daily()
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        mod.run_usage_capture(
            seasons=[season], specs=(mod.DEPTH_CHARTS,), identity=identity,
            db_path=td / "u.db", raw_root=td / "rt",
            fetch=lambda s, se: [dict(r) for r in rows],
        )
        run = sorted((td / "rt" / "export" / "runs").iterdir())[-1]
        frame = pl.read_parquet(run / "depth_charts.parquet")
    dtypes = dict(zip(frame.columns, frame.dtypes))
    for column in expected_ints:
        assert dtypes[column] == pl.Int64, (
            f"{fixture_name} era published {column} as {dtypes[column]}, expected Int64"
        )
