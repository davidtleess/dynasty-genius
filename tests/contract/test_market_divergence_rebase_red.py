"""DG2-S0-01 — rank-population mismatch. RED contract.

The defect: `universe_market_divergence` ranks a player's model value against the
MODEL-backed population and its market value against the MARKET-priced population, then
subtracts the two percentiles. Those are different populations, so the delta is not
like-for-like — a 60th percentile of 300 model rows and a 60th percentile of 500 market
rows are not the same position.

This module defines the COMMON cohort (players present in both populations, per position)
and rebases both percentiles onto it, so the subtraction compares like with like.

Descriptive throughout: the rebase reports quantities and counts. It issues no verdict and
carries `decision_supported=False`, per the No-Verdict Line.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.dynasty_genius.market_divergence_rebase import (
    CohortMismatchError,
    _is_band_crossing,
    _is_direction_reversal,
    _model_index,
    build_rebased_divergence,
    common_cohort,
)
from src.dynasty_genius.pvo_source import resolve_pvo_source
from src.dynasty_genius.services.market_overlay_service import NOISE_BAND

REPO_ROOT = Path(__file__).resolve().parents[2]
LIVE_PVO = REPO_ROOT / "app" / "data" / "valuation_runtime" / "universe_pvo_runtime.json"
SEED_PVO = REPO_ROOT / "app" / "data" / "valuation" / "universe_pvo_latest.json"
SEED_PVO_COVERAGE = (
    REPO_ROOT / "app" / "data" / "valuation" / "universe_pvo_coverage_latest.json"
)

# The production identity key, verified against the shipped consumer
# (`universe_market_divergence.py:165` reads `row["sleeper_player_id"]`) and against the
# live artifact (12,201/12,201 rows carry it at the ROOT; 0 carry a nested `player.sleeper_id`).
PRODUCTION_IDENTITY_KEY = "sleeper_player_id"


def _model_row(sleeper_id: str, position: str, xvar: float, *,
               engine_path: str = "ENGINE_B", status: str = "MODEL_SUPPORTED") -> dict:
    """A row in the shape production ACTUALLY emits: identity at the ROOT as
    ``sleeper_player_id``, position nested at ``player.position``.

    The constants are the real contract constants (`MODEL_BACKED_ROUTES` /
    `MODEL_BACKED_STATUSES`). The earlier version of this helper put identity at
    ``player.sleeper_id`` — a location production has never emitted — so the whole suite
    verified the author's imagination and went green while comparing zero real players.
    Shape, not just values, has to come from production.
    """
    return {
        "sleeper_player_id": sleeper_id,
        "player": {"position": position},
        "valuation": {"xvar": xvar, "engine_path": engine_path, "valuation_status": status},
    }


def _market_entry(sleeper_id: str, position: str, value: float) -> dict:
    return {"player": {"sleeperId": sleeper_id, "position": position}, "value": value}


def _fabricated_nested_identity_row(sleeper_id: str, position: str, xvar: float) -> dict:
    """The shape THIS FILE fabricated before 2026-07-27, preserved deliberately.

    Production has never emitted it. It exists here only so the contract can prove the
    shape is rejected — see `test_a_row_with_only_the_fabricated_nested_identity_is_ignored`.
    """
    return {
        "player": {"sleeper_id": sleeper_id, "position": position},
        "valuation": {
            "xvar": xvar,
            "engine_path": "ENGINE_B",
            "valuation_status": "MODEL_SUPPORTED",
        },
    }


# ─────────── (c) band crossing vs direction reversal — two facts, separately named ────
#
# Codex HIGH, 2026-07-27: the implementation reported 133 signal changes where the
# ticket's registered figure is 131. Neither number was wrong; they measure different
# things. 131 rows cross the |0.10| noise band. Two further rows never touch the band —
# they stay outside it and flip SIGN. The RED prose defines reclassification as crossing
# the band, so 131 is the contract-consistent count and 133 silently mixed in a second
# phenomenon. Both facts survive here, separately named, neither discarded.
#
# The values below are the two REAL rows Codex identified, not invented ones.


def test_an_outside_band_sign_flip_is_a_direction_reversal_not_a_band_crossing() -> None:
    """Ja'Tavion Sanders, +0.157 -> -0.100: both magnitudes at or beyond the band."""
    assert _is_direction_reversal(0.157, -0.100) is True
    assert _is_band_crossing(0.157, -0.100) is False


