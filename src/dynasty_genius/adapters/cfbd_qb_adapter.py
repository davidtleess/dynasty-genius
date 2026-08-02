"""CFBD QB adapter.

Uses httpx directly against the College Football Data API for QB college stats.

Identity discipline (G1/G7, 2026-08-01): the adapter resolves the player through
`/player/search` and then binds every feature family to that resolved identity by
filtering responses locally. It never passes an unsupported `playerName` filter to
a stats endpoint, and it never takes "the first row that matches a stat type" —
that behaviour attributed one quarterback's season to as many as fifteen players.

Ambiguity is refused, not guessed: when the resolved identity cannot narrow a
response to exactly one record for a value, that value is None.

Transport honesty (G2): a failed request raises `CfbdRequestError`. An empty
response is data ("this player has no rows"); a timeout is not. Collapsing the
two is what made a rate-limited run look like a player with no college career.
"""
from __future__ import annotations

import os
import re
from typing import Any

import httpx
from dotenv import load_dotenv

from src.dynasty_genius.adapters import cfbd_http

load_dotenv()

BASE_URL = "https://api.collegefootballdata.com"

ENDPOINT_PLAYER_SEARCH = "/player/search"
ENDPOINT_PLAYER_SEASON = "/stats/player/season"
ENDPOINT_PPA = "/ppa/players/season"
ENDPOINT_WEPA = "/wepa/players/passing"
# CFBD serves its Swagger docs page at /stats/team/season — an HTTP 200 with
# text/html, not an API route. The adapter called it from Stage 2 onward and the
# old exception-swallowing turned every response into [], which is why
# `qb_sack_rate_final` measured 0/126 dark: the team figures it derives from
# never arrived. Verified live 2026-08-01: /stats/season returns the
# statName/statValue array. The receiving adapter already used the correct path.
ENDPOINT_TEAM_SEASON = "/stats/season"

QB_CFBD_FEATURES: list[str] = [
    "completion_pct",
    "yards_per_attempt",
    "td_int_ratio",
    "sack_rate",
]

#: Keys under which raw, unmodified endpoint responses are exposed to callers
#: that persist a raw snapshot (G6).
RAW_PAYLOAD_KEYS: tuple[str, ...] = (
    "player_search",
    "passing",
    "rushing",
    "ppa",
    "wepa",
    "team",
)


class CfbdRequestError(RuntimeError):
    """Raised when a CFBD request cannot be completed.

    Distinct from an empty result: this means the question was never answered.
    """


def _empty_result() -> dict[str, Any]:
    return {feature: None for feature in QB_CFBD_FEATURES}


def _auth_key(api_key: str | None) -> str:
    key = (api_key or os.getenv("CFBD_API_KEY") or "").strip()
    return key


def _headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


def _normalized(text: Any) -> str:
    return re.sub(r"[^a-z]", "", str(text or "").lower())


def _request_json(
    endpoint: str, params: dict[str, Any], api_key: str
) -> list[dict[str, Any]]:
    """Call CFBD and return the decoded list payload.

    Raises `CfbdRequestError` when the request cannot be completed, so a failure
    is never silently indistinguishable from "no data" (G2). Transient failures
    are retried first via the shared policy in `cfbd_http`: on 2026-08-01 a
    single `Connection reset by peer` during an ~800-call refresh discarded the
    entire paid run. Fail-closed on the record and fail-fast on the batch are
    different things — this keeps the first and drops the second.
    """
    url = f"{BASE_URL}{endpoint}"

    def _call():
        response = httpx.get(url, headers=_headers(api_key), params=params)
        response.raise_for_status()
        return response.json()

    try:
        payload = cfbd_http.with_retry(_call)
    except Exception as exc:  # transport, HTTP status, or JSON decode
        raise CfbdRequestError(
            f"CFBD request to {endpoint} failed: {exc.__class__.__name__}: {exc}"
        ) from exc
    if not isinstance(payload, list):
        # A provider schema change is a failed request, not an empty season.
        raise CfbdRequestError(
            f"CFBD request to {endpoint} returned {type(payload).__name__}, "
            f"expected a JSON array; treating a schema change as no-data is the "
            f"defect this gate exists to prevent"
        )
    return payload


# ── Identity resolution and identity-bound selection (G1/G7) ──────────────────


