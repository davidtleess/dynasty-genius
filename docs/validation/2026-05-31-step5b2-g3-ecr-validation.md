# Step-5b.2 G3 Validation — Engine B vs DynastyProcess Expert Consensus

- **Date:** 2026-05-31
- **Status:** DESCRIPTIVE / DIAGNOSTIC — not decision-grade. No edge claim.
- **Initiative:** Harness Trust Completion → Step-5b (historical market backfill) → Step-5b.2 (G3 run).
- **Run git_sha:** `12f55658` (audit-trail commit; Step-5b.2 production code GREEN landed in `9e5b59a`).
- **Model:** `engine_b_v2`, `refit_per_fold_fixed_alpha`, schema `1.0.0`.
- **Baseline source:** DynastyProcess point-in-time archive, labeled `dynastyprocess_ecr_2qb` — **expert-consensus ECR (2QB), NOT a trade-market price.** Source verified in `docs/validation/2026-05-30-step5a-dynastyprocess-source-verification.md`.

## What this is

The first real G3 run of the model-validation harness against a **historical, point-in-time** market baseline (replacing the prior synthetic placeholder). G3 asks: **does Engine B's ranking beat or usefully diverge from the market baseline at the decision-relevant top-k, measured against realized outcomes?**

It is a **trust-surface** measurement. Per the constitution it is descriptive — it does not, by itself, authorize any David-facing decision-grade claim.

## Method

- **Design:** expanding-window walk-forward, feature-season N → preseason N+1 snapshot.
- **Folds:** 4 (feature seasons 2020–2023 → snapshots 2021-09-08, 2022-09-08, 2023-09-08, 2024-09-08).
- **Metric:** NDCG at position-primary k (Gate B: QB/TE @12, RB/WR @24) of model ranks vs market ranks, scored against **realized PPG**.
- **Comparison statistic:** paired BCa bootstrap 95% CI on the per-fold NDCG-diff (model − market). CI is **disclosed, not gating** (David Gate B ruling §8.2).
- **G3 point-estimate rule (Gate B §8.2):** PASS = model ≥ market at position-primary k in **≥3/4 evaluable folds**.
- **No imputation / smoothing / centered windows / forward-fill.** Under-coverage folds defer (do not fail). All four folds were evaluable for every position (pools ≥ primary-k).
- **Crosswalk:** GSIS→Sleeper via `db_playerids`; malformed ids (fractional/non-numeric/non-finite/blank) skipped, never truncated; zero-overlap folds fail loud (Design S). See harness commit `9e5b59a`.

## Coverage

2185 `dp_archive` rows across the four dates; matched pools per position-fold (all evaluable):

| Pos | primary-k | matched pool n (2021/22/23/24) |
|---|---|---|
| QB | 12 | 40 / 44 / 45 / 49 |
| RB | 24 | 86 / 86 / 89 / 79 |
| WR | 24 | 125 / 128 / 132 / 130 |
| TE | 12 | 184 / 121 / 75 / 65 |

## Results

Per-fold NDCG-diff (model − consensus) at primary-k, with BCa 95% CI:

| Pos | fold diffs (model − consensus) | folds model ≥ mkt | ≥3/4 rule | every CI includes 0? |
|---|---|---|---|---|
| QB | −0.052, −0.041, +0.001, −0.005 | 1/4 | does **not** pass | yes |
| RB | −0.024, −0.001, −0.058, −0.042 | 0/4 | does **not** pass | yes |
| WR | +0.010, +0.010, +0.016, −0.039 | 3/4 | **passes** | yes |
| TE | −0.016, +0.019, +0.046, −0.037 | 2/4 | does **not** pass | yes |

Both rankers score realized PPG well at top-k: primary-k NDCG ranges ≈ **0.82–0.97 for *both* model and consensus** across all folds (lowest observed 0.816 — RB model, 2022 fold; highest 0.973). All point differences are small (|diff| ≤ 0.058). **Every fold's BCa 95% CI on the NDCG-diff straddles zero** by a wide margin (roughly ±0.2 to ±0.5).

## Verdict

