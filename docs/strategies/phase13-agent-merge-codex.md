# Phase 13 Agent Merge — Codex

Source reports:

- `docs/strategies/Phase13-round2-research.md`
- `docs/strategies/Phase13-Round2-Dynasty Genius Framework Review.md`

Governance inputs read:

- `docs/governance/02-agent-operating-loop.md`
- `docs/governance/00-product-constitution.md`
- `docs/governance/01-north-star-architecture.md`
- `AGENT_SYNC.md`
- `docs/agent-ledger/2026-05-15.md`

This is an independent research synthesis. It does not use the existing Phase 13 spec as source material.

## 1. Executive Recommendation

Phase 13 should be sequenced as:

1. **13.1 Identity Resolution Audit**
2. **13.2 Engine A Draft-Capital Step-Function Bake-Off**
3. **13.3 TE Remodel Step 0**

Identity resolution is the first hard gate because Phase 13 introduces the highest-risk failure mode in the system: silent joins between collegiate/PFF rows and the wrong Dynasty Genius player identity. That failure is worse than missing data because it contaminates training rows without triggering a caveat.

Draft-capital work can begin as offline research/design in parallel with identity audit, but no Engine A feature change should be promoted until the historical cohort identity snapshot is locked. TE remodel work should not ingest PFF or alignment data until the TE cohort identity gate passes.

The final Phase 13 shape should be a disciplined foundation phase, not a broad model rewrite:

- build auditable identity coverage and override infrastructure;
- backtest candidate draft-capital encodings against the current Engine A baseline;
- prove TE data feasibility and archetype labeling quality before any TE model promotion;
- keep TE `EXPERIMENTAL`;
- keep market data out of Engine A and Engine B;
- keep DVS out of scope.

## 2. Evidence Table

| Claim | Source Document | Confidence | Implementation Implication |
|---|---|---:|---|
| Identity audit must gate PFF/TE ingestion because bad joins silently corrupt training rows. | Both reports | High | 13.1 must precede any PFF TE feature materialization. Unresolved rows go to review, not training. |
| Draft capital is nonlinear and position-specific. | Both reports | High | Evaluate bucketed, log-decay, and monotonic/isotonic transforms instead of relying on a smooth raw pick feature. |
| QB draft capital has the steepest early cliff. | Both reports | Medium-high | Candidate QB bins should isolate premium Round 1 / top-15 capital, but final thresholds must be learned or validated rather than hardcoded permanently. |
| WR viability extends deeper than RB, approximately into the pick-75 range in the Framework Review. | Framework Review | Medium | Include a WR-specific candidate bin around 33-75; require sensitivity testing before adoption. |
| RB value drops sharply after Day 2 / Round 3 depending on hit definition. | Both reports | Medium-high | RB bins should test 1-32, 33-64, 65-105, 106+ or close variants. Do not treat RB and WR bins as identical by default. |
| TE draft-capital evidence is thin and should not support fine-grained breakpoint fitting. | Phase13-round2-research.md | High | TE draft capital should use broad shrinkage or R1-vs-rest priors; avoid overfitting TE bins. |
| TE model failure is likely role heterogeneity: move/big-slot receivers and inline blockers are pooled. | Both reports | High | Phase 13 TE work should start with archetype labeling and feature feasibility, not immediate model promotion. |
| Objective TE alignment/rate fields are more appropriate than subjective PFF grades. | Framework Review, reinforced by governance | High | Use routes, snaps, slot/wide/inline rates, YPRR, TPRR-like rates where available. Treat PFF grades as diagnostic only unless explicitly approved later. |
| PFF Premium likely requires manual CSV export; API access is enterprise/team-tier. | Phase13-round2-research.md | Medium | Phase 13 should plan for CSV fixtures, provenance, manual export tax, and license-safe private storage. |
| Public fallbacks cannot fully replace PFF alignment data for college TE prospects. | Phase13-round2-research.md | High | cfbfastR/CFBD/PlayerProfiler can supply production/athletic context, but not reliable slot-inline-wide alignment. |
| Active NFL TE alignment can use nflverse participation/personnel proxies. | Phase13-round2-research.md | Medium | This can support diagnostics for active TEs, but should not leak collegiate features into Engine B retraining. |
| `ff_playerids` is the primary crosswalk candidate for Sleeper/GSIS/PFF/PFR IDs. | Both reports | High | Build identity audit around source-ID mapping rather than adapter-local matching. |
| Fuzzy matching must never silently resolve production identity. | Both reports and governance | High | Fuzzy candidates may only populate review queues with top candidates and disambiguating fields. |
| `prospect_alias_bridge.json` exists but may be too narrow for Phase 13 source-ID expansion. | Framework Review; Phase13-round2-research.md implies broader override registry | Medium-high | Final spec should decide whether to extend the bridge or create a broader identity override registry. Codex recommendation: broader source-ID override registry. |
| Less than 2% mapping loss / 98% coverage for 2018-2025 drafted TE cohort is the proposed hard gate. | Framework Review | Medium | Good candidate acceptance gate, but denominator policy for pure inline blockers needs David approval. |
| 10+ draft classes are needed for draft-capital backtesting. | Phase13-round2-research.md | High | 13.2 must use historical class-based validation, not a single pooled split. |
| LOOCV by draft class and intra-class rank correlation are better than global correlation for rookie draft decisions. | Framework Review | High | Evaluate lift using leave-one-class-out and within-class Kendall/Spearman, with confidence intervals where feasible. |
| Hierarchical priors are useful but may exceed current sklearn/Ridge scope. | Both, conflict on readiness | Medium | Defer hierarchical modeling or keep as research-only baseline unless David approves added complexity. |

