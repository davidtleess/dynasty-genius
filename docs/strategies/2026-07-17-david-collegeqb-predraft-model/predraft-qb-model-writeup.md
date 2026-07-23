# Pre-Draft QB Dynasty Value Model
## Research, Backtest v0, Data Pipeline, and Hypotheses to Test

Audience: Product, ML, Engineering
Status: Research complete, backtest v0 complete, pipeline and hypothesis validation not started
Format context: Superflex dynasty (QB-premium scoring environment)

---

## 1. Executive Summary

We want to rank college quarterbacks by predicted dynasty fantasy value BEFORE the NFL draft. The established research consensus is that draft capital (round, pick) and age are the strongest predictors of NFL QB outcomes. Our problem: draft capital does not exist yet at ranking time, so it must be proxied, and our target is fantasy value in a Superflex format, not NFL wins, which changes what matters.

Three conclusions drive the proposed design:

1. **Draft capital, proxied by aggregated mock draft data, is the spine.** College stats explain residuals around it, not the other way around. This is the single most replicated finding in the literature and our backtest confirms it: a 50/50 blend of a stats-only model and draft position beat both components and was the only ranker that never went negative in any test class.
2. **The residual signal is concentrated almost entirely in rushing production.** Every case where the stats-only model beat the NFL's own ordering (Lamar Jackson 2018, Jalen Hurts 2020, Justin Fields 2021) was a rushing QB the league underpriced. This is the Superflex edge and it is mechanical: rushing yards are worth roughly 2.5x passing yards in fantasy scoring.
3. **The ceiling is modest and the product must communicate uncertainty.** With roughly 100 to 150 usable training QBs since 2010 and 25 to 35 hits, this is a small-sample problem. Some misses (Josh Allen) are irreducible from pre-draft data. A model that reliably beats consensus rank correlation by a few points, with honest uncertainty bands, is a win. Anyone promising more is overfitting.

---

## 2. Problem Statement

Rookie QB acquisition is the highest-leverage decision in Superflex dynasty. Startup and rookie draft picks spent on QBs who hit compound for 5 to 10 years; misses are near-total losses. Managers currently rely on consensus rookie rankings that are published after the NFL draft, which means the largest value windows (pre-draft trades, early rookie pick pricing) close before good information exists. A pre-draft ranking with calibrated uncertainty lets a user price rookie picks and prospects before the market does.

### Goals

- Produce a pre-draft ranking of draft-eligible QBs with a value band (floor and ceiling), not just a point rank.
- Beat the consensus baseline (Expected Draft Position ordering) on leave-one-class-out rank correlation against realized outcomes.
- Support two user intents: build-to-keep (predicted on-field fantasy production) and draft-and-flip (predicted peak market value).
- Refresh continuously through draft season as mock draft consensus moves.

### Non-Goals

- Predicting NFL landing spot or team fit. Unknowable pre-draft; the model treats draft slot as a distribution and stops there.
- Modeling RB/WR/TE prospects. Separate models with different feature sets; this document is QB-only.
- Film-based or traits-based scouting inputs. We consume the market's aggregation of scouting (mock drafts) rather than attempting to reproduce it.
- Beating NFL front offices at identifying the best NFL quarterback. Our target is fantasy value, which weights rushing far more than the NFL does. That gap is the product.

---

## 3. Research Findings

Each claim below was pressure-tested against published research. Verdicts: HOLDS, PARTIALLY HOLDS, or BREAKS.

### 3.1 Draft capital proxy via mock draft aggregation. PARTIALLY HOLDS.

Grinding the Mocks (Benjamin Robinson) aggregates weighted mock draft data into Expected Draft Position (EDP). His Bayesian model explains roughly 85% of variance in actual draft outcomes, but on a log-adjusted, all-positions basis. QB-specific accuracy is weaker and bimodal: QBs are systematically over-projected during mock season and historically get drafted about a round later than their EDP round, yet individual QBs also get reached on (Bo Nix went 12th against a consensus rank of 35; Michael Penix Jr. went 8th against a late-first consensus) or slide hard (Will Levis out of round 1 in 2023; Malik Willis to pick 86 in 2022 as the internet consensus QB1). Implication: consume EDP as a probability distribution over draft ranges, never a point estimate, and widen QB bands relative to other positions.

### 3.2 Age. PARTIALLY HOLDS, down-weight it.

