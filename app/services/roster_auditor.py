import json
import os
from pathlib import Path
from typing import Optional, Union

import httpx

from app.data.sleeper import get_user, get_leagues, get_rosters, get_all_players
from app.services.engine_b_service import score_inference_partition
from src.dynasty_genius.adapters.nflreadpy_qb_adapter import fetch_qb_nfl_stats
from src.dynasty_genius.models.engine_a_contract import QB_CONTEXT_COLUMNS
from src.dynasty_genius.models.league_context import LeagueContext

_ROOT = Path(__file__).resolve().parents[2]
_QB_BRIDGE_PATH = _ROOT / "resources" / "nflreadpy_qb_id_map.json"

QB_CONTEXT_SEASONS = [2024, 2023]
QB_LOW_TD_INT_RATIO_THRESHOLD = 0.7
QB_ALL_PURPOSE_YARDS_MOBILITY_THRESHOLD = 3700
QB_CONTEXT_ANNOTATION_FIELDS = {
    "qb_context_annotations",
    "qb_context_caveats",
    "source_qb_context_annotations",
}


def load_qb_identity_bridge() -> dict:
    if not _QB_BRIDGE_PATH.exists():
        return {"players": {}}
    with open(_QB_BRIDGE_PATH) as f:
        return json.load(f)

USERNAME_ENV = "DYNASTY_SLEEPER_USERNAME"
LEAGUE_ID_ENV = "DYNASTY_SLEEPER_LEAGUE_ID"
LEAGUE_NAME_ENV = "DYNASTY_SLEEPER_LEAGUE_NAME"
SEASON_ENV = "DYNASTY_SEASON"

CLIFF_AGES = {"RB": 26, "WR": 28, "TE": 30, "QB": 33}
SKILL_POSITIONS = set(CLIFF_AGES.keys())
ENGINE = "roster_auditor_v2"
ROSTER_CAVEATS = ["no_market_overlay"]
INTERNAL_VALUE_KEYS = ("internal_valuation", "internal_value", "dynasty_value_score")
SIGNAL_DRIVERS = {
    "past_cliff": "age_past_position_cliff",
    "at_cliff": "age_at_position_cliff",
    "approaching_cliff": "age_within_two_years_of_position_cliff",
    "no_age_signal": "age_not_near_position_cliff",
}

# Superflex PPR per-season PPG anchors for display-context classification.
# A player projecting at or above this threshold is "above average" for their position.
# Display-only constants — never model features.
_ABOVE_AVG_PPG_THRESHOLD = {"QB": 18.0, "RB": 12.0, "WR": 12.0, "TE": 8.0}
NOT_DECISION_GRADE_REASON = (
    "Roster audit includes age-curve and active-player forecasting (Engine B), "
    "but market signals are currently excluded."
)


class RosterConfigError(ValueError):
    pass


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def age_cliff_risk(position: str, age: Optional[Union[float, int]]) -> Optional[float]:
    """
    Calculate the roster-audit display risk for proximity to the position cliff.

    This mirrors the Gold SQL formula:
    LEAST(1, GREATEST(0, (age - (cliff_age - 3)) / 3)).
    It is a decision-surface warning, not an Engine B model feature.
    """
    if age is None or position not in CLIFF_AGES:
        return None
    cliff_age = CLIFF_AGES[position]
    return round(_clamp((float(age) - (cliff_age - 3.0)) / 3.0), 4)


def _internal_value(player: dict) -> Optional[float]:
    for key in INTERNAL_VALUE_KEYS:
        value = player.get(key)
        if value is not None:
            return float(value)
    return None


