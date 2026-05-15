# Dynasty Genius — Phase 13 Research Brief (Merged)
*Lanes: 3A Engine A Draft-Capital Step Function · 3B TE Remodel · 3C Identity Resolution Audit*
*Sources merged: "Deep Research Phase 13," "Dynasty Genius Framework Review Phase 13.md," "Phase-13-Research-Brief.md"*
*Merged: 2026-05-15. Status: Research brief only. No implementation spec. No code.*

## 1. Executive Recommendation

Phase 13 should be run as a governed research-to-spec sequence, not as immediate model implementation. The correct order is:

1. **13.1 Identity Resolution Audit (3C)**
2. **13.2 Engine A Draft-Capital Step Function (3A)**
3. **13.3 TE Remodel Step 0 (3B data feasibility and archetype diagnosis)**

3C is a hard gate for 3B. PFF collegiate alignment data is only useful if the PFF prospect rows map cleanly into Dynasty Genius identity. Bad joins are worse than null features because they silently attach one prospect's role profile to another player's training row.

3A can proceed in parallel as research and offline backtesting because it depends primarily on draft metadata already present in the rookie pipeline. Promotion of any Engine A change should still wait for identity coverage checks on the historical backtest cohort.

Keep Phase 13 split into subphases under one umbrella:

| Subphase | Purpose | Gate |
|---|---|---|
| 13.1 | Identity bridge audit, coverage matrix, review queue, override registry | Required before PFF ingestion or TE model work |
| 13.2 | Draft-capital transform bake-off for Engine A | Must beat current linear/log baseline on held-out draft classes |
| 13.3 | TE role-remodel feasibility: PFF/manual CSV, archetype labels, public fallback path | Requires 13.1 coverage gate and separate spec approval |

Non-negotiables:

- Market data remains overlay-only.
- `dynasty_value_score` remains deferred.
- TE remains `EXPERIMENTAL`.
- No silent fuzzy matching.
- No new PFF, CFBD, PlayerProfiler, or public-source fields enter training tables before identity coverage gates pass.
- This brief does not authorize production model retraining.

## 2. Key Merge Resolutions

The two reports mostly agree on direction but differ in several important details. The merged position is:

| Topic | Report A: Deep Research | Report B: Framework Review | Merged Resolution |
|---|---|---|---|
| Phase order | 3C -> 3B Step 0 -> 3A/3B | 3A and 3C parallel, then 3B | 3C is first/gating for 3B. 3A may run offline in parallel, but no promotion before historical identity coverage is known. |
| Canonical ID | `gsis_id` as primary key | Sleeper/ff_playerids bridge framing | Dynasty's internal `player_id` remains canonical. `gsis_id` is the strongest NFL bridge key, not the app-level canonical ID. |
| Fuzzy matching | Fuzzy candidates may enter review queue | Fuzzy matching forbidden | Fuzzy scoring is allowed only in offline review staging. It can propose candidates but can never auto-resolve production identity. |
| Draft-capital transform | Isotonic / piecewise with bucket baseline | Ordinal categorical bins | Bake off bucketed bins, log-decay, and monotonic/isotonic step transforms. Start with buckets for interpretability; do not hardcode final breakpoints without backtest evidence. |
| PFF grades | Candidate predictive inputs | Prohibited as subjective grades | Objective PFF participation/rate fields are the target. PFF grades may be diagnostic/context only until separately approved and validated. |
| TE implementation | Archetype labels before model retrain | Continuous slot/wide feature + blocking flag | Start with archetype labeling and diagnostics. Do not split into separate TE models in Phase 13; evaluate role features/flags only after coverage gates. |

## 3. 3A Findings: Engine A Draft-Capital Step Function

### Evidence Summary

Both reports agree that the current smooth treatment of draft capital is too weak. NFL draft capital is not merely a talent proxy; it also captures organizational commitment, opportunity runway, contract structure, and patience. The relationship with fantasy hit rates is nonlinear and position-dependent.

The strongest repeated pattern:

- **QB:** Round 1 is a severe breakpoint. Round 2 and later QBs have much lower fantasy-hit odds, especially for Superflex starter stability. The Early R1 / Late R1 split (pick ~1–15 vs. 16–32) is meaningful for QB specifically — franchise viability collapses after the early first round.
- **RB:** Round 1 and Round 2 carry immediate opportunity value. The Day 2 to Day 3 drop is steep, but recent NFL economics may make RB breakpoints more volatile than QB/WR.
- **WR:** Round 1 matters, but WR viability extends deeper into Round 2 and parts of Round 3 than RB or QB. WR hit rates remain statistically relevant through pick ~75.
- **TE:** Draft capital is directionally useful but too sparse for fine-grained buckets. Round 1 vs. non-Round 1 may be the only stable split until role data is added.

