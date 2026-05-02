# Dynasty Genius — System Design

Canonical north-star architecture and product rules. This is the strategy layer.

- Companion playbook: [agent-execution-plan.md](agent-execution-plan.md)
- Adapter / identity contracts: [data-source-contracts.md](data-source-contracts.md)
- Phase advancement gates: [validation-gates.md](validation-gates.md)

## Mission

**Help David win this league now while staying a sustained dynasty contender.**

Dynasty Genius is a personal decision system for one user (David), in one Superflex PPR league, focused on one objective: win the championship and remain a sustained contender. It produces continuous valuations for every relevant NFL player at QB / RB / WR / TE — rookies, active veterans, waiver players, and players on opponent rosters — but valuation is the means, not the end. The end is decisions David has to make.

Guardrail: never optimize for short-term feature completion over long-term valuation accuracy. Never drift toward generic dynasty SaaS.

## Product Positioning

Dynasty Nerds, KTC, FantasyCalc, and Superflex.app are category foils, not templates. They are broad consumer tools optimized for many users acting faster. Dynasty Genius is optimized for one user acting more correctly.

> **Dynasty Nerds helps many users act faster. Dynasty Genius helps David act more correctly in one league.**

That one-user, one-league scope is a feature, not a limitation. It is the source of the system's edge.

### Primary Objective

Become champion and remain a sustained dynasty contender in David's primary Superflex PPR league. Every feature is judged by whether it improves a decision that follows from that objective.

### Decision Hierarchy

Every product surface must improve at least one of these concrete decisions:

- **Rookie draft pick** — who to take with each rookie pick, BPA vs. roster need
- **Trade accept / reject / counter** — is this offer better than my current asset, by how much, with what uncertainty
- **Roster hold / sell / replace** — which assets to move now vs. hold vs. develop
- **Contender vs. future-value tension** — when to mortgage future picks for now, when to accumulate
- **Waiver / depth stash decision** — which available players are leading-indicator buys
- **League-opponent trade targeting** — which opponents are buyers, which are sellers, and on which positions

Features that don't improve one of these decisions are out of scope until they do.

### Personal Context Is Core Data

David's actual league is a first-class model input, not configuration. The system knows and reasons over:

- **League settings** — Superflex PPR, scoring, lineup requirements, taxi/IR rules
- **David's roster** — every active player, taxi player, draft pick
- **League-mate rosters** — every other team, scored on the same scale
- **Draft capital** — David's incoming picks across all years, by round
- **Championship window** — explicit posture (contender / sustained-contender / soft-rebuild) is a settable input
- **Risk tolerance** — David's preference for variance, set explicitly, not assumed
- **Trade partner history** — who David has historically traded with, who is open to deals

These are encoded in `app/data/league/` and consumed by every decision surface. Changing posture (e.g., contender → rebuild) is a single config edit that propagates through every recommendation.

### Better Than Dynasty Nerds Means More Transparent, Not Broader

Do not compete by copying their feature list. Compete by separating layers that broad consumer dynasty tools blend into a single number:

- **Production forecast** — what the model expects this player to produce
- **Market price** — what KTC / DN / FantasyCalc say this player is worth
- **Talent / scouting signal** — pre-NFL signal quality (Engine A inputs)
- **Age curve** — where this player sits on the fitted decline curve
- **Roster fit** — how this player compares against David's current depth at position
- **Championship-window value** — how this player contributes given David's posture
- **League-specific scarcity** — how scarce this profile is across opponent rosters
- **Trade liquidity / opponent fit** — which league-mates would value this player more than David does

Every decision card decomposes into these layers. A user who only wants the headline number can read it; a user who wants to understand it can drill in.

### No Mystery Rankings

A single dynasty value score is allowed but it must be decomposable. Every recommendation surfaces:

1. **What the model thinks** — production forecast with uncertainty
2. **What the market thinks** — KTC overlay, model-vs-market delta
3. **What David's roster context implies** — fit, scarcity, championship-window weight
4. **The strongest counterargument** — generated from threshold-flag risk set, not freeform
5. **Missing or stale data** — explicit `inputs_missing` and `caveats`

Opaque expert consensus is the failure mode this rule prevents.

### Backtesting Is A Product Advantage

The backtest harness is a David-facing product surface, not internal QA. Per-position monthly charts of model prediction vs. KTC vs. realized fantasy outcome are how David learns when to trust the system and when to override it. A model whose backtest record David cannot see is a model David should not trust.

