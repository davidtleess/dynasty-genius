---
title: Backtest Trust Completion — Engine A/B Model-vs-Market Validation — Design Spec
status: DESIGN SPEC v4 — APPROVED. Dual-CLEAR complete (Codex technical CLEAR v4 13:46; Gemini governance CLEAR ×3). David Gate B rulings LOCKED 2026-05-30 (§8: R²=disclose, G3=≥3/4+disclosed-CI, W1 archive APPROVED, Gate-4/W2b deferred). NEXT: writing-plans → cockpit TDD (W3 → W2a → W1 → W4).
changelog:
  - v2 (2026-05-30) integrates Codex round-1 (13:34): C1 NaN/inf fail-closed RED rows (§3); C2 R² OOS-only, in-fold dropped from v1 (§3); C3 G3 under-coverage → deferred-not-failed, existing-code fix (§1/§5); C4 NDCG-diff paired bootstrap contract (§5); C5 position-aware NDCG k-table + coverage reconciliation (§5); C6 G4 producer absent — W2 split W2a/W2b (§1/§4); C7 Gate-4 matched-control design lock = W2b/§8.3; C8 W4 narrowed to one trust-surface field (§6). Gemini round-1 governance CLEAR (13:33).
  - v3 (2026-05-30) integrates Codex round-2 (13:41): D1 R² caveat schema destination = new `metric_caveats: List[str]` on `FoldResult` + `r2_oos_mean` null-handling (§3); D2 reconcile stale `@24`-as-verdict language to the position-primary k (§1, §8.2); D3 W2a immutability key = store's actual `(snapshot_date, league_settings_hash, sleeper_id)` PK + replace existing `INSERT OR REPLACE` with verify-or-raise (§4). Gemini round-2 governance CLEAR (13:41).
  - v4 (2026-05-30) integrates Codex round-3 (13:44): E1 `ModelCardMetrics.r2_oos_per_fold: List[Optional[float]]` + `r2_oos_mean: Optional[float]` (fail-closed folds emit null; `List[float]` would fail Pydantic validation) (§3). Gemini round-3 CONCUR & CLEAR (13:44).
date: 2026-05-30
author: Claude Code (reconciler), grounding the 2026-05-28 scoping brief against post-S4 main
parent_brief: docs/strategies/2026-05-28-harness-trust-completion-scoping-brief.md
parent_reviews:
  - Codex statistical review — docs/agent-ledger/2026-05-30.md (13:19 ET): GO-after-revisions
  - Gemini governance review — docs/agent-ledger/2026-05-30.md (13:18 ET): GO-conditional (5 governance locks)
  - Claude reconciliation — docs/agent-ledger/2026-05-30.md (13:22 ET): reconciled GO
governance_hold: Frontend HOLD intact. decision_supported=False throughout. NOISE_BAND lock untouched. No Engine A/B model .pkl/manifest/feature/training change. Market data overlay-only.
scope_guard: This is NOT Subsystem 4. S4 (the mock-draft-consensus harness, backtest_mock_draft.py) is MERGED to main (95345ea), which RELEASED the §11.1 inviolate lock on the Phase 10/11 files this spec touches. This spec extends the EXISTING Phase 10/11 model-validation harness (backtest_harness.py, backtest_metrics.py, market_snapshot_store.py, backtest_artifact.py, model_card.py, trust_surface.py).
---

# Backtest Trust Completion — Engine A/B Model-vs-Market Validation (Design Spec)

> Doc version is in the frontmatter `status`/`changelog` (currently v4). "v1" in the workstream text below refers to the **first build increment** of this feature (vs deferred later increments like W2b / R²-as-gate), not the doc revision.

## 0. Why this exists

The *form* of Dynasty Genius's headline value — "our valuation vs the market's price, and the gap" — is fully built and honest, but its *scientific substance* is unvalidated:

- **G3 (market-superiority) has never returned anything but `"deferred"`** — no market snapshots have been ingested at the harness evaluation dates, so the system cannot currently claim it beats the market.
- **G4 (divergence forward-return validity) has never returned anything but `"deferred"`** — no forward-collected native FantasyCalc snapshot series exists to populate `DivergenceResult`.
- **R² is not computed anywhere in the harness** — only Kendall/Spearman/NDCG/RMSE. The QB model (the one a Trevor-Lawrence-type model-vs-market read leans on) is the weakest engine, and rank metrics hide magnitude-prediction failure.

