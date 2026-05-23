"""Contract tests for Phase 16 college feature additions to Engine A.

Guards that ryptpa and yprr_college are correctly admitted as enrichment-only
WR candidates, that their source/provenance fields are allowed, that market
data remains prohibited, and that active-player route fields are not
accidentally admitted as college features.
"""
from src.dynasty_genius.models.engine_a_contract import (
    CFBD_MODEL_INPUT_COLUMNS,
    ALLOWED_ENRICHMENT_COLUMNS,
    POSITION_FEATURE_MATRIX,
    PROHIBITED_COLUMNS,
)


# ── New college feature columns admitted ─────────────────────────────────────

def test_ryptpa_in_allowed_columns():
    assert "ryptpa" in CFBD_MODEL_INPUT_COLUMNS


def test_yprr_college_in_allowed_columns():
    assert "yprr_college" in CFBD_MODEL_INPUT_COLUMNS


def test_source_ryptpa_in_allowed_columns():
    assert "source_ryptpa" in CFBD_MODEL_INPUT_COLUMNS


def test_source_yprr_college_in_allowed_columns():
    assert "source_yprr_college" in CFBD_MODEL_INPUT_COLUMNS


def test_new_columns_propagate_to_allowed_enrichment():
    # ALLOWED_ENRICHMENT_COLUMNS is derived from CFBD_MODEL_INPUT_COLUMNS
    assert "ryptpa" in ALLOWED_ENRICHMENT_COLUMNS
    assert "yprr_college" in ALLOWED_ENRICHMENT_COLUMNS


# ── Position feature matrix ───────────────────────────────────────────────────

def test_wr_feature_matrix_lists_ryptpa():
    assert "ryptpa" in POSITION_FEATURE_MATRIX["WR"]


def test_wr_feature_matrix_lists_yprr_college():
    assert "yprr_college" in POSITION_FEATURE_MATRIX["WR"]


def test_rb_feature_matrix_lists_ryptpa():
    assert "ryptpa" in POSITION_FEATURE_MATRIX["RB"]


def test_te_feature_matrix_unchanged():
    # TE does not receive the new college signals in Phase 16
    assert "ryptpa" not in POSITION_FEATURE_MATRIX["TE"]
    assert "yprr_college" not in POSITION_FEATURE_MATRIX["TE"]


# ── Market data still prohibited ──────────────────────────────────────────────

def test_market_columns_remain_prohibited():
    for col in ("ktc_value", "ktc_rank", "adp", "fantasycalc_value"):
        assert col in PROHIBITED_COLUMNS, f"Market column no longer prohibited: {col}"


# ── Active-player and NFL route fields not accidentally admitted ───────────────

def test_nfl_yprr_still_prohibited():
    # nfl_yprr is the active-player metric — must never be an Engine A college feature
    assert "nfl_yprr" in PROHIBITED_COLUMNS


def test_bare_yprr_not_in_college_feature_columns():
    # Plain 'yprr' (mislabeled PlayerProfiler field) must not enter as college feature
    assert "yprr" not in CFBD_MODEL_INPUT_COLUMNS


def test_pff_grade_columns_still_prohibited():
    assert "pff_grade" in PROHIBITED_COLUMNS
    assert "pff_route_grade" in PROHIBITED_COLUMNS