**Hit-rate data by pick range (synthesized, 2000–2023):**

| Draft Range | QB Top-12 | RB Top-12 | WR Top-24 | TE Top-12 |
|---|---|---|---|---|
| Picks 1–15 (Early R1) | ~59% | ~67% | ~49% | ~91% |
| Picks 16–32 (Late R1) | ~59% | ~67% | ~49% | ~91% |
| Picks 33–64 (Round 2) | ~14% | ~33% | ~32% | ~35% |
| Picks 65–100 (Round 3) | ~0% | ~25% | ~18% | ~22% |
| Picks 101+ (Day 3 / UDFA) | <7% | <7% | <3% | <10% |

Note: Round 1 QB hit rates appear undifferentiated by early vs. late because the sample blends Early/Late. Internal breakpoint analysis consistently shows the early-R1 QB franchise ceiling is materially higher — treat the R1 aggregate as a conservative floor.

Research sources cited across the reports include Dynasty Nerds, The Fantasy Footballers, Campus2Canton/Peter Howard data, Last Word On Sports, PFF historical hit-rate work, Fantasy Life rookie-model framing, and academic draft-value work from CMU/arXiv.

### Recommended Modeling Approach

Run a controlled candidate bake-off rather than picking one encoding upfront:

1. **Current baseline:** raw pick / current Engine A representation.
2. **Log-decay baseline:** `1 / log(pick)` or equivalent smooth decay.
3. **Bucketed categorical bins:** interpretable position-specific buckets.
4. **Monotonic step / isotonic transform:** learns step-like structure subject to monotonicity.

Recommended starting bins for the bake-off:

| Position | Candidate Breakpoints | Rationale |
|---|---|---|
| QB | 1–15, 16–32, 33–64, 65+ | Early-R1 franchise window is meaningfully different from Late-R1 |
| RB | 1–32, 33–64, 65–105, 106+ | Day-2/Day-3 cliff is steep; UDFA merged with 106+ initially |
| WR | 1–32, 33–75, 76–105, 106+ | WR viability extends to ~pick 75; R2/R3 gap is most consistent secondary cliff |
| TE | 1–32, 33+ | Evidence only supports R1 vs. non-R1 split until role features are added |

Do not hardcode these as permanent model law. They are candidate transforms for backtesting. Breakpoints must be re-fit from the backtest cohort at each model refresh.

### Validation Gates

Before any Engine A promotion:

- Use leave-one-draft-class-out or rolling held-out draft-class validation.
- Evaluate within-draft-class rank correlation, not just global rank correlation.
- Compare against current baseline and log-decay baseline.
- Report Kendall tau / Spearman, calibration, Brier or comparable probability metrics if classification labels are used, and bootstrap confidence intervals.
- Run sensitivity checks around breakpoint stability.
- Refresh model card and Trust Surface artifacts for any promoted change.

### Risks and Counterarguments

- Draft capital partly measures opportunity, not pure talent.
- Recent RB economics may make old first-round RB hit rates less stable.
- Rigid buckets can create artificial differences between adjacent picks.
- Overfitting to rare outliers, especially late-round WR hits, is a real risk.

Mitigation: treat draft-capital transforms as priors, not verdicts. Allow production/efficiency signals to challenge the prior, but require backtested lift before promotion.

## 4. 3B Findings: TE Remodel

### Why The Current TE Model Fails

The reports agree that TE is not merely underperforming because of low sample size. The deeper issue is role heterogeneity:

- Inline blockers and receiving specialists are labeled as the same position.
- NFL teams draft some TEs for real-football blocking utility, not fantasy target earning.
- TE development curves are slow and target volume is role-dependent.
- Small yearly cohorts make noisy labels more damaging.

This explains why the current TE model remains `EXPERIMENTAL` and why simply adding more generic TE rows is unlikely to fix the issue.

### Recommended TE Archetype Framework

Phase 13 should label TE archetypes before any remodel:

| Archetype | Signal thresholds | Dynasty ceiling |
|---|---|---|
| Move / receiving specialist | ≥55% receiving snaps, slot share ≥30%, run-block grade typically <65 | High |
| Inline receiving TE | ≥55% inline alignment, receiving grade ≥75, run-block grade 60–80 | High (Kelce/Kittle/Andrews profile) |
| Inline blocker / TE2 | ≥70% inline, run-block grade ≥75, route participation low | Low — triggers `blocking_first` sample weight |
| Big-slot hybrid | Slot share >40%, lighter frame, designed-target rate high | High (Loveland/Fannin profile) |

