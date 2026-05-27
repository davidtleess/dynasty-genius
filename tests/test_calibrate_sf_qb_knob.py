from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scripts.calibrate_sf_qb_knob as cal
from scripts.calibrate_sf_qb_knob import (
    is_rookie_draft,
    nfl_skill_ranks_from_outcomes,
    normalize_name,
    qb_promotions,
    recommend_k,
    round_half_up,
)


def test_round_half_up_is_not_bankers():
    assert round_half_up(0.5) == 1
    assert round_half_up(2.5) == 3
    assert round_half_up(1.5) == 2


def test_recommend_k_clamps_and_half_up():
    assert recommend_k([0.0, 1.0]) == 1
    assert recommend_k([2.0, 3.0]) == 3
    assert recommend_k([5.0, 5.0, 5.0]) == 3
    assert recommend_k([-2.0, -1.0]) == 0
    assert recommend_k([]) == 0


def test_normalize_name_strips_case_punct_suffix():
    assert normalize_name("Michael Penix Jr.") == normalize_name("michael penix")
    assert normalize_name("Ja'Marr Chase") == "jamarr chase"
    assert normalize_name("Marvin Harrison Jr.") == "marvin harrison"


def test_is_rookie_draft_requires_small_rounds_and_complete():
    assert is_rookie_draft({"status": "complete", "settings": {"rounds": 3}}) is True
    assert is_rookie_draft({"status": "complete", "settings": {"rounds": 15}}) is False
    assert is_rookie_draft({"status": "drafting", "settings": {"rounds": 3}}) is False


def test_nfl_skill_ranks_first36_by_pick_skill_only():
    df = pd.DataFrame(
        [
            {
                "season": 2024,
                "pick": 1,
                "position": "QB",
                "pfr_player_name": "Caleb Williams",
            },
            {
                "season": 2024,
                "pick": 2,
                "position": "OT",
                "pfr_player_name": "Joe Alt",
            },
            {
                "season": 2024,
                "pick": 10,
                "position": "QB",
                "pfr_player_name": "J.J. McCarthy",
            },
            {
                "season": 2023,
                "pick": 1,
                "position": "QB",
                "pfr_player_name": "Bryce Young",
            },
        ]
    )

    ranks = nfl_skill_ranks_from_outcomes(df, 2024)

    assert ranks["caleb williams"] == 1
    assert ranks["jj mccarthy"] == 2
    assert "bryce young" not in ranks


def test_qb_promotions_matched_unmatched_and_nonqb_ignored():
    boards = [
        {
            "draft_class": 2024,
            "picks": [
                {"ff_slot": 1, "player_name": "Caleb Williams", "position": "QB"},
                {"ff_slot": 5, "player_name": "J.J. McCarthy", "position": "QB"},
                {"ff_slot": 2, "player_name": "Marvin Harrison Jr.", "position": "WR"},
                {"ff_slot": 9, "player_name": "Unknown Qb", "position": "QB"},
            ],
        }
    ]
    rank_maps = {2024: {"caleb williams": 1, "jj mccarthy": 2}}

    promos, matched, unmatched = qb_promotions(boards, rank_maps)

    assert sorted(promos) == [-3.0, 0.0]
    assert matched == 2
    assert unmatched == 1


def test_qb_promotions_supports_seed_qbs_shape():
    boards = [
        {
            "draft_class": 2022,
            "qbs": [
                {"slot": 3, "player_name": "Kenny Pickett"},
                {"slot": 14, "player_name": "Desmond Ridder"},
            ],
        }
    ]
    rank_maps = {2022: {"kenny pickett": 1, "desmond ridder": 2}}

    promos, matched, unmatched = qb_promotions(boards, rank_maps)

    assert sorted(promos) == [-12.0, -2.0]
    assert matched == 2
    assert unmatched == 0


def test_main_writes_artifact_with_monkeypatched_fetch(tmp_path, monkeypatch):
    monkeypatch.setattr(
        cal,
        "_fetch_league_rookie_drafts",
        lambda league_id: [
            {
                "draft_class": 2026,
                "picks": [
                    {
                        "ff_slot": 1,
                        "player_name": "Fernando Mendoza",
                        "position": "QB",
                    }
                ],
            }
        ],
    )
    out = tmp_path / "cal.json"

    k = cal.main(out_path=out)
    art = json.loads(out.read_text())

    assert art["recommended_k"] == k
    assert "sf_qb_calibration_thin_sample" in art["caveats"]
    assert art["n_qbs_matched"] >= 1
    assert isinstance(k, int)
    assert 0 <= k <= 3
    # Per-draft provenance (spec §4): audit trail per contributing draft.
    assert isinstance(art["per_draft"], list) and art["per_draft"]
    entry = art["per_draft"][0]
    assert {"draft_class", "source", "n_qbs_matched", "n_qbs_unmatched", "promotions"} <= set(entry)
    # Aggregate matched == sum of per-draft matched (consistency).
    assert art["n_qbs_matched"] == sum(e["n_qbs_matched"] for e in art["per_draft"])
