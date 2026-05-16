# Phase 13 Agent Synthesis — Claude
*Source documents: Phase13-round2-research.md, Phase13-Round2-Dynasty Genius Framework Review.md*
*Agent role: Evidence arbitration, conflict resolution, governance grounding*
*Do not use the existing Phase 13 spec or research prompts as source material — this synthesis derives from the two source reports only.*
*Written: 2026-05-15*

---

## 1. Executive Recommendation

**Execute Phase 13 in three sequenced workstreams with a hard dependency gate between 3C and 3B.**

The two source documents agree on the top-level ordering: 3C (Identity Audit) must complete before 3B (TE Remodel) ingests PFF data. This is not a soft preference — silent identity corruption in a training table is categorically worse than a missing feature, because it fails invisibly. 3A (Draft-Capital Step Function) can proceed in parallel for research and offline backtesting, but model promotion must wait for the historical-cohort identity coverage confirmed by 3C.

The deeper divergence between the two sources is methodological, not sequencing. One agent recommends fitting breakpoints empirically (isotonic regression); the other recommends encoding them as hand-defined ordinal bins. One uses gsis_id as the canonical primary key; the other implies Sleeper's player_id as the internal anchor. These conflicts are resolvable and the resolution is documented in Section 3.

**One provenance flag before proceeding:** The Framework Review document (source 2) cites prior Dynasty Genius artifacts — specifically Phase-13-Research-Brief.md and phase_13_research_prompts.md — as primary references [1] throughout. It is not an independent derivation from the raw research. Where the two documents conflict, the Framework Review's constraint often traces to governance documents already in the repo, not to new empirical evidence. This does not invalidate the Framework Review, but the final synthesizer should weight conflicts accordingly: Framework Review = governance enforcement, not independent corroboration.

---

## 2. Evidence Table

| Claim | Source | Confidence | Implementation Implication |
|---|---|---|---|
| RB fantasy hit rate collapses after Round 2 (~6% Day-3 rate vs. ~33% Round-2) | Source 1 (Last Word On Sports 2011–2021) | High | RB Tier 3 breakpoint at pick 65 or Round-3 start |
| WR hit rate decay is flatter than RB; Round-3 WRs viable through ~pick 75 | Source 1 (Campus2Canton since 2001; Last Word 211 Day-3 WRs) | High | WR Tier 2 should extend to ~pick 75 |
| QB cliff between R1 and R2 is steepest of any position; R2+ effectively zero top-12 seasons in last 6 drafts | Source 1 (multiple) | High | QB Tier 1 restricted to Top 32; Tier 2 = 33–64 with heavy discount; 65+ = near-zero weight |
| TE draft capital signal: only R1 vs. rest has statistical support; ≤1.87 TEs/round historically | Source 1 (Fantasy Footballers) | Moderate | TE bins: R1 vs. 33+. Do not fit finer breakpoints. |
| Hit rate table (picks 1–15, 16–32, 33–64, 65–100, 101+) by position | Source 2 | Moderate (synthesized from multiple sources; exact numbers should be verified against primary data at backtest time) | Use as research priors only; refit from backtest cohort |
| Draft capital is endogenous to opportunity, especially at RB (more snaps = higher hit rate attribution) | Source 1 | High | Flag RB step-function as confounded; add snap/target share as separate features when available |
| Role conflation is the primary TE model failure: inline blocker ≠ pass-catching specialist | Source 1 and 2 | High | Archetype labeling precedes model retraining |
| PFF college data starts 2014 — structural backtest constraint | Source 1 | High | Pre-2014 portion of 3A backtest runs without PFF features; 3B cohort limited to 2014–2025 |
| PFF Premium does not include API access; manual CSV export only | Source 1 | High | PFF ingestion = csv_fixture cache policy; operational tax must be reflected in Phase 13 scope |
| PFF college receiving grade ≥80.6 clusters with NFL top-50 TE outcomes | Source 1 (BrainyBallers) | Moderate | Secondary threshold for archetype validation, not primary feature |
| gsis_id is the canonical nflverse primary key; nflverse-players overwrites all IDs against it | Source 1 (nflverse-players documentation) | High | gsis_id = crosswalk anchor for identity bridge; not the internal Dynasty Genius canonical key |
| ff_playerids crosswalk exposes 35 columns across 12,186 players including pff_id, sleeper_id, gsis_id | Source 1 (nflreadr documentation) | High | Use load_ff_playerids as the deterministic mapping table |
| 2022+ rookies are the highest-risk identity gap: gsis_id propagates late, Sleeper assigns player_id immediately | Source 1 (nflfastR documentation) | High | Enumerate 2022–2025 rookie cohort separately in coverage matrix |
| Sports Reference Terms of Use prohibit ML training on SR content without permission | Source 1 | High | CFB Reference = reference/spot-check only; not a training feature source |
| Fuzzy matching is prohibited in production; all fuzzy candidates go to manual review queue | Source 1 and 2 | High (governance constraint) | No production path invokes string similarity; review queue is the only fallback |
| LOOCV on draft classes is the required validation protocol for 3A | Source 1 and 2 | High | Hold out one draft class; evaluate intra-class Kendall τ rank correlation |

