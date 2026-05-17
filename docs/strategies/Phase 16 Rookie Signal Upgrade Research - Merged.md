# Phase 16 Rookie Signal Upgrade Research — Merged
*Engine A Rookie Signal Upgrade*

Date: 2026-05-17
Status: FINAL MERGED — approved by David
Sources: Compass report (spine), Dynasty Rookie Signal Upgrade Research (supporting material)

---

## 1. Executive Recommendation

**Phase 16 should first unblock the six PRE_MODEL rookies through verified birth dates, then run validation-only bake-offs for draft-capital transforms and a small set of college production candidates. The only near-term Engine A feature candidates with enough evidence to prioritize are WR breakout age and WR final-season YPRR. Position-isotonic draft capital remains a candidate, not an approved production change.**

Phase 16 is a **data engineering and model validation sprint only**. No feature is promoted to production without a backtest gate showing measurable lift over the current 3-feature baseline. Specifically:

- Ingest and verify the six blocked birth dates against identity contract rules.
- Run a validation-only bake-off across three draft-capital transform candidates: current linear, position-bucketed log-decay, and position-isotonic-step.
- Phase 16 WR feature candidates: **breakout age** and **RYPTPA** are the feasible-now primary candidates (CFBD-computable, no paywall). **YPRR** enters the bake-off only if PFF/Fantasy Points route data is exported under a governed process. If YPRR beats RYPTPA cleanly and passes VIF and coverage checks, it can supersede RYPTPA in the model-change spec.
- All other signal candidates (TPRR, 1D/RR, RB receiving/YAC/MTF, QB rushing/EPA) enter validation-only research queues. None are promoted from this brief alone.

**What does not change in Phase 16:**
- xVAR formula and replacement anchors (display/decision currency, not model input)
- Engine B production artifacts
- Any UI or board changes
- TE production features (deferred Phase 18+)
- Market data (overlay-only — permanently)

---

## 2. Age-Blocker Findings

All six players are confirmed 2026 NFL draftees. Candidate birth dates have been identified from multiple sources. **Ingestion requires a source audit per identity contract before writing to `prospect_identity_2026.json`.** Only official school/team roster bios and Pro Football Reference player pages qualify as Tier-1 sources. Wikipedia, Reddit, fantasy scouting profiles, and secondary betting/lines pages are supporting or conflicting evidence only — they may confirm a Tier-1 finding but cannot stand alone.

| Player | Candidate Birth Date | Tier-1 Source | Supporting Sources | Conflict | Implementation |
|---|---|---|---|---|---|
| Omar Cooper Jr. | Dec 14, 2003 | IU Hoosiers official roster bio; NYJ roster | Wikipedia | None | Ready to ingest after source audit |
| Chris Brazzell II | Sep 22, 2003 | UT Sports official roster bio; CAR roster | Wikipedia | None | Ready to ingest after source audit |
| Mike Washington Jr. | Jul 3, 2003 | LV Raiders official roster; Wikipedia (family confirmation cited) | Steelers Depot scouting report | Lines.com states Mar 15, 2002 — reject as tertiary/error | Ingest Jul 3, 2003; log conflict and rejected source in identity file |
| Kevin Coleman Jr. | Sep 10, 2003 | Missouri official roster bio; MIA roster | Wikipedia; FTN Fantasy scouting | NFLDraftBuzz states "Feb 2004" — reject; school bio takes precedence | Ingest Sep 10, 2003; log NFLDraftBuzz conflict in identity file |
| Emmanuel Henderson Jr. | Mar 21, 2003 | SEA Seahawks official roster; KU Athletics bio | Wikipedia; Fox Sports | None | Ready to ingest after source audit |
| Jam Miller | Apr 29, 2004 | NE Patriots official roster; Wikipedia | Wolf Sports; SI.com | None | Legal name Jamarion Miller; ingest Apr 29, 2004 after source audit |

**Resolution note (Washington Jr.):** Lines.com reports March 15, 2002 — a ~16-month discrepancy. Primary roster and family-verified sources confirm July 3, 2003. The correct date is July 3, 2003. Log `dob_conflict_source: "lines.com, March 2002, rejected"` in the identity file.