def _resolve_player_id(
    records: list[dict[str, Any]], player_name: str, college_team: str | None
) -> str | None:
    """Resolve a single provider player id from a `/player/search` response.

    Returns None when the search does not identify exactly one player; callers
    then fall back to unambiguity checks rather than to a positional guess.
    """
    target = _normalized(player_name)
    matches = [row for row in records if _normalized(row.get("name")) == target]
    if college_team:
        # No fallback. Narrowing by team and then reverting to the name-only
        # matches when none survive is not a narrowing at all — it resolves an
        # identically-named quarterback at a different school and accepts his
        # season. The requested team is part of the identity, not a hint.
        team_key = _normalized(college_team)
        matches = [row for row in matches if _normalized(row.get("team")) == team_key]
    if len(matches) != 1:
        return None
    identifier = matches[0].get("id")
    if identifier in (None, ""):
        return None
    return str(identifier)


def _bind_to_player(
    records: list[dict[str, Any]], player_id: str | None, id_field: str
) -> list[dict[str, Any]]:
    """Narrow a response to the resolved player.

    Without a resolved identity NOTHING survives. An unattributed row is not
    evidence about the requested player even when it is the only row present —
    "there was just one, so it must be his" is precisely the reasoning that
    attributed a single quarterback's season to nine of them. Unresolved
    identity yields no features, not convenient ones.
    """
    if not player_id:
        return []
    return [row for row in records if str(row.get(id_field, "")) == player_id]


def _stat_value(records: list[dict[str, Any]], stat_key: str) -> float | None:
    """Return a stat only when exactly one record carries it.

    Zero records means absent. More than one means the response spans multiple
    players and identity did not disambiguate them — that is refused, because
    picking one is how nine quarterbacks came to share a single stat line.
    """
    candidates = [
        row
        for row in records
        if str(row.get("statType", "")).strip().upper() == stat_key
    ]
    if len(candidates) != 1:
        return None
    value = candidates[0].get("stat")
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _team_stat(records: list[dict[str, Any]], stat_name: str) -> float | None:
    for row in records:
        if str(row.get("statName", "")).strip() == stat_name:
            value = row.get("statValue")
            if value in (None, ""):
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
    return None


def _ppa_value(
    records: list[dict[str, Any]], player_id: str | None
) -> float | None:
    rows = _bind_to_player(records, player_id, "id")
    if len(rows) != 1:
        return None
    average_ppa = rows[0].get("averagePPA")
    if not isinstance(average_ppa, dict):
        return None
    value = average_ppa.get("all")
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _wepa_value(
    records: list[dict[str, Any]], player_id: str | None
) -> float | None:
    rows = _bind_to_player(records, player_id, "athleteId")
    if len(rows) != 1:
        return None
    value = rows[0].get("wepa")
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _sum_present(*values: float | None) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return float(sum(present))


def _completion_fraction(value: float | None) -> float | None:
    """Return completion percentage as a fraction, without double-dividing.

    CFBD has served this field both as a percentage (65.2) and as a fraction
    (0.652). The old adapter divided unconditionally, so a fraction became
    0.00594 — the defect measured across 62/62 populated rows on 2026-08-01.
    Magnitude decides: a completion rate above 1.0 can only be a percentage.
    """
    if value is None:
        return None
    return value / 100.0 if value > 1.0 else value


# ── Fetch + normalize ─────────────────────────────────────────────────────────


def _fetch_raw_payloads(
    player_name: str, year: int, key: str, college_team: str | None
) -> dict[str, list[dict[str, Any]]]:
    """Fetch every endpoint response, unmodified, keyed by `RAW_PAYLOAD_KEYS`."""
    search_params: dict[str, Any] = {
        "searchTerm": player_name,
        "year": year,
        "position": "QB",
    }
    if college_team:
        search_params["team"] = college_team
    search_records = _request_json(ENDPOINT_PLAYER_SEARCH, search_params, key)
    player_id = _resolve_player_id(search_records, player_name, college_team)

    team_name = college_team or next(
        (
            row.get("team")
            for row in search_records
            if _normalized(row.get("name")) == _normalized(player_name)
            and row.get("team")
        ),
        None,
    )

    def _season_params(category: str) -> dict[str, Any]:
        params: dict[str, Any] = {"year": year, "category": category}
        if team_name:
            params["team"] = team_name
        return params

    passing = _request_json(ENDPOINT_PLAYER_SEASON, _season_params("passing"), key)
    rushing = _request_json(ENDPOINT_PLAYER_SEASON, _season_params("rushing"), key)

    ppa_params: dict[str, Any] = {"year": year}
    if player_id:
        ppa_params["playerId"] = player_id
    if team_name:
        ppa_params["team"] = team_name
    ppa = _request_json(ENDPOINT_PPA, ppa_params, key)

    wepa_params: dict[str, Any] = {"year": year}
    if team_name:
        wepa_params["team"] = team_name
    wepa = _request_json(ENDPOINT_WEPA, wepa_params, key)

    team_records: list[dict[str, Any]] = []
    if team_name:
        team_records = _request_json(
            ENDPOINT_TEAM_SEASON, {"year": year, "team": team_name}, key
        )

    return {
        "player_search": search_records,
        "passing": passing,
        "rushing": rushing,
        "ppa": ppa,
        "wepa": wepa,
        "team": team_records,
    }