This spec converts the faithful-but-unproven anchor into a validated one. It is the unfinished half of the constitutional mandate that "backtesting is a trust layer, not optional QA."

## 1. Scope boundary (read first) + current-state ground truth

**This work extends the EXISTING Phase 10/11 + Phase 12 production harness.** Touch surface, verified present on `origin/main` post-S4 (2026-05-30):

| File | Role in this spec |
|---|---|
| `src/dynasty_genius/eval/backtest_harness.py` | add R² to fold metrics (`run()`); G3 consumer wired (`evaluate_promotion_gates`, `_compute_market_ndcg`) — **fix G3 under-coverage branch (C3)** |
| `src/dynasty_genius/eval/backtest_metrics.py` | add `compute_r2` + `compute_ndcg_diff_bootstrap` (W1 uncertainty); G4 stat building-blocks (`_bca_ci`, `_wilson_ci`, `diebold_mariano_hln`) present but the **`DivergenceResult` producer is unbuilt (W2b)** |
| `src/dynasty_genius/eval/backtest_artifact.py` | add R² fields to `FoldResult`; `GateResult`/`DivergenceResult`/`BacktestResult` schemas exist (G4 schema present, **producer absent**) |
| `src/dynasty_genius/eval/model_card.py` | report R² in `ModelCardMetrics` |
| `src/dynasty_genius/eval/market_snapshot_store.py` | backfill (`ktc_community_csv`/`dp_archive`) + forward (`fc_native`) — both store modes already supported |
| `app/api/routes/trust_surface.py` | QB-reliability stamp (W4) |

**CRITICAL GROUND-TRUTH (corrected in Codex round-1 review, 2026-05-30 13:34).** Some gate machinery exists from Phase 10/11; some does not. Stated precisely so the plan does not under-scope:

- **G3 producer + consumer both exist.** `_compute_market_ndcg` (`backtest_harness.py:66`) computes the model/market NDCG; `evaluate_promotion_gates` (`:182-195`) consumes it: `g3_market_superiority_pass: Literal[True, False, "deferred"]`. **Current state:** the verdict is hardcoded on `ndcg_at_24` (`:192`) in ≥3/4 market-available folds, `"deferred"` only when *zero* folds are market-available. **W1 changes two things about this existing code (Codex D2/C3):** (a) the verdict keys on the **position-primary k** from the §5 table, not hardcoded `@24` (QB/TE → @12); (b) `<3` evaluable folds → `"deferred"`, not `"failed"`. **W1's job is data (point-in-time backfill) + power honesty + these two gate-logic fixes — not building the gate from scratch.**
  - **Existing-code defect W1 must fix (Codex C3, verified `:186-195`):** with **1–2** evaluable folds, `wins >= 3` is impossible, so the gate returns `"failed"` — reporting *under-coverage as a market-superiority failure* (false confidence). W1 must change the branch so `< 3 evaluable folds → "deferred"` (with an artifact coverage caveat distinguishing zero-coverage from partial-coverage), never `False`.
- **G4: schema + gate-consumer exist; the matched-control PRODUCER does NOT (Codex C6, verified).** `DivergenceResult` (`backtest_artifact.py:69`) is defined, and `evaluate_promotion_gates` *consumes* a passed-in `divergence` (`:197-208`), but **nothing in the harness constructs a `DivergenceResult`** — no matched-control selection, no forward-return computation, no Mann-Whitney/BCa/Wilson assembly. The stat *building blocks* exist in `backtest_metrics.py` (`_bca_ci`, `_wilson_ci`, `diebold_mariano_hln`) but the producer is unbuilt. W2 is therefore split (§4): **W2a** = forward snapshot collection (RED-authorable now, starts the clock); **W2b** = the `DivergenceResult` producer + matched-control design (a separate increment, gated on ~6mo data maturity; design locked at §8.3).
- **R² is genuinely absent** — not in `FoldResult`, `ModelCardMetrics`, or `GateResult`. W3 adds it.

