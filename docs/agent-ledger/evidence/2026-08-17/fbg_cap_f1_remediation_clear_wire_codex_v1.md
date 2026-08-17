From Codex (independent review lane) - FBG-CAP-F1 remediation delta CLEAR [w#fbg-cap-1]

Artifact reviewed: tests/contract/test_footballguys_phase_a_red.py, 1 file +13/-13, worktree SHA-256 36de40c39eaec52a772d975ba98c61f0a4276c851d8c27da486342610a833789. Durable review: docs/agent-ledger/evidence/2026-08-17/fbg_cap_f1_remediation_review_codex_v1.md, SHA-256 993df7a64a2fd9ee908db1f6fbb4499e75527ac4920e9efea274a642c3508669.

VERDICT: CLEAR. Edit 1 makes MANIFEST_REQUIREMENTS match the committed post-capture objects.required=true truth. Edit 2 is necessary and in scope: the helper default now represents the post-capture epoch, while only the named S23 historical negative passes post_capture_epoch=False and forces objects optional; its refusal semantics remain unchanged.

Independent checks: complete diff/call-site sweep and diff-check clean; exact Phase A + anti-rot 665/665 passed; focused anti-rot 5/5 passed; scoped Ruff clean; direct helper probe proved required current-state and optional historical-state shapes. GitHub run 32073785133 independently confirms d39ff34 failed only the stale objects expectation. Store hashes remain receipts 54522831..., semantics f555aef7..., object d8af0985...; observations absent; no intake or re-fire.

Remaining gate: David commit + push, exact-head CI green, then Codex post-commit divergence audit. Horizon adjudication remains a separate David gate.

PLEASE REPLY with: (a) ACK - CLEAR recorded and the exact reviewed delta will be handed to David for commit/push, OR (b) a concrete mismatch in the reviewed pin/scope.
