---
document: Dynasty Genius North Star Architecture
version: 1.0.0
last_updated: 2026-05-07
authority: technical
source_documents:
  - docs/governance/archive/originals/DYNASTY_GENIUS_NORTH_STAR.original.md
---

# Dynasty Genius North Star Architecture

This is the binding technical contract for Dynasty Genius.

The constitution defines how Dynasty Genius thinks. This document defines how the system is built so the product cannot drift away from that thinking.

## Architecture Principle

Build a unified dynasty valuation system for David's league, not a collection of disconnected tools.

Every data source, model, API, and decision surface must converge on one comparable player valuation layer. Decision surfaces read from that layer; they do not invent their own scoring logic.

## Layered System

```text
------------------------------------------------+
| Frontend                                      |
| Last; no decision-grade polish before trust   |
+------------------------------------------------+
| Decision Card API Layer                       |
| rookies, roster, trade, waiver, league pulse  |
+------------------------------------------------+
| Decision Surfaces                             |
| read-only over PVO + league context           |
+------------------------------------------------+
| Unified Dynasty Valuation Layer               |
| Player Value Object                           |
+------------------------------------------------+
| Engine A Rookie Forecast | Engine B Active    |
+------------------------------------------------+
| Feature Store                                 |
| versioned player_id x season features         |
+------------------------------------------------+
| League Context Layer                          |
| David roster, picks, scoring, posture, risk   |
+------------------------------------------------+
| Identity Resolution Layer                     |
| canonical player_id and source mappings       |
+------------------------------------------------+
| Source Adapters + Raw Snapshots               |
| Sleeper, nfl_data_py, PFF, PP, RAS, KTC       |
+------------------------------------------------+
```

## League Context Is Core Data

David's league is not generic configuration. It is a first-class model input and decision context.

The system must reason over:

- Superflex PPR scoring
- lineup requirements
- taxi and IR rules
- David's roster
- David's future draft picks
- league-mate rosters
- championship posture
- risk tolerance
- trade partner fit

Changing posture must propagate through decision recommendations without changing model training data.

## Source Adapter Rules

Each external source has exactly one adapter.

Every adapter must:

- fetch or ingest data through a defined interface
- write a raw snapshot before parsing when feasible
- parse into normalized rows
- attach source timestamp, parser version, and completeness flags
- expose stale-source caveats downstream
- define a manual fallback if automated scraping is fragile

Silent substitution is forbidden. If a source breaks, downstream records must show stale or missing data rather than pretending nothing happened.

## Data Platform Pattern

Databricks is the preferred governed data platform when the work requires durable storage, scheduled jobs, lineage, or cross-agent auditability. The platform pattern is medallion-oriented:

Bronze:

- raw or minimally transformed source snapshots
- ingestion timestamps
- source metadata
- provenance and source-rank fields where available
- replayable inputs for parser and model debugging

Silver:

- cleaned and normalized rows
- canonical identity attached
- metric standardization
- source-rank enforcement
- historical backfills
- business-rule-safe transformations

Gold:

- decision-grade outputs
- valuation anchors and calibrated artifacts
- trade evaluation logs
- exception or archetype candidate outputs
- compliance flags and lineage fields

Current or planned governed tables may include:

- `gen_alpha.gold.agent_activity_log`
- `gen_alpha.gold.artifact_registry`
- `gen_alpha.gold.trade_evaluations`
- `gen_alpha.gold.exception_archetype_candidates`
- `gen_alpha.silver.efficiency_metrics`

These table names are implementation artifacts, not analytical law. If they conflict with the constitution, the constitution wins and the table design must change.

## Identity Resolution

Canonical identity is foundational.

Rules:

- Dynasty Genius owns one canonical `player_id`.
- Source IDs live in one mapping layer.
- Fuzzy matching is allowed only in reviewable staging.
- Unresolved feature rows are rejected to triage, not silently scored.
- No adapter may invent its own production identity logic.

Identity resolution must be built before broad feature ingestion, because inconsistent identity corrupts valuation.

## Feature Store

Features are versioned hypotheses, not eternal constants.

Every computed feature should preserve:

- `player_id`
- season or effective date
- source
- source timestamp
- parser or metric version
- completeness / caveat flags

Metric formulas must be versioned. Formula changes without version bumps are defects.

Thresholds and calibration values belong in structured artifacts with provenance, not in hidden application logic.

Feature storage must preserve enough lineage to answer: which source, snapshot, parser version, metric version, and governance version produced this value?

Market-derived values may exist in overlay tables, but they must be physically and semantically separated from Engine A and Engine B training features.

## Deployment And Environment Standards

When running on Databricks or other production-like infrastructure:

- use file-based configuration over UI-only configuration
- use Databricks Asset Bundles or equivalent IaC when available
- store SQL and job logic in version-controlled files
- pass required business parameters explicitly
- log job runs, environment, code version, and governing doctrine version
- promote through controlled Dev -> Staging -> Prod paths when environments exist

