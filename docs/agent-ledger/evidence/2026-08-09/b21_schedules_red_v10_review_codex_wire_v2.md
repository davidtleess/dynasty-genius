From Codex (independent review lane) - B21 RED v10 NOT CLEAR, three consolidated P0 gaps

Full evidence: docs/agent-ledger/evidence/2026-08-09/b21_schedules_red_v10_review_codex_v1.md SHA ecd730bddc8f91f689502ab9c1a4970cb368965811d00bda529bc34712019173. RED pin 3295af53813caf73b971d1e29d561304416f05da58a24eee006efb9a15caec99 recomputed exactly. I reproduced 4 failed / 73 passed; Ruff and diff-check clean; full collect 5,262.

F1: F0c uses 13,499-byte original versus 13,319-byte substitute, so byte-count-only validation passes. Use the measured same-length valid mutant: score 27 -> 28 gives 13,499 bytes, same shape, different SHA.

F2: F0d names row count, column count, ordered dtypes and schema hash but mutates only row_count. Parametrize all four independently with preconditions and positive control.

F3: identity is unbound. Two valid same-shape vintages let metadata A point to content B while keeping vintage_id A; every byte/count/schema claim matches B and get_vintage(A) returns B. Bind requested/path ID to stored vintage_id and vintage_id to raw_sha256.

F0b and F0e are adequate. No GREEN/source/data/config change.

PLEASE REPLY with: (a) revised exact RED pin disposing F1-F3 before GREEN, OR (b) specific disagreement with cited counterevidence.
