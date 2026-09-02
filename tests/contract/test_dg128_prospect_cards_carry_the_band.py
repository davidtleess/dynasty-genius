"""DG-128 (2026-09-01): the 80 rookie cards carry the band the veterans carry.

The prospect cards are a tracked artifact regenerated through ``assemble_pvo`` by
``scripts/refresh_prospect_cards.py``; nothing in the daily chain rebuilds them, so a
field the assembler gains only reaches the served universe once the artifact is
regenerated. David's ruling is "the band ships with the number" and "every player";
four of the rookies are on his own roster.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import refresh_prospect_cards as regen
from src.dynasty_genius.models.dvs_band import (
    DVS_SIGMA_A,
    DVS_SIGMA_A_V3,
    ENGINE_A_SIGMA_RUN,
    ENGINE_A_V3_HEAD,
    ENGINE_A_V3_SIGMA_RUN,
)

ROOT = Path(__file__).resolve().parents[2]
CARDS_JSON = ROOT / "resources" / "prospect_cards.json"
CARDS_JS = ROOT / "resources" / "prospect_cards.js"


def _cards() -> list[dict]:
    return json.loads(CARDS_JSON.read_text())


def test_every_scored_card_carries_a_band_around_its_number() -> None:
    missing = []
    for card in _cards():
        score = card.get("dynasty_value_score")
        if score is None:
            continue
        low, high = card.get("dvs_band_low"), card.get("dvs_band_high")
        if low is None or high is None or not (0.0 <= low <= score <= high <= 100.0):
            missing.append((card["full_name"], score, low, high))
    assert not missing, f"scored cards without a band around the number: {missing}"


def test_each_card_s_band_is_the_error_of_the_head_that_scored_it() -> None:
    # Two heads score rookies: the v2 ridge (every position) and the v3 TE head. The band
    # around a number is that head's own published error, clamped to the scale.
    wrong = []
    for card in _cards():
        score = card.get("dynasty_value_score")
        if score is None:
            continue
        sigma = (
            DVS_SIGMA_A_V3 if card["engine_used"] == ENGINE_A_V3_HEAD else DVS_SIGMA_A
        )[card["position"]]
        expected = (
            round(max(0.0, score - sigma), 1),
            round(min(100.0, score + sigma), 1),
        )
        if (card["dvs_band_low"], card["dvs_band_high"]) != expected:
            wrong.append(
                (
                    card["full_name"],
                    card["engine_used"],
                    expected,
                    (card["dvs_band_low"], card["dvs_band_high"]),
                )
            )
    assert not wrong, f"cards whose band is not their scoring head's error: {wrong}"
    assert any(c.get("engine_used") == ENGINE_A_V3_HEAD for c in _cards()), (
        "no v3-scored card in the artifact"
    )


def test_every_scored_card_records_the_runs_its_band_was_pinned_to() -> None:
    for card in _cards():
        if card.get("dynasty_value_score") is None:
            continue
        versions = card["source_versions"]
        assert versions["dvs_band_sigma_run_a"] == ENGINE_A_SIGMA_RUN, card["full_name"]
        assert versions["dvs_band_sigma_run_a_v3"] == ENGINE_A_V3_SIGMA_RUN, card[
            "full_name"
        ]


def test_the_regen_refuses_to_band_against_heads_the_tree_does_not_serve(
    monkeypatch,
) -> None:
    # Same seam the universe batch has: a re-promoted head nobody re-pinned stops the regen
    # before a single card is scored, rather than shipping 22 bands that describe a model
    # no longer serving.
    def refuse() -> None:
        raise ValueError("dvs_band_sigma_run_stale:A_v3:TE:20260915T090000Z")

    assembled: list[object] = []
    monkeypatch.setattr(regen, "assert_band_sigma_runs_match_served_models", refuse)
    monkeypatch.setattr(regen, "assemble_pvo", lambda *a, **k: assembled.append(a))
    player = {
        "dg_id": "dg-test",
        "full_name": "Test Rookie",
        "position": "TE",
        "pick": 40,
        "round": 2,
        "birth_date": "2004-01-01",
        "verification_status": "VERIFIED",
    }
    with pytest.raises(ValueError, match=r"^dvs_band_sigma_run_stale:A_v3:TE:"):
        regen._build_pvo_dicts([player], {}, {"snapshot_date": "2026-05-09"})
    assert assembled == []


def test_an_unscored_card_carries_no_band() -> None:
    unscored = [c for c in _cards() if c.get("dynasty_value_score") is None]
    assert unscored, "the artifact has no PRE_MODEL card to probe"
    for card in unscored:
        assert card.get("dvs_band_low") is None
        assert card.get("dvs_band_high") is None


def test_the_js_wrapper_serves_the_same_cards() -> None:
    payload = CARDS_JS.read_text()
    start, end = payload.index("["), payload.rindex("]") + 1
    assert json.loads(payload[start:end]) == _cards()
