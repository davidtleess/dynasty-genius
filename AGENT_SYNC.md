# Dynasty Genius Agent Sync

Doctrine version: 1.0.0
Last updated: 2026-05-11

## Active Phase

Stage 2 QB college feature pipeline complete. PR #17 merged to main. QB features are context-signal only (backtest FAIL 0/3). Next: Stage 4 EPA/CPOE via nflreadpy, 4 missing adapter test gates.

## Current Sprint Objective

Engine A v2 Phase 2 complete as infrastructure. No QB features promoted to model_input.

- PR #13 (`hygiene/pydantic-compat`): MERGED → main `16e3567`.
- PR #14 (`hygiene/pydantic-v2-upgrade`): MERGED → main `f54ba11`. Pydantic>=2.0, removes cfbd package.
- PR #15 (`hygiene/nflreadpy-migration`): MERGED → main `fa995624`. Registry key and provenance string unchanged.
- PR #17 (`engine-a/v2-enrichment-pipeline`): MERGED → main. QB CFBD adapter, ID map (95.2%), TDD tests, backtest gate (FAIL 0/3). POSITION_FEATURE_MATRIX["QB"] populated but context-only.

## Latest Activity

- Claude Code (2026-05-11, Session 8): Stage 2 QB pipeline shipped. Codex: CFBD adapter (19 pass), college_team param fix (sack_rate/passing_yards_share nulls). Gemini: QB ID map 95.2% coverage. Backtest FAIL 0/3 — QB stays context-only. PR #17 merged (105 pass, 11 skip, 0 fail).
- Claude Code (2026-05-11, Session 7): Resolved PR #15 rebase conflict, fixed provenance string (ingest_2026_draft.py:35), merged PR #15 at fa995624. Stage 1 complete.
- Claude Code (2026-05-11, Session 6): Merged PR #14 (f54ba11). Identified PR #15 provenance issue. Wrote QB Stage 0 investigation prompts.
- Claude Code (2026-05-11, Session 5): PR #13 merged (16e3567). Adapter test gate stubs (4 files, 28 governance tests). QB strategy approved.

## Open Blockers

1. **4 missing adapter test gates** — `test_ras_adapter.py`, `test_manual_export_adapter.py`, `test_market_overlay.py`, `test_market_leakage_gate.py` stubs exist, implementations empty. Phase 2 work.
2. **PP below 80% gate** — target_share 69.6%, breakout_age WR/TE 72.8%. Path B holds. Do not promote PP without explicit instruction.
3. **PR C** — governance reconciliation is human-reviewed only, not agent-delegatable.

## Next Recommended Work (in order)

1. **Stage 4** — nflreadpy EPA/CPOE/DAKOTA integration for professional QB tracking. Fresh session.
2. **4 adapter test gates** — implement stubs for RAS, manual export, market overlay, market leakage. Can delegate to Codex.
3. **Categorical QB bust filters** — P2S%, TD/INT threshold (<0.7 bust), AP yards flag (>3,700) as display-only context annotations. Not model inputs.

## QB Strategy (approved 2026-05-11)

- Draft capital: 70% weight R1/R2, 50% R3, 30% R4-7
- College features: CFBD Tier 3 via httpx — completion_pct, yards_per_attempt, td_int_ratio, sack_rate, all_purpose_yards, passing_yards_share, ppa, wepa, rushing_yards, rushing_tds
- Backtest verdict: FAIL (0/3) — features registered in contract, NOT promoted to model_input
- Bifurcated aging curve: pocket passer cliff 33, dual-threat cliff 29 (display warnings only)
- Konami Code (rushing): R²=0.5674 — stickiest QB stat, valued explicitly
- cfbd Python SDK: NO-GO — pins pydantic<2. Use httpx only.

## CFBD Tier 3 QB Endpoint Spec

| Feature | Endpoint | Field |
|---|---|---|
| Completion % | /stats/player/season (passing) | PCT |
| Yards Per Attempt | /stats/player/season (passing) | YPA |
| PPA | /ppa/players/season | averagePPA.all |
| WEPA | /wepa/players/passing | wepa |
| Pass Yards Share | player YDS / team netPassingYards | derived |
| Sack Rate | team sacksAllowed / (passAttempts + sacksAllowed) | derived |
| Rushing | /stats/player/season (rushing) | CAR, YDS, TD |

## Branch / Worktree Notes

- `main`: at `e66e992` — 105 pass, 11 skip, 0 fail.
- `engine-a/v2-enrichment-pipeline`: MERGED (PR #17).
- `hygiene/pydantic-v2-upgrade`: MERGED (f54ba11).
- `hygiene/nflreadpy-migration`: MERGED (fa995624).
- Main worktree: `/Users/davidleess/dynasty-genius` (main).
- Engine A worktree: `/Users/davidleess/dynasty-genius-product` (engine-a/v2-enrichment-pipeline).
