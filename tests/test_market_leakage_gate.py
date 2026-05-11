"""Market leakage gate tests.

Enforces that market-derived values (KTC, ADP, FantasyCalc, consensus) never
reach Engine A or Engine B training features by any path.

Real enforcement (runs against enriched CSV):
- Enriched training CSV has no prohibited market columns.
- LEAKAGE_REGEX catches common market-derived column name patterns.

Registry enforcement:
- KTC is market_overlay only, ktc_value/ktc_rank are prohibited.
- No market source is model_input.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

import pytest

from src.dynasty_genius.models.engine_a_contract import LEAKAGE_REGEX, PROHIBITED_COLUMNS
from src.dynasty_genius.sources.source_registry import SOURCE_REGISTRY

ROOT = Path(__file__).resolve().parents[1]
ENRICHED_CSV = ROOT / "app" / "data" / "training" / "prospects_with_outcomes_v2.csv"

MARKET_SOURCES = {"fantasycalc", "dynasty_data_lab", "dynasty_nerds", "ktc"}


# ── Registry enforcement ──────────────────────────────────────────────────────

def test_ktc_is_market_overlay_not_model_input():
    ktc = SOURCE_REGISTRY["ktc"]
    assert "market_overlay" in ktc.roles
    assert "model_input" not in ktc.roles
    assert "training_label" not in ktc.roles


def test_ktc_fields_are_prohibited():
    assert "ktc_value" in PROHIBITED_COLUMNS
    assert "ktc_rank" in PROHIBITED_COLUMNS


def test_no_market_source_is_model_input():
    for name in MARKET_SOURCES:
        src = SOURCE_REGISTRY[name]
        assert "model_input" not in src.roles, (
            f"Market source '{name}' must not be model_input. "
            "Market values are price discovery — never ground truth features."
        )


# ── Regex gate enforcement ────────────────────────────────────────────────────

def test_leakage_regex_catches_ktc_prefix():
    assert re.search(LEAKAGE_REGEX, "ktc_value")
    assert re.search(LEAKAGE_REGEX, "ktc_rank")


def test_leakage_regex_catches_adp_columns():
    assert re.search(LEAKAGE_REGEX, "adp_sleeper")
    assert re.search(LEAKAGE_REGEX, "adp_fantasycalc")


def test_leakage_regex_catches_market_prefix():
    assert re.search(LEAKAGE_REGEX, "market_value")
    assert re.search(LEAKAGE_REGEX, "market_rank")


def test_leakage_regex_catches_consensus_prefix():
    assert re.search(LEAKAGE_REGEX, "expert_rank")
    assert re.search(LEAKAGE_REGEX, "consensus_adp")


def test_leakage_regex_does_not_block_clean_columns():
    clean = ["dominator_rating", "receiving_yards_share", "target_share",
             "pick", "round", "age", "source_dominator_rating"]
    for col in clean:
        assert not re.search(LEAKAGE_REGEX, col), (
            f"Leakage regex incorrectly flagged clean column: '{col}'"
        )


# ── Enriched CSV enforcement ──────────────────────────────────────────────────

@pytest.mark.skipif(not ENRICHED_CSV.exists(), reason="Enriched CSV not yet generated")
def test_enriched_csv_has_no_prohibited_columns():
    with open(ENRICHED_CSV) as f:
        cols = set(next(csv.reader(f)))
    violations = cols & PROHIBITED_COLUMNS
    assert not violations, (
        f"Enriched CSV contains prohibited market columns: {violations}. "
        "These must be removed before any model training."
    )


@pytest.mark.skipif(not ENRICHED_CSV.exists(), reason="Enriched CSV not yet generated")
def test_enriched_csv_has_no_leakage_regex_columns():
    with open(ENRICHED_CSV) as f:
        cols = list(next(csv.reader(f)))
    flagged = [c for c in cols if re.search(LEAKAGE_REGEX, c)]
    assert not flagged, (
        f"Enriched CSV contains columns matching leakage regex: {flagged}"
    )
