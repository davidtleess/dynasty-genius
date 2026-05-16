# Dynasty Genius — Phase 13 Research Brief
*Lanes: 3A Engine A Draft-Capital Step Function · 3B TE Remodel · 3C Identity Resolution Audit*
*Drafted: 2026-05-15. Status: Research brief only. No implementation spec. No code.*

---

## 1. Executive Recommendation

**Sequence: 3C → 3B Step 0 (data feasibility) → 3A (parallel, gated on backtest cohort identity) → 3B model work.** 3C is a hard gate on 3B. Joining PFF collegiate prospect rows to the gsis_id/sleeper_id keyspace without an audited identity layer will silently corrupt any TE training table and is the highest-leverage risk in Phase 13. 3A also depends on 3C because the 10–15 year backtest cohort needed to validate a draft-capital step function spans rosters where `ff_playerids` coverage degrades for retired and short-career players, and where pfr_id/pff_id assignments have historically been the weakest link.

**Phase split.** Recommend three sub-phases under a single Phase 13 umbrella, with explicit promotion gates between them:

- **Phase 13.1 — Identity Audit (3C).** Mandatory. Produces the canonical ID map, coverage report, and review queue. Must reach defined coverage thresholds before any new source touches feature-store tables.
- **Phase 13.2 — Engine A Draft-Capital Step Function research/backtest (3A).** Can proceed in parallel with 13.1 *for design and offline exploration*, but model promotion is gated on 13.1's historical-cohort coverage.
- **Phase 13.3 — TE Remodel (3B).** Begins with PFF Step 0 feasibility *only after* 13.1 hits coverage gates. Public-fallback path is preserved as the contingency.

Reaffirmed governance: market data (KTC, FantasyCalc, ADP, consensus) remains overlay-only; DVS stays unimplemented; TE stays EXPERIMENTAL; RAS stays risk/context; no hardcoded age cliffs; no adapter invents production identity.

---

## 2. 3A Findings: Draft-Capital Step Function

### 2.1 Evidence summary

Public hit-rate studies consistently show that the predictive relationship between NFL draft pick and fantasy outcome is **non-smooth and position-dependent**, not a clean linear or log decay:

- **RB.** The Fantasy Footballers' 2000–2018 study finds Day-1 RBs return an "RB1" rookie season ~25.5% of the time and an "RB2 or better" 55.3% of the time; Day-2 falls to ~10% RB1 / 20% RB2; after Round 3, RB2 rate collapses to ~2.86%. Last Word On Sports' 2011–2021 sample shows a similar pattern with 75% first-round hit rate, ~50% second-round, dropping to ~32% in Round 3 and <5% by Round 7.
- **WR.** Campus2Canton's 2001+ work (sourced from Peter Howard's dataset) shows Round-1 WRs hit top-24 at ~48.7%, Round-2 at ~34%, Round-3 at ~23.4% — a step-like drop between rounds, with another sharp cliff after Round 3 (Last Word: 211 Day-3 WRs since 2011, only 6 hit). PFF's 2025 historical positional study and Dynasty Nerds 2026 work corroborate that Round-1 WRs since 2015 have lower outright "WR1" hit rates than Round-1 RBs in the rookie window, because volume is earned at WR but assigned at RB.
- **QB.** Round-1 QBs hit top-24 ~50% of seasons, top-12 ~31%; Round-2 drops to ~20% / 13%; Round-3+ is essentially zero top-12 seasons in the last six drafts (Gardner Minshew is the cited single top-24 outlier). The QB cliff between Round 1 and Round 2 is the steepest of any position — a critical signal for Superflex.
- **TE.** Sample sizes are too small for confident step estimation: average 1.87 TEs drafted/round historically; first-round TEs have produced ~32% more rookie-window PPG than Round 2 (Fantasy Footballers). PFF's 2025 study notes only ~5 TEs in 7 years exceeded 600 rookie receiving yards. **Treat TE draft-capital effect as directionally bucketed (R1 vs. rest) but do not fit fine-grained breakpoints.**

### 2.2 Where the natural breakpoints appear