Net: the initiative is still predominantly **data-provisioning + R² + honesty-stamping**, but it includes one existing-code G3 fix (C3) and one genuinely-new producer (W2b) — neither is "build a gate from scratch," but the plan must scope both.

**Not in scope / explicitly barred:**
- Any change to Engine A/B *feature* sets or training rows (the market-overlay wall stays correct and untouched; W1 increases market-data *volume*, never its *role*).
- Any touch to S4's mock-draft modules (`backtest_mock_draft.py` and the `test_subsystem_4_*` suite).
- Frontend (Phase 12 HOLD). W4 changes a backend route's emitted caveat only.
- R5 (Phase 20 Engine A null root-cause) — separate research-only stub, its own doc and David approval; referenced in §12, never folded in here.

## 2. Robustness boundary (Falsification Discipline Rule 8 — up front)

Modules consuming external/variable market data must define their robustness boundary at design time:

- **API-misuse → fail loud.** Wrong argument types into `compute_r2`, the backfill adapter, or the snapshot writer raise immediately (caller contract).
- **Data-corruption → fail closed.** Malformed/empty community-CSV archives, missing snapshot dates, or under-covered folds must surface `"deferred"`/`"unavailable"`/null and a caveat — never a fabricated or silently-substituted value. (Constitution: "Truth over convenience"; Architecture: "Silent substitution is forbidden.")
- **Semantic/range/finiteness → producer's job.** R² may be negative (legitimately, for a worse-than-mean model); the spec treats negative R² as a real, reportable value, not an error. Non-finite (NaN/inf) inputs fail closed to null + caveat.

## 3. W3 — Compute & report R² in the harness  *(smallest, lowest-risk — first build)*

**Problem.** Rank metrics (Spearman) hide magnitude-prediction failure. QB R² was last seen *negative*. The harness reports no R² at all.

