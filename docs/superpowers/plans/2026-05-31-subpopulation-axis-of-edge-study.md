# Subpopulation / Axis-of-Edge Study — Implementation Plan

> **For agentic workers:** This project executes via the **tmux cockpit TDD loop** (Codex authors the RED contract tests; Claude implements GREEN; independent technical CLEAR + governance CLEAR *before* each commit), NOT superpowers subagent dispatch. Steps use checkbox (`- [ ]`) syntax for tracking. Authoritative spec: `docs/superpowers/specs/2026-05-31-subpopulation-axis-of-edge-study-design.md` (dual-CLEARED, commit `11e3c2d`).

**Goal:** Build a model-blind, descriptive "slice ledger" that characterizes Engine B vs DynastyProcess expert-consensus ranking quality across three pre-registered subpopulations, with strict statistical hygiene and no decision-grade output.

**Architecture:** One pure-function module (`subpopulation_landscape.py`) holding all stats/tagging logic + one thin CLI (`run_subpopulation_landscape.py`) that loads existing G3 run artifacts + the `db_playerids` id-map, runs the pure functions, and writes JSON + Markdown. No model/training code is touched; all market/identity data is read-only and joined *after* scoring.

**Tech Stack:** Python 3.14, `.venv/bin/python3.14`, pytest, numpy/scipy (Spearman + bootstrap), pandas/polars for artifact loading, ruff (`E4 E7 E9 F I`). Reuse existing `compute_ndcg` / bootstrap helpers in `src/dynasty_genius/eval/` where present.

---

## File Structure

- **Create** `src/dynasty_genius/eval/subpopulation_landscape.py` — pure functions (no I/O of model artifacts):
  `resolve_draft_year`, `tag_cohorts`, `compute_slice`, `aggregate_folds`, `apply_fdr`, `build_slice_ledger`, plus module constants (`NEUTRAL_BAND = 0.05`, `AGING_THRESHOLDS`, `DISAGREEMENT_MIN_SLOTS = 12`, `EARLY_CAREER_MAX_EXP = 2`, `SPEARMAN_MIN_N = 30`, `COVERAGE_GATE = 0.95`, `FDR_Q = 0.10`).
- **Create** `scripts/run_subpopulation_landscape.py` — CLI: load `market_comparison_*.json` + `predictions_*.csv` from a run dir + `--id-map-csv`; call the pure functions; write `subpopulation_landscape_{latest,<run>}.{json,md}`. Re-exec-under-venv guard (mirror `run_backtest.py`).
- **Create** `tests/contract/test_subpopulation_landscape.py` — the §11 contract suite (Codex-authored RED).
- **Tasks 1–8 modify only** the module, the CLI, and the contract test. **Task 9 may add/update a `docs/validation/` note only, and only after a separate cockpit review.** No Engine A/B, PVO, trade, or frontend changes in any task.

**Module boundary check:** every function answers cleanly — `resolve_draft_year` (id→draft_year, dedup), `tag_cohorts` (rows→cohort flags), `compute_slice` (one slice-fold→stats dict), `aggregate_folds` (slice-folds→aggregate), `apply_fdr` (aggregates→+q), `build_slice_ledger` (everything→balanced ledger). Each is independently testable with hand-built inputs.

---

## Task 1: Module scaffold + pre-registered constants

**Files:** Create `src/dynasty_genius/eval/subpopulation_landscape.py`; Test `tests/contract/test_subpopulation_landscape.py`.

- [ ] **Step 1 (RED, Codex):** test that the module exposes the locked constants with exact values: `NEUTRAL_BAND == 0.05`, `DISAGREEMENT_MIN_SLOTS == 12`, `EARLY_CAREER_MAX_EXP == 2`, `SPEARMAN_MIN_N == 30`, `COVERAGE_GATE == 0.95`, `FDR_Q == 0.10`, and `AGING_THRESHOLDS == {"RB":25,"WR":27,"TE":29,"QB":32}`. (Pre-registration integrity — these must be constants, not inline literals.)
- [ ] **Step 2:** run it, expect ImportError/AttributeError.
- [ ] **Step 3 (GREEN, Claude):** add the module with the constants + docstring header citing the spec and the `DESCRIPTIVE/DIAGNOSTIC — not decision-grade` posture.
- [ ] **Step 4:** focused test passes; ruff clean.
- [ ] **Step 5:** commit `feat(subpop): module scaffold + pre-registered constants`.

## Task 2: `resolve_draft_year` (early-career dedup contract — spec §6/§7)

**Files:** Modify the module; extend the test file.

