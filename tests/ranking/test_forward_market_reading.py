"""A new research reading keeps forecast vintage separate from later market observation."""

import copy
import hashlib
import json
from datetime import datetime, timezone

import pytest

from src.dynasty_genius.ranking import market_ranks as ranking
from tests.ranking.market_ranks_fixtures import synthetic_sources


def template_bundle(tmp_path):
    from src.dynasty_genius.capture.workspace_snapshot_sources import (
        load_workspace_snapshot,
    )
    from tests.contract.workspace_snapshot_fixtures import write_sources

    return load_workspace_snapshot(*write_sources(tmp_path / "inputs"))


def later_market(market, stamp="2026-09-10T13:00:00+00:00"):
    market = copy.deepcopy(market)
    market["snapshot_date"] = stamp[:10]
    market["retrieved_at"] = stamp
    for item in [market["capture_report"], *market["entries"]]:
        item["snapshot_date"] = stamp[:10]
        item["retrieved_at"] = stamp
    return market


def forward(report, market, league):
    method = getattr(ranking, "build_forward_market_ranks", None)
    assert callable(method), "Explicit forward reading entry point is required"
    return method(report, market, league)


def test_new_market_date_does_not_rewrite_forecast_or_old_reader():
    report, market, league = synthetic_sources()
    old = ranking.build_market_ranks(report, market, league)
    inputs = copy.deepcopy((report, market, league))
    updated_market = later_market(market)
    with pytest.raises(ranking.SourceError, match="dates differ"):
        ranking.build_market_ranks(report, updated_market, league)
    updated = forward(report, updated_market, league)
    assert updated["source"]["forecast_date"] == old["source"]["forecast_date"]
    assert updated["source"]["ownership_as_of"] == old["source"]["ownership_as_of"]
    assert updated["source"]["market_as_of"] == "2026-09-10T13:00:00+00:00"
    assert updated["rows"] == old["rows"]
    assert (report, market, league) == inputs


@pytest.mark.parametrize("stamp", ["2026-09-05T13:00:00+00:00", "invalid"])
def test_forward_market_refuses_earlier_or_invalid_dates(stamp):
    report, market, league = synthetic_sources()
    with pytest.raises(ranking.SourceError):
        forward(report, later_market(market, stamp), league)


def test_forward_market_does_not_relax_ownership_or_price_checks():
    report, market, league = synthetic_sources()
    market = later_market(market)
    report["league"]["captured_at"] = "2026-09-10T00:00:00+00:00"
    with pytest.raises(ranking.SourceError, match="ownership captures differ"):
        forward(report, market, league)
    report, original, league = synthetic_sources()
    market = later_market(original)
    market["entries"][0]["value"] += 1
    with pytest.raises(ranking.SourceError, match="hash mismatch"):
        forward(report, market, league)


def test_market_day_must_match_its_actual_capture_time():
    report, market, league = synthetic_sources()
    market = later_market(market)
    market["snapshot_date"] = "2026-09-09"
    with pytest.raises(ranking.SourceError):
        forward(report, market, league)


def test_forward_retains_unknown_position_price_without_paired_rank_or_pick_count():
    report, market, league = synthetic_sources()
    market = later_market(market)
    row = market["entries"][0]
    sid, value = row["sleeper_id"], row["value"]
    row["position"] = "UNK"
    row["payload_hash"] = ranking.digest({key: row[key] for key in ranking.ROW_HASH_FIELDS})
    market["capture_report"]["store_hash"] = ranking.digest({"sigs": sorted(e["player_key"] + ":" + e["payload_hash"] for e in market["entries"])})
    result = forward(report, market, league)
    actual = next(r for r in result["rows"] if r["sleeper_id"] == sid)
    assert actual["market_value"] == value
    assert actual["model_value"] is not None
    assert actual["our_rank"] is None and actual["market_rank"] is None
    assert "position" in actual["missing_reason"].lower()
    assert result["coverage"]["market_unresolved_positions"] == 1
    assert result["coverage"]["market_picks"] == 1  # the fixture's actual draft pick
    assert result["coverage"]["common_players"] == 1  # only player 2 still pairs


def test_forward_still_refuses_a_conflicting_known_market_position():
    report, market, league = synthetic_sources()
    market = later_market(market)
    row = market["entries"][0]
    row["position"] = "WR"
    row["payload_hash"] = ranking.digest({key: row[key] for key in ranking.ROW_HASH_FIELDS})
    market["capture_report"]["store_hash"] = ranking.digest({"sigs": sorted(e["player_key"] + ":" + e["payload_hash"] for e in market["entries"])})
    with pytest.raises(ranking.SourceError, match="positions disagree"):
        forward(report, market, league)


