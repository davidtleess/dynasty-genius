# Dynasty Genius Agent Sync

Doctrine version: 1.0.0
Last updated: 2026-05-11

## Active Phase

Stage 1 infrastructure PRs open (#14, #15). After both merge, Stage 2 QB college feature pipeline begins.

## Current Sprint Objective

Land PRs #14 and #15, then implement QB Engine A college features (CFBD Tier 3).

- PR #13 (`hygiene/pydantic-compat`): MERGED → main `16e3567`.
- PR #14 (`hygiene/pydantic-v2-upgrade`): OPEN — CI GREEN. Merge immediately. Removes all v1/v2 shims, pins pydantic>=2.0,<3.0, removes cfbd package.
- PR #15 (`hygiene/nflreadpy-migration`): OPEN — needs one fix before merge (see below), then retarget onto main after #14 merges.
- Engine A v2 PP remediation: committed on `engine-a/v2-enrichment-pipeline` (not yet PRed to main).

## PR #15 Required Fix (Before Merge)

Scope confirmed by David: keep SOURCE_REGISTRY key `"nfl_data_py"` unchanged, do not rename provenance labels.

One file needs a change on branch `hygiene/nflreadpy-migration`:
- `scripts/ingest_2026_draft.py` line 35: change `"source": "nflreadpy_verified_nfl_draft"` back to `"source": "nfl_data_py_verified_nfl_draft"`

Everything else in PR #15 is correct:
- Import swap (`import nflreadpy as nfl`) ✓
- API call replacements (load_draft_picks, load_player_stats) ✓
- Test renamed to `test_nflreadpy_2026_results` ✓ (reflects implementation, not registry key)
- SOURCE_REGISTRY key left as `"nfl_data_py"` ✓

Sequence: fix provenance string → commit → retarget PR #15 onto main (after #14 merges) → CI → merge.

## Latest Activity

- Claude Code (2026-05-11, Session 6): Opened PR #14 (Pydantic v2 upgrade, Codex `7896e7c`, CI green). Opened PR #15 (nflreadpy migration, Gemini). Identified PR #15 provenance string issue (`ingest_2026_draft.py:35`). Restored AGENT_SYNC after stale Codex overwrite. Confirmed CI uses Python 3.11 (nflreadpy works; local 3.9 venv is broken/mismatched). Wrote Stage 0 Gemini prompts for QB strategy investigation.
- Claude Code (2026-05-11, Session 5): PR #13 merged (16e3567). Opened adapter test gate stubs (4 files). Merged PR via gh CLI. Wrote Stage 1 delegation prompts.
- Claude Code (2026-05-11, Session 4): PR #13 Pydantic compat — 84/0. Wrote QB strategy reconciliation. Delivered source map (connected vs. planned sources).

## Open Blockers

1. **PR #14 — merge now** (CI green, no issues).
2. **PR #15 — fix provenance string first**, then merge after #14 lands.
3. **Local venv mismatch** — `.venv/bin/pip` points to Python 3.14, `.venv/bin/python` is 3.9. nflreadpy requires 3.10+. To run tests locally, rebuild venv: `python3.11 -m venv .venv && pip install -r requirements.txt`. Not blocking CI.
4. **SOURCE_REGISTRY rename decision** — David confirmed: keep `"nfl_data_py"` as registry key. No rename needed.
5. **QB feature pipeline (Stage 2)** — blocked on PRs #14/#15. CFBD Tier 3 spec finalized. David has Tier 3 Patreon. cfbd Python SDK is NO-GO (still pins pydantic<2). Use httpx.
6. **PP below 80% gate** — Path B holds. Do not promote PP without explicit instruction.
7. **PR C** — human-reviewed only, not agent-delegatable.

## Next Recommended Work (in order)

1. Merge PR #14 (immediate — CI already green).
2. Fix PR #15 provenance string → retarget → CI → merge.
3. Stage 2: QB college feature pipeline.
   - Claude writes TDD gate tests first (failing).
   - Codex or Gemini implements CFBD adapter expansion.
   - Backtest gate validates lift before any QB feature becomes model_input.
4. Stage 4 (later): nflverse EPA/CPOE for professional QB tracking (Engine B).

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

- `main`: at `16e3567` — 84 pass, 0 fail.
- `hygiene/pydantic-v2-upgrade`: PR #14 open, CI green — merge immediately.
- `hygiene/nflreadpy-migration`: PR #15 open — fix provenance string first.
- `engine-a/v2-enrichment-pipeline`: adapter test stubs + PP remediation committed, not yet PRed to main.
- Main worktree: `/Users/davidleess/dynasty-genius` (main).
- Engine A worktree: `/Users/davidleess/dynasty-genius-product` (engine-a/v2-enrichment-pipeline).
