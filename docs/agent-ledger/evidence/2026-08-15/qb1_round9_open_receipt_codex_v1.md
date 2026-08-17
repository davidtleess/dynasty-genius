# TW15 QB-1 bounded green-review round 9 open receipt

Date: 2026-08-15 ET  
Executor: Codex review lane  
Run: `f8f7551c-a145-46e2-b9b4-dec427f313ba`

## Authority and boundary

David's word, verbatim:

> one more bounded round - open round 9 per your sanctioned mechanism, claude implements your three R8 smallest corrections, execution only on your clear

Authorized implementation scope:

- `src/dynasty_genius/eval/qb_validation/execution.py`
- `scripts/run_qb1_study.py`
- `tests/contract/test_qb1_green_correction_contracts.py`

The round carries exactly the three unresolved round-8 BLOCKERs. No execution,
publication, registration change, provider fetch, commit, push, or wider product
change is authorized. Study execution remains held for Codex's explicit CLEAR.
H2 QB rushing remains UNDER TEST with no result.

## Transition artifact

- Script: `docs/agent-ledger/evidence/2026-08-15/qb1_round9_open_codex_v1.mjs`
- SHA-256: `49c66578a43dc1c16a8eb6a85a46dae691089fc60239859ca17a1c3ea5d01af6`
- Mutation path: revision-guarded atomic `persistRun` only.
- Default mode: dry-run; sole mutating invocation: exactly one `--apply`.
- Failure behavior: new round-9 snapshot directory is removed if persistence
  fails; no earlier snapshots or run archives are modified.

The script failed closed against all of these preconditions:

- exact run id and schema version;
- revision 50 terminal `BLOCKED` state and exact reason;
- empty reason-code list and review failure count 4;
- exactly four failed review receipts;
- existing Judge STOP ruling and timestamp;
- exactly eight closed green-review rounds;
- exact round-8 close snapshot hash;
- exact three unresolved round-8 criterion ids;
- existing round-8 authorization repair record;
- absence of a round-9 snapshot directory;
- exact hashes of all three scoped files;
- current scoped hash equal to the round-8 close hash.

## Dry run and apply

Syntax check: `node --check .../qb1_round9_open_codex_v1.mjs` — exit 0.

Dry run loaded revision 50 and produced:

- open snapshot hash
  `205d84b2073a567cd205fde01a74984c087fca742cfbbd1902cd1f12a0058f44`;
- carried criteria `R8-G1-H5-SPECIAL-CASE`,
  `R8-G2-EVALUABLE-RECONCILIATION`, and `R8-G3-F13-TOTALITY`;
- `executionHeldPendingCodexClear: true`.

The exact pinned script was then invoked once with `--apply`. `persistRun`
returned revision **51** and result `APPLIED`.

## Post-apply proof

Machine state now reports:

- phase `green-review`;
- terminal state `ACTIVE`;
- round 9 open at `2026-08-15T13:17:45.635Z`;
- round 9 `closedAt: null`;
- authorization word embedded verbatim;
- open snapshot hash exactly equal to the round-8 close hash;
- all three round-8 findings still unresolved and carried, not pre-resolved;
- state repair `TW15-QB1-R9-OPEN-CODEX-V1` recorded.

Snapshot file pins independently reproduce:

- execution `913225f529a0c63a30b4ee6b025c3d1ac408a5d6107be15b8a65dc80d83e9f37`;
- runner `ef7a8244d5b141eaa7280f37b269531089f5eeeb6649b230b09fcbe50bde86eb`;
- contracts `513ed1bd255c9c62368bcb68f8cacfbfdc3284aa5c9df3a0c8a36affd46b9b58`.

The non-applying loop verdict reports
`ADJUDICATION_REQUIRED: PHASE_ROUND_CAP`, expected because counters remain
intact. It was not applied or re-docketed; David's direct word is the recorded
bounded exception.

## Claude routing

- Wire artifact:
  `docs/agent-ledger/evidence/2026-08-15/qb1_round9_open_wire_codex_v1.md`
- SHA-256:
  `3e7ce064e2cdd3a2e44b3d532042d858362c35961547a24f3300bec1b1961445`

Pane discovery immediately before send identified `dynasty:1.1` as Claude.
The helper returned its known `wire_body_mismatch`; capture showed Codex's own
message stranded in Claude's input, so the single permitted submit-only Enter
was used. Recapture showed the message in Claude's transcript and the composer
cleared. Submission was therefore positively verified under the Wire Rule.