def factory():
    try:
        from src.dynasty_genius.capture.forward_market_reading import (
            build_forward_reading,
        )
    except ImportError:
        pytest.fail("Forward snapshot factory is not implemented")
    return build_forward_reading


def test_factory_preserves_template_and_round_trips_as_a_new_archive(tmp_path):
    from src.dynasty_genius.capture.workspace_snapshot_store import (
        read_snapshot,
        save_snapshot,
    )

    original = template_bundle(tmp_path)
    before = copy.deepcopy(original)
    newer = later_market(json.loads(original.artifacts["market.json"]))
    market_bytes = json.dumps(newer).encode()
    bundle = factory()(original, market_bytes, capture_artifacts={"capture-report.json": json.dumps(newer["capture_report"]).encode()})
    assert original == before
    for name in ["report.json", "league.json", "catalog.json", "catalog-companion.json", "evaluation-plan.json"]:
        assert bundle.artifacts[name] == original.artifacts[name]
    assert bundle.artifacts["market.json"] == market_bytes
    assert bundle.comparison == original.comparison
    assert bundle.ranks["source"]["market_sha256"] == hashlib.sha256(market_bytes).hexdigest()
    assert bundle.ranks["source"]["forecast_date"] == "2026-09-06"
    saved = save_snapshot(tmp_path / "new-archive", bundle, captured_at=datetime(2026, 9, 10, 14, tzinfo=timezone.utc), code_sha="unknown")
    loaded = read_snapshot(tmp_path / "new-archive", saved["snapshot"]["snapshot_id"])
    assert loaded["snapshot"]["market_as_of"] == "2026-09-10T13:00:00+00:00"
    assert loaded["snapshot"]["forecast_date"] == "2026-09-06"
    assert loaded["comparison"] == original.comparison


def test_factory_rejects_moved_original_source_or_derived_values(tmp_path):
    original = template_bundle(tmp_path)
    newer = later_market(json.loads(original.artifacts["market.json"]))
    market_bytes = json.dumps(newer).encode()
    original.ranks["rows"][0]["model_value"] += 1
    with pytest.raises(ValueError, match="template"):
        factory()(original, market_bytes, capture_artifacts={})


@pytest.mark.parametrize("field,changed", [("team", "XXX"), ("model_zero_tie", True), ("reference_player", "Different reference")])
def test_factory_rejects_template_identity_and_zero_tie_drift(tmp_path, field, changed):
    original = template_bundle(tmp_path)
    newer = json.dumps(later_market(json.loads(original.artifacts["market.json"]))).encode()
    original.ranks["rows"][0][field] = changed
    with pytest.raises(ValueError, match="template rank values"):
        factory()(original, newer, capture_artifacts={"receipt.json": b"{}"})


def test_factory_does_not_hide_capture_evidence_or_allow_paths(tmp_path):
    import base64

    original = template_bundle(tmp_path)
    newer = json.dumps(later_market(json.loads(original.artifacts["market.json"]))).encode()
    raw = b'{"status": "ok", "note": "original bytes retained"}\n'
    bundle = factory()(original, newer, capture_artifacts={"receipt.json": raw})
    evidence = json.loads(bundle.artifacts["source-manifest.json"])["capture_evidence"]["receipt.json"]
    assert base64.b64decode(evidence["base64"]) == raw
    assert evidence["sha256"] == hashlib.sha256(raw).hexdigest()
    with pytest.raises(ValueError, match="artifact"):
        factory()(original, newer, capture_artifacts={"../escape.json": raw})


def test_forward_preserves_unresolved_identity_in_raw_capture_without_inventing_player():
    report, market, league = synthetic_sources()
    market = later_market(market)
    entry = market['entries'][0]
    entry['sleeper_id'] = None
    entry['payload_hash'] = ranking.digest({key: entry[key] for key in ranking.ROW_HASH_FIELDS})
    market['capture_report']['joinable_rows_written'] -= 1
    market['capture_report']['store_hash'] = ranking.digest({'sigs': sorted(e['player_key']+':'+e['payload_hash'] for e in market['entries'])})
    before = copy.deepcopy(market)
    result = forward(report, market, league)
    assert market == before
    assert result['coverage']['market_unresolved_identities'] == 1
    assert result['coverage']['market_picks'] == 1
    row = next(r for r in result['rows'] if r['sleeper_id'] == '1')
    assert row['model_value'] == 20 and row['market_value'] is None
    assert result['coverage']['common_players'] == 1
    entry['value'] += 1
    with pytest.raises(ranking.SourceError, match='hash mismatch'):
        forward(report, market, league)
