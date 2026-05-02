from __future__ import annotations

from app.services.roster_auditor import CLIFF_AGES, ELITE_RB_YAC_PER_ATTEMPT
from app.utils.compliance import (
    RANK_1_GROUND_TRUTH,
    RANK_3_MARKET_SIGNAL,
    calculate_compliance_ratio,
)

VALUATION_STATUS_OK = "VALUATION_STATUS_OK"
VALUATION_STATUS_PENDING_ENGINE_B = "VALUATION_STATUS_PENDING_ENGINE_B"
VALUATION_STATUS_PENDING_GROUND_TRUTH = "VALUATION_STATUS_PENDING_GROUND_TRUTH"
VALUATION_STATUS_PENDING_MARKET_ANCHOR = "VALUATION_STATUS_PENDING_MARKET_ANCHOR"

DVU_PER_101_PICK = 100.0
GENERATIONAL_2027_FIRST_FLOOR_DVU = 120.0
STATIC_PICK_DVU_VALUES = {1: 100.0, 2: 56.25, 3: 25.0, 4: 12.5}

TRADE_NOT_DECISION_GRADE_REASON = (
    "Trade output is experimental: active-player valuations are blocked until "
    "Engine B exists, and pick/market math is normalized to DVU for inspection only."
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
    "veteran_values_pending_engine_b",
    "trade_math_uses_dvu_normalization",
]

AGE_SELL_THRESHOLDS = {"RB": 26, "WR": 28}


def _round_dvu(value: float | None) -> float | None:
    if value is None:
        return None
    rounded = round(value, 1)
    return 0.0 if rounded == 0 else rounded


def _market_to_dvu(asset: dict) -> tuple[float | None, str | None]:
    market_value = asset.get("market_value", asset.get("ktc_value"))
    if market_value is None:
        return None, None

    scale = asset.get("market_value_scale")
    if scale == "dvu":
        return _round_dvu(float(market_value)), "market_value_already_dvu"
    if scale == "one_oh_one_ratio":
        return _round_dvu(float(market_value) * DVU_PER_101_PICK), "market_value_101_pick_ratio"

    one_oh_one_value = asset.get("market_101_pick_value")
    if one_oh_one_value is None:
        return None, VALUATION_STATUS_PENDING_MARKET_ANCHOR
    if float(one_oh_one_value) <= 0:
        return None, VALUATION_STATUS_PENDING_MARKET_ANCHOR
    return (
        _round_dvu((float(market_value) / float(one_oh_one_value)) * DVU_PER_101_PICK),
        "market_value_normalized_to_dvu",
    )


def _asset_compliance_header(asset: dict, ground_truth_check: dict | None = None) -> str:
    metrics: list[dict] = []
    if asset["type"] == "pick":
        metrics.append(
            {
                "name": "pick_dvu_normalization",
                "kind": "quantitative",
                "source_rank": RANK_1_GROUND_TRUTH,
                "weight": 0.70,
            }
        )
        if asset.get("market_value", asset.get("ktc_value")) is not None:
            metrics.append(
                {
                    "name": "market_price_signal",
                    "kind": "quantitative",
                    "source_rank": RANK_3_MARKET_SIGNAL,
                    "weight": 0.30,
                }
            )
        return calculate_compliance_ratio(metrics, [])

    if ground_truth_check and ground_truth_check.get("status") == "verified":
        metrics.append(
            {
                "name": "nfl_status_ground_truth_check",
                "kind": "quantitative",
                "source_rank": RANK_1_GROUND_TRUTH,
                "weight": 1.0,
            }
        )
    return calculate_compliance_ratio(metrics, [])


def value_pick_dvu(round_num: int, year: int, current_year: int = 2025) -> float:
    if year == 2027 and round_num == 1:
        return GENERATIONAL_2027_FIRST_FLOOR_DVU
    base = STATIC_PICK_DVU_VALUES.get(round_num, 6.25)
    years_away = year - current_year
    if years_away <= 0:
        return base
    return round(base * (0.85 ** years_away), 1)


def value_player(asset: dict, ground_truth_check: dict) -> dict:
    years_in_nfl = ground_truth_check.get("years_experience")
    if years_in_nfl is None:
        years_in_nfl = asset.get("years_in_nfl")

    if years_in_nfl is None:
        return {
            "valuation_status": VALUATION_STATUS_PENDING_GROUND_TRUTH,
            "internal_score": None,
            "dvu": None,
            "model_version": None,
            "error": "ground_truth_years_in_nfl_required_before_player_trade_valuation",
        }
    if int(years_in_nfl) > 0:
        return {
            "valuation_status": VALUATION_STATUS_PENDING_ENGINE_B,
            "internal_score": None,
            "dvu": None,
            "model_version": None,
            "error": "active_player_trade_valuation_blocked_until_engine_b",
        }

    market_dvu, market_source_or_status = _market_to_dvu(asset)
    if market_source_or_status == VALUATION_STATUS_PENDING_MARKET_ANCHOR:
        return {
            "valuation_status": VALUATION_STATUS_PENDING_MARKET_ANCHOR,
            "internal_score": None,
            "dvu": None,
            "model_version": None,
            "error": "market_value_requires_market_101_pick_value_to_normalize_to_dvu",
        }
    if market_dvu is not None:
        return {
            "valuation_status": VALUATION_STATUS_OK,
            "internal_score": market_dvu,
            "dvu": market_dvu,
            "model_version": None,
            "scoring_method": market_source_or_status,
        }

    from app.services.rookie_evaluator import score_prospect

    result = score_prospect(
        position=asset["position"],
        pick=asset["pick"],
        round_num=asset["round"],
        age=float(asset["age"]),
    )
    dvu = _round_dvu(result["predicted_y24_ppg"])
    return {
        "valuation_status": VALUATION_STATUS_OK,
        "internal_score": dvu,
        "dvu": dvu,
        "model_version": result.get("model_version"),
        "scoring_method": "engine_a_rookie_forecast_dvu_proxy",
    }