def test_the_second_real_reversal_behaves_identically() -> None:
    """Dontayvion Wicks, +0.107 -> -0.109."""
    assert _is_direction_reversal(0.107, -0.109) is True
    assert _is_band_crossing(0.107, -0.109) is False


def test_entering_the_noise_band_is_a_band_crossing_not_a_reversal() -> None:
    assert _is_band_crossing(0.157, 0.02) is True
    assert _is_direction_reversal(0.157, 0.02) is False


def test_leaving_the_noise_band_is_also_a_band_crossing() -> None:
    assert _is_band_crossing(0.01, -0.22) is True
    assert _is_direction_reversal(0.01, -0.22) is False


def test_a_row_that_moves_without_changing_signal_is_neither() -> None:
    assert _is_band_crossing(0.30, 0.18) is False
    assert _is_direction_reversal(0.30, 0.18) is False


# A fixture SEARCHED FOR, not assumed: the earlier version of this row produced
# 0 crossings and 0 reversals, so its union assertion was only `0 == 0 + 0` and no
# committed row proved a nonzero reversal reaches the row flags or the counters
# (Codex, 2026-07-27). These values were found by measuring candidates until one
# yielded BOTH phenomena, then pinned; the counts below are measured, not predicted.
_SPLIT_COMMON_XVARS = [49.0, 22.0, 46.0, 50.0, 55.0, 30.0, 32.0, 38.0]
_SPLIT_COMMON_VALUES = [991.0, 260.0, 973.0, 1028.0, 330.0, 368.0, 305.0, 950.0]
_SPLIT_MODEL_ONLY_XVARS = [7.0, 18.0, 12.0, 30.0, 36.0, 37.0]


def _split_report() -> dict:
    rows = [_model_row(str(i), "QB", x) for i, x in enumerate(_SPLIT_COMMON_XVARS)]
    rows += [
        _model_row(str(100 + j), "QB", x) for j, x in enumerate(_SPLIT_MODEL_ONLY_XVARS)
    ]
    fc = [_market_entry(str(i), "QB", v) for i, v in enumerate(_SPLIT_COMMON_VALUES)]
    return build_rebased_divergence(rows, fc, snapshot_date="2026-07-26")


def test_the_report_counts_a_nonzero_split_exactly() -> None:
    """Both phenomena nonzero, exact counts, so the union assertion cannot be 0 == 0 + 0."""
    report = _split_report()

    assert report["compared_rows"] == 8
    assert report["band_crossing_count"] == 5
    assert report["direction_reversal_count"] == 1
    assert report["classification_change_count"] == 6


def test_the_nonzero_direction_reversal_reaches_the_row_flags() -> None:
    """The reversal row: +0.116 -> -0.124, outside the band on BOTH sides, sign flipped."""
    report = _split_report()
    reversals = [r for r in report["rows"] if r["direction_reversal"]]

    assert len(reversals) == 1
    row = reversals[0]
    assert row["current_delta"] > 0 and row["rebased_delta"] < 0
    assert abs(row["current_delta"]) >= NOISE_BAND
    assert abs(row["rebased_delta"]) >= NOISE_BAND
    assert row["band_crossing"] is False
    assert row["classification_changed"] is True


def test_the_split_phenomena_stay_mutually_exclusive_on_a_nonzero_report() -> None:
    report = _split_report()

    for row in report["rows"]:
        assert not (row["band_crossing"] and row["direction_reversal"]), (
            "the two phenomena are mutually exclusive by construction"
        )
    assert report["classification_change_count"] == (
        report["band_crossing_count"] + report["direction_reversal_count"]
    )


