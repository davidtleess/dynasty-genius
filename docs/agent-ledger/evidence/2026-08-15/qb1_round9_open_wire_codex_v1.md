From Codex (review lane) - QB-1 GREEN round 9 OPEN; implement exactly three R8 corrections

DAVID'S WORD, recorded verbatim in the round: “one more bounded round - open round 9 per your sanctioned mechanism, claude implements your three R8 smallest corrections, execution only on your clear”.

Structured state is now ACTIVE at run f8f7551c-a145-46e2-b9b4-dec427f313ba revision 51, green-review round 9 open. The revision-guarded transition script is `docs/agent-ledger/evidence/2026-08-15/qb1_round9_open_codex_v1.mjs`, SHA-256 `49c66578a43dc1c16a8eb6a85a46dae691089fc60239859ca17a1c3ea5d01af6`. Its dry run passed at revision 50; `--apply` persisted revision 51 through `persistRun`. The round-9 open snapshot hash is `205d84b2073a567cd205fde01a74984c087fca742cfbbd1902cd1f12a0058f44`, exactly the round-8 close hash. Snapshot file pins reproduce execution `913225f5…`, runner `ef7a8244…`, contracts `513ed1bd…`.

AUTHORIZED WRITE SCOPE — exactly:
- `src/dynasty_genius/eval/qb_validation/execution.py`
- `scripts/run_qb1_study.py`
- `tests/contract/test_qb1_green_correction_contracts.py`

Carry and fix exactly these unresolved findings:
1. `finding-green-review-8-1` / `R8-G1-H5-SPECIAL-CASE`: below-floor direct exception requires all inference numerics null, `ni_met=False`, registered status, exact below-floor flag; complete evidence uses the total function; partial evidence refuses.
2. `finding-green-review-8-2` / `R8-G2-EVALUABLE-RECONCILIATION`: derive exact evaluable seasons from emitted metric content using the producer admission invariant; equality to the aggregate evaluable claim; excluded seasons are the registered complement; no key-presence counting.
3. `finding-green-review-8-3` / `R8-G3-F13-TOTALITY`: require exact equality to recomputed per-case flip booleans in both directions, then require per-fold aggregate flip counts to equal sums across boundary cases.

Baseline evidence: full review `docs/agent-ledger/evidence/2026-08-15/qb1_green_round8_review_codex_v1.md` SHA-256 `4f155f1e04fbefeb492675d76a4d9dffa49f69a38f1831cfef008bed7668d47d`; public-runner probe `docs/agent-ledger/evidence/2026-08-15/qb1_green_round8_adversarial_probe_codex_v1.py` SHA-256 `750f8213945cccf71c969ce7417ed4f7577ee5e7a709c988418a4b57a1bb254b` (4/4 invalid payloads currently publish ok). Resolve the three finding ids in round 9 only after their fixes and regression coverage are complete, then route exact pins and fresh evidence to Codex for independent review.

BOUNDARY: no wider product change, registration change, provider fetch, study execution, result publication, commit, or push. The non-applying verdict still reports the expected `PHASE_ROUND_CAP`; do not apply or re-docket it. Study execution remains held until my explicit CLEAR. H2 QB rushing remains UNDER TEST with no result.

PLEASE REPLY with: (a) ACK round-9 scope and begin the three fixes, OR (b) blocked, with the named reason and state left open.
