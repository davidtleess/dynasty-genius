from __future__ import annotations

import json

from src.dynasty_genius.mfl_rookie_adp_divergence import (
    build_mfl_rookie_adp_divergence,
    write_mfl_rookie_adp_divergence_artifacts,
)


def _adp(mfl_id, name, pos, rank):
    return {
        "mfl_id": mfl_id,
        "full_name": name,
        "position": pos,
        "market_adp_rank": rank,
        "market_average_pick": float(rank),
        "source": "mfl_rookie_adp",
        "decision_supported": False,
        "caveats": [
            "mfl_adp_format_blended_qb_count",
            "mfl_adp_te_premium_unfiltered",
        ],
    }


def _card(name, pos, draft_class, xvar_rank, dvs_rank=None):
    return {
        "full_name": name,
        "position": pos,
        "draft_class": draft_class,
        "xvar_class_rank": xvar_rank,
        "dvs_class_rank": dvs_rank,
        "xvar": 0.0,
        "dynasty_value_score": 0.0,
    }


def _build(adp, cards, **kw):
    return build_mfl_rookie_adp_divergence(
        adp,
        cards,
        season=2026,
        captured_at="2026-05-27T00:00:00Z",
        caveats=["source_publish_age_h=1"],
        **kw,
    )


def test_match_flags_and_xvar_primary():
    adp = [
        _adp("1", "Caleb Williams", "QB", 6),
        _adp("2", "Big Riser", "WR", 1),
        _adp("3", "Model Darling", "RB", 12),
    ]
    cards = [
        _card("Caleb Williams", "QB", 2026, 8, dvs_rank=5),
        _card("Big Riser", "WR", 2026, 10),
        _card("Model Darling", "RB", 2026, 2),
    ]

    out = _build(adp, cards)

    by = {r["full_name"]: r for r in out["matched"]}
    assert by["Caleb Williams"]["model_rank"] == 8
    assert by["Caleb Williams"]["rank_gap"] == -2
    assert by["Caleb Williams"]["divergence_flag"] == "aligned"
    assert by["Caleb Williams"]["dvs_class_rank"] == 5
    assert by["Big Riser"]["divergence_flag"] == "market_higher_than_model"
    assert by["Model Darling"]["divergence_flag"] == "model_higher_than_market"
    assert out["rank_source"] == "xvar_class_rank_v1"
    assert out["aligned_band"] == 3
    assert out["decision_supported"] is False
    assert all(r["decision_supported"] is False for r in out["matched"])


def test_model_rank_unavailable_when_xvar_missing():
    adp = [_adp("1", "No Rank", "QB", 3)]
    cards = [_card("No Rank", "QB", 2026, None)]

    out = _build(adp, cards)

    assert out["matched"] == []
    assert out["model_rank_unavailable"][0]["full_name"] == "No Rank"


def test_season_isolation_excludes_other_classes():
    adp = [_adp("1", "Wrong Year", "QB", 1)]
    cards = [_card("Wrong Year", "QB", 2025, 1)]

    out = _build(adp, cards)

    assert out["adp_draft_class"] == 2026
    assert out["matched"] == []
    assert len(out["unmatched_adp"]) == 1


def test_unmatched_both_sides():
    adp = [_adp("1", "Adp Only", "WR", 1)]
    cards = [_card("Card Only", "RB", 2026, 1)]

    out = _build(adp, cards)

    assert [r["full_name"] for r in out["unmatched_adp"]] == ["Adp Only"]
    assert [r["full_name"] for r in out["unmatched_model"]] == ["Card Only"]


def test_fail_closed_ambiguous_not_matched():
    adp = [
        _adp("1", "Dup Name", "WR", 1),
        _adp("2", "Dup Name", "WR", 2),
    ]
    cards = [_card("Dup Name", "WR", 2026, 1)]

    out = _build(adp, cards)

    assert out["matched"] == []
    assert any(
        a["side"] == "adp" and a["reason"] == "adp_identity_ambiguous"
        for a in out["ambiguous"]
    )


def test_coverage_block_reconciles_and_guards():
    adp = [
        _adp("1", "Caleb Williams", "QB", 6),
        _adp("2", "Adp Only", "WR", 1),
        _adp("3", "Dup", "RB", 3),
        _adp("4", "Dup", "RB", 4),
    ]
    cards = [_card("Caleb Williams", "QB", 2026, 8)]

    out = _build(adp, cards)

    cov = out["coverage"]
    assert cov["total_adp_rows"] == 4
    adp_ambig = sum(1 for a in out["ambiguous"] if a["side"] == "adp")
    assert (
        cov["matched_count"]
        + cov["model_rank_unavailable_count"]
        + cov["unmatched_adp_count"]
        + adp_ambig
        == 4
    )
    assert cov["decision_supported_true_count"] == 0
    assert cov["banned_language_present"] == []


def test_writer_emits_run_and_latest_json_and_md(tmp_path):
    out = _build(
        [_adp("1", "Caleb Williams", "QB", 6)],
        [_card("Caleb Williams", "QB", 2026, 8, dvs_rank=5)],
    )

    write_mfl_rookie_adp_divergence_artifacts(out, output_dir=tmp_path, run_id="r1")

    assert {p.name for p in tmp_path.iterdir()} == {
        "mfl_rookie_adp_divergence_latest.json",
        "mfl_rookie_adp_divergence_latest.md",
        "mfl_rookie_adp_divergence_r1.json",
        "mfl_rookie_adp_divergence_r1.md",
    }
    latest_json = json.loads(
        (tmp_path / "mfl_rookie_adp_divergence_latest.json").read_text()
    )
    latest_md = (tmp_path / "mfl_rookie_adp_divergence_latest.md").read_text()
    assert latest_json["matched"][0]["full_name"] == "Caleb Williams"
    assert "Caleb Williams" in latest_md
    assert "aligned" in latest_md
    assert "decision_supported: false" in latest_md
