# Subpopulation / Axis-of-Edge Study — Design Spec

- **Date:** 2026-05-31
- **Status:** DESIGN (pre-implementation). Descriptive/diagnostic study; **no decision-grade output, no edge claim, no model/training change.**
- **Initiative:** Harness Trust Completion → follow-up to the Step-5b.2 G3 result (`docs/validation/2026-05-31-step5b2-g3-ecr-validation.md`).
- **Lineage:** team brainstorm 2026-05-31 — Goal 3 (characterize the landscape) chosen over edge-hunting; Option 1 (derive experience) chosen for the early-career axis.

## 1. Why this study exists (vision + discipline)

**The vision (the destination — what Dynasty Genius is for).** The product goal is to help David win: know when to sell a depreciating veteran a year before the market does, surface calibrated contrarian trade targets, and nail rookie evaluation. The three axes below are chosen *because* they map directly onto those goals.

**The discipline (what this study is allowed to claim).** The G3 whole-population result is a statistical **tie** with DynastyProcess expert consensus — edge unproven (every fold CI on the NDCG-diff includes 0; 4 annual folds). This study is the honest **measurement of how far we are toward the vision on each axis**. It must stay descriptive: it surfaces *hypotheses* about where model quality is strong, weak, or indistinguishable — it does **not** assert the model has arrived at any of the vision goals. The vision motivates *which* slices to cut; the measurement governs *what we may claim*.

This separation is the spec's central rule: **per-axis vision-motivation = legitimate framing; per-slice claims = strictly descriptive with disclosed uncertainty.**

## 2. Objective

