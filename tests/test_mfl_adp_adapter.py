from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ADP_FIXTURE = Path("tests/fixtures/mfl_rookie_adp_2026_05_27.json")
PLAYERS_FIXTURE = Path("tests/fixtures/mfl_players_2026_05_27.json")


def _adp_player_rows() -> list[dict]:
    return json.loads(ADP_FIXTURE.read_text())["adp"]["player"]


def _players_rows() -> list[dict]:
    return json.loads(PLAYERS_FIXTURE.read_text())["players"]["player"]


def _write_adp_cache(path, fetched_at, source_ts, rows, ttl=24):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "fetched_at": fetched_at,
        "source_timestamp": source_ts,
        "ttl_hours": ttl,
        "data": rows,
    }))


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


def test_source_publish_age_parses_epoch():
    from src.dynasty_genius.adapters.mfl_adp_adapter import (
        _source_publish_age_hours,
    )

    one_hour_ago = str(int(time.time()) - 3600)
    age = _source_publish_age_hours(one_hour_ago)
    assert age is not None
    assert 0.9 < age < 1.2


def test_source_publish_age_unparseable_returns_none():
    from src.dynasty_genius.adapters.mfl_adp_adapter import (
        _source_publish_age_hours,
    )

    assert _source_publish_age_hours(None) is None
    assert _source_publish_age_hours("not-a-timestamp") is None


def test_freshness_caveats_flags_missing_timestamp():
    from src.dynasty_genius.adapters.mfl_adp_adapter import _freshness_caveats

    assert "mfl_adp_timestamp_unavailable" in _freshness_caveats(None)
    valid_epoch = str(int(time.time()))
    assert "mfl_adp_timestamp_unavailable" not in _freshness_caveats(valid_epoch)


def test_adp_stage1_fresh_cache_served(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.dynasty_genius.adapters.mfl_adp_adapter.CACHE_DIR",
        tmp_path,
    )
    from src.dynasty_genius.adapters import mfl_adp_adapter as m

    fresh = datetime.now(timezone.utc).strftime(m._TS_FMT)
    source_ts = str(int(time.time()))
    _write_adp_cache(m._adp_cache_file(2026), fresh, source_ts, _adp_player_rows())
    with patch("httpx.get", side_effect=AssertionError("must not hit network")):
        rows, caveats = m.fetch_adp_with_cache(2026)
    assert len(rows) == len(_adp_player_rows())
    assert any(c.startswith("source_publish_age_h=") for c in caveats)


def test_adp_stage2_stale_serve_carries_both_ages(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.dynasty_genius.adapters.mfl_adp_adapter.CACHE_DIR",
        tmp_path,
    )
    from src.dynasty_genius.adapters import mfl_adp_adapter as m

    old = (datetime.now(timezone.utc) - timedelta(hours=48)).strftime(m._TS_FMT)
    old_source_ts = str(int(time.time()) - 48 * 3600)
    _write_adp_cache(m._adp_cache_file(2026), old, old_source_ts, _adp_player_rows())
    with patch("httpx.get", side_effect=Exception("network error")):
        rows, caveats = m.fetch_adp_with_cache(2026)
    assert len(rows) == len(_adp_player_rows())
    assert "stale_market_data" in caveats
    assert any(c.startswith("cache_age_h=") for c in caveats)
    assert any(c.startswith("source_publish_age_h=") for c in caveats)


def test_adp_stage3_cold_fail(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.dynasty_genius.adapters.mfl_adp_adapter.CACHE_DIR",
        tmp_path,
    )
    from src.dynasty_genius.adapters import mfl_adp_adapter as m

    with patch("httpx.get", side_effect=Exception("network error")):
        rows, caveats = m.fetch_adp_with_cache(2026)
    assert rows == []
    assert "market_data_unavailable" in caveats


def test_adp_live_refresh_parses_and_caches(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.dynasty_genius.adapters.mfl_adp_adapter.CACHE_DIR",
        tmp_path,
    )
    from src.dynasty_genius.adapters import mfl_adp_adapter as m

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return json.loads(ADP_FIXTURE.read_text())

    with patch("httpx.get", return_value=_Resp()):
        rows, _caveats = m.fetch_adp_with_cache(2026)
    assert len(rows) == len(_adp_player_rows())
    assert "junk" not in rows[0]
    assert m._adp_cache_file(2026).exists()


