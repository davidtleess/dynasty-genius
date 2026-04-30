from app.services.rookie_evaluator import score_prospect

PICK_BASE_VALUES = {1: 80.0, 2: 45.0, 3: 20.0, 4: 10.0}

AGE_DISCOUNT = {
    "RB": {"baseline": 23, "rate": 0.12},
    "WR": {"baseline": 24, "rate": 0.09},
    "TE": {"baseline": 25, "rate": 0.08},
    "QB": {"baseline": 28, "rate": 0.07},
}

TRADE_NOT_DECISION_GRADE_REASON = (
    "Trade output is experimental: player scores use a rookie-model proxy plus "
    "manual age discounts, and pick scores use a static chart. This is not a "
    "decision-grade trade valuation."
)

REQUIRED_BEFORE_DECISION_GRADE = [
    "unified_valuation_layer_for_all_assets",
    "engine_b_active_player_forecast",
    "calibrated_uncertainty_by_position",
    "pick_values_from_slot_weighted_expected_rookie_scores",
    "market_overlay_available_for_sanity_checks",
]

TRADE_NOTES = [
    "trade_engine_internal_only",
    "no_verdict_until_unified_value_layer",
    "veteran_values_use_rookie_model_proxy",
    "pick_values_use_static_chart",
]


def value_pick(round_num: int, year: int, current_year: int = 2025) -> float:
    base = PICK_BASE_VALUES.get(round_num, 5.0)
    years_away = year - current_year
    if years_away <= 0:
        return base
    return round(base * (0.85 ** years_away), 1)


def value_player(position: str, age: int, pick: int, round_num: int) -> float:
    result = score_prospect(position=position, pick=pick, round_num=round_num, age=float(age))
    ppg = result["predicted_y24_ppg"]
    base = ppg * 6.0

    discount = AGE_DISCOUNT.get(position)
    if discount is None:
        return round(base, 1)

    age_multiplier = max(0.0, 1.0 - (max(0, age - discount["baseline"]) * discount["rate"]))
    return round(base * age_multiplier, 1)


def _asset_label(asset: dict) -> str:
    if asset["type"] == "pick":
        return f"{asset['year']} R{asset['round']}"
    return asset.get("name") or f"{asset.get('position', 'UNKNOWN')} player"


def _score_asset(asset: dict) -> dict:
    if asset["type"] == "pick":
        value = value_pick(round_num=asset["round"], year=asset["year"])
        return {
            **asset,
            "asset_type": "pick",
            "label": _asset_label(asset),
            "internal_score": value,
            "value": value,
            "score_status": "heuristic",
            "scoring_method": "static_pick_chart",
            "caveats": ["pick_value_from_static_chart"],
        }
    elif asset["type"] == "player":
        value = value_player(
            position=asset["position"],
            age=asset["age"],
            pick=asset["pick"],
            round_num=asset["round"],
        )
        return {
            **asset,
            "asset_type": "player",
            "label": _asset_label(asset),
            "internal_score": value,
            "value": value,
            "score_status": "heuristic",
            "scoring_method": "rookie_model_proxy_with_manual_age_discount",
            "engine": "rookie_forecast",
            "model_grade": "unvalidated_for_veteran_trade_value",
            "signal_completeness": "draft_capital_age_proxy",
            "caveats": ["veteran_value_uses_rookie_model_proxy"],
        }
    else:
        raise ValueError(f"Unknown asset type: {asset['type']}")


def analyze_trade(my_assets: list[dict], their_assets: list[dict]) -> dict:
    my_scored = [_score_asset(a) for a in my_assets]
    their_scored = [_score_asset(a) for a in their_assets]

    my_total = round(sum(a["internal_score"] for a in my_scored), 1)
    their_total = round(sum(a["internal_score"] for a in their_scored), 1)
    difference = round(my_total - their_total, 1)

    return {
        "status": "experimental",
        "decision_supported": False,
        "reason": TRADE_NOT_DECISION_GRADE_REASON,
        "required_before_decision_grade": REQUIRED_BEFORE_DECISION_GRADE,
        "notes": TRADE_NOTES,
        "my_assets_breakdown": my_scored,
        "their_assets_breakdown": their_scored,
        "experimental_totals": {
            "my_total": my_total,
            "their_total": their_total,
            "difference": difference,
            "status": "experimental",
            "caveat": "Totals aggregate heuristic player proxy scores and static pick values; do not use as a trade verdict.",
        },
        "deprecated_fields": {
            "verdict": "removed_until_unified_value_layer",
            "my_total": "use_experimental_totals.my_total_for_internal_debug_only",
            "their_total": "use_experimental_totals.their_total_for_internal_debug_only",
            "difference": "use_experimental_totals.difference_for_internal_debug_only",
        },
        "my_assets_scored": my_scored,
        "their_assets_scored": their_scored,
    }