## 3. Conflicts And Resolutions

| Conflict | Report A Position | Report B Position | Codex Resolution |
|---|---|---|---|
| Phase ordering | 3C first, then 3B Step 0; 3A can design offline but promotion waits on identity coverage. | 3A and 3C can proceed in parallel, then 3B after less than 2% mapping loss. | Use a gated parallel model: 13.1 identity is first implementation gate; 13.2 draft-capital design can proceed but promotion waits on locked historical identity; 13.3 PFF/TE ingestion waits for TE identity gate. |
| Canonical ID | Treats `gsis_id` as canonical primary key, consistent with nflverse. | Refers to Dynasty Genius canonical `player_id`, with mappings through Sleeper/GSIS/PFF. | North Star wins: Dynasty Genius owns canonical `player_id`; `gsis_id` is the strongest NFL bridge key, not the application-level canonical ID. |
| Draft-capital transform | Recommends monotonic isotonic/piecewise-constant with shrinkage, plus bucket/log baselines. | Recommends ordinal categorical bins and rejects hierarchical priors/splines. | Bake off candidates. Do not choose the transform before validation. Candidate set: current baseline, log-decay, bucketed categorical, monotonic/isotonic step. Hierarchical prior is deferred unless needed for TE stability. |
| Position thresholds | Gives broad bins: QB 1-32/33-64/65+, RB 1-32/33-64/65-105/106+, WR 1-32/33-64/65-105/106+, TE R1/rest. | Gives sharper thresholds: QB top 15, WR to pick 75, RB after R2/R3 cliffs. | Use thresholds as candidate priors only. Include QB top-15 and WR pick-75 variants in bake-off; final breakpoints must be validated and sensitivity-tested. |
| TE model action | Label archetypes first; no model retraining/promotion in Phase 13. | Adds `slot_wide_route_pct` and `blocking_first` sample weight into Engine A after 3C, with lock-removal conditions. | Phase 13 should stop at Step 0 unless David approves implementation after feasibility results. If implemented, add features only behind explicit backtest gates; do not remove TE experimental lock in Phase 13 by default. |
| PFF grades | Allows receiving/run-block/pass-block grades as potentially predictive context. | Prohibits subjective PFF grades from feature matrix. | Governance-safe resolution: objective PFF participation/rate fields are candidates; PFF grades are diagnostic/model-card context only until separately approved. |
| Inline blockers in coverage denominator | Keeps all drafted TEs in denominator by default. | Raises exception to exclude pure inline blockers with fewer than 10 college receptions. | Keep all drafted TEs in the identity denominator. If David wants a fantasy-relevance denominator, report it as a secondary metric, not the gate. |
| `prospect_alias_bridge.json` expansion | Suggests override registry mirroring nflverse-player JSON overrides. | Suggests structurally expanding `app/data/prospect_alias_bridge.json` with `pff_id` arrays. | Create/approve a broader source-ID override registry. The existing prospect alias bridge can seed it, but it should not become the universal identity layer. |
| Divergence ledger terminology | Uses coverage matrix, review queue ledger, override registry, failure-mode report. | Calls identity failures a Divergence Ledger / Null-Value Log. | Avoid overloading Phase 12 divergence ledger. Use `identity_review_queue`, `identity_coverage_matrix`, and `identity_failure_report`; link to divergence only if later market overlay gaps are involved. |

