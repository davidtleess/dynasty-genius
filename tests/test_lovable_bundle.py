"""The read-model bundle the Lovable client reads, and the rules it must not be able to break.

Why this file exists, and why it is shaped the way it is:

The decision behind this bundle is that the CLIENT adapts to our semantics. So the tests below are
not about serialisation; each one pins a way our meaning could be lost in transit:

  a tie must stay an interval          — a tied rank is a range, and its ends are both real
  a null must not become a zero        — a zero model value means replacement level, which is a fact
  an unavailable comparison has no gap — absence of a comparison is itself the finding
  prices come from one snapshot only   — /api/players serves a second, older market overlay
  one bundle is one snapshot           — report, catalog and ownership must all agree
  a written bundle is immutable        — evidence that can be overwritten is not evidence

WHAT THESE TESTS DO NOT CLAIM. They say nothing about how the Lovable client computes anything. Our
value is projected points above replacement and the market's is a trade price; the only claim made
here is that ours cannot be consumed as an equivalent price, and that a margin between the two lanes
cannot be reproduced from our numbers. How the client currently derives what it shows is a question
for whoever reads its source, not something inferable from a rendered screen.

THE FIXTURE IS A DELIBERATE CUT. It is a slice of the ACTUAL payloads served by the frozen preview
8794 at report run 20260906T214512Z, with every source, coverage, basis and populations block kept as
served, but only a handful of rows — chosen to cover a tie, a real zero, a null, a roster player, an
unowned player and three populations. **Its row counts therefore do NOT match its coverage counts,
and that mismatch is intentional**: `test_the_fixture_is_a_deliberate_cut` asserts it, so no later
reader mistakes a metadata assertion for a check on the rows.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.dynasty_genius.adapters.lovable_bundle import (
    BUNDLE_KIND,
    BUNDLE_VERSION,
    BundleRejected,
    build_bundle,
)

FIXTURES = Path(__file__).parent / "fixtures" / "lovable_bundle"
GENERATED_AT = "2026-09-08T19:00:00Z"


def load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text())


def build(**over) -> dict:
    payloads = {
        "market_ranks": load("market_ranks"),
        "comparison": load("comparison"),
        "available": load("available"),
    }
    payloads.update(over)
    return build_bundle(generated_at=GENERATED_AT, **payloads)


def rows_by_name(bundle: dict) -> dict:
    return {r["name"]: r for r in bundle["payloads"]["market_ranks"]["rows"]}


# ── the envelope ────────────────────────────────────────────────────────────────

def test_the_envelope_names_itself_and_its_version():
    bundle = build()
    assert bundle["kind"] == BUNDLE_KIND
    assert bundle["bundle_version"] == BUNDLE_VERSION
    assert bundle["generated_at"] == GENERATED_AT


def test_the_three_payloads_are_carried_verbatim():
    bundle = build()
    for name in ("market_ranks", "comparison", "available"):
        assert bundle["payloads"][name] == load(name), f"{name} was altered on the way through"


def test_building_a_bundle_does_not_mutate_what_it_was_given():
    original = load("market_ranks")
    given = copy.deepcopy(original)
    build(market_ranks=given)
    assert given == original


def test_the_snapshot_records_every_as_of_time_and_the_report_bytes():
    snapshot = build()["snapshot"]
    assert snapshot["report_run"] == "20260906T214512Z"
    assert snapshot["report_sha256"].startswith("19e032a4")
    for field in ("market_sha256", "league_sha256", "catalog_run", "census_run_id"):
        assert snapshot[field], f"{field} is empty"
    # three separate as-of times, because they are genuinely different moments
    assert snapshot["forecast_date"] == "2026-09-06"
    assert snapshot["market_as_of"].startswith("2026-09-06T13:00:02")
    assert snapshot["ownership_as_of"].startswith("2026-09-06T13:00:52")


def test_the_counts_blocks_are_carried_through_unaltered():
    """These describe the FULL snapshot they were served with, not this cut fixture's rows."""
    bundle = build()
    assert bundle["coverage"] == load("market_ranks")["coverage"]
    assert bundle["populations"] == load("available")["populations"]
    assert bundle["basis"] == load("market_ranks")["basis"]


def test_the_fixture_is_a_deliberate_cut():
    """Guards the test above from being read as a check on the rows. It is not, and cannot be."""
    bundle = build()
    ranked = len(bundle["payloads"]["market_ranks"]["rows"])
    available = len(bundle["payloads"]["available"]["rows"])
    assert 0 < ranked < bundle["coverage"]["total_players"]
    assert 0 < available < bundle["populations"]["default"]["total"]


# ── the four rules the old screen broke ─────────────────────────────────────────

