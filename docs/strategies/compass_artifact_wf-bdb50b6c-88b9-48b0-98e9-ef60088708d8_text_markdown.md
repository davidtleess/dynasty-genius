# Phase 16 Research Brief — Engine A Rookie Signal Upgrade

## 1. Executive Recommendation

**Bottom line for David: Phase 16 should ingest the six verified birth dates immediately, run a validation-only bake-off on a position-bucketed (not isotonic-stepped) draft-capital transform, and add only TWO new Engine A features — WR Breakout Age and WR final-season YPRR — both behind a validation gate.** Everything else (TPRR, MTF/G, CPOE, EPA, alignment data) belongs in xVAR/display or in a separate Phase 17 backlog. The strongest evidence in the 2015-present era is that (a) NFL draft capital and age remain the two dominant signals for WR/TE, (b) age-at-draft is NOT a meaningful RB signal once draft capital is controlled (per Ryan Heath, Fantasy Points, 2026 RB Rankings: *"Chronological age doesn't seem to matter as much at RB; unlike at WR and TE, my model wasn't made any more predictive by adjusting for age, so I don't do it directly"*), and (c) WR draft-capital decay is steeper than RB — the opposite of the user-supplied hypothesis. Do not promote a production model change in Phase 16 without a backtest showing ≥3% lift in early-career fantasy PPG MAE over the current draft-capital + age baseline.

## 2. Age Blocker Findings Table

All six birth dates are verifiable from at least one Tier-1 source (Wikipedia cross-checked against an official school bio, NFL.com prospect page, or team page). All six are confirmed 2026 NFL Draft picks — no class discrepancies. The only conflict is Kevin Coleman Jr. (one secondary source asserts "February 2004" while the school bio and Wikipedia agree on Sept 10, 2003); the school bio takes precedence.

| Player | Verified Birth Date | Primary Source URL | Confirming Source | Confidence | Implementation Implication |
|---|---|---|---|---|---|
| Omar Cooper Jr. | Dec 14, 2003 | iuhoosiers.com official roster bio ("born on Dec. 14, 2003") | en.wikipedia.org/wiki/Omar_Cooper | **Verified** | Ingest into identity file (`nfl_data_py_verified_nfl_draft`) |
| Chris Brazzell II | Sep 22, 2003 | en.wikipedia.org/wiki/Chris_Brazzell_II | utsports.com roster bio (confirms parents/HS); NFL.com prospect page | **Verified** | Ingest into identity file |
| Mike Washington Jr. | Jul 3, 2003 | steelersdepot.com 2026 scouting report ("Birthday: July 3, 2003 (22)") | en.wikipedia.org/wiki/Mike_Washington_Jr.; raiders.com team page | **Verified** | Ingest into identity file |
| Kevin Coleman Jr. | Sep 10, 2003 | mutigers.com official Missouri bio ("PERSONAL: Born September 10, 2003") | en.wikipedia.org/wiki/Kevin_Coleman_Jr. | **Verified (conflict flagged)** | Ingest; flag NFLDraftBuzz's "February 2004" claim as incorrect |
| Emmanuel Henderson Jr. | Mar 21, 2003 | en.wikipedia.org/wiki/Emmanuel_Henderson_Jr. | essentiallysports.com biographical profile; kuathletics.com bio | **Verified** | Ingest into identity file |
| Jam Miller (Jamarion) | Apr 29, 2004 | en.wikipedia.org/wiki/Jam_Miller | si.com/college/alabama "four-year contributor"; nfldraftbuzz.com profile | **Verified** | Ingest into identity file (legal name Jamarion Miller) |

**Note:** All six were April 2026 draft picks: Cooper (R1.30, NYJ), Brazzell (R3.83, CAR), Washington (R4.122, LV), Henderson (R6.199, SEA), Miller (R7.245, NE), and Coleman (Day 3, MIA per draft trackers). All six can now exit PRE_MODEL and receive standard Engine A scoring.

## 3. Evidence Table for Production Signal Candidates