## 4. Phase 13 Workstreams And Ordering

### 13.1 Identity Resolution Audit

Objective: prove that Dynasty Genius can join active, historical, prospect, and PFF/college rows without silent corruption.

Required outputs:

- identity contract documenting canonical `player_id` and source-ID columns;
- deterministic source-ID cascade;
- coverage matrix by cohort and source;
- manual review queue for ambiguous/unresolved rows;
- override registry with author, timestamp, reason, and source fields;
- duplicate and row-count preservation checks;
- historical identity snapshot lock for backtests.

Recommended cohort gates:

- David roster and active high-value players: 100% resolved or explicitly queued;
- active NFL/Sleeper cohort: at least 99% deterministic coverage;
- historical backtest cohort: at least 95% coverage;
- 2018-2025 drafted TE cohort: at least 98% resolved for PFF/college ingestion, with all misses documented.

### 13.2 Engine A Draft-Capital Step-Function Bake-Off

Objective: replace or confirm the current draft-capital representation using class-based validation.

Candidate transforms:

- current Engine A baseline;
- smooth log-decay baseline;
- position-specific bucketed categorical bins;
- monotonic/isotonic step transform fit per position;
- optional interaction terms with validated college efficiency metrics, tested separately.

Recommended candidate bins:

- QB: top 15, 16-32, 33-64, 65+; also test 1-32, 33-64, 65+ for simplicity.
- RB: 1-32, 33-64, 65-105, 106+, UDFA where available.
- WR: 1-32, 33-75, 76-105, 106+; also test 33-64 / 65-105 split.
- TE: 1-32 vs 33+ or broad shrinkage only.

Validation:

- leave-one-draft-class-out validation;
- within-class Kendall tau / Spearman rank lift over baseline;
- calibration/Brier or bucket-level reliability where target framing supports it;
- bootstrap confidence intervals;
- breakpoint sensitivity under pick jitter;
- model card update if any feature is promoted.

### 13.3 TE Remodel Step 0

Objective: determine whether TE role heterogeneity can be measured cleanly enough to justify a later model change.

Step 0 outputs:

- PFF manual CSV feasibility report: fields, seasons, costs, license boundaries, repeatability;
- TE identity coverage report for 2018-2025 drafted cohort;
- TE archetype rubric v0;
- sample labeled cohort;
- public fallback comparison: CFBD/cfbfastR production, PlayerProfiler/athletic metrics, nflverse participation for active NFL TEs;
- no TE promotion.

Candidate archetypes:

- receiving specialist / move TE;
- big-slot hybrid;
- in-line receiving TE;
- blocking-first / TE2.

Candidate objective fields:

- routes run;
- route participation;
- slot snaps/routes;
- wide snaps/routes;
- inline snaps/routes;
- slot plus wide route percentage;
- inline blocking rate;
- YPRR;
- targets per route run if available;
- RYPTPA / normalized receiving usage;
- drop/contested/YAC rates as secondary context.

PFF grades should remain diagnostic context only unless a future spec approves them as features after validation.

## 5. Explicit Out-Of-Scope Items

- DVS implementation or promotion.
- Market-derived fields as Engine A or Engine B model inputs.
- KTC/FantasyCalc/ADP/consensus in training tables.
- Silent fuzzy identity matching.
- Adapter-local production identity logic.
- TE promotion out of `EXPERIMENTAL`.
- Engine B retraining from collegiate alignment data.
- Per-archetype TE submodels in Phase 13.
- Subjective PFF grades as model features.
- CFB Reference / Sports Reference as ML training features without explicit licensing approval.
- Hardcoded age cliffs as model features.
- RAS as positive model lift unless separately validated.
- Permanent hardcoded draft-capital breakpoints before backtest validation.

## 6. Open Decisions For David