def _age_value_context(signal: str, predicted_ppg: Optional[float], position: str) -> str:
    """Cliff-contextualized display context from age proximity + Engine B projection.

    Display-only annotation. Not a model output. Not market-derived.
    Context guide:
      past_cliff_depreciation_risk      — past cliff regardless of projection
      approaching_cliff_high_projection — above-average projection and near cliff
      approaching_cliff_low_projection  — below-average projection and near cliff
      prime_window_high_projection      — above-average projection and away from cliff
      stable_age_low_projection         — below-average projection and away from cliff
      no_engine_b_projection            — no Engine B score; age-curve signal only
    """
    if signal == "past_cliff":
        return "past_cliff_depreciation_risk"

    if predicted_ppg is None:
        return "no_engine_b_projection"

    above_avg = predicted_ppg >= _ABOVE_AVG_PPG_THRESHOLD.get(position, 12.0)

    if signal in ("at_cliff", "approaching_cliff"):
        return "approaching_cliff_high_projection" if above_avg else "approaching_cliff_low_projection"

    return "prime_window_high_projection" if above_avg else "stable_age_low_projection"


def biological_debt_score(player: dict) -> Optional[float]:
    """
    Value-weighted age-curve risk for a roster asset.

    This intentionally uses internal value only. KTC, ADP, FantasyPros, and
    other market-derived prices are excluded by design.
    """
    risk = age_cliff_risk(player.get("position", ""), player.get("age"))
    internal_value = _internal_value(player)
    if risk is None or internal_value is None:
        return None
    return round(risk * max(internal_value, 0.0), 4)


def liquidity_risk(has_2026_2nd: bool, has_2027_2nd: bool) -> str:
    """
    Classify roster escape-hatch risk from second-round pick inventory.

    Second-round picks are treated as liquidity buffers for patching depth,
    not as market-derived valuation inputs.
    """
    if not has_2026_2nd and not has_2027_2nd:
        return "HIGH_NO_SECOND_ROUND_ESCAPE_HATCH"
    if not has_2026_2nd or not has_2027_2nd:
        return "MEDIUM_LIMITED_ESCAPE_HATCH"
    return "LOW"


def roster_biological_debt(players: list[dict]) -> dict:
    debt_value = 0.0
    total_internal_value = 0.0
    debt_players: list[str] = []
    incomplete_players: list[str] = []

    for player in players:
        if player.get("position") not in SKILL_POSITIONS:
            continue

        internal_value = _internal_value(player)
        debt_score = biological_debt_score(player)
        if internal_value is None or debt_score is None:
            incomplete_players.append(player.get("full_name") or player.get("player_id", "UNKNOWN"))
            continue

        total_internal_value += max(internal_value, 0.0)
        debt_value += debt_score
        if debt_score > 0:
            debt_players.append(player.get("full_name") or player.get("player_id", "UNKNOWN"))

    debt_ratio = None
    if total_internal_value > 0:
        debt_ratio = round(debt_value / total_internal_value, 4)

    return {
        "biological_debt_value": round(debt_value, 4),
        "biological_debt_ratio": debt_ratio,
        "biological_debt_players": debt_players,
        "incomplete_biological_debt_players": incomplete_players,
        "total_internal_roster_value": round(total_internal_value, 4),
    }


def roster_risk_summary(
    players: list[dict],
    has_2026_2nd: bool,
    has_2027_2nd: bool,
) -> dict:
    debt = roster_biological_debt(players)
    return {
        **debt,
        "liquidity_risk": liquidity_risk(has_2026_2nd, has_2027_2nd),
        "decision_supported": False,
        "caveats": [
            "internal_value_only",
            "age_curve_only",
            "no_market_derived_inputs",
        ],
    }


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RosterConfigError(f"Missing required environment variable: {name}")
    return value


def _roster_config(league_context: Optional[LeagueContext] = None) -> dict:
    if league_context is not None:
        return {
            "username": None,
            "user_id": league_context.david_user_id,
            "season": league_context.season,
            "league_id": league_context.league_id,
            "league_name": league_context.league_name,
        }

    username = _required_env(USERNAME_ENV)
    season = _required_env(SEASON_ENV)
    league_id = os.getenv(LEAGUE_ID_ENV)
    league_name = os.getenv(LEAGUE_NAME_ENV)

    if not league_id and not league_name:
        raise RosterConfigError(
            f"Set either {LEAGUE_ID_ENV} or {LEAGUE_NAME_ENV}; refusing to guess a league."
        )

    return {
        "username": username,
        "user_id": None,
        "season": season,
        "league_id": league_id,
        "league_name": league_name,
    }


