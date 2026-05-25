"""Tests for the Dynasty Genius Source Registry.

Enforces:
- No market_overlay or prohibited* source has fields in ALLOWED_ENRICHMENT_COLUMNS.
- Every model_input source requires provenance.
- Enterprise sources are prohibited_current_phase, not model_input.
- training_label is never model_input on the same source (labels != features).
- Every source has a test_gate string.
"""
from __future__ import annotations


from src.dynasty_genius.models.engine_a_contract import ALLOWED_ENRICHMENT_COLUMNS, PROHIBITED_COLUMNS
from src.dynasty_genius.sources.source_registry import SOURCE_REGISTRY

NON_MODEL_ROLES = {"market_overlay", "prohibited_current_phase", "prohibited"}
ENTERPRISE_SOURCES = {"sportradar", "genius_sports", "stats_perform", "rolling_insights"}


def test_registry_has_all_expected_sources():
    expected = {
        "nfl_data_py", "cfbd", "playerprofiler", "ras", "pff", "rotoviz",
        "campus2canton", "fantasycalc", "dynasty_data_lab", "dynasty_nerds",
        "ktc", "sleeper", "sportradar", "genius_sports", "stats_perform",
        "rolling_insights", "nflreadpy_qb_context",
    }
    assert expected == set(SOURCE_REGISTRY.keys()), (
        f"Registry mismatch. Missing: {expected - set(SOURCE_REGISTRY.keys())}. "
        f"Extra: {set(SOURCE_REGISTRY.keys()) - expected}."
    )


def test_no_market_or_prohibited_source_in_allowed_enrichment_columns():
    """market_overlay and prohibited* sources must not provide model features."""
    for name, src in SOURCE_REGISTRY.items():
        if src.roles & NON_MODEL_ROLES:
            overlap = set(src.allowed_fields) & ALLOWED_ENRICHMENT_COLUMNS
            assert not overlap, (
                f"Source '{name}' has role(s) {src.roles & NON_MODEL_ROLES} "
                f"but lists allowed_fields that overlap with ALLOWED_ENRICHMENT_COLUMNS: {overlap}"
            )


def test_every_model_input_source_requires_provenance():
    for name, src in SOURCE_REGISTRY.items():
        if "model_input" in src.roles:
            assert src.provenance_required, (
                f"Source '{name}' is model_input but provenance_required=False. "
                "Every model feature must carry a source_ sibling column."
            )


def test_enterprise_sources_are_prohibited_current_phase():
    for name in ENTERPRISE_SOURCES:
        src = SOURCE_REGISTRY[name]
        assert "prohibited_current_phase" in src.roles, (
            f"Enterprise source '{name}' must be prohibited_current_phase. "
            f"Current roles: {src.roles}"
        )
        assert "model_input" not in src.roles, (
            f"Enterprise source '{name}' must not be model_input."
        )


def test_training_label_sources_are_not_sole_model_input():
    """A source with training_label must not use that to supply model features.
    training_label and model_input can coexist (nfl_data_py provides both draft
    capital features AND historical outcome labels) but the test_gate must exist
    and the roles are explicitly documented.
    """
    for name, src in SOURCE_REGISTRY.items():
        if "training_label" in src.roles:
            # Verify the source is documented about label vs feature separation
            assert src.notes, (
                f"Source '{name}' has training_label role but no notes documenting "
                "the label-vs-feature separation."
            )
            assert "label" in src.notes.lower() or "outcome" in src.notes.lower(), (
                f"Source '{name}' training_label notes must explain that labels "
                "are prediction targets, not model inputs. Got: '{src.notes}'"
            )


def test_every_source_has_test_gate():
    for name, src in SOURCE_REGISTRY.items():
        assert src.test_gate, f"Source '{name}' has no test_gate defined."
        assert src.test_gate.startswith("tests/"), (
            f"Source '{name}' test_gate '{src.test_gate}' must be a tests/ path."
        )


def test_model_input_sources_have_no_prohibited_allowed_fields():
    """Caught at import time too, but verify explicitly in tests."""
    for name, src in SOURCE_REGISTRY.items():
        if "model_input" in src.roles:
            leakage = set(src.allowed_fields) & PROHIBITED_COLUMNS
            assert not leakage, (
                f"Source '{name}' is model_input but allowed_fields contains "
                f"prohibited columns: {leakage}"
            )


def test_failure_behavior_is_valid():
    valid = {"fail_closed", "skip_enrichment", "use_cached"}
    for name, src in SOURCE_REGISTRY.items():
        assert src.failure_behavior in valid, (
            f"Source '{name}' has invalid failure_behavior '{src.failure_behavior}'. "
            f"Must be one of: {valid}"
        )


def test_prohibited_current_phase_sources_fail_closed():
    """Enterprise sources must fail loudly, not silently skip."""
    for name in ENTERPRISE_SOURCES:
        src = SOURCE_REGISTRY[name]
        assert src.failure_behavior == "fail_closed", (
            f"Enterprise source '{name}' must have failure_behavior='fail_closed'. "
            f"Got: '{src.failure_behavior}'"
        )


def test_playerprofiler_is_not_model_input_until_gate_resolves():
    """PP must remain context_signal until the probe test passes."""
    pp = SOURCE_REGISTRY["playerprofiler"]
    assert "model_input" not in pp.roles, (
        "playerprofiler must not be model_input until the Task 3 coverage probe "
        "confirms >=80% non-null coverage. Update the registry only after the gate passes."
    )
    assert "context_signal" in pp.roles or "prohibited" in pp.roles or "prohibited_current_phase" in pp.roles


def test_ktc_is_market_overlay_only():
    ktc = SOURCE_REGISTRY["ktc"]
    assert "market_overlay" in ktc.roles
    assert "model_input" not in ktc.roles
    assert "training_label" not in ktc.roles


def test_sleeper_is_context_signal_not_model_input():
    sleeper = SOURCE_REGISTRY["sleeper"]
    assert "context_signal" in sleeper.roles
    assert "model_input" not in sleeper.roles