1. Should the Phase 13 identity gate use 98% coverage for the 2018-2025 drafted TE cohort, or a different threshold?
2. Should pure inline blockers remain in the primary identity denominator? Codex recommendation: yes; report a fantasy-relevance denominator only as a secondary view.
3. Should the existing `prospect_alias_bridge.json` be expanded, or should Phase 13 create a broader source-ID override registry? Codex recommendation: broader registry.
4. Is manual PFF CSV export acceptable for Phase 13 Step 0, including its operational tax and private-data handling limits?
5. Are PFF subjective grades fully prohibited as features, or allowed as diagnostic-only model-card context? Codex recommendation: diagnostic-only.
6. Should 13.2 implement draft-capital changes in Phase 13 if the bake-off passes, or should Phase 13 stop at a validation report?
7. Should `slot_wide_route_pct` and `blocking_first` be allowed into Engine A during Phase 13 after Step 0, or should Phase 13 only produce a TE remodel spec for a later phase?
8. Who owns manual identity review decisions: David only, or a named reviewer role?
9. What historical draft-class window should be authoritative for 13.2: 10 classes, 15 classes, or all available classes with recency weighting?
10. Should hierarchical draft-capital priors remain deferred, or be included as a research-only benchmark for TE?

## 7. Risks And Failure Modes

### Identity Risks

- Incorrect identity joins silently contaminate training rows.
- Prospect-to-veteran transitions can duplicate players if historical prospect aliases do not resolve to active `player_id`.
- Short-career, retired, Day-3, UDFA, and position-change players are likely to drive missing IDs.
- Expanding `prospect_alias_bridge.json` beyond its original role may create a brittle, overloaded file unless schema ownership is explicit.
- Fuzzy review candidates can become accidental production matches if staging/production boundaries are unclear.

### Draft-Capital Risks

- Bucket boundaries can overfit historical noise.
- Adjacent picks near a threshold can receive artificial value differences.
- Draft capital partly measures opportunity assignment, not pure talent.
- Recency effects may matter because RB draft economics and WR passing environments have changed.
- TE sample size is too small for fine-grained step estimation.

### TE Remodel Risks

- College alignment may not translate to NFL usage.
- PFF manual export may be incomplete, costly, or license-constrained.
- Public fallbacks lack true college alignment and blocking equivalents.
- Archetype labels may create a false sense of precision.
- Over-penalizing inline-heavy college players may miss athletes whose NFL teams deploy them differently.
- TE remains inherently noisy; even improved features may not justify promotion.

### Governance Risks

- Treating market prices as validation shortcuts would violate the constitution.
- Using PFF grades as numeric features without explicit approval would blur objective and subjective evidence.
- Moving too quickly from Step 0 feasibility to TE model promotion would overstate trust.

## 8. Proposed Acceptance Criteria

### 13.1 Identity Audit

- Identity contract defines canonical `player_id`, source ID fields, deterministic cascade, review states, and override schema.
- Coverage matrix includes active players, David roster, incoming rookies, historical backtest cohort, and 2018-2025 drafted TE cohort.
- Review queue is append-only or otherwise auditable, with candidate evidence and no silent production fuzzy matches.
- Override registry requires source IDs, author, timestamp, reason, and confidence.
- CI or contract tests fail if unresolved PFF/college rows enter training materialization.
- Duplicate tests assert no two production records share non-null `player_id`, `gsis_id`, or `sleeper_id` where uniqueness is required.
- Historical identity snapshots are locked per backtest run.

### 13.2 Draft-Capital Bake-Off

- Candidate transforms are evaluated against current Engine A using leave-one-draft-class-out validation.
- Results report per-position within-class rank correlation, calibration, and confidence intervals.
- Candidate breakpoints are documented as learned/validated artifacts, not hidden constants.
- Sensitivity analysis shows stable breakpoints under reasonable pick jitter.
- No promoted feature uses market data.
- Model card and validation artifact are updated before any Engine A change is considered production-ready.

### 13.3 TE Remodel Step 0

- PFF field availability, manual export process, license boundaries, and coverage limitations are documented.
- TE identity coverage passes David-approved threshold before PFF-derived rows are materialized.
- Archetype rubric is versioned and uses objective alignment/usage thresholds.
- Labeled sample includes receiving specialists, big-slot hybrids, in-line receiving TEs, and blocking-first TEs.
- PFF grades are absent from training feature candidates unless separately approved.
- Engine B artifacts remain untouched.
- TE remains `EXPERIMENTAL` at the end of Phase 13 unless David explicitly approves a later promotion spec and backtest gate.
