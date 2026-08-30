# Dynasty Genius Roadmap

> ## ⚠️ SUPERSEDED — HISTORICAL, NOT THE PLAN (banner added 2026-08-30, DG-101)
>
> **Last substantive change 2026-04-30 — four months before the current law set, and before
> DG 3.0 existed.** Working from this file today reproduces exactly the doc-rot failure the
> 2026-08-29 gap audit found. The governing documents are:
> - `docs/strategies/2026-08-20-dynasty-genius-MASTER-architecture-and-build-plan.md` (David-approved)
> - `docs/strategies/2026-08-20-dg-product-law-amendments-REV2.md`
> - `~/dg-build/BOARD.md` + `~/dg-build/ROADMAP-LAYERS.md` (the live ticket board and ratified layer roadmap)
> - `~/dg-build/IN-SEASON-QUEUE.md` (the ordered queue through the 2026 season)
>
> Anything below that promises buy/sell flags, verdicts, or a cloud-warehouse architecture is
> **contradicted by current law**, not merely stale. Kept for history; do not plan from it.

## North Star

Build a unified dynasty value system that scores all relevant players (QB/RB/WR/TE) across rookies and active NFL players.

## Phases

### Phase 1: Foundation Stabilization
- Harden config and remove hardcoded league/user assumptions.
- Add validation harness and quality gates for model outputs.
- Version model artifacts and persist model metrics.

### Phase 2: Two-Engine Modeling
- Engine A (Incoming Rookie Forecast): draft-time and pre-NFL features.
- Engine B (Active Player Forecast): NFL usage and efficiency signals.
- Produce comparable outputs for both engines.

### Phase 3: Unified Value Layer
- Normalize both engine outputs into one dynasty value currency.
- Add confidence bands and 1/2/3-year horizon projections.
- Power roster, waiver, and trade decisions from one source of truth.

### Phase 4: Product Surfaces
- League-wide rankings and filtering.
- Roster auditor with hold/sell/buy flags.
- Trade analysis driven by unified value scores.
- Rookie board built on the same valuation scale.

## Current Confirmed Decisions

- RAS ingestion is approved.
- Trade evaluator stays internal for now.
- Frontend expansion stays secondary to model credibility.
