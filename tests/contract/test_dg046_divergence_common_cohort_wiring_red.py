"""DG-046 RED — production divergence must rank against the COMMON cohort.

Written test-first 2026-08-26 (David's "1 yes", same day as the layer audit that
found the rebase built-but-dark). The shipped builder ranks a player's model value
against ALL model-backed rows and its market value against ALL market-priced rows —
different populations, uninterpretable delta (the module's own docstring for
`market_divergence_rebase` says exactly this). After DG-046, the served
percentiles rank both lanes against the players carrying BOTH a model-backed xVAR
and a market value — per position, the same inclusion rule
`market_divergence_rebase.INCLUSION_RULE` names — and the artifact says so.

Fixtures are tiny and synthetic. `min_cohort_size` is passed explicitly so the
small-cohort gate never hides the property under test (except in the test that
targets the gate itself).
"""

from __future__ import annotations

from src.dynasty_genius.market_divergence_rebase import (
    INCLUSION_RULE,
    build_rebased_divergence,
)
from src.dynasty_genius.services.market_overlay_service import pct_rank
from src.dynasty_genius.universe_market_divergence import (
    build_universe_market_divergence,
)


def _model_row(sleeper_id: str, xvar: float, position: str = "RB") -> dict:
    return {
        "sleeper_player_id": sleeper_id,
        "identity_status": "resolved",
        "player": {"position": position, "full_name": f"P{sleeper_id}"},
        "valuation": {
            "xvar": xvar,
            "engine_path": "ENGINE_B",
            "valuation_status": "MODEL_SUPPORTED",
        },
    }


def _fc_entry(sleeper_id: str, value: float, position: str = "RB") -> dict:
    return {
        "player": {"sleeperId": sleeper_id, "position": position},
        "value": value,
        "maybeMovingStandardDeviation": None,
        "trend30Day": 0,
    }


def _build(min_cohort_size: int = 2):
    """Universe: A(10), B(20), C(30) model-backed; market prices A, B and a
    stranger X(50, below both) who is not in the universe. Common cohort = {A, B}.
    C sits ABOVE the cohort on the model side while X sits BELOW it on the market
    side — asymmetric on purpose, so mismatched-population deltas differ from
    rebased ones and the cross-proof test can actually fail on the old code."""
    batch = {"players": [_model_row("a1", 10.0), _model_row("b2", 20.0), _model_row("c3", 30.0)]}
    fc = [_fc_entry("a1", 100.0), _fc_entry("b2", 200.0), _fc_entry("x9", 50.0)]
    result = build_universe_market_divergence(
        batch,
        fc,
        market_source_timestamp="2026-08-26T12:00:00Z",
        market_snapshot_date="2026-08-26",
        min_cohort_size=min_cohort_size,
    )
    rows = {r["sleeper_player_id"]: r for r in result["players"]}
    return result, rows, batch, fc


class TestCommonCohortRanking:
    def test_model_percentile_ranks_only_the_common_cohort(self):
        _, rows, _, _ = _build()
        div = rows["a1"]["divergence"]
        assert div["model_percentile"] == round(pct_rank([10.0, 20.0], 10.0), 3)
        assert div["model_percentile"] != round(pct_rank([10.0, 20.0, 30.0], 10.0), 3)

    def test_market_percentile_ranks_only_the_common_cohort(self):
        _, rows, _, _ = _build()
        div = rows["a1"]["divergence"]
        assert div["market_percentile"] == round(pct_rank([100.0, 200.0], 100.0), 3)
        assert div["market_percentile"] != round(
            pct_rank([100.0, 200.0, 999.0], 100.0), 3
        )

    def test_served_delta_equals_the_rebase_modules_rebased_delta(self):
        """The cross-proof: production now serves exactly what the proof module
        calls `rebased`. If the two ever drift, this is the tripwire."""
        _, rows, batch, fc = _build()
        report = build_rebased_divergence(
            batch["players"], fc, snapshot_date="2026-08-26"
        )
        rebased = {r["sleeper_id"]: r for r in report["rows"]}
        for sid in ("a1", "b2"):
            assert (
                rows[sid]["divergence"]["model_minus_market_delta"]
                == rebased[sid]["rebased_delta"]
            )

    def test_non_cohort_model_row_stays_unavailable_not_ranked(self):
        _, rows, _, _ = _build()
        div = rows["c3"]["divergence"]
        assert div["signal"] == "UNAVAILABLE"
        assert div["model_minus_market_delta"] is None


class TestCohortDisclosure:
    def test_delta_rows_carry_the_inclusion_rule_and_population(self):
        _, rows, _, _ = _build()
        cohort = rows["a1"]["divergence"]["cohort"]
        assert cohort["inclusion_rule"] == INCLUSION_RULE
        assert cohort["population"] == 2

    def test_batch_header_declares_the_cohort_method(self):
        result, _, _, _ = _build()
        method = result["divergence_cohort_method"]
        assert method["inclusion_rule"] == INCLUSION_RULE
        assert method["populations"] == {"RB": 2}


class TestSmallCohortGate:
    def test_gate_judges_the_common_population_not_the_inflated_ones(self):
        """Old populations here are size 3 (model) and 3 (market); the common
        cohort is 2. With min_cohort_size=3 the gate must FIRE — a gate that
        judges the inflated populations would silently pass."""
        _, rows, _, _ = _build(min_cohort_size=3)
        div = rows["a1"]["divergence"]
        assert "small_cohort" in div["failed_gates"]