def normalize_qb_payloads(
    raw: dict[str, list[dict[str, Any]]],
    player_name: str,
    college_team: str | None = None,
) -> dict[str, Any]:
    """Derive the QB contract from raw endpoint payloads.

    Pure: the same raw snapshot always yields the same features, which is what
    lets a cached raw snapshot be re-normalized without another paid call.
    """
    search_records = raw.get("player_search") or []
    player_id = _resolve_player_id(search_records, player_name, college_team)

    passing = _bind_to_player(raw.get("passing") or [], player_id, "playerId")
    rushing = _bind_to_player(raw.get("rushing") or [], player_id, "playerId")
    team_records = raw.get("team") or []

    passing_yards = _stat_value(passing, "YDS")
    rushing_yards = _stat_value(rushing, "YDS")
    rushing_tds = _stat_value(rushing, "TD")
    completion_pct = _completion_fraction(_stat_value(passing, "PCT"))
    yards_per_attempt = _stat_value(passing, "YPA")
    passing_tds = _stat_value(passing, "TD")
    interceptions = _stat_value(passing, "INT")
    player_pass_attempts = _stat_value(passing, "ATT")

    team_pass_attempts = _team_stat(team_records, "passAttempts")
    # CFBD has no `sacksAllowed` stat — verified live 2026-08-01 against the 63
    # statNames /stats/season actually returns. `sacks` is what THIS defence
    # recorded; `sacksOpponent` is what opposing defences recorded against this
    # offence, i.e. sacks allowed. Using `sacks` would measure the defence and
    # attribute it to the quarterback. Magnitude check across 2020 Clemson /
    # Alabama / Georgia gives 4.1% / 4.1% / 5.9%, the right range for a college
    # offence; `sacks` would have produced 8.6% for Clemson.
    sacks_allowed = _team_stat(team_records, "sacksOpponent")
    net_passing_yards = _team_stat(team_records, "netPassingYards")

    td_int_ratio = None
    if passing_tds is not None and interceptions is not None:
        td_int_ratio = passing_tds / max(interceptions, 1.0)

    sack_rate = None
    if team_pass_attempts is not None and sacks_allowed is not None:
        denominator = team_pass_attempts + sacks_allowed
        if denominator > 0:
            sack_rate = sacks_allowed / denominator

    passing_yards_share = None
    if passing_yards is not None and net_passing_yards not in (None, 0):
        passing_yards_share = passing_yards / net_passing_yards

    return {
        "completion_pct": completion_pct,
        "yards_per_attempt": yards_per_attempt,
        "td_int_ratio": td_int_ratio,
        "sack_rate": sack_rate,
        "all_purpose_yards": _sum_present(passing_yards, rushing_yards),
        "passing_yards_share": passing_yards_share,
        "ppa": _ppa_value(raw.get("ppa") or [], player_id),
        "wepa": _wepa_value(raw.get("wepa") or [], player_id),
        "rushing_yards": rushing_yards,
        "rushing_tds": rushing_tds,
        "pass_attempts": (
            int(player_pass_attempts) if player_pass_attempts is not None else None
        ),
    }


def fetch_qb_college_stats(
    player_name: str,
    year: int,
    api_key: str,
    college_team: str | None = None,
    raw_sink: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Fetch QB college stats from CFBD and normalize them into the contract shape.

    When `raw_sink` is supplied it is populated with the unmodified endpoint
    responses so the caller can persist a genuine raw snapshot (G6).
    """
    key = _auth_key(api_key)
    if not key:
        return _empty_result()

    raw = _fetch_raw_payloads(player_name, year, key, college_team)
    if raw_sink is not None:
        raw_sink.update(raw)
    return normalize_qb_payloads(raw, player_name, college_team)
