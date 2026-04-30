# Dynasty Genius Mission Recalibration

Date: 2026-04-29
Status: Locked for next iteration

## Core Mission

Dynasty Genius is a continuous dynasty valuation engine for every relevant NFL player (QB, RB, WR, TE), not only a rookie tool.

The system must continuously project future dynasty value for:
- Players on my roster
- Incoming rookies
- Waiver players
- Players on opponent rosters

## Competitive Advantage Goals

1. Highest hit rate on incoming rookies using pre-NFL signal quality.
2. Most accurate predictive metrics and values for active NFL players across the league.

## System Design Direction

### Engine A: Incoming Rookie Forecast
- Purpose: Pre-draft and rookie-draft decisions.
- Inputs: Pre-NFL and draft-time features only (for example: draft capital, age, RAS, college metrics).
- Output: Long-horizon projection at player entry.

### Engine B: Active NFL Player Forecast
- Purpose: Ongoing in-season and offseason valuation of current NFL players.
- Inputs: NFL usage, efficiency, time-series performance, age curve context, and market context.
- Output: Forward dynasty projection for current players.

### Unified Dynasty Value Layer
- Purpose: Put rookies and veterans on one comparable value scale.
- Core outputs:
  - `dynasty_value_score`
  - confidence/uncertainty band
  - horizon projections (1-year, 2-year, 3-year)

## Product Implications

This architecture powers:
- League-wide player rankings by projected future value
- Roster hold/sell/buy signals
- Waiver pickup prioritization
- Trade package comparison from one common value currency
- Rookie board inside the same valuation system

## Current Decisions (Confirmed)

- RAS ingestion: Approved
- Trade evaluator: Keep internal valuation for now
- Frontend timing: Secondary to model credibility and validation quality

## Tomorrow Kickoff Plan

1. Convert this mission into canonical project docs and planning artifacts.
2. Define the unified output schema for all player valuations.
3. Split planning into two pipelines:
   - incoming rookie model path
   - active player model path
4. Align trade analyzer with the unified value layer (without external KTC dependency yet).
5. Set measurable quality gates before frontend expansion.

## Working Principle

Never optimize for short-term feature completion over long-term valuation accuracy.