# ────────────────────────── the identity finding (Codex BLOCKER, 2026-07-27) ──────────
#
# The defect was never "one wrong key". A suite went 10/10 GREEN while comparing ZERO
# players, because the fixtures invented an identity location production does not have,
# and the module read the invention. Green meant "the code agrees with my imagination".
# These rows exist so that can never again be true silently.


def test_model_index_reads_the_production_identity_key() -> None:
    """A row in the REAL production shape must be indexed."""
    row = {
        PRODUCTION_IDENTITY_KEY: "4034",
        "player": {"position": "QB"},
        "valuation": {
            "xvar": 12.5,
            "engine_path": "ENGINE_B",
            "valuation_status": "MODEL_SUPPORTED",
        },
    }

    index = _model_index([row])

    assert index == {"4034": {"position": "QB", "xvar": 12.5}}


def test_a_row_with_only_the_fabricated_nested_identity_is_ignored() -> None:
    """THE EVIDENCE ROW. The pre-2026-07-27 fixture shape must now index NOTHING.

    Had this row existed, the original 10/10 green would have been impossible: it fails
    the moment the module accepts an identity location production does not emit.
    """
    assert _model_index([_fabricated_nested_identity_row("4034", "QB", 12.5)]) == {}


def test_the_shared_fixture_carries_the_production_identity_key() -> None:
    """The fixture builder itself is under contract, so a future edit cannot quietly
    reintroduce a fabricated shape and take the whole suite green with it."""
    row = _model_row("4034", "QB", 12.5)

    assert PRODUCTION_IDENTITY_KEY in row, "fixtures must carry the production identity key"
    assert "sleeper_id" not in row.get("player", {}), "the nested identity is an invention"


def test_the_committed_pvo_seed_is_indexable_by_this_module() -> None:
    """MANDATORY — never skips, anywhere. This is CI's identity defense.

    Codex, 2026-07-27: an identity guard that rests only on the gitignored runtime artifact
    skips in CI and a fresh clone, leaving the contract defended solely by fixtures the
    implementing lane edits alongside the code — the original failure class exactly. The
    committed seed is tracked production data, so this row runs everywhere and cannot be
    satisfied by editing a fixture.

    Reached through the verified `resolve_pvo_source` contract rather than bare file
    existence; `runtime_dir` is a directory with no runtime trace, so resolution is
    deterministically the seed on every host.
    """
    resolved = resolve_pvo_source(
        seed_paths={"pvo": SEED_PVO, "coverage": SEED_PVO_COVERAGE},
        runtime_dir=REPO_ROOT / "app" / "data" / "valuation" / "_no_runtime_trace_here",
    )
    assert resolved.source_kind == "seed"

    players = json.loads(Path(resolved.pvo_path).read_text())["players"]
    index = _model_index(players)

    assert index, (
        f"_model_index returned ZERO rows from {len(players)} committed seed players — "
        "the module cannot see production identities"
    )


def test_the_local_runtime_pvo_artifact_is_indexable_by_this_module() -> None:
    """Second, host-bound row. The LOCAL RUNTIME artifact — not live Sleeper state, and not
    a substitute for the mandatory seed row above. Skipped where the gitignored artifact is
    absent; binding where it exists."""
    if not LIVE_PVO.exists():
        pytest.skip(f"local runtime PVO artifact absent: {LIVE_PVO.relative_to(REPO_ROOT)}")

    players = json.loads(LIVE_PVO.read_text())["players"]
    index = _model_index(players)

    assert index, (
        f"_model_index returned ZERO rows from {len(players)} local runtime players — "
        "the module cannot see production identities"
    )


def test_a_cohort_built_from_the_shared_fixtures_is_never_empty() -> None:
    """A green suite must never be able to mean 'nothing was compared'."""
    rows = [_model_row("1", "QB", 10.0), _model_row("2", "QB", 8.0)]
    fc = [_market_entry("1", "QB", 5000.0), _market_entry("2", "QB", 4000.0)]

    cohort = common_cohort(rows, fc)

    assert sum(len(members) for members in cohort.values()) == 2


# --------------------------------------------------------------- AC1: the inclusion rule


