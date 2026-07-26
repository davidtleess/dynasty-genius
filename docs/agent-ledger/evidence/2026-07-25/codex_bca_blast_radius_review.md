# Adversarial review — BCa zero-width-CI blast radius

**Reviewer:** Codex, independent technical lane
**Source attacked:** `/tmp/gemini_bca_blast_radius.md`
**Scope:** read-only source/artifact inspection plus in-memory probes; no helper/code/artifact edit, commit, push, wire, or delivery tooling.

## Bottom line

The report is **materially less serious than written in present-tense blast radius**. It flattens four different states into `USER-VISIBLE`:

- one live rendered/gated path whose **ordinary degenerate inputs do not reproduce the claimed collapse** under the installed SciPy;
- one **currently inactive** future API path with no artifact and no metric rendering;
- one live API-only diagnostic with a readily reachable zero-width CI but **no UI column and no promotion gate**; and
- one real promotion-evidence pipeline whose custom helpers have a **normal, reachable fail-open degeneracy branch**, although the committed run contains no collapsed CI and did not promote.

Tower should **not** tell David that four shipped user-visible pipelines are presently emitting false certainty. The defensible recommendation is narrower: schedule a preventive validation-integrity hardening slot, led by the QB-v3 custom helpers and the exception fallback in the shared rank helper, before either validation is rerun. There is no evidence that a current displayed artifact or past promotion decision was corrupted by this defect.

## Per-call-site verdicts

### 1. `compute_rank_correlation` → Engine-B trust surface: **OVERSTATED**

**Pipeline reach is confirmed.** `WalkForwardDriver.run()` unconditionally calls `compute_rank_correlation` for every fold (`backtest_harness.py:593-595`); the four current trust artifacts contain 16 fold CIs and the Trust Console renders them. Current `n_test` is 43–206, well above the helper's only `n<10` guard. The route and gate are therefore genuinely live.

**The reported trigger is wrong in practice.** The report says zero variance/perfect agreement reaches `_bca_ci`'s `(point, point)` fallback. With installed SciPy and the shipped defaults, it does not:

- perfect rank agreement at `n=10` reproduced point estimates ≈1.0 but CIs **`[-1.0, 1.0]`**, with `DegenerateDataWarning`/`RuntimeWarning`;
- constant predictions at `n=10` reproduced non-finite points and CIs **`[-1.0, 1.0]`**;
- a tied, finite `n=10` case produced ordinary nonzero-width intervals.

Reason: SciPy returns non-finite bounds with warnings rather than raising; `_bca_ci` then turns them into `[-1,1]` through its range clamp (`backtest_metrics.py:101-106`). The dangerous zero-width branch at `:107-110` requires an actual exception. No shipped caller varies `n_bootstrap` from the valid default or passes fewer than 10 rows after the guard, and all 16 current artifact intervals have positive width. Thus ordinary data degeneracy is fail-wide here, not fail-narrow.

**The gate consequence remains real if an exception occurs.** The current QB artifact is `PROVISIONAL` with `failed_ci_folds=[1,3]`; fold 1 is the mechanically tolerated cold start, all rank folds pass, and the most recent fold passes. Therefore **one** exception during QB fold 3's Spearman bootstrap would yield a positive-point zero-width CI, remove the only non-tolerated CI failure, and change the composite status to `VALIDATED`. The smallest trigger is not “perfect correlation”; it is any SciPy/runtime exception after the positive point estimate is computed. That is a fail-open exception-policy defect, but I could not reproduce it from valid current data without fault injection.

**Verdict basis:** live/rendered/gated pipeline confirmed; natural reachability and present corruption refuted; severity overstated but preventive fix justified.

### 2. `compute_rank_correlation` → realized-outcome scorecard: **REFUTED as presently USER-VISIBLE; latent future API risk**

This pipeline does **not execute in the shipped product today**:

- `app/data/realized_outcome/scorecard_latest.json` is absent;
- the terminal marker records `status=noop`, `noop_reason=no_predictions_for_target`, season 2025 week 22;
- the producer explicitly says off-season is the dominant path and scoring waits for finalized 2026 weeks (`run_realized_outcome_scoring.py:8-11`);
- the route returns the healthy `inactive` response when the artifact is absent (`realized_outcome_scorecard.py:74-100`);
- the React surface says rich metric rendering waits until a real artifact exists and renders no metric table (`RealizedOutcomeScorecard.tsx:13-19,85-101`).

Future reach is guarded but possible: `_cohort_metric` requires at least 10 rank-eligible players (`realized_outcome_scorer.py:157-174`), validates finite inputs, and returns the power-floor stub when Spearman itself is non-finite (`:175-176`). Once 2026 predictions/outcomes exist, a valid cohort can call the shared helper. But the same probe result as call site 1 applies: ordinary perfect/constant degeneracy does not reach a zero-width fallback under installed SciPy. A positive zero-width scorecard CI requires an actual helper exception.

The API is a running-software contract, so this is properly **future API-exposed**. Calling it currently `USER-VISIBLE` is inflated: there is no scorecard artifact, the API returns no metrics, and the UI deliberately does not render them. Stored-artifact reach in the report is also false in the present tense because the named artifact does not exist.

### 3. `compute_ndcg_diff_bootstrap` → trust artifact/API: **OVERSTATED impact, CONFIRMED reachable collapse**

The collapse is naturally reachable after its real guards. `n >= max(k,10)`, finite inputs, and positive ranks are sufficient (`backtest_metrics.py:163-198`). Reproduced:

