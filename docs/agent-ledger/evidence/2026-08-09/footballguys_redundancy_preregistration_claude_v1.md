# Pre-registration — Footballguys `adp_sleeper-sf` redundancy vs the market baseline we already hold

Date: 2026-08-09 · Claude (implementing lane) · Layer 1/2
**Written and hashed BEFORE the statistic is computed.** Framing v1 seed F11: a materiality
threshold chosen after seeing the number is not a result. This file exists so the threshold cannot
move.

## 1. Correction to framing v1 seed F10, before anything is run

F10 named **KTC** and **`dynastyprocess_ecr_2qb`** as the redundancy baselines. **Codex challenged
this as an unverified claim and Codex is right.** Measured on disk this session:

- `app/data/ktc.py` is a **55-byte Python file**, not data. **No KTC data artifact exists.**
- **No `dp_archive` / ECR artifact exists** under `app/data`. `dynastyprocess_ecr_2qb` survives only
  as a *label* in `src/dynasty_genius/eval/backtest_harness.py:71` and a `Literal` in
  `eval/backtest_artifact.py:165-168`. A label is not an artifact.
- The **only** market data actually held is **FantasyCalc**: `app/data/fc_forward_capture.db`,
  table `fc_forward_capture_joinable`, `source = fc_native`, 21,941 rows, **47 daily snapshots
  spanning 2026-06-24 → 2026-08-09**, latest snapshot **475 rows with `value`, `overall_rank`,
  `position_rank`, `sleeper_id` all populated**.

**F10 is therefore re-specified against FantasyCalc.** The `ff_rankings` Spearman .99 precedent was
measured against `ecr_2qb` and remains the *precedent*, but it is not reproducible here as a
baseline because the artifact is absent.

## 2. What is compared

- **Candidate:** `adp_sleeper-sf` from `adp.csv` (500 populated of 608; dense rank 1..500).
- **Baseline:** FantasyCalc `overall_rank` at the **latest** snapshot (`2026-08-09`, 475 rows).
- **Join:** Footballguys `pfr_id` → governed crosswalk → `sleeper_id` → FantasyCalc `sleeper_id`.
  **The 34 measured wrong-human ids are excluded**, and every retained pair is name-verified against
  `projections.csv`. Ids that cannot be name-verified are **excluded, not assumed correct**.
- **Statistic:** Spearman rank correlation on the verified intersection, plus top-24 overlap.
- The intersection size is reported with the statistic. **A correlation on a small or biased
  intersection is not evidence about the whole file, and will be stated as such.**

## 3. The thresholds, fixed now

| Spearman ρ on the verified intersection | Reading, fixed in advance |
| :-- | :-- |
| **ρ ≥ 0.95** | **Redundant.** Consistent with the `ff_rankings` outcome; recommend `blocked_for_use`, no intake. |
| **0.85 ≤ ρ < 0.95** | **Weak increment.** Materiality unproven; no intake without a David-ratified use case naming what the increment buys. |
| **ρ < 0.85** | **Genuinely divergent.** The divergence itself becomes the object of study — and divergence is **descriptive**, never an edge, per the standing unvalidated-divergence rule. |

**No threshold moves after the number is seen.** If the result is ambiguous, it is reported as
ambiguous.

## 4. What this cannot decide, stated in advance

1. **It cannot rescue the identity defect.** A favourable ρ would not make the 7.5% wrong-human rate
   acceptable; it is computed on the *cleaned* subset precisely so the two questions stay separate.
2. **It cannot resolve dynasty-vs-redraft.** FantasyCalc is a dynasty trade market; `adp_sleeper-sf`
   is a Superflex *draft* position whose dynasty-vs-seasonal nature is **still unestablished**. A
   low ρ may simply mean "these measure different things", not "we found an edge". **This is the
   most likely confound and it is registered here, before the number exists.**
3. **It cannot authorize anything.** Descriptive only; `decision_supported=False`; no model input,
   no surface, no scheduler.
4. One vintage, one snapshot date. No cadence claim, no stability claim.
