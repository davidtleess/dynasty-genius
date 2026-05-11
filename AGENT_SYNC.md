# Dynasty Genius Agent Sync

Doctrine version: 1.0.0
Last updated: 2026-05-11

## Active Phase

Stage 1 infrastructure complete (PRs #13, #14, #15 all merged to main). Stage 2 QB college feature pipeline is next.

## Current Sprint Objective

Implement QB college feature pipeline (Engine A v2 Phase 2) using CFBD Tier 3 via httpx.

- PR #13 (`hygiene/pydantic-compat`): MERGED → main `16e3567`. Pydantic v1/v2 shims.
- PR #14 (`hygiene/pydantic-v2-upgrade`): MERGED → main `f54ba11`. Removes shims, pins pydantic>=2.0,<3.0, removes cfbd package.
- PR #15 (`hygiene/nflreadpy-migration`): MERGED → main `fa995624`. nfl_data_py → nflreadpy. Registry key `"nfl_data_py"` and provenance string `"nfl_data_py_verified_nfl_draft"` unchanged.
- Engine A v2 PP remediation: committed on `engine-a/v2-enrichment-pipeline` (not yet PRed to main).

## Latest Activity

- Claude Code (2026-05-11, Session 7): Resolved rebase conflict in PR #15 ledger file, fixed provenance string (`ingest_2026_draft.py:35`), force-pushed, CI green (84 pass), merged PR #15 at `fa995624`. Stage 1 complete.
- Claude Code (2026-05-11, Session 6): Merged PR #14 (`f54ba11`). Identified PR #15 provenance string issue. Restored AGENT_SYNC after stale Codex overwrite. Wrote QB Stage 0 investigation prompts.
- Claude Code (2026-05-11, Session 5): PR #13 merged (`16e3567`). Adapter test gate stubs (4 files, 28 governance tests). QB strategy approved.
- Claude Code (2026-05-11, Session 4): PR #13 Pydantic compat — 84/0. QB strategy reconciliation. Source map delivered.

## Open Blockers

1. **Local venv mismatch** — `.venv/bin/python` is 3.9, pip is 3.14. Rebuild: `python3.11 -m venv .venv && pip install -r requirements.txt`. Not blocking CI.
2. **QB feature pipeline (Stage 2)** — unblocked. CFBD Tier 3 spec finalized. David has Tier 3 Patreon. cfbd Python SDK is NO-GO (still pins pydantic<2). Use httpx.
3. **PP below 80% gate** — Path B holds. Do not promote PP without explicit instruction.
4. **PR C** — governance reconciliation is human-reviewed only, not agent-delegatable.

## Next Recommended Work (in order)

1. Stage 2: QB college feature pipeline.
   - Claude writes TDD gate tests first (failing) for CFBD QB adapter.
   - Codex or Gemini implements adapter expansion.
   - Backtest gate validates lift before any QB feature becomes model_input.
2. Stage 4 (later): nflverse EPA/CPOE for professional QB tracking (Engine B).

## QB Strategy (approved 2026-05-11)

- Draft capital: 70% weight R1/R2, 50% R3, 30% R4-7
- College features (CFBD Tier 3 via httpx): completion %, YPA, TD/INT ratio, sack rate, all-purpose yards, passing yards share, passing TD share, PPA, WEPA
- Bifurcated aging curve: pocket passer cliff 33, dual-threat cliff 29 (display warnings only — not model law per constitution)
- Konami Code (rushing) valued explicitly — stickiest QB stat (R²=0.5674)
- cfbd Python SDK: NO-GO — still pins pydantic<2. Keep httpx.

## CFBD Tier 3 QB Endpoint Spec (finalized, ready for Stage 2)

| Feature | Endpoint | Field |
|---|---|---|
| Completion % | /stats/player/season (passing) | PCT |
| Yards Per Attempt | /stats/player/season (passing) | YPA |
| PPA | /ppa/players/season | averagePPA.all |
| WEPA | /wepa/players/passing | wepa |
| Pass Yards Share | player YDS / team netPassingYards | derived |
| Sack Rate | team sacksOpponent / (passAttempts + sacksOpponent) | derived proxy |
| Rushing | /stats/player/season (rushing) | CAR, YDS, TD |

All-purpose yards = passing YDS + rushing YDS (derived). Garbage-time filter in WEPA is automatic.

## Branch / Worktree Notes

- `main`: at `fa995624` — 84 pass, 0 fail. All Stage 1 hygiene PRs merged.
- `hygiene/pydantic-v2-upgrade`: MERGED (f54ba11).
- `hygiene/nflreadpy-migration`: MERGED (fa995624).
- `engine-a/v2-enrichment-pipeline`: adapter test stubs + PP remediation committed, not yet PRed to main.
- Main worktree: `/Users/davidleess/dynasty-genius` (main).
- Engine A worktree: `/Users/davidleess/dynasty-genius-product` (engine-a/v2-enrichment-pipeline).
