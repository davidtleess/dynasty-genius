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


def test_load_byo_draft_ids_dedupes_order_preserving(tmp_path, monkeypatch):
    p = tmp_path / "byo.json"
    p.write_text(json.dumps({"draft_ids": ["A", "B", "A", "C", "B"]}))
    monkeypatch.setattr(cal, "_BYO_PATH", p)

    ids, dupes = cal._load_byo_draft_ids()

    assert ids == ["A", "B", "C"]
    assert dupes == ["A", "B"]


def test_load_byo_draft_ids_missing_file_is_noop(tmp_path, monkeypatch):
    monkeypatch.setattr(cal, "_BYO_PATH", tmp_path / "does_not_exist.json")

    assert cal._load_byo_draft_ids() == ([], [])


def test_load_byo_draft_ids_empty_list(tmp_path, monkeypatch):
    p = tmp_path / "byo.json"
    p.write_text(json.dumps({"draft_ids": []}))
    monkeypatch.setattr(cal, "_BYO_PATH", p)

    assert cal._load_byo_draft_ids() == ([], [])


def test_is_superflex_exact_token():
    assert cal.is_superflex({"roster_positions": ["QB", "RB", "SUPER_FLEX", "BN"]}) is True
    assert cal.is_superflex({"roster_positions": ["QB", "RB", "WR", "BN"]}) is False
    assert cal.is_superflex({}) is False


def test_is_twelve_team_int_coerced():
    assert cal.is_twelve_team({"total_rosters": 12}) is True
    assert cal.is_twelve_team({"total_rosters": "12"}) is True
    assert cal.is_twelve_team({"total_rosters": 10}) is False
    assert cal.is_twelve_team({}) is False
    assert cal.is_twelve_team({"total_rosters": "oops"}) is False


def test_league_format_metadata_reads_scoring_settings():
    league = {
        "roster_positions": ["QB", "SUPER_FLEX"],
        "total_rosters": 12,
        "scoring_settings": {"rec": 1.0, "bonus_rec_te": 0.5},
    }

    meta = cal.league_format_metadata(league)

    assert meta == {
        "superflex": True,
        "total_rosters": 12,
        "ppr": 1.0,
        "te_premium": True,
    }

    meta2 = cal.league_format_metadata({"roster_positions": [], "total_rosters": 10})

    assert meta2["ppr"] is None
    assert meta2["te_premium"] is False


def _sf12_league():
    return {
        "roster_positions": ["QB", "SUPER_FLEX"],
        "total_rosters": 12,
        "scoring_settings": {"rec": 1.0},
    }


def test_gate_byo_draft_accepts_sf_12team_complete_rookie():
    draft = {"status": "complete", "settings": {"rounds": 4}, "type": "snake"}

    accepted, reason, fmt = cal.gate_byo_draft(draft, _sf12_league())

    assert accepted is True
    assert reason is None
    assert fmt["superflex"] is True


def test_gate_byo_draft_reject_reasons():
    sf12 = _sf12_league()

    accepted, reason, _ = cal.gate_byo_draft(
        {"status": "drafting", "settings": {"rounds": 4}},
        sf12,
    )
    assert (accepted, reason) == (False, "not_rookie")

    accepted, reason, _ = cal.gate_byo_draft(
        {"status": "complete", "settings": {"rounds": "x"}},
        sf12,
    )
    assert (accepted, reason) == (False, "malformed_draft_settings")

    accepted, reason, _ = cal.gate_byo_draft(
        {"status": "complete", "settings": {"rounds": 15}},
        sf12,
    )
    assert (accepted, reason) == (False, "not_rookie")

    accepted, reason, _ = cal.gate_byo_draft(
        {"status": "complete", "settings": {"rounds": 4}, "type": "auction"},
        sf12,
    )
    assert (accepted, reason) == (False, "unsupported_draft_type")

    accepted, reason, _ = cal.gate_byo_draft(
        {"status": "complete", "settings": {"rounds": 4}},
        {"roster_positions": ["QB"], "total_rosters": 12},
    )
    assert (accepted, reason) == (False, "not_superflex")

    accepted, reason, _ = cal.gate_byo_draft(
        {"status": "complete", "settings": {"rounds": 4}},
        {"roster_positions": ["SUPER_FLEX"], "total_rosters": 10},
    )
    assert (accepted, reason) == (False, "not_12_team")


def _pick(no, first="Caleb", last="Williams", pos="QB"):
    return {
        "pick_no": no,
        "metadata": {
            "first_name": first,
            "last_name": last,
            "position": pos,
        },
    }


def test_build_byo_board_caps_at_36_and_sorts():
    board, reason = cal._build_byo_board(
        "draft-1",
        {"season": "2026"},
        _sf12_league(),
        [
            _pick(40, "Late", "Quarterback", "QB"),
            _pick(2, "Tetairoa", "McMillan", "WR"),
            _pick(1, "Caleb", "Williams", "QB"),
        ],
    )

    assert reason is None
    assert board["draft_class"] == 2026
    assert board["draft_id"] == "draft-1"
    assert board["source"] == "sleeper_draft:draft-1"
    assert board["format_meta"]["superflex"] is True
    assert board["n_picks_raw"] == 3
    assert board["n_picks_used"] == 2
    assert board["n_picks_excluded_after_36"] == 1
    assert [p["ff_slot"] for p in board["picks"]] == [1, 2]
    assert [p["player_name"] for p in board["picks"]] == [
        "Caleb Williams",
        "Tetairoa McMillan",
    ]


def test_build_byo_board_invalid_draft_class():
    board, reason = cal._build_byo_board("draft-1", {"season": None}, {}, [_pick(1)])

    assert board is None
    assert reason == "invalid_draft_class"


def test_build_byo_board_malformed_picks_whole_draft_reject():
    malformed = {"metadata": {"first_name": "No", "last_name": "Pick", "position": "QB"}}

    board, reason = cal._build_byo_board(
        "draft-1",
        {"season": "2026"},
        _sf12_league(),
        [_pick(1), malformed],
    )

    assert board is None
    assert reason == "malformed_picks"


def test_build_byo_board_draft_class_falls_back_to_league_season():
    board, reason = cal._build_byo_board(
        "draft-1",
        {"season": None},
        {**_sf12_league(), "season": "2025"},
        [_pick(1)],
    )

    assert reason is None
    assert board["draft_class"] == 2025


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