**Design.**
- Add `compute_r2(y_true, y_pred) -> Optional[float]` to `backtest_metrics.py` — coefficient of determination `1 - SS_res/SS_tot`, computed on the **OOS test fold only** (the harness's existing per-fold predict step). Negative values are valid and returned as-is. Fail-closed → `None` + a fold-level caveat on: degenerate `SS_tot == 0` (zero-variance truth); any non-finite (NaN/inf) in `y_true`/`y_pred`; length mismatch or empty fold (the latter two are API-misuse → raise per §2). (Resolves Codex C1.)
- **v1 reports OOS R² only.** Add `r2_oos: Optional[float]` to `FoldResult` in `backtest_artifact.py`. **In-fold R² (`r2_in_fold`) is explicitly OUT of v1 acceptance** — it is optimistic-by-construction and low-value, and "if cheap" is not RED-authorable (Codex C2). If a future increment wants it, it gets its own field + a defined train-set computation + its own RED; v1 does not gate or require it.
- **Caveat schema destination (Codex D1).** `FoldResult` has no structured caveat field today (only `regime_notes: Optional[str]`). W3 adds `metric_caveats: List[str] = []` to `FoldResult` — the named destination for every fail-closed caveat in this spec (R² zero-var/NaN/inf, and W1's `pool_below_k` / `insufficient_pool_for_bootstrap`). Caveat strings are fixed tokens (banned-language-safe), not freeform prose.
- Surface `r2_oos_mean: Optional[float]` + `r2_oos_per_fold: List[Optional[float]]` in `ModelCardMetrics` (Codex E1 — both must admit `null` since fail-closed folds emit `null`; `List[float]` would fail Pydantic validation). **Null handling:** `r2_oos_per_fold` carries `null` for any fail-closed fold; `r2_oos_mean` = mean over non-null folds with the contributing-fold count disclosed, or `null` if all four folds are null.
- Per-fold reporting: small-sample folds (QB n≈43) report the point estimate with an explicit small-sample caveat rather than a misleadingly-tight CI. (No bootstrap CI on R² in v1 — the point estimate + caveat is the honest v1 surface; a BCa CI on R² may be a later increment.)

**Acceptance gate (RED-authorable; thresholds LOCKED at Gate B §8):**
- `compute_r2` returns the exact closed-form value on a known fixture; negative-R² fixture returns the negative value (not clamped, not errored).
- Fail-closed rows (Codex C1): zero-variance-truth fixture → `None` + caveat; NaN-in-`y_pred` fixture → `None` + caveat; inf-in-`y_pred` fixture → `None` + caveat; length-mismatch / empty → raises (API-misuse, §2).
- `FoldResult` carries `r2_oos` per fold; `ModelCardMetrics` carries `r2_oos_mean` + `r2_oos_per_fold`. **No `r2_in_fold` field in v1.**
- **[LOCKED Gate B §8.1] R² = DISCLOSE only** — report-only, no promotion effect (R²-as-gate deferred behind the unbuilt Step 0.5 composite gate).

## 4. W2 — Native daily FantasyCalc snapshots → start the Gate-4 clock  *(time-gated; stand up early in the build)*

Split into **W2a** (snapshot collection — RED-authorable now) and **W2b** (the `DivergenceResult` producer — a later increment), per Codex C6/C7: only W2a is buildable today; W2b's matched-control statistics must not be hand-waved into a RED that can't be authored.

**Problem.** G4 needs a forward-collected, point-in-time snapshot series that **does not exist yet.** Verified 2026-05-30: `scripts/snapshot_fantasycalc.py` exists and writes `app/data/fc_snapshots.db`, but it is **not scheduled** (no crontab, no active LaunchAgent, no GH Actions schedule) and **has never run** (`fc_snapshots.db` absent). Every day not collecting pushes the Gate-4 readiness date out a day.

### W2a — Forward snapshot collection (build now; starts the clock)

**Design.**
- Confirm + activate scheduled execution of `snapshot_fantasycalc.py` writing `fc_native` rows to `MarketSnapshotStore`. Local-first scheduling (LaunchAgent or a documented manual daily cadence) — **no Databricks** (`[[project_databricks_spend_limit]]`).
- **Immutability contract (concrete; Codex D3 + the round-1 "mutate under an idempotent label" risk).** A snapshot row is keyed by the store's existing PRIMARY KEY `(snapshot_date, league_settings_hash, sleeper_id)` (`market_snapshot_store.py:31`). **Existing-code defect this fixes:** the store currently writes with `INSERT OR REPLACE` (`:62`) — which *silently overwrites* an already-recorded date. W2a replaces that with **append-only verify-or-raise**: a same-key re-run first verifies value-identity of the existing row and **raises on any divergence** (a changed value for an already-recorded date is a corruption signal, not an overwrite); identical re-run is a verified no-op. `_row_count_for_date` / `_resolve_date` are the existing read seams; the contract adds the write rule. Provenance per row: source, fetch timestamp, `league_settings_hash`, URL params, archive/publish date.

**W2a acceptance gate (RED-authorable now):**
- Daily `fc_native` write verified immutable + provenance-stamped: same-date re-run with identical values is a verified no-op (row count + values stable); same-date re-run with a *changed* value RAISES (no silent mutation).
- Distinct dates accumulate as distinct immutable row-sets.
- **No file-lock conflict with S4** — S4 is merged; lock released. (The brief's "verify at spec time" hedge is resolved: no conflict.)

### W2b — `DivergenceResult` producer + Gate-4 run (later increment; design locked at §8.3)

**Status:** the producer is unbuilt (Codex C6). W2b builds matched-control selection + forward-return computation + `DivergenceResult` assembly so a future run can populate G4. It is **gated on ~6 months of W2a data maturity** and on David's §8.3 design lock — it does **not** block this spec or the W3/W1/W4 build. Carrying it as a named, scoped increment (not hand-waved into W2a's RED) is the point of the split.

**Design to lock at §8.3 (not RED-authorable until locked):** matched-control selection (covariates to match on, caliper, whether K=3 is adequate at the realized flagged-n), forward horizon (180 vs 365 days), the flag definition, and confirmation of the stat battery already schema'd in `DivergenceResult` (Mann-Whitney exact/asymptotic + BCa diff CI + Wilson hit-rate CI, beta-adjusted alpha). Output: a populated `DivergenceResult` the existing G4 consumer already reads.

## 5. W1 — Historical market backfill → run G3 (market superiority)  *(keystone — most adversarial scrutiny)*

**Problem.** G3 returns `"deferred"`: no market data at the harness's evaluation dates. The system cannot yet claim it beats the market.

**Design.**
- Use the existing community-CSV ingest (`scripts/ingest_market_archive.py`) + `MarketSnapshotStore` (`ktc_community_csv`/`dp_archive` modes) to backfill historical FantasyCalc dynasty values at the harness's `_market_snapshot_date(test_year)` targets (the walk-forward folds: test years 2020–2023, market-snapshot dates per `_market_snapshot_date`). Then let the *already-built* `_compute_market_ndcg` + G3 path run.
- **Point-in-time integrity (Codex condition, non-negotiable).** Backfilled archive rows must be the values **as published at the snapshot date** — no post-hoc revision, no survivorship leakage (players who later busted/retired must still be present at their historical value). The ingest must record the archive's own publish date and reject rows whose provenance cannot establish point-in-time correctness → fail closed (`market_source="unavailable"` for that fold, G3 stays `"deferred"` for it).
- **G3 under-coverage fix (Codex C3) — part of W1.** Change the `evaluate_promotion_gates` G3 branch so `len(market_available_folds) < 3 → "deferred"` (never `False`). The artifact records a coverage caveat distinguishing `zero_market_coverage` from `partial_market_coverage_{n}_of_4`. This is a behavior change to existing Phase-10/11 code and gets its own RED (assert 1- and 2-evaluable-fold inputs return `"deferred"`, not `"failed"`).
- **Position-aware NDCG cohort/k table + coverage reconciliation (Codex C5).** `_compute_market_ndcg` currently computes @12/@24 and returns `None` when pool n < k (`backtest_harness.py:110`). v1 fixes the *primary* k the G3 verdict keys on, per position, with a documented fallback (these k values are LOCKED at Gate B §8.2 (the table below stands)):

  | Position | Primary k (verdict) | Secondary k (report) | Typical matched pool n | Rule |
  |---|---|---|---|---|
  | QB | 12 | 24 if pool ≥ 24 | ~32–50 | verdict keys on @12; @24 reported when pool supports it |
  | RB | 24 | 12 | ~60–90 | verdict keys on @24 |
  | WR | 24 | 12 | ~90–130 | verdict keys on @24 |
  | TE | 12 | 24 if pool ≥ 24 | ~30–45 | verdict keys on @12 |

  Coverage reconciliation: a fold's `@k` is computed only when matched pool n ≥ k; otherwise that k is `null` + a `pool_below_k` caveat, and the fold is **not** counted as market-available for the verdict (feeds the C3 under-coverage rule). Unmatched players are excluded from the pool and never silently shrink k.
- **NDCG-difference uncertainty contract (Codex C4) — `compute_ndcg_diff_bootstrap`.** Not "a CI or spread" — a defined statistic: **paired player-level bootstrap** over the matched pool — resample player indices with replacement (B = 1000, fixed `rng_seed` per the harness's existing BCa convention), apply the *same* resample to model-rank and market-rank against realized PPG relevance, compute `ndcg_diff@k = ndcg_model@k − ndcg_market@k` per resample, return point `ndcg_diff@k` + BCa 95% CI (reuse the `_bca_ci` pattern) + `pool_n`. Degenerate (pool < primary k, or < ~10 paired points) → `null` diff + `insufficient_pool_for_bootstrap` caveat. Multiple-comparisons exposure across 4 positions disclosed in the artifact.
- **Leakage wall re-verified under load (Gemini + constitution).** Backfilled market rows increase market-data *volume*; they must remain overlay-only and never enter any Engine A/B training/feature path. The S4 anti-laundering AST audit pattern is the model; an equivalent check confirms no market field crosses into `engine_*` features under the new data volume.

**Acceptance gate (RED-authorable; thresholds LOCKED at Gate B §8.2):**
- G3 returns `"deferred"` (not `"failed"`) on 1- and 2-evaluable-fold inputs (C3 RED).
- G3 is *evaluable* for ≥3 of 4 folds per position only when each counted fold has matched pool n ≥ its primary k (point-in-time-valid market data present).
- Artifact reports per position per fold: `ndcg_model@{primary,secondary}`, `ndcg_market@{...}`, per-fold win/loss, `pool_n`, and `compute_ndcg_diff_bootstrap` output (point diff + BCa CI) with multiple-comparisons disclosure.
- **A loss or tie is a valid, publishable result.** The deliverable is *truth about the edge*, not a passing grade.
- **[LOCKED Gate B §8.2] G3 PASS threshold = ≥3/4 evaluable folds at the position-primary k, with the NDCG-diff bootstrap CI disclosed** (CI reported but not required to exclude 0).
- **[LOCKED Gate B §8.4] external-source sign-off = APPROVED** — historical FC archive approved for W1, overlay-only, with the §5 point-in-time/provenance requirements.

## 6. W4 — Stamp QB-model reliability on consuming surfaces  *(depends on W3 metrics)*

**Problem.** A TLaw-type QB divergence read silently inherits the least-validated engine.

**Design (scope narrowed per Codex C8).** W4 touches **exactly one surface**: a single QB-reliability caveat field on the `trust_surface.py` response (the existing trust-surface route — name the exact field/endpoint at plan time), sourced from W3's measured OOS R²/Spearman. **NOT "anywhere divergence is consumed"** — Trade Lab, PVO, and other consumers are explicitly out of W4 scope (they would each be their own later increment if ever wanted). One field, one route.
- **Banned-language-safe (Codex + Gemini condition).** Wording is a measured-uncertainty caveat — **no buy/sell/roster-action, no verdict/tier/grade/confidence-from-bucket** (north-star banned-field list). It states the metric reality ("QB OOS R² = X, Spearman = Y; magnitude predictions carry elevated uncertainty"), not a recommendation. Must survive the existing banned-language guard.

**Draft acceptance gate (RED-authorable):**
- QB outputs carry an explicit reliability stamp sourced from W3's measured R²/Spearman.
- Banned-David-facing-language guard stays green; no false-confidence phrasing; no buy/sell/action language.
- `decision_supported` unchanged (False); no frontend change (HOLD).

## 7. Sequencing & cockpit roles

**Build order (internal to the TDD step):**
1. **W3 (R²)** — smallest, lowest-risk warm-up.
2. **W2a (snapshot clock)** — stand up `fc_native` daily collection early; starts the Gate-4 timer. (W2b producer is a later, data-gated increment — §4.)
3. **W1 (G3 backfill + under-coverage fix)** — keystone; most adversarial scrutiny (point-in-time integrity, k-table/uncertainty, leakage wall).
4. **W4 (QB stamp)** — depends on W3's metrics; one trust-surface field.

W2b (DivergenceResult producer / Gate-4 run) is out of this build's critical path — it waits on ~6mo of W2a data + the §8.3 design lock.

**Cockpit roles (locked review pattern + Reviewer Lane Calibration):**
- **Codex = spine.** Test-drives the statistical gates RED-first (R² computation, G3 NDCG comparison + power disclosure, Gate-4 matched-control). Stats-heavy, test-first — its lane.
- **Claude Code = implementer.** Greens the gates; owns the backfill adapter + snapshot-store plumbing.
- **Gemini = governance review ONLY** (`[[feedback_multi_agent_review]]`): leakage compliance (W1 overlay-only), banned-language, external-source provenance/sign-off, scope-boundary enforcement (R5 stays research-only; no bleed into S4 or model inputs). Technical assertions non-binding unless cited (Reviewer Lane Calibration).
- **David = arbiter.** Owns the PASS thresholds (§8) and the R² gate-vs-disclose call.

## 8. David rulings — LOCKED at Gate B (2026-05-30)

David's Gate B decisions on the product rulings. The mechanisms were dual-CLEARed (Codex technical v4, Gemini governance ×3); these values are now binding inputs to the plan.

### 8.1 R² gate-vs-disclose — **LOCKED: DISCLOSE ONLY** *(ties to `[[project_step_0_5_followups]]`)*
Measured R² **discloses** (reports per fold/position with caveats), it does **not** gate promotion. Rationale: "gate" is not currently buildable — `_PROMOTION_ABOVE_C_GATED_UNTIL_STEP_0_5 = True` in `train_models.py` and the `validation/composite.py` composite gate was never shipped. **R²-as-gate is a separate later increment** sequenced after the Step 0.5 composite gate (which would also reconcile the inherited `low_sample_holdout` RB-semantics item). This build implements disclose only.

### 8.2 G3 PASS threshold — **LOCKED: ≥3/4 folds + disclosed CI**
G3 may claim market superiority when `model ≥ market NDCG at the position-primary k` (§5 table — QB/TE @12, RB/WR @24) in **≥3/4 evaluable folds**, with the `compute_ndcg_diff_bootstrap` CI **reported alongside** (the noise floor is always visible) but **not required to exclude 0**. The primary-k values in the §5 table stand as drafted. A loss/tie publishes honestly regardless. *(Note: this is a looser bar than "CI excludes 0" — the honesty guard is the mandatory CI disclosure, not a significance gate.)*

### 8.3 Gate-4 (W2b) design lock + readiness — **DEFERRED** (lock when W2b is authored, ~6mo)
Not locked now — W2b (the `DivergenceResult` producer) is data-gated on ~6 months of W2a collection, so locking its matched-control design (K=3 controls, covariates + caliper, forward horizon 180/365, flag definition, the MW p ≤ 0.10 / diff-CI>0 / hit-rate-CI>0.50 defaults, readiness date) now would be premature. **W2a + W3 + W1 + W4 proceed without it;** §8.3 reopens as a focused ruling when W2b is authored.

### 8.4 W1 external-source sign-off — **LOCKED: APPROVED**
David **approves** the historical FantasyCalc archive as W1's external data source (operating-loop escalation trigger satisfied), conditioned on the spec's point-in-time integrity + provenance requirements (§5): rows must be as-published-at-snapshot-date, no post-hoc revision/survivorship leakage, and the source remains **overlay-only** (never trains Engine A/B).

## 9. Governance & leakage invariants (binding)

1. **Overlay-only wall.** Market data (backfilled or forward) never enters Engine A/B training/features. Re-verified under the new data volume via an anti-laundering check (S4 AST-audit pattern).
2. **External-source escalation.** W1 archive needs §8.4 sign-off.
3. **decision_supported=False** throughout; no banned David-facing language on any surface (W4 especially).
4. **Fail-closed honesty.** Missing/under-covered/non-point-in-time data → `"deferred"`/`"unavailable"`/null + caveat, never substitution.
5. **Local-first / spend.** All local; no Databricks without per-session David override.
6. **Frontend HOLD** intact; W4 is a backend caveat only.
7. **Inviolate boundaries.** S4 modules and Engine A/B model artifacts untouched; one agent owns a cross-cutting file at a time; AGENT_SYNC + ledger per session; close-the-loop confirmations.

## 10. Out of scope

- Engine A/B feature/training changes (market stays overlay-only).
- S4 mock-draft modules.
- Frontend surfaces (Phase 12 HOLD).
- **R5** (Phase 20 Engine A null root-cause) — research-only, separate doc (`2026-05-28-phase20-engine-a-null-rootcause-research-stub.md`), separate David approval, hard lock: no production model change.
- Building the Step 0.5 composite gate (a prerequisite for R²-as-gate, sequenced separately).

## 11. Counter-argument (Constitution: counter-argument required)

1. **"Premature — finish the subsystem chain first."** Queued explicitly; can slot whenever David chooses. But note the **W2 clock**: every day Gate-4 collection is deferred is a day until divergence can *ever* be validated — real option-value cost on W2 specifically.
2. **"G3 may just tell us we don't beat the market."** That is the point. A model that loses to the market is vital to know *before* leaning on its divergence calls. An honest loss redirects effort; a hidden loss compounds into bad trades.
3. **"R² on n≈43 QBs is itself noisy."** True — which is why W3 reports it per-fold with explicit small-sample caveats and W1 stress-tests power. The cure for one weak metric is more honest metrics, not fewer.
4. **"Scope creep into a generic backtest platform."** Guarded: 4 workstreams against named files, no S4/Engine-feature touch; the G3 gate consumer + producer already exist (W1 is data + one under-coverage fix), R²/W4 are additive, and the one net-new producer (W2b) is explicitly data-gated and deferred — this is data + R² + stamping, not platform-building.

## 12. Audit trail

- Brief: `docs/strategies/2026-05-28-harness-trust-completion-scoping-brief.md`
- Reviews: ledger 2026-05-30 (Gemini 13:18, Codex 13:19, Claude reconciliation 13:22)
- This spec: dual-CLEAR loop (Codex technical + Gemini governance) → David Gate B (lock §8) → plan → cockpit TDD.
