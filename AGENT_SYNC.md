# Dynasty Genius Agent Sync

Doctrine version: 1.0.0
Last updated: 2026-05-11

## Active Phase

Stage 4 QB professional context layer merged via PR #19. QB college features remain context-signal only (final corrected backtest FAIL 0/3). EPA/CPOE/DAKOTA/dropbacks/attempts are roster-facing `context_signal` only, not Engine B training inputs.

## Current Sprint Objective

Engine A v2 Phase 2 infrastructure complete. Stage 4 adds roster-facing QB professional telemetry context only. No QB pro fields promoted to Engine A or Engine B model inputs.

- PR #13 (`hygiene/pydantic-compat`): MERGED → main `16e3567`.
- PR #14 (`hygiene/pydantic-v2-upgrade`): MERGED → main `f54ba11`. Pydantic>=2.0, removes cfbd package.
- PR #15 (`hygiene/nflreadpy-migration`): MERGED → main `fa995624`. Registry key and provenance string unchanged.
- PR #17 (`engine-a/v2-enrichment-pipeline`): MERGED → main. QB CFBD adapter, ID map (95.2%), TDD tests, backtest gate (FAIL 0/3). POSITION_FEATURE_MATRIX["QB"] populated but context-only.

## Latest Activity

- Codex (2026-05-11): Reviewed and merged PR #19. Confirmed `QB_CONTEXT_COLUMNS` is not in `ALLOWED_ENRICHMENT_COLUMNS` or `POSITION_FEATURE_MATRIX`; `nflreadpy_qb_context` is `context_signal` only. Fixed CI-only optional CFBD partial artifact gate. CI passed and PR #19 merged at `da5c0f7`. Local full suite with Python 3.14: 184 passed, 11 skipped.
- Stage 4 PR #19: MERGED. Adds `fetch_qb_nfl_stats()` for EPA/dropback, CPOE, DAKOTA, dropbacks/attempts; QB GSIS identity bridge; and roster `qb_context_cards`. Context-only by registry and contract.
- Adapter gates PR #18: Implemented and merged separately before Stage 4. Four adapter gate stubs closed.
- Claude Code (2026-05-11, Session 8): Stage 2 QB pipeline shipped. Codex: CFBD adapter (19 pass), college_team param fix (sack_rate/passing_yards_share nulls). Gemini: QB ID map 95.2% coverage. Backtest FAIL 0/3 — QB stays context-only. PR #17 merged (105 pass, 11 skip, 0 fail).
- Claude Code (2026-05-11, Session 7): Resolved PR #15 rebase conflict, fixed provenance string (ingest_2026_draft.py:35), merged PR #15 at fa995624. Stage 1 complete.
- Claude Code (2026-05-11, Session 6): Merged PR #14 (f54ba11). Identified PR #15 provenance issue. Wrote QB Stage 0 investigation prompts.
- Claude Code (2026-05-11, Session 5): PR #13 merged (16e3567). Adapter test gate stubs (4 files, 28 governance tests). QB strategy approved.

## Open Blockers

1. **PP below 80% gate** — target_share 69.6%, breakout_age WR/TE 72.8%. Path B holds. Do not promote PP without explicit instruction.
2. **PR C** — governance reconciliation is human-reviewed only, not agent-delegatable.
3. **Local Python mismatch** — `.venv/bin/python` may point to Python 3.9, but `nflreadpy` 0.1.5 requires Python >=3.10. Use CI Python 3.11+ or `.venv/bin/python3.14` for full-suite/live nflreadpy work.

## Next Recommended Work (in order)

1. **Categorical QB bust filters** — P2S%, TD/INT threshold (<0.7 bust), AP yards flag (>3,700) as display-only context annotations. Not model inputs.
2. **Phase 5 planning** — fitted aging-curve/outcome-variable decisions before any Engine B training.
3. **Clean branch/worktree state** — remove stale Stage 4 local branch after confirming no untracked debug artifacts are needed.

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

- `main`: at `da5c0f7` — PR #19 merged; CI passed.
- `engine-a/v2-enrichment-pipeline`: MERGED (PR #17).
- `hygiene/pydantic-v2-upgrade`: MERGED (f54ba11).
- `hygiene/nflreadpy-migration`: MERGED (fa995624).
- Main worktree: `/Users/davidleess/dynasty-genius` (main).
- Product worktree: `/Users/davidleess/dynasty-genius-product` still on local `stage4/qb-professional-context`; remote PR branch deleted after merge.