def test_a_tied_rank_survives_as_an_interval():
    tie = rows_by_name(build())["Xavier Hutchinson"]["our_rank"]
    assert tie == {"start": 230, "end": 388, "total": 388}
    assert tie["start"] != tie["end"], "a tie collapsed to a single rank"


def test_a_missing_value_and_a_real_zero_stay_different():
    rows = rows_by_name(build())
    assert rows["Cameron Latu"]["model_value"] == 0.0      # scored at replacement level
    assert rows["Kyle McCord"]["model_value"] is None      # not scored at all
    assert rows["Kyle McCord"]["missing_reason"]           # and it says why, in words


def test_an_unavailable_comparison_carries_no_gap():
    latu = rows_by_name(build())["Cameron Latu"]
    assert latu["comparison"]["direction"] == "unavailable"
    assert latu["comparison"]["gap_min"] is None
    assert latu["comparison"]["gap_max"] is None
    assert latu["market_value"] is None
    assert latu["missing_reason"]


def test_a_gap_that_is_a_bound_keeps_both_ends():
    hutchinson = rows_by_name(build())["Xavier Hutchinson"]["comparison"]
    assert hutchinson["direction"] == "overlap"
    assert hutchinson["gap_min"] != hutchinson["gap_max"], "a bound was flattened to one number"


def test_no_row_carries_a_field_from_the_stale_player_overlay():
    bundle = build()
    for row in bundle["payloads"]["market_ranks"]["rows"]:
        for field in ("market_rank_overall", "market_rank_position", "source_timestamp"):
            assert field not in row, f"{field} belongs to the six-week-old overlay"


# ── populations ─────────────────────────────────────────────────────────────────

def test_roster_membership_and_the_available_board_stay_distinct():
    bundle = build()
    ranks = bundle["payloads"]["market_ranks"]["rows"]
    assert any(r["on_roster"] for r in ranks)
    assert any(not r["on_roster"] for r in ranks)

    available = bundle["payloads"]["available"]["rows"]
    populations = {r["population"] for r in available}
    assert "default" in populations and "owned" in populations
    for row in available:
        if row["population"] == "owned":
            assert row["owned_now"] is True
            assert row["roster_id"] is not None
        if row["population"] == "default":
            assert row["owned_now"] is False


def test_identity_is_a_separate_block_that_carries_no_price():
    identity = build()["identity"]
    assert identity["kind"] == "headshot_reference"
    assert identity["path_template"] == "/assets/headshots/{sleeper_id}.jpg"
    assert identity["ids"] is None  # presence is not asserted unless a cache was read
    assert "market_value" not in json.dumps(identity)


def test_identity_lists_only_the_ids_it_was_told_about():
    identity = build_bundle(
        generated_at=GENERATED_AT,
        market_ranks=load("market_ranks"),
        comparison=load("comparison"),
        available=load("available"),
        headshot_ids=["11565", "8130"],
    )["identity"]
    assert identity["ids"] == ["11565", "8130"]


# ── fail closed ─────────────────────────────────────────────────────────────────

def test_rejects_payloads_from_different_report_runs():
    comparison = load("comparison")
    comparison["source"]["report_run"] = "20260907T999999Z"
    with pytest.raises(BundleRejected, match="report_run"):
        build(comparison=comparison)


def test_rejects_payloads_whose_report_bytes_differ():
    available = load("available")
    available["source"]["report_sha256"] = "0" * 64
    with pytest.raises(BundleRejected, match="report_sha256"):
        build(available=available)


def test_rejects_a_payload_with_no_provenance():
    comparison = load("comparison")
    comparison.pop("source")
    with pytest.raises(BundleRejected, match="source"):
        build(comparison=comparison)


def test_rejects_a_payload_whose_provenance_is_blank():
    market_ranks = load("market_ranks")
    market_ranks["source"]["report_sha256"] = ""
    with pytest.raises(BundleRejected, match="report_sha256 is empty"):
        build(market_ranks=market_ranks)


def test_rejects_an_unpinned_catalog():
    available = load("available")
    available["source"]["pinned"] = False
    with pytest.raises(BundleRejected, match="pinned"):
        build(available=available)


def test_rejects_market_ranks_that_are_not_available():
    with pytest.raises(BundleRejected, match="status"):
        build(market_ranks={"status": "not_configured"})


def test_rejects_a_row_carrying_the_stale_player_overlay():
    market_ranks = load("market_ranks")
    market_ranks["rows"][0]["market_rank_overall"] = 129
    with pytest.raises(BundleRejected, match="market_rank_overall"):
        build(market_ranks=market_ranks)


