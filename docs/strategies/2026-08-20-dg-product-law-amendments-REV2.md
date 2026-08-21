# Dynasty Genius — Product Law Amendments, REVISION 2

**Date:** 2026-08-20
**Supersedes:** `2026-08-20-dg-product-law-amendments.md` (Revision 1)
**Status:** PROPOSED. Nothing applied.

**Why a revision:** David asked whether the amendments had been given the same rigor as the audit that
produced them. They had not — Revision 1 was written in one pass with no adversarial review, while the
audit beneath it ran ten agents and two challengers. Six adversarial reviews were then run against
Revision 1. **14 FATAL and 30 MAJOR findings.** A1, the centrepiece, is withdrawn.

---

## HEADLINE

A1 does not survive. Its central argument — that the no-verdict law makes decision_supported unreachable — is falsified three separate ways by the repo's own artifacts, and I verified all three; the repeal is withdrawn and only a re-scoped record-keeping half survives. A3, A6 and my bootstrap impact claim were also wrong and are corrected; A4 comes out strongest and now refutes A1. The revised order front-loads the bootstrap fix and the retrospective 937-transaction replay, both of which deliver value now and repeal nothing.

---

# Dynasty Genius — Product Law Amendments, Revision 2

**Date:** 2026-08-20 · **Supersedes:** `docs/strategies/2026-08-20-dg-product-law-amendments.md`
**Basis:** six adversarial reviews, plus my own independent re-verification of every load-bearing claim against the repo.

---

## 0. What changed, in one table

| # | Status | What happened |
|---|---|---|
| **A1** | **WITHDRAWN** | Its causal chain is falsified. Split: a re-scoped record survives as A1a; the repeal (A1b) is withdrawn, not deferred. |
| **A2** | **REVISED** | Survives, re-scoped from one deletion to three dispositions. My "10 of 12" evidence was a bad measurement; corrected. |
| **A3** | **REVISED** | Not incoherent, but under-specified and unsafe as written. Gains three verdicts, a granularity clause, and a split by direction. |
| **A4** | **HOLDS — promoted** | The strongest amendment in the set. It now refutes A1, which is the best evidence it is real. |
| **A5** | **REVISED** | Survives; must keep the market guard armed on the diagnostic lane. |
| **A6** | **WITHDRAWN in its main half** | Two independent footguns found. Only the regex fix survives. |
| **A7** | **REVISED** | Survives, but was aimed at the wrong mechanism. Re-aimed, and unbundled from A2. |
| **Bootstrap** | **REVISED** | The bug is real and the ~80% figure is accurate. My impact claim was false and is withdrawn. |

---

## 1. Three corrections I owe you before anything else

**These are my errors, not the reviewers'.**

**(a) "The no-verdict law makes its own success condition unreachable" — false.** This was A1's engine and it does not run. Verified:

- `backtest_harness.py:295–316` computes G3 market superiority purely from model-vs-market NDCG over *rank predictions*. `backtest_result_WR.json` ships `g3_market_superiority_pass: true`, `overall_grade: ACTIVE_B_VALIDATED`. **Zero recommendations were issued to get there.**
- Your own approved governance defines the route. `2026-08-19-dynasty-genius-master-proposal-3.md`, the `decision_supported` criteria gate, requires "claim-composition tests, power/replication thresholds, examples at every claim level, independent science review." **Not one graded decision.** The decision ledger appears one row down, under *First production DOO workflow* — evidence for a gate **downstream** of `decision_supported`, not upstream. A1 inverted the order the architecture already specifies.
- The chain's real break is at **graded decisions**, not recorded ones. A1's row schema (action · basis receipt · as_of · claim level · interval · counter-argument) has no counterparty, no package received, no executed flag, no alternative taken. Every field describes the *claim*; none describes the *decision*. Graded by the named player's PPG, it is a graded **forecast** — which `realized_outcome_scorer.py` already does, over 501 frozen predictions, with a pre-registration record A1 lacks.

**(b) The vocabulary evidence was mis-measured, and A1's repeal list names rules that do not exist.** The actual `banned_standalone_words` is `["elite", "starter", "depth", "bust"]`. **`buy`, `sell`, `hold`, `cut`, `start`, `target` are not banned anywhere.** A1 proposed repealing a rule that does not exist.

