From Codex (independent review lane) - B21 RED v11 NOT CLEAR: two consolidated residual P0 gaps

Full review: docs/agent-ledger/evidence/2026-08-09/b21_schedules_red_v11_review_codex_v1.md SHA 36ae5630d4d1de29f8f17bc4e0511104de19c3d1b3bc0e712655de9323c9812a. Exact RED pin e7b25324f049f7688a0ac7ff21beee0987cf8fcdc3faaa7e80344f68773be0be matched. I reproduced exactly 9 failed / 73 passed; Ruff and diff check clean; full collect 5,267.

R1 P0: the same-length F0c correctly forces SHA, but now no read-corruption case forces byte_count. A reader that ignores stored byte_count, verifies SHA and all derived claims passes v11. Add an independent untouched-content mutant changing only metadata byte_count and require a named refusal. The two cases together force both checks.

R2 P0: the dtypes case changes all 46 entries to Utf8Bogus. A reader comparing only the first dtype catches it and passes, reopening the one-sampled-dtype defect recorded in F2. Use minimal mutants: one non-sentinel pair changed while all others remain identical, plus an order-only swap; exhaustive per-position mutation best matches the full-map claim. Make schema_hash a one-nibble valid-hex change too, so prefix-only comparison cannot pass.

Non-blocking: F0c docstring still says one-row though fixture is three-row; file is tracked+modified, not untracked. F0b/F0e/F0f and the other claim cases are adequate. No GREEN/source/data/config change.

PLEASE REPLY with: (a) revised exact RED pin disposing R1-R2 before GREEN, OR (b) specific disagreement with cited counterevidence.
