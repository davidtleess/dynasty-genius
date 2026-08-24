# DG-022 session-close handoff

State: implementation complete; autonomy run `BLOCKED` only at real-surface QA and the DG-031
integration sequence. Nothing from DG-022 is committed, pushed, merged, released, or written to
shared data. DG-031 was committed/pushed separately at `9a38dc7`; `main` remains `552733c`.

## Product result preserved

- Historical frozen-prediction membership is a separate typed player-detail lane.
- Tank Dell resolves to `not_in_frozen_prediction_cohort` with basis
  `non_model_route_at_freeze` at the declared 2026-08-05 capture.
- Live read-only coverage measured 221 included of 274 current rostered skill players; 53 were not
  included.
- Universe identity, capture joinability, and scorer eligibility are unchanged.

## Frozen verification receipts

- Resolver/API contracts: 26 passed.
- Independent backend/capture/scorer gate: 85 passed.
- Focused frontend: 16 passed.
- Full frontend: 72 files / 296 tests passed.
- Ruff, typecheck, banned-language, production build, OpenAPI regeneration idempotence, and
  `git diff --check`: passed.
- Independent technical review: no P0/P1 correctness finding.
- Independent visual review: no P0 code/composition defect found, but no visual verdict because
  desktop, mobile, mid-scroll, and axe artifacts do not exist.

## Exact resume order

1. Land committed/pushed DG-031 (`9a38dc7`) through its owner and `dg-land.sh`.
2. Confirm `main` advanced from `552733c`.
3. Rebase DG-022 under a commit-authorized lane; resolve the four overlapping generated paths by
   regenerating from the rebased source contract, never by hand-merging generated output:
   `frontend/openapi.json`, `frontend/src/lib/api/index.ts`,
   `frontend/src/lib/api/types.gen.ts`, and `frontend/src/lib/api/zod.gen.ts`.
4. Rerun the frozen verification matrix.
5. Produce desktop, mobile, mid-scroll, and axe evidence on the real Tank Dell surface, then obtain
   one fresh post-rebase technical/visual verdict.
6. Only after all gates pass, use the mandatory exact-path landing workflow for DG-022.

## Source of record

- Ticket ledger: `docs/agent-ledger/2026-08-19.md`
- Implementation plan: `docs/superpowers/plans/2026-08-19-dg-022-identity-cohort-truth.md`
- Run record: this directory
- Worktree / branch: `/Users/davidleess/dg-wt/DG-022` / `ticket/DG-022`