I re-ran the filter with a corpus I did not tune. Result: **5 of 12** honest bear cases suppressed, not 10. The 10/12 figure was an artifact of my test set and I withdraw it. What survives corpus choice, because those six words are simply absent from the list:

> **0 of 17 real verdicts suppressed — including "Sell Puka Nacua," "Strong buy," and "Cut him."**

Live exposure is also zero: across all 12,201 rows of the shipped PVO artifact, the filter produces **0 hits**. It has never fired on real data. It buys none of the safety it is credited with, and it does suppress ordinary analytic vocabulary. Both halves of that are worth saying.

**(c) The bootstrap impact claim was false.** Detail in §3.

Two smaller ones: **CI_WIDTH_MAX is not the *sole* reason QB is PROVISIONAL** — QB fails on two folds (2020, width 0.4048; 2022, width 0.4131), and TE also fails one (2020, 0.3444) yet ships VALIDATED because its failure is cold-start-excused. QB's real disqualifier is **2022, a mature fold the cold-start exception explicitly declines to excuse.** That is a *stronger* argument for the refusal than the one I made. And the straddle ratio is **8x to 758x**, not 10–50x (TE 2022 = 8x; RB 2021 = 758x).

---

## 2. A1 — WITHDRAWN as written

### 2.1 Why the repeal dies

Beyond the falsified chain, four independent failures, each sufficient:

**The selection problem is unsolvable here, and specifically because there is one user.** If A1 is repaired to grade executed decisions, the labelled set is {recommendations David executed}. You execute when you already agree, which correlates with your private out-of-model information — the Week-4 role change A1's own mockup names. The hit rate estimates (model ∧ David's assent), never the model. Declined recommendations are missing *because of* the judgment under evaluation. The leading nonparametric remedy (Lakkaraju et al. contraction) exploits heterogeneity across many decision-makers. **You are one, permanently, by design. Single-user removes the fix, it doesn't shrink the sample.**

**The arithmetic is fatal and I measured it.** From `app/data/league_transactions.db`: completed trades league-wide were 2023=12, 2024=11, 2025=9, 2026=7 — **39 across four seasons, twelve managers.** Roughly 1.6–3.0 trade decisions per manager per season. Detecting a 60% hit rate against a coin at 80% power needs n≈194; 55% needs n≈783. That is 65–261 seasons. `SETTLEMENT_HORIZON_WEEKS = 34` puts the first *settled* grade on an August 2026 call at **January 2028**, not "~Nov 2026" as my mockup claimed. `POWER_FLOOR_MIN_COHORT = 10` puts a usable cohort around **2031**. And the escape hatch is closed: the model cards exclude single-season start/sit, so the only decision class the model is in-scope for is the rarest one.

**A1's only gate is vacuous.** "A recommendation that cannot show its record does not render" is satisfied by my own mockup's text: *"0 graded, 4 pending."* It is a display requirement wearing an evidence requirement's clothes. It can fail only if the ledger plumbing breaks — never because the model is bad. A1 repealed hard prohibitions and installed a gate that cannot bind.

**A1 is refuted by A4, my own principle.** Its restricting half is one cheap edit that lands immediately. Its enabling half — ledger, claim ladder, per-player interval, track-record surface — is months, and A1 explicitly deferred itself to last. This repo's measured base rate for shipping enabling halves is **zero** (`tier_calibration` / `CalibratedTier`: 0 code hits, re-verified). `trade_analyzer.py` already lists `calibrated_uncertainty_by_position` in `REQUIRED_BEFORE_DECISION_GRADE` — the repo has been carrying that IOU for months. **A1 is the amendment A4 exists to stop.** I am not going to exempt my own work from my own rule.

