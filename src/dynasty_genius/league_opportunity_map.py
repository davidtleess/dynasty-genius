from __future__ import annotations

import copy
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.dynasty_genius.roster_cut_engine import RosterCutCandidate, RosterCutResult
from src.dynasty_genius.team_posture import apply_team_postures

SCHEMA_VERSION = "league_opportunity.v2"
BANNED_LANGUAGE = frozenset({"buy", "sell", "target", "fade"})
SKILL_POSITIONS = ("QB", "RB", "WR", "TE")
SURPLUS_THRESHOLD = 0.75
DEFICIT_THRESHOLD = -0.75
DEFAULT_MAX_CARDS = 20


def _team_by_roster(team_matrix: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {int(team["roster_id"]): team for team in team_matrix.get("teams") or []}


def _player_by_sleeper(market_divergence: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("sleeper_player_id")): row
        for row in market_divergence.get("players") or []
        if row.get("sleeper_player_id") is not None
    }


def _rostered_market_rows(market_divergence: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    by_roster: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in market_divergence.get("players") or []:
        context = row.get("league_context") or {}
        roster_id = context.get("roster_id")
        if context.get("rostered") and roster_id is not None:
            by_roster[int(roster_id)].append(row)
    return by_roster


def _safe_score(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 3)


def _position_z(team: dict[str, Any], position: str) -> float:
    return float(((team.get("positional_summary") or {}).get(position) or {}).get("z_score") or 0.0)


def _position_label(team: dict[str, Any], position: str) -> str:
    summary = ((team.get("positional_summary") or {}).get(position) or {})
    label = summary.get("surplus_label")
    if label:
        return str(label)
    z_score = _position_z(team, position)
    if z_score >= SURPLUS_THRESHOLD:
        return "surplus"
    if z_score <= DEFICIT_THRESHOLD:
        return "deficit"
    return "neutral"


def _asset_from_market_row(row: dict[str, Any]) -> dict[str, Any]:
    player = row.get("player") or {}
    return {
        "sleeper_player_id": row.get("sleeper_player_id"),
        "dg_player_id": row.get("dg_player_id"),
        "full_name": player.get("full_name"),
        "position": player.get("position"),
    }


# No-Verdict T3: the hidden weighted composite score (a blended grade used as a
# cross-type priority ranking) is removed. Cards instead carry a
# transparent, per-category sort metric — exposed via a named `sort_key` + the
# raw `sort_value` — so the surface is "sorted by X" not "the tool ranked your
# moves". `evidence_status` describes the mechanical evidence gate (NOT a
# calibration/trust verdict on the unvalidated divergence).
_EVIDENCE_STATUS_BY_SIGNAL = {
    "gates_passed": "evidence_complete",
    "gates_blocked": "evidence_gated",
    "unavailable": "inputs_unavailable",
}


def _evidence_status(signal_status: str | None) -> str:
    return _EVIDENCE_STATUS_BY_SIGNAL.get(str(signal_status or "unavailable"), "inputs_unavailable")


def _base_card(
    *,
    card_id: str,
    card_type: str,
    perspective_roster_id: int,
    counterparty_team: dict[str, Any] | None,
    asset: dict[str, Any] | None,
    primary: str,
    secondary: list[str],
    evidence: dict[str, Any],
    score_components: dict[str, float],
    signal_status: str,
    sort_key: str,
    sort_value: float,
    caveats: list[str] | None = None,
) -> dict[str, Any]:
    # Normalize an overlay evidence dict's mechanical gate key to the neutral name.
    rationale_evidence = dict(evidence)
    if "signal_status" in rationale_evidence:
        rationale_evidence["evidence_status"] = _evidence_status(
            rationale_evidence.pop("signal_status")
        )
    return {
        "schema_version": "opportunity.v2",
        "card_id": card_id,
        "card_type": card_type,
        "perspective_roster_id": perspective_roster_id,
        "counterparty_roster_id": counterparty_team.get("roster_id") if counterparty_team else None,
        "counterparty_team_name": ((counterparty_team or {}).get("owner") or {}).get("team_name")
        or ((counterparty_team or {}).get("owner") or {}).get("display_name"),
        "asset": asset,
        "rationale": {
            "primary": primary,
            "secondary": secondary,
            "evidence": rationale_evidence,
        },
        "score_components": score_components,
        "evidence_status": _evidence_status(signal_status),
        "sort_key": sort_key,
        "sort_value": round(float(sort_value), 3),
        "decision_supported": False,
        "caveats": caveats or [],
    }


def _counterparty_best_player(team: dict[str, Any], position: str) -> dict[str, Any] | None:
    candidates = [
        player
        for player in team.get("players") or []
        if player.get("position") == position and player.get("raw_xvar") is not None
    ]
    if not candidates:
        return None
    best = max(candidates, key=lambda player: float(player.get("raw_xvar") or 0.0))
    return {
        "sleeper_player_id": best.get("sleeper_player_id"),
        "dg_player_id": None,
        "full_name": best.get("full_name"),
        "position": best.get("position"),
    }


def build_partner_rankings(
    team_matrix: dict[str, Any],
    market_divergence: dict[str, Any],
    *,
    perspective_roster_id: int,
) -> list[dict[str, Any]]:
    teams = _team_by_roster(team_matrix)
    perspective = teams[perspective_roster_id]
    rostered_rows = _rostered_market_rows(market_divergence)
    rankings: list[dict[str, Any]] = []

    for roster_id, team in teams.items():
        if roster_id == perspective_roster_id:
            continue
        matched_positions: list[str] = []
        position_scores: dict[str, float] = {}
        for position in SKILL_POSITIONS:
            david_z = _position_z(perspective, position)
            counterparty_z = _position_z(team, position)
            if david_z <= DEFICIT_THRESHOLD and counterparty_z >= SURPLUS_THRESHOLD:
                matched_positions.append(position)
                position_scores[position] = _safe_score((abs(david_z) + counterparty_z) / 4.0)

        complementarity_score = max(position_scores.values(), default=0.0)
        divergence_rows = [
            row
            for row in rostered_rows.get(roster_id, [])
            if (row.get("divergence") or {}).get("signal")
            in {"MODEL_HIGH_MARKET_LOW", "MODEL_LOW_MARKET_HIGH"}
        ]
        divergence_density_score = _safe_score(len(divergence_rows) / 5.0)
        activity_recency_score = 0.0
        perspective_posture = ((perspective.get("posture") or {}).get("label") or "UNCLASSIFIED")
        counterparty_posture = ((team.get("posture") or {}).get("label") or "UNCLASSIFIED")
        posture_alignment_score = _posture_alignment_score(str(perspective_posture), str(counterparty_posture))
        partner_score = round(
            complementarity_score
            + divergence_density_score
            + activity_recency_score
            + posture_alignment_score,
            3,
        )
        rankings.append(
            {
                "counterparty_roster_id": roster_id,
                "counterparty_team_name": (team.get("owner") or {}).get("team_name")
                or (team.get("owner") or {}).get("display_name"),
                "partner_score": partner_score,
                "matched_positions": matched_positions,
                "score_components": {
                    "complementarity_score": complementarity_score,
                    "divergence_density_score": divergence_density_score,
                    "activity_recency_score": activity_recency_score,
                    "posture_alignment_score": posture_alignment_score,
                },
                "evidence": {
                    "position_scores": position_scores,
                    "divergence_row_count": len(divergence_rows),
                    "perspective_posture": perspective_posture,
                    "counterparty_posture": counterparty_posture,
                },
                "decision_supported": False,
            }
        )

    return sorted(rankings, key=lambda row: row["partner_score"], reverse=True)


def _posture_alignment_score(perspective_posture: str, counterparty_posture: str) -> float:
    if "UNCLASSIFIED" in {perspective_posture, counterparty_posture}:
        return 0.0
    if perspective_posture == counterparty_posture:
        return 0.05
    complementary_pairs = {
        frozenset({"CONTENDER", "REBUILDING"}): 0.25,
        frozenset({"CONTENDER", "ASCENDING"}): 0.15,
        frozenset({"BALANCED", "CONTENDER"}): 0.10,
        frozenset({"BALANCED", "REBUILDING"}): 0.10,
        frozenset({"BALANCED", "ASCENDING"}): 0.10,
        frozenset({"TRANSITIONAL", "CONTENDER"}): 0.10,
        frozenset({"TRANSITIONAL", "REBUILDING"}): 0.10,
    }
    return complementary_pairs.get(frozenset({perspective_posture, counterparty_posture}), 0.0)


def _fit_card_caveats(perspective: dict[str, Any], team: dict[str, Any]) -> list[str]:
    p_label = ((perspective.get("posture") or {}).get("label") or "UNCLASSIFIED")
    c_label = ((team.get("posture") or {}).get("label") or "UNCLASSIFIED")
    caveats = []
    if "UNCLASSIFIED" in {p_label, c_label}:
        caveats.append("posture_unclassified")
    caveats.append("future_pick_values_deferred")
    return caveats


def _fit_cards(
    teams: dict[int, dict[str, Any]],
    perspective_roster_id: int,
    card_start: int,
) -> list[dict[str, Any]]:
    perspective = teams[perspective_roster_id]
    cards: list[dict[str, Any]] = []
    card_no = card_start
    for roster_id, team in teams.items():
        if roster_id == perspective_roster_id:
            continue
        for position in SKILL_POSITIONS:
            david_z = _position_z(perspective, position)
            counterparty_z = _position_z(team, position)
            if david_z > DEFICIT_THRESHOLD or counterparty_z < SURPLUS_THRESHOLD:
                continue
            fit_score = _safe_score((abs(david_z) + counterparty_z) / 4.0)
            # Transparent roster-fit sort: positional z-score differential
            # (deficit magnitude on our side + surplus on theirs). No blend.
            z_differential = round(abs(david_z) + counterparty_z, 3)
            asset = _counterparty_best_player(team, position)
            cards.append(
                _base_card(
                    card_id=f"opp-{card_no:04d}",
                    card_type="ROSTER_SURPLUS_DEFICIT_MATCH",
                    perspective_roster_id=perspective_roster_id,
                    counterparty_team=team,
                    asset=asset,
                    primary="POSITIONAL_SURPLUS_ON_COUNTERPARTY",
                    secondary=["PERSPECTIVE_POSITIONAL_DEFICIT"],
                    evidence={
                        "position": position,
                        "perspective_position_z": david_z,
                        "counterparty_position_z": counterparty_z,
                        "positional_z_differential": z_differential,
                        "counterparty_surplus_label": _position_label(team, position),
                        "perspective_surplus_label": _position_label(perspective, position),
                    },
                    score_components={
                        "fit_score": fit_score,
                        "divergence_score": 0.0,
                        "feasibility_score": 0.5,
                    },
                    signal_status="gates_blocked",
                    sort_key="positional_z_differential_desc",
                    sort_value=z_differential,
                    caveats=_fit_card_caveats(perspective, team),
                )
            )
            card_no += 1
    return cards


def _divergence_cards(
    market_divergence: dict[str, Any],
    teams: dict[int, dict[str, Any]],
    perspective_roster_id: int,
    card_start: int,
) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    card_no = card_start
    for row in market_divergence.get("players") or []:
        divergence = row.get("divergence") or {}
        signal = divergence.get("signal")
        if signal not in {"MODEL_HIGH_MARKET_LOW", "MODEL_LOW_MARKET_HIGH"}:
            continue
        context = row.get("league_context") or {}
        roster_id = context.get("roster_id")
        if context.get("on_taxi") and roster_id == perspective_roster_id:
            continue
        if not context.get("rostered"):
            continue
        counterparty_team = teams.get(int(roster_id)) if roster_id is not None else None
        if counterparty_team is None:
            continue
        delta = float(divergence.get("model_minus_market_delta") or 0.0)
        card_type = "DIVERGENCE_MODEL_HIGH" if signal == "MODEL_HIGH_MARKET_LOW" else "DIVERGENCE_MARKET_HIGH"
        cards.append(
            _base_card(
                card_id=f"opp-{card_no:04d}",
                card_type=card_type,
                perspective_roster_id=perspective_roster_id,
                counterparty_team=counterparty_team,
                asset=_asset_from_market_row(row),
                primary="MODEL_MARKET_ASYMMETRY",
                secondary=["FANTASYCALC_PERCENTILE_DIVERGENCE"],
                evidence={
                    "signal": signal,
                    "signal_status": divergence.get("signal_status"),
                    "model_minus_market_delta": delta,
                    "asset_xvar": (row.get("valuation") or {}).get("xvar"),
                    "model_percentile": divergence.get("model_percentile"),
                    "market_percentile": divergence.get("market_percentile"),
                    "asset_roster_id": roster_id,
                },
                score_components={
                    "fit_score": 0.0 if roster_id == perspective_roster_id else 0.35,
                    "divergence_score": _safe_score(abs(delta)),
                    "feasibility_score": 0.5,
                },
                signal_status=str(divergence.get("signal_status") or "unavailable"),
                sort_key="absolute_model_market_delta_desc",
                sort_value=abs(delta),
                caveats=["market_overlay_context_only"],
            )
        )
        card_no += 1
    return cards


# Descriptive capacity pool: the No-Verdict reconcile replaces the old
# tool-selected single-drop field (which nominated a single cut target via
# position-matching + priority fallback) with the FULL set of capacity
# candidates, ordered transparently and never narrowed to one "the tool picks".
# The pool exposes roster constraints (hard rules conflicts, single-candidate
# pressure, empty) without nominating an action. ``decision_supported`` is False
# at every level.
_CAPACITY_POOL_SORT_KEY = "xvar_pct_ascending_then_full_name_then_sleeper_player_id"
_CAPACITY_POOL_SELECTION_RULE = "descriptive_candidate_pool_no_tool_selection"


def _capacity_candidate_item(candidate: RosterCutCandidate) -> dict[str, Any]:
    valued = candidate.xvar_pct is not None
    hard_conflict = candidate.cut_priority == 0
    item_caveats: list[str] = []
    if not valued:
        item_caveats.append("valuation_unavailable")
    return {
        "sleeper_player_id": candidate.sleeper_player_id,
        "full_name": candidate.full_name,
        "position": candidate.position,
        "value_status": "valued" if valued else "unvalued",
        "xvar_pct": candidate.xvar_pct,
        "dvs": candidate.dvs,
        "capacity_conflict_status": (
            "hard_roster_rules_conflict" if hard_conflict else "roster_capacity_pressure"
        ),
        "rule_conflict_label": "IR compliance violation" if hard_conflict else None,
        "caveats": item_caveats,
        "decision_supported": False,
    }


def _roster_capacity_candidate_pool(
    cut_candidates: list[RosterCutCandidate],
) -> dict[str, Any]:
    ordered = sorted(
        cut_candidates,
        key=lambda c: (
            c.xvar_pct is None,
            c.xvar_pct if c.xvar_pct is not None else 0.0,
            c.full_name,
            c.sleeper_player_id,
        ),
    )
    items = [_capacity_candidate_item(c) for c in ordered]
    if not items:
        pool_status = "empty"
        narrowing_rule = "no_safe_capacity_candidates"
        pool_caveats = ["capacity_blocks_move_unless_protected_player_cut"]
    elif len(items) == 1:
        pool_status = "constrained_single_candidate"
        narrowing_rule = "only_one_capacity_candidate_available"
        pool_caveats = []
    else:
        pool_status = "available"
        narrowing_rule = "all_capacity_candidates"
        pool_caveats = []
    return {
        "decision_supported": False,
        "pool_status": pool_status,
        "selection_rule": _CAPACITY_POOL_SELECTION_RULE,
        "narrowing_rule": narrowing_rule,
        "sort_key": _CAPACITY_POOL_SORT_KEY,
        "items": items,
        "caveats": pool_caveats,
    }


def _waiver_cards(
    market_divergence: dict[str, Any],
    perspective_roster_id: int,
    card_start: int,
    roster_cut_result: RosterCutResult | None = None,
) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    card_no = card_start
    for row in market_divergence.get("players") or []:
        context = row.get("league_context") or {}
        divergence = row.get("divergence") or {}
        if context.get("rostered") or divergence.get("signal") != "MODEL_HIGH_MARKET_LOW":
            continue
        delta = float(divergence.get("model_minus_market_delta") or 0.0)
        card = _base_card(
            card_id=f"opp-{card_no:04d}",
            card_type="UNROSTERED_MODEL_MARKET_DIVERGENCE",
            perspective_roster_id=perspective_roster_id,
            counterparty_team=None,
            asset=_asset_from_market_row(row),
            primary="UNROSTERED_MODEL_MARKET_ASYMMETRY",
            secondary=["FANTASYCALC_PERCENTILE_DIVERGENCE"],
            evidence={
                "signal": divergence.get("signal"),
                "signal_status": divergence.get("signal_status"),
                "model_minus_market_delta": delta,
                "asset_xvar": (row.get("valuation") or {}).get("xvar"),
            },
            score_components={
                "fit_score": 0.4,
                "divergence_score": _safe_score(abs(delta)),
                "feasibility_score": 0.9,
            },
            signal_status=str(divergence.get("signal_status") or "unavailable"),
            sort_key="absolute_model_market_delta_desc",
            sort_value=abs(delta),
            caveats=["waiver_status_from_sleeper_snapshot"],
        )
        if roster_cut_result is not None:
            card["roster_capacity_candidates"] = _roster_capacity_candidate_pool(
                roster_cut_result.cut_candidates
            )
        cards.append(card)
        card_no += 1
    return cards


def _taxi_cards(
    teams: dict[int, dict[str, Any]],
    player_index: dict[str, dict[str, Any]],
    perspective_roster_id: int,
    card_start: int,
) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    card_no = card_start
    perspective = teams[perspective_roster_id]
    for player in perspective.get("players") or []:
        if player.get("lineup_role") != "taxi":
            continue
        raw_xvar = float(player.get("raw_xvar") or 0.0)
        if raw_xvar <= 0:
            continue
        market_row = player_index.get(str(player.get("sleeper_player_id"))) or {}
        divergence = market_row.get("divergence") or {}
        cards.append(
            _base_card(
                card_id=f"opp-{card_no:04d}",
                card_type="TAXI_LONG_TERM_VALUE_PRESENT",
                perspective_roster_id=perspective_roster_id,
                counterparty_team=None,
                asset={
                    "sleeper_player_id": player.get("sleeper_player_id"),
                    "dg_player_id": market_row.get("dg_player_id"),
                    "full_name": player.get("full_name"),
                    "position": player.get("position"),
                },
                primary="TAXI_LONG_TERM_VALUE_PRESENT",
                secondary=["ACTIVATION_COST_REPRESENTED"],
                evidence={
                    "raw_xvar": raw_xvar,
                    "lineup_role": player.get("lineup_role"),
                    "signal": divergence.get("signal"),
                    "model_minus_market_delta": divergence.get("model_minus_market_delta"),
                },
                score_components={
                    "fit_score": _safe_score(raw_xvar / 25.0),
                    "divergence_score": _safe_score(abs(float(divergence.get("model_minus_market_delta") or 0.0))),
                    "feasibility_score": 0.4,
                },
                signal_status=str(divergence.get("signal_status") or "gates_blocked"),
                sort_key="taxi_long_term_value_desc",
                sort_value=raw_xvar,
                caveats=["taxi_activation_cost_requires_manual_review"],
            )
        )
        card_no += 1
    return cards


def _coverage(cards: list[dict[str, Any]], partner_rankings: list[dict[str, Any]]) -> dict[str, Any]:
    language_surface = [
        {
            "card_type": card.get("card_type"),
            "primary": (card.get("rationale") or {}).get("primary"),
            "secondary": (card.get("rationale") or {}).get("secondary"),
            "caveats": card.get("caveats"),
            "evidence_status": card.get("evidence_status"),
        }
        for card in cards
    ]
    serialized = json.dumps(language_surface, sort_keys=True).lower()
    banned_terms_present = sorted(term for term in BANNED_LANGUAGE if term in serialized)
    type_counts = Counter(card.get("card_type") for card in cards)
    evidence_count = sum(1 for card in cards if ((card.get("rationale") or {}).get("evidence")))
    def _count_ds_true(obj: object) -> int:
        if isinstance(obj, dict):
            here = 1 if obj.get("decision_supported") is True else 0
            return here + sum(_count_ds_true(v) for v in obj.values())
        if isinstance(obj, list):
            return sum(_count_ds_true(item) for item in obj)
        return 0

    decision_supported_true_count = sum(_count_ds_true(card) for card in cards)
    return {
        "card_count": len(cards),
        "partner_count": len(partner_rankings),
        "cards_by_type": dict(sorted(type_counts.items())),
        "cards_with_evidence_count": evidence_count,
        "decision_supported_true_count": decision_supported_true_count,
        "banned_language_present": banned_terms_present,
        "phase17_5_exit_criteria": {
            "opportunity_cards_evidence_backed": evidence_count == len(cards),
            "decision_supported_false": decision_supported_true_count == 0,
            "no_automated_trade_execution": True,
            "output_json_and_markdown": True,
            "no_imperative_language": not banned_terms_present,
        },
    }


def build_league_opportunity_map(
    team_matrix: dict[str, Any],
    market_divergence: dict[str, Any],
    *,
    team_posture: dict[str, Any] | None = None,
    perspective_roster_id: int = 1,
    max_cards: int = DEFAULT_MAX_CARDS,
    captured_at: str | None = None,
    roster_cut_result: RosterCutResult | None = None,
) -> dict[str, Any]:
    team_source = apply_team_postures(team_matrix, team_posture)
    divergence_source = copy.deepcopy(market_divergence)
    captured = captured_at or datetime.now(timezone.utc).isoformat()
    teams = _team_by_roster(team_source)
    if perspective_roster_id not in teams:
        raise ValueError(f"perspective_roster_id {perspective_roster_id} not found in team matrix")

    partner_rankings = build_partner_rankings(
        team_source,
        divergence_source,
        perspective_roster_id=perspective_roster_id,
    )
    player_index = _player_by_sleeper(divergence_source)
    cards: list[dict[str, Any]] = []
    cards.extend(_fit_cards(teams, perspective_roster_id, len(cards) + 1))
    cards.extend(_divergence_cards(divergence_source, teams, perspective_roster_id, len(cards) + 1))
    cards.extend(_waiver_cards(divergence_source, perspective_roster_id, len(cards) + 1, roster_cut_result))
    cards.extend(_taxi_cards(teams, player_index, perspective_roster_id, len(cards) + 1))
    # Transparent grouped sort (No-Verdict T3): group by the per-category
    # sort_key, then descending sort_value WITHIN each group (card_id as a stable
    # tie-break). No hidden cross-type composite ranking; categories are not
    # blended onto one scale.
    cards = sorted(
        cards,
        key=lambda card: (card["sort_key"], -card["sort_value"], card["card_id"]),
    )[:max_cards]

    result = {
        "schema_version": SCHEMA_VERSION,
        "league_id": team_source.get("league_id") or divergence_source.get("league_id"),
        "captured_at": captured,
        "source_artifacts": {
            "team_matrix_schema_version": team_source.get("schema_version"),
            "market_divergence_schema_version": divergence_source.get("schema_version"),
            "team_posture_schema_version": (team_posture or {}).get("schema_version"),
            "team_matrix_captured_at": team_source.get("captured_at"),
            "market_divergence_captured_at": divergence_source.get("captured_at"),
            "team_posture_captured_at": (team_posture or {}).get("captured_at"),
        },
        "perspective_roster_id": perspective_roster_id,
        "partner_rankings": partner_rankings,
        "cards": cards,
        "decision_supported": False,
        "automated_trade_execution": False,
        "caveats": [
            "phase17_non_decision_grade",
            "future_pick_values_deferred",
            *([] if team_posture else ["posture_unclassified"]),
        ],
    }
    result["coverage"] = _coverage(cards, partner_rankings)
    return result


def _markdown(opportunity_map: dict[str, Any]) -> str:
    lines = [
        "# League Opportunity Map",
        "",
        f"captured_at: {opportunity_map.get('captured_at')}",
        "decision_supported: false",
        f"card_count: {len(opportunity_map.get('cards') or [])}",
        "",
        "## Partner Rankings",
    ]
    for ranking in (opportunity_map.get("partner_rankings") or [])[:10]:
        positions = ", ".join(ranking.get("matched_positions") or []) or "none"
        lines.append(
            f"- roster {ranking.get('counterparty_roster_id')}: "
            f"score {ranking.get('partner_score')} | matched_positions: {positions}"
        )
    lines.extend(["", "## Cards"])
    for card in opportunity_map.get("cards") or []:
        asset = card.get("asset") or {}
        asset_name = asset.get("full_name") or asset.get("sleeper_player_id") or "asset unavailable"
        lines.append(
            f"- {card.get('card_id')} | {card.get('card_type')} | {asset_name} | "
            f"sorted by {card.get('sort_key')}={card.get('sort_value')} | decision_supported: false"
        )
    lines.append("")
    return "\n".join(lines)


def write_league_opportunity_artifacts(
    opportunity_map: dict[str, Any],
    *,
    output_dir: Path,
    run_id: str | None = None,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_run_id = run_id or str(opportunity_map["captured_at"]).replace(":", "").replace("-", "")
    batch_path = output_dir / f"league_opportunity_{safe_run_id}.json"
    latest_path = output_dir / "league_opportunity_latest.json"
    markdown_path = output_dir / f"league_opportunity_{safe_run_id}.md"
    markdown_latest_path = output_dir / "league_opportunity_latest.md"

    payload = json.dumps(opportunity_map, indent=2, sort_keys=True) + "\n"
    markdown_payload = _markdown(opportunity_map)
    batch_path.write_text(payload)
    latest_path.write_text(payload)
    markdown_path.write_text(markdown_payload)
    markdown_latest_path.write_text(markdown_payload)
    return {
        "batch": batch_path,
        "batch_latest": latest_path,
        "markdown": markdown_path,
        "markdown_latest": markdown_latest_path,
    }
