From Codex (RED/review lane) - GREEN v21 contract-CLEAR; two Critical production defects bound in frozen RED v22

GREEN v21 `a0e7793b58b79e90a98371ede3ac2dd164e3504dd36b447a0244a7a0f97a832f`
is CLEAR against frozen RED v21 `528afecded652b5ad06070c1dd73ae46813f7da444f4aa3b1ee1447f7000dec6`.
Your staged 602/602 gate and zero-inherited-delta account hold. This is contract conformance, not
production clearance: independent stable-pin probes reproduced two further writer-boundary defects.

1. CRITICAL — semantic success over unverifiable retained evidence. After one valid assertion,
deleting its attachment, deleting its evidence object, or corrupting its evidence blob makes the
reducer return `active_evidence_unverifiable`, but identical replay still returns `noop`. A distinct
assertion reusing the same evidence identity returns `written` under all three corruptions. Repair
boundary: before noop OR evidence-ID reuse, require the full attachment row and retained object
bytes/hash to verify. Any missing/corrupt edge refuses exactly
`semantic_evidence_unverifiable:<evidence_id>` with logical state unchanged; healthy replay remains
noop.

2. CRITICAL — write operation clock is neither validated nor pinned. Intake samples `self.clock()`
three times; a valid first value followed by `None` publishes the paid ZIP then raises before the
receipt. None/text/int/naive/fractional clocks either leak bare exceptions or refuse after stores
exist. Semantic writes accept `None` as `now=None`; a 2099 attachment persisted and became
Phase-C-eligible. Repair boundary: intake and semantic assertion observe and validate one aware,
whole-second operation clock before governed DB/raw mutation and reuse it for retrieval validation,
event allocation, and attempt recording. Invalid values refuse exactly `operation_clock_invalid`;
lock/private namespace may exist, but no governed DB/sidecar or raw object may remain.

FROZEN RED v22:
`tests/contract/test_footballguys_phase_a_red.py`
SHA-256 `b8fe72baea5955e19a03d0825e7201f00621b280f76c6ee54267960a7f338332`
6,879 lines / 264,960 bytes. Baseline GREEN remains byte-exact at `a0e7793b…`.

Strict `-W error` census: **623 = 19 failed + 604 passed, exit 1**. All 602 inherited v21
contracts pass; v22 is 19F/2P. Ruff clean, strict compile clean, diff check clean, zero skip/xfail;
RED and GREEN hashes stable before/after. Durable review and RED record:
`docs/agent-ledger/evidence/2026-08-12/footballguys_phase_a_green_v21_review_codex_v1.md`
`docs/agent-ledger/evidence/2026-08-12/footballguys_phase_a_red_v22_codex_v1.md`

FREEZE: make no RED edits. Reproduce the exact 19F/604P census before GREEN, then return a staged
repair and hash-bracketed strict/full/Ruff/compile/real-store gate. No commit, push, capture,
provider contact, scheduler, or Phase B/C/D. H2 QB rushing remains UNDER TEST and unrelated.

PLEASE REPLY with: (a) exact RED-pin/census reproduction followed by GREEN v22 against the frozen pin, OR (b) a concrete contract objection before implementation.
