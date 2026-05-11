"""CFBD QB adapter governance and unit tests.

Governance tests (run immediately — fail until engine_a_contract.py and the
adapter module are implemented):
  - POSITION_FEATURE_MATRIX["QB"] is non-empty
  - QB_CFBD_FEATURES matches the approved feature set exactly
  - Every QB feature is registered in CFBD_MODEL_INPUT_COLUMNS
  - Every QB feature has a source_ provenance sibling registered
  - No QB feature is in PROHIBITED_COLUMNS or matches LEAKAGE_REGEX
  - Source registry "cfbd" remains model_input

Unit tests (fail until adapter module exists — define the fetch interface):
  - Returns exactly the expected keys for any player/year
  - completion_pct is 0.0–1.0 (not raw API percent)
  - all_purpose_yards = passing YDS + rushing YDS
  - td_int_ratio denominator is capped at 1 (no divide-by-zero)
  - Missing PPA returns None, never 0.0
  - Player not found → every value is None
  - Authorization header carries the API key on every request
  - Never raises on partial data

Integration tests: skipped until Phase 2 implementation confirmed with live key.
"""
from __future__ import annotations

import re
from unittest.mock import MagicMock, patch

import pytest

from src.dynasty_genius.models.engine_a_contract import (
    CFBD_MODEL_INPUT_COLUMNS,
    LEAKAGE_REGEX,
    POSITION_FEATURE_MATRIX,
    PROHIBITED_COLUMNS,
)
from src.dynasty_genius.sources.source_registry import SOURCE_REGISTRY
from src.dynasty_genius.adapters.cfbd_qb_adapter import (
    QB_CFBD_FEATURES,
    fetch_qb_college_stats,
)


# ── Approved QB feature set (from QB strategy, 2026-05-11) ───────────────────

APPROVED_QB_FEATURES = {
    "completion_pct",
    "yards_per_attempt",
    "td_int_ratio",
    "sack_rate",
    "all_purpose_yards",
    "passing_yards_share",
    "ppa",
    "wepa",
    "rushing_yards",
    "rushing_tds",
}


# ── Governance: feature matrix ────────────────────────────────────────────────

def test_qb_feature_matrix_is_not_empty():
    """Stage 2 gate: QB matrix must be populated before QB scoring is valid."""
    assert POSITION_FEATURE_MATRIX["QB"], (
        "POSITION_FEATURE_MATRIX['QB'] is still []. "
        "Populate it in engine_a_contract.py and register QB features in "
        "CFBD_MODEL_INPUT_COLUMNS before any QB scoring runs."
    )


def test_qb_feature_matrix_matches_approved_set():
    """Matrix must match the QB strategy approved on 2026-05-11 exactly."""
    matrix = set(POSITION_FEATURE_MATRIX["QB"])
    unexpected = matrix - APPROVED_QB_FEATURES
    missing = APPROVED_QB_FEATURES - matrix
    assert not unexpected and not missing, (
        f"QB feature matrix mismatch. "
        f"Unexpected: {unexpected}. Missing: {missing}."
    )


def test_qb_feature_matrix_matches_adapter_constant():
    """POSITION_FEATURE_MATRIX['QB'] and QB_CFBD_FEATURES must be identical sets."""
    assert set(POSITION_FEATURE_MATRIX["QB"]) == set(QB_CFBD_FEATURES), (
        "engine_a_contract.py and cfbd_qb_adapter.QB_CFBD_FEATURES are out of sync. "
        f"Matrix: {set(POSITION_FEATURE_MATRIX['QB'])}. "
        f"Adapter constant: {set(QB_CFBD_FEATURES)}."
    )


# ── Governance: registration in contract ─────────────────────────────────────

def test_qb_cfbd_features_registered_in_cfbd_model_input_columns():
    """Every QB feature must be in CFBD_MODEL_INPUT_COLUMNS to be pipeline-legal."""
    unregistered = set(QB_CFBD_FEATURES) - CFBD_MODEL_INPUT_COLUMNS
    assert not unregistered, (
        f"QB features not in CFBD_MODEL_INPUT_COLUMNS: {unregistered}. "
        "Add them to engine_a_contract.py."
    )


def test_qb_cfbd_features_have_source_provenance_columns():
    """Every model_input QB feature must have a source_ sibling registered."""
    missing_provenance = [
        f for f in QB_CFBD_FEATURES
        if f"source_{f}" not in CFBD_MODEL_INPUT_COLUMNS
    ]
    assert not missing_provenance, (
        f"Missing source_ provenance columns for: {missing_provenance}. "
        "Add source_<feature> to CFBD_MODEL_INPUT_COLUMNS for each QB feature."
    )


# ── Governance: leakage ───────────────────────────────────────────────────────

def test_qb_cfbd_features_not_in_prohibited_columns():
    leaked = set(QB_CFBD_FEATURES) & PROHIBITED_COLUMNS
    assert not leaked, (
        f"QB features found in PROHIBITED_COLUMNS: {leaked}. "
        "These cannot enter the model pipeline."
    )


