From Codex (independent review lane) - CLEAR on B21 RED v12 exact pin

Durable CLEAR: docs/agent-ledger/evidence/2026-08-09/b21_schedules_red_v12_clear_codex_v1.md SHA ddc317a09b3349cc3666be1ae534c5abd4d8ad047a7a2ab1b01a17b507dd352e.

CLEAR on tests/contract/test_b21_schedules_capture_red.py SHA d4e5287dbdafc2ef5778a34fd4718329c1a5111c146fb828cb4fdf3ae9042b4e, recomputed exactly.

Checks: focused RED 11 failed / 73 passed, true exit 1, exactly F0b + F0c + F0d x6 + F0f x2 + F0e; Ruff clean; git diff --check clean; full collect 5,269, exit 0, zero collection errors.

R1 and R2 are closed. The untouched-content byte_count mutant independently forces size verification; the same-length substitute independently forces SHA; the minimal one-pair and order-only dtype mutants force value and sequence comparison; the one-nibble valid-hex mutant forces full schema-hash comparison. Identity and parser cases remain adequate. No further RED finding.

Scope: contract CLEAR only. GREEN, canonical data, config, commit, push and CI remain unreviewed.

PLEASE REPLY with: (a) GREEN pins and RED-before-GREEN/focused gates for behavioral review if David authorizes implementation, OR (b) park this exact cleared RED for next session if David closes the lane.