Produce a **descriptive "slice ledger"** characterizing Engine B vs DynastyProcess expert-consensus (`dynastyprocess_ecr_2qb`) ranking quality against realized PPG, across **pre-registered subpopulations**, for the **whole player universe** (not David's roster). Output enables exactly one decision: *which model-quality hypotheses deserve a powered confirmatory follow-up or feature-improvement investigation.* It does **not** enable "trust this pocket."

## 3. Pre-registered axes

All axis definitions are **hardcoded before analysis** (no ad-hoc slices; any post-hoc slice goes only in a clearly labeled exploratory appendix). Evaluated within each position; primary aggregation across the 4 folds.

### Axis 1 — Aging-cliff transition
- **Vision served:** sell-timing on depreciating veterans — does the model see decline before the market?
- **Definition:** players whose `age_at_feature_season` is within 1 of, or past, the doctrine cliff: RB ≥ 25, WR ≥ 27, TE ≥ 29, QB ≥ 32. (One season ahead of the constitution cliffs RB26/WR28/TE30/QB33 to capture the transition.)
- **Data:** `age_at_feature_season` from `predictions_*.csv` (point-in-time correct). Feasible now.

### Axis 2 — High model-vs-consensus disagreement
- **Vision served:** calibrated contrarian trade targets — are the model's high-conviction departures from consensus actually right?
- **Definition:** `abs(model_rank − consensus_rank) ≥ 12` slots (within position-fold). Reported split into model-bullish (model_rank < consensus_rank) and model-bearish sub-buckets so direction is visible.
- **Data:** `model_rank`, `fc_rank` (consensus, derived from `fc_value`) from `market_comparison_*.json`. Feasible now.

### Axis 3 — Early-career (draft-class experience ≤ 2)
- **Vision served:** rookie / young-player evaluation.
- **Definition:** `early_career_experience_year = feature_season − draft_year`; cohort = `experience_year ∈ {0,1,2}`. **Labeled "draft-class experience / years since NFL draft class," NOT accrued NFL seasons** (UDFAs, opt-outs, late debuts differ).
- **Data:** `draft_year` from the same DynastyProcess `db_playerids.csv` used for G3, joined by `gsis_id == player_id`. Probe (Codex, 2026-05-31): 100% draft_year coverage over the G3 comparison rows (1702 rows / 649 players, every position).

## 4. Metric & classification

- **Within-slice rank-quality metric (orientation-locked).** For each ranker, compute Spearman ρ between the ranker's per-player rank and the realized rank, **both on a lower-is-better scale** (rank 1 = best; realized_rank 1 = best PPG). On this scale a *good* ranker yields **positive** ρ. Define `rho_diff = rho_model − rho_consensus`, where **positive `rho_diff` means the model's ordering aligns better with realized outcomes than consensus**. (Equivalently use `rank_score = −rank` against realized PPG; the spec mandates the lower-is-better/lower-is-better convention so implementation and tests cannot silently invert the sign — Codex finding #1.)
- **Fold-level computation, then aggregate (no pseudo-replication — Codex finding #2).** Compute the metric **per (axis, slice, position, fold/test_year)**. Player-season rows are NOT pooled across folds for the primary statistic (that would treat correlated rows as independent and hide fold instability). Aggregate across *evaluable* folds with **median `rho_diff` + `folds_covered`**; the ledger **preserves the fold-level rows**, not only the aggregate. A pooled row-level diagnostic, if included, is explicitly labeled **secondary/exploratory**.
- **Consistency cross-check:** where a slice-fold has `n ≥ position-primary k`, also report NDCG@k (model vs consensus) for continuity with the G3 whole-population framing.
- **Min-n gate, split by metric (Codex finding #6):** Spearman requires slice-fold `n ≥ 30`; the NDCG cross-check requires `n ≥ position-primary k`. Below the relevant gate → that metric is `insufficient_n` (descriptive counts only); the two eligibility rules are reported separately, never blurred.
- **Output category — assigned by point-estimate sign + a pre-registered neutral band, INDEPENDENT of the CI (Codex r2 #1, #2).** This covers every case (CI in or out of 0) and keeps uncertainty in separate fields:
  - `model_leads_point_estimate` — `rho_diff ≥ +NEUTRAL_BAND`
  - `consensus_leads_point_estimate` — `rho_diff ≤ −NEUTRAL_BAND`
  - `statistically_indistinguishable` — `|rho_diff| < NEUTRAL_BAND`
  - `insufficient_n` — below the metric's min-n gate (assigned before the others)
  - **`NEUTRAL_BAND` is a pre-registered constant = `0.05` (absolute `rho_diff`), locked before any results and not tuned after** (§9.2). The word **"edge" is not used**; there is **no "confirmed"/"detectable" category** — direction is a point estimate, never a verdict.
- **Separate descriptive uncertainty fields (not part of the category):** `ci_includes_zero` (bool, from the BCa CI), `boot_p_value`, `q_value` (BH), `powered_followup_candidate` (bool).
- **Multiplicity (statistically coherent — Codex #3 + r2 #3; aggregate-p construct ruled 2026-06-01, before any subpopulation results were computed — pre-registration preserved).** The aggregate p-value for each per-(axis,slice,position) slice is an **exact fold-level sign-flip permutation test** on the *evaluable* fold `rho_diff`s: statistic = `abs(median(fold_rho_diffs))`; null = all `2^K` sign flips of the K fold effects; two-sided `boot_p_value` = fraction of sign-flips whose `abs(null median) ≥ observed`; `K = 0 → None`; all-zero effects `→ 1.0`; method recorded as `fold_signflip_median_exact`. This keeps the **fold as the unit of inference** (no row-level pooling / pseudo-replication) and is **deterministic (no RNG)**. (A pooled row-level bootstrap and Fisher/Stouffer combination were both rejected — the former reintroduces pseudo-replication for inference, the latter assumes fold independence and hides the fold p-values as the aggregate source.) The **primary BH family is these per-(axis,slice,position) aggregate p-values only** (§9.3 global across aggregates); the **per-fold `boot_p_value` from `compute_slice` is diagnostic only** — never the aggregate source and never carries `q_value` / `powered_followup_candidate`. Report the BH **`q_value`** descriptively; `q ≤ 0.10` → `powered_followup_candidate=true`, explicitly **hypothesis-generating, not a verdict**. BH corrects p-values, never CIs. **No pass/fail promotion gate is emitted.** **Low-fold-count caveat (MANDATORY artifact disclosure):** the sign-flip null has a minimum two-sided p of `0.25` at `K ≤ 4` (and `0.125` at `K = 6`), so with this study's ≤ 4 annual folds `powered_followup_candidate` is **structurally unreachable — no candidate can fire**. The artifact MUST disclose this as a statistical-power limitation of the fold count, NOT as evidence of "no signal."
- **Balanced reporting:** every axis table shows all directions + `statistically_indistinguishable` + `insufficient_n` bins with n and folds-covered. Selective publication of only favorable slices is prohibited.

## 5. Inputs & data flow

1. **Load fold artifacts:** the `market_comparison_*.json` + `predictions_*.csv` from a backtest run produced with `--market-store` (the G3 run). Read-only.
2. **Enrich:** join `predictions` (age) by `(player_id, feature_season)`; join `db_playerids` (`draft_year`) by `gsis_id == player_id`.
3. **Tag cohorts:** apply the three axis definitions → per-player boolean/bucket flags.
4. **Compute slice metrics:** per (axis, slice, position, fold/test_year), model vs consensus ρ + BCa CI + min-n gate + NDCG cross-check; then aggregate across evaluable folds.
5. **Classify + FDR:** assign neutral categories; apply Benjamini-Hochberg.
6. **Write outputs:** slice-ledger JSON + Markdown report.

## 6. Components (designed for isolation)

- **`src/dynasty_genius/eval/subpopulation_landscape.py`** — pure functions, model-blind, no I/O of model artifacts:
  - `resolve_draft_year(db_playerids_rows) -> ({gsis_id: draft_year}, db_season_snapshot, diagnostics)` — deterministic de-dup. **Real-id-map robustness (cockpit-ruled 2026-06-01, refines Codex finding #5):** null-marker `gsis_id` rows (`{None, "", "NA", "NULL", "None"}`, case-insensitive) are SKIPPED (unjoinnable keys); null-marker `draft_year` is treated as MISSING (excluded, counted toward coverage); a **genuinely conflicting** non-null `draft_year` for one real `gsis_id` EXCLUDES that ambiguous id (counted; surfaced in `diagnostics.conflicting_draft_year_excluded_count` + excluded ids) rather than raising-and-aborting the whole map — fail-closed at the player-key level, never catastrophic, and **never** "latest wins" / pick-a-year. Truly malformed `draft_year` (non-integer, non-null-marker — e.g. `"abc"`, `"2020.5"`) still raises `InvalidDraftYearError`. Integer / integer-string / integral-float still map.
  - `tag_cohorts(rows, draft_year_map) -> rows+flags` (axis definitions; lower-is-better rank convention; invalid/negative experience excluded with caveat)
  - `compute_slice(model_ranks, consensus_ranks, realized_ranks, k, *, n_bootstrap, rng_seed) -> {rho_model, rho_consensus, rho_diff, bca_ci95, ci_includes_zero, boot_p_value, ndcg_xcheck, n, category}` — computed **per slice-fold**, orientation-locked (lower-is-better both sides), split min-n gate; `category` by sign + `NEUTRAL_BAND` (CI-independent).
  - `apply_fdr(aggregate_slice_tests) -> +q` — Benjamini-Hochberg over the **aggregate** per-(axis,slice,position) p-values only (global across aggregates), where each aggregate's `boot_p_value` is the fold-signflip permutation p (above); sets `q_value` + `powered_followup_candidate` (q ≤ 0.10, hypothesis-generating). The per-fold `boot_p_value` is not part of this family.
  - `aggregate_folds(slice_folds) -> {median_rho_diff, folds_covered, fold_rows}` — aggregate across evaluable folds; preserves the fold-level rows. **Point estimate only — emits no p-value.**
  - `aggregate_signflip_p(fold_rho_diffs) -> boot_p_value` — exact fold-level sign-flip permutation p (§4): statistic `abs(median(evaluable fold rho_diffs))`, null = all `2^K` sign flips, two-sided; `K = 0 → None`, all-zero `→ 1.0`; deterministic. The orchestration attaches this to each aggregate record before `apply_fdr`.
  - `build_slice_ledger(...) -> ledger` (balanced; all directions + insufficient bins; coverage/provenance block).
- **`scripts/run_subpopulation_landscape.py`** — CLI: loads run artifacts + id-map CSV, calls the pure functions, writes `subpopulation_landscape_{latest,<run>}.{json,md}`. Re-exec-under-venv guard like the other scripts.

## 7. Early-career input contract & provenance (Option 1 gates)

- **Input contract:** the early-career axis requires an id-map/identity CSV containing `gsis_id` and **integer** `draft_year`. If absent/empty/non-integer → emit `early_career_axis_unavailable` and **do not** substitute age (fail closed; "silent substitution forbidden").
- **De-duplication (Codex finding #5; real-id-map robustness 2026-06-01):** `db_playerids` may carry multiple rows per `gsis_id` across `db_season`. Select the **latest `db_season`** row per `gsis_id`; identical/null-vs-value duplicates are fine. A **genuine conflict** (≥2 distinct non-null `draft_year` for one real `gsis_id`) **excludes that ambiguous id** (counted + surfaced in diagnostics), it does NOT raise/abort the map and NEVER picks "latest wins". Null-marker `gsis_id` rows are skipped. The selected `db_season` snapshot is recorded in provenance.
- **Coverage gate:** require `draft_year` coverage ≥ 95% overall **and per position-fold** among rows entering the early-career slice; below gate → that axis/position-fold marked unavailable, coverage counts only.
- **Provenance fields in output:** `draft_year_source="dynastyprocess_db_playerids"`, source path/artifact label, `db_season_snapshot`, `draft_year_coverage_numerator/denominator`, `excluded_missing_draft_year_count`, `invalid_negative_experience_count`, `conflicting_draft_year_excluded_count` (+ excluded ids), `null_marker_gsis_id_skipped_count`.

## 8. Constraints (non-negotiable)

- **No leakage:** read-only, joined **after** model scoring; `draft_year`/`experience`/age cohorts **never** enter Engine A/B training features. This is validation-report metadata only.
- **Overlay-only market data**; `decision_supported` absent/False on any structured output.
- **No banned David-facing language** in any generated string (verdict/tier/grade/action; no "edge"/"buy"/"sell" in slice labels).
- **Frontend HOLD intact.**
- **Report header:** `DESCRIPTIVE / DIAGNOSTIC — not decision-grade. No edge claim.`

## 9. Resolved design decisions (cockpit review round 1, 2026-05-31)

1. **Primary metric — RESOLVED: Spearman `rho_diff` primary (orientation-locked, fold-level) + NDCG@k cross-check.** NDCG is not made primary for arbitrary subpopulations. (Codex + Gemini.)
2. **Pre-registered thresholds — RESOLVED and LOCKED before any results:** disagreement `≥ 12` absolute slots; aging offsets 1 season ahead of doctrine cliffs. The report **must disclose the per-position denominator/percentage** for the disagreement bucket (12 ranks ≠ equal severity across QB vs WR). Thresholds are **not tuned after seeing results.**
3. **FDR family scope — RESOLVED: global** across all pre-registered slice tests for v1 (defensible default under Goal 3). Per-axis families may be reported **secondarily as exploratory sensitivity** only.

## 10. Out of scope / future increments

- Powered confirmatory study of any axis whose aggregate `*_leads_point_estimate` is not yet a `powered_followup_candidate` (CI includes 0 / q > 0.10) — needs more point-in-time archive years.
- Trade-market (FantasyCalc/KTC) baseline (Task C; Gate-4/W2b, deferred).
- Any David-roster-specific / decision-context analysis (explicitly excluded — this study is whole-universe model quality).

## 11. Testing

Contract tests (Codex RED → Claude GREEN) for `subpopulation_landscape.py`:
- **Orientation lock:** a synthetic perfectly-ranked slice yields `rho_diff` with the correct sign (a better ranker → higher ρ on the lower-is-better/lower-is-better convention); a deliberately inverted ranker flips the sign. Guards Codex finding #1.
- **Fold-level, no pooling:** metric computed per slice-fold; aggregate = median across evaluable folds + `folds_covered`; fold rows preserved in the ledger. Guards finding #2.
- **Split min-n gate:** Spearman gated at n≥30, NDCG cross-check at n≥primary_k; QB/TE slice-fold at n=20–29 yields Spearman `insufficient_n` only if <30, independent of NDCG eligibility. Guards finding #6.
- **Category covers all cases, CI-independent (Codex r2 #1):** `rho_diff ≥ +0.05` → `model_leads_point_estimate` whether or not CI excludes 0; `≤ −0.05` → consensus; `|rho_diff| < 0.05` → `statistically_indistinguishable`; below min-n → `insufficient_n`. `ci_includes_zero` is a separate field, never part of the category. No `confirmed` category exists.
- **Neutral band is deterministic (Codex r2 #2):** `NEUTRAL_BAND=0.05` boundary cases classify deterministically; test exactly at the band edge.
- **FDR coherence + family (Codex #3, r2 #3; aggregate-p ruled 2026-06-01):** BH applied to **p-values** (not CIs), over **aggregate** per-(axis,slice,position) tests only, where each aggregate p is the exact fold-signflip permutation p (§4, `fold_signflip_median_exact`); the per-fold `boot_p_value` carries no `q_value`/`powered_followup_candidate`; `powered_followup_candidate` set at q≤0.10, labeled hypothesis-generating, and **structurally unreachable at K≤4** (min sign-flip p = 0.25) — disclosed as a fold-count power limit.
- **Early-career contract (real-id-map robustness, cockpit-ruled 2026-06-01):** null-marker / absent `draft_year` → MISSING (excluded, counted toward coverage; no age substitution); **truly malformed** non-integer `draft_year` → `InvalidDraftYearError`; null-marker `gsis_id` rows skipped; **a genuine `draft_year` conflict for one real `gsis_id` EXCLUDES that ambiguous id** (counted + diagnostics) rather than raising/aborting the map (no latest-wins); `db_season_snapshot` = latest `db_season`; <95% draft_year coverage (overall or per position-fold) → `early_career_axis_unavailable`. Guards finding #5 + §7.
- **Balanced ledger:** every axis table includes all directions + `statistically_indistinguishable` + `insufficient_n` bins.
- **Posture guard:** no banned David-facing language and no `decision_supported=True` in any output string/field.
