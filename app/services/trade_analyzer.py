from __future__ import annotations

import math
from typing import Any, List, Optional
from datetime import datetime, timezone

from app.services.rookie_evaluator import score_prospect
from src.dynasty_genius.models.player_value_object import PlayerValueObject
from src.dynasty_genius.models.player_identity import PlayerIdentity
from src.dynasty_genius.pvo_assembler import assemble_pvo
from src.dynasty_genius.identity import generate_dg_id

# Validated RMSE values
POSITION_RMSE = {
    "QB": 4.508,
    "RB": 3.582,
    "WR": 2.887,
    "TE": 99.0,
}

TE_EXPERIMENTAL_CAVEAT = "engine_b_experimental_v1_fallback"

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


def value_pick(round_num: int, year: int, current_year: int = 2025) -> float:
    base = PICK_BASE_VALUES.get(round_num, 5.0)
    years_away = year - current_year
    if years_away <= 0:
        return base
    return round(base * (0.85 ** years_away), 1)


def value_player(position: str, age: int, pick: int, round_num: int) -> tuple[float, str | None]:
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
            "caveats": [
                "veteran_value_uses_rookie_model_proxy",
                "signal_completeness_not_applicable_to_trade_proxy",
            ],
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


def assemble_asset_pvo(asset: dict) -> PlayerValueObject:
    if asset["type"] == "player":
        name = asset.get("name", "Unknown Player")
        position = asset.get("position", "UNKNOWN").upper()
        dg_id = generate_dg_id(name, position)

        identity = PlayerIdentity(
            dg_id=dg_id,
            full_name=name,
            position=position,
            sleeper_id=asset.get("sleeper_id")
        )

        # Include all asset fields except type, name, position as features.
        # This allows passing engine_b_score or other signals for testing or enrichment.
        features = {k: v for k, v in asset.items() if k not in ["type", "name", "position"]}

        # If pick/round are present, treat as a prospect
        is_prospect = asset.get("pick") is not None or asset.get("round") is not None

        pvo = assemble_pvo(identity, features=features, is_prospect=is_prospect)

        # TE assets in either side carry "engine_b_experimental_v1_fallback" in caveats
        if position == "TE" and TE_EXPERIMENTAL_CAVEAT not in pvo.caveats:
            pvo.caveats.append(TE_EXPERIMENTAL_CAVEAT)

        # market_overlay is None on all asset PVOs
        pvo.market_overlay = None

        return pvo

    elif asset["type"] == "pick":
        return PlayerValueObject(
            player_id=f"pick_{asset['year']}_{asset['round']}",
            full_name=f"{asset['year']} Round {asset['round']} Pick",
            position="PICK",
            model_grade="PRE_MODEL",
            dynasty_value_score=None,
            projection_2y=None,
            signal_completeness=1.0,
            caveats=["pick_asset_no_player_model"]
        )
    else:
        raise ValueError(f"Unknown asset type: {asset['type']}")


def compute_delta_status(my_pvos: List[PlayerValueObject], their_pvos: List[PlayerValueObject]) -> str:
    def side_rmse(pvos: List[PlayerValueObject]) -> float:
        squared_sum = sum(
            POSITION_RMSE.get(pvo.position.upper(), 99.0)**2
            for pvo in pvos
            if pvo.projection_2y is not None
        )
        return math.sqrt(squared_sum)

    def side_projection(pvos: List[PlayerValueObject]) -> float:
        return sum(
            pvo.projection_2y
            for pvo in pvos
            if pvo.projection_2y is not None
        )

    my_proj = side_projection(my_pvos)
    my_rmse = side_rmse(my_pvos)
    their_proj = side_projection(their_pvos)
    their_rmse = side_rmse(their_pvos)

    # If either side has NO assets with a non-null projection_2y, delta_status must be "Within_Model_Error"
    my_has_proj = any(pvo.projection_2y is not None for pvo in my_pvos)
    their_has_proj = any(pvo.projection_2y is not None for pvo in their_pvos)

    if not my_has_proj or not their_has_proj:
        return "Within_Model_Error"

    left_lo = my_proj - my_rmse
    left_hi = my_proj + my_rmse
    right_lo = their_proj - their_rmse
    right_hi = their_proj + their_rmse

    overlap = max(0, min(left_hi, right_hi) - max(left_lo, right_lo))
    narrower_width = min(left_hi - left_lo, right_hi - right_lo)

    if narrower_width == 0 or overlap / narrower_width > 0.5:
        return "Within_Model_Error"
    elif left_lo > right_hi:
        return "Likely_Favors_You"
    else:
        return "Likely_Favors_Opponent"


def analyze_trade_pvo(my_assets: list[dict], their_assets: list[dict]) -> dict:
    my_pvos = [assemble_asset_pvo(a) for a in my_assets]
    their_pvos = [assemble_asset_pvo(a) for a in their_assets]

    from src.dynasty_genius.services.market_overlay_service import enrich_pvo_list_with_market_overlay
    enrich_pvo_list_with_market_overlay(my_pvos + their_pvos)

    delta_status = compute_delta_status(my_pvos, their_pvos)

    return {
        "status": "experimental",
        "engine": "trade_analyzer_pvo_v1",
        "decision_supported": False,
        "reason": "Trade output is experimental. Confidence bands are RMSE-proxied, not calibrated.",
        "caveats": [
            "no_calibrated_confidence_band",
            "no_market_overlay",
            "rmse_proxy_uncertainty"
        ],
        "delta_status": delta_status,
        "uncertainty_note": "RMSE: QB=4.51, RB=3.58, WR=2.89. TE model is experimental.",
        "my_assets": [pvo.dict() for pvo in my_pvos],
        "their_assets": [pvo.dict() for pvo in their_pvos]
    }
