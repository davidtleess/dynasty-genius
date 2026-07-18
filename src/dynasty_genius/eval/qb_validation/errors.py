"""QB-1 validation-study failure type: every refusal carries a NAMED reason.

Fail-closed law (spec §D5/F32): a failure is never silent and never partial —
callers surface ``reason`` into the run artifact's ``failure_reason`` field.
Spec of record: docs/superpowers/specs/2026-07-16-qb-validation-program-design.md
(v8, SHA 8fa244c1…, byte-frozen).
"""
from __future__ import annotations


class QBValidationFailure(Exception):
    """A named, fail-closed refusal from the QB-1 validation study.

    ``reason`` is the machine-readable failure code the spec enumerates
    (e.g. ``preregistration_missing``, ``output_path_violation``,
    ``manifest_column_missing``); ``detail`` is the human-readable evidence.
    """

    def __init__(self, reason: str, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason}: {detail}" if detail else reason)
