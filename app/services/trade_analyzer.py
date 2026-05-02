from __future__ import annotations

from app.services.roster_auditor import CLIFF_AGES, ELITE_RB_YAC_PER_ATTEMPT

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
    "verdict_thresholds_calibrated_to_rmse",
]

TRADE_NOTES = [
    "trade_engine_internal_only",
    "no_verdict_until_unified_value_layer",
    "veteran_values_use_rookie_model_proxy",
    "pick_values_use_static_chart",
]

AGE_SELL_THRESHOLDS = {"RB": 26, "WR": 28}


def value_pick(round_num: int, year: int, current_year: int = 2025) -> float:
    base = PICK_BASE_VALUES.get(round_num, 5.0)
    years_away = year - current_year
    if years_away <= 0:
        return base
    return round(base * (0.85 ** years_away), 1)


def value_player(position: str, age: int, pick: int, round_num: int) -> tuple[float, str | None]:
    from app.services.rookie_evaluator import score_prospect

    result = score_prospect(position=position, pick=pick, round_num=round_num, age=float(age))
    ppg = result["predicted_y24_ppg"]
    base = ppg * 6.0

    discount = AGE_DISCOUNT.get(position)
    if discount is None:
        return round(base, 1), result.get("model_version")

    age_multiplier = max(0.0, 1.0 - (max(0, age - discount["baseline"]) * discount["rate"]))
    return round(base * age_multiplier, 1), result.get("model_version")


def _asset_label(asset: dict) -> str:
    if asset["type"] == "pick":
        return f"{asset['year']} R{asset['round']}"
    return asset.get("name") or f"{asset.get('position', 'UNKNOWN')} player"


def _ground_truth_check(asset: dict) -> dict:
    ground_truth = asset.get("ground_truth") or {}
    nfl_status = ground_truth.get("nfl_status") or asset.get("nfl_status")
    current_team = ground_truth.get("current_team") or asset.get("current_team") or asset.get("team")
    years_experience = ground_truth.get("years_experience", asset.get("years_experience"))
    source = ground_truth.get("source") or asset.get("ground_truth_source")

    verified = any(value is not None for value in (nfl_status, current_team, years_experience))
    check = {
        "status": "verified" if verified else "missing",
        "nfl_status": nfl_status,
        "current_team": current_team,
        "years_experience": years_experience,
        "source": source,
    }
    if verified and years_experience is not None and int(years_experience) > 0:
        check["classification"] = "active_nfl_veteran"
    elif verified:
        check["classification"] = "nfl_status_checked"
    else:
        check["classification"] = "unverified"
    return check


def _elite_rb_exception(asset: dict) -> bool:
    yac_per_attempt = asset.get("yards_after_contact_per_attempt")
    if yac_per_attempt is None:
        yac_per_attempt = asset.get("yac_per_attempt")
    return (
        asset.get("position") == "RB"
        and int(asset["age"]) >= CLIFF_AGES["RB"]
        and yac_per_attempt is not None
        and float(yac_per_attempt) >= ELITE_RB_YAC_PER_ATTEMPT
    )


def _asset_management_signal(asset: dict) -> str | None:
    position = asset.get("position")
    age = asset.get("age")
    if position is None or age is None:
        return None
    if _elite_rb_exception(asset):
        return "Elite Exception: HOLD"
    threshold = AGE_SELL_THRESHOLDS.get(position)
    if threshold is not None and int(age) >= threshold:
        return "Sell"
    return None


def _counter_argument(asset: dict, signal: str | None, ground_truth_check: dict) -> str:
    label = _asset_label(asset)
    if signal == "Sell":
        return (
            f"The strongest case against selling {label} is that age-curve pressure alone "
            "does not measure current usage, weekly contender value, injury recovery, or "
            "trade-market price; a contender may rationally hold if the verified role is elite."
        )
    if signal == "Elite Exception: HOLD":
        return (
            f"The strongest case against holding {label} is that even elite yards-after-contact "
            "efficiency can collapse quickly after the RB age cliff; the exception should be "
            "rechecked against current workload, injury status, and market liquidity."
        )
    if ground_truth_check["status"] != "verified":
        return (
            f"The strongest case against using {label}'s trade score is that NFL status has "
            "not been verified against ground truth, so the system may be stale or misclassify "
            "the player."
        )
    return (
        f"The strongest case against using {label}'s trade score is that this surface still "
        "uses a rookie-model proxy for active players and lacks Engine B usage, efficiency, "
        "market, and roster-context inputs."
    )


def _score_asset(asset: dict) -> dict:
    if asset["type"] == "pick":
        value = value_pick(round_num=asset["round"], year=asset["year"])
        return {
            **asset,
            "asset_type": "pick",
            "label": _asset_label(asset),
            "internal_score": value,
            "score_status": "heuristic",
            "scoring_method": "static_pick_chart",
            "caveats": ["pick_value_from_static_chart"],
        }
    elif asset["type"] == "player":
        value, model_version = value_player(
            position=asset["position"],
            age=asset["age"],
            pick=asset["pick"],
            round_num=asset["round"],
        )
        ground_truth_check = _ground_truth_check(asset)
        asset_management_signal = _asset_management_signal(asset)
        caveats = [
            "veteran_value_uses_rookie_model_proxy",
            "signal_completeness_not_applicable_to_trade_proxy",
        ]
        if ground_truth_check["status"] != "verified":
            caveats.append("ground_truth_status_unverified")
        if ground_truth_check["classification"] == "active_nfl_veteran":
            caveats.append("active_nfl_veteran_not_rookie_prospect")
        if asset_management_signal == "Sell":
            caveats.append("age_curve_sell_signal_only")
        elif asset_management_signal == "Elite Exception: HOLD":
            caveats.append("elite_exception_requires_current_yac_verification")
        return {
            **asset,
            "asset_type": "player",
            "label": _asset_label(asset),
            "internal_score": value,
            "score_status": "heuristic",
            "scoring_method": "rookie_model_proxy_with_manual_age_discount",
            "engine": "rookie_forecast",
            "model_version": model_version,
            "model_grade": "unvalidated",
            "ground_truth_check": ground_truth_check,
            "asset_management_signal": asset_management_signal,
            "counter_argument": _counter_argument(
                asset,
                asset_management_signal,
                ground_truth_check,
            ),
            "caveats": caveats,
        }
    else:
        raise ValueError(f"Unknown asset type: {asset['type']}")


def analyze_trade(my_assets: list[dict], their_assets: list[dict]) -> dict:
    my_scored = [_score_asset(a) for a in my_assets]
    their_scored = [_score_asset(a) for a in their_assets]
    model_version = next(
        (
            asset.get("model_version")
            for asset in [*my_scored, *their_scored]
            if asset.get("model_version") is not None
        ),
        None,
    )
    notes = list(TRADE_NOTES)
    if model_version is None:
        notes.append("model_version_unavailable_for_current_trade_assets")

    return {
        "status": "experimental",
        "decision_supported": False,
        "model_version": model_version,
        "reason": TRADE_NOT_DECISION_GRADE_REASON,
        "required_before_decision_grade": REQUIRED_BEFORE_DECISION_GRADE,
        "notes": notes,
        "my_assets_breakdown": my_scored,
        "their_assets_breakdown": their_scored,
    }
