"""PVO Assembler — merges identity + feature signals into a Decision Card JSON.

Runs entirely in local Python. No Spark or Databricks compute required.
Scores and projections are left None until the relevant engine is validated.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from src.dynasty_genius.models.player_identity import PlayerIdentity
from src.dynasty_genius.models.player_value_object import PlayerValueObject


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


def assemble_pvo(
    identity: PlayerIdentity,
    features: Optional[dict[str, Any]] = None,
    is_prospect: bool = False,
    source_versions: Optional[dict[str, str]] = None,
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

    return PlayerValueObject(
        player_id=identity.dg_id,
        full_name=identity.full_name,
        position=identity.position,
        nfl_team=identity.nfl_team,
        age=features.get("age"),
        engine_used=None,
        model_version=None,
        model_grade="PRE_MODEL",
        dynasty_value_score=None,
        projection_1y=None,
        projection_2y=None,
        projection_3y=None,
        signal_completeness=completeness,
        inputs_present=present,
        inputs_missing=missing,
        top_drivers=[],
        risk_flags=risk_flags,
        counter_argument=None,
        caveats=caveats,
        market_overlay=None,
        assembled_at=datetime.now(timezone.utc).isoformat(),
        source_versions=source_versions or {},
    )


def assemble_roster_audit(
    mock_identity_path: Path,
    features_by_dg_id: Optional[dict[str, dict[str, Any]]] = None,
) -> list[dict[str, Any]]:
    """Build a Decision Card JSON list for all players in the mock identity fixture.

    Returns a list of PVO dicts suitable for the Roster Audit dashboard.
    No Databricks compute required — runs entirely from local mock files.
    """
    raw = json.loads(mock_identity_path.read_text())
    features_by_dg_id = features_by_dg_id or {}

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
        features = features_by_dg_id.get(identity.dg_id, {})
        pvo = assemble_pvo(identity, features, is_prospect=is_prospect)
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
