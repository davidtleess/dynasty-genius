# BUILD-4 — qb_v3_candidate Promotion Decision Record

**Date:** 2026-07-04 · **Author:** Claude (implementation lead), on the three-way cockpit blueprint
**Decision owner:** David (this record prepares the decision; only the ratification line below makes it)
**Evidence:** `docs/validation/build4_qb_v3_validation_evidence_v1.json` (point-in-time snapshot; metadata + source-drift caveat inside)
**Machinery:** ratified spec `docs/superpowers/specs/2026-07-03-build4-superflex-qb-design.md` (`df64699`) · T1 `c8abba3` · T2 `450e41d` · T3 `896927f` · T4 `0c304f2` — all cockpit-TDD, dual-CLEARed, zero-divergence-audited.

---

## 1. Decision

**`qb_v3_candidate` is NOT PROMOTED.** It remains a research-only descriptive artifact. No Engine A/B active artifact changed; no serving, PVO, or UI integration exists; `decision_supported=false` everywhere this candidate's output appears. A future promotion attempt is a new, separately David-gated validation cycle against the same pre-registered gates.

**Ratification: ratified_date: 2026-07-04** *(David ratified this record and the fork-A disposition above on 2026-07-04.)*

## 2. What the pre-registered gates said (the evidence)

Walk-forward validation (expanding-window folds, test years 2020–2023; logistic-regression baseline family; per-fold train-only preprocessing; baseline = train-fold prevalence; run `random_state=20260703`, `n_bootstrap=500`):

| Horizon | Structural folds | Evaluable | Verdict | Reason |
|---|---|---|---|---|
| 1y | 4 | 1 | not eligible | 3 of 4 folds excluded `low_sample_qb_holdout` — the fold-starvation the spec's pressure test predicted (Codex F5), observed exactly |
| 2y | 4 | 3 | not eligible | BCa CI lower bounds not above zero (Brier and AUC gates) |
| 3y | 3 | 3 | not eligible | BCa CI lower bounds not above zero |

Per-fold detail (all in the evidence JSON): average Brier improvement over the train-fold prevalence baseline +0.050 / +0.015 / +0.004 by horizon — positive but **never statistically separable from zero** at ~32–36 QBs per fold. Discrimination is real: AUC 0.67–0.78, top-12 precision 0.75–1.00. In plain terms: **the model orders startable QBs well; it cannot prove its probabilities are better-calibrated than the base rate at this sample size.** The gates therefore hold. "Passes on the subset with enough data" was excluded as a promotion argument in advance, and no threshold was tuned after seeing results.

## 3. Disposition — how this candidate may and may not be used

- **Allowed (descriptive):** relative ordinal ordering of QBs *within a cohort or draft class* — the discrimination evidence supports comparing peers. Every rendered probability carries the `uncalibrated_probability` and `not_promoted_candidate` caveats with the cohort prior displayed alongside (T4 packaging enforces this by construction).
- **Prohibited:** absolute survival probabilities as load-bearing inputs anywhere — trade calculators, value-at-risk, pick-for-veteran math. The calibration gate failed; the absolute numbers are not trustworthy.
- **The baseline default:** for roster/trade thinking, the cohort-prior table (§4) is the honest anchor — itself descriptive (`decision_supported=false`), like everything else in this record. Nothing here is decision-grade.
- Abstentions stand: Day-3 rookies, undrafted rookies, small-sample QBs, and missing-draft-metadata rows receive no model number — reason and base rate only.

## 4. The real cohort-prior table (evidence context, NOT a prior update)

Computed from the regenerated 2018–2023 label table (population: **labeled QB feature-seasons in NFL years 1–3 that met the games≥4 feature floor** — i.e., young QBs *who played*; this conditions on opportunity and is therefore NOT the same population as the T4 rookie-filter v1 priors, which address a draft class before anyone plays):

| Capital band | H1 n / rate | H2 n / rate | H3 n / rate |
|---|---|---|---|
| Round 1 (picks 1–32) | 56 / **0.911** | 56 / 0.804 | 48 / 0.750 |
| Picks 33–64 | 7 / 0.714 | 7 / 0.429 | 6 / 0.500 |
| Day 3 (65+) | 18 / 0.500 | 18 / 0.111 | 12 / 0.333 |
| Undrafted | 6 / 0.000 | 6 / 0.167 | 5 / 0.000 |

Read honestly: first-round capital + actual playing time is a ~90% one-year startable-survival signal (organizational patience is even stronger than assumed); every other band is small-n and noisy (the Day-3 non-monotonicity is noise, not signal). **This table does not replace the registered T4 filter v1 priors (0.63/0.15/0.05)** — those cover the unconditioned draft-class population. The gap between them is a named observation: any prior recalibration is a separate David-gated ticket, not a silent edit.

## 5. Accrual path — power to test, never a promise to promote

More seasons do not promote this model; they **reopen the window for a properly powered test**:
- Each completed NFL season adds one structural fold per horizon (H1 gains test-2024 when 2025 outcomes finalize; H3 gains test-2023 only when 2026 outcomes exist) and ~40–60 labeled QB rows.
- H1's specific blocker is fold starvation under the small-n gates (<30 rows / <10 minority per fold): larger per-fold cohorts as seasons accrue address the denominator directly.
- Shrinking BCa intervals cut both ways: **if a real calibration edge exists, the CIs eventually clear zero; if they still span zero at larger n, that is evidence the edge does not exist, and the candidate stays rejected.** The gates themselves (baseline definition, CI requirement, structural-fold eligibility, no-survivorship rule) are pinned in the ratified spec and are not tunable in response to results.

## 6. Superflex strategy note (for David reading this cold in ~2027)

The empirical table is the durable takeaway: **top-64 — especially round-1 — draft capital buys a large, market-wide organizational-patience window in years 1–3; Day-3 and undrafted QBs have no such insulation.** Strategy HYPOTHESES for David to weigh manually — never directives, and not model outputs: the insulation window is where young-QB acquisition risk is lowest (capital is the signal, not preseason hype); Day-3/UDFA developmental QB stashes carry low survival bands and plausibly drain roster capacity; proven second-contract starters are one candidate consolidation target for surplus mid/late firsts. The model above earned no decision authority, and neither does this note.

## 7. Reproduction and verification

- Evidence reproducibly generated by the committed script `.venv/bin/python3.14 scripts/assemble_qb_v3_validation_evidence.py` (also cited in `evidence_metadata.generation_command`): the T3 validation run + the cohort table (registered pick bands over the regenerated label table, NFL-years-1–3 window, games≥4-conditioned).
- Focused suites at authoring: T1 16 · T2 14 · T3 14 · T4 22 — all green; full suite 2878+/0 at the T4 commit.
- Source-drift caveat: nflreadpy data (2025 season especially) may shift after generation; the evidence JSON is a snapshot and says so in its metadata. Regeneration at a later date may differ and does not retroactively alter this record.
