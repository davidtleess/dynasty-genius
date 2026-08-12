From Codex (independent reviewer / RED author) - Phase A RED v19 ready for GREEN

RED:
`tests/contract/test_footballguys_phase_a_red.py`
SHA-256 `ad6712a79a5c975b951423abfd2456680e6d4d8794e51344c810e4a4239ad046`
6,306 lines / 241,867 bytes.

BASELINE GREEN remains byte-exact at
`cf3338e3918c169aa535a7c8cbf46c144abb6b93d1043e8be40d810be59754eb`.

STRICT CENSUS: **563 collected = 46 failed + 517 passed, exit 1**. All 505 inherited v18 cases
pass. V19 slice = 58 cases: 46 prospective failures + 12 exact migration anchors. Ruff clean,
strict compile clean, diff check clean, no skip/xfail.

BOUND FAMILIES:
1. Exact positive matrix: acquisitions v1/v2/v3 × attempts v1/v2 × both active stores migrates to
   one current postcondition and reopens cleanly.
2. Exact legacy grammars: hidden CHECK/wrong order across acquisition versions; hidden CHECK across
   attempt versions.
3. Closed legacy object inventory: surplus trigger/table cannot be erased by rebuild.
4. Exact marker-only identity: NULL offering, wrong reserved row id, and wrong reserved kind are
   populated/unreconcilable.
5. DELETE-mode acquisition prevalidation is main/WAL byte-frozen before journal-mode writes.
6. Legacy acquisitions + current malformed attempts refuses before staging/event allocation.
7. Current acquisitions + exact legacy attempts still migrates (prevents premature postcondition).
8. `sqlite_sequence=41` survives attempts v1/v2 migration; next allocation is 42.

Evidence:
`docs/agent-ledger/evidence/2026-08-11/footballguys_phase_a_red_v19_codex_v1.md`
SHA-256 `dea81d55be41c79bbf30c949c5dd630a1f32ea40f5978a66f7b7bc458dfa002a`.

Per David's standing word, implement GREEN v19 against this exact pin, then return the new GREEN
SHA plus strict 563/563 exit 0, tracked full-suite census, Ruff, strict compile, and a real-store
byte-copy migration probe. Do not commit/push/capture/contact/schedule/open Phase B/C/D.

PLEASE REPLY with: (a) exact RED reproduction before repair and repaired GREEN evidence, OR (b)
the precise RED defect or ambiguity. Confirm the GREEN file's pre-edit hash first.
