# Dynasty Genius — Developer Quick Reference

Read the governance files and `AGENT_SYNC.md` before using this guide. This document is a stable reference for the module layout, commands, and architecture — it does not replace governance or sprint state.

## Stack

- Backend: FastAPI / Python 3.14
- Models: scikit-learn Ridge regression (position-stratified)
- Sources: Sleeper, nflreadpy, PFF (local exports), CFBD, RAS, FantasyCalc overlay

## Architecture

Every decision surface reads from the **Player Value Object (PVO)** assembled by `src/dynasty_genius/pvo_assembler.py`. No surface invents its own scoring logic.

```
FastAPI routes          app/api/routes/
  └─ Services           app/services/
       └─ PVO Assembler src/dynasty_genius/pvo_assembler.py
            ├─ Engine A (prospects)    src/dynasty_genius/scoring/engine_a.py
            ├─ Engine B (active)       app/services/engine_b_service.py
            └─ Market Overlay          src/dynasty_genius/services/market_overlay_service.py
```

## Key Module Locations

| Path | Purpose |
|------|---------|
| `src/dynasty_genius/models/player_value_object.py` | Canonical PVO and MarketOverlay Pydantic schemas |
| `src/dynasty_genius/models/engine_b_contract.py` | All numeric constants: P90, Λ_pos, replacement DVS, blend-k, trade bands |
| `src/dynasty_genius/pvo_assembler.py` | Merges identity + features → PVO |
| `src/dynasty_genius/adapters/` | One adapter per external source |
| `src/dynasty_genius/eval/backtest_harness.py` | Walk-forward 4-fold backtest driver |
| `src/dynasty_genius/trade_lab/evaluator.py` | Trade evaluation: xVAR parity, consolidation penalty, pick valuation |
| `src/dynasty_genius/audit/` | Identity resolution, coverage matrix, materialization gate |
| `app/data/models/engine_b/v2_manifest.json` | Routes positions to current pkl artifacts (gitignored) |
| `resources/draft_state.js` | Live draft state written by `refresh_draft_state.py` |

## Commands

```bash
# API server
uvicorn app.main:app --reload

# Tests (check AGENT_SYNC.md for current --ignore flags)
.venv/bin/python3.14 -m pytest

# Single test file
.venv/bin/python3.14 -m pytest tests/contract/test_pvo_schema.py -v

# Backtest (check AGENT_SYNC.md for which positions are ACTIVE_B)
.venv/bin/python3.14 scripts/run_backtest.py --position WR
.venv/bin/python3.14 scripts/run_backtest.py --all

# Refresh prospect cards — GATED: check AGENT_SYNC.md for current phase gate before running
.venv/bin/python3.14 scripts/refresh_prospect_cards.py

# DVS percentiles
.venv/bin/python3.14 scripts/compute_dvs_pct_batch.py

# FantasyCalc snapshot — market data is overlay-only; run only within approved task scope
.venv/bin/python3.14 scripts/snapshot_fantasycalc.py

# Draft state refresh — GATED: check AGENT_SYNC.md for the current run condition
.venv/bin/python3.14 scripts/refresh_draft_state.py

# What-Changed daily report — read-only producer over the capture stores; writes the
# gitignored overwrite-latest report served by GET /api/league/what-changed.
# Scheduled by ops/launchd/com.davidleess.dynasty-what-changed-report.plist (09:45, RunAtLoad=false);
# launchctl load + first live generation are David-gated. decision_supported=false.
.venv/bin/python3.14 scripts/run_what_changed_report.py --preflight   # readiness check (no write)
.venv/bin/python3.14 scripts/run_what_changed_report.py               # generate the report
```

### Frontend — run the gate before every push

CI's Frontend job runs `typecheck → lint (Biome) → test (Vitest) → banned-language → build`. A green `tsc`/`vitest` is **not** a green CI: Biome (`npm run lint`) enforces formatting + a11y/correctness rules that TypeScript and Vitest never check, and it is not part of the typecheck/vitest/ruff gate. Run the combined gate from `frontend/` before pushing any frontend change — exit 0 means the CI Frontend job will pass:

```bash
cd frontend
npm run gate    # typecheck && lint (Biome) && test && banned-language && build — mirrors CI's Frontend job
npm run visual:smoke   # Playwright desktop/mobile/focus/axe evidence bundle (read the captures — contract-green ≠ visual-green)
```

## Test Layout

- `tests/` — unit and integration tests, one file per module
- `tests/contract/` — schema and phase contract tests; gate phase advancement
- `tests/fixtures/` — shared fixtures

## Banned Code Patterns

These are defects, not style preferences:

- KTC or any market-derived value as an Engine A or B model feature (leakage)
- `confidence`, `dynasty_tier`, `verdict`, `action` as David-facing output fields
- Binary age-cliff logic inside model training (cliff ages are display warnings only)
- Aliasing `TRADE_PARITY_BAND` and `NOISE_BAND` — they govern different things
