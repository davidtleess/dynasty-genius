---
document: Dynasty Genius Product Constitution
version: 1.0.0
last_updated: 2026-05-07
authority: highest
source_documents:
  - docs/governance/archive/originals/DYNASTY_GENIUS_FRAMEWORK.original.md
  - docs/governance/archive/originals/DYNASTY_GENIUS_PRODUCT_DESIGN.original.md
---

# Dynasty Genius Product Constitution

This is the binding analytical doctrine for Dynasty Genius.

Authority: This document supersedes all other architecture and process files regarding player evaluation logic. If an architectural pipeline conflicts with this constitution, the architecture is wrong.

Dynasty Genius is a personal dynasty fantasy football intelligence system for David and David's primary Superflex PPR league. It is not a public SaaS product. It does not need authentication, billing, roles, public APIs, social features, or generic multi-user abstractions.

The mission is simple and demanding: help David win now while remaining a sustained dynasty contender.

Every analysis, feature, model, data pipeline, and agent session must serve a concrete dynasty decision David actually has to make:

- rookie draft pick: best player available vs. roster need
- trade accept, reject, or counter
- roster hold, sell, replace, or develop
- contender vs. future-value tension
- waiver or depth stash decision
- league-opponent trade targeting

If a feature does not improve one of those decisions, it is out of scope until David explicitly changes the mission.

## Prime Directive

Be right, not fast.

Dynasty Genius optimizes for decisions that will look correct 3-7 years from now. Speed, confidence, and surface plausibility are not product virtues unless the underlying evaluation is verified and durable.

Before moving from evidence to recommendation, slow down and re-read the data. The transition from collection to conclusion is the highest-risk point in this product.

## Product Tenets

Truth over convenience. If a conclusion cannot be supported by verified inputs, label it as inference or do not make the claim.

Reproducibility over improvisation. The same versioned inputs, formulas, and model artifacts should produce the same outputs.

Governance is part of the product. Source quality, compliance checks, anti-hallucination controls, and auditability are not wrappers around Dynasty Genius; they are part of what makes the system valuable.

Football logic before infrastructure preference. Databricks, medallion layers, jobs, and tables exist to serve the dynasty decision system, not the other way around.

## Evidence Hierarchy

Primary data anchors the analysis. Analyst opinion and market prices are useful only after factual inputs are verified.

1. Ground truth sources:
   - Pro Football Reference and Sports Reference
   - Next Gen Stats
   - PFF
   - PlayerProfiler and RotoViz
   - RAS / ras.football
   - Sleeper for league, roster, and player-universe state
2. Validated analyst sources:
   - Rich Hribar
   - Heath Cummings
   - Adam Harstad
   - Nate / Nathan Jahnke
   - Scott Fish for structural dynasty strategy
3. Market signal sources:
   - KeepTradeCut
   - DynastyNerds ADP
   - FantasyPros consensus
   - SFBX and other dynasty ADP sources
4. Never use as primary evidence:
   - unsourced claims
   - highlights-only evaluation
   - narrative-first takes
   - pure beat-reporter hype
   - redraft analysis dressed up as dynasty analysis

Market data is price discovery, not truth. KTC and similar sources reveal what the market believes. They do not define player quality.

## Quantitative / Qualitative Discipline

The default evidence weighting is 65% quantitative and 35% qualitative.

The quantitative side must be grounded in verifiable metrics such as draft capital, age at entry, dominator rating, breakout age, YPRR, target share, route participation, snap share, EPA, CPOE, weighted opportunity, and fitted age-curve state.

The qualitative side is reserved for high-quality, verifiable signals:

- coaching and scheme usage
- medical and injury context
- organizational development environment
- credible film analysis that explains something not yet visible in box-score data

The qualitative allocation is not a license for hype, narrative, or consensus-chasing.

## Locked Analytical Rulings

These rulings resolve prior document drift and are not relitigated by agents.

### Aging Curves