def test_qb_cfbd_features_pass_leakage_regex():
    flagged = [f for f in QB_CFBD_FEATURES if re.search(LEAKAGE_REGEX, f)]
    assert not flagged, (
        f"QB features flagged by LEAKAGE_REGEX ('{LEAKAGE_REGEX}'): {flagged}. "
        "Rename to remove market/rank signals from feature names."
    )


# ── Governance: source registry ───────────────────────────────────────────────

def test_cfbd_source_is_model_input():
    assert "model_input" in SOURCE_REGISTRY["cfbd"].roles, (
        "SOURCE_REGISTRY['cfbd'] must remain model_input. Do not demote."
    )


def test_cfbd_source_not_prohibited():
    assert "prohibited" not in SOURCE_REGISTRY["cfbd"].roles
    assert "prohibited_current_phase" not in SOURCE_REGISTRY["cfbd"].roles


# ── Mock helpers ──────────────────────────────────────────────────────────────

def _passing_stats(pct=65.2, ypa=8.1, td=30, int_=8, yds=3000, att=400, team="Clemson"):
    return [
        {"statType": "PCT",  "stat": pct,  "team": team},
        {"statType": "YPA",  "stat": ypa,  "team": team},
        {"statType": "TD",   "stat": td,   "team": team},
        {"statType": "INT",  "stat": int_, "team": team},
        {"statType": "YDS",  "stat": yds,  "team": team},
        {"statType": "ATT",  "stat": att,  "team": team},
    ]


def _rushing_stats(car=80, yds=400, td=5, team="Clemson"):
    return [
        {"statType": "CAR", "stat": car, "team": team},
        {"statType": "YDS", "stat": yds, "team": team},
        {"statType": "TD",  "stat": td,  "team": team},
    ]


def _ppa_stats(value=0.38, team="Clemson"):
    return [{"name": "Trevor Lawrence", "team": team, "averagePPA": {"all": value}}]


def _wepa_stats(value=42.3, team="Clemson"):
    return [{"name": "Trevor Lawrence", "team": team, "season": 2020, "wepa": value}]


def _team_stats(pass_att=430, sacks=18, net_pass_yds=3200, team="Clemson"):
    return [
        {"team": team, "statName": "passAttempts",    "statValue": pass_att},
        {"team": team, "statName": "sacksAllowed",    "statValue": sacks},
        {"team": team, "statName": "netPassingYards", "statValue": net_pass_yds},
    ]


def _full_mock(url, **kwargs):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "category=passing" in url:
        resp.json.return_value = _passing_stats()
    elif "category=rushing" in url:
        resp.json.return_value = _rushing_stats()
    elif "/ppa/players/season" in url:
        resp.json.return_value = _ppa_stats()
    elif "/wepa/players/passing" in url:
        resp.json.return_value = _wepa_stats()
    elif "/stats/team/season" in url:
        resp.json.return_value = _team_stats()
    else:
        resp.json.return_value = []
    return resp


def _no_ppa_mock(url, **kwargs):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "category=passing" in url:
        resp.json.return_value = _passing_stats()
    elif "category=rushing" in url:
        resp.json.return_value = _rushing_stats()
    elif "/ppa/players/season" in url:
        resp.json.return_value = []          # PPA unavailable
    elif "/wepa/players/passing" in url:
        resp.json.return_value = _wepa_stats()
    elif "/stats/team/season" in url:
        resp.json.return_value = _team_stats()
    else:
        resp.json.return_value = []
    return resp


def _empty_mock(url, **kwargs):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = []
    return resp


PATCH = "src.dynasty_genius.adapters.cfbd_qb_adapter.httpx.get"


# ── Unit: return shape ────────────────────────────────────────────────────────

@patch(PATCH, side_effect=_full_mock)
def test_fetch_returns_all_expected_keys(_):
    result = fetch_qb_college_stats("Trevor Lawrence", 2020, api_key="test-key")
    assert set(result.keys()) == APPROVED_QB_FEATURES, (
        f"Unexpected keys: {set(result.keys()) - APPROVED_QB_FEATURES}. "
        f"Missing keys: {APPROVED_QB_FEATURES - set(result.keys())}."
    )


@patch(PATCH, side_effect=_full_mock)
def test_completion_pct_is_fraction_not_raw_percent(_):
    """CFBD returns PCT as e.g. 65.2 — adapter must divide by 100."""
    result = fetch_qb_college_stats("Trevor Lawrence", 2020, api_key="test-key")
    assert 0.0 < result["completion_pct"] <= 1.0, (
        f"completion_pct={result['completion_pct']} is out of 0–1 range. "
        "Divide the raw CFBD PCT value by 100."
    )


@patch(PATCH, side_effect=_full_mock)
def test_all_purpose_yards_is_passing_plus_rushing(_):
    """all_purpose_yards = passing YDS (3000) + rushing YDS (400) = 3400."""
    result = fetch_qb_college_stats("Trevor Lawrence", 2020, api_key="test-key")
    assert result["all_purpose_yards"] == pytest.approx(3400.0), (
        f"all_purpose_yards={result['all_purpose_yards']}. Expected 3400.0 "
        "(passing 3000 + rushing 400)."
    )