def _asset_label(asset: dict) -> str:
    if asset["type"] == "pick":
        return f"{asset['year']} R{asset['round']}"
    return asset.get("name") or f"{asset.get('position', 'UNKNOWN')} player"


def _ground_truth_check(asset: dict) -> dict:
    ground_truth = asset.get("ground_truth") or {}
    nfl_status = ground_truth.get("nfl_status") or asset.get("nfl_status")
    current_team = ground_truth.get("current_team") or asset.get("current_team") or asset.get("team")
    years_experience = ground_truth.get(
        "years_experience",
        asset.get("years_experience", asset.get("years_in_nfl")),
    )
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
        market_dvu, market_source_or_status = _market_to_dvu(asset)
        caveats = ["pick_value_normalized_to_dvu"]
        if asset["year"] == 2027 and asset["round"] == 1:
            caveats.append("generational_anchor_2027_first_floor_120_dvu")
        if market_source_or_status == VALUATION_STATUS_PENDING_MARKET_ANCHOR:
            caveats.append("market_value_requires_dvu_anchor")
            value = None
            scoring_method = "pending_market_anchor"
            valuation_status = VALUATION_STATUS_PENDING_MARKET_ANCHOR
        elif market_dvu is None:
            value = value_pick_dvu(round_num=asset["round"], year=asset["year"])
            scoring_method = "static_pick_chart_dvu"
            valuation_status = VALUATION_STATUS_OK
        else:
            value = market_dvu
            scoring_method = market_source_or_status
            valuation_status = VALUATION_STATUS_OK
        return {
            **asset,
            "compliance_header": _asset_compliance_header(asset),
            "asset_type": "pick",
            "label": _asset_label(asset),
            "internal_score": value,
            "dvu": value,
            "valuation_status": valuation_status,
            "score_status": "heuristic",
            "scoring_method": scoring_method,
            "caveats": caveats,
        }
    elif asset["type"] == "player":
        ground_truth_check = _ground_truth_check(asset)
        valuation = value_player(asset, ground_truth_check)
        asset_management_signal = _asset_management_signal(asset)
        caveats = ["trade_player_value_requires_ground_truth"]
        if ground_truth_check["status"] != "verified":
            caveats.append("ground_truth_status_unverified")
        if ground_truth_check["classification"] == "active_nfl_veteran":
            caveats.append("active_nfl_veteran_not_rookie_prospect")
        if valuation["valuation_status"] == VALUATION_STATUS_PENDING_ENGINE_B:
            caveats.append("active_player_valuation_pending_engine_b")
        elif valuation["valuation_status"] == VALUATION_STATUS_PENDING_MARKET_ANCHOR:
            caveats.append("market_value_requires_dvu_anchor")
        elif valuation.get("scoring_method") == "engine_a_rookie_forecast_dvu_proxy":
            caveats.append("engine_a_rookie_only")
        if asset_management_signal == "Sell":
            caveats.append("age_curve_sell_signal_only")
        elif asset_management_signal == "Elite Exception: HOLD":
            caveats.append("elite_exception_requires_current_yac_verification")
        return {
            **asset,
            "compliance_header": _asset_compliance_header(asset, ground_truth_check),
            "asset_type": "player",
            "label": _asset_label(asset),
            "internal_score": valuation["internal_score"],
            "dvu": valuation["dvu"],
            "valuation_status": valuation["valuation_status"],
            "valuation_error": valuation.get("error"),
            "score_status": "heuristic",
            "scoring_method": valuation.get("scoring_method", "pending"),
            "engine": "pending_engine_b" if valuation["valuation_status"] == VALUATION_STATUS_PENDING_ENGINE_B else "rookie_forecast",
            "model_version": valuation["model_version"],
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
    my_dvu_total = _round_dvu(
        sum(asset["dvu"] for asset in my_scored if asset.get("dvu") is not None)
    )
    their_dvu_total = _round_dvu(
        sum(asset["dvu"] for asset in their_scored if asset.get("dvu") is not None)
    )
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
    compliance_metrics = [
        {
            "name": "ground_truth_checked_assets",
            "kind": "quantitative",
            "source_rank": RANK_1_GROUND_TRUTH,
            "weight": 1.0,
        }
    ]
    if any(
        asset.get("market_value", asset.get("ktc_value")) is not None
        for asset in [*my_assets, *their_assets]
    ):
        compliance_metrics.append(
            {
                "name": "market_signal_overlay",
                "kind": "quantitative",
                "source_rank": RANK_3_MARKET_SIGNAL,
                "weight": 0.30,
            }
        )

    return {
        "compliance_header": calculate_compliance_ratio(compliance_metrics, []),
        "status": "experimental",
        "decision_supported": False,
        "model_version": model_version,
        "reason": TRADE_NOT_DECISION_GRADE_REASON,
        "required_before_decision_grade": REQUIRED_BEFORE_DECISION_GRADE,
        "notes": notes,
        "dvu_normalization": {
            "unit": "DVU",
            "one_oh_one_rookie_pick_value": DVU_PER_101_PICK,
            "aggregation_status": "partial_pending_engine_b",
            "my_assets_dvu_total": my_dvu_total,
            "their_assets_dvu_total": their_dvu_total,
            "excluded_asset_labels": [
                asset["label"]
                for asset in [*my_scored, *their_scored]
                if asset.get("dvu") is None
            ],
        },
        "my_assets_breakdown": my_scored,
        "their_assets_breakdown": their_scored,
    }