| Claim | Source | Position | Confidence | Proposed Feature | Governance Status |
|---|---|---|---|---|---|
| Breakout Age <20 is meaningfully predictive at every NFL draft round | RotoViz (Shawn Siegele & Frank DuPont, Jan 2014 — *introduced the metric*); DLF (Peter Howard, 2018 follow-up by draft round) | WR | High | `breakout_age` (continuous) | **Model-ready (with validation)** |
| Final-season college YPRR is among the most predictive WR prospect signals | Fantasy Points (Ryan Heath, 2026 Rookie WR Rankings); Elite Drafters model (Substack/Fantasy Footballers, Jun 2025) | WR | High | `wr_final_yprr` | **Model-ready (with validation)** |
| TPRR adds incremental signal beyond YPRR but with smaller effect | RotoViz "Checking All the Boxes, Part 1" (May 2025); Fantasy Points | WR | Medium | `wr_final_tprr` | **Validation-only** |
| College Dominator Rating is highly correlated with breakout age (multicollinear) | PFF; PlayerProfiler glossary | WR/TE | High | — | **Context-only** (don't add both) |
| First Downs per Route Run (1D/RR) ≥ 8% is a useful WR threshold | FantasyData "Beneath the Surface" (1D/RR study, 2018-23 classes) | WR | Medium | `wr_1drr` | **Validation-only** |
| Draft capital + age + YPRR + breakout age is the canonical 4-input WR stack | Elite Drafters; Fantasy Points; Fantasy Life "Super Model" | WR | High | (composite) | **Model-ready** |
| RB Yards After Contact + the catch per game is highly predictive of NFL hit | Fantasy Points (Heath, 2026 RB Rankings) | RB | Medium-High | `rb_yacontact_per_game` | **Validation-only** |
| Receiving production (rec yards, receiving market share) outpredicts rushing efficiency for RB fantasy: Pearson >0.3 vs PPR+N1 across a 10-year, 215-stat study | Legendary Upside Pearson study | RB | High | `rb_recv_yards_per_game` | **Model-ready (with validation)** |
| Missed Tackles Forced / game is more predictive than YPC | Fantasy Points (Heath RB model) | RB | Medium | `rb_mtf_per_game` | **Validation-only** |
| Explosive run rate (≥10 yd run %) correlates to NFL big-play upside | PFF 2026 RB rankings | RB | Medium | `rb_explosive_pct` | **Validation-only** |
| Chronological age adjustment does NOT improve RB models, verbatim: *"my model wasn't made any more predictive by adjusting for age, so I don't do it directly"* | Fantasy Points (Heath, 2026 RB Rankings) | RB | High | — | **Reject as input; keep as descriptor** |
| One-hit-wonder RBs (1 strong season, weak prior) have poor NFL track record relative to draft capital | Fantasy Points (Heath, Mike Washington analysis) | RB | Medium | `rb_career_consistency_flag` | **Validation-only** |
| Designed rushing + scramble production is the differentiating QB fantasy signal | 4for4 "Most Predictable Quarterback Stats"; PFF 2026 rushing QB analysis | QB | High | `qb_rush_ypg` | **Model-ready (with validation)** |
| QB rate of >0.55 fantasy pts/dropback strongly predicts next-year ceiling | 4for4 partial-dependence plot analysis | QB (NFL Y1+) | High | — | **Context-only** (NFL-side, not college rookie input) |
| CPOE and EPA/play improve QB college projection but CFBD does not expose CPOE cleanly; pull EPA/play instead | CFBD API docs; nflverse | QB | Medium | `qb_college_epa_play` | **Validation-only** |
| Rounds 3 and 6 have produced zero rookie QB1 seasons over the last 11 years; only 4 of 90 non-first-round QBs have produced a QB1 season (Hurts, Prescott, Howell, Purdy) | Dynasty Nerds "How NFL Draft Capital Predicts Success" | QB | High | (captured by draft capital) | **Context-only** |
| TE Round 1 draft capital → 10 of 11 produced ≥1 TE1 season (O.J. Howard the lone exception) | Dynasty Nerds | TE | High | (captured by capital) | **Context-only** |
| TE Day 2: *"27% hit rate for TE1 seasons and 34% for top-20 finishes"*; Day 3 R4-5 still produces hits (Kittle, Schultz, Ferguson) | Dynasty Nerds | TE | High | (captured by capital) | **Context-only** |
| TE YPRR and MTF/G are predictive incremental signals (Mark Andrews / Brock Bowers / Pitts cohort) | Fantasy Points (Heath TE model) | TE | Medium | `te_yprr`, `te_mtf_per_game` | **Validation-only** (small sample) |
| TE alignment (inline vs flex) % shifts fantasy ceiling | PFF | TE | Medium | `te_flex_route_pct` | **Validation-only** |
| PFF grades as model inputs: PROHIBITED by spec | n/a | All | n/a | — | **Reject (governance)** |
| Fuzzy identity matching: PROHIBITED by spec | n/a | All | n/a | — | **Reject (governance)** |

## 4. Position-by-Position Recommendations

### Wide Receiver
The 2015-present evidence converges on a **4-input core** for WRs: (1) NFL draft capital, (2) age-at-draft, (3) final-season YPRR, (4) breakout age. PFF/RotoViz/Fantasy Points all use variants of this stack. Beyond this, TPRR, 1D/RR, and dominator add incremental but heavily-correlated signal. **Recommendation:** Add breakout age and YPRR as Engine A features with a backtest gate. Add TPRR and 1D/RR to xVAR display only — they are too correlated with YPRR to justify both in production until correlation/VIF analysis is run. WR draft capital decays steeply: per Campus2Canton (Peter Howard data, since 2001), Round 1 WR top-24-ever hit rate is 48.7%; Round 2 is 34%; Round 3 is 23.4%. Per FantasyPros (Andrew Erickson, Apr 2026), R4 WRs have produced exactly one rookie top-50 season in 35 attempts since 2013 (Amon-Ra St. Brown) and R6+ WRs have produced **zero** top-36 rookie seasons since 2013. **Therefore the user-supplied hypothesis that WR draft capital remains predictive "deeper than RB" is partially incorrect:** WR remains *more* predictive at the top of the draft, but Day 3 WR hit rates collapse harder than Day 3 RB hit rates. This finding should inform the transform choice in §5.

### Running Back
The college signals that survive 2015-present scrutiny are: receiving market share, yards after contact + after catch per game, missed tackles forced per game, and explosive run rate. Multi-year consistency matters — one-hit-wonders (Mike Washington's profile, e.g.) underperform draft capital. **Critically, chronological age-at-draft does NOT improve RB models after controlling for capital** (Ryan Heath, Fantasy Points). This means Engine A should *de-emphasize* age for RB-bucket scoring relative to WR/TE. Recommendation: add `rb_recv_yards_per_game` as the single new RB Engine A input (highest evidence-to-cost ratio); push YAC/MTF/explosive% into xVAR display until a multi-feature backtest is run. Day 2 RBs (R2-R3) have a clear cliff: per Dynasty Nerds "How NFL Draft Capital Predicts Success," *"Out of 161 running backs drafted, only 9 have given us RB1 seasons"* on Day 3, while Day 2 RBs deliver ~28% top-30 hit rate — confirming the "top-of-R3 cliff" the user flagged.

### Quarterback
The signal hierarchy for QB rookies is well-established: **draft capital >> rushing production >> everything else**. Per Dynasty Nerds, since 2015 only 5 QBs have produced a rookie QB1 season; 4 were Round 1 picks; Rounds 3 and 6 have produced zero QB1 seasons in 11 years. Mobile/rushing QBs dominate the top of fantasy: 4for4's PDP shows >0.55 fantasy points per dropback as the league-breaker threshold, almost always rushing-driven. **Recommendation:** Add `qb_rush_ypg` (college designed + scramble yards per game) as a single new QB Engine A feature. CPOE is theoretically additive but CFBD does not expose it cleanly — pull EPA/play instead (`qb_college_epa_play`) as a validation-only candidate. Games-started count and SOS belong in context-only display.

### Tight End
TE is the position where the small-sample warning matters most. Round 1 TEs are near-locks (10/11 ever produced a TE1 season since the cohort began, O.J. Howard the only miss); per Dynasty Nerds, *"Day 2 tight ends offer some decent outcomes for fantasy football, with a 27% hit rate for TE1 seasons and 34% for top-20 finishes"*; Round 4-5 has produced Kittle / Schultz / Ferguson / Goedert. **The slow-development curve is real** and means rookie-year fantasy production is a weak signal — Engine A should suppress its rookie-year output certainty for TEs, not add more features. The strongest analytical candidates (YPRR, MTF/G, route participation) all suffer from <10 hits/year cohort sizes. **Recommendation:** Do NOT add new TE production features in Phase 16. Instead, widen the TE uncertainty interval in xVAR display. Revisit in Phase 18+ when the 2026-2027 cohorts are scored.

## 5. Draft-Capital Transform Recommendation

**Vote: position-bucketed log-decay, validated via bake-off before any production change. Reject pure isotonic-step.**

Reasoning:
- A single linear/log-decay curve across all positions is demonstrably wrong given the differential cliffs documented in §3-4. QB has a Round-1 cliff (no Round 3/6 QB1s in 11 years), WR has a steeper Round-2→Round-3 cliff than RB, and TE has unusual mid-Round-4/5 hits (Kittle, Schultz).
- Position-isotonic-step is tempting because it perfectly fits historical cliffs, but it overfits to small samples (especially at TE) and creates discontinuous gradients that destabilize trade-value math and rank-delta interpretation. The Phase 13 validation work already exposed this risk.
- Position-bucketed log-decay (separate log-decay curve per position, with bucket boundaries at draft-round transitions) preserves smoothness, captures the major cliffs, and is robust to small samples. This is closest to the consensus structure used by Fantasy Points and Fantasy Life Super Models.

**Phase 16 decision: run a bake-off, not a spec.** Specifically: backtest (a) current linear/log capital, (b) position-bucketed log, (c) position-isotonic-step on the 2015-2022 rookie cohorts (held out: 2023-2024 cohorts; 2025 too recent for stable outcomes). Promotion criterion: bucketed must beat baseline by ≥3% in early-career fantasy PPG MAE AND not regress TE MAE by more than 1%. If both new transforms tie within 1%, default to bucketed (less overfit risk).

## 6. Conflicts or Weak Evidence

- **Kevin Coleman Jr. birth date conflict.** NFLDraftBuzz states "February 2004 birthday." Official Missouri Athletics roster bio states "Born September 10, 2003." Wikipedia agrees with the school. Resolution: trust the school bio; flag the secondary source as incorrect.
- **Pre-2014 vs post-2015 era WR data.** The Breakout Age metric was introduced by RotoViz's Shawn Siegele and Frank DuPont in **January 2014** (per PlayerProfiler's terms glossary: *"In January 2014, Rotoviz writers Shawn Siegele and Frank DuPont introduced the fantasy football world to the Breakout Age metric"*); the 2021 RotoViz expansion explicitly used "All WRs from 2000-2018 drafts — 849 players." Sample skew toward outside WRs vs. modern slot-heavy usage means raw thresholds (e.g., "BOA <20") may understate slot-WR ceilings. FLAG, do not average.
- **WR vs RB draft-capital depth.** The user-supplied hypothesis ("WR draft capital remains predictive deeper than RB/QB") is partially wrong post-2015. WR is *more* concentrated at the top and Day 3 WRs collapse harder than Day 3 RBs. Recommendation reflects this.
- **TE samples.** Every TE production claim rests on <100-player cohorts. Confidence-medium at best.
- **CPOE availability.** CFBD does not publish CPOE as a first-class metric; reconstruction from PBP is non-trivial. Treat as out-of-reach for Phase 16.

## 7. Data Source Feasibility

**Free/structured (can feed the repo directly):**
- `nfl_data_py` — already the identity backbone; verified.
- **CFBD Python client** (`cfbd` package) — per the CFBD Blog REST API v2 GA announcement: *"The free tier has been set at 1000 monthly calls (tiering and call limits subject to change)"* and *"Patreon Tier 3 ($10/mo) - 75,000 monthly calls (+ access to the GraphQL API with realtime data subscriptions)."* Provides player season stats, EPA, returning production, recruiting, advanced game stats. Adequate for receiving yards, target share, college games started. **Recommended to upgrade to Patreon Tier 3 ($10/mo)** for 75k calls and GraphQL access — this becomes the primary college stats source.
- `nflverse` / `nflreadr` — for NFL-side outcomes used in training labels.
- College Football Reference / Sports Reference (CFB) — scraping needed; rate-limited; use as cross-check, not primary.

**Requires manual export or paywall:**
- **YPRR, TPRR, 1D/RR, route counts** — only PFF and Fantasy Points publish these at the college level. Full historical needs a paid pull. Plan: manual annual export at end of college season, cached in repo as `pff_college_routes.csv`. Do NOT use PFF *grades*, only raw routes/targets/yards. This is governance-compliant because raw routes are objective data, not subjective grades.
- **Missed tackles forced** — PFF charted data; same constraint as above.
- **Alignment data (inline vs flex)** — PFF only; defer to xVAR display.

**Requires identity audit before ingestion:**
- Any PFF/Fantasy Points export must be joined to `nfl_data_py_verified_nfl_draft` on a verified ID (gsis_id where present, otherwise an explicit name+school+class-year hash). NO FUZZY MATCHING. Players who do not join exactly stay at PRE_MODEL until manually resolved.

## 8. Explicit Out-of-Scope Items

Phase 16 should NOT touch:
- PFF grades as model inputs (governance violation).
- Fuzzy identity matching (governance violation).
- KTC, FantasyCalc, FantasyPros consensus, dynasty rankings, ADP — these remain overlay-only.
- xVAR formula changes (Phase 15 baseline is frozen).
- UI / display layer changes (not a Phase 16 deliverable).
- TE production features (defer to Phase 18+).
- Combine athletic testing (40-time, SPARQ, broad jump) — a separate workstream; Phase 16 is about college production signals, not athletic profile.
- Backfilling birth dates by inference. Every missing DOB must remain PRE_MODEL until verified from a Tier-1 source.

## 9. Risks and Failure Modes

- **Adding YPRR creates a covert PFF dependency.** Even with raw route data only, the source is paywalled and license-restricted. Mitigation: cache annual snapshot in repo and treat the source as "external proprietary data" with a documented refresh procedure.
- **Breakout Age + YPRR collinearity.** Both signals encode "produced young," and adding both without VIF analysis can inflate variance. Mitigation: run correlation and VIF in the bake-off; if VIF >5, retain only YPRR.
- **Position-bucketed transform increases parameter count.** Risk of overfitting to small TE/QB samples. Mitigation: regularize via shared global log-decay shape with position-specific scale/intercept; do not let TE bucket fit its own curve shape.
- **Day 3 hit-rate near-zero for WR.** Engine A may correctly assign near-zero scores to R6-R7 WRs, but this conflicts with anchor-effect rookie ADP. Mitigation: keep market data overlay-only; do not let it leak in.
- **Coleman birth-date conflict.** If NFLDraftBuzz is correct and the school is wrong, his age-at-draft shifts by ~5 months — non-trivial for an age-sensitive WR model. Mitigation: log both candidate DOBs in the identity file with `source_priority` and re-verify if a Pro Football Reference page publishes a definitive value post-draft.
- **CFBD rate limits** (1,000 calls/month on free tier) can stall ingestion mid-season. Mitigation: nightly cron + Patreon Tier 3 upgrade ($10/mo for 75,000 calls).
- **One-hit-wonder RB feature** can be gamed by transfer portal players (Washington's 2025 Arkansas season). Mitigation: explicit "best two seasons" rather than "career trend slope."

## 10. Proposed Phase 16 Workstreams and Ordering

1. **W1 (1-2 days): Identity unblock.** Ingest the six verified birth dates from §2 into `nfl_data_py_verified_nfl_draft`. Move all six rookies from PRE_MODEL to scored. Smoke-test that Engine A produces sane DVS/xVAR for each.
2. **W2 (3-5 days): CFBD ingestion layer.** Add `cfbd` client wrapper, environment variable for API key, nightly cron, cached parquet output. Endpoints needed: player season stats, returning production, advanced game stats. Tests: deterministic identity-join on 2015-2024 verified rookies.
3. **W3 (1-2 weeks): Backtest harness.** Build the bake-off framework that scores three transforms (current, bucketed log, isotonic step) against held-out 2023-2024 rookie cohorts. Metrics: MAE on Y1-Y3 PPR PPG, Spearman rank correlation, and bucket-level hit-rate accuracy.
4. **W4 (1-2 weeks): WR candidate features.** Add `breakout_age` and `wr_final_yprr` as candidate Engine A features behind a feature flag. Run VIF and ablation. Promote only if ≥3% MAE lift over baseline AND no TE regression >1%.
5. **W5 (3-5 days): RB candidate feature.** Add `rb_recv_yards_per_game` behind a feature flag; ablation only.
6. **W6 (3-5 days): QB candidate feature.** Add `qb_rush_ypg` behind a feature flag; ablation only.
7. **W7 (1 week): Transform decision & promotion.** Based on bake-off, promote at most one transform change + the WR features that passed §4 gate. Everything else moves to Phase 17 backlog.
8. **W8 (2-3 days): Documentation & rank-delta regression test.** Document all changes; add a regression test that flags any rookie whose Engine A rank moves more than 5 spots vs. Phase 15 frozen output for unchanged inputs.

## 11. Acceptance Criteria for the Phase 16 Spec

- All six PRE_MODEL rookies in §2 produce non-null DVS, xVAR, xVAR rank, DVS rank, and rank delta.
- `cfbd` ingestion is deterministic: re-running on the same date yields byte-identical parquet.
- Identity join coverage ≥99% for 2015-present rookies; remaining ≤1% are explicitly listed in a `manual_review.csv` (not silently dropped, not fuzzy-matched).
- Bake-off output is a committed artifact: `phase16_transform_bakeoff.csv` with one row per candidate transform and columns for MAE, Spearman, TE-MAE delta, and a pass/fail flag against the ≥3% / ≤1% promotion gates.
- Any feature promoted to production must have: (a) an ablation row in the bake-off, (b) a documented data-source provenance, (c) a unit test that fails if the feature's mean drifts >2σ on a synthetic 2015-2024 input.
- A documented rollback path: every Phase 16 change must be revertable via a single feature flag.
- Market data (KTC, FantasyCalc, FantasyPros, ADP) does not appear in any feature import path. Enforced by a grep-based CI check.

## 12. Open Decisions for David

1. **PFF/Fantasy Points college-routes data**: are you willing to license / manually export raw YPRR and TPRR? Without this, the WR YPRR feature cannot be added and Phase 16's biggest expected lift evaporates. Fallback: use CFBD targets and team passing attempts to construct a target-share proxy, which is weaker but free.
2. **Promotion threshold**: ≥3% MAE lift is a starting proposal. Tighter (≥5%) protects against overfit; looser (≥1%) ships more changes but risks noise.
3. **TE deferral**: confirm you are OK leaving TE production features for Phase 18+ rather than half-shipping them now.
4. **One-hit-wonder RB flag**: should this be a binary feature, a continuous "career consistency" score, or just an xVAR display badge? My recommendation is display-only until the bake-off justifies more.
5. **Coleman DOB conflict resolution**: confirm preference is school-bio-wins (Sept 10, 2003) over the secondary "February 2004" claim. I recommend yes, with a `dob_source` audit column in the identity file.
6. **CFBD Patreon tier**: $10/mo for 75k calls vs free 1k/mo. Recommend yes given the volume of historical backtest pulls planned in W2-W3.
7. **Whether the WR Round 6+ zero-hit-rate finding should drive a hard "do not draft" badge in xVAR display.** This is a market/decision UI question, not a model question; flagged here because it crossed my desk.

---

### Completion Table

| Spec Item | Status |
|---|---|
| §1 Executive recommendation | ✅ |
| §2 Age blocker findings table (6 players × 5 columns) | ✅ |
| §3 Evidence table for production signals | ✅ |
| §4 Position-by-position recs (WR/RB/QB/TE) | ✅ |
| §5 Draft-capital transform vote + spec-vs-bake-off | ✅ Bake-off |
| §6 Conflicts / weak evidence | ✅ |
| §7 Data source feasibility | ✅ |
| §8 Out-of-scope items | ✅ |
| §9 Risks & failure modes | ✅ |
| §10 Phase 16 workstreams | ✅ |
| §11 Acceptance criteria | ✅ |
| §12 Open decisions for David | ✅ |
| All 6 birth dates verified, conflict flagged | ✅ |
| Every signal classified (model-ready / validation-only / context-only / reject) | ✅ |
| Pre-2014 evidence flagged with caveat | ✅ |
| No PFF grades / no fuzzy matching / no market data as input | ✅ |
| Concrete enough for developer to write a Phase 16 spec | ✅ |