**Blocking-first flag threshold:** ≥60% inline blocking rate in the final collegiate season → triggers a `blocking_first` boolean used as a sample weight penalizing projected ceiling, not a hard exclusion from training (preserves the rows; avoids survivorship bias).

**Receiving specialist flag:** Combined slot + wide route rate ≥40% → Archetype A/D range.

Archetypes should start as diagnostic labels and conditioning variables, not separate models. Separate TE sub-models are deferred because the sample size (~30–50 players per class × 7–8 classes) is too small for independent Ridge regularization.

### PFF Step 0 Feasibility

PFF collegiate data is the preferred source for TE role segmentation because it can expose objective participation and alignment fields:

- routes run
- slot snaps / slot route share
- inline snaps / inline route share
- wide snaps
- targets
- YPRR
- YAC per reception
- contested-target/catch context
- drop rate
- run-blocking/pass-blocking participation context

Important resolution: **objective participation and rate fields are Phase 13 candidates; PFF grades are not automatically model features.** Receiving grade, run-block grade, or pass-block grade may be used in a research report or model-card diagnosis, but they should not enter Engine A until separately approved and backtested. This preserves the framework review's concern about subjective vendor grading while retaining the deep report's useful PFF field inventory.

Operational caveat: individual PFF subscriptions likely imply manual CSV export, not stable API ingestion. Treat PFF as a manual-export / fixture-style source unless a governed data license exists.

### Public Fallback Options

If PFF is not feasible:

- **cfbfastR / CollegeFootballData:** college production, team context, play-by-play-derived rates. Good for production; weak for TE alignment.
- **PlayerProfiler:** athletic and production context such as dominator, College YPR, catch radius, speed/agility/burst metrics. Useful context; no alignment.
- **nflverse participation:** strong for active NFL TE deployment and 11/12 personnel context, but not a direct college-prospect alignment source.
- **Sports Reference / CFB Reference:** useful for spot checks only unless licensing permits ML training use.

### Validation Gates

Before any TE remodel training:

- 13.1 identity coverage gate must pass.
- TE prospect cohort must be mapped from PFF/college source to internal `player_id`.
- Archetype labels must be versioned and auditable.
- Baseline TE failure mode must be documented in model card artifacts.
- Any new TE features must pass leakage checks and backtest gates.

Before TE can leave `EXPERIMENTAL`:

- It must pass the same backtest/promotion discipline as other positions.
- It must demonstrate improved rank correlation and calibration on held-out cohorts.
- It must show that highly drafted inline blockers are not falsely elevated while receiving specialists remain appropriately valued.

### Risks and Counterarguments

- College TE role does not always translate to NFL role.
- PFF data coverage begins around the modern charting era, limiting historical sample depth.
- Vendor grades can smuggle subjective judgment into a quantitative layer.
- Archetype labels can become subjective unless thresholds and overrides are versioned.
- TE may remain intrinsically harder to forecast than QB/RB/WR even after role segmentation.

## 5. 3C Findings: Identity Resolution Audit

### Required ID Design

Dynasty Genius owns the canonical internal `player_id`. Source IDs live in the identity layer and must not be invented or resolved inside individual adapters.

Use `gsis_id` as the strongest NFL bridge key where available, because nflverse and ff_playerids orient heavily around it. But do not replace the internal canonical ID with `gsis_id`, especially for pre-draft prospects that do not yet have NFL identifiers.

Required source IDs to track where available:

- internal `player_id`
- `sleeper_id`
- `gsis_id`
- `pff_id`
- `pfr_id`
- `cfbref_id`
- `espn_id`
- `yahoo_id`
- `sportradar_id`
- `fantasy_data_id`
- source-specific PFF college player ID if distinct from NFL PFF ID

### Deterministic Matching Cascade

Use deterministic matching first:

1. Direct ID joins via existing bridge tables / nflverse `ff_playerids`.
2. Sleeper payload pass-through for active players carrying `gsis_id` or related IDs.
3. Composite `(name, DOB, position, draft year)`.
4. Composite `(name, college, position, draft year)` for pre-NFL prospects.
5. Review queue for all unresolved or ambiguous cases.

Fuzzy scoring may be used only to propose review candidates in staging. It must never auto-resolve a production identity mapping.

### Coverage Thresholds

Recommended gates:

| Cohort | Threshold |
|---|---|
| David roster / active decision set | 100% resolved or explicitly queued |
| Active NFL cohort | >=99% deterministic `player_id` to Sleeper/NFL bridge coverage |
| Historical backtest cohort | >=95% primary ID coverage, with gaps reported by draft class and position |
| TE 2014-2025 PFF candidate cohort | >=98% deterministic or reviewed resolution before PFF-derived training tables |

