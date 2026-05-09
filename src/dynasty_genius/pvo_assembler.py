"""PVO Assembler — merges identity + feature signals into a Decision Card JSON.

Runs entirely in local Python. No Spark or Databricks compute required.
Scores and projections are left None until the relevant engine is validated.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.services.roster_auditor import audit_player, roster_risk_summary
from src.dynasty_genius.decision_logic.counter_arguments import generate_counter_argument
from src.dynasty_genius.models.player_identity import PlayerIdentity
from src.dynasty_genius.models.player_value_object import PlayerValueObject, RosterAuditSignals


# ── Position-specific required signal sets ────────────────────────────────────
# These match the feature contracts defined in the North Star Architecture.

_ENGINE_B_REQUIRED: dict[str, list[str]] = {
    "RB": ["snap_share", "target_share", "breakaway_run_pct", "run_blocking_grade"],
    "WR": ["snap_share", "target_share", "yards_per_route_run"],
    "TE": ["snap_share", "target_share", "yards_per_route_run"],
    "QB": ["snap_share"],
}

_ENGINE_A_REQUIRED: dict[str, list[str]] = {
    "RB": ["draft_capital", "age_at_nfl_entry", "college_dominator_rating"],
    "WR": ["draft_capital", "age_at_nfl_entry", "college_dominator_rating"],
    "TE": ["draft_capital", "age_at_nfl_entry", "college_dominator_rating"],
    "QB": ["draft_capital", "age_at_nfl_entry"],
}

# Identity signals always required regardless of engine
_IDENTITY_SIGNALS = ["player_id", "full_name", "position"]


def _required_signals(position: str, is_prospect: bool) -> list[str]:
    pos = position.upper()
    source = _ENGINE_A_REQUIRED if is_prospect else _ENGINE_B_REQUIRED
    return _IDENTITY_SIGNALS + source.get(pos, [])


def _compute_completeness(
    required: list[str],
    features: dict[str, Any],
    identity: PlayerIdentity,
) -> tuple[float, list[str], list[str]]:
    """Return (completeness_ratio, present_list, missing_list)."""
    identity_vals = {
        "player_id": identity.dg_id,
        "full_name": identity.full_name,
        "position": identity.position,
        "nfl_team": identity.nfl_team,
        "sleeper_id": identity.sleeper_id,
        "pff_id": identity.pff_id,
    }
    all_vals = {**identity_vals, **features}

    present = [s for s in required if all_vals.get(s) is not None]
    missing = [s for s in required if all_vals.get(s) is None]
    ratio = len(present) / len(required) if required else 1.0
    return round(ratio, 4), present, missing


def _build_risk_flags(
    identity: PlayerIdentity,
    features: dict[str, Any],
    is_prospect: bool,
) -> list[str]:
    flags: list[str] = []

    if identity.verification_status == "CONFLICT":
        flags.append("identity_conflict_requires_manual_review")
    if identity.verification_status == "PENDING":
        flags.append("identity_unverified")

    if not is_prospect:
        snap = features.get("snap_share")
        if snap is not None and snap < 0.40:
            flags.append("snap_share_below_40pct")

    feature_warnings = features.get("feature_warnings") or []
    for w in feature_warnings:
        if w not in flags:
            flags.append(w)

    return flags


def _build_caveats(
    signal_completeness: float,
    is_prospect: bool,
    inputs_missing: list[str],
) -> list[str]:
    caveats: list[str] = []

    engine = "Engine A (prospect)" if is_prospect else "Engine B (active player)"
    caveats.append(
        f"dynasty_value_score unavailable: {engine} not yet validated; "
        "model_grade is PRE_MODEL"
    )

    if signal_completeness < 1.0:
        caveats.append(
            f"Signal completeness {signal_completeness:.0%} — "
            f"missing: {', '.join(inputs_missing)}"
        )

    if signal_completeness < 0.5:
        caveats.append(
            "Fewer than 50% of required signals present — "
            "do not use for dynasty decisions until data is refreshed"
        )

    return caveats


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _age_at_snapshot(birth_date: Optional[str], snapshot_date: Optional[str]) -> Optional[float]:
    born = _parse_date(birth_date)
    snapshot = _parse_date(snapshot_date)
    if not born or not snapshot:
        return None
    years = snapshot.year - born.year
    if (snapshot.month, snapshot.day) < (born.month, born.day):
        years -= 1
    return float(years)


def _build_roster_audit_signals(
    identity: PlayerIdentity,
    features: dict[str, Any],
    roster_context: Optional[dict[str, Any]],
) -> Optional[RosterAuditSignals]:
    player = {
        "player_id": identity.dg_id,
        "full_name": identity.full_name,
        "position": identity.position,
        "team": identity.nfl_team,
        **features,
    }
    audited = audit_player(player)
    if audited is None:
        return None

    liquidity = None
    if roster_context:
        has_2026_2nd = bool(roster_context.get("has_2026_2nd", True))
        has_2027_2nd = bool(roster_context.get("has_2027_2nd", True))
        liquidity = roster_risk_summary([player], has_2026_2nd, has_2027_2nd)["liquidity_risk"]

    return RosterAuditSignals(
        cliff_age=audited.get("cliff_age"),
        years_to_cliff=audited.get("years_to_cliff"),
        age_cliff_risk=audited.get("age_cliff_risk"),
        biological_debt_score=audited.get("biological_debt_score"),
        liquidity_risk=liquidity,
        signal=audited.get("signal"),
        signal_drivers=audited.get("signal_drivers", []),
        caveats=audited.get("caveats", []),
        decision_supported=False,
    )


def assemble_pvo(
    identity: PlayerIdentity,
    features: Optional[dict[str, Any]] = None,
    is_prospect: bool = False,
    source_versions: Optional[dict[str, str]] = None,
    roster_context: Optional[dict[str, Any]] = None,
) -> PlayerValueObject:
    """Assemble a PlayerValueObject from identity + available feature signals.

    Parameters
    ----------
    identity:
        Canonical PlayerIdentity record (from silver.player_identity or mock).
    features:
        Dict of signal name → value for this player. Missing keys treated as
        absent signals and reflected in signal_completeness.
    is_prospect:
        True → use Engine A signal contract. False → use Engine B.
    source_versions:
        Optional provenance metadata (parser version, snapshot date, etc.)
    """
    features = features or {}
    required = _required_signals(identity.position, is_prospect)
    completeness, present, missing = _compute_completeness(required, features, identity)
    risk_flags = _build_risk_flags(identity, features, is_prospect)
    caveats = _build_caveats(completeness, is_prospect, missing)
    roster_audit = _build_roster_audit_signals(identity, features, roster_context)
    top_drivers: list[str] = []

    if roster_audit:
        for driver in roster_audit.signal_drivers:
            if driver not in top_drivers:
                top_drivers.append(driver)
            # Mandatory steel-manned counter-argument logic requires this flag in risk_flags
            if driver == "age_past_position_cliff" and driver not in risk_flags:
                risk_flags.append(driver)
        for caveat in roster_audit.caveats:
            if caveat not in caveats:
                caveats.append(caveat)

    pvo = PlayerValueObject(
        player_id=identity.dg_id,
        full_name=identity.full_name,
        position=identity.position,
        nfl_team=identity.nfl_team,
        age=features.get("age"),
        is_prospect=is_prospect,
        engine_used=None,
        model_version=None,
        model_grade="PRE_MODEL",
        dynasty_value_score=features.get("dynasty_value_score"),
        projection_1y=None,
        projection_2y=None,
        projection_3y=None,
        signal_completeness=completeness,
        inputs_present=present,
        inputs_missing=missing,
        top_drivers=top_drivers,
        risk_flags=risk_flags,
        counter_argument=None,
        caveats=caveats,
        roster_audit=roster_audit,
        market_overlay=None,
        assembled_at=datetime.now(timezone.utc).isoformat(),
        source_versions=source_versions or {},
    )

    # Apply mandatory steel-manned counter-argument
    pvo.counter_argument = generate_counter_argument(pvo)

    return pvo


def assemble_roster_audit(
    mock_identity_path: Path,
    features_by_dg_id: Optional[dict[str, dict[str, Any]]] = None,
    roster_context: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """Build a Decision Card JSON list for all players in the mock identity fixture.

    Returns a list of PVO dicts suitable for the Roster Audit dashboard.
    No Databricks compute required — runs entirely from local mock files.
    """
    raw = json.loads(mock_identity_path.read_text())
    features_by_dg_id = features_by_dg_id or {}
    snapshot_date = raw.get("snapshot_date")

    from src.dynasty_genius.identity import generate_dg_id

    cards: list[dict[str, Any]] = []
    for p in raw["players"]:
        identity = PlayerIdentity(
            dg_id=generate_dg_id(p["full_name"], p["position"], p.get("birth_year")),
            full_name=p["full_name"],
            position=p["position"],
            birth_date=p.get("birth_date"),
            nfl_team=p.get("nfl_team"),
            jersey_number=p.get("jersey_number"),
            sleeper_id=p.get("sleeper_id"),
            pff_id=p.get("pff_id"),
            pfr_id=p.get("pfr_id"),
            playerprofiler_id=p.get("playerprofiler_id"),
        )
        is_prospect = bool(p.get("is_prospect", False))
        fixture_features = {
            "age": _age_at_snapshot(p.get("birth_date"), snapshot_date),
        }
        features = {**fixture_features, **features_by_dg_id.get(identity.dg_id, {})}
        pvo = assemble_pvo(
            identity,
            features,
            is_prospect=is_prospect,
            roster_context=roster_context,
            source_versions={
                "identity_source": raw.get("source", "unknown"),
                "identity_parser_version": raw.get("parser_version", "unknown"),
                "identity_snapshot_date": snapshot_date or "unknown",
            },
        )
        cards.append(pvo.model_dump())

    return cards


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    mock_path = root / "resources" / "mock_playerprofiler_identity.json"
    cards = assemble_roster_audit(mock_path)

    output_path = root / "resources" / "roster_audit_cards.json"
    output_path.write_text(json.dumps(cards, indent=2))
    print(f"Assembled {len(cards)} Decision Cards → {output_path.relative_to(root)}")

    # Print signal completeness summary
    print(f"\n{'Player':<28} {'Pos':<4} {'Completeness':>13}  Model Grade")
    print("-" * 62)
    for card in cards:
        print(
            f"{card['full_name']:<28} {card['position']:<4} "
            f"{card['signal_completeness']:>12.0%}  {card['model_grade']}"
        )