Models consume fitted, continuous aging curves whenever sufficient data exists.

Hard cliff ages remain human-readable decision warnings only:

- RB: age 26 warning
- WR: age 28 warning
- TE: age 30 warning
- QB: age 33 warning

Decision surfaces may flag players approaching those thresholds. Predictive models must not encode a binary cliff unless explicitly approved after validation.

### RAS

RAS is a risk and context signal by default.

Low RAS may flag downside risk or athletic limitations. High RAS does not mechanically increase dynasty value score unless backtesting proves positive predictive lift for the relevant position and model version.

### KTC And Market Data

KTC, DynastyNerds, FantasyPros, ADP, and market-derived values are overlays only.

They must never enter Engine A or Engine B as predictive model features. Any market-derived feature in a model training row is leakage and a defect.

### Backtesting

Backtesting is a trust layer, not optional QA.

Dynasty Genius must show whether its model beats or usefully diverges from the market over time. Model credibility is earned through validation and backtest visibility, not attractive UI.

### Frontend

Frontend polish comes last.

No David-facing surface should imply decision-grade confidence before the underlying model, source freshness, and validation gates justify it.

## Rookie Evaluation Rules

NFL draft capital is the strongest single rookie predictor because it captures organizational commitment, opportunity runway, and role patience.

Draft capital is evaluated before landing spot.

Default rookie decision order:

1. NFL draft capital
2. age at NFL entry
3. position-specific production and efficiency metrics
4. verified trusted post-draft rankings
5. David's roster need
6. landing spot quality as a contextual modifier

Approximate draft-capital / situation weighting:

- picks 1-32: draft capital dominates
- picks 33-64: draft capital and situation are roughly equal
- picks 65+: situation and path to role become more important

Age modifies the framework. A younger player with slightly worse draft capital can beat an older player with better capital because age expands the dynasty production window.

## Position Signals

These are analytical priorities, not hardcoded formulas.

QB:

- draft capital
- age at entry
- EPA/play
- CPOE
- job security and Superflex starter stability
- rushing profile and aging trajectory

RB:

- draft capital
- age at entry
- weighted opportunity
- yards before contact context
- breakaway profile
- receiving role
- offensive line context
- fitted aging-curve state

WR:

- draft capital
- age at entry
- dominator / breakout age
- YPRR
- TPRR
- target share
- air yards share
- route participation
- fitted aging-curve state

TE:

- draft capital
- age at entry
- YPRR
- route participation
- target share
- role path in pass offense
- slower development curve

## Mandatory Protocols

### Verify Current Status

Before evaluating any active player, verify:

- current NFL team
- current role
- age
- most recent season production
- relevant usage metrics
- current dynasty market value from a named source when market context is used

Do not evaluate a player from memory if current status may have changed.

### Separate Dynasty And Redraft

Every recommendation must state its time horizon. A player can be useful for redraft and a poor dynasty asset, or the reverse.

### Counter-Argument Required

Every strong recommendation must include a real counter-argument. Steelman the downside path rather than creating a weak objection.

### Uncertainty Required

Dynasty forecasting is probabilistic. Use confidence ranges, caveats, or explicit uncertainty language when the evidence is incomplete or the recommendation is materially risky.

### Picks Appreciate, Veterans Depreciate

Trade analysis must explicitly account for the tendency of future picks to appreciate as rookie drafts approach and veteran assets to depreciate with age, injury, and role uncertainty.

## Standing Non-Goals

These are out of scope unless David explicitly revises the constitution:

- authentication
- multi-user accounts
- billing
- public SaaS features
- mobile app
- social features
- league chat assistant
- DFS optimizer
- best-ball tooling
- mock draft simulator
- public leaderboards
- generic AI chatbot that bypasses structured decision cards

## Authority

This constitution governs analytical decisions.

If this file conflicts with `01-north-star-architecture.md`, stop and log the conflict before implementation. Do not silently choose the more convenient rule.
