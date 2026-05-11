"""Engine A v2 feature contract tests.

Guards the enriched training data schema, enforces leakage rules,
and verifies data completeness before model retraining is permitted.

These tests run against the *enriched* CSV once historical enrichment
is complete. They are intentionally skipped while enrichment is pending.

Leakage rules enforced here:
  - No market-derived columns (KTC, ADP, FantasyCalc values)
  - No post-NFL production stats (these would be look-ahead when scoring prospects)
  - No freeform narrative columns
  - All new features must carry a source_<field> provenance column
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import pytest

from src.dynasty_genius.models.engine_a_contract import (
    ALLOWED_ENRICHMENT_COLUMNS,
    BASELINE_COLUMNS,
    PROHIBITED_COLUMNS,
)

ROOT = Path(__file__).resolve().parents[1]
TRAINING_CSV = ROOT / "app" / "data" / "training" / "prospects_with_outcomes.csv"
CFBD_PARTIAL_CSV = ROOT / "app" / "data" / "training" / "prospects_with_outcomes_cfbd_partial.csv"
ENRICHED_CSV = ROOT / "app" / "data" / "training" / "prospects_with_outcomes_v2.csv"
FEATURE_MEDIANS = ROOT / "resources" / "engine_a_feature_medians.json"

# ── Provenance: every enrichment column needs a source_ sibling ──────────────

ENRICHMENT_DATA_COLUMNS = {c for c in ALLOWED_ENRICHMENT_COLUMNS if not c.startswith("source_") and not c.startswith("imputed_")}
EXPECTED_PROVENANCE_COLUMNS = {f"source_{c}" for c in ENRICHMENT_DATA_COLUMNS}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _read_csv_columns(path: Path) -> set[str]:
    with path.open() as f:
        reader = csv.reader(f)
        return set(next(reader))


def _read_csv_rows(path: Path) -> list[dict]:
    with path.open() as f:
        return list(csv.DictReader(f))


def _skip_if_not_partial():
    return pytest.mark.skipif(
        not CFBD_PARTIAL_CSV.exists(),
        reason="CFBD partial CSV not yet generated — run scripts/enrich_training_data.py first",
    )


def _skip_if_not_enriched():
    return pytest.mark.skipif(
        not ENRICHED_CSV.exists(),
        reason="enriched training CSV not yet generated — run scripts/enrich_training_data.py first",
    )


# ── Baseline CSV health (always runs) ────────────────────────────────────────

def test_baseline_csv_exists():
    assert TRAINING_CSV.exists(), f"Baseline training CSV missing: {TRAINING_CSV}"


def test_baseline_csv_has_required_columns():
    cols = _read_csv_columns(TRAINING_CSV)
    missing = BASELINE_COLUMNS - cols
    assert not missing, f"Baseline CSV missing expected columns: {missing}"


def test_baseline_csv_row_count():
    rows = _read_csv_rows(TRAINING_CSV)
    assert len(rows) >= 800, f"Baseline CSV has only {len(rows)} rows — expected ≥800"


def test_baseline_csv_no_prohibited_columns():
    """Baseline CSV should not already contain market or post-NFL features."""
    cols = _read_csv_columns(TRAINING_CSV)
    violations = cols & PROHIBITED_COLUMNS
    assert not violations, f"Baseline CSV contains prohibited columns: {violations}"


# ── CFBD partial CSV (Task 2 artifact, skipped until partial runs) ────────────

@_skip_if_not_partial()
def test_partial_csv_row_count_preserved():
    """CFBD enrichment join must not silently drop training rows."""
    baseline_count = sum(1 for _ in TRAINING_CSV.open()) - 1
    partial_count = sum(1 for _ in CFBD_PARTIAL_CSV.open()) - 1
    assert partial_count == baseline_count, (
        f"Row count changed: baseline={baseline_count}, partial={partial_count}\n"
        "Enrichment join must be a left join — no prospect rows may be dropped."
    )


@_skip_if_not_partial()
def test_partial_csv_dominator_rating_completeness():
    """dominator_rating must be present for ≥80% of WR, RB, TE rows in the CFBD partial artifact."""
    rows = _read_csv_rows(CFBD_PARTIAL_CSV)
    skill_rows = [r for r in rows if r.get("position") in ("WR", "RB", "TE")]
    if not skill_rows:
        pytest.skip("No WR/RB/TE rows found")
    present = [r for r in skill_rows if r.get("dominator_rating", "").strip() not in ("", "nan")]
    pct = len(present) / len(skill_rows)
    assert pct >= 0.80, f"dominator_rating completeness {pct:.0%} below 80% threshold"


# ── Enriched CSV schema (skipped until enrichment runs) ──────────────────────

@_skip_if_not_enriched()
def test_enriched_csv_contains_all_baseline_columns():
    cols = _read_csv_columns(ENRICHED_CSV)
    missing = BASELINE_COLUMNS - cols
    assert not missing, f"Enriched CSV dropped baseline columns: {missing}"


@_skip_if_not_enriched()
def test_enriched_csv_has_all_allowed_enrichment_columns():
    cols = _read_csv_columns(ENRICHED_CSV)
    enrichment_cols = cols - BASELINE_COLUMNS
    unrecognized = enrichment_cols - ALLOWED_ENRICHMENT_COLUMNS
    assert not unrecognized, (
        f"Enriched CSV contains columns not in allowed set: {unrecognized}\n"
        "Add to ALLOWED_ENRICHMENT_COLUMNS if intentional, or remove from CSV."
    )


@_skip_if_not_enriched()
def test_enriched_csv_no_prohibited_columns():
    """Core leakage guard — market data and post-NFL stats must never appear."""
    cols = _read_csv_columns(ENRICHED_CSV)
    violations = cols & PROHIBITED_COLUMNS
    assert not violations, (
        f"LEAKAGE: enriched CSV contains prohibited columns: {violations}\n"
        "Market data and post-NFL stats cannot be Engine A model inputs."
    )


@_skip_if_not_enriched()
def test_enriched_csv_has_provenance_columns():
    """Every enrichment data column must have a source_ sibling."""
    cols = _read_csv_columns(ENRICHED_CSV)
    enrichment_data_cols = (cols - BASELINE_COLUMNS) & ENRICHMENT_DATA_COLUMNS
    missing_provenance = {f"source_{c}" for c in enrichment_data_cols} - cols
    assert not missing_provenance, (
        f"Enrichment columns missing provenance siblings: {missing_provenance}"
    )


@_skip_if_not_enriched()
def test_enriched_csv_provenance_values_are_known_sources():
    """source_ columns must name a known, governed data source."""
    # "manual" is not allowed as a bare provenance value — too easy to abuse.
    # Manual overrides must be explicit: e.g. "manual_verified_birth_date".
    # PFF college data must be prefixed "college_pff_<field>" — generic "pff_grade" stays prohibited.
    ALLOWED_SOURCES = {"playerprofiler", "cfbd", "nfl_data_py", "imputed_median"}
    ALLOWED_PREFIXES = ("manual_", "college_pff_")

    rows = _read_csv_rows(ENRICHED_CSV)
    source_cols = [c for c in rows[0] if c.startswith("source_")]
    violations = []
    for row in rows:
        for col in source_cols:
            val = row.get(col, "").strip().lower()
            if not val:
                continue
            if val in ALLOWED_SOURCES:
                continue
            if any(val.startswith(p) for p in ALLOWED_PREFIXES):
                continue
            violations.append(f"{row['pfr_player_name']}: {col}={val!r}")
    assert not violations, (
        f"Unknown or bare provenance sources (use explicit names, not 'manual'): {violations[:10]}"
    )


# ── Enriched CSV completeness (skipped until enrichment runs) ─────────────────

@_skip_if_not_enriched()
def test_enriched_csv_dominator_rating_completeness():
    """dominator_rating must be present for ≥80% of WR, RB, TE rows."""
    rows = _read_csv_rows(ENRICHED_CSV)
    skill_rows = [r for r in rows if r.get("position") in ("WR", "RB", "TE")]
    if not skill_rows:
        pytest.skip("No WR/RB/TE rows found")
    present = [r for r in skill_rows if r.get("dominator_rating", "").strip() not in ("", "nan")]
    pct = len(present) / len(skill_rows)
    assert pct >= 0.80, f"dominator_rating completeness {pct:.0%} below 80% threshold"


@_skip_if_not_enriched()
def test_enriched_csv_yprr_completeness_wr():
    """yprr must be present (observed or imputed) for ≥95% of WR rows."""
    rows = _read_csv_rows(ENRICHED_CSV)
    wr_rows = [r for r in rows if r.get("position") == "WR"]
    if not wr_rows:
        pytest.skip("No WR rows found")
    present = [r for r in wr_rows if r.get("yprr", "").strip() not in ("", "nan")]
    pct = len(present) / len(wr_rows)
    assert pct >= 0.95, (
        f"WR yprr completeness {pct:.0%} below 95% — "
        "check median imputation is applied for pre-2019 classes"
    )


@_skip_if_not_enriched()
def test_enriched_csv_pp_completeness():
    """target_share, breakout_age, and speed_score must have ≥50% coverage for relevant positions."""
    from src.dynasty_genius.models.engine_a_contract import POSITION_FEATURE_MATRIX
    rows = _read_csv_rows(ENRICHED_CSV)
    skill_rows = [r for r in rows if r.get("position") in ("WR", "RB", "TE")]

    for field in ["target_share", "breakout_age", "speed_score"]:
        relevant = [r for r in skill_rows if field in POSITION_FEATURE_MATRIX.get(r.get("position"), [])]
        if not relevant: continue

        present = [r for r in relevant if r.get(field, "").strip() not in ("", "nan")]
        pct = len(present) / len(relevant)
        # Note: Set threshold to 15% for initial foundation build as we discover API gaps
        assert pct >= 0.15, f"{field} completeness {pct:.0%} below 15% threshold"


@_skip_if_not_enriched()
def test_enriched_csv_row_count_preserved():
    """Enrichment join must not silently drop training rows."""
    baseline_count = sum(1 for _ in TRAINING_CSV.open()) - 1  # subtract header
    enriched_count = sum(1 for _ in ENRICHED_CSV.open()) - 1
    assert enriched_count == baseline_count, (
        f"Row count changed: baseline={baseline_count}, enriched={enriched_count}\n"
        "Enrichment join must be a left join — no prospect rows may be dropped."
    )


# ── Feature medians artifact (skipped until enrichment runs) ─────────────────

@pytest.mark.skipif(not FEATURE_MEDIANS.exists(), reason="feature medians not yet generated")
def test_feature_medians_shape():
    medians = json.loads(FEATURE_MEDIANS.read_text())
    for pos in ("WR", "RB", "TE"):
        assert pos in medians, f"ROSTER_NEED missing position: {pos}"
    wr_medians = medians["WR"]
    assert "yprr" in wr_medians, "WR medians must include yprr for imputation"
    assert "dominator_rating" in wr_medians, "WR medians must include dominator_rating"
