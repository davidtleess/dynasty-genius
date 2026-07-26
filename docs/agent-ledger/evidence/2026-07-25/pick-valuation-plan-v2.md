# Pick Valuation — Plan + Benchmark Design **v2**

Supersedes v1 (`6992673432945f8b693eb8e65744f9853e4aebf903b701814fb3e6d315709994`).
Author: Claude Code (implementing lane). Reviewer: Codex (independent technical).
Status: **pre-fit.** No candidate has been fitted. No curve, artifact, or producer has been changed.

v2 dispositions all ten Codex residuals, folds in Gemini's telemetry (independently re-verified
by me), and records **three errors of my own** — two found by Codex, one found by the data.

---

## §0 What changed from v1, in one place

**Three load-bearing v1 claims are WITHDRAWN:**

1. **"Realized xVAR is an Engine B quantity"** — false. It is built from **Engine A** constants.
2. **"n=8 → ~15 mature years cuts SEs ~30%"** — impossible. The on-disk ceiling is **n=9**.
3. **"The null means v1's coarseness stands"** — this privileged the incumbent and contradicted
   my own standard A6. The null now selects the *simplest construction shown non-inferior*.

**One v1 framing is corrected throughout:** the estimation unit is **not** a dynasty rookie-pick
slot. It is the **ordinal of the Nth skill player in NFL draft order**. Everything downstream is
renamed and re-scoped accordingly.

---

## §1 The estimand, named honestly (Codex #1 — ACCEPTED, and it is worse than stated)

**What the data actually indexes.** `scripts/build_draft_pick_value_curve.py:2-7` says it in its
own docstring: the board is built via the *"first-36-skill-players-in-NFL-draft-order = FF rookie
board" bridge*. `build_slot_curve` (`:50-73`) takes each draft class, filters to QB/RB/WR/TE,
sorts by NFL `pick`, takes `head(36)`, and assigns slots by `enumerate(rows, start=1)`.

**Therefore "slot 13" means the 13th skill player the NFL drafted — not rookie pick 2.01, and not
the player a superflex manager would have taken at 2.01.**

**The strengthening Codex did not name, which I verified:** the one mechanism in the code built to
bridge toward superflex reality is **switched off**. `_SF_QB_PROMOTE_SLOTS = 0`, commented
"SF-QB knob off in v1 (manual calibration deferred)" (`build_draft_pick_value_curve.py:34`), so the
`_adjusted_order` QB-promotion path (`draft_pick_valuation.py:68-80`) never executes. In a
**Superflex** league — where QBs are drafted far earlier than NFL order implies — the proxy is
weakest **exactly where David's league differs most from the NFL**. `01-north-star-architecture`
makes league context a first-class input; this curve is currently blind to it.

**Disposition.** Option (a) — obtain historical SF rookie-draft/ADP slot observations — is
**unavailable**: the FantasyCalc cache is current-state only and forward capture began in 2026, so
no historical rookie-slot archive exists on disk. This is the same unobtainable-archive wall the
W1 thread hit. **So v2 takes option (b):**

- Rename the unit `nfl_skill_ordinal` in every artifact, metric, and surface. "Slot" is retired.
- Register the **NFL-order → SF-rookie-slot bridge as a named, unvalidated, uncorrected source of
  error**, carried as a caveat on every emitted value.
- **The SF-QB knob becomes a registered candidate construction** (§5, Candidate D), because
  turning it on is a testable change rather than a hand-tune.
- **No output may claim to have measured dynasty pick value.** It measures NFL-order skill-ordinal
  payoff, which is a *proxy* for it.
- The market wall (§4) forbids validating the bridge by vendor proximity.

---

## §2 Pre-registered falsifiers — FROZEN by this document's SHA before any candidate is fit

Unchanged in intent from v1; tightened per Codex #6 and #7 so they cannot be won by noise.

**F1 — Out-of-sample loss.** A candidate must beat the fold-reconstructed incumbent (§3.1) on the
primary metric by at least the practical margin (§3.3), under paired year-level uncertainty.
**F2 — Stratified honesty.** It must not regress beyond the margin on **any** ordinal stratum
(1–12, 13–24, 25–36). Pooled improvement that hides a first-round regression is a failure.
**F3 — Calibration.** No systematic signed bias by stratum, tested at the registered level.
**F4 — Stability.** Leave-one-year-out refits must not swing a stratum mean by more than the
registered tolerance.
**F5 — Provenance.** Every constant, formula, seed, and cohort rule is versioned in the evaluation
artifact, or the run is void.
**F6 — Market wall intact.** No fit, selection, tie-break, or cohort decision touches vendor data
(§4).