- [ ] **Step 1 (RED):** tests asserting — (a) one row per `gsis_id` → `{gsis_id: int(draft_year)}`; (b) multiple `db_season` rows per `gsis_id` → **latest `db_season`** wins; (c) conflicting *non-null* `draft_year` for one `gsis_id` → **raises `ValueError`**; (d) null-vs-value or identical → no raise; (e) **null/absent `draft_year` row → excluded from the map (counts toward the coverage denominator), no raise**; (f) **non-null but non-integer `draft_year` (e.g. "abc", 2020.5) → raises a typed `InvalidDraftYearError`** (data-integrity violation; "silent substitution forbidden" — do not coerce to missing); (g) returns `(map, db_season_snapshot)`.
- [ ] **Step 2:** run, expect fail (function missing).
- [ ] **Step 3 (GREEN):** define `InvalidDraftYearError(ValueError)`; implement deterministic latest-`db_season` selection + conflict raise + null→exclude + non-null-non-integer→`InvalidDraftYearError`; return `(map, db_season_snapshot)`. Callers (Task 7/8) catch `InvalidDraftYearError` → `early_career_axis_unavailable` with coverage/provenance counts, preserving the spec fail-closed posture.
- [ ] **Step 4:** focused pass; ruff clean.
- [ ] **Step 5:** commit `feat(subpop): resolve_draft_year dedup + conflict fail-closed`.

## Task 3: `tag_cohorts` (three pre-registered axes — spec §3)

**Files:** Modify module; extend tests.

- [ ] **Step 1 (RED):** tests for each axis flag on hand-built rows — (a) **aging-cliff:** `age_at_feature_season ≥ AGING_THRESHOLDS[pos]` true/false at the boundary per position; (b) **high-disagreement:** `abs(model_rank − consensus_rank) ≥ 12`, split into `model_bullish` (model_rank < consensus_rank) / `model_bearish`; (c) **early-career:** `experience = feature_season − draft_year ∈ {0,1,2}`; negative/null experience → excluded with `invalid_negative_experience` flag; missing draft_year for a row → not early-career-eligible (counted toward coverage). Lower-is-better rank convention asserted.
- [ ] **Step 2:** run, expect fail.
- [ ] **Step 3 (GREEN):** implement cohort tagging; attach boolean/bucket flags + exclusion reasons; never mutate ranks.
- [ ] **Step 4:** focused pass; ruff clean.
- [ ] **Step 5:** commit `feat(subpop): tag_cohorts three pre-registered axes`.

## Task 4: `compute_slice` (orientation-locked metric + split min-n — spec §4)

**Files:** Modify module; extend tests.

- [ ] **Step 1 (RED):** tests — (a) **orientation lock:** a perfectly-aligned ranker yields positive ρ on the lower-is-better/lower-is-better convention; an inverted ranker flips sign; `rho_diff > 0` ⇔ model aligns better. (b) **category by sign+band, CI-independent:** `rho_diff ≥ +0.05` → `model_leads_point_estimate` regardless of CI; `≤ −0.05` → consensus; `|rho_diff| < 0.05` → `statistically_indistinguishable`; band-edge (exactly 0.05) deterministic. (c) **split min-n:** Spearman computed only at `n ≥ 30` else `insufficient_n`; NDCG cross-check only at `n ≥ primary_k`; the two reported separately. (d) returns `ci_includes_zero` + `boot_p_value` as separate fields. Deterministic via fixed `rng_seed`.
- [ ] **Step 2:** run, expect fail.
- [ ] **Step 3 (GREEN):** implement per slice-fold: Spearman ρ (lower-is-better both sides) for model & consensus vs realized_rank; paired BCa CI + two-sided bootstrap p-value on `rho_diff` (reuse existing bootstrap helper if compatible); NDCG cross-check via existing `compute_ndcg`; category by sign+`NEUTRAL_BAND`; split gates.
- [ ] **Step 4:** focused pass; ruff clean.
- [ ] **Step 5:** commit `feat(subpop): compute_slice orientation-locked metric + split min-n`.

## Task 5: `aggregate_folds` (no pseudo-replication — spec §4)

**Files:** Modify module; extend tests.

- [ ] **Step 1 (RED):** tests — per (axis,slice,position) aggregate over *evaluable* folds = **median `rho_diff` + `folds_covered`**; fold-level rows are preserved in the returned structure; pooled-across-folds is NOT used for the primary aggregate (and if present is labeled `secondary`). A slice evaluable in 2/4 folds reports `folds_covered=2`.
- [ ] **Step 2:** run, expect fail.
- [ ] **Step 3 (GREEN):** implement median aggregation + folds_covered; keep fold rows.
- [ ] **Step 4:** focused pass; ruff clean.
- [ ] **Step 5:** commit `feat(subpop): aggregate_folds median + folds_covered`.

## Task 6: `apply_fdr` (aggregate-only BH family — spec §4/§6/§9.3)

**Files:** Modify module; extend tests.

- [ ] **Step 1 (RED):** tests — Benjamini-Hochberg applied to the **aggregate** per-(axis,slice,position) `boot_p_value`s only (global family); sets `q_value` + `powered_followup_candidate = (q ≤ 0.10)`; **fold-level rows carry no `q_value`/`powered_followup_candidate`**; BH ordering/monotonicity correctness on a known p-value vector; candidate flag labeled hypothesis-generating.
- [ ] **Step 2:** run, expect fail.
- [ ] **Step 3 (GREEN):** implement BH over aggregate p-values; attach q + candidate flag; leave fold rows untouched.
- [ ] **Step 4:** focused pass; ruff clean.
- [ ] **Step 5:** commit `feat(subpop): apply_fdr aggregate-only BH family`.