Three further defects, recorded so they don't return: A1's repeal surface is three places wide, not one (`banned_vocabulary.json`, `check-banned-language.mjs`, the linter contract test, the `RecommendedActionBinding.tsx` must-trip fixture, 135 `decision_supported: False` sites and their `Literal[False]` validators, and a hardcoded ban on "recommended" in `test_system_tier_readiness_t1.py:378`). A1's divergence trigger has never been validated — `divergence_validity` is `null` in all four backtests and all four `divergence_ledger_*.json` parse to **0 rows**. And A1 has no positional eligibility rule, so the first thing it would enable is a TE recommendation, against a model card whose shipped text reads `out_of_scope_uses: ["Any trade decision", ...]` while its gate reads `model_status: VALIDATED`.

### 2.2 What genuinely survives, and why it is smaller than I claimed

A1 was right about one thing that nothing else in the repo covers: **grading rankings never measures the selection function** — which players you move, when, at what price. That gap is real.

But it is better closed two other ways, both of which repeal nothing:

- **Retrospectively**, by replaying both lanes against the 39 real trades already in the database (§4, item 5). Already scoped at `MASTER-architecture-and-build-plan.md:550`. ~13x the forward ledger's lifetime sample, gradeable today.
- **Forward**, by measuring a *different estimand*. This is the distinction that makes anything survive.

**A1a — THE RECORD (revised, survives).** Two ledgers, two questions, and the second one dissolves the selection objection because it is not asking about accuracy.

**Ledger A — census, compute-time.** Every eligible player, fixed cadence, whether or not you open the page. Renders nothing. Emission policy pre-registered exactly the way the frozen prediction set is (`policy_id`, thresholds, `declared_by`, `declared_at`), and rows never pool across `policy_id`. **Call it what it is: a second prediction ledger.** It is honest and gradeable, and it adds little the frozen-prediction scorer does not already produce. It is cheap because it is a schema swap on the proven capture-store template.

**Ledger B — the anchoring monitor.** You record your own call and confidence **before** the model's number is revealed. On a randomized ~30% of items the reveal is **withheld entirely**. This is browse-conditioned by design, and that is fine, **because the estimand is not accuracy — it is influence.** How far does the reveal move you, by claim level? That is a within-subject measurement. It needs a random sample of *reveals*, which the withhold arm supplies, not a random sample of players. It reaches usable n in **one season**, not sixty.

This matters because four reviewers independently flagged the same failure mode — anchoring on a stated verb from a model with no measured edge — and Ledger B is the only mechanism in the entire plan **that can detect the product harming you.** If the pre/post delta does not shrink as claim level falls, the claim chip is decorative and the surface should be withdrawn. That is a falsifiable safety instrument, and it is worth building on its own merits.

**Honest scope:** Ledger A cannot reach power this century at your league's trade volume. Ledger B measures influence, not edge. Neither is "the road to `decision_supported`." A1a's real value is **a durable record of what you thought and when, plus a monitor on how much the machine moves you.** That is a much smaller claim than the one I made, and it is the one the evidence supports.

**Build notes for A1a:**
- `DecisionLedgerStore` on the `model_forward_capture_store.py` template — composite PK, `_KEY_COLUMNS`/`_CONTENT_COLUMNS`/`_VOLATILE_COLUMNS` split, `_conflict_check_and_write` raising before any write, shared connection for atomic companion writes. ~250–300 LOC plus tests.
- **Add what the template lacks:** those stores are append-only by Python convention only — `sqlite3 ... "UPDATE ..."` rewrites any of them. A ledger whose purpose is to be evidence about the system's own calls needs `BEFORE UPDATE` / `BEFORE DELETE` triggers that `RAISE(ABORT)` plus a `prev_row_hash` chain. ~40 LOC, and it is the difference between a ledger and a log.
- **The basis receipt already exists** — don't design one. `model_forward_capture_driver.py:446–447` computes `semantic_output_hash` and `provenance_hash` from a lineage subset that deliberately excludes volatile fields. The 5-column key joins natively to 646,936 existing snapshot rows.
- **Record at COMPUTE time, never at display time.** Display-time capture couples recording to rendering, and rendering was gated on a record that only recording produces — a closed loop with no entry point, structurally identical to the defect A1 was written to correct.
- **v1 grades player-for-player decisions only.** `PICK_BASE_VALUES` is a 4-entry static chart self-labelled `score_status: "heuristic"`, and nothing computes started-lineup value. Pick valuation and lineup-slot accounting are named prerequisites, not hidden inside "the track-record surface."