### §2.1 The null I must be able to accept — **CORRECTED** (Codex #6)

v1 said: *if no candidate clears, v1's coarseness stands.* **That was wrong** — it made the
incumbent win by default, contradicting my own A6 ("no constant survives because it is already
there"). Codex is right and the correction is:

> **If no candidate is shown superior under §3.3, the selected construction is the SIMPLEST one
> shown NON-INFERIOR — which may be a flat curve, a round-mean curve, or v1. v1 has no default
> claim on the outcome. "No powered distinction" is evidence of nothing, and is never evidence
> that v1 won.**

### §2.2 Pre-registered expectation (stated *before* the result, per David's standard)

Given §5's n=9 ceiling and v1's measured dispersion (MAD/|mean| ≈ 1.86), **I expect this study to
be underpowered for fine ordinal resolution.** The most likely honest outcome is "no candidate
clears the margin → ship the simplest non-inferior construction and publish the limit." I am
recording that expectation now so that a null result cannot later be reframed as a disappointment
to be engineered around, and so that a *positive* result faces the suspicion it deserves.

### §2.3 The incumbent has no privilege

v1 is a comparator, not a baseline-of-record. It enters every comparison reconstructed inside the
training fold (§3.1), never as the shipped artifact.

---

## §3 Benchmark design

### §3.1 The incumbent comparator — leakage fixed (Codex #2 — ACCEPTED)

v1 said "the shipped artifact, exactly as it prices today" while also specifying 7-year LOYO folds.
Those are contradictory: the shipped artifact was built once over **all** of 2015–2022
(`build_draft_pick_value_curve.py:30-32`), so comparing fold-trained candidates against it hands
the incumbent every held-out year.

**Corrected.** Inside each training fold, the **complete v1 procedure is reconstructed** from the
fold's years only: option-value floor at 0 → per-ordinal `fmean` of floored payoffs → running-min
monotone clamp → median tier rollup. The shipped artifact is reported **separately and only** as a
deployment snapshot, never as the OOS comparator.

### §3.2 Comparators (all fold-reconstructed)

Flat (single global mean) · Round-mean · v1-reconstructed · each §5 candidate. Flat and round-mean
are not strawmen — under §2.1 either may legitimately win.

### §3.3 Metrics and the decision rule — frozen (Codex #6, #7)

- **Primary loss:** RMSE on held-out-year realized payoff, reported **pooled and per stratum**
  (1–12 / 13–24 / 25–36), with **paired year-level deltas** (candidate − comparator, one pair per
  held-out year, n=9 pairs) as the inferential unit. Per-ordinal RMSE built from one observation
  per fold is **retired** — it is noise, not a metric.
- **Practical margin:** a candidate must beat the comparator by ≥ the registered margin in paired
  mean delta with a one-sided interval excluding zero at the registered level. Numerically lower
  RMSE alone is **not** a pass.
- **Multiplicity:** candidate count is fixed in §5 before fitting; family-wise control is applied
  across candidates for the primary gate.
- **Gate order and conjunction:** F1 → F2 → F3 → F4, all required, evaluated in that order.
- **"Effective resolution" is DEMOTED** (Codex #7). It was my own invention and I trusted it least;
  Codex is right that it was undefined and gameable. It is no longer a gate. It survives only as a
  **diagnostic**, defined as: the number of adjacent ordinal pairs whose held-out payoff intervals
  are simultaneously separated by at least the registered minimum practical xVAR difference.
- **Monotonicity-violation count is NOT a discriminating metric** and is removed as a gate: every
  candidate is monotone by construction (§6), so it is zero by construction for all of them.
- **Spearman against a single held-out year is removed** as a primary — with an imposed monotone
  order it largely re-tests that imposition, and ties alone can move it.

### §3.4 Protocol freeze (Codex #3 — ACCEPTED)

Before any fit: exact functional forms, parameter counts, weight estimation (train-fold only),
hyperparameter grids, optimizer and convergence criteria, **explicit seeds**, failure handling, and
a deterministic selection/tie rule are all written into §5 and frozen by this document's SHA.
**Given n=9, selection among candidates on the same nine LOYO scores is not promotion-grade.**
This comparison is therefore registered as **EXPLORATORY**: its output may inform a construction
choice and must not be presented as a validated model promotion. Promotion would require either a
genuinely untouched temporal evaluation set or a materially larger cohort — neither exists today.

---

## §4 The market wall

Benchmark against the vendor; **never fit, select, tie-break, or choose a cohort by it.** "Agrees
with the market" appears in no success criterion. Indirect leaks are in scope: no metric chosen for
its correlation with vendor agreement, and no era/sample choice justified by market comparability.
Per §1, vendor proximity **cannot** validate the NFL-order bridge.

---

## §5 Sample — **§5.0's PREMISE IS FALSIFIED** (Codex #8, superseded by data)

v1 ranked "extend `mature_years`" **first**, ahead of all estimator work, on the claim that
n=8 → ~15 would cut SEs ~30%. **That claim is dead.** Telemetry from Gemini, independently
re-verified by me against `app/data/training/prospects_with_outcomes.csv`:

| Fact | Value |
|---|---|
| Earliest `season` on disk (all five training CSVs) | **2015** |
| Latest `season` on disk | 2025 |
| Pre-2015 draft classes anywhere on disk | **none** |
| True NaNs in `y24_ppg` (pre-`fillna`) | **0** |
| 2023 board (first 36 skill) | 36 rows, **35 positive**, 1 zero → **mature** |
| 2024 / 2025 boards | 36 rows, **0 positive, 36 zero** → immature (Y3 unplayed) |
| `_MATURE_YEARS` in the producer | 2015–2022 (**n=8**) |

**Consequence.** The last mature class is **2023**, and it is currently excluded. The honest
extension is therefore **n=8 → n=9**, a single year: `sqrt(8/9) = 0.943`, i.e. **≈5.7% SE
reduction — not 30%.** §5.0's ranking above all estimator work **collapses**, and this is my error,
not Codex's finding and not Gemini's: I asserted a sample I never checked existed.

**Revised §5.0.** Adding 2023 is still worth doing — it is free, it is a real year, and it is the
most recent one — but it is a **housekeeping step, not a strategy.** It is no longer ranked first
and it does not rescue power.

**Cohort-admission rule, frozen before results (Codex #8).** 2023 is admitted only if it satisfies:
identical Y2+Y3 observation horizon; complete 36-row skill board; same scoring and source version;
no `fillna(0)`-substituted outcomes. A calendar-time sensitivity (2015–2022 vs 2015–2023) is
reported either way. Effective n and design effect are reported. **No cohort decision may be made
after seeing candidate behavior.**

### §5.1 Candidates — frozen set

- **A — Isotonic / PAVA** on ordinal means; weights = per-ordinal count (train-fold only); no free
  hyperparameters; deterministic.
- **B — Monotone parametric decay**, exponential form, **2 parameters**, floor as registered in
  §5.2; fitted by least squares on train-fold ordinal means; seed irrelevant (deterministic);
  convergence tolerance registered.
- **C — Hierarchical shrinkage** toward the round mean; shrinkage strength selected **within the
  training fold only** by nested LOYO; prior and grid registered.
- **D — v1 procedure with the SF-QB knob ON** (`_SF_QB_PROMOTE_SLOTS > 0`), per §1. This tests the
  bridge's one built-in superflex correction as a construction rather than a hand-tune.

### §5.2 The zero floor must earn its place (Codex #5 — ACCEPTED)

v1 forced every candidate to share the floor and retained it "as judgment" — making it impossible
to falsify, in direct contradiction of A6. The implementation confirms raw xVAR is intentionally
allowed negative (`draft_pick_valuation.py:39-48`) and only clamped later (`:139-145`).

**Corrected.** Floored and unfloored outcome constructions are **both registered** and run as a
sensitivity. They are different estimands — *gross roster payoff* (floored: a bust costs you
nothing beyond the pick) versus *replacement-relative asset value* (unfloored: a bust costs you the
opportunity). **Which one David needs is a product question, surfaced to him, not settled by me.**
The floor does not survive on incumbency.

**Missingness audit (Codex #4, second half) — verified and nuanced.** The producer coerces
non-numeric/missing `y24_ppg` to `0.0` (`build_draft_pick_value_curve.py:53`). I verified the
current CSV has **zero true NaNs**, so that `fillna` is **inert on today's data** — but the
consequence is worse, not better: the missing-versus-realized-zero conflation is **already baked
into the CSV upstream** and is invisible at the producer. A realized 0.0 and an unrecorded outcome
are indistinguishable on disk. Any cohort extension must resolve this before admission.

---

## §6 The monotone prior is imposed, and its rationale is corrected (Codex #9 — ACCEPTED)

Monotonicity is an **imposed football prior, not a data finding** — the raw ordinal means violate
it in 15 of 35 adjacent pairs.

v1 justified it by "organisational commitment and opportunity" citing draft capital. **That is the
wrong mechanism**: the draft-capital doctrine in `00-product-constitution` describes an *NFL team's*
investment in a player, not a *fantasy manager's* pick position. Codex is right.

**Corrected rationale — choice-set dominance:** the holder of an earlier rookie pick can select any
player still available to a later pick, so under the same information and rational exercise, the
earlier pick's option set weakly dominates. That is an economic argument about the manager's choice
set, and it stands independently of the NFL-order proxy — the two must not be conflated.

---

## §7 Honest limits, carried on the surface

1. **The unit is not a dynasty pick slot** (§1) — it is NFL skill-draft ordinal; the bridge to a
   superflex rookie slot is unvalidated and its one built-in correction is currently off.
2. **Lineage — CORRECTED.** Values derive from **Engine A** constants (`ENGINE_A_P90_PPG`,
   `ENGINE_A_REPLACEMENT_DVS`, `XVAR_LAMBDA_ENGINE_A`, imported at `draft_pick_valuation.py:19-23`
   and applied at `:39-48`) plus the pinned y24-PPG construction and the §1 bridge. **My v1 claim
   that this inherits Engine *B* error is withdrawn.**
3. **n=9 at best**, one observation per ordinal per year; MAD/|mean| ≈ 1.86 — dispersion nearly
   twice the signal.
4. **Only 21 of 36 ordinals carry resolution** in the shipped artifact; rounds 2 and 3 collapse to
   an identical clamped value by construction.
5. **Exploratory, not promotion-grade** (§3.4).
6. Missing and realized-zero outcomes are indistinguishable upstream (§5.2).

---

## §8 Track sequencing (Track 2 contract — Codex #10 — ACCEPTED)

**Track 1** (P2 2027-bounded bucket resolver; P4 payload/display contract + the fixture that hides
it) is independent of the curve and proceeds first; its surface work routes through a cockpit
framing pass with the design foundation loaded, per 02's material-visual-direction rule.

**Track 2** (projected-finish values) outputs a **range, not a point** — a projected finish is a
scenario, not a measurement. v1 left "plausible finishes" undefined, which Codex correctly notes
lets an arbitrary range evade falsification or smuggle false precision. **Frozen now:** scenario-set
membership rule; coverage semantics (**scenario envelope**, explicitly *not* a probabilistic
interval); endpoint derivation; stale/missing behavior (report unavailable, never interpolate);
and whether labelled scenario members are shown. **Track 2 may define this contract now; its
numerical materialization depends on the curve state it consumes — that dependency is real and is
why the contract, not the numbers, is the Track-2 deliverable at this stage.**

**Track 3** is the curve refit under model-change governance — human-gated promotion, pre-registered
validation, never in-season auto-adjustment.

---

## §9 Gates

Every commit and every push remain David's. No candidate is fitted before this document's SHA is
recorded and Codex has reviewed v2. Promotion of any curve is a model change under
`00-product-constitution` → human-gated, pre-registered. All output stays descriptive
(`decision_supported=False`); no pick value is a recommendation.

---

## §10 Routing

v2 → Codex for adversarial review against the ten residuals and this document's new frozen SHA.
Gemini's telemetry is folded in as **facts, independently re-verified by me** (§5); its report was
accurate on every count I checked, and I drew the n=9 consequence it did not state.

**My errors recorded in this document (§Falsification #6):** the Engine-B lineage claim (§7.2), the
n≈15 sample claim (§5), and the incumbent-privileging null (§2.1). Two were caught by Codex's
review; the third by the data I should have checked before writing v1.
