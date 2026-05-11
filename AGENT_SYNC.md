# Dynasty Genius Agent Sync

Doctrine version: 1.0.0
Last updated: 2026-05-11

## Active Phase

Infrastructure hygiene complete (PRs #13, #14 pending merge). QB strategy research done. Stage 1 infrastructure in progress (Pydantic v2 upgrade + nflreadpy migration). Stage 2 QB feature pipeline begins after Stage 1 lands.

## Current Sprint Objective

Complete Stage 1 infrastructure upgrades, then implement QB college feature pipeline (Engine A v2 Phase 2).

- PR #13 (`hygiene/pydantic-compat`): MERGED → main `16e3567`. Pydantic v1/v2 shims. 84 pass.
- PR #14 (`hygiene/pydantic-v2-upgrade`): OPEN — removes all shims, pins pydantic>=2.0,<3.0, removes cfbd package. Codex commit `7896e7c`. 84 pass.
- PR #15 (`hygiene/nflreadpy-migration`): DELIVERED — Gemini commit `6b5eabd`. nfl_data_py → nflreadpy. 84 pass.
- Engine A v2 PP remediation: committed `4afb1c7` on `engine-a/v2-enrichment-pipeline`.

## Latest Activity

- Claude Code (2026-05-11, Session 5): Opened PR #14 (Pydantic v2 upgrade, Codex commit 7896e7c). Reviewed and verified clean. Wrote Stage 1 agent delegation prompts for Codex (PR #14) and Gemini (nflreadpy migration). Wrote Stage 0 investigation prompts for Gemini (3 parallel tracks: nflreadpy, cfbd-python, CFBD QB endpoint spec). Delivered QB strategy reconciliation against constitution.
- Claude Code (2026-05-11, Session 4): PR #13 merged (16e3567). Gemini confirmed CI green + review clean. Adapter test gate stubs (4 files, 28 governance tests). cfbd package identified as unused and pydantic<2 root cause. CFBD QB data confirmed available.
- Claude Code (2026-05-11, Session 3): Fixed PR #11 CI failure (PlayerValueObject.model_dump recursion). Pushed fbedfca. CI passed. PR #11 and PR #12 subsequently merged.

## Open Blockers

1. **PR #14 awaiting CI + merge** — Pydantic v2 upgrade. 84 pass locally. Must land before QB feature work starts.
2. **PR #15 (nflreadpy migration)** — Gemini implementing. Source registry rename decision (nfl_data_py → nflreadpy key) deferred to David.
3. **QB feature pipeline (Stage 2)** — blocked on Stage 1 (PRs #14, #15). CFBD Tier 3 endpoint spec finalized (Track C). PPA/WEPA available via httpx (no SDK). David has Tier 3 Patreon.
4. **PP below 80% gate** — target_share 69.6%, breakout_age WR/TE 72.8%. Path B holds. Do not promote PP without explicit instruction.
5. **PR C** — governance reconciliation is human-reviewed only, not agent-delegatable.

## Next Recommended Work

1. Merge PR #14 (CI + review).
2. Merge PR #15 (Gemini delivered, 84 pass). David needs to decide on "nfl_data_py" registry key rename.
3. Stage 2: QB college feature pipeline — CFBD adapter expansion, TDD gate, backtest validation.
4. Stage 4 (later): nflverse EPA/CPOE integration for professional QB tracking (Engine B territory).

## QB Strategy Summary (approved 2026-05-11)

- Draft capital: 70% weight R1/R2, 50% R3, 30% R4-7
- College features (via CFBD Tier 3 httpx): completion %, YPA, TD/INT ratio, sack rate, all-purpose yards, passing yards share, PPA, WEPA
- Bifurcated aging curve: pocket passer cliff 33, dual-threat cliff 29 (display warnings only — not model law)
- Konami Code (rushing) valued explicitly — rushing is stickiest QB stat (R²=0.5674)
- cfbd Python SDK is NO-GO (still pins pydantic<2); keep httpx

## Branch / Worktree Notes

- `main`: current at `16e3567` — 84 pass, 0 fail.
- `hygiene/pydantic-v2-upgrade`: Codex `7896e7c` — PR #14 open.
- `hygiene/nflreadpy-migration`: Gemini in progress — PR #15 pending.
- `engine-a/v2-enrichment-pipeline`: PP remediation committed, adapter test stubs added. Not yet merged to main.
- Main worktree: `/Users/davidleess/dynasty-genius` (main, at 16e3567).
- Engine A worktree: `/Users/davidleess/dynasty-genius-product` (engine-a/v2-enrichment-pipeline).