Based on the above:
- **QB:** Pick 1–32 (true premium), 33–64 (heavy discount), 65+ (effectively zero historical fantasy hits).
- **RB:** Pick 1–32, 33–64, 65–105, 106+ (Day 3), UDFA. The Day-2/Day-3 step is real but is partially explained by usage volume assignment, not talent — flag as confounded.
- **WR:** Pick 1–32, 33–64, 65–105, 106+. The Round-2/Round-3 gap is the most consistent secondary cliff in the literature.
- **TE:** Pick 1–32 vs. 33+ is the only break with enough evidence to model. Avoid finer slicing.

These are research priors, not pinned hyperparameters; they must be re-fit on the 10–15 year backtest before adoption.

### 2.3 Recommended modeling approach

Recommend a **monotonic isotonic / piecewise-constant transform of overall pick, fit per position, with shrinkage toward a position-prior**, evaluated against bucketed categorical and `1/log(pick)` baselines. Concretely the candidate set:

1. **Bucketed categorical** (R1 / 33–64 / 65–100 / Day-3 / UDFA) — simple, interpretable, but loses within-bucket signal.
2. **Monotonic step / isotonic regression** on overall pick — finds breakpoints empirically subject to monotonicity, naturally produces a step function (PAVA algorithm, well documented in R `isoreg` and scikit-learn). Best fit for the observed cliff structure.
3. **Hierarchical prior across positions** — pools information across positions to stabilize small samples (TE in particular). The CMU 2020 Bayesian draft paper (Robinson) demonstrates the approach for predicting pick position; the same machinery applies to outcome modeling. Recommended for TE specifically.
4. **Log-decay (`1/log(pick)`)** — keep as baseline only. It smooths across real cliffs (pick 32→33, pick 100→106) and underweights the Round-1 QB premium relative to observed data.

**Recommendation:** primary feature is position-specific isotonic step, secondary feature is bucket dummies for interpretability, baselined against log-decay. Hierarchical pooling applied to TE and possibly QB given small annual cohorts.

### 2.4 Rejected alternatives

- **Smooth continuous pick as the sole feature.** Empirically violates the observed cliffs.
- **A single global transform across positions.** The QB R1/R2 cliff differs structurally from the WR R2/R3 cliff; pooling across positions without hierarchy hides this.
- **A "separate rookie archetype gate"** as the primary mechanism. Archetype gating is useful as a complement (especially at TE), but using it instead of draft capital risks substituting subjective tagging for the most reliable signal in the literature.
- **Hand-picked breakpoints in code.** Constitutes a hardcoded structural prior; recompute breakpoints from the backtest cohort each model refresh.

### 2.5 Validation gates (before Engine A change)

- Backtest on ≥10 draft classes with complete identity coverage (gated on 3C).
- Calibration report at least as good as current Engine A on held-out classes; divergence ledger entry required.
- Per-position out-of-fold AUC / Brier delta vs. log-decay baseline, reported with bootstrap CIs.
- Sensitivity check: rerun with random ±10 pick jitter — step function must not move breakpoints by more than one bucket.
- Trust Surface v2 update; model card refreshed.

### 2.6 Risks / counterarguments

- **Draft capital is endogenous to opportunity.** Teams give early picks more snaps, especially RBs. A draft-capital step function may be partially measuring opportunity assignment, not talent. Mitigation: include early-career opportunity proxies (snap share, target share) as separate features once available; do not let draft capital absorb their signal in the rookie-year prediction.
- **Modern NFL draft economics are shifting.** Recent classes show fewer Day-1 RBs and more 6th–7th round RB hits (Last Word). A step function fit on 10–15 years may underweight recency. Mitigation: time-weighted resampling in backtest.
- **TE evidence is thin.** Resist over-modeling at TE. Use hierarchical shrinkage and accept wider posteriors.

---

## 3. 3B Findings: TE Remodel

### 3.1 Why the current TE model likely fails

The fantasy TE literature converges on three failure modes that almost certainly apply to Dynasty Genius's current pipeline:

1. **Role conflation.** "Tight end" pools inline blockers, in-line receivers (Kittle/Kelce-type), and big-slot/move TEs (Loveland, Pitts, Bowers). PFF prospect work (2025/2026 Big-Board pieces; Fantasy Life's Loveland profile showing 43.7% slot / 39.1% inline / 16.4% boundary across his Michigan career) demonstrates that alignment heterogeneity is structural, not noise. A single TE model is mis-specified.
2. **Small annual cohorts.** ~1.87 TEs/round historically (Fantasy Footballers); only ~25–34 NFL TEs in 7 years exceed 600 receiving yards (PFF). The "TE breakout in Year 2/3" pattern (Trey McBride 53.6 → 80.5 → 89.6 receiving grade) means rookie-year features are weak predictors and require multi-year horizons.
3. **Receiving production at TE is highly correlated with offensive role, not raw talent.** This is why isolated college receiving grades (e.g., BrainyBallers' top vs. bottom-10 PFF receiving grade cohort showing a 40.8% higher top-10 NFL rate at ≥80.6) are predictive but not deterministic.

### 3.2 Recommended TE archetypes (label first, then model)

Archetype labeling should precede any model retraining:

- **A. Receiving specialist / move TE** (≥55% receiving snaps, slot share ≥30%, run-block grade typically <65). Examples: Pitts, Kincaid, Bowers in college usage.
- **B. In-line receiving TE** (≥55% inline alignment, receiving grade ≥75, run-block grade 60–80). Examples: Kelce, Kittle, Andrews, Warren, McBride.
- **C. Inline blocker / TE2** (≥70% inline, run-block grade ≥75, route participation low). Examples: Hawes, most Day-3 NFL TEs.
- **D. Big-slot hybrid / "WR-body" TE** (slot share >40%, lighter frame, designed-target rate high). Loveland, Fannin Jr. lean here.

Archetypes are conditioning variables, not separate models initially — sample sizes don't yet support per-archetype models.

### 3.3 PFF collegiate Step 0 feasibility

**Field availability.** PFF documents the following collegiate fields, all of which appear in published draft scouting articles citing PFF Premium parameters: receiving grade, run-blocking grade, pass-blocking grade, yards per route run (YPRR), yards after catch per reception, contested-catch% / contested-target attempts, drop rate, slot snap%, inline snap%, wide snap%, routes run, targets, receptions, missed tackles forced, alignment by formation, late-down threat rate, zone vs. man splits, and PFF Signature Stats glossary fields (YPRR, slot performance, deep passing, drop rate). PFF's college usage hub (Week 1 2025 piece) explicitly confirms slot/wide/tight/backfield alignment, target depth, situational splits, and personnel-faced data at the college level.

**Feasibility constraints.**
- PFF Premium does **not** include API access for individual subscribers (their support article and B2B/data page indicate API access is enterprise/team-tier; consumer Premium provides CSV export from Premium Stats UI). For Phase 13, plan around **manual CSV export** of relevant TE prospect cohorts and historical college seasons, not programmatic ingestion. This is a meaningful operational tax and must be reflected in Phase 13 scope.
- The PFF college data window starts **2014**, which materially constrains a 10–15 year backtest and is a key risk for combining 3A and 3B on the same historical cohort.
- License: PFF data may not be redistributed; treat exports as private feature store inputs, never as public artifacts.

**Most predictive collegiate TE metrics** (based on PFF scouting/model articles and prospect-model evidence):
- PFF college receiving grade (top-50 NFL TEs since 2016 cluster at ≥80.6; threshold from BrainyBallers).
- Yards per route run (≥2.21 cited as the rookie-class benchmark in PFF 2026; bowers/warren/fannin/loveland all exceeded).
- Yards after catch per reception (separates Kittle/Fannin types from receiving specialists).
- Contested-catch rate (Koziol's 74.1% example; secondary signal).
- Receiving Yards per Team Pass Attempt — RYPTPA (Fantasy Footballers/Fantasy Life identifies as most predictive normalized usage metric).
- Slot% / inline% split and snaps wide (the alignment vector that anchors archetype assignment).
- Run-block grade and pass-block grade (separates Archetype C from A/B).

### 3.4 Public / lower-cost fallbacks evaluated with equal depth

If PFF Step 0 fails feasibility (license, manual cost, or coverage), the following fallback stack is viable but degraded:

- **cfbfastR / collegefootballdata.com (sportsdataverse)** — Open-source CFB play-by-play, rosters, player usage, EPA/PPA. Provides snap-counted routes only indirectly (must be inferred from play participation). Strong for **receiving production, RYPTPA, target share, conference strength of schedule**. Weak for **alignment (slot vs. inline) and blocking grades** — these are PFF's proprietary signals and have no public equivalent in cfbfastR.
- **nflverse college data + nflreadr `load_rosters`, `load_combine`, `load_draft_picks`** — Provides combine athleticism, draft data, and NFL career outcomes for the target cohort. Pairs naturally with cfbfastR for college production but does not contain alignment.
- **PlayerProfiler college metrics** — Documents College Dominator Rating, Speed Score, Height-Adjusted Speed Score, Burst Score, Agility Score, Catch Radius, SPARQ-x, College YPR. PlayerProfiler's own TE breakout work (Okwuegbunam profile) calls out 15% College Dominator and 12.0 YPR as thresholds. Good for athletic and production profiling, **no alignment or block-grade data**.
- **CFB Reference / Sports-Reference** — Strong historical box-score and career data back to 1956 (FBS player stats). **License risk:** Sports-Reference's Terms of Use explicitly prohibit using their content for training or supporting ML models without permission. This makes CFB Reference unusable as a feature-store source for model training in Phase 13 under conservative interpretation. Recommend treating it as a **reference / spot-check only**, not as a training feature source.
- **Sports Info Solutions (SIS)** — Maintains route-level college charting comparable to PFF for some seasons. License is enterprise; SIS is generally not a realistic individual-subscription fallback.
- **nflverse `load_participation` + `offense_personnel`** — For *active NFL* TEs only, the participation dataset exposes 11/12/21/22 personnel and Next Gen Stats' positional alignment labels (offense has six positional categories per play, including TE alignments). This is the **best public proxy for the slot/inline/wide split for NFL TEs already on rosters**, and is sufficient for the active-cohort half of the TE problem even if college PFF is unavailable.

### 3.5 Recommended path

**Prospect TE modeling (incoming rookies):** PFF Step 0 preferred. If infeasible, use cfbfastR production + PlayerProfiler athleticism + combine data, accepting that **archetype labeling will require manual film/scouting-report tagging** until route alignment is licensed. Start with archetype labeling on the 2014–2025 cohort, then fit a hierarchical model with archetype as conditioning variable.

**Active NFL TE modeling (currently rostered):** Use nflverse `load_participation` for personnel-group context (11 vs 12 personnel deployment), plus nflfastR play-by-play target/route inference. This is decoupled from PFF and can proceed in parallel.

### 3.6 Validation gates and out-of-scope

- Minimum 10 college seasons of complete PFF or fallback coverage before any TE model can be promoted from EXPERIMENTAL.
- ≥80% identity match for the TE prospect cohort to NFL outcomes before training.
- Backtest required with hold-out classes; calibration report; divergence ledger entry; model card.
- **Out of scope for Phase 13:** per-archetype separate models, TE blocking-impact modeling for fantasy (insufficient sample), Year-3 breakout prediction (requires longer horizon than current artifacts support), promotion of TE out of EXPERIMENTAL.

### 3.7 Risks / counterarguments

- The "TE is fundamentally unpredictable" critique (Last Word) is real. Even with role-conditioning, expect calibration bands wider than QB/RB/WR.
- PFF grades are descriptive of past play, not raw predictive scores; over-reliance risks overfitting to a single vendor's judgment. Mitigation: pair every PFF feature with at least one publicly verifiable production feature (YPRR is the natural one).
- Archetype tags are themselves noisy labels. Use inter-tagger agreement (or rule-based thresholds) and version the tagging rubric.

---

## 4. 3C Findings: Identity Audit

### 4.1 Canonical ID design

Treat **`gsis_id`** as the canonical Dynasty Genius primary key (consistent with nflverse practice — nflverse-players uses gsis_id as its primary key and overwrites associated IDs against it). All source-specific IDs live in the identity layer; no adapter generates production identity.

**ID columns required in the bridge** (drawn from nflreadr's `load_ff_playerids`, which exposes 35 columns across 12,186 players as of January 2026): `mfl_id`, `sportradar_id`, `fantasypros_id`, `gsis_id`, `pff_id`, `sleeper_id`, `nfl_id`, `espn_id`, `yahoo_id`, `rotowire_id`, `fantasy_data_id`, `pfr_id`, `cfbref_id` (via `nflverse-players` extensions where present), plus DOB, draft year, draft team, college, position, status. The Sleeper `/v1/players/nfl` payload itself returns `gsis_id`, `espn_id`, `yahoo_id`, `rotowire_id`, `rotoworld_id`, `sportradar_id`, `stats_id`, `fantasy_data_id`, `swish_id`, `opta_id`, `pandascore_id`, `oddsjam_id`, `kalshi_id` (per current Sleeper API client documentation), which provides the bridge from Sleeper's `player_id` to `gsis_id` directly. **PFF college player_id, when supplied with PFF exports, must be stored in this layer and not in any adapter.**

### 4.2 Deterministic matching strategy (required first)

Cascade, in order — every step must produce an audit-logged decision:

1. **Direct ID join** via `ff_playerids` (gsis_id ↔ sleeper_id ↔ pff_id ↔ pfr_id ↔ espn_id).
2. **Sleeper payload pass-through** for active rosters (Sleeper carries gsis_id and sportradar_id natively).
3. **(Name + DOB + position + draft year)** composite key for residuals.
4. **(Name + college + draft year + position)** for pre-NFL prospects who lack gsis_id.
5. Only after 1–4 produce no match, items go to the **review queue**. Fuzzy matching is never silent.

The nflverse `join_coalesce` utility in `nflreadr` documents the canonical pattern for coalescing IDs across sources and is a useful reference; the `nflverse-players` repo also documents that gsis_id is the "single source of truth" primary key and that manual overrides are explicitly supported via a JSON override file — this is a model worth mirroring.

### 4.3 Fuzzy / review policy

- All fuzzy candidates (token-set ratio ≥ threshold) enter a **manual review queue** with the top-K candidates, their scores, and the disambiguating attributes (DOB, draft year, college, height/weight).
- A reviewer (David or a sanctioned identity reviewer) must approve before any fuzzy resolution is written to the identity layer.
- Approved fuzzy resolutions persist as **named overrides** (JSON override pattern), versioned in git, never as opaque inline matches.
- Rejected candidates persist in a "do-not-merge" list to prevent regression.

### 4.4 Coverage thresholds (gate values)

Recommended thresholds for Phase 13 promotion (final values TBD by David):

- **Current cohort** (active rosters + incoming rookie cohort): ≥99% deterministic gsis_id ↔ sleeper_id coverage; ≥97% pff_id coverage among players with a PFF profile; 100% of users' Superflex starters resolved.
- **Historical cohort** (10–15 year backtest, including retired players): ≥95% gsis_id coverage; ≥90% pff_id; ≥85% pfr_id; documented gaps by draft round (we expect Day-3 / UDFA / retired players to drive most gaps).
- **TE-specific**: ≥90% of the TE cohort 2014–2025 must have valid PFF college player_id ↔ gsis_id mapping before TE remodel training can begin.

### 4.5 The "missing cohort"

The expected gaps, based on nflverse-players documentation and community practice:

- **2022+ rookies** with missing or late-arriving gsis_ids — nflfastR documents that 2022 PBP introduced new IDs that gsisdecoder cannot decode and that rookies have been the worst-affected group. Sleeper assigns its own player_id immediately on signing, often before gsis_id propagates, producing a window where sleeper_id exists but gsis_id is NULL.
- **Pre-NFL prospects** (declared but not yet drafted) have no gsis_id at all; they are the highest-volume identity gap for any rookie-evaluation engine.
- **Short-career and retired players** lose ID-source coverage over time; ff_playerids occasionally trims inactive players.
- **Position-changers** (e.g., college WR → NFL TE conversions like Boyd at Georgia Tech) — these break college-position-based heuristic joins.

These cohorts must be enumerated explicitly in the audit artifact.

### 4.6 Audit artifacts (must be produced in 13.1)

- **Coverage matrix** — rows: source IDs, columns: cohort segments (active starters / active depth / 2024–25 rookies / 2014–2023 retired). Values: % matched, % review queue, % unmatched.
- **Review queue ledger** — every ambiguous match, its candidates, who decided, and when.
- **Override registry** — versioned JSON list of manual ID corrections, mirroring nflverse-players' contribution model.
- **Failure-mode report** — enumerate gsis_id ↔ sleeper_id missing-rookie examples, position-change cases, and known name-collision pairs.
- **Identity contract** — formal statement that source-specific IDs live only in the identity layer, with adapter API expectations.

### 4.7 Tests / checks to require

- **Contract tests:** every adapter must declare which source IDs it emits and must fail closed if asked to emit gsis_id directly.
- **Daily integrity job:** verify all active-roster Sleeper players have either a gsis_id or a queued review item; alert on regressions.
- **Backtest cohort lock:** historical identity snapshot is versioned and frozen per backtest run; later identity updates must not silently change historical features.
- **Duplicate detection:** assert no two production records share (gsis_id) and no two share (sleeper_id) when both are non-null.
- **Override audit:** every manual override has an author, timestamp, and justification.
- **Coverage smoke test in CI:** if coverage drops below threshold on any cohort segment, the build fails before model training tables are regenerated.

---

## 5. Recommended Phase 13 Scope

**In scope**
- 13.1 Identity audit: canonical key design, deterministic cascade, review queue, coverage matrix, override registry, contract tests, CI gates.
- 13.2 Engine A draft-capital research: isotonic / bucketed / hierarchical / log-decay bake-off on the backtest cohort, position-specific breakpoint discovery, validation gates.
- 13.3 TE remodel Step 0: PFF collegiate feasibility evaluation (cost, manual export tax, license, coverage from 2014); archetype labeling rubric on 2014–2025 prospect cohort; nflverse participation-based active-TE alignment proxy.
- Phase 12 artifact updates: model cards, calibration reports, divergence ledger entries, Trust Surface v2 surfaces for any promoted change.

**Out of scope (not deferred — explicitly excluded)**
- DVS implementation.
- Promotion of TE out of EXPERIMENTAL.
- Any ingestion of market data (KTC/FantasyCalc/ADP/consensus) into Engine A or Engine B training features.
- Silent fuzzy ID matching in production paths.
- Hardcoded age cliffs.
- CFB Reference as a model-training feature source (license risk).

**Explicitly deferred (revisit in Phase 14)**
- Per-archetype separate TE models.
- TE blocking-impact contribution to fantasy projection.
- SIS or other enterprise charting subscriptions.
- A formal CFB-Reference license negotiation if PFF Step 0 fails.
- QB backup-profile model refresh (the Phase 12 caveat remains).

---

## 6. Implementation Implications (Repo Surfaces, Not Code)

Likely surfaces touched:

- **Identity bridge module** — new package/folder, owns gsis_id-keyed ID map; consumes `nflreadr::load_ff_playerids`, `nflverse-players` overrides, Sleeper `/v1/players/nfl`, PFF export player_ids.
- **Source adapters** (Sleeper, nflverse, PFF export reader, PlayerProfiler if used) — must be refactored so each emits only source-native IDs and joins through the bridge; no adapter produces gsis_id directly.
- **Feature store tables/CSVs** — new `te_prospect_features` and `draft_capital_features` tables with explicit gsis_id (NULL allowed only for pre-draft prospects, with prospect_id surrogate); existing TE features rebuilt under archetype tags.
- **Model training gates** — coverage checks at training-table assembly, refusing to materialize tables that violate threshold.
- **Contract tests** — adapter-emits-correct-IDs, no-duplicate-gsis_id, override-registry-well-formed, backtest-cohort-frozen.
- **Documentation artifacts** — coverage matrix, override registry README, identity contract spec, updated model cards for Engine A and TE, updated divergence ledger.
- **Trust Surface v2** — surface coverage metrics and any new step-function breakpoints with provenance.

---

## 7. Open Questions for David

1. Is the PFF Premium account's manual CSV-export workflow acceptable as the Phase 13 ingestion mechanism, or do we need to budget for the PFF B2B/Data tier (which provides API access)?
2. What coverage thresholds should be hard gates vs. soft warnings? (Suggested values above; need product-owner sign-off.)
3. Who owns the review queue? You alone, or do we sanction additional reviewers? This determines how many ambiguous matches can be resolved per Phase 13 cycle.
4. For the 10–15 year backtest window, are we comfortable with PFF's college data starting in 2014 limiting 3A's *combined* validation cohort? If yes, 3A's pre-2014 portion runs without PFF features (which is fine for draft-capital research but worth confirming).
5. Should CFB Reference be pursued under a paid/permission-based license, or accept the public fallback gap?
6. Archetype rubric ownership: do you tag the historical TE cohort yourself, or do we build a rule-based labeller subject to your review?

---

## 8. Source Bibliography

- *NFL Draft Capital Predicts Success*, Dynasty Nerds (2026) — hit-rate framing for Round-1 WRs since 2015. https://www.dynastynerds.com/analytics/nfl-draft-capital-fantasy-football/
- *Draft Capital & Its Correlation To Early-Career Fantasy Production*, The Fantasy Footballers (2000–2018 sample) — RB/WR/TE hit rates by round. https://www.thefantasyfootballers.com/articles/draft-capital-its-correlation-to-early-career-fantasy-production/
- *Importance of Draft Round When Evaluating WRs*, Campus2Canton (Peter Howard data, since 2001) — WR step pattern between rounds 1/2/3. https://campus2canton.com/importance-of-draft-round-when-evaluating-wrs/
- *Running Back Hit Rates by NFL Draft Round* and *Wide Receiver Hit Rates by Draft Position*, Last Word On Sports (2011–2021 sample). https://lastwordonsports.com/nfl/2024/04/12/running-back-hit-rates-by-nfl-draft-round/ ; https://lastwordonsports.com/nfl/2024/04/09/wide-receiver-hit-rates-by-draft-position/
- *Why Draft Capital Is the Most Important Thing In Dynasty Leagues*, Last Word On Sports — QB Round-1/Round-2 cliff. https://lastwordonsports.com/nfl/2023/03/30/why-draft-capital-is-the-most-important-thing-in-dynasty-leagues/
- *2025 NFL Draft: What historical hit rates reveal about positional success*, PFF — positional hit-rate framing by round. https://www.pff.com/news/draft-what-historical-hit-rates-reveal-about-positional-success
- *Rating the 2026 NFL Rookie Wide Receivers* and *Fantasy Football Rookie Rankings From NFL Draft Round 1*, Fantasy Life — Rookie Super Model framing for draft capital weighting. https://www.fantasylife.com/articles/fantasy/rating-the-2026-nfl-draft-wide-receiver-prospects-the-rookie-sup ; https://www.fantasylife.com/articles/fantasy/fantasy-football-rookie-rankings-for-2026
- *2025/2026 NFL Draft: Scouting tight ends using PFF+* (Bobby Beers, PFF) — TE production thresholds, YPRR / receiving grade / YAC. https://www.pff.com/news/draft-2025-nfl-draft-scouting-tight-ends-pff ; https://www.pff.com/news/draft-2026-nfl-draft-scouting-tight-ends-pff
- *Fantasy Football: Rookie tight end prospect model* and *2026 rookie TE model*, PFF. https://www.pff.com/news/draft-fantasy-football-rookie-tight-end-prospect-model ; https://www.pff.com/news/fantasy-football-2026-rookie-tight-end-prospect-model
- *Dynasty Range of Outcomes: 2024 TE Class*, Fantasy Footballers — RYPTPA and declare-status framing. https://www.thefantasyfootballers.com/dynasty/dynasty-range-of-outcomes-2024-tight-end-class/
- *Tight Ends and PFF Receiving Grade Predictive Insights*, BrainyBallers — 80.6 college receiving-grade threshold. https://brainyballers.com/tight-ends-can-pffs-receiving-grades-help-predict-nfl-success/
- *Finding Rookie Breakout TEs Using PlayerProfiler's Advanced Metrics*, PlayerProfiler — Speed Score, Agility, Burst, Catch Radius, College Dominator, College YPR. https://www.playerprofiler.com/article/albert-okwuegbunam-advanced-stats-metrics-analytics-profile-2/
- *Signature Stat Spotlight: Tight Ends* and *PFF Signature Statistics – a glossary*, PFF — fields available in PFF Premium Stats / Elite. https://www.pff.com/news/nfl-signature-stat-spotlight-tight-ends ; https://www.pff.com/news/pro-pff-signature-statistics-a-glossary
- *College Football Usage and Production Report*, PFF — confirms slot/wide/tight/backfield alignment, target depth, situational splits at college level. https://www.pff.com/news/college-football-usage-production-report-week-1-2025
- *PFF Support: Does API access come with a subscription?* — basis for the claim that Premium does not include API access (page returned 403, but the article title is in PFF's Zendesk index). https://profootballfocussupport.zendesk.com/hc/en-us/articles/32094827302163
- *PFF Data (B2B)*, Teamworks/PFF — enterprise data offering. https://b2b.pff.com/data
- *Load Fantasy Player IDs — load_ff_playerids*, nflreadr — 35-column ID bridge spec; columns include mfl_id, sportradar_id, fantasypros_id, gsis_id, pff_id, sleeper_id, nfl_id, espn_id. https://nflreadr.nflverse.com/reference/load_ff_playerids.html
- *nflverse-players CONTRIBUTING.md*, GitHub — gsis_id as primary key, manual override workflow. https://github.com/nflverse/nflverse-players/blob/master/.github/CONTRIBUTING.md
- *Package 'nflreadr' reference manual*, CRAN — `join_coalesce` utility, `dictionary_ff_playerids`. https://cran.r-project.org/web/packages/nflreadr/refman/nflreadr.html
- *Package 'nflfastR'*, CRAN — 2022 rookie gsis_id decode failures, `nflreadr::load_players` join fallback. https://cran.r-project.org/web/packages/nflfastR/nflfastR.pdf
- *Introduction to NFL Analytics with R*, Brad Congelio — load_rosters returns IDs across nine sources. https://bradcongelio.com/nfl-analytics-with-r-book/03-nfl-analytics-functions.html
- *Sleeper API*, Sleeper — players endpoint, ID list including gsis_id, sportradar_id, espn_id, yahoo_id. https://docs.sleeper.com/
- *go-sleeper package*, dsheehan167/go-sleeper — full Sleeper Player struct including gsis_id, sportradar_id, fantasy_data_id, etc. https://pkg.go.dev/github.com/dsheehan167/go-sleeper
- *cfbfastR*, sportsdataverse — open-source college football play-by-play and player usage. https://cfbfastr.sportsdataverse.org/
- *Sports Reference Data Use Policy* — prohibits ML training on SR content without permission. https://www.sports-reference.com/data_use.html
- *Grinding the Bayes: A Hierarchical Modeling Approach to Predicting the NFL Draft*, Robinson (CMU CMSAC 2020) — hierarchical Bayesian framing for draft outcomes. https://www.stat.cmu.edu/cmsac/conference/2020/assets/pdf/Robinson.pdf
- *isoreg: Isotonic / Monotone Regression*, R Core — canonical PAVA reference for monotonic step-function fitting. https://rdrr.io/r/stats/isoreg.html
- *Personnel grouping (gridiron football)*, Wikipedia, and *A Look Into Offensive Personnel Diversity*, SumerSports — 11/12 personnel framing for active-TE alignment proxy. https://en.wikipedia.org/wiki/Personnel_grouping_(gridiron_football) ; https://sumersports.com/the-zone/a-look-into-offensive-personnel-diversity/
- *The Evolution of Personnel Groupings and Usage*, NFL Football Ops — Next Gen Stats positional categories used for alignment. https://operations.nfl.com/gameday/analytics/stats-articles/the-evolution-of-personnel-groupings-and-usage-what-is-versatility/
- *Dynasty Genius: Phase 12 Research Brief* (internal Google Doc, accessed 2026-05-15) — confirms operational state going into Phase 13; no Phase-13-Research-Brief.md was found in Drive at the time of this research, so prior-draft challenge is treated as N/A. https://docs.google.com/document/d/168l_016j31le_EG8JclCPfYYsAMz2jtceR5wcAbuke8/

*Access date for all URLs: 2026-05-15 unless otherwise noted. Where dates are not visible on the source page, treat the cited claim as as-of access date.*