@patch(PATCH, side_effect=_full_mock)
def test_td_int_ratio_uses_actual_int_count(_):
    """TD=30, INT=8 → td_int_ratio = 30 / 8 = 3.75."""
    result = fetch_qb_college_stats("Trevor Lawrence", 2020, api_key="test-key")
    assert result["td_int_ratio"] == pytest.approx(30 / 8, rel=1e-3)


@patch(PATCH, side_effect=_full_mock)
def test_td_int_ratio_caps_denominator_at_one_for_zero_ints(_):
    """Zero INTs must not divide by zero — denominator capped at max(INTs, 1)."""
    # Rebuild mock with INT=0
    def zero_int_mock(url, **kwargs):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        if "category=passing" in url:
            resp.json.return_value = _passing_stats(int_=0)
        elif "category=rushing" in url:
            resp.json.return_value = _rushing_stats()
        elif "/ppa/players/season" in url:
            resp.json.return_value = _ppa_stats()
        elif "/wepa/players/passing" in url:
            resp.json.return_value = _wepa_stats()
        elif "/stats/team/season" in url:
            resp.json.return_value = _team_stats()
        else:
            resp.json.return_value = []
        return resp

    with patch(PATCH, side_effect=zero_int_mock):
        result = fetch_qb_college_stats("Trevor Lawrence", 2020, api_key="test-key")
    assert result["td_int_ratio"] == pytest.approx(30 / 1)


# ── Unit: None semantics ──────────────────────────────────────────────────────

@patch(PATCH, side_effect=_no_ppa_mock)
def test_missing_ppa_returns_none_not_zero(_):
    """PPA absent from API → None. Zero would fabricate a signal."""
    result = fetch_qb_college_stats("Any QB", 2020, api_key="test-key")
    assert result["ppa"] is None, (
        f"ppa={result['ppa']}. Missing PPA must be None, not a default value."
    )


@patch(PATCH, side_effect=_empty_mock)
def test_player_not_found_returns_all_none(_):
    """All endpoints return [] → every feature is None."""
    result = fetch_qb_college_stats("Nobody McUnknown", 2020, api_key="test-key")
    none_values = {k: v for k, v in result.items() if v is not None}
    assert not none_values, (
        f"Expected all-None dict for unknown player. Non-None: {none_values}"
    )


# ── Unit: API key and safety ──────────────────────────────────────────────────

@patch(PATCH, side_effect=_full_mock)
def test_api_key_sent_as_bearer_on_every_request(mock_get):
    fetch_qb_college_stats("Trevor Lawrence", 2020, api_key="my-secret-key")
    assert mock_get.call_count >= 1, "No httpx.get calls were made."
    for call in mock_get.call_args_list:
        headers = call.kwargs.get("headers", {})
        assert headers.get("Authorization") == "Bearer my-secret-key", (
            f"Missing or wrong Authorization header in call to {call.args[0]}. "
            "Every CFBD request must carry 'Bearer <api_key>'."
        )


@patch(PATCH, side_effect=_full_mock)
def test_fetch_does_not_raise_on_full_data(_):
    """Smoke test — must not raise with complete mock data."""
    try:
        fetch_qb_college_stats("Trevor Lawrence", 2020, api_key="test-key")
    except Exception as exc:
        pytest.fail(f"fetch_qb_college_stats raised unexpectedly: {exc}")


@patch(PATCH, side_effect=_no_ppa_mock)
def test_fetch_does_not_raise_on_partial_data(_):
    """Must not raise even when PPA endpoint returns nothing."""
    try:
        fetch_qb_college_stats("Any QB", 2020, api_key="test-key")
    except Exception as exc:
        pytest.fail(f"fetch_qb_college_stats raised on partial data: {exc}")


# ── Integration tests (skipped — require live CFBD Tier 3 key) ───────────────

_SKIP = "Integration: requires live CFBD_API_KEY and network — skip until Phase 2 confirmed"


@pytest.mark.skip(reason=_SKIP)
def test_live_trevor_lawrence_2020():
    import os
    key = os.environ["CFBD_API_KEY"]
    result = fetch_qb_college_stats("Trevor Lawrence", 2020, api_key=key)
    assert result["completion_pct"] is not None
    assert 0.5 < result["completion_pct"] < 1.0
    assert result["ppa"] is not None
    assert result["yards_per_attempt"] > 6.0


@pytest.mark.skip(reason=_SKIP)
def test_live_result_keys_contain_no_prohibited_columns():
    import os
    key = os.environ["CFBD_API_KEY"]
    result = fetch_qb_college_stats("Bryce Young", 2022, api_key=key)
    leaked = set(result.keys()) & PROHIBITED_COLUMNS
    assert not leaked, f"Prohibited columns in live result: {leaked}"
