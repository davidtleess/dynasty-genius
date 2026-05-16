"""Source-ID override registry validation for Phase 13.1."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ALLOWED_ASSERTION_FIELDS = {
    "sleeper_id",
    "gsis_id",
    "pff_id",
    "pfr_id",
    "cfbref_id",
    "espn_id",
    "yahoo_id",
    "sportradar_id",
    "fantasypros_id",
    "rotowire_id",
    "fantasy_data_id",
}

ALLOWED_CONFIDENCE = {"LOW", "MEDIUM", "HIGH"}
ALLOWED_REVIEW_STATUS = {"PENDING", "APPROVED", "REJECTED", "SUPERSEDED"}


class OverrideRegistryValidationError(ValueError):
    """Raised when the override registry is not auditable or safe."""


def _require_mapping(value: Any, *, path: str) -> dict:
    if not isinstance(value, dict):
        raise OverrideRegistryValidationError(f"{path} must be an object")
    return value


def _require_non_empty(value: Any, *, path: str) -> None:
    if value is None or value == "":
        raise OverrideRegistryValidationError(f"{path} is required")


def validate_override_registry(registry: dict) -> None:
    """Validate a Phase 13 source-ID override registry.

    The registry is intentionally strict: every override needs a canonical
    player_id, at least one source-ID assertion, evidence, and auditable
    metadata. Market IDs are not valid identity assertions.
    """
    _require_mapping(registry, path="registry")
    overrides = registry.get("overrides")
    if not isinstance(overrides, list):
        raise OverrideRegistryValidationError("overrides must be a list")

    for idx, override in enumerate(overrides):
        path = f"overrides[{idx}]"
        override = _require_mapping(override, path=path)
        _require_non_empty(override.get("canonical_player_id"), path=f"{path}.canonical_player_id")

        assertions = _require_mapping(override.get("assertions"), path=f"{path}.assertions")
        if not assertions:
            raise OverrideRegistryValidationError(f"{path} requires at least one source ID assertion")
        for field, value in assertions.items():
            if field not in ALLOWED_ASSERTION_FIELDS:
                raise OverrideRegistryValidationError(f"{path}.assertions has unknown source ID: {field}")
            _require_non_empty(value, path=f"{path}.assertions.{field}")

        evidence = _require_mapping(override.get("evidence"), path=f"{path}.evidence")
        _require_non_empty(evidence.get("source_row"), path=f"{path}.evidence.source_row")

        metadata = _require_mapping(override.get("metadata"), path=f"{path}.metadata")
        for field in ("author", "timestamp", "reason"):
            _require_non_empty(metadata.get(field), path=f"{path}.metadata.{field}")
        confidence = metadata.get("confidence")
        if confidence not in ALLOWED_CONFIDENCE:
            raise OverrideRegistryValidationError(
                f"{path}.metadata.confidence must be one of {sorted(ALLOWED_CONFIDENCE)}"
            )
        review_status = metadata.get("review_status")
        if review_status not in ALLOWED_REVIEW_STATUS:
            raise OverrideRegistryValidationError(
                f"{path}.metadata.review_status must be one of {sorted(ALLOWED_REVIEW_STATUS)}"
            )


def load_override_registry(path: Path | str) -> dict:
    """Load and validate a source-ID override registry JSON file."""
    registry = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_override_registry(registry)
    return registry
