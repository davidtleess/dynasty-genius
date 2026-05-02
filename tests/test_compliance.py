from app.models.valuation import DynastyValuation, ValuationEngine
from app.utils.compliance import (
    RANK_1_GROUND_TRUTH,
    RANK_2_VALIDATED_ANALYST,
    RANK_3_MARKET_SIGNAL,
    calculate_compliance_ratio,
)


def test_compliance_ratio_passes_at_65_quantitative_percent() -> None:
    result = calculate_compliance_ratio(
        [
            {
                "name": "draft_capital",
                "kind": "quantitative",
                "source_rank": RANK_1_GROUND_TRUTH,
                "weight": 0.65,
            },
            {
                "name": "scheme_note",
                "kind": "qualitative",
                "source_rank": RANK_2_VALIDATED_ANALYST,
                "weight": 0.35,
            },
        ],
        [],
    )

    assert result == "Compliance: 65% / 35% (PASS)"


def test_compliance_ratio_fails_market_only_quantitative_input() -> None:
    result = calculate_compliance_ratio(
        [
            {
                "name": "ktc_value",
                "kind": "quantitative",
                "source_rank": RANK_3_MARKET_SIGNAL,
                "weight": 1.0,
            }
        ],
        [],
    )

    assert result == "Compliance: 0% / 0% (FAIL)"


def test_dynasty_valuation_carries_source_rank() -> None:
    valuation = DynastyValuation(
        name="Source Ranked Prospect",
        position="RB",
        engine=ValuationEngine.ROOKIE_FORECAST,
        source_rank=RANK_1_GROUND_TRUTH,
        dynasty_value_score=10.0,
        projection_1y=10.0,
        projection_2y=10.0,
        projection_3y=10.0,
    )

    assert valuation.source_rank == 1
