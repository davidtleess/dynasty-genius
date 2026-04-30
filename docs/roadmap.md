# Dynasty Genius Roadmap

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
