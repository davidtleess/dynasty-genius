# Model Architecture

## Overview

Dynasty Genius uses two prediction engines that feed a unified dynasty value layer.

## Engine A: Incoming Rookie Forecast

- **Use case:** Pre-draft and rookie-draft decisions
- **Input class:** Pre-NFL and draft-time features
- **Examples:** Draft capital, age at entry, RAS, college production metrics
- **Output:** Long-horizon projection at player entry

## Engine B: Active NFL Player Forecast

- **Use case:** Ongoing valuation of current NFL players
- **Input class:** NFL usage, efficiency, time-series production, aging context
- **Examples:** Target share, air yards share, EPA-based metrics, age curve state
- **Output:** Forward projection for active players

## Unified Dynasty Value Layer

This layer converts both engine outputs into one comparable scale.

### Required Outputs
- `dynasty_value_score`
- `confidence_band` (or uncertainty range)
- `projection_1y`
- `projection_2y`
- `projection_3y`

## Data and Evaluation Principles

- Position-stratified modeling for QB/RB/WR/TE.
- No manually invented feature weights.
- Bust outcomes remain encoded as real zeros (not null drops).
- Validation gates must be satisfied before downstream product exposure.
