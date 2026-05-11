# Dynasty Genius Agent Sync

Doctrine version: 1.0.0
Last updated: 2026-05-11

## Active Phase

PR #13 merged. Main is clean (84 pass, 0 fail). David researching QB strategy. Phase 2 replan pending QB decision.

## Current Sprint Objective

Stabilize `main` CI before resuming Engine A v2 Phase 2.

- PR #11 (Data Foundation + Identity): MERGED → main `423979e`.
- PR #12 (Rookie Board v1): MERGED → main `7f6f590`.
- PR C (Governance Reconciliation): deferred, human-reviewed only.
- Engine A v2 PP remediation: committed `4afb1c7` on `engine-a/v2-enrichment-pipeline`.

## Latest Activity

- Claude Code (2026-05-11, Session 5): PR #13 merged (`16e3567`). Gemini confirmed CI green + review clean. `cfbd` package identified as unused but pinning pydantic<2 — follow-up upgrade PR queued. Adapter test gate audit: all 4 files missing. CFBD QB data confirmed available (passing/rushing stats). AGENT_SYNC updated.
- Claude Code (2026-05-11, Session 4): `hygiene/pydantic-compat` — added `model_dump` shim to `DynastyValuation` (pops `mode=`), `ProspectRequest` (defensive), guarded `computed_field` import in `Player`. 84 pass, 0 fail. PR #13 open.
- Claude Code (2026-05-11, Session 3): Fixed PR #11 CI failure (`PlayerValueObject.model_dump` recursion on Pydantic v2). Pushed `fbedfca`. CI passed. PR #11 and PR #12 subsequently merged.
- Claude Code (2026-05-11, Session 2): PP remediation complete — removed imputation (258 fabricated rows), fixed `year_stats` typo, renamed `yprr` → `yptt` internally, added name normalization. Gate rewritten as clean-artifact promotion tripwire. Coverage: target_share 69.6%, breakout_age WR/TE 72.8%. Path B holds. 40 targeted tests pass.

## Open Blockers

1. **`cfbd` package removal** — `cfbd` PyPI package is not imported anywhere but pins `pydantic<2`. Removing it from `requirements.txt` enables Pydantic v2 natively and makes all shims unnecessary. Separate hygiene PR needed (`hygiene/pydantic-v2-upgrade`).
2. **4 missing adapter test gates** — `test_ras_adapter.py`, `test_manual_export_adapter.py`, `test_market_overlay.py`, `test_market_leakage_gate.py` all missing. SOURCE_REGISTRY stubs unvalidated. Phase 2 work.
3. **QB feature gap** — `POSITION_FEATURE_MATRIX["QB"] = []`. 126 QB rows scored on pick/round/age only. David researching strategy. CFBD has passing/rushing data (ATT, PCT, YDS, YPA, rushing) — Passing Yards Share and Passing TD Share are calculable. Hold implementation until David approves feature design.
4. **PP below 80% gate** — target_share 69.6%, breakout_age WR/TE 72.8%. Path B holds. Do not promote PP without explicit instruction.
5. **PR C** — governance reconciliation is human-reviewed only, not agent-delegatable.

## Next Recommended Work

1. **`hygiene/pydantic-v2-upgrade`** — remove `cfbd` from `requirements.txt`, upgrade to Pydantic v2, remove shims. Clean, targeted, no scope creep.
2. **QB strategy decision** — David to approve feature design (CFBD passing/rushing stats). Then Phase 2 replan with QB track.
3. **Phase 2 replan** — after QB decision: Engine A v2 tasks 5–8, adapter test gates (4 missing), context/risk layer design.

## Branch / Worktree Notes

- `main`: current at `16e3567` — 84 pass, 0 fail.
- `hygiene/pydantic-compat`: merged to main as `16e3567`.
- `engine-a/v2-enrichment-pipeline`: PP remediation committed, not merged to main yet.
- `cleanup/pr-a-data-foundation`: merged to main.
- `cleanup/pr-b-rookie-board`: merged to main.
- `engine-a/historical-enrichment` (PR #10): closed without merge.
- `codex/governance-seal`: superseded.
- Main worktree: `/Users/davidleess/dynasty-genius` (up to date at `7f6f590`).
- Engine A worktree: `/Users/davidleess/dynasty-genius-product` (on `engine-a/v2-enrichment-pipeline`).
- PR A worktree: `/private/tmp/dg-pr-a` (cleanup/pr-a-data-foundation, merged).
