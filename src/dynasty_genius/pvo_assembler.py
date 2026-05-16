"""PVO Assembler — merges identity + feature signals into a Decision Card JSON.

Runs entirely in local Python. No Spark or Databricks compute required.
Scores and projections are left None until the relevant engine is validated.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.services.engine_b_service import predict_player_season as predict_player_season_b
from app.services.roster_auditor import audit_player, roster_risk_summary
from src.dynasty_genius.decision_logic.counter_arguments import generate_counter_argument
from src.dynasty_genius.models.league_context import LeagueContext
from src.dynasty_genius.models.player_identity import PlayerIdentity
from src.dynasty_genius.models.player_value_object import PlayerValueObject, RosterAuditSignals
from src.dynasty_genius.models.engine_b_contract import (
    ENGINE_B_FEATURES_BY_POSITION,
    ENGINE_B_P90_PPG,
    ENGINE_B_MIN_GAMES_T,
)
from src.dynasty_genius.scoring.engine_a import score_prospect, _P90_PPG


# ── Position-specific required signal sets ────────────────────────────────────
# These match the feature contracts defined in the North Star Architecture.

def _engine_b_required(position: str) -> list[str]:
    pos = position.upper()
    contract = ENGINE_B_FEATURES_BY_POSITION.get(pos, frozenset())
    return sorted(contract)

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
    if is_prospect:
        return _IDENTITY_SIGNALS + _ENGINE_A_REQUIRED.get(pos, [])
    return _IDENTITY_SIGNALS + _engine_b_required(pos)


def _compute_completeness(
    required: list[str],
    features: dict[str, Any],
    identity: PlayerIdentity,
) -> tuple[float, list[str], list[str]]:
    """Return (completeness_ratio, present_list, missing_list)."""
    feature_aliases = {
        "draft_capital": ("draft_capital", "pick"),
        "age_at_nfl_entry": ("age_at_nfl_entry", "age"),
    }
    identity_vals = {
        "player_id": identity.dg_id,
        "full_name": identity.full_name,
        "position": identity.position,
        "nfl_team": identity.nfl_team,
        "sleeper_id": identity.sleeper_id,
        "pff_id": identity.pff_id,
    }
    all_vals = {**identity_vals, **features}

    def has_signal(signal: str) -> bool:
        aliases = feature_aliases.get(signal, (signal,))
        return any(all_vals.get(alias) is not None for alias in aliases)

    present = [s for s in required if has_signal(s)]
    missing = [s for s in required if not has_signal(s)]
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
    league_context: Optional[LeagueContext] = None,
    position: str = "",
    verification_status: str = "PENDING",
    age_verified: bool = False,
    identity_verified: bool = False,
) -> list[str]:
    caveats: list[str] = []

    engine = "Engine A (prospect)" if is_prospect else "Engine B (active player)"

    if verification_status == "VERIFIED_NFL_DRAFT":
        caveats.append("NFL draft capital verified")
        if not age_verified:
            caveats.append("Birth date missing: Engine A signal inhibited")
        if not identity_verified:
            caveats.append("Sleeper identity unverified: local matching only")
    else:
        caveats.append(
            f"dynasty_value_score unavailable: {engine} not yet validated; "
            "model_grade is PRE_MODEL"
        )
    if league_context:
        if league_context.is_superflex:
            if position.upper() == "QB":
                caveats.append("Superflex scoring active: QB value is elevated")
            else:
                caveats.append("Superflex scoring active")
        if league_context.te_premium > 0 and position.upper() == "TE":
            caveats.append(f"TE Premium ({league_context.te_premium}) active: TE scarcity is elevated")

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
    league_context: Optional[LeagueContext] = None,
    engine_b_score: Optional[dict] = None,
) -> Optional[RosterAuditSignals]:
    player = {
        "player_id": identity.dg_id,
        "full_name": identity.full_name,
        "position": identity.position,
        "team": identity.nfl_team,
        **features,
    }
    audited = audit_player(player, engine_b_score=engine_b_score)
    if audited is None:
        return None

    liquidity = None
    if league_context:
        picks = league_context.my_future_picks
        has_2026_2nd = any(p.year == 2026 and p.round == 2 for p in picks)
        has_2027_2nd = any(p.year == 2027 and p.round == 2 for p in picks)
        liquidity = roster_risk_summary([player], has_2026_2nd, has_2027_2nd)["liquidity_risk"]

    return RosterAuditSignals(
        cliff_age=audited.get("cliff_age"),
        years_to_cliff=audited.get("years_to_cliff"),
        age_cliff_risk=audited.get("age_cliff_risk"),
        biological_debt_score=audited.get("biological_debt_score"),
        liquidity_risk=liquidity,
        signal=audited.get("signal"),
        signal_drivers=audited.get("signal_drivers", []),
        age_value_context=audited.get("age_value_context"),
        caveats=audited.get("caveats", []),
        decision_supported=False,
    )


def assemble_pvo(
    identity: PlayerIdentity,
    features: Optional[dict[str, Any]] = None,
    is_prospect: bool = False,
    source_versions: Optional[dict[str, str]] = None,
    league_context: Optional[LeagueContext] = None,
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
    league_context:
        The "David's Context" model for scoring and roster fit.
    """
    features = features or {}
    required = _required_signals(identity.position, is_prospect)
    completeness, present, missing = _compute_completeness(required, features, identity)
    risk_flags = _build_risk_flags(identity, features, is_prospect)
    caveats = _build_caveats(
        completeness,
        is_prospect,
        missing,
        league_context,
        identity.position,
        identity.verification_status,
        identity.age_verified,
        identity.identity_verified
    )

    # Resolve Engine B score for active players before building roster audit so the
    # audit context (age_value_context, experimental caveats) reflects the projection.
    engine_b_resolved: Optional[dict] = None
    if not is_prospect:
        engine_b_resolved = features.get("engine_b_score")
        if engine_b_resolved is None:
            # Single-player scoring path: only trigger when feature_season is present,
            # indicating a real NFL season row (not a partial test fixture).
            pos_contract = ENGINE_B_FEATURES_BY_POSITION.get(identity.position.upper(), frozenset())
            if (pos_contract
                    and pos_contract.issubset(set(features.keys()))
                    and "feature_season" in features):
                try:
                    engine_b_resolved = predict_player_season_b(
                        {**features, "position": identity.position}
                    )
                except Exception:
                    engine_b_resolved = None
        if engine_b_resolved and "error" in engine_b_resolved:
            engine_b_resolved = None

    roster_audit = _build_roster_audit_signals(identity, features, league_context, engine_b_score=engine_b_resolved)
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

    # Engine A: score prospect if pick + round + age are all supplied.
    # Veterans stay PRE_MODEL until Engine B is trained or are scored via Dead Window bridge.
    engine_a_result = None
    pick = features.get("pick")
    round_ = features.get("round")
    age = features.get("age")
    if pick is not None and round_ is not None and age is not None:
        engine_a_result = score_prospect(identity.position, float(pick), float(round_), float(age))

    engine_used = None
    model_version = None
    model_grade = "PRE_MODEL"
    dynasty_value_score = features.get("dynasty_value_score")
    dvs_engine: Optional[str] = None
    dvs_p90_ref_val: Optional[float] = None
    dvs_clamped_val: Optional[bool] = None
    source_season: Optional[int] = None
    projection_2y: Optional[float] = None

    if engine_a_result:
        # DVS engine A always populates provenance if score is present
        dynasty_value_score = engine_a_result["dynasty_value_score"]
        dvs_engine = "A"
        dvs_p90_ref_val = _P90_PPG.get(identity.position.upper())
        dvs_clamped_val = engine_a_result["dynasty_value_score"] >= 100.0
        
        # BUT: Engine A model metadata only overrides PRE_MODEL if is_prospect is True.
        # This prevents veterans with draft capital from appearing as PROSPECT_C.
        if is_prospect:
            engine_used = engine_a_result["engine_used"]
            model_version = engine_a_result["model_version"]
            model_grade = engine_a_result["model_grade"]
            caveats = [
                c for c in caveats
                if not c.startswith("dynasty_value_score unavailable:")
            ]
            for caveat in engine_a_result["caveats"]:
                if caveat not in caveats:
                    caveats.append(caveat)

    # Engine B: populate active-player metadata from resolved score.
    if engine_b_resolved:
        engine_used = "engine_b"
        model_version = engine_b_resolved["engine"]
        source_season = engine_b_resolved.get("feature_season")
        projection_2y = engine_b_resolved.get("predicted_avg_ppg_t1_t2")
        model_grade = "EXPERIMENTAL" if engine_b_resolved.get("experimental") else "ACTIVE_B"
        caveats = [c for c in caveats if not c.startswith("dynasty_value_score unavailable:")]
        for caveat in engine_b_resolved.get("caveats", []):
            if caveat not in caveats:
                caveats.append(caveat)

        # DVS normalization — Engine B path.
        # Formula: clamp(predicted_avg_ppg_t1_t2 / POSITION_P90_PPG_B * 100, 0, 100)
        # P90 constants are Engine B-native (May 2026 diagnostic from engine_b_features_v2.csv).
        # Veterans with games_t below ENGINE_B_MIN_GAMES_T are routed to the Dead Window
        # fallback below; this block runs only for Engine B-eligible players.
        games_t = features.get("games_t")
        pos_upper = identity.position.upper()
        _b_p90 = ENGINE_B_P90_PPG.get(pos_upper)
        _below_games_gate = (
            games_t is not None
            and float(games_t) < ENGINE_B_MIN_GAMES_T
        )

        if (projection_2y is not None
                and _b_p90 is not None
                and not _below_games_gate):
            dvs_raw = projection_2y / _b_p90 * 100.0
            dvs_clamped_flag = dvs_raw > 100.0
            dynasty_value_score = round(min(100.0, max(0.0, dvs_raw)), 1)
            dvs_engine = "B"
            dvs_p90_ref_val = _b_p90
            dvs_clamped_val = dvs_clamped_flag

        # Dead Window bridge: player has exited prospect status and Engine B feature data
        # exists, but games_t is below the reliability threshold. Retain Engine A DVS as
        # a prior if draft capital is present; otherwise stay PRE_MODEL.
        # The caveat is mandatory — the user must know the score rests on draft capital,
        # not verified professional efficiency.
        if engine_b_resolved and _below_games_gate:
            _dw_caveat = (
                "Insufficient professional season data — Engine A prospect score used as prior"
            )
            # Try Engine A fallback (reuse engine_a_result computed above)
            if engine_a_result:
                dynasty_value_score = engine_a_result["dynasty_value_score"]
                dvs_engine = "A"
                dvs_p90_ref_val = _P90_PPG.get(pos_upper)
                dvs_clamped_val = engine_a_result["dynasty_value_score"] >= 100.0
            # Caveat is appended regardless of whether Engine A data was available.
            if _dw_caveat not in caveats:
                caveats.append(_dw_caveat)

        # TE-specific caveat: G3 (market superiority) deferred; decision_supported = False.
        if pos_upper == "TE" and model_grade == "ACTIVE_B":
            _te_caveat = "TE market superiority gate deferred — projection-quality score only"
            if _te_caveat not in caveats:
                caveats.append(_te_caveat)

        # QB low-volume flag (unchanged from Phase 12.5).
        if pos_upper == "QB":
            if games_t is not None and float(games_t) < 3:
                backup_caveat = "High-Efficiency / Low-Volume Anomaly (Backup Profile)"
                if backup_caveat not in caveats:
                    caveats.append(backup_caveat)

    pvo = PlayerValueObject(
        player_id=identity.dg_id,
        full_name=identity.full_name,
        position=identity.position,
        nfl_team=identity.nfl_team,
        age=features.get("age"),
        is_prospect=is_prospect,
        sleeper_id=identity.sleeper_id,
        draft_class=int(features["draft_class"]) if features.get("draft_class") is not None else None,
        nfl_draft_pick=int(features["pick"]) if features.get("pick") is not None else None,
        nfl_draft_round=int(features["round"]) if features.get("round") is not None else None,
        decision_supported=False,
        engine_used=engine_used,
        model_version=model_version,
        model_grade=model_grade,
        dynasty_value_score=dynasty_value_score,
        dvs_engine=dvs_engine,
        dvs_p90_ref=dvs_p90_ref_val,
        dvs_clamped=dvs_clamped_val,
        projection_1y=None,
        projection_2y=projection_2y,
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
        value_above_replacement=features.get("value_above_replacement"),
        assembled_at=datetime.now(timezone.utc).isoformat(),
        source_season=source_season,
        source_versions=source_versions or {},
    )

    # Apply mandatory steel-manned counter-argument
    pvo.counter_argument = generate_counter_argument(pvo)

    return pvo


def assemble_roster_audit(
    mock_identity_path: Path,
    features_by_dg_id: Optional[dict[str, dict[str, Any]]] = None,
    league_context: Optional[LeagueContext] = None,
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
            verification_status=p.get("verification_status", "PENDING"),
            age_verified=p.get("age_verified", False),
            identity_verified=p.get("identity_verified", False),
        )
        is_prospect = bool(p.get("is_prospect", False))
        fixture_features: dict[str, Any] = {
            "age": _age_at_snapshot(p.get("birth_date"), snapshot_date),
            "draft_class": p.get("draft_class"),
        }
        if p.get("pick") is not None:
            fixture_features["pick"] = float(p["pick"])
        if p.get("round") is not None:
            fixture_features["round"] = float(p["round"])
            
        is_verified_draft = identity.verification_status == "VERIFIED_NFL_DRAFT"
        if is_prospect and not is_verified_draft and (p.get("pick") is not None or p.get("round") is not None):
            fixture_features["feature_warnings"] = ["mock_draft_capital_unverified"]
        features = {**fixture_features, **features_by_dg_id.get(identity.dg_id, {})}
        pvo = assemble_pvo(
            identity,
            features,
            is_prospect=is_prospect,
            league_context=league_context,
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