def test_common_cohort_is_the_intersection_per_position():
    """AC1: the common cohort is defined with its inclusion rule.

    A player belongs to the common cohort for its position when it carries BOTH a
    model-backed xVAR and a market value. Membership is per position, because both
    percentiles are computed within position."""
    rows = [_model_row("1", "QB", 10.0), _model_row("2", "QB", 8.0),
            _model_row("3", "WR", 5.0)]
    market = [_market_entry("1", "QB", 100.0), _market_entry("2", "QB", 90.0),
              _market_entry("9", "QB", 50.0)]          # market-only, excluded
    cohort = common_cohort(rows, market)
    assert set(cohort) == {"QB"}, "WR has no market row, so no common QB/WR cohort member"
    assert {m.sleeper_id for m in cohort["QB"]} == {"1", "2"}
    assert cohort["QB"][0].inclusion_rule == "model_backed_and_market_priced"


def test_model_rows_without_a_model_backed_route_are_excluded():
    """A row that is not model-backed has no comparable model value to rank."""
    rows = [_model_row("1", "QB", 10.0),
            _model_row("2", "QB", 8.0, engine_path="PRE_MODEL")]
    market = [_market_entry("1", "QB", 100.0), _market_entry("2", "QB", 90.0)]
    cohort = common_cohort(rows, market)
    assert {m.sleeper_id for m in cohort["QB"]} == {"1"}


def test_common_cohort_reports_the_population_it_excluded():
    """The rule is only auditable if the exclusions are counted, not silently dropped."""
    rows = [_model_row("1", "QB", 10.0), _model_row("2", "QB", 8.0)]
    market = [_market_entry("1", "QB", 100.0), _market_entry("7", "QB", 70.0)]
    cohort = common_cohort(rows, market)
    member = cohort["QB"][0]
    assert member.model_population == 2, "two model-backed QBs existed"
    assert member.market_population == 2, "two market-priced QBs existed"
    assert len(cohort["QB"]) == 1, "only one player was in both"


# ------------------------------------------------- AC2/AC4: rebased divergence + deltas


def test_rebase_changes_a_delta_when_the_populations_differ():
    """AC2: a rebased divergence exists for the same snapshot date, and it DIFFERS.

    Player 2 sits mid-pack among model-backed QBs but bottom among market-priced QBs,
    because the market population carries extra low-value players the model does not
    rank. Rebasing onto the common cohort removes that asymmetry."""
    rows = [_model_row("1", "QB", 30.0), _model_row("2", "QB", 20.0),
            _model_row("3", "QB", 10.0)]
    market = [_market_entry("1", "QB", 300.0), _market_entry("2", "QB", 200.0),
              _market_entry("3", "QB", 100.0),
              _market_entry("90", "QB", 5.0), _market_entry("91", "QB", 4.0)]
    report = build_rebased_divergence(rows, market, snapshot_date="2026-07-26")
    assert report["snapshot_date"] == "2026-07-26"
    by_id = {r["sleeper_id"]: r for r in report["rows"]}
    mid = by_id["2"]
    assert mid["current_delta"] != mid["rebased_delta"], (
        "the two market-only players shift the market percentile but not the model one")
    assert mid["rebased_model_percentile"] == mid["rebased_market_percentile"], (
        "on the common cohort the orderings agree exactly, so the rebased delta is 0")
    assert mid["rebased_delta"] == 0.0


def test_report_carries_both_average_deltas_and_the_signal_change_counts():
    """AC3 + AC4: current and rebased average delta are both reported, and the counts of
    rows whose signal changes are reported alongside them — band crossings and direction
    reversals separately, per the (c) split."""
    rows = [_model_row(str(i), "QB", float(30 - i)) for i in range(6)]
    market = ([_market_entry(str(i), "QB", float(300 - 10 * i)) for i in range(6)]
              + [_market_entry("90", "QB", 1.0), _market_entry("91", "QB", 2.0)])
    report = build_rebased_divergence(rows, market, snapshot_date="2026-07-26")
    assert "current_mean_abs_delta" in report
    assert "rebased_mean_abs_delta" in report
    assert isinstance(report["band_crossing_count"], int)
    assert isinstance(report["direction_reversal_count"], int)
    assert report["compared_rows"] == 6
    assert report["classification_change_count"] <= report["compared_rows"]


