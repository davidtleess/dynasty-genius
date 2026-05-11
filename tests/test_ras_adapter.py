"""RAS adapter governance tests.

Enforces:
- RAS is context_signal only — never a model input.
- Allowed fields are limited to risk-flag columns, not production metrics.
- RAS failure behavior is skip_enrichment (never blocks pipeline).
- Provenance required for every emitted field.
"""
from __future__ import annotations

import pytest

from src.dynasty_genius.sources.source_registry import SOURCE_REGISTRY
from src.dynasty_genius.adapters.ras_adapter import fetch_ras_context

RAS_ALLOWED_FIELDS = {"low_ras_risk_flag", "missing_athletic_profile", "source_ras_score"}


def test_ras_is_context_signal_not_model_input():
    ras = SOURCE_REGISTRY["ras"]
    assert "context_signal" in ras.roles
    assert "model_input" not in ras.roles, (
        "RAS must not be a model input. High RAS has no validated positive lift — "
        "only low_ras_risk_flag (downside risk) is governed for use."
    )


def test_ras_allowed_fields_are_risk_flags_only():
    ras = SOURCE_REGISTRY["ras"]
    assert set(ras.allowed_fields) == RAS_ALLOWED_FIELDS, (
        f"RAS allowed_fields must be exactly {RAS_ALLOWED_FIELDS}. "
        f"Got: {set(ras.allowed_fields)}. "
        "Production metric fields must not be added without a validated backtest."
    )


def test_ras_allowed_fields_do_not_include_raw_score():
    """Raw RAS score is not an allowed field — only the derived risk flags."""
    ras = SOURCE_REGISTRY["ras"]
    assert "ras_score" not in ras.allowed_fields
    assert "ras" not in ras.allowed_fields


def test_ras_failure_behavior_is_skip_enrichment():
    """RAS unavailability must never block the enrichment pipeline."""
    ras = SOURCE_REGISTRY["ras"]
    assert ras.failure_behavior == "skip_enrichment", (
        f"RAS failure_behavior must be 'skip_enrichment', got '{ras.failure_behavior}'. "
        "A missing RAS record is a caveat (missing_athletic_profile=True), not an error."
    )


def test_ras_provenance_required():
    ras = SOURCE_REGISTRY["ras"]
    assert ras.provenance_required, (
        "RAS fields must carry provenance. source_ras_score must accompany any RAS output."
    )


def test_ras_logic_enforcement():
    """Test that low RAS triggers flag and high RAS does not."""
    # Low RAS player
    low_ras = fetch_ras_context("Malachi Corley")
    assert low_ras["low_ras_risk_flag"] is True
    assert low_ras["missing_athletic_profile"] is False
    
    # High RAS player
    high_ras = fetch_ras_context("Caleb Williams")
    assert high_ras["low_ras_risk_flag"] is False
    assert high_ras["missing_athletic_profile"] is False
    
    # Missing player
    missing = fetch_ras_context("Nobody")
    assert missing["low_ras_risk_flag"] is False
    assert missing["missing_athletic_profile"] is True
    
    # Null score player
    null_score = fetch_ras_context("Unknown Player")
    assert null_score["low_ras_risk_flag"] is False
    assert null_score["missing_athletic_profile"] is True


def test_ras_emits_only_governed_fields():
    res = fetch_ras_context("Caleb Williams")
    assert set(res.keys()) == RAS_ALLOWED_FIELDS
    assert "ras_score" not in res