def test_a_rejected_build_writes_nothing(tmp_path):
    from src.dynasty_genius.adapters.lovable_bundle import write_bundle

    out = tmp_path / "bundle.json"
    available = load("available")
    available["source"]["pinned"] = False
    with pytest.raises(BundleRejected):
        write_bundle(
            out,
            market_ranks=load("market_ranks"),
            comparison=load("comparison"),
            available=available,
            generated_at=GENERATED_AT,
        )
    assert not out.exists(), "a rejected build left a file behind"


def test_a_written_bundle_round_trips(tmp_path):
    from src.dynasty_genius.adapters.lovable_bundle import write_bundle

    out = tmp_path / "bundle.json"
    written = write_bundle(
        out,
        market_ranks=load("market_ranks"),
        comparison=load("comparison"),
        available=load("available"),
        generated_at=GENERATED_AT,
    )
    assert json.loads(out.read_text()) == written


# ── root review 2026-09-08: one snapshot means more than one report ──────────────

def test_rejects_payloads_from_different_catalog_runs():
    """The same report can be paired with a different catalog, which is a different board."""
    available = load("available")
    available["source"]["catalog_run"] = "20260908T000000Z"
    with pytest.raises(BundleRejected, match="catalog_run"):
        build(available=available)


def test_rejects_payloads_whose_ownership_captures_differ():
    """Ranks and forecasts dated from different roster captures would disagree about who owns whom."""
    comparison = load("comparison")
    comparison["source"]["ownership_as_of"] = "2026-09-07T13:00:52.635970+00:00"
    with pytest.raises(BundleRejected, match="ownership_as_of"):
        build(comparison=comparison)


def test_rejects_conflicting_catalog_content_hashes():
    """Where two payloads both publish the catalog's content hash, they must be the same bytes."""
    available = load("available")
    available["source"]["catalog_content_sha256"] = "b" * 64
    with pytest.raises(BundleRejected, match="catalog_content_sha256"):
        build(available=available)


def test_the_snapshot_records_the_catalog_identity_it_was_given():
    snapshot = build()["snapshot"]
    assert snapshot["catalog_run"] == "20260907T013635Z"
    assert snapshot["catalog_content_sha256"].startswith("d47c4a40")
    assert snapshot["nfl_status_as_of"]


# ── root review 2026-09-08: refuse malformed input rather than stepping over it ──

def test_a_malformed_row_is_rejected_not_skipped():
    market_ranks = load("market_ranks")
    market_ranks["rows"].append(["not", "an", "object"])
    with pytest.raises(BundleRejected, match="row 5"):
        build(market_ranks=market_ranks)


def test_a_row_without_an_identity_is_rejected():
    market_ranks = load("market_ranks")
    market_ranks["rows"][0] = {k: v for k, v in market_ranks["rows"][0].items() if k != "sleeper_id"}
    with pytest.raises(BundleRejected, match="sleeper_id"):
        build(market_ranks=market_ranks)


def test_rejects_a_report_hash_that_is_not_a_hash():
    """All three carry the SAME bad digest, so they agree with each other and only the format check
    can reject them. Setting it on one payload would be caught by the mismatch check instead, and
    this test would pass without the format check existing at all."""
    payloads = {n: load(n) for n in ("market_ranks", "comparison", "available")}
    for payload in payloads.values():
        payload["source"]["report_sha256"] = "not-a-sha256"
    with pytest.raises(BundleRejected, match="not a sha256 digest"):
        build(**payloads)


def test_rejects_a_coverage_block_that_does_not_hold_counts():
    market_ranks = load("market_ranks")
    market_ranks["coverage"]["common_players"] = "388"
    with pytest.raises(BundleRejected, match="coverage"):
        build(market_ranks=market_ranks)


def test_rejects_a_basis_with_no_seasons():
    market_ranks = load("market_ranks")
    market_ranks["basis"]["years"] = []
    with pytest.raises(BundleRejected, match="basis"):
        build(market_ranks=market_ranks)


def test_rejects_an_available_payload_with_no_populations():
    available = load("available")
    available.pop("populations")
    with pytest.raises(BundleRejected, match="populations"):
        build(available=available)


# ── root review 2026-09-08: a written bundle is immutable evidence ───────────────

def test_refuses_to_overwrite_an_existing_bundle_and_leaves_its_bytes_alone(tmp_path):
    from src.dynasty_genius.adapters.lovable_bundle import write_bundle

    out = tmp_path / "bundle.json"
    out.write_text("evidence from an earlier run\n")
    before = out.read_bytes()

    with pytest.raises(BundleRejected, match="exists"):
        write_bundle(
            out,
            market_ranks=load("market_ranks"),
            comparison=load("comparison"),
            available=load("available"),
            generated_at=GENERATED_AT,
        )
    assert out.read_bytes() == before, "an existing bundle was modified"