### Anti-Scope Rule

If a feature is mostly useful for a public dynasty product but does not directly improve a decision in the Decision Hierarchy above, it is out of scope. This rule overrides analyst intuition. When in doubt, the feature is out.

## Locked Defaults

These decisions are settled. Agents do not re-litigate them.

| Decision | Locked Value |
| --- | --- |
| Build mode | Build forward from current repo. No restart. |
| Scope | One user (David), one league (his primary Superflex PPR). No multi-league abstraction unless it directly serves David's league. |
| Default league format | Superflex PPR. |
| Core valuation philosophy | Production-first. Market data is overlay only, never an input to the score. |
| Personal context | League settings, rosters, picks, posture, and risk tolerance are first-class model inputs, not config. |
| Paid source access | In scope. PFF, PlayerProfiler, KTC subscriptions assumed. Credentials never committed. |
| Scraping posture | Automated scraping primary; manual export fallback always defined. |
| Trade and roster surfaces | Stay quarantined as `experimental` until they consume the unified Player Value Object. |
| Removed output fields | Stay removed (see "Field Ratchet" below). |
| Frontend | Last. Never ships before model credibility. |

## Architectural Layers

The system is layered. Each layer has one responsibility and a stable contract with the layers above and below it. Agents work inside one layer at a time.

```
+------------------------------------------------+
| Frontend (deferred, last)                      |
+------------------------------------------------+
| Decision Card API Layer                        |
| (rookies, roster, trade, waiver, league pulse) |
+------------------------------------------------+
| Decision Surfaces (read-only over PVO + LC)    |
| (Rookie Board, Roster Audit, Trade Lab, ...)   |
+------------------------------------------------+
| Unified Dynasty Valuation Layer                |
| (Player Value Object — single canonical row)   |
+------------------------------------------------+
| Engine A (rookie forecast) | Engine B (active) |
+------------------------------------------------+
| Feature Store                                  |
| (versioned features per player_id × season)    |
+------------------------------------------------+
| League Context Layer                           |
| (David's settings, roster, picks, posture,     |
|  league-mate rosters, risk tolerance)          |
+------------------------------------------------+
| Identity Resolution Layer                      |
| (canonical player_id ↔ all source IDs)         |
+------------------------------------------------+
| Source Adapters + Raw Snapshots                |
| (Sleeper, nfl_data_py, PFF, PlayerProfiler,    |
|  RAS, KTC — automated + manual paths)          |
+------------------------------------------------+
```

The League Context layer sits above identity and below the engines because every engine output is interpreted through David's league. A player score with no league context is a curiosity; the same score combined with David's posture, depth chart, and trade-partner fit is a decision.

## Data Source Responsibilities

| Source | Owns |
| --- | --- |
| Sleeper API | League state, rosters, player universe, draft picks where exposed |
| `nfl_data_py` / Pro Football Reference | Historical stats, NFL draft capital, outcomes, active-player baselines |
| PFF (subscriber) | Snap counts, route participation, player grades, YPRR |
| PlayerProfiler / RAS | College Dominator, Breakout Age, athletic testing, RAS |
| KeepTradeCut (KTC) | Market value overlay, trend deltas, market-vs-model deltas |

Cross-cutting rules for every source:

- Each source has exactly one adapter. No source is read in two places.
- Every adapter writes a raw snapshot before parsing.
- Every parser produces normalized rows tagged with source timestamp, parser version, and completeness flags.
- A source breaking degrades to a stale-source caveat surfaced on every downstream record. Silent substitution is forbidden.

Per-source schemas, automated paths, manual export paths, and freshness rules live in [data-source-contracts.md](data-source-contracts.md).

## Player Identity Strategy (Phase 1, Foundational)

Identity resolution is the spine of the system. Without it, every feature adapter invents its own fuzzy match and the valuation surface becomes silently inconsistent. This is built before any external feature adapter is wired in.

Rules:

- One canonical internal `player_id` is owned by Dynasty Genius and stamped on every feature row, projection, and decision card.
- Source-specific IDs (Sleeper `player_id`, gsis_id, PFR slug, PFF `player_id`, PlayerProfiler ID, RAS row, KTC slug) live in a single mapping table. The mapping is the only place fuzzy logic is allowed.
- Fuzzy matches are written to a reviewable staging table, not directly to production. A new mapping enters production only after a human (David) or an explicit confidence-rule check approves it.
- Any feature row whose source ID cannot be resolved to a canonical `player_id` is rejected, not silently produced. Rejected rows go to a triage table.