---

## 3. Conflicts Between the Two Reports and Resolutions

### Conflict 1: Draft-Capital Transform Method

**Source 1 recommends:** Monotonic isotonic regression (PAVA) as primary, with bucketed categorical and log-decay as baselines. Hierarchical pooling applied to TE and QB given small annual cohorts.

**Source 2 recommends:** Ordinal categorical encoding (hand-defined bins by position). Hierarchical priors explicitly deferred due to sklearn compatibility and complexity concerns.

**Resolution:** The isotonic approach is more empirically defensible because it derives breakpoints from the backtest data rather than encoding them as priors. Hand-defined bins risk anchoring to the last decade's NFL draft economics, which Source 1 flags as potentially shifting (fewer Day-1 RBs recently). However, Source 2's concern about sklearn compatibility is a real operational constraint.

**Adopted position:** Run both in the bake-off as Source 1 recommends — isotonic step as primary candidate, bucketed categorical as the interpretability-preserving alternative, log-decay as the baseline. Do not hand-code final bin boundaries before the backtest. Let the data determine whether the Source 2 bins are correct or need adjustment. **Hierarchical pooling is deferred** (Source 2's constraint holds) but should be documented as a Phase 14 candidate, specifically for TE where cohort sizes are the smallest.

### Conflict 2: Canonical Primary Key

**Source 1 states:** gsis_id is THE canonical primary key, consistent with nflverse practice.

**Source 2 implies:** Sleeper's player_id is the internal anchor; gsis_id is the ff_playerids bridge key.

**Resolution:** The North Star Architecture specifies "canonical player_id" as the Dynasty Genius internal identifier, and the existing Phase 9.5 identity infrastructure uses Sleeper's player_id as the internal canonical key. gsis_id is the crosswalk anchor — the bridge between external sources. Source 1's framing is correct for the nflverse ecosystem but conflicts with the existing Dynasty Genius identity layer design. **gsis_id = crosswalk anchor; internal canonical key = Sleeper player_id.** The Phase 13 identity bridge must use gsis_id to join ff_playerids, then translate to Sleeper player_id for internal use. Source 2 is closer to correct for this system.

### Conflict 3: TE Archetype Granularity

**Source 1 recommends:** Four archetypes (A: Receiving Specialist, B: In-Line Receiving TE, C: Inline Blocker, D: Big-Slot Hybrid).

**Source 2 recommends:** Two archetypes (Move/Pass-Catching TE vs. Blocking-First TE).

**Resolution:** The 4-archetype framework is richer and captures real variation (Kittle vs. Pitts vs. Hawes vs. Loveland are genuinely different). But for Phase 13 Step 0, 4 archetypes create label ambiguity at the boundaries (where does Type B end and Type D begin?) and reduce training cohort sizes further. **Phase 13 Step 0 uses 2 archetypes** (receiving-leaning vs. blocking-leaning) with a "boundary/ambiguous" tag for players who straddle the threshold. The 4-archetype framework is the right target for Phase 14 when per-archetype sample sizes justify it.

### Conflict 4: TE Identity Coverage Threshold

**Source 1:** ≥90% of the TE cohort 2014–2025 must have valid PFF college player_id ↔ gsis_id mapping before TE remodel training can begin.

**Source 2:** < 2% loss rate for 2018–2025 drafted TEs (equivalent to ≥98% coverage, narrower window).

**Resolution:** Source 2's 2% threshold is stricter. The narrower 2018–2025 window is more tractable to achieve given identity coverage degradation for retired/older players, but it produces a smaller training cohort. **Use Source 2's 2% threshold and 2018–2025 window as the hard gate.** Separately, measure coverage for 2014–2017 as an extended context report — not a gate, but a documented gap that constrains how much pre-2018 PFF data can safely enter the training table.

### Conflict 5: Validation Rigor

**Source 1:** Per-position AUC/Brier delta vs. log-decay + bootstrap CIs + ±10 pick jitter sensitivity check.

**Source 2:** Kendall τ as primary metric; statistically significant lift over linear baseline required.

**Resolution:** These are complementary, not contradictory. **Kendall τ intra-class rank correlation is the primary gate metric** (Source 2). Bootstrap CIs and jitter sensitivity are robustness checks that run alongside the primary gate but are not blocking conditions for promotion. The jitter sensitivity check (Source 1) is particularly valuable because it tests whether the step function is genuinely capturing cliff structure or just fitting noise at specific pick numbers.

---

## 4. Phase 13 Workstreams and Ordering

### 13.1 — Identity Resolution Audit (3C) | Start Immediately

**Objective:** Establish a deterministic, audited identity bridge covering the 2018–2025 drafted player cohort with sufficient TE-specific coverage to unblock 3B.

**Inputs:** nflreadr `load_ff_playerids` (35-column crosswalk), Sleeper `/v1/players/nfl` payload, existing `prospect_alias_bridge.json`.

**Outputs:**
- Coverage matrix (rows: source IDs; columns: active starters / active depth / 2024–25 rookies / 2018–2023 retired)
- Review queue ledger (all ambiguous matches, candidates, resolution decisions)
- Override registry (versioned JSON, git-tracked)
- Failure-mode report (name collisions, position-changers, late-arriving gsis_ids for 2022+ rookies)
- Identity contract document

**Gate:** <2% loss rate for 2018–2025 drafted TEs (per Source 2). 100% of David's active TE starters resolved deterministically.

**Key risk:** 2022+ rookies have a documented gsis_id propagation lag in nflfastR. The audit must enumerate this cohort separately and not count late-arriving gsis_ids as resolved until confirmed.

### 13.2 — Engine A Draft-Capital Bake-Off (3A) | Parallel Research

**Objective:** Determine whether a position-specific step-function encoding of draft capital improves Rookie Board rank correlation over the current linear/log-decay treatment.

**Bake-off candidates:**
1. Isotonic step (PAVA, per-position, fit from backtest data) — primary candidate
2. Bucketed categorical bins (hand-defined, per-position) — interpretability alternative
3. Log-decay `1/log(pick)` — baseline

**Validation protocol:** LOOCV on draft classes. Primary metric: Kendall τ intra-class rank correlation per position. Robustness checks: bootstrap CIs (95%), ±10 pick jitter sensitivity. All results must beat log-decay baseline with statistical significance before promotion.

**Promotion gate:** Cannot promote until 13.1 confirms historical cohort identity coverage for the 10–15 year backtest window. Design and offline exploration can proceed now; production promotion waits for 3C gate.

**Interaction terms:** After bin encoding, add position × bin × collegiate-efficiency interaction (e.g., WR bin × YPRR). This allows elite Day-3 production to partially override weak capital signal (Source 2's recommendation; Source 1 implies the same through the archetype-override caveat).

### 13.3 — TE Remodel Step 0 (3B) | Gated on 13.1

**Objective:** Produce an archetype-labeled TE prospect cohort and evaluate PFF collegiate data feasibility. Do not retrain the TE model in Phase 13.

**Step 0 tasks only:**
- PFF Premium CSV export feasibility: document fields available, manual export tax, license constraints
- Archetype labeling rubric: define thresholds for receiving-leaning vs. blocking-leaning (and boundary tag)
- Apply rubric to 2018–2025 TE draft cohort using available public data first (cfbfastR production + PlayerProfiler)
- Evaluate nflverse `load_participation` as an active-TE alignment proxy (11 vs. 12 personnel deployment)
- Enumerate gaps where PFF alignment data is the only source

**Model retraining is out of scope for Phase 13.** Step 0 produces the data preconditions for Phase 14.

---

## 5. Explicit Out-of-Scope Items

- TE promotion from EXPERIMENTAL status (requires model retraining + validation gates, Phase 14 minimum)
- Per-archetype separate TE models (insufficient sample size; Phase 14)
- Dynasty Value Score (DVS) implementation (locked)
- Any market data (KTC, FantasyCalc, ADP, consensus) entering Engine A or Engine B training features
- Silent fuzzy matching in any production path
- CFB Reference as a training feature source (Sports Reference license prohibition)
- Engine B modification based on collegiate alignment data
- SIS charting or other enterprise data subscriptions
- Hierarchical Bayesian priors for draft capital (sklearn incompatibility; Phase 14 candidate)
- PFF grade features (pff_grade, pff_route_grade) — subjective, prohibited from feature matrix
- Hardcoded age cliffs

---

## 6. Open Decisions for David

1. **PFF ingestion mechanism:** Is the manual CSV export workflow acceptable for Phase 13, or do you want to budget for PFF B2B/Data API tier before committing to 3B?

2. **Identity coverage thresholds:** The 2% loss rate for 2018–2025 TEs is proposed as the hard gate. Do you want the pre-2018 coverage (2014–2017) to be an additional soft warning or ignored entirely for Phase 13?

3. **Review queue ownership:** Ambiguous identity matches require human approval. Who resolves the queue — you alone, or can an agent make provisional decisions subject to your review?

4. **Archetype labeling method:** Do you tag the historical TE cohort manually, or should we build a rule-based labeler (≥X% inline = blocking-leaning) with your review of boundary cases?

5. **RB endogeneity acknowledgment:** The step-function likely partially captures opportunity assignment at RB, not just talent. Do you want this flagged as a known limitation in the model card, or do you want snap share / target share added as separate features alongside draft capital before 3A promotes?

6. **Bake-off tie-breaker:** If isotonic and bucketed categorical produce statistically equivalent Kendall τ, which do you prefer — interpretability (categorical bins, David can inspect what Tier 1 means) or data-driven breakpoints (isotonic, finds cliffs automatically but less legible)?

---

## 7. Risks and Failure Modes

| Risk | Likelihood | Severity | Mitigation |
|---|---|---|---|
| Silent identity corruption in TE training table | High without 3C gate | Critical | Hard gate enforced; 13.1 completes before 13.3 touches training data |
| RB step-function overfit to last decade's draft economics | Medium | Moderate | Time-weighted resampling in backtest; jitter sensitivity check |
| PFF manual export proves infeasible (licensing, access) | Medium | High for 3B | Public fallback path documented: cfbfastR + PlayerProfiler + nflverse participation |
| TE archetype labels are noisy (college scheme ≠ NFL role) | High | Moderate | Document inter-tagger agreement; version the labeling rubric; add RAS as override caveat for athletically mismatched prospects |
| gsis_id propagation lag for 2022–2025 rookies creates phantom coverage gaps | High | Moderate for 3C gate | Enumerate separately; do not count as resolved until gsis_id confirmed |
| Historical backtest cohort identity degrades for pre-2020 retired players | High | Moderate | Document coverage by draft year; exclude cohort segments that fall below threshold with explicit justification |
| Draft capital endogeneity at RB inflates step-function predictive value | Medium | Moderate | Flag in model card; add snap share as separate feature when available |
| TE EXPERIMENTAL status creates stakeholder pressure to fast-track promotion | Low (governance is clear) | High if succumbed to | Promotion gates are non-negotiable; document in acceptance criteria |

---

## 8. Proposed Acceptance Criteria

### 13.1 Identity Audit
- Coverage matrix produced covering all four cohort segments (active starters / active depth / 2024–25 rookies / 2018–2023 retired)
- <2% loss rate confirmed for 2018–2025 drafted TEs
- 100% of David's active TE starters resolved deterministically (not in review queue)
- Review queue ledger, override registry, and identity contract document committed to repo
- At least one contract test in CI verifying no duplicate gsis_ids and no adapter-invented identity

### 13.2 Engine A Draft-Capital Bake-Off
- All three candidates (isotonic, bucketed categorical, log-decay) evaluated on ≥10 draft classes with complete identity coverage
- Isotonic or categorical must show statistically significant Kendall τ lift over log-decay baseline within each position's holdout classes
- Bootstrap CI lower bounds positive for the winning candidate (not just point estimate improvement)
- Jitter sensitivity check completed: step-function breakpoints do not shift by more than one bucket under ±10 pick perturbation
- Divergence ledger entry and model card update produced before promotion
- Trust Surface v2 updated with new breakpoints and provenance

### 13.3 TE Remodel Step 0
- PFF feasibility memo produced: fields available, manual export workflow documented, license constraints noted
- Archetype labeling rubric versioned and committed
- 2018–2025 TE cohort tagged with archetype labels (with boundary/ambiguous tier)
- nflverse `load_participation` active-TE alignment proxy evaluated and documented
- Gap report: players requiring PFF data vs. coverable by public sources
- No model retraining, no EXPERIMENTAL lock removal

---

## Provenance Note for Final Synthesizer

Source 2 (Framework Review) is not fully independent of prior Dynasty Genius artifacts. It cites `Phase-13-Research-Brief.md` and `phase_13_research_prompts.md` as primary references throughout. Governance constraints in Source 2 that trace directly to those documents (prohibited PFF grades, DVS deferral, EXPERIMENTAL lock rules) are reinforcing existing governance, not new independent findings. Where Source 2 offers independent analytical judgment (the bucketed categorical encoding recommendation, the 2% loss-rate threshold, the hit-rate table), treat it as corroborating evidence with the caveat that some numerical values in the table appear to pool across studies without individual citation.

Source 1 (Deep Research) is the more independent empirical document. Its citations are specific, its uncertainty is explicit, and it identifies failure modes (Sports Reference license, RB endogeneity, PFF data window starting 2014) that Source 2 does not surface. Where the two conflict on methodology, Source 1's empirical grounding should carry more weight. Where they conflict on governance constraints, defer to Source 2 and the existing governance layer.
