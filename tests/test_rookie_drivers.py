from app.services.rookie_evaluator import score_prospect


def _driver(result: dict, feature: str) -> dict:
    return next(item for item in result["top_drivers"] if item["feature"] == feature)


def test_top_pick_low_age_has_positive_draft_capital_direction() -> None:
    result = score_prospect(position="WR", pick=1, round_num=1, age=20.0, name="Top Prospect")
    draft_capital = _driver(result, "draft_capital")
    assert draft_capital["direction"] == "positive"


def test_late_pick_high_age_has_negative_draft_capital_direction() -> None:
    result = score_prospect(position="WR", pick=220, round_num=7, age=25.0, name="Late Prospect")
    draft_capital = _driver(result, "draft_capital")
    assert draft_capital["direction"] == "negative"


def test_rookie_response_has_no_confidence_key() -> None:
    result = score_prospect(position="RB", pick=24, round_num=1, age=21.3, name="No Confidence Field")
    assert "confidence" not in result
    assert result["compliance_header"] == "Compliance: 100% / 0% (PASS)"
    assert result["source_rank"] == 1
    assert result["valuation"]["source_rank"] == 1


def test_top_drivers_exclude_intercept_terms() -> None:
    result = score_prospect(position="TE", pick=45, round_num=2, age=22.4, name="No Intercept Driver")
    features = {driver["feature"] for driver in result["top_drivers"]}
    assert "intercept" not in features
    assert "model_intercept" not in features


def test_tier_1_prospect_has_ground_truth_anchor() -> None:
    result = score_prospect(position="RB", pick=14, round_num=1, age=21.0, name="Jeremiyah Love")
    assert result["ground_truth_check"]["status"] == "verified"
    assert result["ground_truth_check"]["classification"] == "tier_1_2026_prospect_anchor"
    assert result["threshold_flags"]["dominator_above_position_line"] is True
    assert result["threshold_flags"]["ras_above_8"] is True
    assert result["decision_weights"]["draft_capital_influence_tier"] == (
        "draft_capital_locked_70_percent_round_1_2"
    )
