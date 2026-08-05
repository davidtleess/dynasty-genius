# Contracts closeout cross-lane audit — Codex v13

Date: 2026-08-05  
Layer: 1 ingestion  
Audited lane: Claude Code  
Audited repository state: `4909d52e89af022f004b0bfeb88847c2ac63c0c2`  
Disposition: **Claude closeout requires a state-doc re-flush; contracts remain parked and NOT CLEAR**

## Mechanical facts independently reproduced

- `HEAD` and `origin/main` both resolve to `4909d52e89af022f004b0bfeb88847c2ac63c0c2`;
  behind 0, ahead 0, clean working tree.
- Latest main CI run reported by `verify_closeout.py`: `31040947372`, completed successfully on
  `4909d52`.
- `tests/contract/test_contracts_ingestion_red.py`: **59 passed**.
- `verify_closeout.py` returned exit 0. Its three ENFORCE rows passed. The independent run's only
  background match was the focused pytest launched concurrently by this Codex audit; it completed
  before postflight. Claude's reported no-background state is not contradicted.
- Commit `4909d52` changes exactly the contracts adapter, its 59-test contract, and two fixtures.
  It truthfully labels the code NOT CLEAR and names V12-1 through V12-5.

## Post-commit divergence audit

**CLEAR-AS-PARKED:** `4909d52` faithfully preserves the contracts implementation reviewed in
Codex v12. All five blockers remain visible in the committed blobs:

1. the generic first-row missing check still preempts the indexed exact-shape check;
2. the required G1-G5 durable controls remain absent from the 59-test contract;
3. `write_raw_snapshot` still accepts malformed or contradictory axis envelopes;
4. `_assert_schema` still compares snapshot-ledger column names without verifying constraints;
5. `by_stream_snapshot` still omits `rows_not_canonically_identified`.

This closes the narrow post-commit divergence loop. It is **not** a GREEN/content CLEAR and does
not authorize contracts capture, product-store landing, scheduling, consumer use, or model use.

## Closeout defect

Claude's status cannot yet be accepted as a completed `closed — parked` flush because the durable
state documents contradict the final repo state:

- `docs/agent-ledger/2026-08-05.md` still says **“NOTHING COMMITTED”** and `HEAD=d645933` in the
  stream-5 handoff, although contracts code is now committed and pushed at `4909d52`.
- The live current board in `AGENT_SYNC.md` still says all six loaders have zero callers and that
  contracts/depth charts have no `StreamSpec`, while streams 1-4 are landed and contracts is now a
  committed-but-NOT-CLEAR fifth stream.
- Commit `4909d52` contains no ledger or `AGENT_SYNC.md` update. The mechanical durable-record gate
  checks that those files are tracked and committed, not that their statements reflect the final
  commit; its PASS therefore does not close the semantic gap.

Claude should append/merge a corrective postflight, commit the two state docs, rerun
`verify_closeout.py`, and re-report. Do not amend or rewrite `4909d52`; preserve the truthful
uncleared-code commit and correct forward.

## Parked work and next gate

- Contracts: committed on `main` at `4909d52`, pushed, CI green, zero product-store rows,
  **NOT CLEAR**. Next gate: a fresh implementing session closes V12-1 through V12-5, runs the
  durable controls and full gate, and routes a fresh GREEN.
- Stream 6 `ff_rankings`: untouched. It still requires a physically separate `market_overlay`
  destination and a negative Engine A/B consumer gate.
- Any eventual contracts landing remains one capture/export over all twelve prior streams plus
  contracts, with prior-file and NGS-consumer reconciliation. Landing requires separate David word.