def test_adp_wrong_season_cache_not_served(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.dynasty_genius.adapters.mfl_adp_adapter.CACHE_DIR",
        tmp_path,
    )
    from src.dynasty_genius.adapters import mfl_adp_adapter as m

    fresh = datetime.now(timezone.utc).strftime(m._TS_FMT)
    source_ts = str(int(time.time()))
    _write_adp_cache(m._adp_cache_file(2025), fresh, source_ts, _adp_player_rows())
    with patch("httpx.get", side_effect=Exception("network error")):
        rows, caveats = m.fetch_adp_with_cache(2026)
    assert rows == []
    assert "market_data_unavailable" in caveats


def test_players_live_refresh_builds_map(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.dynasty_genius.adapters.mfl_adp_adapter.CACHE_DIR",
        tmp_path,
    )
    from src.dynasty_genius.adapters import mfl_adp_adapter as m

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return json.loads(PLAYERS_FIXTURE.read_text())

    with patch("httpx.get", return_value=_Resp()):
        pmap, _caveats = m.fetch_players_with_cache(2026)
    first = _players_rows()[0]
    assert pmap[first["id"]]["name"] == first["name"]
    assert pmap[first["id"]]["position"] == first["position"]
    assert m._players_cache_file(2026).exists()


def test_players_cold_fail_returns_empty_map_with_caveat(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.dynasty_genius.adapters.mfl_adp_adapter.CACHE_DIR",
        tmp_path,
    )
    from src.dynasty_genius.adapters import mfl_adp_adapter as m

    with patch("httpx.get", side_effect=Exception("network error")):
        pmap, caveats = m.fetch_players_with_cache(2026)
    assert pmap == {}
    assert "mfl_players_map_unavailable" in caveats


def test_players_handles_singleton(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.dynasty_genius.adapters.mfl_adp_adapter.CACHE_DIR",
        tmp_path,
    )
    from src.dynasty_genius.adapters import mfl_adp_adapter as m

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "players": {
                    "player": {
                        "id": "1",
                        "name": "Solo, Han",
                        "position": "WR",
                        "team": "FA",
                    },
                },
            }

    with patch("httpx.get", return_value=_Resp()):
        pmap, _caveats = m.fetch_players_with_cache(2026)
    assert pmap["1"]["name"] == "Solo, Han"


def test_normalize_matched_row():
    from src.dynasty_genius.adapters.mfl_adp_adapter import (
        _rows_to_player_map,
        normalize_mfl_adp_entry,
    )

    pmap = _rows_to_player_map(_players_rows())
    row = _adp_player_rows()[0]
    out = normalize_mfl_adp_entry(row, pmap)
    assert out["mfl_id"] == row["id"]
    assert out["full_name"] == pmap[row["id"]]["name"]
    assert out["position"] == pmap[row["id"]]["position"]
    assert out["market_adp_rank"] == int(row["rank"])
    assert out["market_average_pick"] == float(row["averagePick"])
    assert out["market_min_pick"] == int(row["minPick"])
    assert out["market_max_pick"] == int(row["maxPick"])
    assert out["draft_selection_pct"] == float(row["draftSelPct"])
    assert out["drafts_selected_in"] == int(row["draftsSelectedIn"])
    assert out["source"] == "mfl_rookie_adp"
    assert out["decision_supported"] is False
    assert "mfl_adp_format_blended_qb_count" in out["caveats"]
    assert "mfl_adp_te_premium_unfiltered" in out["caveats"]


def test_normalize_unmatched_row_has_none_identity():
    from src.dynasty_genius.adapters.mfl_adp_adapter import (
        _rows_to_player_map,
        normalize_mfl_adp_entry,
    )

    pmap = _rows_to_player_map(_players_rows())
    unmatched = next(r for r in _adp_player_rows() if r["id"] == "99999")
    out = normalize_mfl_adp_entry(unmatched, pmap)
    assert out["mfl_id"] == "99999"
    assert out["full_name"] is None
    assert out["position"] is None
    assert out["decision_supported"] is False
    assert out["market_adp_rank"] == int(unmatched["rank"])