async def _sleeper_config_lookup(description: str, lookup) -> object:
    try:
        return await lookup
    except ValueError as e:
        raise RosterConfigError(f"{description}: {e}") from e
    except httpx.HTTPStatusError as e:
        raise RosterConfigError(
            f"{description} failed with Sleeper status {e.response.status_code}; check roster config."
        ) from e


async def get_my_roster(league_context: Optional[LeagueContext] = None) -> list[dict]:
    config = _roster_config(league_context)
    if config["user_id"]:
        user_id = config["user_id"]
    else:
        user = await _sleeper_config_lookup(
            "Sleeper username lookup",
            get_user(config["username"]),
        )
        user_id = user["user_id"]

    if config["league_id"]:
        league_id = config["league_id"]
    else:
        leagues = await _sleeper_config_lookup(
            "Sleeper league lookup",
            get_leagues(user_id, config["season"]),
        )
        league = next(
            (lg for lg in leagues if lg.get("name") == config["league_name"]),
            None,
        )
        if league is None:
            raise RosterConfigError(
                f"League named {config['league_name']!r} was not found for season {config['season']}."
            )
        league_id = league["league_id"]

    rosters = await _sleeper_config_lookup(
        "Sleeper roster lookup",
        get_rosters(league_id),
    )
    my_roster = next((r for r in rosters if r["owner_id"] == user_id), None)
    if my_roster is None:
        raise RosterConfigError(
            f"No roster found for configured user in league {league_id}."
        )

    all_players = await get_all_players()

    players = []
    for pid in my_roster["players"]:
        p = all_players.get(pid)
        if not p:
            continue
        players.append({
            "player_id": pid,
            "full_name": f"{p.get('first_name', '')} {p.get('last_name', '')}".strip(),
            "position":  p.get("position", ""),
            "team":      p.get("team") or "FA",
            "age":       p.get("age"),
            "gsis_id":   p.get("gsis_id"),
        })

    return players


def audit_player(player: dict, engine_b_score: Optional[dict] = None) -> Optional[dict]:
    position = player.get("position", "")
    if position not in SKILL_POSITIONS:
        return None

    age = player.get("age")
    if age is None:
        return None

    cliff_age = CLIFF_AGES[position]
    years_to_cliff = cliff_age - int(age)
    cliff_risk = age_cliff_risk(position, age)
    biological_debt = biological_debt_score(player)

    if years_to_cliff < 0:
        cliff_status = "Past cliff"
        signal = "past_cliff"
    elif years_to_cliff == 0:
        cliff_status = "At cliff"
        signal = "at_cliff"
    elif years_to_cliff <= 2:
        cliff_status = "Approaching"
        signal = "approaching_cliff"
    else:
        cliff_status = "No age signal"
        signal = "no_age_signal"

    caveats = list(ROSTER_CAVEATS)
    if biological_debt is None:
        caveats.append("no_internal_value_signal")

    if engine_b_score is None:
        caveats.append("no_usage_signal")
        caveats.append("age_curve_only")
    elif engine_b_score.get("experimental"):
        caveats.append("engine_b_experimental_v1_fallback")

    predicted_ppg: Optional[float] = (
        engine_b_score.get("predicted_avg_ppg_t1_t2") if engine_b_score else None
    )
    age_value_context = _age_value_context(signal, predicted_ppg, position)

    audited = {
        **player,
        "cliff_age":          cliff_age,
        "years_to_cliff":     years_to_cliff,
        "age_cliff_risk":     cliff_risk,
        "biological_debt_score": biological_debt,
        "cliff_status":       cliff_status,
        "signal":             signal,
        "signal_drivers":     [SIGNAL_DRIVERS[signal]],
        "age_value_context": age_value_context,
        "caveats":            caveats,
        "engine_b_prediction": engine_b_score,
        "decision_supported": False,
    }
    return audited


