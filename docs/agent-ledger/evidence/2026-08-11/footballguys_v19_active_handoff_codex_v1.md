# Footballguys Phase A — active v19 handoff checkpoint

**Authority:** David: “work freely with claude until this is production grade.” Direct
RED/GREEN/review iteration is open. Do not infer push, provider contact, first capture, scheduler,
or Phase B/C/D authority.

**Current state:** Codex authored RED v19 and delivered it to Claude. Delivery was positively
verified in Claude's transcript; Claude replied: “RED v19 received. Verifying pins and reproducing
the census before I touch anything.” Claude is the implementing lane and was working on GREEN at
the time of this checkpoint.

**RED v19:** `tests/contract/test_footballguys_phase_a_red.py`  
SHA `ad6712a79a5c975b951423abfd2456680e6d4d8794e51344c810e4a4239ad046`  
6,306 lines / 241,867 bytes  
Strict baseline: **563 collected = 46 failed + 517 passed, exit 1**. All 505 inherited v18 tests
pass; v19 slice = 46 prospective failures + 12 positive migration anchors.

**Pre-edit GREEN:** `src/dynasty_genius/sources/footballguys_intake.py`  
SHA `cf3338e3918c169aa535a7c8cbf46c144abb6b93d1043e8be40d810be59754eb`.

**V19 contracts:** exact acquisitions v1/v2/v3 and attempts v1/v2 grammars/inventories; exact
NULL-safe marker identity; non-mutating DELETE-mode acquisition prevalidation before WAL writes;
unconditional full post-migration validation; legacy-acquisition/current-attempt hidden-CHECK
orphan-event control; current-acquisition/legacy-attempt positive migration; preserve
`sqlite_sequence=41` so next allocation is 42.

**Evidence:**
- RED record: `footballguys_phase_a_red_v19_codex_v1.md`, SHA
  `dea81d55be41c79bbf30c949c5dd630a1f32ea40f5978a66f7b7bc458dfa002a`.
- GREEN v18 review: `footballguys_phase_a_green_v18_review_codex_v1.md`, SHA
  `f0b269254ea473cf9ab7a9f794e1fa54ae60331ae09e753571fe728e1ba35997`.
- Full RED wire: `footballguys_phase_a_red_v19_codex_wire_v1.md`, SHA
  `e8417d8d1f5b5a3de4a0c02b5115dd345f46ae8e4631eaec2c993e21b9ab1d16`.

**Next action:** wait for Claude's repaired GREEN card; verify GREEN/RED pins are stable; run the
strict RED, tracked full suite, Ruff, compile, real-store byte-copy probe, and fresh adversarial
migration review. If defects remain, author the smallest prospective next RED and continue. If
clear, finish READY_FOR_GATE; do not commit or push under the autonomy hard gate.

**Unrelated dirty tree:** preserve all pre-existing user/other-lane changes. HEAD was `87362f1`;
that commit contains only a 60-line ledger claim despite its GREEN-repaired subject. The record/tree
mismatch remains for later reconciliation. H2 QB rushing remains **UNDER TEST** with no result.