**A1b — THE REPEAL: withdrawn, not deferred.** Re-argue in 2027 from a record that exists, against the `decision-supported-v1` ADR — **which does not exist yet**; I checked. If the record shows an edge, the repeal will be trivial to win. If it doesn't, the law will have done exactly the job it was written for. When it is re-argued it must carry: a quantitative render floor tied to a stated power calculation, positional eligibility keyed to `out_of_scope_uses` rather than `model_status`, a horizon field (the constitution's *Separate Dynasty And Redraft* requires one and my field list omitted it), and claim level as an input to **whether a verb is emitted at all** — not merely to how it is presented.

---

## 3. The bootstrap bug — real, quantified, and far smaller than I said

I reproduced this independently rather than take it on report.

**The defect is real and I can prove it in one line.** Inside `compute_ndcg_diff_bootstrap`, `_diff` passes the **original pool's ranks** into each resample, while `compute_ndcg` rebuilds its IDCG denominator from the **resampled** relevance vector. The DCG mask `ranks <= k` therefore selects a random number of items while IDCG always sums exactly `k`. Numerator and denominator describe two different lists.

My measurement, n=43 / k=12, 3000 resamples:

- **42.3% of replicates produced "NDCG" values above 1.0.** NDCG is bounded in [0,1] by construction. Nearly half the replicates are mathematically impossible.
- Top-k members drawn per replicate: **mean 12.0, sd 3.0, range 2 to 21** — must be exactly 12.

**The ~80% width figure is accurate.** Re-ranking inside the resample, across four fold geometries: **QB 75%, RB 82%, WR 83%, TE 84%** width reduction. Two reviewers got 73–85% and 5.8–9.0x independently. **Point estimates are unchanged** to four decimals — the defect is purely in the resampling.

**"This may move more than every amendment combined" is FALSE, and I withdraw it.** `ndcg_diff_bca_ci95` is **orphaned**. Grepped repo-wide: producer, artifacts, OpenAPI, generated frontend types, and two tests that assert it is *absent*. **No consumer.** G3 counts wins on **point estimates** (`backtest_harness.py:310–315`) and is annotated in the source as *"DISCLOSED only; never gates model_status."* `CI_WIDTH_MAX` reads `spearman_rho_bca_ci95` — a different function, correctly paired, no such defect. Blast radius: **one function, zero gates, zero surfaces.**

**Before you pay for it, know what it buys and what it costs.** After the fix, corrected half-widths are ~0.08–0.12 against point estimates of 0.0008–0.058, so **all 16 folds still straddle zero.** The fix does not create an edge; it proves the absence of one more precisely. And **11 of 16 point estimates are negative** — so the direction of any future significance is more likely *against* the product than for it. RB 2022 (−0.0578) and QB 2020 (−0.0519) are already close to the corrected half-width. **The honest headline after the fix is unchanged: no measured edge over free consensus, and a real chance the next larger measurement shows the model is worse than it.** That is worth knowing two years early, which is why it still goes first.

**Fix:** pass the underlying scores (`pool_pred` / `pool_market`) instead of pre-computed ranks and re-rank inside each resample. Rewrite the docstring, which currently affirms the broken construction as correct — that is what let it survive a prior adversarial review of this exact function. **Add one contract test: every replicate must lie in [−1, 1].** That assertion fails on the current implementation and would have caught this.

---

## 4. The revised order

Derived from the dependency graph and from what delivers value to you soonest, not from the shape of the original document.

**1. Bootstrap fix + `[-1,1]` contract test + regenerate the four trust-surface artifacts.**
One function, ~30 lines. No gate reads it, so it cannot break anything. Corrects a number that is currently 4–8x wrong inside an artifact whose entire purpose is honesty. Highest value per unit of work on the list. Rationale is artifact honesty — not unlocking anything.

**2. A4 + A3-forward.** Zero code, and A4 is load-bearing for what follows.