Age matters, but less for QBs than for WR/RB. QB fantasy breakouts cluster before the age-27 season (roughly 82% of them), but successful QBs enter the league across a wide age band (Burrow and Daniels at 23, Nix at 24). Frame age as "breakout window closes around 26 to 27," not "younger prospect is strictly better." Keep draft-day age and breakout age as features with modest weight.

### 3.3 Rushing production as the Superflex differentiator. HOLDS, with a longevity caveat.

The strongest and most consistent finding in the whole research base:

- Roughly 90%+ of QB seasons with 100+ rush attempts since 2014 finished top-12 in fantasy points per game.
- College rushing translates: QBs on average maintain or increase rush attempts as rookies relative to their final college season, and college rush attempts are the primary predictor of NFL rushing volume.
- Academic support: Craig and Winchester (2021, European Journal of Operational Research) found college rushing ability significantly predicts NFL performance among drafted QBs (rush yards per attempt vs NFL QBR: p < 0.001, R-squared 0.21) while college passing ability does not (p = 0.71).

Caveats: rushing production declines meaningfully with age (roughly 26% drop from the age-26 to age-27 season on average; the dual-threat sell window is 27 to 28), so rushing profiles are shorter-duration assets. And rushing does not rescue broken passers as long-term assets (Richardson, Willis, Lance). A passing-floor gate is required. Rushing stats must be sack-adjusted: the NCAA counts sacks against rushing yards, which materially deflates true rushing production (Lamar Jackson's 2017 official 6.9 yards per carry was roughly 8.7 sack-adjusted).

### 3.4 Passing efficiency features. MOSTLY BREAKS at the detail level. Keep three, drop the rest.

- Keep: PFF passing grade (college-to-NFL translation roughly r = 0.37, rising to 0.45 with attempt thresholds), adjusted completion percentage or CPOE-style accuracy (r roughly 0.35, beats raw completion percentage at 0.26), and EPA/PPA per dropback.
- Keep as a negative filter only: pressure-to-sack rate. Eager (PFF, 2019) showed QBs control their own pressure rate more than their offensive line does and the trait is stable college to pro. But applied work shows it spots landmines (career 20%+ flagged Willis, Ridder, Zach Wilson) rather than identifying stars (Burrow and Jackson were also above 20%). Binary flag, not a continuous positive feature.
- Drop: raw completion percentage (dominated by adjusted), deep attempt rate and ADOT as headline features (max published correlation roughly 0.28 to 0.32, from small or niche samples; deep accuracy is the weakest accuracy sub-signal), big-time throw and turnover-worthy rates as separate features (already components of PFF grade; double-counting risk), play-action splits (PFF found play-action passer rating is essentially non-predictive season to season).

### 3.5 Recruiting pedigree. PARTIALLY HOLDS, weakening.

Blue-chip composite ratings correlate with eventual draft selection, but the tails are loud: Cam Ward was a zero-star recruit taken first overall in 2025; Mayfield was a walk-on; Allen, Rodgers, and Burrow were all missed by recruiting services. In the transfer portal and NIL era the development pathway recruiting ratings were built to predict has changed. Use as a weak prior that decays to near zero once a QB has 2+ seasons of major-college production.

### 3.6 Measurables. HOLDS (mostly weak).

Relative Athletic Score has essentially no correlation with QB fantasy outcomes. Height, weight, and hand size matter only at extreme tails. The one defensible measurable is the 40 time as a rushing-upside proxy. Small weights only.

### 3.7 The humbling caveat. HOLDS in spirit.

Wolfson, Addona, and Schmicker (2011, Journal of Quantitative Analysis in Sports) concluded college and combine statistics have little predictive value beyond draft position because NFL teams aggregate pre-draft information effectively. Three things soften this for us: modern metrics (PFF grades, EPA, charted accuracy) did not exist in their data; our target is fantasy points, which are rushing-weighted in a way NFL evaluation is not; and modern hit-rate work confirms draft capital dominance is compatible with a modest residual edge. The architectural lesson stands: draft capital proxy first, small residual model second.

---

## 4. Backtest v0: Method, Results, Interpretation

### 4.1 Design

Classes 2018 to 2021, top 5 drafted QBs each (n = 20), all with 5+ NFL seasons to judge. Inputs restricted to information knowable before that year's draft: final college season stats, draft-day age, recruiting stars, and a pre-declared competition-level multiplier (FCS 0.75, Group of 5 or weak slate 0.80 to 0.85, Power 5 1.00). No draft position. No NFL data. Weights were locked before scoring from the research-derived spec:

```
score = 0.35 * z(rush yds/gm) + 0.10 * z(rush TD/gm)
      + 0.25 * z(AY/A)        + 0.10 * z(comp %)
      + 0.15 * z(-draft age)  + 0.05 * (stars - 3)/2
```

Outcome label: realized Superflex dynasty value rank within class through the 2025 season. Baseline: actual NFL draft order of the same five QBs (slightly generous to the baseline, since pre-draft consensus was wrong in the same direction as the draft on the key cases). Metric: Spearman rank correlation, per class and averaged.

### 4.2 Results

| Class | Stats-only model | Actual draft order | 50/50 blend |
|---|---|---|---|
| 2018 | 0.00 | -0.10 | +0.10 |
| 2019 | +0.30 | +0.60 | +0.60 |
| 2020 | +0.40 | -0.30 | +0.20 |
| 2021 | -0.20 | +0.20 | +0.20 |
| Mean | +0.125 | +0.100 | +0.275 |

Notable individual calls:

| Player | Model rank | NFL draft rank (QB order) | Realized outcome rank |
|---|---|---|---|
| Lamar Jackson (2018) | 1 | 5 | 2 |
| Jalen Hurts (2020) | 1 | 5 | 1 |
| Justin Fields (2021) | 1 | 4 | 2 |
| Kyler Murray (2019) | 1 | 1 | 1 |
| Josh Allen (2018) | 5 | 3 | 1 |
| Trey Lance (2021) | 2 | 3 | 5 |
| Tua Tagovailoa (2020) | 2 | 2 | 5 |

### 4.3 Interpretation

- **The blend wins.** It beat both components on average and never produced a negative class. This directly validates the "draft capital spine plus residual model" architecture.
- **Every stats-model win is a rushing QB the NFL underpriced.** Jackson, Hurts, Fields. The alpha is exactly where the Superflex thesis says it should be.
- **The failure modes match the research warnings.** Allen (traits invisible in stats; irreducible miss), Lance (elite rushing against FCS competition fooled the model even with a 0.75 penalty; small samples at low competition levels need widened uncertainty or hard flags, not adjusted point ranks), Tua and Haskins (efficiency without rushing in loaded offenses).

### 4.4 Limitations of v0 (why this is a smoke test, not proof)

1. College stats were assembled from recalled public records, not pulled from a source of truth. Errors of a few percent will not flip Jackson-or-Hurts-sized gaps but could flip close calls. All numbers must be re-derived from CFBD in the production harness.
2. Hindsight contamination: weights were locked before scoring, but the spec was written by someone who knows how these players turned out. True validation requires the pipeline running leave-one-class-out on 2012 to 2024.
3. Outcome ranks are hand-assigned and disputable at the margins.
4. n = 5 per class means one rank swap moves Spearman by 0.3. Only the pattern across classes is meaningful, not any single number.

---

## 5. Proposed Model Spec

### 5.1 Features (capped at roughly 6 active features plus 2 flags, per the sample-size math below)

| # | Feature | Role | Expected weight |
|---|---|---|---|
| 1 | Projected draft capital as a distribution over ranges (P(top-5), P(round 1), P(day 2), P(day 3)) | Spine | Dominant |
| 2 | Sack-adjusted rushing production, final season (yds/gm, attempts/gm, rush TD/gm) | Primary residual | High |
| 3 | Passing accuracy/quality: PFF passing grade and adjusted completion percentage (or CPOE proxy) | Passing floor | Medium |
| 4 | EPA or PPA per dropback, opponent-adjusted where available | Passing quality | Medium |
| 5 | Draft-day age and breakout age | Modifier | Low-medium |
| 6 | Recruiting composite rating | Weak prior, decays with college sample | Low |
| F1 | Pressure-to-sack rate >= 20% career | Binary downside flag | Filter |
| F2 | Competition/sample flag (sub-FBS, single-season starter, fewer than ~16 career starts) | Uncertainty widener | Filter |

Explicitly dropped, with reasons documented in Section 3.4: raw completion percentage, deep rate/ADOT as headline features, standalone big-time-throw and turnover-worthy rates, RAS beyond a token term, height and hand size except extreme tails, play-action splits.

Candidate additions to evaluate (not in v1): career starts count, early-declare status, strength-of-schedule adjustment on efficiency stats, performance vs top-25 defenses, teammates-drafted supporting cast proxy, final-season vs career weighting scheme.

### 5.2 Target design (two heads)

- **Head A, on-field:** ordinal outcome from best-3-year Superflex fantasy points per game within the first 4 NFL seasons. Tiers: bust/backup, spot starter, QB2, QB1 season(s), elite multi-year QB1.
- **Head B, market:** peak dynasty market value (KeepTradeCut and/or FantasyCalc Superflex value) within 3 years of draft.

Head B is partly circular with draft capital by construction. For a trading product that is the point: Anthony Richardson's peak market value was real, capturable value regardless of his on-field outcome. Head A anchors the model to reality and prevents pure hype-chasing. Product exposes a keep-vs-flip weighting between the heads.

### 5.3 Modeling constraints (ML team)

- Sample: roughly 100 to 150 drafted QBs from 2012 to 2024 with usable labels; roughly 25 to 35 hits. This is a low events-per-variable regime. Clinical prediction literature (van Smeden et al. 2019; Riley et al.) says predictor selection is unstable and coefficients bias extreme below ~10 events per variable. Hence the 4-to-6 feature cap.
- Baseline model: regularized ordinal or logistic regression (ridge or elastic net) with shrinkage. Bayesian version with informative priors (strong prior on draft capital and rushing, weak on recruiting) is the preferred variant because it encodes the research directly and stabilizes small-sample estimates.
- Gradient boosting only with heavy constraints: max depth 2 to 3, monotone constraints on draft capital and rushing, cross-validated early stopping. Expect it to lose to regularized regression at this n; prove otherwise before shipping it.
- Leakage rules: no feature may encode information generated after the draft. Mock-draft-derived features must be timestamped and snapshotted as of a defined pre-draft date (recommend two snapshots: post-combine and draft-week).

---

## 6. Data Pipeline (Engineering)

### 6.1 Sources

| Source | Provides | Access (as of mid-2026) | Notes |
|---|---|---|---|
| CollegeFootballData API v2 | Season/game stats, PPA (EPA analog), usage, recruiting composite, player info | Free tier 1,000 calls/mo with key; Patreon Tier 3 ($10/mo) 75,000 calls/mo + GraphQL | v1 was shut down before the 2025 season; build on v2 only. No pressure/ADOT charting. |
| nflreadpy (nflverse) | Draft picks, combine, weekly NFL fantasy stats, ID crosswalks | Free, Python, Polars-based | Supersedes nfl_data_py; migrate to it now. FTN charting from 2022+ (CC-BY-SA). |
| Grinding the Mocks | EDP and draft-probability distributions, history to 2018 | Public dashboard, no clean API; scrape or contact author | Want the probabilistic outputs, not point EDP. |
| NFL Mock Draft Database | Consensus board (~90 boards, 500+ mocks) | Scrape | Secondary consensus source. |
| PFF | College passing grade, adjusted completion %, pressure-to-sack, BTT/TWP | PFF+ subscription (~$120/yr), no bulk API for individuals | Licensing decision required; fallback is CFBD PPA + derived accuracy proxies. |
| KeepTradeCut / FantasyCalc | Superflex dynasty market values (Head B labels) | FantasyCalc has a documented API; KTC requires scraping | Cache historical pulls; DynastyProcess GitHub archives backfill history. |
| PlayerProfiler | Breakout age, athletic profiles, comps | Existing source | Thin college charting; use for measurables and breakout age. |

### 6.2 Architecture

Raw pulls land immutably (JSON/parquet per source per snapshot date), staged into normalized tables, then a feature-store table per prospect per snapshot. FastAPI serves the ranking endpoint from the feature store; the ML layer reads snapshots only.

The single biggest engineering risk is **entity resolution**: mapping a college identity (CFBD athlete id) to an NFL identity (gsis/pfr ids via nflreadpy crosswalks) to fantasy-market identities (Sleeper, KTC, DynastyProcess db_playerids). Build the ID crosswalk as a first-class, tested component with manual override support. Every downstream join depends on it.

Secondary risks: scraper fragility (GTM, KTC, mock draft aggregators change markup; wrap scrapers with contract tests and cache aggressively), CFBD rate limits (budget calls, cache season pulls), and PFF terms (manual export workflows if no API; keep PFF-derived features optional so the model degrades gracefully without them).

### 6.3 Core schema sketch (feature store)

```
qb_prospect_snapshot (
  player_key, class_year, snapshot_date,
  edp_mean, p_top5, p_round1, p_day2, p_day3,
  age_draft_day, breakout_age, career_starts, early_declare,
  rush_ypg_adj, rush_att_pg, rush_td_pg,        -- sack-adjusted
  pff_pass_grade, adj_comp_pct, ppa_per_dropback,
  pressure_to_sack_pct, p2s_flag,
  comp_level, comp_sample_flag,
  recruit_composite, recruit_stars,
  ht, wt, forty
)
qb_outcome_label (
  player_key, class_year,
  sf_ppg_best3_within4, outcome_tier,           -- Head A
  ktc_peak_36mo, fc_peak_36mo                   -- Head B
)
```

### 6.4 Backfill scope

Classes 2012 to 2024. Full labels for 2012 to 2021; partial (market-value head only, or shorter windows) for 2022 to 2024. Mock draft history limits EDP features to 2018+; for 2012 to 2017 use actual draft slot as the capital feature and treat those classes as capital-known training data, clearly flagged.

---

## 7. Hypotheses to Test

Each hypothesis has a test method and a pass criterion. Evaluation protocol for all: leave-one-class-out cross-validation (LOCO), Spearman rank correlation against realized outcomes, consensus EDP ordering as the baseline.

**H1. The blend beats both components.** A model combining the draft-capital distribution with the residual features beats both capital-only and stats-only rankers. Test: LOCO across all classes. Pass: mean Spearman improvement of at least +0.10 over the capital-only baseline AND no held-out class where the blend is materially worse than capital-only.

**H2. Rushing is the dominant residual.** Sack-adjusted rushing production carries the largest residual coefficient, and ablating it degrades LOCO performance more than ablating any other non-capital feature. Test: ablation study. Pass: rushing ablation causes the largest drop; drop is statistically distinguishable from the next feature's under bootstrap.

**H3. Competition penalties do not fix low-level profiles; uncertainty widening does.** Point-rank multipliers for sub-FBS/small-sample QBs (the Lance case) cannot be tuned to a value that both demotes the busts and keeps the hits. Test: sweep the multiplier over held-out classes; separately, test a variance-widening flag with interval-based evaluation. Pass: no single multiplier value improves all classes, while flagged-profile prediction intervals achieve nominal coverage.

**H4. Probabilistic EDP beats point EDP for QBs.** Using P(range) features instead of a scalar EDP improves ranking on debated QBs specifically. Test: reconstruct historical GTM distributions 2018 to 2024; compare LOCO on the subset of QBs whose EDP-to-actual-slot error exceeded one round. Pass: measurable improvement on that subset without degradation elsewhere. Sub-test: quantify QB-specific EDP error and bimodality vs other positions.

**H5. Final-season efficiency beats career efficiency; career beats final for stability traits.** Test: fit variants weighting final season vs career for AY/A, accuracy, and grade; keep pressure-to-sack at career always. Pass: consistent LOCO ordering of the weighting schemes across classes.

**H6. Age weight is lower for QBs than the skill-position default.** Test: regularized weight sweep on the age term. Pass: optimal weight lands in the 0.05 to 0.15 band and the LOCO curve is flat above it, confirming down-weighting costs nothing.

**H7. The market head is more predictable than the on-field head.** Peak-KTC labels (Head B) yield higher LOCO correlation than the ordinal on-field labels (Head A), because Head B partly re-expresses consensus. Test: identical feature set, both heads. Pass: Head B correlation exceeds Head A by a meaningful margin, quantifying how much of the product is market prediction vs talent prediction. Product uses this to set default head weighting.

**H8. Pressure-to-sack works as a filter, not a feature.** Test: compare (a) continuous P2S feature, (b) binary >= 20% flag, (c) neither. Pass: (b) improves or matches (a) on LOCO while flagged players show a materially higher bust rate in Head A tiers.

**H9. The recruiting prior decays.** Recruiting composite adds signal for QBs with fewer than ~2 seasons of major-college production and approximately zero for 3+ year starters. Test: interaction term between recruiting rating and college sample size. Pass: interaction is negative and the main effect for large-sample QBs is indistinguishable from zero.

**H10. An irreducible-miss class exists and must be a product feature.** For the largest historical misses (Allen-type), no pre-draft feature or feature combination flags them without breaking other classes. Test: residual analysis of the top-5 absolute misses per head; adversarial search for any candidate feature that would have caught them, evaluated LOCO. Pass (expected): no such feature survives; the product ships uncertainty bands and, for F2-flagged profiles, declines to publish a point rank.

---

## 8. Evaluation Protocol (standing)

1. LOCO CV by draft class, never random splits. Classes are the unit of generalization and random splits leak class context.
2. Report per-class and mean Spearman, both heads, against two baselines: consensus EDP ordering and actual draft order.
3. Calibration: for the ordinal head, reliability of tier probabilities; for value bands, empirical coverage of nominal intervals.
4. Ship gate: the blend must satisfy H1's pass criterion on the frozen 2012 to 2023 backfill before any ranking is user-visible. If it fails, the product falls back to "EDP distribution + rushing adjustment + age adjustment" only, and we stop adding features.
5. Every draft class thereafter is a true out-of-sample test. Freeze pre-draft predictions publicly (internally timestamped) before each draft so evaluation is never retroactive.

---

## 9. Asks by Team

**Product.** Design for uncertainty as a first-class element: value bands, a confidence indicator, an explicit "insufficient data profile" state for F2-flagged prospects, and the keep-vs-flip head weighting control. Decide how we present the model's disagreement with market consensus, since disagreement cases (the Jackson/Hurts calls) are the entire value proposition but also where we will be most visibly wrong (the Lance calls).

**ML.** Own Sections 5.3, 7, and 8. Sequence: build the label sets first (both heads), then the capital-only baseline, then add residual features one at a time with ablations. Deliver H1 through H4 before any others; they determine the architecture.

**Engineering.** Own Section 6. Sequence: ID crosswalk first, then CFBD v2 + nflreadpy ingestion, then label sources (FantasyCalc API, DynastyProcess archives, KTC scrape), then mock-draft scrapers with snapshotting. PFF licensing decision needed early because it gates two features; the model must degrade gracefully without them.

Open questions: PFF individual-license terms for derived-data use in a product (Engineering + whoever owns legal risk); whether to contact Grinding the Mocks for data access rather than scraping (Engineering); minimum viable label window for 2023 to 2024 classes (ML); how public we make frozen pre-draft predictions (Product).

---

## 10. Risks

- **Circularity.** Both the capital proxy and the market-value head are downstream of the same public consensus. Part of the model is an efficient re-expression of that consensus. Acceptable for a trading tool; do not market it as independent scouting.
- **Small sample.** Roughly 25 to 35 hits total. Every conclusion carries wide error bars; the protocol in Section 8 exists to keep us honest.
- **Source fragility.** Two of the most important sources (GTM, KTC) have no official API. Scrapers will break during draft season, which is exactly when the product matters most. Cache, snapshot, contract-test.
- **The visible-miss problem.** The model's differentiated calls will sometimes be Lances, not Hurtses. Uncertainty presentation is not polish, it is the core risk mitigation.

---

## Appendix A: Backtest v0 script

`qb_backtest.py` (shipped alongside this document). Locked weights, pre-declared competition multipliers, embedded 2018 to 2021 dataset assembled from public records, Spearman evaluation against hand-assigned outcome ranks, plus the blend comparison. Intended to be superseded by the pipeline harness in Section 6; until then it is the reference implementation of the scoring formula and evaluation logic. Known caveats are in Section 4.4.

## Appendix B: Key sources

- Robinson, B. "Grinding the Bayes: A Hierarchical Modeling Approach to Predicting the NFL Draft" (CMSAC 2020). EDP methodology and accuracy.
- Wolfson, Addona, Schmicker. "The Quarterback Prediction Problem" (Journal of Quantitative Analysis in Sports, 2011). College/combine stats add little beyond draft position.
- Craig & Winchester (European Journal of Operational Research, 2021). College rushing predicts NFL QB performance; college passing does not.
- Eager, E. "Quarterbacks in control: who controls pressure rates" (PFF, 2019). Pressure and sack rates are QB-driven and stable college to pro.
- PFF college-to-NFL translation studies (passing grade r ~ 0.37 to 0.45; adjusted vs raw completion 0.35 vs 0.26).
- Konami Code hit-rate research (RotoWire/Footballguys): ~90%+ top-12 PPG rate for 100+ rush-attempt seasons since 2014.
- van Smeden et al. (2019); Riley et al. Sample-size and events-per-variable guidance for prediction models.