Full identity contract: [data-source-contracts.md](data-source-contracts.md#identity-resolution).

## Quantitative Foundations

Three principles that govern how metrics enter the system. They exist because the underlying domain literature attaches numbers to thresholds and formulas with more confidence than the data justifies.

### 1. Thresholds are configurable artifacts with provenance

Every threshold (cliff age, Dominator cutoff, RAS line, snap %, YPRR line) lives in `app/data/calibration/thresholds.yaml`. Each entry has:

```yaml
- id: wr_dominator_floor
  value: 0.20
  position: WR
  provenance: published_source     # personal_calibration | fitted | published_source
  source: "PlayerProfiler glossary, retrieved 2026-04"
  last_reviewed: 2026-04-30
```

Thresholds with `provenance: personal_calibration` are flagged in every decision card that uses them. Thresholds with `provenance: fitted` reference the artifact they were fitted from.

### 2. Metric formulas are versioned hypotheses, not constants

Dominator Rating, Weighted Opportunity, TPRR, Breakout Age, RAS — each has multiple defensible operationalizations in the literature. The system stores a formula version (`metric_version`) alongside every computed value. Adding a new formula does not overwrite the old one; both run in parallel until a comparison test picks a winner.

Example:

- `dominator_v1_dupont` (DuPont original)
- `dominator_v2_rotoviz` (Siegele / RotoViz)
- `dominator_v3_playerprofiler` (PlayerProfiler operationalization)

The model's training row records which version it consumed. A formula change without a version bump is a defect.

### 3. Aging curves are fitted continuous artifacts, not hardcoded cliff ages

The framework's cliff ages (RB 26, WR 28, TE 30, QB 33) are personal calibration that current research considers too aggressive. Hardcoded cliff constants are removed. In their place: per-position continuous decline curves fitted from `nfl_data_py` historicals, stored as versioned artifacts under `app/data/calibration/aging_curves/`. Decision surfaces consume the curve, not a constant.

A cliff *age* is allowed only as a default fallback when a position has insufficient data to fit a curve. Even then it is read from `thresholds.yaml`, not hardcoded.

## First-Class Predictive Features

These are the features Engine A and Engine B must consume as first-class inputs. Each is a hypothesis with provenance, version, and a backing test — not a settled formula.

| Feature | Engine | Position | Why first-class |
| --- | --- | --- | --- |
| NFL Draft Capital | A | All | Strongest single rookie predictor for QB/RB; Tier 1 for WR alongside production |
| Age at Entry | A | All | Compounds the production window; underused historically |
| RAS | A | All | **Red-flag-only signal.** Low RAS flags risk; high RAS does not raise floor (no published correlation to WR fantasy outcomes) |
| College Dominator | A | WR / TE / RB | Team-quality-controlled production; multiple operationalizations versioned |
| Breakout Age | A | WR / TE | Distinct from Dominator; pre-20 breakouts disproportionately produce hits |
| YPRR | A then B | WR / TE | Single-number receiving efficiency; stronger when paired with TPRR |
| Weighted Opportunity | A then B | RB | R² ~0.82 to RB fantasy points; the single best RB stat. Not optional. |
| TPRR (targets per route run) | A then B | WR / TE | Leading indicator that *precedes* target share growth |
| Snap % | B | All | Year-1 leading indicator; 70%+ Year-1 disproportionately produces hits |
| Route Participation | B | WR / TE | Same as above; often more informative than snap % |
| Target Share | B | WR / TE | Stable role indicator |
| Air Yards Share | B | WR / TE | Separates volume role from impact role |
| EPA / CPOE | B | QB | Best efficiency metrics for QB |
| Aging Curve State | B | All | Continuous, fitted, position-specific |

Features explicitly *not* first-class inputs to the score (overlay only):

- KTC market value (lives in `market_overlay`, never in the model)
- Expert consensus rankings (sanity-check overlay only)
- Narrative / hype / beat-reporter quotes (not ingested as features)

## Engines

### Engine A — Rookie Forecast

- Use case: pre-draft and rookie-draft decisions.
- Inputs: pre-NFL scoring features only — draft capital, age at entry, College Dominator, Breakout Age, college YPRR, college market share. No NFL usage.
- **RAS is not a positive scoring feature.** RAS-derived signals (`ras_below_position_floor`, `ras_missing`, `ras_context_available`) are risk and context flags surfaced on the decision card; they do not contribute to `dynasty_value_score`.
- Output: long-horizon dynasty projection at entry, conformed to the unified valuation schema.

### Engine B — Active Player Forecast

- Use case: ongoing valuation of every active NFL player.
- Inputs: NFL usage, efficiency, multi-year production trends, age curve state, team context (offensive scheme, target competition, OL grade). No rookie pre-NFL features (those are baked into the prior).
- **Explicitly excluded from Engine B inputs**: KTC, FantasyCalc, Dynasty Nerds ranks/values, ADP, expert consensus, or any market-derived value. Engine B is production-first. Market signals join the player record only later, in the PVO assembly step (Phase 7).
- Output: forward dynasty projection conformed to the unified valuation schema.

Engines are separate. Their feature pipelines do not share columns. A pre-NFL feature leaking into Engine B's training is a leakage defect. A market-derived feature appearing in either engine's training is a leakage defect — `tests/contract/test_ktc_not_in_features.py` enforces this.

## Unified Player Value Object

Every relevant player has exactly one row, regardless of engine:

```
player_id, position, age,
inputs_present:   [list of features that fed the score]
inputs_missing:   [list of features unavailable for this player]
engine_used:      A | B | hybrid
dynasty_value_score
projection_1y, projection_2y, projection_3y
confidence:       {low, median, high}   # only when calibrated
signal_completeness:                    # used until confidence is calibrated
model_grade:      A | B | C | D | unvalidated
top_drivers:      [{feature, contribution, direction}]
risk_flags:       [...]
counter_argument: str
caveats:          [...]
market_overlay:   {ktc_value, model_minus_market, percentile} | null
```

Decision surfaces read this object. They never re-derive valuation.

## Decision Surfaces (read-only over the Player Value Object)

| Surface | Status | Notes |
| --- | --- | --- |
| Rookie Board | First polished surface | BPA / Needs toggle; roster fit is a post-filter, never an input to the score |
| Roster Audit | Promoted from age-only signals once Engine B is calibrated | `value − replacement` and years_to_cliff appear only when calibrated |
| Trade Lab | `delta_status` leaves `within_model_error` only when both sides consume PVO and the uncertainty band excludes zero | Until then: per-asset breakdown, no totals |
| Waiver Radar | Gated until route_pct + snap_share are ingested | Building it earlier produces noise, not signal |
| League Pulse | Every roster scored on the same scale | Required for "who is a contender vs. rebuilder" trade targeting |
| Backtest Harness | First-class product surface, not a checkbox | Monthly chart of model vs. KTC vs. realized outcomes per position |
| Research Assistant | Source-backed evidence trail, never memory-based | Final phase before frontend |

## Public Interfaces and Contracts

Existing endpoint families are preserved:

- `/api/rookies/*`
- `/api/roster/audit`
- `/api/trade/analyze`

Internal service boundaries are added before any new public endpoint:

- `source_adapters`
- `identity_resolution`
- `feature_generation`
- `rookie_forecast`
- `active_player_forecast`
- `unified_valuation`
- `market_overlay`

Every decision card (any David-facing record) includes:

- `engine`, `model_version`, `model_grade`, `signal_completeness`
- `horizon_years`, `dynasty_value_score`, `projection_1y/2y/3y`
- `inputs_present`, `inputs_missing`
- `top_drivers`, `risk_flags`, `counter_argument`
- `caveats`
- `market_overlay` when available, `null` when not

Counter-argument and risk_flags are required and generated from the threshold flag set, not freeform text.

## Field Ratchet — Removed Stays Removed

Once a field is removed from a David-facing surface, it does not come back without an explicit re-introduction step in `agent-execution-plan.md`. Currently removed — and **permanently** removed; the ratchet does not include a path to reintroduce them under any circumstances:

- Rookie `confidence` (the High/Medium/Low one mapped from pick bucket)
- Rookie `dynasty_tier` ("Elite" / "Starter" / "Depth" / "Bust")
- Trade `verdict` (any "Strong win" / "Win" / "Fair" / "Loss" / "Strong loss" framing)
- Trade side totals / aggregated difference
- Roster `action` ("Sell now" / "Shop actively" / "Hold")

Tests in `tests/contract/` enforce that these fields cannot be emitted by their respective surfaces.

### Decision-support replacement fields

Trade decision support, when the model has earned it, returns a structured field rather than reviving the banned verbiage:

- `delta_status` (Trade Lab): one of `within_model_error | likely_favors_me | likely_favors_them | insufficient_confidence`. Computed from the uncertainty band on the trade delta. Never collapses to "you win" / "you lose" framing.

Adding any new decision-support field follows the same pattern: enum with explicit allowed values, computed from a measurable model property, never re-introducing the banned vocabulary.

## Validation Philosophy

Phase advancement is governed by **composite gates**, not single numbers. A position's R² alone — on small one-year holdouts — is variance-driven and a poor blocker. A composite gate combines:

- R² (continuous fit)
- Spearman rank correlation (rank quality)
- Top-k hit rate (does the model put real top-K players in its top-2K?)
- RMSE stability across a 3-year rolling holdout
- Null coverage (% of position rows actually scored)
- Caveat hygiene (no production card emitting `model_grade=unvalidated`)

Definitions, current measured status, and per-phase advancement criteria live in [validation-gates.md](validation-gates.md).

## Phase Sequence (high level)

Detail and step-by-step execution: [agent-execution-plan.md](agent-execution-plan.md).

0. **Foundation Safety** — reincorporate `agent/modeling-backend`, scaffold tests / config / composite-gate harness, `thresholds.yaml` with provenance.
1. **League Context Foundation** — encode David's league: settings, roster, picks, scoring, starter requirements, taxi/IR rules, contender posture, league-mate rosters, risk tolerance. First-class context layer.
2. **Identity Resolution** — canonical `player_id`, mapping table, reviewable staging, fuzzy-only-in-staging rule.
3. **Source Adapter Contract + Raw Snapshots** — adapter interface (fetch / snapshot / parse / normalize / freshness), automated + manual paths, Sleeper and nfl_data_py first.
4. **Engine A Feature Expansion** — RAS (red-flag-only), Dominator, Breakout Age, YPRR, Weighted Opportunity, TPRR. Each metric is a versioned hypothesis.
5. **Fitted Aging Curves** — per-position continuous decline curves from `nfl_data_py` historicals; replaces hardcoded cliff constants.
6. **Engine B MVP** — active-player forecast skeleton with usage / efficiency / aging-curve features.
7. **Unified Player Value Object** — schema and resolver; replaces ad-hoc rookie-only schema. PVO joins the player score with league context.
8. **Decision Surfaces** — Rookie Board, Roster Audit upgrade, Trade Lab over PVO, Waiver Radar (gated), League Pulse, opponent-fit trade targeting.
9. **Market Overlay (KTC)** — separate fields, never enters the score.
10. **Backtest Harness** — first-class David-facing product surface, the trust flywheel.
11. **Frontend** — last, intentionally.

## Workstream Ownership for Parallel Agents

Multiple developer agents may run in parallel. To prevent overlapping write scopes:

- One agent per phase at most. A new phase does not start until its predecessor's validation gate passes.
- Inside a phase, parallel agents may run on disjoint adapters (e.g., RAS adapter and Dominator adapter) but must not edit the same files.
- Cross-cutting files (`thresholds.yaml`, `app/models/valuation.py`, `app/data/identity/mapping.py`) are owned by one agent at a time.
- Every agent commit references the implementation-plan step number it is executing.

## Non-Goals / Do-Not-Do

This product is extremely scope-creep prone. The following are explicitly out of scope and remain so unless David revises this list:

- Authentication, multi-user accounts, billing, roles
- Public API or SaaS exposure
- Mobile app
- Real-time draft mode (live drafts as they happen)
- Mock draft simulator
- League chat / message integration
- Trade chat assistant
- Social features (followers, comments, sharing)
- Push notifications
- DFS optimizer
- Best-ball-specific tooling
- Public leaderboards or premium tiers
- "AI assistant chatbot" surface that bypasses the structured decision-card layer

## Assumptions

- The canonical GitHub remote is `https://github.com/davidtleess/dynasty-genius`. Local canonical checkout: `dynasty-genius` on `main`. Other local clones / worktrees feed back via PR. All paths in code and docs are repo-relative.
- Paid subscriptions for PFF, PlayerProfiler, and KTC are available. Credentials, cookies, and session files are stored outside the repo and never committed.
- Automated scraping is acceptable, but every scraper isolates behind cached snapshots, parser tests, and a manual-export fallback path.
- Implementation work is divided among multiple developer agents; each agent reads system-design + the relevant data-source-contracts and validation-gates excerpts before executing a step.
- No frontend work begins before the unified Player Value Object and the backtest harness are live.