> **A4 — HOLDS, promoted.** No amendment lands its restricting half without its enabling half. `tier_calibration` re-verified at 0 hits; that prohibition stays suspended. **Add the mirror obligation:** *a repeal ships with re-ratification of every gate that cited it.* `no_directive_copy` is a **non-optional** gate component on five surfaces you personally ratified (2026-07-02 / 2026-07-04) citing `check-banned-language.mjs` and `scan_league_opportunity_no_verdict.py`. Nothing may repeal those without a structural replacement component and your dated re-ratification. That is the exact class of quiet governance drift this whole set exists to stop, and my A1 was about to commit it.
>
> **One work item, three claimants.** A per-player predictive interval does not exist anywhere — only fold-level and cohort-level uncertainty; `xvar` is a variance proxy, not a calibrated CI. A1 mandated one, A4's suspended prohibition needs one, and `REQUIRED_BEFORE_DECISION_GRADE` already lists `calibrated_uncertainty_by_position`. **Three things want one build** (conformal prediction or quantile regression over Engine B residuals). Build it once, or stop pretending any of the three is close.

> **A3 — REVISED.** It failed its own test: no automated check can read a rule and judge whether its justification sentence is true, so its mechanism was a human reading prose — a language inspection, which A2 repeals. Fixes: **(i)** state A3's own sentence, with a structural mechanism — *every rule in the enumerated corpus carries a recorded verdict in one docket file; no rule ships without one*. **(ii)** Three verdicts, not one — **KEEP** / **ENFORCE** (danger named, mechanism absent or unwired) / **REPEAL** — plus a **LIVE/DORMANT** status. The audit's own heading was "enforce or delete"; I collapsed it to delete. **(iii)** Granularity clause: the unit is the smallest thing that can independently fire. **(iv)** Numeric thresholds carry a fourth element — where the number came from. `CI_WIDTH_MAX = 0.30`'s provenance is *"three-way cockpit consensus"*: KEEP-with-a-note, not a derived bound, and A3 as written erased that distinction. **(v)** Well-formed ≠ desirable — passing A3 never establishes that a rule should exist. **(vi)** **Strike "ANY RULE THAT CANNOT IS REPEALED."** Self-executing mass repeal over a 127-rule corpus, landing *first*, would have silently deleted "Counter-Argument Required" and "Uncertainty Required" — both mechanism-free, both your ratified constitutional text, both prerequisites of A1. It would also have protected the morning-tape 503 that A1b must repeal. **Split by direction:** A3-forward lands now; A3-retroactive goes last.
>
> Routed to **ENFORCE**, not repeal: the pre-commit CSV guard (correct rule, present only in `.pre-commit-config.yaml`, absent from CI, no hook installed); `leakage_clean` (a hard floor fed a literal `True` at every call site — `None` in all four shipped artifacts, so it cannot fire; wire it from the `validate_no_temporal_leakage` calls the harness already makes). Routed to **DORMANT-KEEP**: the `null_coverage >= 0.90` floor, structurally 1.0 today because the harness imputes rather than drops rows — correct wiring, activates the moment feature work introduces row drops.

**3. A7, re-aimed and unbundled from A2.**

> **A7 — REVISED.** My premise was wrong: the vocabulary filter is **not** silent — it emits `evidence_suppressed_banned_term`. It suppresses honest content *and discloses that it did*. The genuine silent replacement is `league_pulse_models.py:55–60`: an unknown rationale token maps to `_FALLBACK_LABEL = "opportunity_signal"` **with no caveat at all**. That is the whole real cost of A7 — about five lines — and it is independent of A2.

**4. A2, re-scoped to three dispositions.**

> **A2 — REVISED.** Not one deletion; three. **REPEAL** the two denylist filters (`players.py:174–189`, `roster_audit_models.py:115–123`) and their four contract assertions. **KEEP** `league_pulse.validate_tokens` — it is an **allowlist over structural token identity**, precisely what A2 asks for. **KEEP** `validate_surface3_regen_integrity.py:145–157` — the build-time loud check A7 wants. And **write A2's scope boundary into A2**: it governs natural-language output rendered to David; it does **not** govern governance prose (or it repeals A3) and it does **not** govern machine-generated identifiers — otherwise it repeals `engine_b_contract`'s temporal-leakage name scanner, the single highest-consequence guard in the repo, called at eight production sites. That scanner's honest sentence is narrower than its reputation: *it catches leakage that announces itself in a column name, and cannot catch a T+1 value stored in a column named `snap_share`.* Blocked on the A4-mirror re-ratification in step 2.

