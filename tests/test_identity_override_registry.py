"""Task 13.1.2 tests: source-ID override registry validation."""
from __future__ import annotations

import json

import pytest

from src.dynasty_genius.audit.identity_override_registry import (
    OverrideRegistryValidationError,
    load_override_registry,
    validate_override_registry,
)


def _valid_registry() -> dict:
    return {
        "schema_version": "1.0.0",
        "overrides": [
            {
                "canonical_player_id": "mason_taylor_te_2025",
                "assertions": {
                    "sleeper_id": "12345",
                    "gsis_id": "00-0099999",
                    "pff_id": "987654",
                },
                "evidence": {
                    "source_row": "pff_export_2025_te.csv:42",
                    "note": "Manual verification against Sleeper and PFF export.",
                },
                "metadata": {
                    "author": "David",
                    "timestamp": "2026-05-15T21:45:00Z",
                    "reason": "Resolve PFF export row after deterministic cascade miss.",
                    "confidence": "HIGH",
                    "review_status": "APPROVED",
                },
            }
        ],
    }


def test_valid_override_registry_passes_validation():
    validate_override_registry(_valid_registry())


@pytest.mark.parametrize(
    "field_path",
    [
        ("overrides", 0, "canonical_player_id"),
        ("overrides", 0, "evidence", "source_row"),
        ("overrides", 0, "metadata", "author"),
        ("overrides", 0, "metadata", "timestamp"),
        ("overrides", 0, "metadata", "reason"),
    ],
)
def test_override_registry_requires_auditable_fields(field_path):
    registry = _valid_registry()
    cursor = registry
    for key in field_path[:-1]:
        cursor = cursor[key]
    cursor.pop(field_path[-1])

    with pytest.raises(OverrideRegistryValidationError):
        validate_override_registry(registry)


def test_override_registry_requires_at_least_one_source_id_assertion():
    registry = _valid_registry()
    registry["overrides"][0]["assertions"] = {}

    with pytest.raises(OverrideRegistryValidationError, match="source ID assertion"):
        validate_override_registry(registry)


def test_override_registry_rejects_unknown_source_id_fields():
    registry = _valid_registry()
    registry["overrides"][0]["assertions"]["ktc_id"] = "market-leakage-id"

    with pytest.raises(OverrideRegistryValidationError, match="unknown source ID"):
        validate_override_registry(registry)


def test_load_override_registry_validates_file(tmp_path):
    path = tmp_path / "identity_override_registry.json"
    path.write_text(json.dumps(_valid_registry()))

    loaded = load_override_registry(path)

    assert loaded["schema_version"] == "1.0.0"
    assert loaded["overrides"][0]["canonical_player_id"] == "mason_taylor_te_2025"
