# CFBD DATA promotion post-action review — Codex v1

**Date:** 2026-08-03
**Lane:** independent reviewer / RED author
**Verdict:** **NOT CLEAR — G21 receipt-defined jurisdiction is fail-open**

## State ruling

**Do not roll back the promotion on this finding.** The reported live state is internally coherent:
the active bytes equal the pinned candidate, the preimage equals the pinned former active bytes,
the receipt records the authorized delta and honesty block, the live guarded writers refuse, and
rollback remains available. G21 is a defect in the uncommitted compatibility repair, not evidence
that the promoted data or durable evidence is corrupt.

Keep the data live, repair G21 before any correction commit or push, then rerun the full gate on the
literal final bytes.

## G21 — receipt-defined jurisdiction can self-exempt

The uncommitted fix asks the receipt whether it governs the target:

```python
if Path(payload.get("active_path", "")) != active_path:
    return
```

That is circular. Editing only `receipt.active_path` to a decoy path makes the guard silently return
on the real promoted active file. The artifact being validated can therefore opt itself out of
validation. Structure and honesty checks do not close this: the modified receipt remains a complete,
well-formed mapping with all four honesty booleans false.

## Binding contract

Authored:
`tests/contract/test_cfbd_data_promotion_green_review_red_v5.py`
SHA-256:
`6f142416ea81d9eb0779a6a0bb45c2b2b67190d12a815517a614d2f893d6cf81`

Binding RED census: **6 collected / 0 passed / 6 failed / 0 errors**.

The contract requires:

1. Jurisdiction comes from a trusted caller-supplied `governed_active_path`, not receipt content.
2. If `active_path` is outside that trusted jurisdiction, return before reading or validating the
   unrelated receipt. A corrupt real receipt must not block a fixture-world target.
3. Inside jurisdiction, `receipt.active_path` must match the governed active path; mismatch is
   `promotion_receipt_invalid`, never silent success.
4. The canonical promoted target still refuses with `promoted_projection_write_refused`.
5. Both destructive production callers explicitly pass trusted jurisdiction; the earlier
   incomplete-set pattern must not leave one writer on the unsafe default.

An optional `governed_active_path` parameter defaulting to `active_path` is compatible with the
existing direct contract surface; the two live callers must pass the canonical active path derived
from their trusted default promotion spec.

## Why the proposed malformed-receipt ordering is also wrong

The proposal validates receipt structure before deciding jurisdiction so a malformed real receipt
still blocks an unrelated fixture. That preserves the same cross-world coupling that caused the
four live-suite failures. Jurisdiction must be established first from trusted configuration. Only a
target inside that boundary is governed by the receipt and therefore subject to fail-closed receipt
validation.

## Checks and scope

- Read the literal post-commit uncommitted diff and both production call sites.
- Reproduced the unsafe contract as six deterministic RED failures under `tmp_path`.
- No real active, candidate, preimage, receipt, model, or data artifact was mutated by the review.
- The reported full-suite follow-up is superseded as a landing gate until G21 is green.

QB rushing remains a registered hypothesis **UNDER TEST** with no result. This data movement and
guard repair supply no evidence about it.