**Consensus-competitive; edge unproven.** Engine B is **statistically indistinguishable** from DynastyProcess expert consensus at the position-primary top-k over 2021–2024. By the point-estimate ≥3/4 rule only **WR** passes — but that pass is **statistically unconfirmed** (its CIs include 0), and QB/RB/TE's apparent deficits are equally insignificant. **No proven edge in any direction.**

The model-vs-market-**divergence-as-edge** hypothesis is **not supported on this sample, and not refuted** — it remains unvalidated.

## Limits

- **Low statistical power.** 4 annual folds at k=12/24 produce wide bootstrap CIs *because the sample is thin*, not because the model is erratic. This run cannot establish an edge in either direction.
- **The baseline is *rational* expert consensus (ECR), not the trade market.** Tying with a strong rational baseline is the expected, healthy outcome of a sanity check — it is not evidence about whether the model can exploit an *emotional/volatile* trade market (KTC/FantasyCalc). Those are different questions.
- **The formal harness grade incorporates the point-estimate G3 rule — but that is not a statistical edge claim.** The artifact `promotion_gate` includes `g3_market_superiority_pass`: WR = `True` → `overall_grade=ACTIVE_B_VALIDATED` (justification: "G1 rank-corr pass, G2 stability pass, G3 market superiority pass"); QB/RB/TE = `False` → `ACTIVE_B` ("Promotion blocked by G3"). That G3 gate is the **point-estimate ≥3/4 rule** (Gate B §8.2), which by David's ruling is **CI-disclosed, not CI-gated**. This report therefore does **not** reinterpret WR's `ACTIVE_B_VALIDATED` as a statistically *proven* market edge: the disclosed BCa CI on every WR fold-diff includes 0, so the point-estimate pass is real per the gate definition but statistically unconfirmed.

## What the result means for the thesis (team brainstorm, 2026-05-31)

The ECR tie **relocates** the edge thesis rather than killing it. Because Engine B is now a verified "rational anchor" competitive with expert consensus, the edge — if it exists — lives in two places ECR cannot reach:

1. **Decision-context translation.** ECR is blind to David's league: Superflex scarcity, forced-cut capacity, taxi/IR limits, future-pick value, contender/future posture. The model is a consensus-grade ranker; the product edge is translating that rank into David's specific portfolio constraints.
2. **Divergence vs the *emotional* trade market.** The meaningful divergence test is model-vs-**trade-market** (KTC/FantasyCalc), not model-vs-ECR. Being a rational anchor is what makes model-vs-trade-market deltas a useful **review trigger** — flag a player for a mandatory human counter-argument, never an automatic buy/sell.

## How this may be used (honest-recording constraints)

- Frame as **"consensus-competitive, edge unproven."** WR is **"point-rule pass, statistically unconfirmed,"** never a validated win.
- **Not decision-grade.** Do not promote into David-facing decision confidence. Use divergence as a **review trigger** (require counter-argument + human verification), not a buy/sell signal.
- Market data stays **overlay-only**; no market-derived feature enters Engine A/B training. Frontend HOLD intact.

## Next experiments (sequenced)

- **B — Subpopulation / axis-of-edge study (next, cheap):** slice existing fold data — rookies/young (first ~2 seasons), aging-cliff cohorts (RB 26 / WR 28 / TE 30 / QB 33), and high model-vs-consensus disagreement buckets. Edge most plausibly appears where static consensus is weakest. More diagnostic per dollar than broadening archive years.
- **C — Trade-market baseline (deferred / parallel):** historical point-in-time FantasyCalc/KTC trade-market archive via W2b / Gate-4 daily collection (Gate-4 clock starts when David loads the W2a scheduler). This is the *real* actionable-mispricing test; overlay-only.

## Provenance

- Run artifacts: `app/data/backtest/runs/{483f87f9…/QB, e639a40c…/RB, fc1e6e1c…/WR, 6ba3a451…/TE}/backtest_result_*.json` (+ `market_comparison_*.json`, `predictions_*.csv`). Run dirs are local/gitignored; regenerate with:
  `.venv/bin/python3.14 scripts/run_backtest.py --all --market-store app/data/fc_snapshots.db --id-map-csv <db_playerids.csv>` (TE via `--position TE`; `ACTIVE_POSITIONS` excludes TE from `--all`).
- Market store: `app/data/fc_snapshots.db` (local/gitignored), `dp_archive` source, 4 verified kickoff dates.