- identical model/market ranks with `n=k=12` → `ndcg_diff=0.0`, CI **`[0.0,0.0]`**, no caveat;
- `n=14,k=12`, identical ranks through the top 12 but swapped ranks below `k` → the same zero-width CI. Thus exact below-cutoff disagreement does not prevent collapse.

The smallest shipped trigger is pool `n=12` for QB/TE or `n=24` for RB/WR with identical effective top-k rank contributions. This is realistic agreement, not an exotic exception. The contract test explicitly locks the behavior (`test_harness_trust_w1_bootstrap.py:92-106`).

But the blast-radius severity is lower than the report implies:

- all 16 current trust-artifact NDCG-difference CIs have positive width;
- `FoldTable` does not render this field;
- it enters no composite/promotion gate;
- its statistical-superiority interpretation is explicitly disclosure-only in the governing validation note.

The trust API serves the field, so `API-VISIBLE` is fair. `USER-VISIBLE` without qualification overstates what David sees in the normal React surface, and this call site cannot cause promotion. This is an honesty/artifact-quality bug, not the priority driver.

### 4. QB-v3 `_bca_interval` / `_bca_auc_delta_interval`: **CONFIRMED preventive promotion-integrity defect**

The pipeline really executed: the committed evidence contains seven evaluable fold-horizon rows, and the ratified decision record directly summarizes their gates. None is collapsed. Every current Brier and AUC interval has positive width; H1 is structurally ineligible (1/4 evaluable), and H2/H3 failed because lower bounds did not clear zero. The 2026-07-04 decision was **NOT PROMOTED**, so there is no historical false promotion to correct.

Unlike the shared helper, these custom branches are normally reachable: both helpers explicitly collapse when `np.allclose(boot, boot[0])` (`qb_v3_walk_forward.py:235-236,273-274`).

**Smallest admissible reproduced trigger:** the real upstream floor is `n_test >= 30` and minority class `>=10` (`:49-50,400-411`). At exactly `n=30` (20 negatives, 10 positives), baseline prevalence `1/3`, constant within-class probabilities `p0=0.2472066`, `p1=0.3719519` produce:

- perfect AUC `1.0`, AUC-delta CI **`[0.5,0.5]`**;
- equal positive per-row Brier improvement `0.05`, Brier-delta CI **`[0.05,0.05]`**.

That synthetic fold passes both lower-bound checks with fabricated certainty. Perfect AUC alone is more realistic: with complete class separation and 30+ rows, almost every bootstrap replicate retains both classes, so AUC delta is invariant at 0.5 and collapses even when Brier improvements vary. A false horizon promotion then requires the structural fold floor (H1/H2 3 of 4; H3 2 of 3) plus every evaluable fold's other lower bound above zero. A **single** collapsed interval can be decisive if the companion CI and other folds genuinely pass; both intervals need not collapse together.

Thus the helper is a real fail-open promotion-record defect worth fixing before a future QB-v3 rerun. The report should say **future promotion-integrity risk, current evidence unaffected**, not generic live user-visible corruption.

## Missed implementations / wrappers

### Missed BCa sibling: `subpopulation_landscape._bootstrap_rho_diff`

The report omitted `src/dynasty_genius/eval/subpopulation_landscape.py:306-378`. It initializes `lo=hi=rho_diff`, preserves that collapse on non-finite SciPy bounds, and on exception also sets `boot_p_value=0.0` for any nonzero point. Reproduced at its actual `SPEARMAN_MIN_N=30`:

- model ranks perfectly aligned, consensus perfectly reversed, `n=30` → `rho_diff=2.0`, CI **`[2.0,2.0]`**, `ci_includes_zero=False`, `boot_p_value=0.0`.

Reach is real: `run_subpopulation_landscape.py:204-215` calls it and writes run/latest JSON and Markdown artifacts. Impact is bounded: the fold CI/p-value is descriptive; aggregate follow-up candidacy recomputes an exact fold-level sign-flip p-value from `rho_diff` (`run_subpopulation_landscape.py:216-235`) and is structurally unreachable at ≤4 folds. The rendered Markdown does not print the per-fold CI. Classification: missed artifact-honesty defect, not a promotion path.

### Same collapse shape but guarded: Gate-4 month-block bootstrap

`gate4_divergence_edge.month_block_bootstrap_ci` returns `[0,0]` when it has no bootstrap stats (`:272-277`). This is not BCa and does not share `_bca_ci`, but it is the same false-certainty shape. The downstream verdict checks `effective_month_block_count < MIN_EFFECTIVE_BLOCKS` and returns `UNDERPOWERED` before the CI can pass (`:376-397`). It is therefore a useful counterexample: zero-width output exists, but the promotion path fails closed.

### Checked and not affected

The new QB-1 inference implementation does not reuse these helpers; it names replicate/jackknife degeneracy and returns unavailable endpoints. No additional production `scipy.stats.bootstrap` call sites exist beyond the shared metrics helper and the missed subpopulation sibling.

## Recommendation to Tower

Recommend David spend a bounded hardening slot, but **withdraw the “four USER-VISIBLE pipelines currently at risk” framing**.

Priority order:

1. QB-v3 custom intervals before any rerun or renewed promotion attempt.
2. Shared `_bca_ci` exception fallback because a single exception on current QB fold 3 could flip `PROVISIONAL` to `VALIDATED`, even though normal degeneracy currently fails wide.
3. NDCG and subpopulation diagnostic collapses as the same honesty-family cleanup.
4. Realized-outcome path before its first real 2026 scorecard, not as an active incident.

Current-artifact audit: no zero-width rank, NDCG, or QB-v3 CI was found in the live/committed artifacts inspected. The right severity is **preventive validation-integrity defect with one concrete future promotion path**, not evidence that David is presently seeing or acting on corrupted certainty.