## Task 7: `build_slice_ledger` (balanced + provenance — spec §4/§7/§8)

**Files:** Modify module; extend tests.

- [ ] **Step 1 (RED):** tests — (a) **balanced reporting:** every axis table includes all directions + `statistically_indistinguishable` + `insufficient_n` bins with `n`/`folds_covered`; (b) **early-career coverage gate:** <95% `draft_year` coverage overall or per position-fold → `early_career_axis_unavailable` + coverage counts only; missing `gsis_id`/`draft_year` input OR caught `InvalidDraftYearError` → `early_career_axis_unavailable` (no age substitution); (c) **provenance block** present (`draft_year_source`, `db_season_snapshot`, coverage num/denom, excluded/invalid counts, per-position disagreement denominators); (d) **posture guard:** no banned David-facing language in any string, no `decision_supported=True`, and the word **"edge" does not appear in any category/slice label or recommendation field**; (e) **the required report header is exactly** `DESCRIPTIVE / DIAGNOSTIC — not decision-grade. No edge claim.` (the header's "No edge claim" is the one sanctioned use of the word and is asserted verbatim; the §8 ban applies to labels/recommendation fields, not this header).
- [ ] **Step 2:** run, expect fail.
- [ ] **Step 3 (GREEN):** assemble the ledger dict; enforce coverage gate + fail-closed early-career; emit provenance; balanced bins.
- [ ] **Step 4:** focused pass; ruff clean.
- [ ] **Step 5:** commit `feat(subpop): build_slice_ledger balanced + provenance + fail-closed`.

## Task 8: CLI `run_subpopulation_landscape.py`

**Files:** Create `scripts/run_subpopulation_landscape.py`; extend tests.

- [ ] **Step 1 (RED):** tests — loads `market_comparison_*.json` + `predictions_*.csv` from a run dir + `--id-map-csv`; joins predictions (`age_at_feature_season`) by `(player_id, feature_season)` and `draft_year` by `gsis_id==player_id`; writes `subpopulation_landscape_latest.{json,md}` to the output dir; **read-only** on inputs (no mutation of run artifacts); missing id-map → early-career-unavailable path (not a crash); re-exec-under-venv guard works.
- [ ] **Step 2:** run, expect fail.
- [ ] **Step 3 (GREEN):** implement loader + wiring + writers (atomic write; refuse to overwrite a differing `<run>` file); mirror `run_backtest.py` CLI conventions.
- [ ] **Step 4:** focused pass; ruff clean.
- [ ] **Step 5:** commit `feat(subpop): run_subpopulation_landscape CLI`.

## Task 9: End-to-end run + descriptive result note (no edge claim)

**Files:** none new (run artifacts are local/gitignored); optional short note appended to the G3 validation report or a new `docs/validation/` landscape note — **cockpit-reviewed, descriptive only**.

- [ ] **Step 1:** run the CLI over the existing G3 run artifacts + `db_playerids.csv`; full suite green; ruff clean.
- [ ] **Step 2:** read the produced ledger; deterministic checks: early-career coverage ≥95% (expect ~100% per the Step-5a probe) else axis-unavailable surfaced; balanced bins present for every axis; **every `powered_followup_candidate` flag equals `(aggregate q_value ≤ FDR_Q)`**; fold-level rows carry no `q_value`/`powered_followup_candidate`; any candidate is labeled hypothesis-generating/descriptive.
- [ ] **Step 3:** if recording a result note, frame strictly descriptive (neutral categories, q disclosed, no "edge"); route through the cockpit (Codex numbers + Gemini governance) before commit.
- [ ] **Step 4:** commit only after dual CLEAR; closing-the-loop post-commit audit.

---

## Self-Review

**Spec coverage:** §3 axes → Tasks 3; §4 metric/categories/FDR/min-n → Tasks 4,5,6; §6 functions → Tasks 2–7; §7 early-career contract → Tasks 2,7; §8 constraints → Task 7 posture guard; §11 contracts → Tasks 1–8. No spec section uncovered.

**Placeholder scan:** no TBD/TODO; each task names exact files + concrete assertions. (Full RED test *code* is authored by Codex in the cockpit loop per project workflow; each task specifies exactly what the test must assert, which is the binding contract.)

**Type/name consistency:** function names (`resolve_draft_year`, `tag_cohorts`, `compute_slice`, `aggregate_folds`, `apply_fdr`, `build_slice_ledger`) and field names (`rho_diff`, `ci_includes_zero`, `boot_p_value`, `q_value`, `powered_followup_candidate`, `category`, `folds_covered`) match the spec §4/§6 exactly across all tasks.

**Constraints carried into every task:** model-blind, read-only market/identity, no Engine A/B leakage, `decision_supported` absent/False, no banned language / no "edge", frontend HOLD, descriptive posture.
