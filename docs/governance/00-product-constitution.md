---
document: Dynasty Genius Product Constitution
version: 1.1.0
last_updated: 2026-07-14
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

### In-Season Estimate Responsiveness And Model-Change Governance

Two distinct things may "improve" over time, and they must never be conflated:

1. A player's daily estimate (PVO) may update frequently and autonomously.
2. The predictive model itself — its parameters, features, thresholds, and promotion gates — changes rarely and only by deliberate, human-gated promotion.

Rulings:

- Daily estimates update via a deterministic, versioned overlay on a frozen model artifact. The daily estimate-update path never retrains the model — deliberate, human-gated, pre-registered model promotion (see "The model is the anchor" below) is the only path to a model change. The estimate leads on usage/role signals (snaps, routes, targets, red-zone work, depth-chart and injury-driven role changes) and lags on noisy box-score outcomes (fantasy points, touchdowns, efficiency spikes), with shrinkage toward the prior and position-varying responsiveness: RB fastest; WR medium (move on a sustained multi-week trend, not one game); TE fast on route participation but slow on production (do not chase touchdown variance); QB slowest, reacting to job security and depth-chart status rather than weekly efficiency. For off-season player transfers, free-agency moves, or coaching/coordinator changes — where no new games have been played — the quantitative PVO remains stable until new in-season utilization accumulates; the transition's immediate impact is carried only as a qualitative team-context caveat, never a speculative quantitative PVO adjustment before snaps are played in the new offense.

- Bias to stability. When the correct responsiveness is uncertain, prefer the more stable setting. The too-jumpy error (recency-driven panic acquisition or liquidation that mirrors market noise) destroys more dynasty value than the too-frozen error (an occasional missed acquisition window). [David-ratified 2026-06-27.]

- The model is the anchor. The predictive model must not auto-adjust in-season. In-season monitors may detect, report, alert, and queue candidate changes (cohort-error reports, drift detection, candidate features, pre-registered bake-off jobs, proposed specs/patches). Feature promotion, coefficient or model-artifact replacement, threshold/half-life changes, and any change to model training behavior are human-gated and require pre-registered validation. Auto-tuning the model in-season is a defect: it introduces leakage, breaks reproducibility and auditability, and moves the very baseline used to measure model-vs-market divergence.

- All daily-estimate overlay outputs are descriptive (`decision_supported=False`) until a pre-registered validation earns decision-grade status. Market data stays out of model inputs and out of the predictive overlay throughout (overlay-only, per the KTC ruling).

### Descriptive Tools Issue No Verdicts (The No-Verdict Line)

A descriptive tool surfaces facts, ranges, ranks, and risks so David can decide. It must not decide for him.

This line governs running-software outputs — JSON payloads, API responses, stdout, written artifacts, and their caveats. It does not restrict design specs, roadmap plans, or strategy/PM briefs, which may discuss product-vision destinations (sell-timing, contrarian targets, transaction horizons) as where the product is headed — provided they never claim the current shipped model has already arrived.

Rulings:

- While a tool is classified as descriptive, every output carries `decision_supported=False` recursively — root and every nested model. A tool earns decision-grade status only through a pre-registered validation David ratifies; until then the no-verdict line holds.

- Descriptive is not directive. A descriptive tool may report quantities, explicit sort orders, counts, ranks, value-at-risk ranges, deficits, gaps, caveats, and structural states. It may not emit a normative verdict, recommendation, or imperative — no "buy/sell/hold", "keep/cut", "must"/"do not", "safe to", "recommended", or equivalent. Banned-language scans over running-software output and artifacts are a legitimate enforcement mechanism. Enforcement tests may scan source code, templates, fixtures, or generated-client surfaces when those are direct proxies for running-software output; that is enforcement of runtime safety, not a ban on strategy, spec, or roadmap language.

- Surface the arithmetic honestly, unclamped. Show gaps that cross zero (a cut that is a net upgrade reads negative), deficits as raw counts, and wide volatile ranges as wide ranges. Tightening, clamping, banding, or editorializing a number into a recommendation is the failure mode this line prevents. When inputs cannot be trusted — stale, missing, malformed, or low-coverage — report unavailable, block, or widen uncertainty; never fabricate a confident tidy number that reads as a verdict.

- Ranks and tiers must disclose their basis, never nudge. A default sort or rank must be tied to a declared transparent metric or rule, and any composite ordering must disclose its components and not function as a hidden recommended action order. Present raw percentile position alongside any tier label.

- Named tier labels ("Generational", "Elite", "Cornerstone", "Starter", "Depth") are legal only when assigned by a David-ratified statistical tier-calibration model — never by hand, never by an arbitrary fixed bucket chosen for convenience. A named tier is a descriptive statement about a player's calibrated position (by DVS, by production, or both, per the calibration contract); it carries its basis on the surface (the raw rank/percentile plus the cohort population and its numeric denominator that earned it) and remains descriptive (`decision_supported` is governed separately; a tier label never flips it). "Bust" remains banned — a pejorative verdict, not a calibrated position. Until a valid ratified `tier_calibration` artifact authorizes a given label, that label may not be computed, serialized, emitted on any API, persisted, or rendered — front end or back end; every non-calibration occurrence stays fail-closed. Market-lane and model-lane tiers are calibrated on their own lane's basis and never blend into a single tier. The defect this prevents is not the word but the *unearned* word: a calibrated label is a disclosed-basis position, not a smuggled verdict. [David-ratified 2026-07-14; amendment `docs/superpowers/specs/2026-07-14-00-amendment-calibrated-tier-lexicon.md`; the enforcement-surface edits and the `CalibratedTier` disclosure primitive land per the amendment's binding sequence — the calibration gate before the vocabulary relaxes.]

- No nominated target by the back door. A tool may echo a David-supplied hypothesis (a proposed cut or trade) and display candidate rows — including player identifiers — under an explicit sort key. It may not select a player or action as the tool's own chosen target: a "next/marginal" cost is an index of the next increment in an existing order, not a recommendation, and carries no hidden "do this" payload.

Precedent: Roster Capacity Scenario Simulator v1 (PR #91), built end-to-end against this line. This consolidates and broadens the Frontend ("no decision-grade confidence before validation"), In-Season ("descriptive overlay, `decision_supported=False`"), and KTC ("overlay-only") rulings into a single decision-surface rule. [David-ratified 2026-06-28.]

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
