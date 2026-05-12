# Dynasty Genius Agent Sync

Doctrine version: 1.0.0
Last updated: 2026-05-11

## Active Phase

QB professional context layer and display annotations complete (PRs #18–#20 merged). Phase 5 / Engine B planning drafted — awaiting David's decisions on outcome variable, horizon, and validation gates before any training code begins.

## Current Sprint Objective

Phase 5 planning. No model code, no training, no feature contract changes until Q1–Q6 in the Phase 5 plan are approved.

- PR #18 (`infra/adapter-test-gates`): MERGED. 4 adapter gates (RAS, manual export, FantasyCalc, leakage).
- PR #19 (`stage4/qb-professional-context`): MERGED. EPA/CPOE/DAKOTA context layer, QB identity bridge, roster qb_context_cards.
- PR #20 (`feature/qb-context-annotations`): MERGED. Display-only bust flags (TD/INT <0.7), mobility signal (APY >3,700), P2S/college caveats.

## Latest Activity

- Claude Code (2026-05-11, Session 9): Merged PRs #20. Created Phase 5 / Engine B planning doc (`docs/superpowers/plans/2026-05-11-phase5-engine-b-plan.md`). Updated AGENT_SYNC.
- Codex (2026-05-11): PR #20 — QB display-only context annotations. Bust flags, mobility signals, explicit caveats for missing college context and P2S. Annotation fields kept out of ALLOWED_ENRICHMENT_COLUMNS and POSITION_FEATURE_MATRIX.
- Claude Code (2026-05-11, Session 9): Stage 4 complete. PR #19 merged (EPA/CPOE/DAKOTA context layer). PR #18 merged (4 adapter gates). 184 pass, 11 skip, 0 fail on full suite.
- Claude Code (2026-05-11, Session 8): Stage 2 QB pipeline shipped (PR #17). Backtest FAIL 0/3 — QB stays context-only.

## Open Blockers

1. **Phase 5 decisions pending** — Q1–Q6 in `docs/superpowers/plans/2026-05-11-phase5-engine-b-plan.md` need David's approval before any Engine B work begins. Key decisions: outcome variable (1y/2y/3y PPG), aging curve representation, QB archetype split, validation gates.
2. **PP below 80% gate** — target_share 69.6%, breakout_age WR/TE 72.8%. Path B holds. Do not promote PP without explicit instruction.
3. **PR C** — governance reconciliation is human-reviewed only, not agent-delegatable.

## Next Recommended Work (in order)

1. **David approves Phase 5 Q1–Q6** — decisions recorded as locked doc; no code until locked.
2. **Engine B dataset assembly (Task 5.1)** — player-season rows with T+1 outcome, only after Q1 approved.
3. **Fitted aging curves (Task 5.2)** — piecewise linear by position, only after Q3 approved.

## QB Strategy (approved 2026-05-11)

- Draft capital: 70% weight R1/R2, 50% R3, 30% R4-7
- College features: CFBD Tier 3 via httpx — registered in contract, NOT promoted (backtest FAIL 0/3)
- Professional context: EPA/dropback, CPOE, DAKOTA — context_signal only, not model inputs
- Display annotations: bust flag TD/INT <0.7, mobility signal APY >3,700, P2S caveats
- Bifurcated aging curve: pocket passer cliff 33, dual-threat cliff 29 (display warnings only)
- Konami Code (rushing): R²=0.5674 — stickiest QB stat
- cfbd Python SDK: NO-GO. Use httpx only.

## Branch / Worktree Notes

- `main`: at `162f033` — all PRs #18–#20 merged; 184 pass, 11 skip, 0 fail.
- `docs/phase5-engine-b-plan`: active Claude branch, docs-only Phase 5 plan.
- All feature branches from Stage 2–4: merged and deleted.
- Main worktree: `/Users/davidleess/dynasty-genius` (main).
- Product worktree: `/Users/davidleess/dynasty-genius-product` (on `docs/phase5-engine-b-plan`).
