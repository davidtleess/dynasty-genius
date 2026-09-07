"""DG183 contract: independent ranks, bound sources and honest missing values."""

import copy
import json
from pathlib import Path

import pytest

from src.dynasty_genius.ranking.market_ranks import (
    SourceError,
    build_market_ranks,
    compare,
    load_market_ranks,
    ranks,
)

INPUTS = Path(__file__).resolve().parents[2] / "runs/20260907T112015Z/inputs"


@pytest.fixture
def sources():
    from tests.ranking.market_ranks_fixtures import synthetic_sources

    return synthetic_sources()


@pytest.fixture
def frozen_sources():
    if not INPUTS.exists():
        pytest.skip(
            "local frozen acceptance source; portable source checks run separately"
        )
    return [
        json.loads((INPUTS / name).read_text())
        for name in ("report.json", "market.json", "league_snapshot.json")
    ]


def test_interval_math():
    assert ranks({"a": 8, "b": 0, "c": 0}) == {
        "a": {"start": 1, "end": 1, "total": 3},
        "b": {"start": 2, "end": 3, "total": 3},
        "c": {"start": 2, "end": 3, "total": 3},
    }

    def rank(a, b):
        return {"start": a, "end": b, "total": 10}

    assert compare(rank(2, 3), rank(7, 8)) == {
        "direction": "higher",
        "gap_min": 4,
        "gap_max": 6,
    }
    assert compare(rank(7, 8), rank(2, 3)) == {
        "direction": "lower",
        "gap_min": -6,
        "gap_max": -4,
    }
    assert compare(rank(2, 3), rank(2, 3))["direction"] == "overlap"
    assert compare(rank(2, 2), rank(2, 2))["direction"] == "same"
    assert compare(None, rank(2, 2))["direction"] == "unavailable"


def test_frozen_population(frozen_sources):
    payload = build_market_ranks(*frozen_sources)
    assert payload["coverage"] == dict(
        model_players=825,
        market_players=399,
        market_picks=24,
        common_players=388,
        total_players=836,
        roster_players=27,
        roster_common_players=26,
    )
    rows = {r["sleeper_id"]: r for r in payload["rows"]}
    ali = next(r for r in rows.values() if r["name"] == "Rasheen Ali")
    assert ali["on_roster"] and ali["market_value"] is None and ali["our_rank"] is None
    assert ali["model_rank_all"] is not None
    zero = [r for r in rows.values() if r["model_zero_tie"] and r["our_rank"]]
    assert len(zero) == 159
    assert all(r["our_rank"] == dict(start=230, end=388, total=388) for r in zero)
    assert rows["9484"]["market_rank_published"] == 67
    assert sum(r["comparison"]["direction"] == "higher" for r in rows.values()) == 136
    assert sum(r["comparison"]["direction"] == "lower" for r in rows.values()) == 138


@pytest.mark.parametrize(
    "corruption",
    [
        "value",
        "negative",
        "duplicate",
        "position",
        "roster",
        "date",
        "settings",
        "hash",
        "target",
        "season",
        "te_premium",
        "slots",
        "event",
    ],
)
def test_corrupt_sources_refuse(sources, corruption):
    report, market, league = copy.deepcopy(sources)
    row = report["horizon_board"]["all_inspectable"][0]
    if corruption == "value":
        row["value"] = float("nan")
    if corruption == "negative":
        row["value"] = -1
    if corruption == "duplicate":
        report["horizon_board"]["all_inspectable"].append(row)
    if corruption == "position":
        row["position"] = "K"
    if corruption == "roster":
        row["on_davids_roster"] = not row["on_davids_roster"]
    if corruption == "date":
        market["snapshot_date"] = "2026-08-01"
    if corruption == "settings":
        market["settings"]["numQbs"] = 1
    if corruption == "hash":
        market["entries"][0]["value"] += 1
    if corruption == "target":
        report["board_target"]["window"] = "full_season"
    if corruption == "season":
        row["seasons"][0]["season"] = 2025
    if corruption == "slots":
        league["league"]["roster_positions"].append("QB")
    if corruption == "event":
        report["board_target"]["event"] = "breakout"
    if corruption == "te_premium":
        league["league"]["scoring_settings"]["bonus_rec_te"] = 1
    with pytest.raises(SourceError):
        build_market_ranks(report, market, league)


def test_manifest_tamper(tmp_path, sources):
    import hashlib

    sources[0]["inputs"]["snapshot"]["sha256"] = hashlib.sha256(
        json.dumps(sources[2]).encode()
    ).hexdigest()
    manifest = {"schema_version": 1, "report_run": sources[0]["run"], "files": {}}
    for key, data in zip(("report", "market", "league"), sources):
        p = tmp_path / f"{key}.json"
        p.write_text(json.dumps(data))
        manifest["files"][key] = {
            "path": str(p),
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        }
    mp = tmp_path / "manifest.json"
    mp.write_text(json.dumps(manifest))
    assert load_market_ranks(mp)["status"] == "available"
    (tmp_path / "market.json").write_text("{}")
    with pytest.raises(SourceError):
        load_market_ranks(mp)


def test_synthetic_union_missing_and_zero(sources):
    rows = {r["sleeper_id"]: r for r in build_market_ranks(*sources)["rows"]}
    assert set(rows) == {"1", "2", "3", "4"}
    assert rows["3"]["model_value"] == 0 and rows["3"]["market_value"] is None
    assert rows["4"]["model_value"] is None and rows["4"]["market_value"] == 20
    assert rows["2"]["comparison"]["direction"] == "lower"
    assert rows["1"]["comparison"]["direction"] == "higher"


def test_manifest_rejects_report_bound_snapshot_mismatch(tmp_path, sources):
    import hashlib

    sources[0]["inputs"]["snapshot"]["sha256"] = "0" * 64
    manifest = {"schema_version": 1, "report_run": sources[0]["run"], "files": {}}
    for key, data in zip(("report", "market", "league"), sources):
        p = tmp_path / f"{key}.json"
        p.write_text(json.dumps(data))
        manifest["files"][key] = {
            "path": str(p),
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        }
    mp = tmp_path / "manifest.json"
    mp.write_text(json.dumps(manifest))
    with pytest.raises(SourceError, match="Report-bound ownership bytes differ"):
        load_market_ranks(mp)
