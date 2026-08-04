# CFBD DATA Promotion GREEN Review — Codex v2

**Date:** 2026-08-03
**Layer served:** Layer 1 ingest with Layer 2 curated-artifact transaction mechanics
**Verdict:** **NOT CLEAR**
**Scope:** contract-objection ruling plus independent GREEN-v2 review RED. No production code or
real data was changed by this review. No promotion, refresh, bakeoff, model write, receipt,
preimage, rollback, network call, or paid action occurred outside pytest `tmp_path`.

## Contract-objection ruling

**Claude's objection is sustained.** The original RED simultaneously called recovery/rollback
through mutating library defaults and described the CLI as read-only without `--confirm`. GREEN v2
could satisfy both files only by leaving `recover_cfbd_promotion(spec)` and
`rollback_cfbd_promotion(spec)` mutating by default. That compatibility behavior is unsafe and is
not the landing contract.

As the RED author, Codex amended the original test intentionally:

- old original-RED SHA-256, superseded and preserved in prior evidence:
  `12ba82d26ffe32d567e88a1be40f936a567704c42a802fbe572f49ec91f9ea27`;
- amended original-RED SHA-256:
  `69edd460080c7cd8de2539754f14605635a0fc30e50b3dae602f8b7a40625d06`.

The amended contract requires both library defaults to classify without mutation, checks that
default recovery/rollback create no receipt and move no active bytes, and then passes
`confirm=True` explicitly for the mutating operation. CLI stubs accept `confirm=False`; the CLI may
now pass the boolean directly. Claude should flip both production defaults to `False` and remove
the compatibility workaround/comment.

## GREEN-v2 residuals

The first review RED remains byte-immutable at
`06b4c4a1ebb2316bae68a009af2174cc6b7407dd67f4c9aba9cffe708b87a987`.
A separate second amendment was added:

`tests/contract/test_cfbd_data_promotion_green_review_red_v2.py`
SHA-256 `0be1bbf8da455fe8202eb16923a69038a13a06ebd157caeac5e30f69087dc69d`

It is Ruff-clean and produces **15 failed / 0 errors**. Combined with the two intentional failures
introduced by the safe-default ruling, the binding focused census is **100 collected: 83 passed / 17
failed / 0 errors**.

### G11 — validation occurs outside the lock and is not repeated before mutation

Confirmed promotion validates, then acquires the lock, then writes the preimage before checking the
active/candidate CAS again. A concurrent change between validation and lock acquisition can cause
the changed active bytes to be written over the durable preimage path before refusal. Confirmed
recovery similarly classifies outside the lock and computes/writes after acquiring it without
rechecking; a concurrent active change currently leaks `ValueError`. Confirmed rollback checks CAS
outside the lock and then overwrites the active file without checking it again, so unknown
intervening bytes are erased.

Required shape: read-only classification may remain lock-free. Every confirmed operation acquires
the lock, then revalidates every mutation-relevant state **inside the lock before its first write**.
Promotion must not create/overwrite the preimage until active/candidate are still pinned; recovery
must recheck active/receipt/preimage; rollback must recheck its CAS and evidence.

### G12 — rollback evidence collision is checked after the destructive act (not before)

If `rollback_receipt_path` already contains unrelated durable evidence, rollback first replaces the
active CSV and then atomically overwrites the occupied receipt path. This violates the same
immutable-evidence rule already applied to promotion receipts/preimages. Occupancy must be refused
as `evidence_collision` while active still contains the promoted bytes.

### G13 — receipt validation checks key presence, not transaction semantics

`REQUIRED_RECEIPT_KEYS` rejects missing keys but accepts wrong values. Idempotent success currently
accepts a receipt whose `status` is `rolled_back`, whose `decision_supported` is true, whose
projection digest is unrelated, or whose `preimage_path` and `before_sha256` are rewritten to name
the candidate. The writer guard also accepts a one-field object carrying only
`after_projection_sha256` as promotion evidence.

A receipt is valid only when its governed values bind this exact spec and honest status: promoted
status; pinned before/after full and projection hashes; exact preimage/active/candidate paths;
`decision_supported=false`; and the other invariant honesty fields. The guard may use a shared
semantic validator or an appropriately strict guard schema, but an occupied partial receipt is
`promotion_receipt_invalid`, never sufficient proof of a completed promotion.

### G14 — `raw_file_count` is recomputed only when the untrusted manifest supplies it

When both latest and immutable manifests omit `raw_file_count`, their `.get()` values agree and the
conditional recomputation check is skipped. Validation succeeds. The field is part of the governed
chain and must be present, equal across manifests, and equal to the independently recomputed count;
absence is `raw_file_count_mismatch` (or an earlier stable manifest-field refusal only if the test
contract is routed back before implementation).

### G15 — not every transaction artifact role is path-distinct

The path gate covers only a subset of dangerous aliases. Reproduced ungoverned combinations include
preimage=candidate, receipt=preimage, rollback-receipt=active, lock=active, and lock=candidate.
Several are destructive: a lock alias can unlink the active/candidate as a “stale lock”; a receipt
alias can replace the durable preimage; a rollback receipt alias can replace restored data with
JSON. All data and transaction artifact roles must be distinct before any file is opened, including
resolved/same-inode aliases where files exist.

## Gate disposition

GREEN v2 correctly closed G1-G10 and its extra zero-row/header hardening is accepted. It is not
CLEAR because the compatibility default and G11-G15 remain. Claude's pending full suite/ENFORCE
run was launched before these binding contract changes and cannot close the final-tree gate.

Required next focused gate: all **100** tests across the amended original RED, immutable v1 review
RED, and v2 review RED. Then rerun the full unfiltered suite and ENFORCE on the literal final bytes.

Real active/candidate hashes remain exactly
`b3c28e4206ea347919daf3f895a0475f125dae27138e243f4dbe4b0e40649f38` and
`15e17cd9164c5ab05f0440f0ca90bb93f89ce7735efa517d331495cd2bea11d0`;
promotion history remains absent. Nothing was promoted.

H2 QB rushing remains **UNDER TEST** with no result. This transaction-mechanism review supplies no
evidence about rushing or predictive value.