The framework review proposes a `<2%` loss-rate gate for drafted TEs. Keep that as the 3B hard gate, but do not exclude pure inline blockers from the denominator by default. Excluding them can hide identity failure. If David chooses to exclude any cohort, document it as a product decision and report both raw and filtered coverage.

### Audit Artifacts

13.1 should produce:

- Coverage matrix by source and cohort.
- Review queue ledger for ambiguous matches.
- Override registry with author, timestamp, reason, and source evidence.
- Do-not-merge list for rejected candidates.
- Null-value / missing-cohort report.
- Duplicate-ID report.
- Backtest identity snapshot lock for reproducibility.
- Identity contract for adapters.

### Required Checks

- No two production players share non-null `gsis_id`.
- No two production players share non-null `sleeper_id`.
- All active roster players have a resolved ID or queued review item.
- PFF rows cannot enter training tables unless identity coverage gates pass.
- Manual overrides must be versioned and auditable.
- Historical backtest identity snapshots must not drift silently after reruns.

## 6. Recommended Phase 13 Scope

### In Scope

- Identity audit script/spec and coverage matrix.
- Identity review queue and override registry.
- Deterministic ID cascade using Sleeper, nflverse/ff_playerids, and existing bridge files.
- Engine A draft-capital transform bake-off.
- TE PFF Step 0 feasibility: field availability, manual export process, license constraints, historical coverage, and mapping coverage.
- TE archetype labeling rubric.
- Public fallback path for TE role proxies.
- Model-card and Trust Surface updates for any later approved changes.

### Out Of Scope

- DVS implementation.
- Market data in Engine A or Engine B features.
- Silent fuzzy matching.
- TE promotion out of `EXPERIMENTAL`.
- Production model artifact replacement without a governed backtest/promotion path.
- Engine B retraining from collegiate TE features.
- PFF subjective grades as training features without separate approval.

### Explicitly Deferred

- Separate TE sub-models by archetype.
- Bayesian hierarchical draft-capital priors as production code.
- SIS or enterprise charting subscriptions.
- Sports Reference / CFB Reference as training features without licensing clarity.
- Any global frontend polish beyond Trust Surface artifact exposure.

## 7. Implementation Implications

Likely repo surfaces for later specs:

- Identity bridge package or module.
- `app/data/prospect_alias_bridge.json` or successor override registry.
- Sleeper / nflverse / PFF export adapters.
- Engine A training table builder.
- Training CSV leakage guard extensions.
- Backtest harness or Engine A validation harness.
- Model card generator and Trust Surface artifacts.
- Contract tests for identity coverage, duplicate IDs, adapter boundaries, and training-table gate failures.

Do not let any adapter own identity resolution. Adapters should emit source-native IDs and normalized rows; identity joins belong in the identity layer.

## 8. Open Questions For David

1. **PFF ingestion mechanism.** Is manual PFF Premium CSV export acceptable for Phase 13 Step 0, or should PFF B2B/API access be evaluated before spec work? This determines whether PFF ingestion is a one-time build or an ongoing operational dependency.
2. **Coverage threshold enforcement.** Should the <2% TE mapping loss rate be a hard CI gate or a soft warning? Should thresholds vary by active vs. historical vs. prospect cohorts (as the coverage table suggests)?
3. **Review queue ownership.** Who approves ambiguous identity matches — David only, or can agent-generated candidate lists be submitted for David's final approval? This determines throughput capacity.
4. **Inline blockers in the denominator.** Should pure inline blockers (athletes with <10 career collegiate receptions) be excluded from the TE identity denominator? Recommendation: no by default — report both raw and filtered coverage if needed. Exclusion can mask mapping gaps.
5. **Draft-capital transform priority.** Should Phase 13 start with interpretable bucket bins (faster, simpler) or run the full isotonic/monotonic bake-off from the start?
6. **PFF grades policy.** Should PFF grades remain diagnostic-only by standing policy, or should a later experiment test them as features behind an explicit governance approval?
7. **Archetype rubric ownership.** Should the historical TE cohort (2014–2025) be labeled manually by David, or should a rule-based labeler (slot%/inline% thresholds) be built and submitted for David's review?

## 9. Source Bibliography

Sources cited across the two reports:

- Dynasty Nerds, "How NFL Draft Capital Predicts Success." https://www.dynastynerds.com/analytics/nfl-draft-capital-fantasy-football/
- The Fantasy Footballers, "Draft Capital & Its Correlation To Early-Career Fantasy Production." https://www.thefantasyfootballers.com/articles/draft-capital-its-correlation-to-early-career-fantasy-production/
- Campus2Canton, "Importance of Draft Round When Evaluating WRs." https://campus2canton.com/importance-of-draft-round-when-evaluating-wrs/
- Last Word On Sports, "Running Back Hit Rates by NFL Draft Round." https://lastwordonsports.com/nfl/2024/04/12/running-back-hit-rates-by-nfl-draft-round/
- Last Word On Sports, "Wide Receiver Hit Rates by Draft Position." https://lastwordonsports.com/nfl/2024/04/09/wide-receiver-hit-rates-by-draft-position/
- Last Word On Sports, "Why Draft Capital Is the Most Important Thing In Dynasty Leagues." https://lastwordonsports.com/nfl/2023/03/30/why-draft-capital-is-the-most-important-thing-in-dynasty-leagues/
- PFF, "What historical hit rates reveal about positional success." https://www.pff.com/news/draft-what-historical-hit-rates-reveal-about-positional-success
- Fantasy Life, "NFL Draft Capital Is King For Predicting Fantasy Football Success." https://www.fantasylife.com/articles/dynasty/nfl-draft-capital-is-king-for-predicting-fantasy-football-success-is-puka-nacua-an-outlier
- PFF, "Scouting tight ends using PFF+." https://www.pff.com/news/draft-2026-nfl-draft-scouting-tight-ends-pff
- PFF, "Fantasy Football: Rookie tight end prospect model." https://www.pff.com/news/draft-fantasy-football-rookie-tight-end-prospect-model
- The Fantasy Footballers, "Dynasty Range of Outcomes: 2024 TE Class." https://www.thefantasyfootballers.com/dynasty/dynasty-range-of-outcomes-2024-tight-end-class/
- BrainyBallers, "Tight Ends and PFF Receiving Grade Predictive Insights." https://brainyballers.com/tight-ends-can-pffs-receiving-grades-help-predict-nfl-success/
- PlayerProfiler, "Finding Rookie Breakout TEs Using PlayerProfiler's Advanced Metrics." https://www.playerprofiler.com/article/albert-okwuegbunam-advanced-stats-metrics-analytics-profile-2/
- PFF, "PFF Signature Statistics - a glossary." https://www.pff.com/news/pro-pff-signature-statistics-a-glossary
- PFF, "College Football Usage and Production Report." https://www.pff.com/news/college-football-usage-production-report-week-1-2025
- PFF / Teamworks B2B data. https://b2b.pff.com/data
- nflreadr, `load_ff_playerids` documentation. https://nflreadr.nflverse.com/reference/load_ff_playerids.html
- nflreadr ff player IDs dictionary. https://nflreadr.nflverse.com/articles/dictionary_ff_playerids.html
- nflverse-players contributing documentation. https://github.com/nflverse/nflverse-players/blob/master/.github/CONTRIBUTING.md
- CRAN nflreadr reference manual. https://cran.r-project.org/web/packages/nflreadr/refman/nflreadr.html
- CRAN nflfastR package documentation. https://cran.r-project.org/web/packages/nflfastR/nflfastR.pdf
- Sleeper API documentation. https://docs.sleeper.com/
- cfbfastR documentation. https://cfbfastr.sportsdataverse.org/
- Sports Reference Data Use Policy. https://www.sports-reference.com/data_use.html
- Robinson, "Grinding the Bayes: A Hierarchical Modeling Approach to Predicting the NFL Draft." https://www.stat.cmu.edu/cmsac/conference/2020/assets/pdf/Robinson.pdf
- R `isoreg` documentation. https://rdrr.io/r/stats/isoreg.html
- Brill, "Exploring the discrepancy between NFL draft expected value curves and the observed trade market." https://www.stat.cmu.edu/cmsac/conference/2024/assets/pdf/Brill24.pdf
- arXiv, "The Winner of the NFL Draft is Not Necessarily Cursed." https://arxiv.org/html/2411.10400v1
- MDPI, "Optimizing NFL Draft Selections with Machine Learning Classification." https://www.mdpi.com/2673-2688/6/9/221
- Underdog, "How TE Usage in 11- and 12-Personnel Impacts Fantasy Football." https://underblog.underdogfantasy.com/how-te-usage-in-11-and-12-personnel-impacts-fantasy-football-d471ebb60076
- Underdog Network, "This TE Data Predicts Fantasy Football Busts." https://underdognetwork.com/football/analysis/this-te-data-predicts-fantasy-football-busts

All URLs were cited by the source reports as accessed on 2026-05-15 unless otherwise stated.