**5. The retrospective decision ledger — replay the 39 trades.**
Pin both lanes on the date of each transaction and replay forward. Already scoped at `MASTER-architecture-and-build-plan.md:550`, which calls this class of value *"the strongest thing shippable this month."* **Zero repeals, zero new data, no realized outcomes needed, and it measures the selection function — the exact gap A1 correctly identified — at ~13x the forward ledger's lifetime sample, today.** Player-for-player trades first; check what fraction of the 39 involve picks before scoping further. This is the item I should have led with.

**6. A1a — Ledger A + Ledger B (§2.2).** Records at compute time, renders nothing, repeals nothing. Nothing to explain except "the clock started on date X."

**7. A5, with the market guard left armed.**

> **A5 — REVISED.** Survives. Mechanical blocker is two edits (`feature_assembly.py:110` silently reindexes to `ENGINE_B_OUTPUT_COLUMNS`; the contract test asserts exact column equality). **Non-negotiable:** `validate_no_prohibited_features` stays armed on the diagnostic lane, market half included.

**8. A6, reduced to the regex fix.**

> **A6 — MAIN HALF WITHDRAWN.** Two footguns, either fatal. **(i)** A6 + A5 together remove the only runtime guard keeping market columns out of the assembled training CSV, at the exact moment A5 opens a lane into it. The closed-world intersection argument covers the **X matrix**; `validate_no_prohibited_features` protects the **assembled CSV that feeds it**, at four call sites. By my own A4, A6 is a permission shipping with no replacement guard. **(ii)** By keyword match A6 would also delete `head_b_contract.MARKET_PROHIBITED_COLUMNS` — half of whose members (`nfl_yards`, `nfl_tds`, `nfl_targets`, `nfl_carries`, `nfl_receptions`, `nfl_air_yards`, `nfl_yprr`) are NFL production columns banned from a **pre-NFL prospect head**: a temporal-leakage guard wearing a market label, enforced on a hand-edited spec dict, not a closed-world intersection. Measuring the intersection at `[]` proves the guard **has been holding**, not that it cannot fire.
>
> What survives: **fix the regex** that blocks `value_over_replacement` / `market_share_yds` while passing `sleeper_adp` / `fantasycalc_value`. Rename head_b's list to `HEAD_B_POST_NFL_PROHIBITED_COLUMNS` so no future reader repeals it by keyword. Do **not** touch `engine_a_contract.PROHIBITED_COLUMNS` — it is live in `manual_export_adapter.py:31`. Note `check_leakage` has no production caller (test-only). After this scoping A6's residual value is small; treat it as cleanup, not an amendment.

**9. A3-retroactive** — the docket sweep, after the replacement mechanisms exist.

**10. A1b** — not scheduled.

---

## 5. What this costs you, stated plainly

You asked for the plan producing the strongest product with the greatest value **to you**. Three things follow from that framing that I did not say the first time.

**The product will not say "sell" in 2026, and that is now an evidence-based decision rather than a rule I was arguing around.** The measured position is not "we lose to free consensus" — it is *"we carry no measurable information beyond `dynastyprocess_ecr_2qb`, a free source this repo already ingests."* A recommendation surface built on that would be grading consensus with extra steps and charging you the anchoring cost for it. If you want a recommendation surface in 2027, the honest version shows **both calls side by side** — which also hands the ledger a matched control arm for free.

**Silence is not the absence of a decision — it is the default of holding, and holding is currently optimal.** In a market where your best measurement says you are indistinguishable from free consensus, every additional trade is variance against a counterparty pricing off the same source. You trade ~2x/season. A surface that pushes that to six would quadruple your exposure to a zero-edge process. A1 never priced what it costs to displace the default, and it should have.

**Steps 1 and 5 both ship value with zero repeals and zero new law.** That is the real finding. The plan's value was never concentrated in the repeal — it was in a bootstrap fix I mis-sold and a retrospective replay I did not mention. The reviews did not weaken the plan; they relocated it.

