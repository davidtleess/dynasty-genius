"""QB-1 study registration: one hash gates every fit (spec F2/F7/F23).

The registration document pins every pre-registered policy (folds, manifests,
estimator pipelines, comparison set with directions, inference contract, seeds,
disclosures). ``build_registration`` canonicalizes and hashes it;
``require_registration_hash`` refuses any runner invocation without the exact
matching hash (``preregistration_missing``); ``reject_registration_drift``
refuses when a pinned document no longer matches its pinned hash
(``registration_drift``). Changing a pinned policy after the pin is a protocol
violation, not a tuning knob.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from src.dynasty_genius.eval.qb_validation.errors import QBValidationFailure


def build_registration(registration: dict[str, Any]) -> dict[str, str]:
    """Canonicalize a registration document and return it with its sha256.

    Canonical form: JSON with sorted keys, compact separators, UTF-8 — so the
    hash is byte-stable across writers. Non-serializable content fails loud
    (``registration_not_serializable``) rather than being coerced.
    """
    if not isinstance(registration, dict) or not registration:
        raise QBValidationFailure(
            "registration_invalid", "registration must be a non-empty mapping"
        )
    try:
        canonical = json.dumps(
            registration, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
    except (TypeError, ValueError) as exc:
        raise QBValidationFailure("registration_not_serializable", str(exc)) from exc
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {"canonical_json": canonical, "sha256": digest}


def require_registration_hash(
    registration: dict[str, Any] | None, expected_sha256: str | None
) -> str:
    """Gate for EVERY D3/D4 runner: refuse to run without the matching hash.

    Returns the verified hash on success. Absent registration, absent expected
    hash, or a mismatch all refuse with the spec-named
    ``preregistration_missing`` failure (F7 — study-wide, not D4-only).
    """
    if registration is None or not expected_sha256:
        raise QBValidationFailure(
            "preregistration_missing",
            "runner invoked without a registration document and pinned hash",
        )
    actual = build_registration(registration)["sha256"]
    if actual != expected_sha256:
        raise QBValidationFailure(
            "preregistration_missing",
            f"registration hash mismatch: pinned {expected_sha256}, actual {actual}",
        )
    return actual


def reject_registration_drift(
    registration: dict[str, Any], pinned_sha256: str
) -> None:
    """Refuse post-pin drift: any altered pinned policy voids the run (F23).

    Distinct from ``require_registration_hash`` in intent: this is the
    re-verification a runner performs against an ALREADY-pinned document —
    a mismatch is named ``registration_drift`` so the artifact shows tampering
    rather than a missing pre-registration.
    """
    actual = build_registration(registration)["sha256"]
    if actual != pinned_sha256:
        raise QBValidationFailure(
            "registration_drift",
            f"pinned {pinned_sha256} but current document hashes to {actual}",
        )