Code should use portable configuration variables such as `S3_BUCKET` rather than hardcoded storage locations. Documentation may name canonical placeholder paths when useful, but production code should remain environment-safe.

Jobs and pipelines must be reproducible. A manual notebook result is not production behavior until the logic is checked into the repo and scheduled or callable through governed execution.

## Engine A: Rookie Forecast

Engine A supports pre-draft and rookie-draft decisions.

Allowed feature classes:

- NFL draft capital
- age at entry
- college production
- dominator / breakout-style production metrics
- college YPRR and receiving efficiency
- college target share
- position-specific athletic risk flags

Disallowed feature classes:

- NFL usage after the player enters the league
- KTC, ADP, FantasyPros, DynastyNerds, or market-derived values
- freeform narrative

RAS handling:

- low RAS may contribute risk flags
- missing RAS may contribute caveats
- high RAS is not a positive model input unless validated by backtesting

Output must conform to the Player Value Object contract.

## Engine B: Active Player Forecast

Engine B supports ongoing valuation of active NFL players.

Allowed feature classes:

- NFL usage
- snap share
- route participation
- target share
- air yards share
- YPRR
- TPRR
- weighted opportunity
- EPA and CPOE for QBs
- multi-year production trends
- team and role context
- fitted continuous aging-curve state

Disallowed feature classes:

- KTC, ADP, FantasyPros, DynastyNerds, or market-derived values
- expert consensus as a model feature
- rookie-only pre-NFL features leaking into active-player training unless explicitly modeled as a prior

Market-derived features in Engine B are leakage defects.

## Aging Curve Architecture

Models consume fitted continuous curves when sufficient data exists.

Human-readable cliff warnings may appear on decision cards, but the model should use calibrated continuous state such as age percentile, estimated decline state, or fitted remaining value curve.

Hardcoded age cliffs are fallback display warnings, not model law.

## Unified Player Value Object

Every relevant player should resolve to one comparable valuation row.

Required fields, as the system matures:

```text
player_id
position
age
engine_used
model_version
model_grade
signal_completeness
dynasty_value_score
projection_1y
projection_2y
projection_3y
inputs_present
inputs_missing
top_drivers
risk_flags
counter_argument
caveats
market_overlay
```

Decision surfaces may omit fields only when the omission is explicit and caveated.

## Market Overlay

KTC and other market sources join after model scoring.

The market overlay may contain:

- current market value
- trend delta
- model-minus-market delta
- market percentile
- source timestamp
- caveats

The market overlay never feeds the predictive score.

## Decision Surfaces

Decision surfaces are read-only over the Player Value Object and league context.

Primary surfaces:

- Rookie Board
- Roster Audit
- Trade Lab
- Waiver Radar
- League Pulse
- Model Trust
- Research Assistant

Gates:

- Rookie Board is first polished surface.
- Roster Audit remains experimental until Engine B is credible.
- Trade Lab must not emit win/loss verdicts before uncertainty bands are validated.
- Waiver Radar is gated on usage signals such as routes and snaps.
- Frontend comes last.

## Banned David-Facing Output Patterns

Do not reintroduce removed fields or vague verdict language:

- rookie `confidence` mapped from pick bucket
- rookie `dynasty_tier` such as Elite / Starter / Depth / Bust
- trade `verdict` such as Strong win / Win / Fair / Loss
- trade side totals before validated uncertainty bands
- roster `action` such as Sell now / Shop actively / Hold as model-grade instruction

Decision support must use measured uncertainty and caveats, not false certainty.

## Validation Gates

Phase advancement is controlled by composite validation gates, not vibes and not a single metric.

Relevant gates include:

- R2
- Spearman rank correlation
- top-k hit rate
- RMSE stability across rolling holdouts
- null coverage
- caveat hygiene
- leakage checks
- banned-field contract tests
- source freshness checks

Backtesting must compare model predictions, market values, and realized outcomes over time.

## Phase Sequence

The build order is:

1. Foundation safety and governance
2. League context foundation
3. Identity resolution
4. Source adapter contract and raw snapshots
5. Engine A feature expansion
6. Fitted aging curves
7. Engine B MVP
8. Unified Player Value Object
9. Decision surfaces over PVO
10. Market overlay
11. Backtest harness
12. Frontend

No agent should advance phases without satisfying the relevant gate or logging an explicit David-approved exception.

## Cross-Agent Write Discipline

Agents must work in bounded scopes.

- One agent owns a cross-cutting file at a time.
- Parallel agents may work on disjoint adapters or analyses.
- Every material session updates `AGENT_SYNC.md` or the daily ledger.
- Every PR states which phase it advances and which validation was run.

## Authority

This document governs technical architecture.

If this file conflicts with `00-product-constitution.md`, the constitution wins for analytical decisions. For implementation details, pause and log the conflict rather than guessing.
