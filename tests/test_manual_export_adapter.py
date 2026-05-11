"""Manual CSV export adapter governance tests.

Covers PFF, RotoViz, and Campus2Canton — all manual-export-only sources.

Enforces:
- All three are context_signal only — never model inputs.
- PFF grade columns are in PROHIBITED_COLUMNS and can never enter any pipeline layer.
- Campus2Canton fields are for CFBD secondary validation only, not model features.
- All three use csv_fixture cache policy (no automated ingestion this phase).
- Provenance required on any emitted field.

Adapter integration tests (CSV schema validation, fixture loading) are skipped
until CSV fixtures and adapter implementations are built in Phase 2.
"""
from __future__ import annotations

import pytest

from src.dynasty_genius.models.engine_a_contract import ALLOWED_ENRICHMENT_COLUMNS, PROHIBITED_COLUMNS
from src.dynasty_genius.sources.source_registry import SOURCE_REGISTRY

MANUAL_EXPORT_SOURCES = {"pff", "rotoviz", "campus2canton"}


def test_all_manual_export_sources_are_context_signal():
    for name in MANUAL_EXPORT_SOURCES:
        src = SOURCE_REGISTRY[name]
        assert "context_signal" in src.roles, (
            f"Source '{name}' must be context_signal. Got: {src.roles}"
        )


def test_no_manual_export_source_is_model_input():
    for name in MANUAL_EXPORT_SOURCES:
        src = SOURCE_REGISTRY[name]
        assert "model_input" not in src.roles, (
            f"Source '{name}' must not be model_input. Manual exports lack "
            "the provenance and freshness controls required for model features."
        )


def test_all_manual_export_sources_use_csv_fixture_cache():
    for name in MANUAL_EXPORT_SOURCES:
        src = SOURCE_REGISTRY[name]
        assert src.cache_policy == "csv_fixture", (
            f"Source '{name}' must use csv_fixture cache policy. "
            f"Got: '{src.cache_policy}'. Automated ingestion is not implemented this phase."
        )


def test_pff_grade_columns_are_prohibited():
    """PFF grade columns must never enter any pipeline layer under any name."""
    assert "pff_grade" in PROHIBITED_COLUMNS
    assert "pff_route_grade" in PROHIBITED_COLUMNS


def test_pff_grade_columns_are_not_in_allowed_enrichment():
    assert "pff_grade" not in ALLOWED_ENRICHMENT_COLUMNS
    assert "pff_route_grade" not in ALLOWED_ENRICHMENT_COLUMNS


def test_campus2canton_is_cfbd_validation_only():
    """Campus2Canton fields (ryptpa, dominator_pct) are secondary CFBD validation — not model inputs."""
    c2c = SOURCE_REGISTRY["campus2canton"]
    assert "model_input" not in c2c.roles
    assert "campus2canton" in c2c.notes.lower() or "validation" in c2c.notes.lower() or "ryptpa" in c2c.notes.lower(), (
        "campus2canton notes must document its role as CFBD validation only."
    )


def test_manual_export_sources_have_no_allowed_fields_in_enrichment_columns():
    """Manual export sources must not supply columns that could bleed into Engine A features."""
    for name in MANUAL_EXPORT_SOURCES:
        src = SOURCE_REGISTRY[name]
        overlap = set(src.allowed_fields) & ALLOWED_ENRICHMENT_COLUMNS
        assert not overlap, (
            f"Source '{name}' allowed_fields overlaps with ALLOWED_ENRICHMENT_COLUMNS: {overlap}. "
            "Manual export fields must not enter the model feature space."
        )


@pytest.mark.skip(reason="CSV fixture not yet provided — Phase 2 adapter implementation needed")
def test_pff_csv_fixture_loads_without_grade_columns():
    pass


@pytest.mark.skip(reason="CSV fixture not yet provided — Phase 2 adapter implementation needed")
def test_rotoviz_csv_fixture_loads_and_has_expected_columns():
    pass


@pytest.mark.skip(reason="CSV fixture not yet provided — Phase 2 adapter implementation needed")
def test_campus2canton_csv_fixture_loads_and_maps_ryptpa():
    pass
