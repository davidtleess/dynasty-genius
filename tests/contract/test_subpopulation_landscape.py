from importlib import import_module


def test_subpopulation_landscape_exposes_pre_registered_constants():
    module = import_module("src.dynasty_genius.eval.subpopulation_landscape")

    assert module.NEUTRAL_BAND == 0.05
    assert module.DISAGREEMENT_MIN_SLOTS == 12
    assert module.EARLY_CAREER_MAX_EXP == 2
    assert module.SPEARMAN_MIN_N == 30
    assert module.COVERAGE_GATE == 0.95
    assert module.FDR_Q == 0.10
    assert module.AGING_THRESHOLDS == {
        "RB": 25,
        "WR": 27,
        "TE": 29,
        "QB": 32,
    }