def _optional_float(player: dict, field: str) -> Optional[float]:
    value = player.get(field)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _qb_context_annotations(player: dict) -> dict:
    annotations = []
    caveats = []

    td_int_ratio = _optional_float(player, "td_int_ratio")
    all_purpose_yards = _optional_float(player, "all_purpose_yards")

    if td_int_ratio is not None and td_int_ratio < QB_LOW_TD_INT_RATIO_THRESHOLD:
        annotations.append("low_td_int_ratio_bust_context")
    if (
        all_purpose_yards is not None
        and all_purpose_yards > QB_ALL_PURPOSE_YARDS_MOBILITY_THRESHOLD
    ):
        annotations.append("all_purpose_yards_mobility_context")

    if td_int_ratio is None and all_purpose_yards is None:
        caveats.append("missing_qb_college_context")

    # Pressure-to-sack is not currently present in the roster context lane.
    caveats.append("p2s_context_unavailable")

    return {
        "qb_context_annotations": annotations,
        "qb_context_caveats": caveats,
        "source_qb_context_annotations": "cfbd_qb_context_annotations",
    }


def _build_qb_context_card(player: dict, bridge_entry: dict, telemetry: dict | None) -> dict:
    pid = player.get("player_id", "")
    full_name = player.get("full_name", "")
    coverage = bridge_entry.get("coverage", "NONE")

    if telemetry is not None:
        fields = {field: telemetry.get(field) for field in QB_CONTEXT_COLUMNS}
        provenance = {f"source_{field}": "nflreadpy_qb_context" for field in QB_CONTEXT_COLUMNS}
    else:
        fields = {field: None for field in QB_CONTEXT_COLUMNS}
        provenance = {
            f"source_{field}": "nflreadpy_qb_context:unresolved_identity"
            for field in QB_CONTEXT_COLUMNS
        }

    return {
        "player_id": pid,
        "full_name": full_name,
        "identity_coverage": coverage,
        "context_role": "context_signal",
        "decision_supported": False,
        **fields,
        **provenance,
        **_qb_context_annotations(player),
    }


async def run_audit() -> dict:
    players = await get_my_roster()

    # ── Engine B scoring ─────────────────────────────────────────────────────
    # Engine B scores are generated BEFORE any market data is fetched.
    # Market values (KTC, ADP, FantasyCalc) must only be appended AFTER this
    # block and must never be passed into score_inference_partition() or
    # predict_player_season(). Architecture gate enforced by test_market_overlay.py.
    engine_b_scores = {s["player_id"]: s for s in score_inference_partition()}

    audited = []
    for p in players:
        gsis_id = p.get("gsis_id")
        score = engine_b_scores.get(gsis_id) if gsis_id else None
        res = audit_player(p, engine_b_score=score)
        if res:
            audited.append(res)

    audited.sort(key=lambda p: p["years_to_cliff"])

    # ── Market overlay attachment point (Phase 7+) ───────────────────────────
    # KTC/FantasyCalc values are fetched here and appended side-by-side with
    # Engine B predictions in the final payload. Market data does not re-enter
    # the Engine B service layer. Source registry enforces market_overlay role.

    bridge = load_qb_identity_bridge()
    bridge_players = bridge.get("players", {})
    qb_context_cards = []
    for player in players:
        if player.get("position") != "QB":
            continue
        pid = player.get("player_id", "")
        entry = bridge_players.get(pid, {})
        coverage = entry.get("coverage", "NONE")
        if coverage in ("FULL", "PARTIAL"):
            gsis_id = entry.get("gsis_id")
            telemetry = fetch_qb_nfl_stats(gsis_id, QB_CONTEXT_SEASONS)
        else:
            telemetry = None
        qb_context_cards.append(_build_qb_context_card(player, entry, telemetry))

    return {
        "status": "experimental",
        "engine": ENGINE,
        "decision_supported": False,
        "reason": NOT_DECISION_GRADE_REASON,
        "caveats": ROSTER_CAVEATS,
        "players": audited,
        "qb_context_cards": qb_context_cards,
    }
