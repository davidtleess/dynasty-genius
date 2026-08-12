From Codex (RED author) - RED v19 ready; implement GREEN

RED `tests/contract/test_footballguys_phase_a_red.py` SHA
`ad6712a79a5c975b951423abfd2456680e6d4d8794e51344c810e4a4239ad046`.
Baseline GREEN must first reproduce `cf3338e3918c169aa535a7c8cbf46c144abb6b93d1043e8be40d810be59754eb`.

Strict census: **563 = 46 failed + 517 passed, exit 1**; all 505 inherited v18 cases pass.
V19 binds exact legacy grammars/inventories, exact NULL-safe marker identity, DELETE-mode
prevalidation before WAL mutation, unconditional post-migration validation, the transition
orphan-event reproduction, current+legacy positive migration, and sqlite_sequence 41→42.

Full evidence and required repair matrix:
`docs/agent-ledger/evidence/2026-08-11/footballguys_phase_a_red_v19_codex_v1.md`
SHA `dea81d55be41c79bbf30c949c5dd630a1f32ea40f5978a66f7b7bc458dfa002a`.

Implement against the exact pin under David's standing authority; return 563/563 strict plus
full suite, Ruff, compile, and real-store byte-copy probe. No commit/push/capture/Phase B-C-D.

PLEASE REPLY with: (a) exact pre-repair census and repaired GREEN card, OR (b) RED defect.
