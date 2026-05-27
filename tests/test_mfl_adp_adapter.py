from __future__ import annotations

import json
from pathlib import Path

ADP_FIXTURE = Path("tests/fixtures/mfl_rookie_adp_2026_05_27.json")
PLAYERS_FIXTURE = Path("tests/fixtures/mfl_players_2026_05_27.json")


def _adp_player_rows() -> list[dict]:
    return json.loads(ADP_FIXTURE.read_text())["adp"]["player"]


def _players_rows() -> list[dict]:
    return json.loads(PLAYERS_FIXTURE.read_text())["players"]["player"]


def test_adp_url_has_locked_params():
    from src.dynasty_genius.adapters.mfl_adp_adapter import ADP_API_URL_TEMPLATE

    url = ADP_API_URL_TEMPLATE.format(year=2026)
    assert "TYPE=adp" in url
    assert "ROOKIES=1" in url
    assert "FCOUNT=12" in url
    assert "IS_PPR=1" in url
    assert "IS_MOCK=No" in url
    assert "IS_KEEPER=Rookie" not in url


def test_as_list_normalizes_singleton_and_list():
    from src.dynasty_genius.adapters.mfl_adp_adapter import _as_list

    assert _as_list([{"id": "1"}]) == [{"id": "1"}]
    assert _as_list({"id": "1"}) == [{"id": "1"}]
    assert _as_list(None) == []


def test_cache_files_are_season_scoped():
    from src.dynasty_genius.adapters.mfl_adp_adapter import (
        _adp_cache_file,
        _players_cache_file,
    )

    assert _adp_cache_file(2026).name == "adp_2026.json"
    assert _players_cache_file(2025).name == "players_2025.json"
    assert _adp_cache_file(2026) != _adp_cache_file(2025)


def test_sanitizers_keep_only_allowed_fields():
    from src.dynasty_genius.adapters.mfl_adp_adapter import (
        _sanitize_adp,
        _sanitize_players,
    )

    adp = _sanitize_adp([dict(_adp_player_rows()[0], junk="x")])
    assert "junk" not in adp[0]
    assert set(adp[0]) <= {
        "id",
        "rank",
        "averagePick",
        "minPick",
        "maxPick",
        "draftSelPct",
        "draftsSelectedIn",
    }

    players = _sanitize_players([dict(_players_rows()[0], junk="x")])
    assert "junk" not in players[0]
    assert set(players[0]) <= {"id", "name", "position", "team"}