**Resolution note (Coleman Jr.):** NFLDraftBuzz states "February 2004." Missouri's official bio and Wikipedia agree on September 10, 2003. School bio takes precedence. Log the conflict.

Once all six are ingested, they exit PRE_MODEL and receive standard Engine A scoring at their verified fractional age-at-draft.

---

## 3. Production Signal Evidence

Governance status column applies to Engine A feature use only. Context-only signals may appear in the PVO as display fields or caveat annotations.

| Signal | Position | Evidence Summary | Sources | Governance Status |
|---|---|---|---|---|
| WR breakout age (<20 at first 20% dominator) | WR | Early dominance predicts NFL target-earning; validated across 2000–2018 draft classes; multi-source consensus | RotoViz (Siegele & DuPont 2014); DLF (Howard 2018); PlayerProfiler | **Model-ready with validation gate** |
| WR final-season YPRR | WR | Higher-fidelity route-level candidate; published predictive lift; draft/age/YPRR/breakout is canonical 4-input WR stack | Fantasy Points (Heath 2026); Elite Drafters; RotoViz (May 2025) | **Model-ready with validation gate (conditional)** — enters bake-off only if PFF/Fantasy Points route data exported under governed process; RYPTPA is preferred when route data unavailable |
| WR TPRR | WR | Incremental over YPRR; smaller effect; high collinearity risk with YPRR | RotoViz "Checking All the Boxes" | **Validation-only** |
| WR 1D/RR | WR | More stable than YPRR for possession receivers; filters low-volume deep threats | Fantasy Points (Heath 2024, 2025) | **Validation-only** |
| RYPTPA (WR/RB) | WR, RB | 0.36 Pearson to NFL PPR PPG, scheme-agnostic; computable from CFBD without paywall | Dynasty Daydream; Fantasy Life | **Model-ready with validation gate (primary automated candidate)** — Phase 16 default WR efficiency candidate; no paywall, CFBD-computable; YPRR supersedes if it beats RYPTPA cleanly and passes VIF/coverage checks |
| RB receiving production (college target share / recv yards per game) | RB | Passing-game involvement is the most resilient RB floor signal in PPR | Legendary Upside Pearson study; Fantasy Points | **Validation-only** |
| RB YAC per attempt | RB | Isolates individual talent from OL quality; translates to NFL when OL advantage regresses | Fantasy Points; PlayerProfiler | **Validation-only** |
| RB missed tackles forced / game | RB | More predictive than YPC; requires PFF charted data | Fantasy Points (Heath 2026 RB model) | **Validation-only** |
| QB rushing yards per game | QB | Rushing floor is the dominant Superflex fantasy signal beyond draft capital | 4for4; Fantasy Points | **Validation-only** |
| QB EPA/play (college) | QB | Outperforms raw TD/INT; CFBD requires PBP computation, not a direct endpoint | CFBD; nflverse | **Validation-only** |
| QB CPOE (college) | QB | Theoretically additive but CFBD does not expose CPOE as a first-class metric; reconstruction from PBP non-trivial | CFBD API docs | **Out of reach for Phase 16** |
| Dominator rating | WR, TE | Highly collinear with breakout age — if breakout age is included, do not add dominator separately | PFF; PlayerProfiler | **Context-only** (don't add both) |
| QB games started / SOS | QB | Descriptive, not independently predictive after capital | Various | **Context-only** |
| TE YPRR, MTF/G, alignment % | TE | Individually predictive but <10 hits/year cohort; sample too small for reliable model lift | Fantasy Points; PFF | **Context-only** (defer Phase 18+) |
| RB age-at-draft | RB | Does NOT improve RB models after controlling for capital: *"my model wasn't made more predictive by adjusting for age"* | Fantasy Points (Heath 2026 RB Rankings) | **Reject as RB model input** (keep as descriptor) |
| PFF grades | All | Constitutionally banned — subjective charting, not falsifiable | Governance | **Reject** |
| Market/ADP/KTC | All | Target leakage and circular logic | Governance | **Reject** |
| Fuzzy identity matching | All | Constitutionally banned in production | Governance | **Reject** |
| Scheme labels (zone/gap) | RB | Too noisy, manual charting, no structural stability | Fantasy Points | **Reject** |

---

## 4. Position-by-Position Recommendations

### Wide Receiver

The evidence consensus (RotoViz, Fantasy Points, Elite Drafters) converges on a 4-input core: draft capital, age, breakout age, final-season YPRR/RYPTPA. Phase 16 starts with the two candidates that are feasible now without a paywall dependency: **breakout age** and **RYPTPA**.

Three WR candidates, distinct roles:
- **Breakout age** — primary age/early-dominance timing candidate. Validated across 2000–2018 draft classes; multi-source consensus.
- **RYPTPA** — primary automated WR efficiency candidate. CFBD-computable, no paywall, 0.36 Pearson correlation. Phase 16 default.
- **YPRR** — higher-fidelity route-level challenger. Enters the bake-off only if PFF/Fantasy Points route data is exported under a governed process. If YPRR beats RYPTPA cleanly and passes VIF and coverage checks, it supersedes RYPTPA in the model-change spec. Do not treat as default when route data availability is unconfirmed.

Key findings from evidence:
- Round 1 WR top-24-ever hit rate ≈48.7%; Round 2 ≈34%; Round 3 ≈23.4%. R4 WRs have produced one rookie top-50 season in 35 attempts since 2013 (Amon-Ra). R6+ WRs: zero top-36 rookie seasons since 2013. WR draft capital decays steeply — more concentrated at the top than RB.
- Breakout age was introduced in January 2014; coverage pre-2014 exists but slot-heavy usage evolution means raw thresholds may understate ceiling. Flag in any pre-2015 training data.
- RYPTPA + YPRR collinearity: if both are available, run VIF before adding both. If VIF >5, retain only YPRR.

TPRR and 1D/RR are validation-only queue candidates.

### Running Back

Draft capital is the overwhelmingly dominant signal for RBs; receiving production is the most resilient secondary signal in PPR formats. YAC/attempt and missed tackles isolate independent talent from OL.

Key findings from evidence:
- Age-at-draft does NOT improve RB models after controlling for capital. Engine A should not weight age for RBs the same way it does for WRs/TEs. This is a systematic correction.
- Day 2 RBs: ~28% top-30 hit rate. Day 3 RBs: ~9 of 161 have produced RB1 seasons. The R3 cliff is real.
- Receiving market share / college yards per team pass attempt are the top independent signal candidates.
- One-hit-wonder flag (strong final season, weak prior career — e.g., Washington Jr.'s profile): meaningful context, not yet validated as a model feature.

Phase 16 adds `rb_recv_yards_per_game` as the single RB candidate in the bake-off. YAC/MTF remain validation-only research.

**RB age de-emphasis — named governance decision (must resolve before bake-off spec):** The evidence finding that age does not improve RB models after controlling for capital is a model semantics change, not a feature selection detail. If Phase 16 changes how `age` is weighted for RBs, that is a structural change to the Engine A feature matrix. It requires an explicit governance artifact — "RB age de-emphasis candidate" — with its own validation gate (does removing/down-weighting age for RBs improve fold-level MAE without degrading WR/TE folds?) and an acceptance or rejection record committed before any RB feature bake-off begins. This decision cannot be absorbed silently into feature selection.

### Quarterback

Draft capital dominates. Since 2015, only 5 QBs have produced a rookie QB1 season; 4 were Round 1. Rounds 3 and 6 have zero QB1 seasons in 11 years. Rushing floor is the key Superflex differentiator.

Key findings from evidence:
- `qb_rush_ypg` (designed + scramble yards per game) is the single highest-evidence addition. Mobile QBs with average passing efficiency frequently outscore pure pocket passers in Superflex.
- CPOE is theoretically additive but CFBD does not expose it as a first-class metric. Treat as out of reach for Phase 16.
- EPA/play requires play-by-play reconstruction and is validation-only.

### Tight End

TE development curve is 2–3 years minimum. Round 1: 10/11 ever produced a TE1 season. Day 2: ~27% TE1 hit rate, ~34% top-20. Day 3/4 has produced Kittle, Schultz, Ferguson, Goedert — so **do not encode R4+ TE as a hard model near-zero**. That pattern belongs in context display, not model architecture.

Phase 16 adds no new TE production features. The sample (<10 hits/year) is too small for reliable lift from YPRR, MTF, or alignment signals. Revisit Phase 18+.

---

## 5. Draft-Capital Transform

**Phase 16 decision: run a bake-off. No production transform change until the bake-off passes.**

Three candidates to test:
1. **Current**: raw pick as linear feature
2. **Position-bucketed log-decay**: separate log-decay curve per position, bucket boundaries at round transitions. Smooth, robust to small samples, captures major cliffs.
3. **Position-isotonic-step**: non-decreasing step function fitted separately per position. Captures exact historical cliffs but overfits to small TE/QB samples and creates discontinuous gradients that can distort rank-delta interpretation.

Isotonic-step is a candidate, not the default winner. Position-bucketed log-decay is the preferred candidate per current evidence, but the bake-off result is authoritative.

**Promotion gate**: candidate must satisfy ALL of the following:
1. ≥3% aggregate MAE improvement over current linear on early-career PPR PPG
2. Improvement holds in **≥3 of 4 LOOCV folds** (aggregate alone is insufficient for a 150–200-row training set — a single held-out class can swing aggregate MAE by 3% on noise)
3. TE MAE does not regress by more than 1%

If two candidates tie within 1% on aggregate MAE, prefer bucketed log (lower overfit risk).

**Bake-off cohort**: 2015–2022 draft classes as training folds; 2023–2024 as holdout. 2025 too recent for stable outcomes. Per-fold LOOCV with immutable identity snapshot required before any promotion.

---

## 6. Data Source Feasibility

### Free / structured (can feed the repo directly)

- **`nfl_data_py`**: identity backbone, already in use. No change.
- **CFBD Python client** (`cfbd` package): structured college stats, EPA/play from PBP, returning production, recruiting. Free tier: 1,000 calls/month (likely insufficient for historical backtest pulls). **Recommend Patreon Tier 3 ($10/mo) for 75,000 calls + GraphQL access.** Provides: receiving yards, target share, team pass attempts, college games started, RYPTPA-computable fields.
- **`nflverse` / `nflreadr`**: NFL-side outcome labels for training.

### Requires manual export or paywall

- **YPRR, TPRR, 1D/RR, route counts**: PFF and Fantasy Points publish these at college level. Raw route/target/yard counts are governance-compliant (objective data, not subjective grades). Plan: manual annual export at end of college season, cached as `pff_college_routes.csv`. Do NOT use PFF overarching grades.
- **Missed tackles forced**: PFF charted data, same constraint.
- **Alignment data**: PFF only — defer to context display.

### Ingestion protocol (Bronze → Silver → Gold structure)

- **Bronze**: raw JSON/CSV from CFBD and Sports Reference, source timestamps preserved, unmodified structure.
- **Silver**: canonical identity resolution join using `nfl_data_py` verified IDs (gsis_id where present). **No fuzzy matching in production.** Unresolved rows routed to manual review queue, not silently dropped.
- **Gold**: cleansed feature vectors passed to Engine A validation harness.

Any PFF/Fantasy Points export must join to `nfl_data_py_verified_nfl_draft` on a verified ID. Players who do not join exactly stay PRE_MODEL until manually resolved.

---

## 7. Conflicts and Weak Evidence

- **Coleman Jr. birth date**: NFLDraftBuzz "February 2004" — reject. Missouri official bio + Wikipedia agree Sep 10, 2003. Log conflict, enforce school bio.
- **Washington Jr. birth date**: Lines.com "March 15, 2002" — reject. Primary roster + family-verified sources confirm Jul 3, 2003. Log and enforce.
- **Pre-2014 breakout age data**: metric introduced January 2014 by RotoViz. Pre-2015 data skews toward outside receivers pre-slot-revolution. Flag, do not average with post-2015 findings.
- **WR draft capital depth hypothesis**: evidence shows WR hit rates collapse harder on Day 3 than RB. WR is more concentrated at the top of the draft, not more forgiving deeper. R6+ WR zero top-36 rookie seasons since 2013.
- **Isotonic-step overfit risk**: TE cohort is ~40–60 rows; fitting a separate step function per position on this sample is unreliable. Bake-off gate will adjudicate.
- **CPOE**: CFBD does not publish CPOE as a structured endpoint. Reconstruction from raw PBP is non-trivial. Out of scope for Phase 16.
- **TE Day 3 "near-zero" as model instruction**: context, not model architecture. Day 4–5 has produced Kittle and Schultz; hard encoding would misrepresent the tails.

---

## 8. Explicit Out-of-Scope

- PFF grades as model inputs (governance violation, permanently banned)
- Fuzzy identity matching in production (governance violation)
- KTC, FantasyCalc, FantasyPros consensus, ADP — overlay-only
- xVAR formula or replacement anchor changes
- UI / board changes
- TE production features (Phase 18+)
- Combine athletic testing / RAS (separate workstream, not Phase 16)
- Birth date inference — every missing DOB must remain PRE_MODEL until verified from a Tier-1 source
- Any production model change without a passing bake-off artifact

---

## 9. Risks and Failure Modes

- **Breakout age + YPRR collinearity**: both encode "produced young." Run VIF before any production promotion; if VIF >5, retain only YPRR.
- **YPRR creates paywalled dependency**: raw route data from PFF is license-restricted. Cache annual snapshot, document refresh procedure, treat as "external proprietary data."
- **Position-bucketed transform increases parameter count**: risk of TE/QB overfit. Regularize by fitting shared global log-decay shape with position-specific scale/intercept.
- **Day 3 near-zero for WR**: Engine A will correctly assign near-zero scores to R6–R7 WRs. This creates anchor-effect tension with rookie ADP. Market overlay remains the only appropriate surface for that comparison — it cannot enter the model.
- **Coleman DOB conflict**: if NFLDraftBuzz is correct (5-month shift), age-at-draft changes non-trivially for an age-sensitive WR model. Mitigation: log both candidate DOBs and `dob_source` in identity file; re-verify against PFR post-draft.
- **CFBD rate limits**: 1,000/month free tier insufficient for multi-year historical backtest. Mitigation: Patreon Tier 3 upgrade ($10/mo).
- **Null coverage**: if CFBD API changes format, ingestion parser produces nulls for an entire incoming cohort. Mitigation: explicit null-handling in Engine A — missing advanced features trigger `signal_completeness` caveat in PVO and fall back to 3-feature baseline scoring.
- **One-hit-wonder RB flag**: transfer portal players with one strong final season may mislead a "career consistency" signal. Mitigation: use best-two-seasons rather than career trend slope.

---

## 10. Workstreams and Ordering

1. **W1 — Identity unblock** (1–2 days): source-audit all six birth dates against Tier-1 sources. Ingest confirmed entries into `prospect_identity_2026.json`. Re-run `scripts/refresh_prospect_cards.py`. Verify all six produce non-null DVS and xVAR. Commit.

2. **W2 — Source and ingestion feasibility** (3–5 days): add `cfbd` client wrapper with API key env var, nightly cron, cached parquet output. Endpoints: player season stats, returning production, advanced game stats. Deterministic identity join on 2015–2024 verified rookies (≥99% coverage gate). Manual review queue for unresolved rows.

3. **W3 — Draft-capital transform bake-off** (1–2 weeks): run all three transform candidates (current, bucketed log, isotonic-step) against 2015–2022 training cohort, 2023–2024 holdout. Immutable identity snapshot required. Metrics: MAE on Y1–Y3 PPR PPG, Spearman ρ. Commit artifact `phase16_transform_bakeoff.csv`. Promotion decision per §5 gate.

4. **W4 — WR feature candidate bake-off** (1–2 weeks): add breakout age and RYPTPA as primary candidates behind feature flags. YPRR enters as a conditional challenger only if governed PFF/Fantasy Points route data exists per §6. Run VIF analysis (if both RYPTPA and YPRR present, retain only the one with lower VIF if VIF >5). Promote only if ≥3% aggregate MAE lift AND improvement holds in ≥3 of 4 LOOCV folds AND no TE regression >1%.

5. **W5 — RB governance decision + candidate research** (3–5 days, conditional on data coverage): **Gate: RB age de-emphasis decision must be resolved and committed as a governance artifact before this workstream begins.** After that gate, add `rb_recv_yards_per_game` as single RB candidate. Ablation only.

6. **W6 — QB candidate research** (3–5 days, conditional on data coverage): add `qb_rush_ypg` as single QB candidate. Ablation only.

7. **W7 — Promotion decision** (1 week): based on bake-off artifacts, promote at most one transform change + WR features that cleared §10/W4 gate. Everything else moves to Phase 17 backlog.

8. **W8 — Documentation and regression tests** (2–3 days): document all changes. Add regression test flagging any 2026 rookie whose Engine A rank moves >5 spots vs. Phase 15 frozen output for unchanged inputs.

---

## 11. Acceptance Criteria

- All six PRE_MODEL rookies produce non-null DVS, xVAR, `xvar_class_rank`, `dvs_class_rank`, `rank_delta`.
- CFBD ingestion is deterministic: re-running on same date yields byte-identical parquet.
- Identity join coverage ≥99% for 2015–present rookies; remaining ≤1% listed in `manual_review.csv` — not silently dropped.
- Bake-off artifact committed: `phase16_transform_bakeoff.csv` with one row per candidate, columns for MAE, Spearman ρ, TE-MAE delta, fold-count-passing (must be ≥3 of 4), pass/fail flag.
- Any feature promoted has: (a) ablation row in bake-off, (b) fold-consistency ≥3 of 4 confirmed, (c) documented data-source provenance, (d) unit test failing if feature mean drifts >2σ on synthetic 2015–2024 input.
- RB age de-emphasis governance artifact committed before W5 begins.
- Rollback path documented: every Phase 16 change revertable via feature flag.
- CI grep check confirms no market data (KTC, FantasyCalc, FantasyPros, ADP) in any feature import path.

---

## 12. Open Decisions for David

1. **YPRR data licensing**: are you willing to manually export raw PFF college route metrics (YPRR, TPRR) annually? Without this, RYPTPA (free, CFBD) becomes the primary WR efficiency candidate. RYPTPA is weaker per current evidence but does not create a paywalled dependency.

2. **Promotion threshold**: ≥3% MAE lift is the starting proposal. Tighter (≥5%) protects against overfit; looser (≥1%) ships more changes with noise risk. Confirm or adjust.

3. **TE deferral**: confirm Phase 18+ is acceptable for TE production features.

4. **Coleman DOB audit preference**: school bio (Sep 10, 2003) vs manual PFR verification before ingestion. Recommend: ingest school bio now, flag for PFR confirmation post-draft when player page is confirmed.

5. **CFBD Patreon tier**: confirm $10/mo upgrade for 75,000 calls vs. remaining on free 1,000/month. Recommend yes given historical backtest volume in W2–W3.

6. **WR R6+ near-zero scores**: Engine A will assign very low DVS to R6–R7 WRs. This will conflict with some dynasty rookie ADP. Confirm that market-overlay-only is the correct handling (no model adjustment).

---

*Compass report (Compass artifact wf-bdb50b6c) used as structural spine. Dynasty Rookie Signal Upgrade Research used as supporting depth and signal explanations. Codex synthesis reviewed. Updated per Claude analysis (2026-05-17): RYPTPA as primary automated WR efficiency candidate, YPRR as conditional challenger; fold-consistency gate (≥3 of 4 LOOCV folds) added to all promotion decisions; RB age de-emphasis elevated to named governance decision gating W5. Reviewed by David (2026-05-17).*