def test_signal_change_is_measured_against_the_noise_band():
    """A row's signal changes when it crosses the noise band or reverses direction outside
    it, not when its delta merely moves — the band is what the classification is made of."""
    rows = [_model_row("1", "QB", 30.0), _model_row("2", "QB", 20.0),
            _model_row("3", "QB", 10.0)]
    market = [_market_entry("1", "QB", 300.0), _market_entry("2", "QB", 200.0),
              _market_entry("3", "QB", 100.0),
              _market_entry("90", "QB", 5.0), _market_entry("91", "QB", 4.0)]
    report = build_rebased_divergence(rows, market, snapshot_date="2026-07-26")
    for row in report["rows"]:
        assert row["current_classification"] in {
            "aligned", "model_higher_than_market", "model_lower_than_market"}
        assert row["rebased_classification"] in {
            "aligned", "model_higher_than_market", "model_lower_than_market"}
        assert row["classification_changed"] is (
            row["current_classification"] != row["rebased_classification"])
        assert row["classification_changed"] is (
            row["band_crossing"] or row["direction_reversal"])


# ------------------------------------------------------------------ fails loudly by name


def test_a_non_common_cohort_run_refuses_by_name():
    """`Fails loudly:` a non-common-cohort run refuses by name — it does not silently
    fall back to the mismatched populations that caused the defect."""
    rows = [_model_row("1", "QB", 10.0)]
    market = [_market_entry("7", "QB", 70.0)]        # zero intersection
    with pytest.raises(CohortMismatchError) as excinfo:
        build_rebased_divergence(rows, market, snapshot_date="2026-07-26")
    assert "common_cohort_empty" in str(excinfo.value)


def test_refusal_names_the_position_that_has_no_common_members():
    rows = [_model_row("1", "QB", 10.0), _model_row("2", "QB", 9.0),
            _model_row("3", "WR", 5.0)]
    market = [_market_entry("1", "QB", 100.0), _market_entry("2", "QB", 90.0),
              _market_entry("8", "WR", 40.0)]
    report = build_rebased_divergence(rows, market, snapshot_date="2026-07-26")
    assert "WR" in report["positions_without_common_cohort"], (
        "a position with no intersection is named, not silently dropped")
    assert all(r["position"] == "QB" for r in report["rows"])


# ---------------------------------------------------------------- No-Verdict compliance


def test_report_is_descriptive_and_carries_no_verdict():
    """00 §Descriptive Tools Issue No Verdicts: the rebase reports quantities. It states
    no recommendation and marks itself not decision-supported."""
    rows = [_model_row("1", "QB", 30.0), _model_row("2", "QB", 20.0)]
    market = [_market_entry("1", "QB", 300.0), _market_entry("2", "QB", 200.0)]
    report = build_rebased_divergence(rows, market, snapshot_date="2026-07-26")
    assert report["decision_supported"] is False
    for row in report["rows"]:
        assert row["decision_supported"] is False
    banned = ("buy", "sell", "hold", "recommend", "should", "must", "safe to")
    blob = repr(report).lower()
    for word in banned:
        assert word not in blob, f"banned verdict language in a descriptive report: {word}"


def test_market_values_never_enter_the_model_side():
    """00 §KTC And Market Data: the market overlay never feeds the predictive score.
    Rebasing changes which POPULATION a value is ranked against, never the value."""
    rows = [_model_row("1", "QB", 30.0), _model_row("2", "QB", 20.0)]
    market = [_market_entry("1", "QB", 300.0), _market_entry("2", "QB", 200.0)]
    report = build_rebased_divergence(rows, market, snapshot_date="2026-07-26")
    by_id = {r["sleeper_id"]: r for r in report["rows"]}
    assert by_id["1"]["xvar"] == 30.0, "the model value is unchanged by rebasing"
    assert by_id["2"]["xvar"] == 20.0
