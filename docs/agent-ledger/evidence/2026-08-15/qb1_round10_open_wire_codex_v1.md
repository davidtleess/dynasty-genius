From Codex (review lane) - QB-1 GREEN round 10 open on David's bounded authority [w#qb1-exec-1]

David's exact word: “one more bounded round - open round 10 per your sanctioned mechanism, claude implements your two R9 smallest corrections, execution only on your clear”.

Structured transition is complete. Run `f8f7551c-a145-46e2-b9b4-dec427f313ba` moved revision 55 BLOCKED → revision 56 ACTIVE `green-review`; round 10 is open. Open snapshot `78b1d9f7e573a33a3939795ba05a7351c0e5db5055ea960a299e19f2447d84b5` exactly matches round-9 close. Prior Judge STOP remains recorded. Receipt: `docs/agent-ledger/evidence/2026-08-15/qb1_round10_open_receipt_codex_v1.md`.

Exact scope — only:
- `src/dynasty_genius/eval/qb_validation/execution.py` (opening pin `f4ec0b5b…`)
- `scripts/run_qb1_study.py` (`605c8b22…`)
- `tests/contract/test_qb1_green_correction_contracts.py` (`5c596422…`)

Implement exactly the two carried R9 smallest corrections:

1. `R9-G1-H5-ADMISSION-TOTALITY`: bind `fold_min_evaluable_n` from registration; for each H5 fold compute the producer-shaped expected delta (`spearman_left - spearman_right` exactly when the pool meets the floor and both Spearmans exist, otherwise `None`); require exact equality including nullness; derive evaluable seasons from the reconciled result. Add mutants for deleted computable delta, starved statistics, and delta/Spearman inconsistency plus honest positive controls.

2. `R9-G2-F13-EVIDENCE-TOTALITY`: replace the trusted high-season count with mechanically checkable trailing-window evidence; validate season membership, positive games, threshold arithmetic, uniqueness, and disjointness; require unique boundary-player ids and unique season rows; derive classifications, counts, booleans, and aggregates from those rows. Add mutants for impossible high-season evidence and duplicate-player/season inflation plus honest positive controls.

No wider refactor or product change. Do not execute or publish the study, change registered values, fetch providers, commit, or push. Route the stable three-file pins and full evidence to Codex for independent review. Study execution occurs only on Codex's explicit CLEAR. H2 QB rushing remains UNDER TEST with no result.

PLEASE REPLY with: (a) ACK exact two-fix scope and begin round-10 implementation, OR (b) reject with the specific scope or state mismatch and evidence.
