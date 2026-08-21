# Dynasty Genius — Inter-Layer Seam Specification v1 (DRAFT — DO NOT BUILD ON YET)

**Date:** 2026-08-20
**Status:** ⚠ **THREE CONFIRMED BREAKS.** This spec is the output of a design pass whose final phase
was three independent adversaries instructed to break it. All three succeeded. The spec below is
sound in most of its surface and *wrong in three specific places that are named in §BREAKS*.

**Do not start per-layer design against this document until the three breaks are resolved.**
The breaks are recorded here rather than quietly patched, because each one changes a decision.

**How it was produced:** six parallel analyses (kernel value types · closed vocabularies · boundary
inventory · extraction layer · extensibility stress-test · reconciliation with existing code), one
max-effort synthesis, then three adversarial break attempts. 10 agents, ~1.37M tokens, zero errors.

---

## BREAKS — read these first

### BREAK 1 — verdict: SEAM_BREAKS

**Attack:** Attack the OPEN/CLOSED split by forcing a new value into a closed vocabulary. Two hits. PRIMARY: `Lane` (CLOSED, 4 values) is asked to carry two orthogonal jobs — provenance ("whose belief") and admissibility ("may this value enter this spec") — and §8 explicitly retires the repo's five shipped admissibility guards in favor of it. R5 simultaneously deletes the period axis from column names, which is the *only* substrate those guards match on. The combination silently destroys temporal-leakage enforcement, and the claim lattice then rewards the leak with a higher ClaimLevel. Adding a fifth lane does not fix it. SECONDARY: `RefusalReason` (CLOSED, 5 values) is a WHY vocabulary and violates the spec's own §0 corollary; two realistic near-term events each force a new member.

# PRIMARY BREAK — Lane cannot carry admissibility, and R5 removes the only thing that could

## What the spec commits to

§8: *"Delete `LEAKAGE_REGEX` and name-based `PROHIBITED_COLUMNS` — but only after the lane type is load-bearing. Leakage must be enforced by the lane type parameter, which cannot be evaded by renaming."*

R5 / B3: the root cause of the feature seam is *"the period axis lives in column names"*; the fix moves it into data — `(entity_id, period, feature_id, value, observed_at, origin_ref)`.

These two commitments are individually defensible and jointly fatal.

## The measured ground truth

There are **five** distinct admissibility guards shipping today, not one. I read all of them.

| Guard | Location | What it bans | Lane-expressible? |
|---|---|---|---|
| Market leakage | `src/dynasty_genius/models/engine_a_contract.py:71` — `LEAKAGE_REGEX = r"^ktc_\|^adp\|_rank$\|^expert\|^market_\|^value_\|^consensus"` | KTC/ADP/consensus | **YES** — this is the one case §8 is right about |
| **Temporal leakage** | `src/dynasty_genius/models/engine_b_contract.py:269-296` — `_LEAKAGE_PATTERNS = [r"_t\+?\d", r"_next", r"^future_", r"_future"]` + exact membership in `OUTCOME_SEASON_COLUMNS = {"ppg_t1","ppg_t2","games_t1","games_t2"}` (`:16`) | future-season data | **NO** |
| Cross-engine | `engine_b_contract.py:250-259` — `ENGINE_A_PROHIBITED_IN_B` = 16 columns (`dominator_rating`, `completion_pct`, `pick`, `round`, `breakout_age`, `speed_score`, …) | Engine A pre-NFL features, banned in Engine B | **NO** |
| Cross-head | `src/dynasty_genius/models/head_b_contract.py:77-83` — `MARKET_PROHIBITED_COLUMNS` also contains `nfl_yards, nfl_tds, nfl_targets, nfl_carries, nfl_receptions, nfl_air_yards, nfl_yprr` | NFL production, banned in Head B | **NO** |
| Cohort | `src/dynasty_genius/features/qb_rookie_risk_filter.py:26` — `ALLOWED_INPUT_COLUMNS = ("player_id","position","draft_number","age_at_entry")`, exact-set | any NFL-usage column | **NO** |

Note the third and fourth rows are **mutually inverse over the same lane**: `ENGINE_A_PROHIBITED_IN_B` bans college production *from* Engine B while requiring it in Engine A; `head_b_contract`'s `nfl_*` block bans NFL production *from* Head B while `yprr` and `air_yards_share` are legal Engine B features (columns 15 and 12 of `app/data/training/engine_b_features_v2.csv`). The identical measurement — same origin, same unit, same `Lane` under any assignment you choose — is required in one spec and a defect in another. Admissibility is a property of the **(TrainingSpec, cohort)** pair, not of the value. A four-member closed vocabulary attached to `FeatureDefinition` cannot express a relation whose arity is two.

Also worth noting for its own sake: `nfl_yards`/`nfl_targets`/`nfl_yprr` are filed under a constant named `MARKET_PROHIBITED_COLUMNS` and nothing about them is market. Lane-tagging that file will classify them `Outcome`, and the ban vanishes.

## The forcing change, and why it is silent

The near-term change is one David has already scoped: **raise lag depth past 2, or ship the sequence model.** The spec's own census — 959 players, 60 with 7 seasons of which 5 are structurally invisible — is the argument for doing it.

Under R5 that is `TrainingSpec.lag_depth = 3` (or `"full_history"`), and `FeatureVintage.as_tabular(spec)` / `as_sequence(spec)` derive the periods. Now trace the guard:

- `validate_no_temporal_leakage` is called at **six live sites**: `features/feature_validation.py:108`, `eval/backtest_harness.py:473`, `scripts/assemble_engine_b_dataset.py:236`, `scripts/train_engine_b.py:129` and `:422`.
- Every one of them receives `feature_cols` — a list of **strings**.
- After R5, those strings are `["ppg", "snap_share", "yprr", …]`. The period is in the `period` column, by design, as the fix.
- `re.compile(r"_t\+?\d").search("ppg")` → `None`. `"ppg" in {"ppg_t1","ppg_t2",…}` → `False`.

**The guard passes green on a feature set that contains the label.** Not by being removed — by being handed input it can no longer see. `feature_validation.py:37-38` already confesses the mechanism: *"the outcome column legitimately encodes T+1/T+2 and would otherwise trip the leakage pattern"* — the guard distinguishes label from feature purely by spelling, and R5 abolishes the spelling.

The proposed replacement cannot help. `ppg` at `period=2025` (a feature) and `ppg` at `period=2027` (half the target `avg_ppg_t1_t2`, `engine_b_contract.py:15`) are the **same `feature_id`, same `FeatureDefinition`, therefore the same `lane`**. Whatever lane you assign — `Outcome` is the only honest one — the feature and the label are the identical type `Measurement[float, Outcome]`. A `FeatureSelector` that selects `period >= spec.training_cutoff`, or a sign error in lag derivation, type-checks, runtime-checks, and lane-checks perfectly.

`residual(p: Measurement[float, Model], a: Measurement[float, Outcome]) -> Residual` has the same hole: nothing in the signature stops `residual(pred_for_2027, ppg_2024)`. The type carries no clock.

## Why the claim lattice makes this worse, not better

This is the part that turns a gap into a break. A model trained with its label in the features produces a **spectacular** `EvaluationReport`. Every input is `Origin.OBSERVED` → `ORIGIN_CEILING` = `DECISION_SUPPORTED`. `compose()` takes `min()` over material inputs — all high. The eval is so strong the `EvidenceRecord` ratifies, lifting the evidence-record ceiling. `ClaimLevel` composes to `DECISION_SUPPORTED`, `Measurement.claim` renders a receipt, `MetricCell.receipt` is populated, `DecisionOpportunity` carries it, and David is shown the one thing the whole architecture exists to prevent: a decision-supported number that is an artifact of leakage, wearing a full provenance chain that is *entirely truthful about every link*. Fail-closed composition cannot catch it because nothing in the chain is open.

The spec's own §7 acceptance row says **"New feature → 1 `FeatureDefinition` row + a new `FeatureSetVersion`. No seam change."** Adding `ppg` as a per-period definition is exactly that one row — and it is the row that makes the label indistinguishable from a feature. The acceptance test passes and the system is unsound.

## Adding a fifth lane does NOT fix it

The tempting patch is a fifth member — `Realized`, `Production`, `World` — splitting "the label lane" from "observed world facts." It fails on the same example: `ppg` is *both*. It is the target at t+1/t+2 and a feature at t-1/t-2, in the same vintage, in the same column. No partition of `Lane` can separate them because the distinction is not about the value; it is about the value's `period` relative to `spec.training_cutoff`.

That is the real finding, and it is worse than "the vocabulary is one short." **`Lane` is closed on the correct axis and is being asked to carry a second, orthogonal one.** Provenance (whose belief) genuinely has four values and genuinely belongs closed. Admissibility (may this value enter this spec) is spec-scoped, cohort-scoped, temporal, and — by the spec's own §0 criterion (b) — *computable from open registries*, so it is not a state at all. §8's plan deletes five guards and replaces one.

## Minimal fix (contained, but it IS a seam change — do it before step 4)

1. **`FeatureDefinition` gains `temporal_role: TemporalRole`** — CLOSED at 2: `POINT_IN_TIME | REALIZED_FUTURE`. This is a legitimate closed vocabulary by the §0 criterion: every consumer branches, and the branch is not registry-computable.
2. **`TrainingSpec` gains a total admissibility predicate**, not a name list:
   ```python
   def admissible(self, d: FeatureDefinition, period: Period) -> bool:
       return period <= self.period_horizon(self.training_cutoff)
   ```
   with `TargetDefinition` the *only* thing permitted to select `period > training_cutoff`.
3. **`as_tabular` / `as_sequence` refuse at the seam**, raising `TemporalLeakage(feature_id, period, cutoff)` — so the guard lives where the pivot happens and cannot be bypassed by a caller who forgot to call a validator. This is the single highest-value line in the fix: today's guard is advisory and called from six sites; the new one should be structurally unbypassable.
4. **Model the four non-market prohibition sets as what they are**: an OPEN, spec-scoped `admissibility` registry keyed by `(spec_hash, feature_id)` with a reason code, seeded byte-identically from `ENGINE_A_PROHIBITED_IN_B`, the `nfl_*` block, `qb_rookie_risk_filter.ALLOWED_INPUT_COLUMNS`, and `OUTCOME_SEASON_COLUMNS`. Then §8's deletion sentence becomes true, because it is scoped to `LEAKAGE_REGEX` alone.
5. **`residual()` must assert `actual.as_of.effective > predicted_as_of.effective`** at runtime. Cheap, and it closes the evaluation-side twin of the same hole.

Sequencing: this must land with build step 4 ("Long-form `FeatureVintage`, written BESIDE the CSV"), not after. Step 4's stated proof is that `as_tabular()` emits a frame byte-identical to `engine_b_features_v2.csv` — that proof is silent on the guard, because the byte-identical frame is produced by a correct selector. The first *new* selector is the unprotected one.

---

# SECONDARY — `RefusalReason` is a WHY vocabulary and will grow twice this season

§0's own corollary: *"the state says WHETHER; the caveat registry says WHY. WHY grows forever, so WHY is never a `Literal` value."* `RefusalReason` is closed at five and is nothing but a WHY.

It fails criterion (a) on its own terms. §B4's justification for `Refusal` is **type**-distinctness — *"A DISTINCT TYPE. Not a dict you can `.get()` to 0.0"* — fixing `engine_b_service.py:139/:200`. Consumers branch on `Prediction | Refusal`. Nobody branches on which of the five. It is display text with a `Literal` around it.

Two forcing cases, both near-term:

**(a) Calibration cohort miss.** `Calibration.OUT_OF_COHORT` is a first-class member — *"artifact exists but does not cover this subject."* If a decision surface requires a calibrated interval (which §2.4 and the constitution both point toward), that subject yields a `Refusal`. Its reason is none of the five: the model exists (`not artifact_unavailable`), covers the cohort (`not no_model_for_cohort`), the entity is present (`not entity_absent`), the features are complete (`not features_incomplete`), and the subject is inside the model's support (`not out_of_support`). Forced member: `calibration_out_of_cohort`. Note the vocabulary is *already* inconsistent with a sibling closed vocabulary shipping in the same spec.

**(b) Retired mid-season.** A player retires week 6. He is on a roster (so `entity_absent` is false), in the training cohort (so `out_of_support` is false — he has seven seasons), his features are complete through week 6. Predicting his t+1/t+2 PPG is not a data problem, it is a subject-state problem. Forced member: `subject_inactive`.

Two members in one season is exactly the `ReportFreshnessStatus` failure the spec names in the `Availability` rationale — *"an 8-value `Literal` that gained a member every time a new failure mode appeared."*

**Fix, one line:** `Refusal.reason: RefusalReason` → `Refusal.caveats` already exists on the type. Make the reason a `CaveatCode` from the OPEN `CaveatCatalog` with `Severity.LIMITATION`, keep the five current values as the catalog's seed rows, and keep `Refusal` a distinct type — which was the whole point.

---

# BONUS — `Corroboration` raises a ceiling with no receipt

Not the assigned axis, but it is the same class of defect as the one §1.2 correctly rejected `Determinism` for, and I would not let it ship.

`Extracted.corroboration: Corroboration` is a **bare enum member**. `CROSS_SOURCE` and `HUMAN_AFFIRMATION` lift the §2.6 ceiling from `DESCRIPTIVE` to `DIAGNOSTIC` and, with an `EvidenceRecord`, to `REPLICATION_CANDIDATE`. There is no field anywhere on `Extracted` or `Receipt` pointing at **which** source agreed, **which** human affirmed, or **when**. `Receipt.evidence` is a single `EvidenceRef` already spoken for by the layout-family ratification, and `frontier()` walks `Derived.inputs` — which `Extracted` does not have.

So a claim-raising assertion is self-declared and unbacked, in a system whose founding law is *"A FACT WITHOUT ITS ORIGIN IS NOT EVIDENCE"* and whose §1.2 rejects `Determinism` in precisely these words: *"A row claiming `EXACT` for an LLM launders a nondeterministic read into a decision-eligible fact — with a green checkmark on it."* `corroboration=CROSS_SOURCE` with no ref is the same green checkmark.

**Fix:** `corroboration: tuple[CorroborationRecord, ...]` where `CorroborationRecord = (kind: CorroborationKind, witness: ReceiptRef, at: datetime)`, the ceiling table keys on `max(kind)`, and `Receipt.frontier()` walks witnesses too. This also delivers the escape hatch §1.2 promised for free — demoting `CorroborationKind` to an OPEN registry with a `claim_ceiling` column becomes a registry insert, since the kind is now a field on a record rather than the field itself.

---

# Verdict rationale

`SEAM_BREAKS` rather than `SEAM_STRAINS` because the primary finding is not a missing convenience — it is a **shipped safety property that the redesign removes with no expressible substitute at the seam**, whose failure mode is silent, whose blast radius is the product's central claim, and which the claim lattice actively amplifies (a leaked model earns a *higher* ClaimLevel than an honest one). The fix is contained — five items, all inside `FeatureDefinition` / `TrainingSpec` / `FeatureVintage` — but it is a genuine seam change and it must land with build step 4, not after it.

Files cited (all absolute):
- `src/dynasty_genius/models/engine_b_contract.py` (`:15-16`, `:250-266`, `:269-296`)
- `src/dynasty_genius/models/head_b_contract.py` (`:77-95`)
- `src/dynasty_genius/models/engine_a_contract.py` (`:66-71`)
- `src/dynasty_genius/features/feature_validation.py` (`:37-38`, `:100-110`)
- `src/dynasty_genius/features/qb_rookie_risk_filter.py` (`:1-26`)
- `src/dynasty_genius/eval/backtest_harness.py` (`:473`)
- `scripts/assemble_engine_b_dataset.py` (`:236`), `scripts/train_engine_b.py` (`:129`, `:422`)
- `app/data/training/engine_b_features_v2.csv` (33 columns, verified)

---
### BREAK 2 — verdict: SEAM_BREAKS

**Attack:** MEDIA × TIME. Walk one blob through five instants — T0 2026-08-13 the ranking is published; T1 2026-08-20 David screenshots it; T2 2026-08-21 extractor spec S1 (still a candidate) reads it; T3 2026-09-15 S1 is promoted; T4 2027-08-20 a better spec S2 re-reads the same blob and disagrees about both the VALUE and the PUBLICATION DATE printed on the page — then ask the spec to answer an as-of query dated between T2 and T4: (effective <= 2026-12-01, known_at <= 2026-12-01). Trace effective_at / captured_at / observed_at / started_at+finished_at / promoted_at / as_of.effective / as_of.known_at and the ClaimLevel through all five.

# Verdict scope

The MEDIA half holds. Adding screenshots and video genuinely costs the promised rows: `Extracted` beside `Observed` in one closed `Basis` union, an open `Locator`, blob-keyed identity, `duration_ms`/`frame_count` present from day one. §7 survives my attack unchanged.

The TIME half breaks. Not at an exotic edge — at re-extraction, which is the ordinary lifecycle of every extracted fact and the whole reason a better model "next year" is desirable. Concretely, **the as-of query Q above has no determinate answer under this spec: two defensible readings of the same text return different values.** Below is the walk, then the seven failures, then the minimal fix.

---

# The walk

| instant | what the spec records | what it cannot record |
|---|---|---|
| T0 2026-08-13 | `RawSnapshot.effective_at` — "what instant the CONTENT depicts" | the date is *printed inside the PNG*. See F1. |
| T1 2026-08-20 | `captured_at`, `Blob.sha256`, `basis` (origin ∈ {OBSERVED, DECLARED}) | — |
| T2 2026-08-21 | `ExtractionRun.started_at/finished_at`, facts keyed `(blob_sha256, field_path, spec_hash)` | which of T1/T2 is `AsOf.known_at`. See F2. |
| T3 2026-09-15 | `PromotionChain` moves the ActivePointer | `promoted_at` — the protocol has **no dates at all**. See F5. |
| T4 2027-08-20 | second run, S2, appends rows under a new key | `Supersession` has **no timestamp**. See F4. |
| Q 2026-12-01 | filter `(effective <= E, known_at <= K)`, then precedence | `precedence.resolve(...)` takes **no `known_as_of`**. See F3. |

---

# F1 — `effective_at` is circular, and `AsOf` is the one kernel field with no basis

`RawSnapshot.effective_at` must be stamped by `sources` at T1. But for a screenshot, T0 is *glyphs inside the image*. The only thing that can read it is the extractor, which sits downstream — and the spec closes that door explicitly: "`basis`: origin in {OBSERVED, DECLARED}. **Never EXTRACTED — that is downstream.**" So `effective_at` is `None`, or it is an operator guess laundered onto an OBSERVED-basis snapshot.

Downstream this is worse. `extract()` takes `as_of: AsOf` as a plain keyword. Every other checkable field is demanded with evidence — `derivation`, `declared_by`, `observed_at`, `locator`, `verbatim` — but `AsOf` is a bare frozen pair of datetimes with **no `Receipt`, no `ClaimLevel`, no origin**. The design's own law is "a value with no basis must not be constructible," and the single field every point-in-time query filters on is exactly that value.

The lattice hole follows mechanically. `compose()` mins over *material input ClaimLevels*. `as_of` is not an input and has no level, so it is **structurally excluded from the min**. A fact can be certified REPLICATION_CANDIDATE (reproduced + cross_source, §2.6 row 4) while its position on the effective axis is an uncorroborated single-glyph read of "Aug 13" that no ceiling table ever saw. The weakest link in the chain is the one link the fail-closed composer cannot see.

# F2 — `known_at` for an extracted fact is undefined, and the two candidates give opposite answers

"Wall-time we could have known it." At T2 the value did not exist in any store — but the *information* had been in our possession inside the blob since T1. The spec names neither.

- **known_at := T1 (blob possession).** Then the T4 re-extraction writes a row stamped `known_at = 2026-08-20`. Q returns S2's value. The store is still append-only — a genuinely new key — but §2.1's guarantee ("no row with known_at > K may enter a result") is violated in substance: **knowledge is back-dated, and an as-of answer already given changes underneath a backtest.**
- **known_at := T2/T4 (run finish).** Safe on that axis — and then the answer depends entirely on machinery that has no clock (F3–F5).

The repo precedent cuts the wrong way and will decide this by default if the kernel stays silent. `capture/fc_forward_capture_store.py` keys on `snapshot_date` and *deliberately excludes* `retrieved_at` from `_CONTENT_COLUMNS` — one world clock, knowledge-time treated as run noise. `sources/schedules_capture.py:931` does the opposite, minting `check_id = f"c-{_compact(observed_at)}-{raw_sha256[:12]}"` — a real knowledge clock per check. Two shipped stores, two conventions; the kernel inherits whichever the first implementer copies.

# F3 — the precedence function is not bitemporal. This is the break.

B1: "read models resolve *currently-preferred extraction for this blob+field as of T*" through "a versioned precedence function (`human_adjudication > deterministic > reproduced > recorded`, then **newer promoted spec**), whose version goes in the Receipt."

Recording the *version* says which code ran. It does not stop that code from seeing rows it must not. "Newer promoted spec" is evaluated against the registry's **present** state. Re-run the Q backtest today and it resolves through S2's T4 reading — the future leaking into the past, the exact defect §2.8 invariant 3 was written to kill at the Series edge, reappearing one layer up where no invariant guards it.

This is **inexpressible, not awkward**: there is no parameter to pass. And the author demonstrably knows the pattern — `Registry.get(key, *, known_as_of)` and `Crosswalk.resolve(key, *, effective, known_as_of)` both have it. Extraction precedence is the one resolver that lost it, and it is the one that adjudicates a *disagreement*.

Worse, §2.10 makes precedence load-bearing by design: `rewritten: tuple[()]` — "report, never repair." The data plane is *forbidden* from settling the S1-vs-S2 dispute. All adjudication is deferred to the read-model plane. **The design pushed every time-sensitive decision into the only component with no clock.**

# F4 — `Supersession` has four fields and zero timestamps

`Supersession(loser, winner, reason, adjudication_ref)`. "As of 2026-12-01, was row A superseded?" is unanswerable from the type. Contrast B2's `Resolution`, which gets this exactly right in the same document: `valid_from`, `valid_to`, `asserted_at`, `superseded_by`. Identity corrections are bitemporal; extraction corrections are not — and they are the same problem.

# F5 — the trust plane has no clock either, so claim level is not point-in-time reconstructible

`PromotionChain`, `ActivePointer`, `PromotionReceipt`, `EvaluationReport` carry **no dates**. Three consequences:

1. **Servability at Q is unreconstructible.** "Serving REFUSES an artifact whose spec_hash is not the promoted one." At T2 the S1 fact existed but was unservable; at T3 it became servable. Nothing timestamps that transition, so a replay at Q resolves against today's pointer. Q's answer depends on today's promotion state — leakage again.
2. **Canary demotion cannot reach already-minted facts.** "A canary failure demotes the active pointer — it does not warn." The pointer governs *future serving of the artifact*. The Measurements minted between T3 and the demotion are immutable, content-addressed, and carry their ceiling frozen in `Receipt.claim_ceiling`. No `Verdict` member covers this: `DISPUTED` means a re-read disagreed, and a demotion is not a re-read of any particular fact. `AuditReport` has `stale_facts` and `disputed_facts` and nothing else. So **facts from a discredited extractor keep their DIAGNOSTIC/REPLICATION_CANDIDATE ceiling and keep serving** — the precise failure mode §8/build-order step 8 exists to prevent.
3. **A retracted experiment cannot lower a claim.** `EvidenceLedger` is append-only and bitemporal; `Receipt.claim_ceiling` is frozen at mint. Falsify an EvidenceRecord and the ledger's ceiling-as-of-now drops while every stored Receipt keeps the old one. Claim level is monotone-up-only in practice — the opposite of fail-closed.

# F6 — re-extraction moves facts on the *effective* axis, so as-of answers are non-monotone in K

S2 reads the page's date as Aug 13 where S1 read Aug 18. A fact that was inside the box `(effective <= E)` **leaves it** when knowledge increases. That is legitimate bitemporal behavior only if a correction record carries a clock — see F4. Without one, both rows are simultaneously "current" with different effective dates, and F3 picks between them with no K.

# F7 — the answer to Q, and whether it is defensible

Q returns S1's reading — the value we now know is wrong. That answer is **right for replay** ("what would we have believed then") and **wrong for audit** ("what does that screenshot actually say"). Real bitemporal separates these on one store with K = then vs K = now.

This spec can deliver *neither reliably*, because the replay/audit choice is made inside a resolver that ignores K. Under F2's blob-time reading Q returns 7142 (future leak); under run-time it returns 7412 only if F3 is also fixed. **Two defensible readings of the same specification return different values for the same query.** That is not a strained seam; that is an undefined one.

Root cause in one line: `derived` had the same re-run-disagrees shape and the spec resolved it by calling disagreement DRIFT (staleness → the newer run wins). Extraction correctly refuses that framing — stochastic disagreement is `DISPUTED`, not stale, and §2.10 forbids repair — **but having refused it, supplies no replacement mechanism with a clock.**

---

# Minimal fix — five edits, one of which is a real seam change

1. **`AsOf` gains a basis.** `effective_basis: ReceiptRef | None`, `effective_claim: ClaimLevel`; `compose()` mins it in. `extract()` refuses a caller-supplied `effective` without a basis; a screenshot with no legible date yields `Unknown(ABSENT)` on the time coordinate, never `captured_at` silently standing in for `published_at`. *Cost: `AsOf` is embedded in Measurement, Receipt, RawSnapshot, Series, Prediction, PVO, Publication — this is the expensive one, and it is far cheaper now than after step 8.*
2. **Name the clock in the kernel.** `known_at(Extracted) := ExtractionRun.finished_at`, never `Blob.captured_at`. Enforce in the constructor: raise if `as_of.known_at < run.started_at`. One assertion; it is the entire difference between append-only-and-safe and append-only-and-back-dating.
3. **`Supersession` gains `asserted_at: datetime` and `valid_from: datetime`.** Copy B2's `Resolution` shape verbatim — this is a paste, not a design.
4. **Every resolver gains `known_as_of`, matching `Registry.get`.** `precedence.resolve(blob, field, *, known_as_of)`; `ActivePointer.active(subject, *, known_as_of)`; `PromotionReceipt.promoted_at`; demotions as append-only rows with `demoted_at`; `EvaluationReport.as_of: AsOf`.
5. **Make the ceiling a read-time projection, not a frozen field.** Keep `Receipt.claim_ceiling` as the immutable mint-time *record*, and compute the served ceiling as `min(receipt.claim_ceiling, ledger_ceiling(as_of=K), promotion_ceiling(as_of=K))`. This is the change that lets a retracted experiment or a demoted extractor *lower* an existing claim without violating immutability — and it makes F5 disappear entirely rather than needing a new `Verdict` member.

Ordering note: (2) and (3) are free today and unaffordable after step 8. (1) must land before step 1 ships `kernel/` "with zero production call sites," or it becomes a 600-line-package rewrite.

---
### BREAK 3 — verdict: SEAM_BREAKS

**Attack:** Sequence-model + distributional-output stress test on FeatureVintage/TrainingSpec/ScoringEnvelope/Measurement, plus the shortest legal path to a de-facto ranked action list.

The ragged-shape half of the sequence case survives. The distribution half, the missingness half, and the no-verdict law do not. Six concrete breaks, each with the minimal fix.

=== (a) SEQUENCE MODEL ===

BREAK 1 — A predictive DISTRIBUTION is not expressible. `type Uncertainty = Interval | Uncalibrated`, and `Interval` carries exactly one `coverage: float`. A quantile-regression GRU, NGBoost, a deep ensemble, or MC-dropout emits P10/P25/P50/P75/P90 — five coverage levels, or a full CDF. `Measurement` has ONE `uncertainty` slot in a frozen `__slots__`. So adding the model family David explicitly named requires editing a kernel union — a seam change — and every `match` on `Uncertainty` becomes non-exhaustive. §7 row "New model family ... **No** seam change" is FALSE for the exact family the pass exists to welcome. Worse: `Uncertainty` is a CLOSED union that is NOT one of the ten closed vocabularies, has no closure argument in §1.1-style prose, no rejected-members table, and no registry escape hatch — it is the only closed surface in the spec that was closed by accident. The honest option the types offer (`Uncalibrated(UNCALIBRATED)`) DISCARDS the model's actual output, so the engineer's rational move is to stash quantiles in `ModelArtifact.fit_diagnostics` (per-artifact, not per-row — wrong cardinality) or in the read-model body as a raw list, un-laned and un-receipted. That is the leak. FIX: make it `type Uncertainty = Interval | QuantileSet | Ensemble | Uncalibrated` NOW, or better, open it: `Uncertainty` becomes a protocol with a `method: CalibrationRef` and a `quantile(p) -> float`, so a new representation is a registry row. Do it before the kernel freezes, not after.

BREAK 2 — `Measurement.__add__`/`__sub__` mint a Measurement with NO stated uncertainty rule and NO derivation parameter. §2.5 says the four smart constructors are "the only path to a Measurement", yet `__add__` returns one and takes no `derivation`, no `inputs`, no `uncertainty`. So arithmetic must private-mint inside `kernel/` (which the §8 AST scan explicitly permits there), and the implementer will write `lo+lo, hi+hi`. That is a comonotonicity assumption: adding two nominal-80% intervals does not yield an 80% interval. The result carries `Calibration.CALIBRATED` and a `CalibrationRef` inherited from an operand it no longer describes. The system's central promise — "every displayed number carries a receipt, a value with no basis must not be constructible" — is satisfied while the uncertainty is silently fabricated. FIX: `__add__`/`__sub__` must either refuse when either operand is an `Interval` (forcing an explicit `derive(...)` with a named combination rule in the derivation registry), or downgrade the result to `Uncalibrated(UNCALIBRATED)` and attach a `LIMITATION` caveat. Pick one and write it into §2.4; today it is unspecified, which means it will be decided by whoever types the operator first.

BREAK 3 — `SequenceBundle.mask` is `(T_i,)` bool, and that single bit re-collapses the exact distinction R6 exists to protect. Two independent problems:
  (i) WRONG RANK. The mask is one bit per PERIOD, but missingness is per (period, feature). Verified against the real vintage: `app/data/training/engine_b_features_v2.csv` row 1 (00-0019596, 2018, QB) has `snap_share_t_minus_1`, `route_participation`, `tprr`, `ppg_t_minus_2`, `target_share_nfl`, `air_yards_share`, `yprr` all EMPTY while the player is unambiguously present that season. `values` is `(T_i, p)`; the mask cannot mark those holes. The only representations left are NaN (which the next `SimpleImputer` fills — the precise defect §B3 names at `app/services/engine_b_service.py:147-150`) or median-impute, which R6 forbids. R6 is therefore UNENFORCEABLE at the seam that was designed to enforce it.
  (ii) WRONG TYPE. A bool cannot distinguish "not in the league" (`NOT_APPLICABLE`, structural, the thing R6 says must never be imputed) from "we have no capture" (`ABSENT`, recoverable) from "exists but observed after as_of" (`OUTSIDE_AS_OF`, recoverable by widening the window). The kernel spent five closed values earning that distinction and `as_sequence` throws four of them away on the way to the model. FIX: `mask: tuple[NDArray, ...]` each `(T_i, p)` of uint8 `Availability` codes, not `(T_i,)` bool. This is the single highest-value edit in the sequence design and it costs one line in the spec.

BREAK 4 — There is no PERIOD GRAIN on `FeatureDefinition`, and the repo already has two grains live. `FeatureShape` is closed at `{SCALAR_PER_ENTITY, PER_ENTITY_PERIOD}` — that is the SHAPE, not the CADENCE. The LongFrame's `period` is a bare int. Today's vintage is seasonal (`feature_season`, 2018), while `src/dynasty_genius/playerprofiler_gamelog.py:90-91` ships `GAMELOG_TABLE = "pp_gamelog_week"` / `GAMELOG_STREAM = "gamelog_week"` — weekly grain, 2020-2025, exactly the stream a career-arc sequence model wants for in-season role change. Register a weekly `FeatureDefinition` (1 row, "no seam change" per §7) into a seasonal FeatureSet and `as_sequence` aligns them on the same `period` index: week 3 silently joins to career-season 3. Nothing raises. `resolve_features` checks NAMES, not grains. FIX: add `period_grain: PeriodGrain` (CLOSED: `season | week | day`) to `FeatureDefinition`, and have `as_sequence`/`as_tabular` refuse a mixed-grain FeatureSet unless the spec names an explicit resampling derivation. Also add a `dtype`/`value_kind` — see Break 5.

BREAK 5 — The LongFrame's single `value` column has no dtype axis, and the current vintage is already ~7/33 non-numeric. Header check: `aging_curve_position` ("QB_pocket"), `depth_chart_position` ("QB"), `team` ("NE"), `position`, `is_dual_threat` (bool), `training_eligible` (bool), `te_role_is_risk_profile`. `FeatureDefinition` carries `unit: Unit` with `symbol`/`dimension` — there is no Unit for "NE". And `Measurement[T: (int, float)]` means the kernel has no categorical value type at all. `team` is *per-entity-period* and is the literal mechanism of a career arc (a WR changing offenses is the signal a sequence model exists to catch). So R5's long-form fix cannot store the features today's wide CSV already stores, and "add a feature = 1 FeatureDefinition row" fails on the first categorical. FIX: `FeatureDefinition.value_kind: ValueKind` (CLOSED: `real | integer | boolean | categorical`) plus a `categories: tuple[str, ...] | None` and a `value_str` column beside `value` in the frame (or an encode-at-read policy named in the spec hash). Note that `Unit` must become `Unit | Nominal` for the categorical case, which touches `Measurement` — so decide it before the freeze.

BREAK 6 — THE HORIZON AXIS LIVES IN THE LABEL NAME. This is R5's own root cause, reproduced verbatim on the output side and not noticed. `PVO.beliefs: Mapping[LabelId, Prediction | Refusal]` is keyed by `LabelId`, while `Prediction` separately carries `horizon: Horizon`. Two predictions for the same label at different horizons COLLIDE ON THE MAPPING KEY and one is silently lost. A career-arc sequence model's natural output is a trajectory — t+1, t+2, t+3 — so the seam forces the engineer to do exactly what the repo does today: bake the horizon into the label. Verified live at `app/services/engine_b_service.py:162`, `src/dynasty_genius/pvo_assembler.py:384`, `app/services/morning_tape_artifact.py:138`, `app/services/roster_auditor.py:503` — the label is literally `predicted_avg_ppg_t1_t2`. "`ppg_t_minus_1` is not a feature, it is a feature plus a query" — and `predicted_avg_ppg_t1_t2` is not a label, it is a label plus a horizon plus an aggregation. Adding a 3-year horizon is then a new LabelId, a new TargetDefinition, and a new consumer branch everywhere the string is read: four files above, and that is before the frontend zod validators. Secondary loss: three marginal `Prediction`s cannot express a JOINT path, so the correlation across horizons — the whole point of a sequence model — has nowhere to live. FIX: key beliefs on `(LabelId, Horizon)`, and make `LabelId` horizon-free by construction (the §6-style mechanical test that forbids mechanism tokens in `ClaimLevel` member names should be pointed at `LabelId` too: no `_t1`, `_t2`, `_yr`).

BREAK 6b — `Residual.error: float` with `predicted: Measurement[float, Model]` forces a POINT estimate into the evaluation record. A quantile model has no canonical point; taking the median is an unrecorded policy choice. Distributional scoring is CRPS / pinball / PIT, not a scalar error, and `Residual` has no horizon and no claim level. `EvaluationReport.metrics` is open so aggregate CRPS is fine — but the per-row audit record, the thing that makes evaluation checkable, is closed to a float. FIX: `Residual.score: Mapping[MetricId, float]` (open) plus `point_reduction: DerivationRef | None` naming how a point was taken, and add `horizon`.

BREAK 6c (minor) — `TrainingSpec.lag_depth: int | Literal["full_history"]` cannot express windowing policy (right-align vs left-align, padding, truncation, whether an in-progress season counts). The engineer puts it in `hyperparameters: Mapping[str, JsonScalar]` — it IS inside the spec hash, so it is reproducible, but it is now DATA SELECTION hiding in the hyperparameter bag, invisible to `resolve_features` and to the feature contract. FIX: `window: WindowPolicy` as a first-class spec field.

=== (b) SHORTEST PATH TO A DE-FACTO RANKED ACTION LIST ===

Length: ONE registry row. Rules violated: ZERO. And the row already exists in the repo.

`OrderingBasis.sort_key: FeatureId | MarketMetric | LabelId`, `lane: type[Lane]`, `claim = DESCRIPTIVE`. `FeatureId` is an OPEN registry key. NOTHING in the spec requires a FeatureId used as a sort key to be a PRIMITIVE feature rather than a composite that already encodes desirability. So: register one `FeatureDefinition(feature_id="xvar_pct", lane=Model, shape=SCALAR_PER_ENTITY, derivation=...)`. Every check passes — single lane, Model only, no market arithmetic, DESCRIPTIVE claim, no banned word, no `Comparison` involved. Then sort every `DecisionOpportunity` by it.

That composite is not hypothetical. `src/dynasty_genius/models/engine_b_contract.py` ships `ENGINE_B_P90_PPG` (normalize prediction to a 0-100 ceiling), `ENGINE_B_VAR_THRESHOLDS` (replacement rank), `ENGINE_B_REPLACEMENT_DVS`, and `XVAR_LAMBDA_ENGINE_B` whose own comment reads "Allows comparing DVS points above replacement ACROSS POSITIONS." That is an omnibus score with a cross-positional comparability multiplier — the definition of the thing PRODUCT LAW bans — and it is 100% Model lane, so the lane type parameter never fires. It is already the sort key at `src/dynasty_genius/league_opportunity_map.py:518` (`sort_key="taxi_long_term_value_desc", sort_value=raw_xvar`) and drives the cut ordering at `src/dynasty_genius/roster_cut_engine.py:171,359`.

Three compounding gaps make it stick:

1. **`Publication` has no ordering field.** §B7 defines `OrderingBasis` and §B8 `Publication[T]` never requires one. `body: T` is a generic; JSON array order IS the ranking, it is covered by `digest` (so it is "receipted") and constrained by nothing. `OrderingBasis` is therefore a documentation type nobody is forced to instantiate. FIX: `Publication.ordering: OrderingBasis | Unordered` — non-defaulted, and a contract test that every list-bodied read model declares it.

2. **Serve is permitted to reorder.** §B9's MAY-NOT list is "compute, fetch, open a file, open a database, import from sources/extraction/adapters/features/modeling, invent a caveat token." Sorting is none of those. And the frontend can `.sort()` freely — the build-enforced arm is LEXICAL, not structural.

3. **The lexical guard demonstrably permits it.** `frontend/src/shell/banned_vocabulary.json` bans `verdict`, `dynasty_tier`, `confidence`, `recommended_action`, `roster_action` and phrases like "sell now". It does NOT ban `score`, `rank`, `priority`, `sort_value`, or `score_components` — and `league_opportunity_map.py:127` ships `score_components` on every card today, under a comment (`:76-78`) asserting "the hidden weighted composite score ... is removed." §8 proposes copying exactly this mechanism.

**Cross-ACTION rank, also free:** `ActionKind` is closed at 6; the repo groups by `sort_key` and sorts within group (`:607-620`). Register ONE FeatureId as the sort key for ALL six ActionKinds and concatenate the groups in a fixed order — a cross-action desirability rank assembled without a single cross-action comparison. And selection is entirely unconstrained: `:667` already does `partner_rankings[:10]`. A top-10 truncation is a verdict with a threshold instead of a sort key, and the spec's prose only forbids the sort key.

**WHERE THE LAW IS PROSE-ONLY — name it plainly.** §B7's `# DELIBERATELY ABSENT AND UNADDABLE: score, rank, desirability, fairness, verdict` is a COMMENT, and its justifying sentence — "DecisionOpportunity has no float to sort by, so a desirability rank is unconstructible" — is false as written. `DecisionOpportunity.lanes.model[0].value` is a `Measurement[float, Model]`, and §2.4's `__lt__` explicitly PERMITS same-lane, same-unit comparison. `sorted(opps, key=lambda o: o.lanes.model[0].value)` is one line, type-correct, lane-correct, and produces a ranked action list with no new field, no new vocabulary word, and no cross-lane arithmetic. That is precisely `app/services/engine_b_service.py:200` today.

MINIMAL FIXES that make the law structural rather than aspirational:
  (i) `FeatureDefinition.lane` is SELF-DECLARED — the same laundering defect R4 correctly kills for `Determinism`. Apply R4's own remedy: COMPUTE a definition's lane from the lanes of its `computed_from` streams and its derivation's input receipts, and refuse a Model-lane definition whose closure touches a Market stream. Without this, one honest-looking registry row blends the lanes below the type system.
  (ii) Add `composite: bool` / `admissible_as_sort_key: bool` to `FeatureDefinition`, defaulting to FALSE, and type `OrderingBasis.sort_key` to accept only admissible keys. A normalized, replacement-adjusted, scarcity-weighted index is not a feature; it is a verdict with a unit.
  (iii) Make `OrderingBasis` mandatory on `Publication` and add a seventh AST scan: no bare `sorted(`/`.sort(` over a `DecisionOpportunity` or card collection outside a function that returns an `OrderingBasis` alongside the ordered list.
  (iv) Add `score`, `rank`, `priority`, `sort_value`, `score_components`, `index`, `grade` to `banned_fields`, and accept that the current surface fails that check — which is the point.

=== VERDICT ===
SEAM_BREAKS. The long-form vintage genuinely fixes the ragged-input problem (R5 is right and the 2-lag/60-player census earns it). But the DISTRIBUTIONAL output — half of what "sequence models for career arcs" means — requires editing a closed kernel union that was never argued closed, so David's own acceptance test fails on his own named extension. And the no-verdict law, the product's central promise, is enforced at the ordering boundary by a comment and a lexical wordlist, both of which the repo's live xVAR surface already walks past. Breaks 1, 3, 5 and 6 must be settled BEFORE the kernel freezes; fixing them after costs the seam change the whole pass exists to avoid.

---

## DECISIONS THAT ARE DAVID'S

### Video retention: keep blobs offsite, keep them local-only with an honest degradation, or do not accept video at all until the extraction lane is proven on stills?

**Why it matters:** app/data is 15 GB measured today. One 1080p clip is 100 MB-1 GB, so a handful of clips doubles the footprint, and the append-only law means nothing can be deleted to recover. Re-extraction requires the EXACT bytes, so eviction is not free: it sets retained=False, recheck returns NOT_CHECKABLE, and the fact automatically and visibly loses claim level. That is honest, but it means a video-derived fact decays to descriptive on a schedule you choose by choosing a budget. The spec ships the type shape for video at zero cost either way (Locator already carries t_start_ms/t_end_ms; RawSnapshot already carries duration_ms/frame_count, None for stills), so this decision gates only whether any video BYTES are ever accepted — not whether the seam supports them.

**Options:** (a) irreplaceable — everything offsite to gs://dynasty-genius-backup-dtl; unbounded cloud cost, full re-checkability forever. (b) local_only_with_receipt (spec's default) — receipt, facts and audit chain go offsite, blobs stay local under a per-source media_budget_bytes with a media_budget_exceeded caveat on the daily health check; on loss the archive honestly reports absence rather than a pretend backup. (c) stills only for now — accept image/png and application/pdf, refuse video/* at the catalog row, revisit once one screenshot extractor has cleared a real adjudication cycle. Note (b) and (c) compose: (c) is (b) with the video row not yet written.

### Retiring overall_grade will LOWER the stated grade on at least one shipped model artifact. Accept the visible drop, or run both numbers side by side until you have seen the divergence?

**Why it matters:** Verified live: backtest_harness.py:337 reads `elif g3_result is not True: grade = "ACTIVE_B"` — G3 MARKET SUPERIORITY decides overall_grade — while line 385 on the SAME object comments `g3_market_superiority_pass=g3_result, # DISCLOSED only; never gates model_status`. Two ladders on one object disagreeing about the product's central law. Under kernel law a Market Observation may never raise a Model claim, so overall_grade must go and model_status is already correct. But the market-free claim will be lower than the number currently displayed, on a surface you look at, and it will read as a regression rather than as the correction it is. This is finishing a migration someone already started, not reversing a ruling — but the number going down is yours to accept, not the seam pass's.

**Options:** (a) Land the market-free ClaimLevel alongside overall_grade, display both, let the divergence be the evidence, retire overall_grade when you have seen it. Slower, no surprise. (b) Retire overall_grade in the same change that lands ClaimLevel, with a caveat on the surface stating that the prior grade included a market comparison. Faster, one visible drop. (c) Keep overall_grade permanently as a disclosed, explicitly market-inclusive DIAGNOSTIC label that can never gate anything. Preserves the number but keeps a fifth ladder alive, which is what the kernel exists to stop.

### May an extracted fact ever become a MODEL FEATURE, and if so at what claim floor?

**Why it matters:** Because claim composes by min(), an extracted feature at DIAGNOSTIC caps the ENTIRE model consuming it at DIAGNOSTIC. That is not a bug — it makes the cost of trusting a screenshot visible at the exact point of trusting it. But it decides whether the screenshot capability is load-bearing or decorative. If extracted facts stay in the context/evidence lane, screenshots inform your reading and never move a number, and the human-adjudication queue stays small. If they may enter features at REPLICATION_CANDIDATE, a paid source you can only screenshot can genuinely change a projection — at the price of an adjudication backlog on the (field x layout-family) pairs that feed it, with you as the only adjudicator. The seam supports both; the type system does not choose.

**Options:** (a) Context lane only — extracted facts never enter a FeatureSet; source_registry's existing context_signal role already expresses this and the guard is already written. (b) Features permitted at REPLICATION_CANDIDATE — requires an EvidenceRecord ratifying the field x layout-family pair, so the queue is bounded by LAYOUTS not by rows, and confirming one screenshot template confirms a class of reads. (c) Features permitted at DIAGNOSTIC — cheapest, but every model consuming one is capped at DIAGNOSTIC forever, which means it can inform and can never decide. Spec default is (a) with (b) as the designed-in upgrade path; (c) is not recommended.

### Add mypy --strict scoped to src/dynasty_genius/kernel/ as a CI step, or ship the lane guarantee runtime-only?

**Why it matters:** Verified: neither mypy nor pyright is importable in the venv, ruff selects only E4/E7/E9/F/I, and CI has no typecheck step — while the FRONTEND is checked under near-maximum strictness. So the static half of Lane is DECORATIVE today: `model_measurement - market_measurement` is caught only when that line actually executes, and a caller who never runs it ships a lane bug. The runtime arm is real and load-bearing on its own, so this is not a correctness gate — it is the difference between one guard and two. The cost is a new tool in a workflow where you are still learning syntax, and PEP 695 generics (`class Measurement[T, L: Lane]`) would be the FIRST generics in this codebase. The mitigation is that callers never spell a generic: they call observe(12.4, unit=PPG, lane=Model, ...), which reads as plain Python, and every bracket stays confined to kernel internals.

**Options:** (a) Add it, scoped to kernel/ only — a brand-new ~600-line stdlib-only package can be strict from day one with zero findings backlog and no repo-wide migration; widen later to market/modeling/features as those land. (b) Ship runtime-only and revisit once a real lane bug escapes — honest, and the LaneError message already names both lanes, both units, and the bridge() alternative, so the failure teaches. (c) Add it repo-wide — NOT recommended: ~140 untyped modules would produce a findings backlog that guarantees the ratchet starts dirty and gets suppressed.


---

## THE SPECIFICATION

# Dynasty Genius — Frozen Seam Specification v1

Every later per-layer design consumes this as a given. Type signatures are normative.
Python 3.14, PEP 695 generics, stdlib-only in `kernel/`.

---

## §0. The reading rules

**The closure criterion.** A value earns a slot in a CLOSED vocabulary iff **(a)** every consumer must branch on it, and **(b)** the branch cannot be computed by reading an OPEN registry. If (a) fails it belongs in a receipt. If (b) fails it is a projection, not a state.

**Corollary (the `ReportFreshnessStatus` lesson):** the state says WHETHER; the caveat registry says WHY. WHY grows forever, so WHY is never a Literal value.

**Two normative constraints on the whole design:**

1. **`Measurement` is a BOUNDARY AND PRODUCT type, never a COMPUTE type.** Vectorized inner loops stay pandas/numpy on plain floats. Measurements are minted exactly once, at the `read_models` publish step, with one `Receipt` object shared by every cell in a column-vintage. This is why `basis` holds a *resolved object* and not a ref — sharing is free, resolution is not. A benchmark in the kernel contract suite mints 10k Measurements over the real 2,741-row feature CSV and asserts a wall-clock ceiling.
2. **`kernel/` imports nothing but stdlib.** Not pandas, not pydantic, not FastAPI, not sqlite3. Pydantic DTO projection is `serve`'s job.

---

## §1. The complete closed surface — `kernel/vocab.py`

Ten vocabularies, **38 values**. This is the entire frozen surface of the system. Everything else is an OPEN registry key (`NewType(..., str)`), insert-only.

```python
# ---- Lane: a TYPE PARAMETER. Tag classes, not enum members. -------------------
class Lane:
    """Tag. Never instantiated, has no value form, cannot be assigned to a field."""
    __slots__ = ()
    key: ClassVar[str]
    def __init__(self, *_a: object, **_k: object) -> NoReturn:
        raise TypeError("Lane is a tag, not a value. Pass the class: Measurement[float, Model]")

class Model(Lane):   key = "model"     # what WE believe (intrinsic, market-independent)
class Market(Lane):  key = "market"    # what OTHERS believe: price AND expert consensus
class Outcome(Lane): key = "outcome"   # what HAPPENED (the label lane; what modeling trains on)
class League(Lane):  key = "league"    # what is STRUCTURALLY TRUE of the league (constraints)

LANES: Final = (Model, Market, Outcome, League)

class Origin(StrEnum):        # partitions by HOW YOU RECHECK
    DERIVED   = "derived"     # re-run a function
    DECLARED  = "declared"    # re-ask a person
    OBSERVED  = "observed"    # re-query the world
    EXTRACTED = "extracted"   # re-read a representation

class ClaimLevel(IntEnum):    # ORDERED. composes by min(). __bool__ RAISES.
    DESCRIPTIVE           = 0
    DIAGNOSTIC            = 1
    REPLICATION_CANDIDATE = 2
    DECISION_SUPPORTED    = 3
    def __bool__(self) -> NoReturn:
        raise TypeError("ClaimLevel has no truth value; `if claim:` inverts DESCRIPTIVE")

class Severity(IntEnum):      # ORDERED. composes by max(). DUAL of ClaimLevel.
    NOTE       = 0            # context only; no mechanical effect
    LIMITATION = 1            # real but narrower than it looks -> CAPS claim level
    INTEGRITY  = 2            # we believe something is false -> FORCES availability=ABSENT

class Availability(StrEnum):        # WHETHER a slot holds evidence
    PRESENT        = "present"
    IMPUTED        = "imputed"          # a stand-in is present; it is NOT evidence
    ABSENT         = "absent"           # we looked; it is not in our stores
    NOT_APPLICABLE = "not_applicable"   # undefined for this subject; capture cannot fix it
    OUTSIDE_AS_OF  = "outside_as_of"    # exists, but observed AFTER the as-of edge

class Freshness(StrEnum):     # LIFTED VERBATIM from sources/feed_cadence.py:84-85
    CURRENT = "current"; DUE = "due"; NOT_DUE = "not_due"; UNDETERMINED = "undetermined"

class Calibration(StrEnum):   # does the UNCERTAINTY statement mean what it says
    CALIBRATED     = "calibrated"       # REQUIRES a CalibrationRef; lane-specific
    UNCALIBRATED   = "uncalibrated"
    OUT_OF_COHORT  = "out_of_cohort"    # artifact exists but does not cover this subject
    NOT_APPLICABLE = "not_applicable"   # not a probabilistic estimate

class Reproducibility(StrEnum):  # ORDERED, best first. COMPUTED, never asserted.
    DETERMINISTIC = "deterministic"  # pure function of bytes; provable by re-running in CI
    REPRODUCED    = "reproduced"     # k>=2 samples agreed after normalization
    RECORDED      = "recorded"       # ran once; auditable, not repeatable

class Corroboration(StrEnum):    # independent support for an extracted fact
    NONE              = "none"
    SELF_CONSISTENT   = "self_consistent"    # the document's own redundancy
    SECOND_EXTRACTOR  = "second_extractor"   # architecturally different reader agrees
    CROSS_SOURCE      = "cross_source"       # an independent OBSERVED source agrees
    HUMAN_AFFIRMATION = "human_affirmation"  # a person saw the crop and confirmed

class Verdict(StrEnum):       # the result of a recheck
    REPRODUCED    = "reproduced"
    DRIFTED       = "drifted"        # derived: re-ran, got something else -> STALE
    DISPUTED      = "disputed"       # extracted: differs, but the reader is stochastic
    AGED          = "aged"           # observed: past its freshness window
    UNAFFIRMED    = "unaffirmed"     # declared: past reaffirm_after
    NOT_CHECKABLE = "not_checkable"  # no derivation to re-run / blob evicted
```

### §1.1 Lane closure argument (RULED)

A number about a player states: our belief (`Model`), others' belief (`Market`), what happened (`Outcome`), or what is structurally true of the league (`League`). There is no fifth belief-holder.

- **Expert consensus is `Market`, not a fifth lane.** Already ruled empirically — DynastyProcess ECR and KTC community CSV sit in the same `market_source` Literal as FantasyCalc at `eval/backtest_artifact.py:165-172`. Mock-draft consensus (`mock_consensus/`) is **pre-classified as `Market`**: it is price discovery. Write this into `lane.py` so the question is answered before it is urgent.
- **`Outcome` and `League` do not merge.** `Outcome` is the label lane — it is what `modeling` trains and evaluates against, and it is subject to the point-in-time law in a way league facts are not (a week-5 outcome does not exist until week 5 completes). `League` is the constraint lane. Merging them would let a box score enter a DOO's constraint set and let a roster-slot count be used as a training label. Structurally: `residual()` consumes `Outcome`; `League` has no residual.
- **Escape hatch, so a genuine fifth lane is never smuggled in as Market:** cross-lane composition returns `Comparison` / `Residual`, which need no new lane. Adding a real lane is a deliberate edit to `LANES` plus fixing every now-non-exhaustive `match` — visible, reviewable friction. That is what CLOSED is for.

### §1.2 Rejected members, and why (the closure criterion applied)

| Proposed | Rejected because | Lives instead as |
|---|---|---|
| `withheld` (Availability) | Derivable: `withheld ⟺ claim(value) < surface.required_claim_level`. Fails (b). | A projection at the `read_models` publication boundary. The same Measurement is published to a diagnostic surface and withheld from a decision surface **without storing two availabilities**. |
| `carried_forward` (Freshness) | A value whose `as_of` did not advance while `published_at` did is, to every consumer, exactly `DUE`. Fails (a). | Nothing. The shipped four-value set was already right. |
| `imputed` (Origin) | It is `DERIVED` (derivation = `impute_position_median`, and it re-runs). Its danger is that it substitutes for absent evidence. | `Availability.IMPUTED`. Passes (a) and (b) there: every consumer must branch on it, and the branch would otherwise require reading the derivation registry. |
| `Determinism` on the extractor spec | **Self-declared.** A row claiming `EXACT` for an LLM launders a nondeterministic read into a decision-eligible fact — with a green checkmark on it. | `Reproducibility`, **computed per fact** from `replicate_count` + `replicate_agreement`. k=1 mechanically yields `RECORDED`. Cutting cost visibly costs claim level instead of silently costing truth. |
| `VerificationKind` as a closed branch | Least-confident closure. | `Corroboration` is closed at five, but the §2.6 ceiling is a **table lookup**, so demoting it to an OPEN registry with a `claim_ceiling` column is a one-row change, no seam change. Escape hatch designed in. |

---

## §2. Kernel value types

### §2.1 Time

```python
@dataclass(frozen=True, slots=True)
class AsOf:
    effective: date        # world-time the fact is ABOUT
    known_at:  datetime    # wall-time we could have known it
    # A query is (effective <= E, known_at <= K). No row with known_at > K may enter a result.
```

### §2.2 Origin — four kinds, each carrying the field that makes it checkable

```python
SnapshotRef = NewType("SnapshotRef", str)   # "dgs1:<sha256>" — content address of raw BYTES
ReceiptRef  = NewType("ReceiptRef",  str)   # "dgr1:<blake2b-160>" — content address of a Receipt

@dataclass(frozen=True, slots=True)
class Blob:
    sha256:     str
    media_type: str      # SNIFFED from magic bytes — NEVER the offered filename
    byte_len:   int
    uri:        str      # app/data/media/blobs/<sha[0:2]>/<sha>.<ext>
    retained:   bool     # False after eviction -> recheck returns NOT_CHECKABLE

@dataclass(frozen=True, slots=True)
class Derived:                          # re-run it; if it no longer reproduces it is STALE
    origin: ClassVar = Origin.DERIVED
    derivation: DerivationRef           # OPEN key: exact callable + version
    inputs: tuple[ReceiptRef, ...]      # NON-EMPTY; refused at construction if empty

@dataclass(frozen=True, slots=True)
class Declared:                         # re-affirmable; a declared fact rots silently
    origin: ClassVar = Origin.DECLARED
    declared_by: str                    # non-empty
    declared_at: datetime
    reaffirm_after: timedelta | None    # None => never expires (a league rule)
    basis_ref: EvidenceRef | None = None

@dataclass(frozen=True, slots=True)
class Observed:                         # staleness is visible
    origin: ClassVar = Origin.OBSERVED
    observed_at: datetime               # ACQUISITION time, not run-completion time
    snapshot: SnapshotRef

@dataclass(frozen=True, slots=True)
class Extracted:                        # THE FOURTH KIND — a model read it out of a representation
    origin: ClassVar = Origin.EXTRACTED
    extraction: ExtractionRef           # ExtractionRun.run_id
    snapshot: SnapshotRef               # the bytes: screenshot, video, PDF, transcript
    locator: Locator                    # WHERE inside them — a human must be able to LOOK
    verbatim: str                       # the literal glyphs read, BEFORE normalization
    reproducibility: Reproducibility    # COMPUTED from replicate_count/agreement
    corroboration: Corroboration
    self_reported_confidence: float | None = None   # QUEUE PRIORITY ONLY. See §2.6.

Basis = Derived | Declared | Observed | Extracted

@dataclass(frozen=True, slots=True)
class Locator:
    kind: LocatorKind                   # OPEN registry key
    spec: Mapping[str, JsonScalar]
    #   image -> {page, bbox}                  bbox NORMALIZED 0..1, resolution-free
    #   video -> {stream, t_start_ms, t_end_ms, bbox?}
    #   text  -> {char_start, char_end}
    #   table -> {sheet, row, col}
    # THE EXTRACTOR OWNS THE MEANING. The kernel requires only that a stable locator exists —
    # otherwise adding video would be a seam change and the acceptance test fails.
```

**Why `extracted` is a fourth kind and not a flavor of the others.** An `observed` fact was *published* by a source; re-reading the bytes yields the same fact by construction. An `extracted` fact is a **claim about** bytes — the bytes are ground truth and the value is a fallible reading of them. It needs three trust properties simultaneously, which no other origin does:

- **re-runnable like `derived`** — but a differing re-run is *not necessarily* staleness; it may be sampling noise. So its verdict is `DISPUTED`, never `DRIFTED`. Calling stochastic disagreement "stale" is the same category error the RED's `test_s1b` names, and would train the operator to ignore the signal.
- **rots like `declared`** — the *interpretation* can be wrong even when the bytes never change.
- **staleness-visible like `observed`** — the media has a capture time, and the *extractor* can be superseded independently of the media. `observed_at` alone collapses both clocks and hides extractor drift entirely.

And one property none of the three have: **a locator**, so a human can look at the same pixels. `verbatim` is what makes it checkable by eye without re-running anything.

### §2.3 Receipt

```python
@dataclass(frozen=True, slots=True)
class Receipt:
    receipt_id: ReceiptRef              # DERIVED, never supplied: blake2b of canonical JSON
    basis: Basis                        # exactly one of four; the union IS the "one field" rule
    as_of: AsOf
    claim_ceiling: ClaimLevel           # the highest claim this evidence can support
    evidence: EvidenceRef | None        # None => ceiling cannot exceed DIAGNOSTIC
    calibration_ref: CalibrationRef | None   # REQUIRED iff calibration is CALIBRATED
    bound_by: ReceiptRef | None         # WHICH input capped the claim — the lattice is debuggable
    caveats: tuple[Caveat, ...] = ()

    def frontier(self, resolve: Callable[[ReceiptRef], "Receipt"]) -> tuple["Receipt", ...]:
        """Walk `inputs` transitively; return terminal nodes. Every one is Observed, Declared,
        or Extracted-with-a-retained-blob, or the chain was unconstructible."""
    def raw_bytes(self, resolve) -> tuple[Blob, ...]: ...
```

**The terminal guarantee.** Every chain, walked to its frontier, terminates only in nodes that are `Observed` (a `SnapshotRef` whose sha256 is recomputable from bytes on disk), `Declared` (a named human + timestamp — the honest terminal when no source exists, which is exactly the calendar-anchor case), or `Extracted` (a retained blob + locator).

**Depth and size.** `inputs` cites **vintage-level** receipts (one FeatureVintage → one receipt), never row-level. Chain depth is bounded by the layer count, so `frontier()` is cheap.

**Storage** reuses the append-only protocol already proven four times (`capture/fc_forward_capture_store.py:131-190`): validate-all-before-write → in-payload dedup (identical collapses, differing fails) → content-signature conflict check excluding the run clock → all-or-nothing write. Content addressing makes idempotence automatic: differing content is a different id.

### §2.4 Measurement — lane as a type parameter

```python
type Uncertainty = Interval | Uncalibrated

@dataclass(frozen=True, slots=True)
class Interval:
    lo: float; hi: float
    coverage: float                     # nominal level: 0.80, 0.95
    method: CalibrationRef              # registry key, WITH a receipt

@dataclass(frozen=True, slots=True)
class Uncalibrated:
    reason: Calibration                 # UNCALIBRATED | OUT_OF_COHORT | NOT_APPLICABLE

class Measurement[T: (int, float), L: Lane]:
    __slots__ = ("value","unit","uncertainty","lane","as_of","basis","claim","availability","caveats")
    __match_args__ = ("value","unit","lane","as_of","basis","claim")

    value: T
    unit: Unit                          # OPEN registry row; compared by IDENTITY at runtime
    uncertainty: Uncertainty            # never Optional — Uncalibrated(...) is first-class
    lane: type[L]                       # the tag class itself
    as_of: AsOf
    basis: Receipt                      # the OBJECT, resolved. A ref can dangle; an object cannot.
    claim: ClaimLevel
    availability: Availability          # PRESENT | IMPUTED only (absence is Unknown, §2.7)
    caveats: tuple[Caveat, ...]

    def __init__(self, *_a, **_k) -> NoReturn:
        raise MeasurementConstructionError(
            "Measurement has no public constructor. Mint one with observe(), derive(), "
            "declare() or extract() — each REQUIRES the evidence its origin needs.")

    def __add__(self, o: "Measurement[T, L]") -> "Measurement[T, L]": ...
    def __sub__(self, o: "Measurement[T, L]") -> "Measurement[T, L]": ...
    def __lt__(self, o: "Measurement[T, L]") -> bool: ...    # refuses cross-lane

    def _require_same(self, o: object) -> "Measurement[T, L]":
        if not isinstance(o, Measurement): raise LaneError(...)
        if o.lane is not self.lane:
            raise LaneError(f"lane violation: {self.lane.key} {self.unit.symbol} vs "
                            f"{o.lane.key} {o.unit.symbol}. "
                            f"Lanes compose through bridge()/residual(), never through arithmetic.")
        if o.unit is not self.unit: raise UnitError(...)
        return o
```

**Why a tag class and not `Literal["model","market"]` or an Enum.** A `Literal` or `Enum` member is a *value*, and a value can be put in a field — which is empirically how `SpreadBar.tsx:24` and `player_value_object.py:24` got here. A tag class has no value form to smuggle. `SpreadBar` also *defaults* `lane` to `"model"`, so a market value rendered by a forgetful caller silently inherits model styling. **A type parameter has no default.**

**Two-layer enforcement, runtime-primary.** No Python type checker runs in this repo (verified: mypy and pyright are not importable in the venv; `pyproject.toml` selects only `E4,E7,E9,F,I`; CI has no typecheck step). So the static arm is dormant until mypy lands. `__lt__` refusing cross-lane is the type-level half of "a sort by desirability is a verdict with a sort key" — you cannot build a mixed list and `sorted()` it.

**Unit is checked at runtime by identity, not by a third type parameter.** Two type params keep signatures readable for a user new to syntax; a third buys zero today with no checker installed. `Unit` carries `symbol`, `dimension`, and `definition_ref` — the PPG=ALL-GAMES ruling (2026-08-19) is exactly a unit-definition problem, and identity comparison catches per-game-played vs per-game-in-season on the first call.

### §2.5 The four smart constructors — the only path to a Measurement

Each demands its origin's checkable field as a keyword-only, non-defaulted parameter. Passing `basis=None` is not a mistake you can make, because `basis` is not a parameter of anything.

```python
def observe[T, L: Lane](value: T, *, unit: Unit, lane: type[L], snapshot: SnapshotRef,
                        observed_at: datetime, as_of: AsOf,
                        uncertainty: Uncertainty = Uncalibrated(Calibration.UNCALIBRATED),
                        ) -> Measurement[T, L]: ...

def derive[T, L: Lane](value: T, *, unit: Unit, lane: type[L], derivation: DerivationRef,
                       inputs: tuple[Receipt, ...],       # runtime-refused if empty
                       as_of: AsOf, uncertainty: Uncertainty) -> Measurement[T, L]: ...

def declare[T, L: Lane](value: T, *, unit: Unit, lane: type[L], declared_by: str,
                        declared_at: datetime, reaffirm_after: timedelta | None,
                        as_of: AsOf) -> Measurement[T, L]: ...    # ceilings at DIAGNOSTIC

def extract[T, L: Lane](value: T, *, unit: Unit, lane: type[L], snapshot: SnapshotRef,
                        locator: Locator, extraction: ExtractionRef, verbatim: str,
                        replicate_count: int, replicate_agreement: float,
                        corroboration: Corroboration, as_of: AsOf,
                        uncertainty: Uncertainty) -> Measurement[T, L]: ...
    # reproducibility is COMPUTED from (replicate_count, replicate_agreement). Not a parameter.
    # RAISES if value is not None and locator is absent: a value with no span is not evidence.
```

**The deserialization hole — the bypass that actually matters.** Everything durable here is SQLite or JSON.

```python
@classmethod
def from_json(cls, blob: Mapping, *, receipts: ReceiptStore) -> "Measurement[T, L]":
    """RE-VERIFIES. Resolves basis from the store, recomputes its content address, walks the
    frontier. A dangling ref, a hash mismatch, or a frontier node that is not a valid terminal
    RAISES. Never trusts the blob."""
```

Fail-closed, matching `features/feature_source.py:100-104` ("refusing to serve unverified features"). Ship `dg receipts fsck` alongside: walk every stored Receipt, recompute `payload_sha256` against bytes on disk, so a deleted source file surfaces as a report rather than as a silently-unprovable number.

### §2.6 The extracted claim ceiling — the fail-closed teeth

```python
ORIGIN_CEILING: Mapping[Origin, ClaimLevel] = {
    Origin.OBSERVED:  ClaimLevel.DECISION_SUPPORTED,
    Origin.DERIVED:   ClaimLevel.DECISION_SUPPORTED,
    Origin.DECLARED:  ClaimLevel.DIAGNOSTIC,      # unverifiable by machine
    Origin.EXTRACTED: ClaimLevel.DIAGNOSTIC,      # see the table below
}
```

`extracted` ceiling = `EXTRACTED_CEILING[(reproducibility, corroboration)]`, a **table lookup**, never a code branch:

| reproducibility | corroboration | ceiling |
|---|---|---|
| any | `none` or `self_consistent` | `DESCRIPTIVE` |
| `recorded` | any | `DESCRIPTIVE` |
| `reproduced` / `deterministic` | `human_affirmation` / `cross_source` / `second_extractor` | `DIAGNOSTIC` |
| `reproduced` / `deterministic` | + an `EvidenceRecord` ratifying the (field × layout-family) pair | `REPLICATION_CANDIDATE` |
| — | — | `DECISION_SUPPORTED` is **unreachable** from `extracted` alone |

Three rulings baked in here:

1. **A human confirming ONE reading never promotes to `DECISION_SUPPORTED`.** It does not establish that the extractor read the other 400 correctly. Verification is per-row evidence; the ceiling is a class property. Adjudication is therefore keyed on **(field × layout family)** — `shape_sha256` — not per fact, which is also what makes the one-human bottleneck tractable.
2. **A second sample of the same model is NOT independence.** That is reproducibility, already counted.
3. **`self_reported_confidence` is structurally unreachable from the composer.** A VLM's confidence is a number the extractor invents about itself; letting it raise a claim means the thing being trusted decides how much it is trusted. It is **review-queue priority only** — the direct generalization of the already-ratified identity ruling ("Never auto-promote. Confidence bands survive as review-queue priority"). Enforced by a test that greps the composer's import closure.

**Reproducibility is computed, never asserted:**

```python
def reproducibility_of(*, replicate_count: int, replicate_agreement: float,
                       extractor_is_pure: bool) -> Reproducibility:
    if extractor_is_pure: return Reproducibility.DETERMINISTIC   # PROVEN by re-running in CI
    if replicate_count >= 2 and replicate_agreement >= 1.0: return Reproducibility.REPRODUCED
    return Reproducibility.RECORDED
```

k=1 mechanically yields `RECORDED` → `DESCRIPTIVE`. Cost-cutting visibly costs claim level instead of silently costing truth. Disagreement across k samples emits `value=None` with caveat `extraction_unstable` — never a coin-flip winner.

### §2.7 Known / Unknown

```python
@dataclass(frozen=True, slots=True)
class Known[T: (int, float), L: Lane]:
    measurement: Measurement[T, L]

@dataclass(frozen=True, slots=True)
class Unknown:
    availability: Availability   # ABSENT | NOT_APPLICABLE | OUTSIDE_AS_OF
    basis: Receipt               # WE KNOW WE DON'T KNOW, and here is the evidence
    as_of: AsOf
    lane: type[Lane]             # an absence still belongs to a lane
    caveats: tuple[Caveat, ...] = ()   # the WHY. Open registry codes.

type Maybe[T: (int, float), L: Lane] = Known[T, L] | Unknown
```

`Unknown` carrying a `Receipt` is the load-bearing part. "FantasyCalc published no volatility for this player on this date" is a **fact with an origin** — `observed`, snapshot-backed. Today it is a bare status string with no link to the bytes that prove it (`fc_forward_capture_store.py:52-54`).

**Operations — deliberately missing `value_or(default)`.** A default is a fabricated value.

```python
def map[T, U, L: Lane](m: Maybe[T, L], f, *, derivation, unit) -> Maybe[U, L]: ...
def combine[L: Lane](*ms: Maybe[Any, L], derivation, unit) -> Maybe[float, L]: ...
    # ALL Known  -> Known, claim = min(input claims, derivation's evidence ceiling)
    # ANY Unknown -> Unknown, basis = a derived receipt citing EVERY input receipt (absences too)
def require[T, L: Lane](m: Maybe[T, L], why: str) -> Measurement[T, L]: ...
    # raises. Internal invariants ONLY. A contract test forbids it under serve/.
```

Consumers use structural pattern matching, so a new `Availability` member surfaces as a non-exhaustive `match` — which is what "closed vocabulary, code branches on it" is supposed to feel like.

### §2.8 Series — the right edge is the last LOOK

```python
@dataclass(frozen=True, slots=True)
class Point[T: (int, float), L: Lane]:
    at: AsOf
    observation: Maybe[T, L]     # a gap is an EXPLICIT Unknown point, never an absent index

@dataclass(frozen=True, slots=True)
class Series[T: (int, float), L: Lane]:
    points: tuple[Point[T, L], ...]
    lane: type[L]
    unit: Unit
    right_edge: AsOf             # THE LAST CAPTURE ATTEMPT — not the last Known value
    basis: Receipt
    window: SeriesWindow         # named, e.g. ("newest_n", 30) — a window is a claim

    @property
    def is_renderable(self) -> bool: ...          # >= 2 Known points
    @property
    def unrenderable_reason(self) -> Availability | None: ...   # WHY, not just None
    @property
    def last_known(self) -> Point[T, L] | None: ...
    @property
    def edge_gap(self) -> timedelta: ...          # right_edge - last_known.at

    def as_of(self, t: AsOf) -> "Series[T, L]":
        """Point-in-time truncation. Drops every point observed after t AND moves the edge back:
        right_edge = min(self.right_edge, t). Never widens it."""
```

`build_series` validates fail-closed:

1. **Strictly ascending, no duplicates.** A duplicate `as_of` **raises `SeriesOrderError`**. The repo currently last-write-wins silently via a dict (`what_changed/daily_diff.py:424`); on an append-only store a genuine duplicate means two captures disagree — a conflict, not a tie-break, and the same stance `model_forward_capture_store.py:206-218` already takes. **Build precondition:** run a read-only duplicate-`(player, date)` scan of both forward-capture joinable tables (57-day market lane, 56-day model lane) and land the count *before* the invariant. If non-zero, the duplicates are a real conflict that was being hidden.
2. **Homogeneous lane and unit.** Concatenating two Series of different lanes is refused — the Series-level form of "model and market never blend."
3. **Right-edge invariant.** No point at or after `right_edge`'s successor; `right_edge` never after the query's `as_of`. Otherwise a backtest at 2024-09-01 renders an edge marker at today's date and leaks the present into the past. **This invariant exists nowhere in the repo today.**
4. **Right edge = last LOOK.** If the newest three points are `Unknown(ABSENT)`, `last_known` is four days back, `right_edge` is today, `edge_gap == 3 days`. This corrects a live defect: `frontend/src/ui/SeriesSlot.tsx:81` computes `lastDrawn` from the last non-null point and uses it for **both** `data-series-endpoint` (correct) and `data-hard-right-edge` (wrong). They coincide today only because the producer never emits trailing nulls. Once absences become explicit `Unknown` points they diverge, and the surface would otherwise imply we have not looked since the last value.
5. **A short Series is still a Series.** `len(points) < 2` yields an object whose `unrenderable_reason` is set. The repo currently drops the player entirely, so the surface can only say "pending" and never says why.

### §2.9 Crossing lanes — the only two legal products

```python
@dataclass(frozen=True, slots=True)
class Comparison:
    """Model vs Market. NO magnitude. Nothing subtractable. Not a Measurement — it has no lane,
    so nothing downstream can add it to anything."""
    subject: CanonicalId
    model_direction:  DirectionLabel   # CLOSED: HIGH | MID | LOW | UNCERTAIN, on the MODEL's scale
    market_direction: DirectionLabel   # CLOSED: same labels, on the MARKET's own scale
    agreement: AgreementLabel          # CLOSED: AGREE | DIVERGE_MODEL_HIGH | DIVERGE_MARKET_HIGH
                                       #       | UNDETERMINED
    claim: ClaimLevel                  # <= DESCRIPTIVE. A comparison never raises a claim.
    basis: Receipt                     # cites BOTH input receipts + the named bridge
    caveats: tuple[Caveat, ...]

@dataclass(frozen=True, slots=True)
class Residual:
    """Model vs Outcome. The model-evaluation record. Also not a Measurement."""
    subject: CanonicalId
    predicted: Measurement[float, Model]
    actual:    Measurement[float, Outcome]
    error: float
    spec_hash: Sha256
    basis: Receipt

def bridge(model: Measurement[float, Model], market: Measurement[float, Market], *,
           model_scale: Scale, market_scale: Scale) -> Comparison | Unknown: ...
def residual(p: Measurement[float, Model], a: Measurement[float, Outcome]) -> Residual: ...
```

This is the promotion of `trade_lab/cross_lane_review.py:5-8` — "each lane is reduced to a direction label on its *own* scale; model and market magnitudes are never subtracted" — from a docstring to a type. It is the exact discipline `services/market_overlay_service.py:178-186` violates today by computing `delta = round(m_pct - k_pct, 3)` and writing it onto `PlayerValueObject.market_overlay`, whence it ships to David in `league_opportunity_latest.json` as `model_minus_market_delta: 0.683`.

`Comparison` and `Residual` are not `Measurement[L]`, so neither can be summed back into a model value. **This is why Lane never needs relaxing for model evaluation: you need a type to land in when you cross, and that type is the audit record.**

### §2.10 Recheck — report, never repair

```python
@dataclass(frozen=True, slots=True)
class Recheck[T]:
    verdict: Verdict
    expected: T
    actual: T | None
    @property
    def stale(self) -> bool: return self.verdict is Verdict.DRIFTED

@dataclass(frozen=True, slots=True)
class AuditReport:
    checked: tuple[Recheck, ...]
    stale_facts: tuple[ReceiptRef, ...]
    disputed_facts: tuple[ReceiptRef, ...]
    rewritten: tuple[()] = ()     # TYPED EMPTY — a rewrite is not representable

def recheck[T](m: Measurement[T, Any], *, actual: T | None, now: AsOf) -> Recheck[T]: ...
```

`.stale`, `.expected`, `.actual`, `.stale_facts`, `.rewritten == []` are shaped so the in-flight RED's D1/D1b/S1/S1b pass unchanged. A `Declared` fact returns `NOT_CHECKABLE`, never `DRIFTED` — reporting it stale is a category error that trains the operator to ignore the signal (`test_s1b`).

### §2.11 Caveat

```python
@dataclass(frozen=True, slots=True)
class Caveat:
    code: CaveatCode                # OPEN REGISTRY KEY — replaces list[str] everywhere
    severity: Severity
    caps_at: ClaimLevel | None      # meaningful only for LIMITATION
    detail: Mapping[str, JsonScalar]   # STRUCTURED — never prose with data baked in
    subject: Ref
```

This retires the free-text state transport at `pvo_assembler.py:150-151`, where a state axis is appended as `f"dynasty_value_score unavailable: {engine} not yet validated..."` and later removed by `c.startswith("dynasty_value_score unavailable:")` at `:374` and `:386` — a wording change silently breaks the strip. It also retires the two disjoint `SAFE_TOKENS` frozensets in the serve layer (`league_pulse_models.py:22`, `roster_audit_models.py:84`) whose intersection is **empty**.

---

## §3. The trust plane — cross-cutting, NOT a layer

**The cycle, named and fixed before either layer is written.** An extractor is a model: it needs a hashed spec, an evaluation, a promotion gate, an active pointer. But `modeling` sits above `sources`, and extraction sits below it. Importing the Model Trust Plane from `modeling` would create `extraction → modeling → features → identity → sources`.

**Ruling:** the trust plane goes in `kernel/trust.py` as *protocols*, exactly as `Measurement` and `Receipt` were lifted. `modeling` implements them for predictors; `extraction` implements them for extractors. Neither imports the other.

```python
class HashedSpec(Protocol):
    @property
    def spec_hash(self) -> Sha256: ...      # canonical JSON -> sha256. THE identity.

class PromotionChain(Protocol):
    """Candidate -> EvalReport -> PromotionReceipt -> ActivePointer.
    A training/extraction RUN creates candidates only and CANNOT mutate the active pointer.
    Serving REFUSES an artifact whose spec_hash is not the promoted one for its subject."""

@dataclass(frozen=True, slots=True)
class EvaluationReport:
    subject: EvidenceSubject
    metrics: Mapping[MetricId, float]       # OPEN — rmse/spearman/hallucination_rate are ROWS
    family_diagnostics: Mapping[str, JsonScalar]   # ridge_alpha lands HERE, not on the seam
    ceiling: ClaimLevel
```

---

## §4. Boundary types — the nine seams

### B0. `sources → identity` : `RawSnapshot`

```python
@dataclass(frozen=True, slots=True)
class RawSnapshot:
    snapshot_id: SnapshotRef
    source_id: SourceId          # OPEN catalog key. The kernel names no provider.
    stream_id: StreamId
    blob: Blob                   # BYTES. Unparsed. JSON, CSV, PNG, MP4 alike.
    shape_sha256: str            # from the profiler registry — "have I seen this SHAPE before?"
    lane: type[Lane]             # INHERITED from the catalog row, IMMUTABLE downstream
    role: SourceRole             # INHERITED. `prohibited_current_phase` makes extraction REFUSE.
    captured_at: datetime        # ACQUISITION time
    effective_at: datetime | None  # what instant the CONTENT depicts; often unknown
    published_at: datetime | None  # what the SOURCE claims; None means unknown, NEVER inferred
    rows_claimed: int | None
    duration_ms: int | None = None   # present from day one, None for stills. VIDEO NEEDS NO SEAM.
    frame_count: int | None = None
    page_count: int | None = None
    basis: Receipt               # origin in {OBSERVED, DECLARED}. Never EXTRACTED — that is downstream.

class SourceAdapter(Protocol):
    source_id: SourceId
    def acquire(self, ctx: AcquisitionContext) -> RawSnapshot | Unknown: ...
    def parse(self, snap: RawSnapshot) -> tuple[Observation, ...]: ...
```

**Bytes are stored before parsing.** This is the one-time change that makes screenshots free. The store, the streaming hasher, and the immutability guard at `sources/pff_intake.py:255-260, 665-672` already work on an MP4 unmodified. What must generalize is the **profiler**, which is CSV-specific in exactly three places (`:334` hardcodes `.csv`; `:273-274` opens text mode; `:263-271` hashes a CSV header). If `_profile_csv` were merely made lenient, `_schema_sha256([])` returns `sha256("")` for **every** media payload, so all media would collide on one schema identity.

```python
Profiler = Callable[[Path], PayloadProfile]
PROFILERS: dict[str, Profiler] = {}          # OPEN registry, keyed by SNIFFED media type
def profile(path: Path) -> PayloadProfile:
    mt = sniff(path)                         # MAGIC BYTES. Never the filename.
    try: return PROFILERS[mt](path)
    except KeyError: raise UnprofilableMedia(mt)   # fail closed; unknown type quarantines
```

Sniffing is not optional: this repo has already measured Sleeper serving **PNG bytes under `.jpg` URLs** (`scripts/build_player_asset_cache.py:53-59`). The `text/csv` profiler must be a **byte-identical** move of the governed `"\n".join(header)` algorithm, guarded by a test against the real ledger values, not a synthetic fixture.

**Storage layout** (lifted from `sources/schedules_capture.py:24-26, 269-293`, which already solved this with hard links and documents the in-place-write hazard):

```
app/data/media/blobs/<sha[0:2]>/<sha>.<ext>     immutable content store, SHARDED
raw/<source>/<date>/<sha>.<ext>                 HARD LINK — human-navigable path preserved
app/data/media/derived/<spec_hash>/<sha>.<ext>  preprocessed frames, OCR text (regenerable)
app/data/media/responses/<sha[0:2]>/<sha>.json  raw provider responses (KBs)
```

**Hard prohibition:** extraction may never read from an id-keyed media store. `build_player_asset_cache.py:101,133` writes `{sleeper_id}.jpg` with `write_bytes` — a re-fetch destroys the exact bytes any prior extraction was anchored to. That is a cache, not a vault.

*Consumer may not assume:* that it parses; that the schema matches the last snapshot; that `published_at` exists; that rows are unique, complete, or ordered; that a paid source succeeded. **Degradation:** missing → `Unknown(ABSENT)` naming the last successful `snapshot_id`, never an empty list. Unparseable → still stored; parse failure is an identity-layer state, never a capture failure. That is what makes replay possible after an adapter fix.

### B1. `extraction → identity` : `ExtractionRun` → `ExtractedMention`

Extraction is its own layer between `sources` and `identity`, because **a blurry screenshot has two independent failure modes — misread the glyphs, and misresolve the name — and collapsing them makes both invisible.** Extraction emits mentions; identity resolves them; the resolution is a separate append-only fact with its own confidence.

```python
@dataclass(frozen=True, slots=True)
class ExtractorSpec:                  # implements HashedSpec
    extractor_id: ExtractorId         # OPEN registry key
    family: ExtractorFamily           # OPEN: "rule" | "ocr" | "vlm" | "llm" | ...
    model_ref: str                    # FULLY QUALIFIED DATED id, never a floating alias
    prompt_sha256: str | None         # of the FULLY RENDERED prompt incl. system + exemplars
    output_schema_sha256: str
    decoding: Mapping[str, JsonScalar]     # temperature, top_p, seed, max_tokens, stop
    preprocess_version: str           # decoder lib + version + resize filter + colorspace policy
    params: Mapping[str, JsonScalar]  # OPEN. video adds params["frame_sampling"] HERE.
    k_samples: int                    # per-field; drives Reproducibility
    test_gate: str                    # pytest node proving the declared purity claim

@dataclass(frozen=True, slots=True)
class ExtractionRun:
    run_id: ExtractionRef             # sha256(blob_sha + spec_hash + attempt_ordinal)
    blob_sha256: str                  # the INPUT
    spec_hash: Sha256
    preprocessed_sha256: str          # the bytes ACTUALLY SENT — where determinism really dies
    response_blob_sha256: str | None  # raw provider response, archived as its own blob
    started_at: datetime; finished_at: datetime
    status: RunStatus                 # CLOSED: ok | refused | failed
    facts: tuple[ExtractedFact, ...]

@dataclass(frozen=True, slots=True)
class ExtractedMention:               # what identity chews on. NOT a player yet.
    surface: str                      # "B. Robinson"
    context: Mapping[str, str]        # {"team": "ATL"} — also extracted, also located
    locator: Locator
```

**The identity of an extracted fact is `(blob_sha256, field_path, spec_hash)`.** A new extractor version therefore **cannot overwrite** — it appends a row with a different key. Drift stops being silent and becomes *a visible disagreement between two rows over the same span of the same blob*. This is the single most important property in the extraction design, and the exact inverse of the headshot cache.

**Canary corpus, re-run on every spec change AND on a schedule.** The schedule is not optional: it is the only thing that catches provider-side drift under a pinned model id, where nothing on our side changed. **A canary failure demotes the active pointer** — it does not warn. Fail-closed, matching the shipped `failure_behavior="fail_closed"` vocabulary.

**Supersession is explicit and append-only:** `Supersession(loser, winner, reason, adjudication_ref)`. Never delete. **The archive is not the view** — read models resolve "currently-preferred extraction for this blob+field as of T" through a versioned precedence function (`human_adjudication > deterministic > reproduced > recorded`, then newer promoted spec), whose version goes in the Receipt.

*Consumer may not assume:* that the extractor read correctly; that a re-run reproduces; that `self_reported_confidence` means anything; that a mention resolves to a player.

### B2. `identity → features` : `Resolution`

```python
CanonicalId = NewType("CanonicalId", str)   # OPAQUE ULID. Carries NO name, position, or year.

@dataclass(frozen=True, slots=True)
class SourceKey:
    source_id: SourceId; namespace: str; native_id: str   # ("pff", "pff_id", "12345")

@dataclass(frozen=True, slots=True)
class Resolution:
    source_key: SourceKey
    canonical_id: CanonicalId | None    # None iff state is not RESOLVED
    state: IdentityState                # CLOSED: RESOLVED | AMBIGUOUS | UNRESOLVED | SOURCE_ID_COLLISION
    candidates: tuple[Candidate, ...]   # non-empty iff AMBIGUOUS
    basis: MatchBasis                   # CLOSED: EXACT_ID | CROSSWALK | NAME | NAME_TEAM
                                        #       | NAME_JERSEY | HUMAN_OVERRIDE
    confidence: float | None            # REVIEW-QUEUE PRIORITY. Never a promotion.
    valid_from: date; valid_to: date | None   # world-time validity
    asserted_at: datetime                      # belief-time — the bitemporal second axis
    superseded_by: ReceiptRef | None           # corrections APPEND, never overwrite
    receipt: Receipt

class Crosswalk(Protocol):
    def resolve(self, key: SourceKey, *, effective: date, known_as_of: datetime) -> Resolution: ...
    def aliases(self, cid: CanonicalId, *, known_as_of: datetime) -> tuple[SourceKey, ...]: ...
```

**One `resolve()`, not `resolve_sleeper_id` + `resolve_pff_id` + `resolve_<next>_id`.** A new source's ids are **crosswalk rows**, not a wide-table field. Set `extra="forbid"` on every identity type: `PlayerIdentity` currently *silently drops* an unknown source id under pydantic's default `extra="ignore"`, which is worse than a hard failure — the mapping vanishes with no error and surfaces later as a coverage gap of unknown cause.

**`dg_id` is demoted to a display alias.** `generate_dg_id` derives `josh_allen_qb_1996` from name + position + birth year, and collisions are resolved by appending `_2`/`_3` **based on input order** — so adding a source can rename an existing player's canonical id, and a WR→TE reclassification mints a new id for the same human. Point-in-time truth is unachievable on an id that is not stable under source addition.

**Never rewrite history.** Old rows resolve through the crosswalk: register `SourceKey("legacy_dg", "dg_id", "josh_allen_qb_1996")` and `SourceKey("legacy_gsis", "gsis", "00-0030061")` as two rows pointing at the same new `CanonicalId`, `valid_from` = the row's own era. This is also how the mixed-namespace bug shipping today in `league_opportunity_latest.json` — where `cards[].asset.dg_player_id` holds both `00-0030061` and `sam_roush_te` — becomes *readable* rather than destroyed.

**Discovery and resolution are different types** (the shipped `identity/college_prospect_identity.py:508-524` pattern): `score_candidate` returns a `MatchCandidate` carrying `match_score`, `score_breakdown`, `matcher_algorithm_version` and is discovery-only; resolution is deterministic-only. This kills the live 5-to-1 contradiction where `identity/__init__.py:171-178` stamps `verification_status="VERIFIED"` on a 0.80 (and 0.60) SequenceMatcher score while five other modules prohibit fuzzy resolution outright. **The same split governs `extracted`** — extraction is fuzzy matching over pixels.

*Consumer may not assume:* that every row resolves; that `canonical_id` is parseable, sortable, or derivable from a name; that today's mapping held last season; that two sources' native ids share a namespace. **Degradation:** unresolved rows are **CARRIED** with `canonical_id=None`, never dropped and never keyed on the source-native id as a fallback — the rule already ratified at `app/services/morning_tape_artifact.py:3-6`.

### B3. `features → modeling` : `FeatureVintage` — **the redesigned seam**

This is the seam the six analyses broke. It is redesigned, not papered over.

**The measured breakage.** The vintage is 2,741 rows × 33 columns at grain `(player_id, feature_season)`. Career history is three hand-materialized lag columns at a **fixed depth of 2** (`ppg_t_minus_1`, `ppg_t_minus_2`, `snap_share_t_minus_1`) plus three `*_available` sentinels. Census: **959 players, career lengths 1–7, and 60 players carry 7 seasons of which 5 are structurally invisible.** Variable length is the norm, not an edge case.

Three independent walls, any one fatal to a sequence model:
- **Schema.** Depth *k* needs 2*k* new columns in a set pinned by exact-equality tests with REQUIRED semantics. Verified: `validate_position_feature_contract('WR', WR_set - {'tprr'})` raises `missing required features: ['tprr']`. **"Old vintages stay readable" already FAILS today.**
- **Precedent.** The repo already ran this experiment. Adding NGS columns raised `KeyError` in the QB-1 walk-forward and `missing required columns` in TE training; the fix was a permanent parallel `ENGINE_B_OPTIONAL_FEATURES_BY_POSITION` mapping, and it cost 23 production files.
- **Shape.** Consumption is strictly `(n, p)`: `train_df[cols] → SimpleImputer(median) → StandardScaler → ridge.fit(X.to_numpy())`. A sequence needs ragged `(n, T_i, p)`. A CSV cell cannot hold a list. And **median-imputing an absent season does not fill a missing measurement — it fabricates a career** for a player who was not in the league.

**THE ROOT CAUSE: the period axis lives in column names.** `ppg_t_minus_1` is not a feature — it is a feature *plus a query*. Baking the query into storage is what makes lag depth a schema change, makes old vintages unreadable, and makes sequences inexpressible.

**THE FIX: move the period axis out of the names and into the data.**

```python
class FeatureShape(StrEnum):        # CLOSED. Code branches on it.
    SCALAR_PER_ENTITY = "scalar_per_entity"
    PER_ENTITY_PERIOD = "per_entity_period"

@dataclass(frozen=True, slots=True)
class FeatureDefinition:            # OPEN registry row — grows forever
    feature_id: FeatureId           # "ppg" — NEVER "ppg_t_minus_1"
    shape: FeatureShape
    unit: Unit
    lane: type[Lane]                # a Market-lane definition CANNOT enter a model FeatureSet
    computed_from: tuple[StreamId, ...]
    null_policy: NullPolicy         # CLOSED: FORBIDDEN | ALLOWED_EXPLICIT | IMPUTED_DECLARED
    derivation: DerivationRef
    definition_hash: Sha256
    claim_ceiling: ClaimLevel

@dataclass(frozen=True, slots=True)
class FeatureSetVersion:
    version_id: Sha256              # content hash of sorted definition_hashes
    definitions: tuple[FeatureDefinition, ...]   # OLD VINTAGES STAY SELF-DESCRIBING

@dataclass(frozen=True, slots=True)
class FeatureVintage:
    vintage_id: Sha256
    feature_set_version: FeatureSetVersion
    as_of: AsOf                     # no row with known_at > as_of.known_at is inside
    frame: LongFrame                # parquet columns:
                                    #   entity_id, period, feature_id, value, observed_at, origin_ref
    coverage: Coverage
    receipt: Receipt

    def definitions(self) -> tuple[FeatureDefinition, ...]: ...

    def as_tabular(self, spec: "TrainingSpec") -> TabularBundle:
        """Pivot to (n, p). LAGS ARE DERIVED HERE from spec.lag_depth.
           Changing lag depth is a NEW TrainingSpec, not a new column."""

    def as_sequence(self, spec: "TrainingSpec") -> SequenceBundle:
        """Ragged (n, T_i, p) + an explicit presence MASK."""

@dataclass(frozen=True, slots=True)
class SequenceBundle:
    entity_ids: tuple[CanonicalId, ...]
    values: tuple[NDArray, ...]     # each (T_i, p)
    mask:   tuple[NDArray, ...]     # each (T_i,) bool — WAS THE ENTITY PRESENT THAT PERIOD
    periods: tuple[tuple[int, ...], ...]
    feature_order: tuple[FeatureId, ...]
    # ABSENCE IS A MASK BIT, NEVER AN IMPUTED MEDIAN.
```

Both readers consume the **same** vintage. Ridge and a GRU read one artifact.

**And the smallest high-value change in the whole spec — superset-tolerant contracts:**

```python
def resolve_features(position: str, spec: "TrainingSpec", available: Collection[str]
                     ) -> ResolvedFeatures:
    """Ask 'are the features I NEED present?' — never 'are EXACTLY these present?'.
       Missing spec-required -> refuse and NAME them.
       Missing non-selected  -> record as absent, do not raise.
       Extra                 -> ignored, UNLESS cross-position-exclusive (that still refuses)."""
```

This makes old vintages readable forever and dissolves the required/optional duplication the NGS incident forced. The cross-position-exclusivity check must survive unchanged — it is catching a real wrong-constant bug (the QB median CPOE written into 2,485 mostly-non-QB rows).

*Consumer may not assume:* that every entity is present; that a feature is non-null; that an unknown `feature_id` returns None (it raises); that two vintages are comparable unless `feature_set_version` matches exactly. **Degradation:** absent feature → `Unknown`, consumable only through `null_policy=IMPUTED_DECLARED` whose imputation constant lands in the Prediction's receipt. This closes the sharpest live defect in the repo: `app/services/engine_b_service.py:147` builds the row with `.get(f)` so a missing feature becomes `None`, then `:150` `imputer.transform` fills it with the training mean — a 40%-complete vector produces a number indistinguishable from a complete one.

### B4. `modeling → decision` : `Prediction | Refusal`, `ModelArtifact`

```python
@dataclass(frozen=True, slots=True)
class TrainingSpec:                 # implements HashedSpec. Its DIGEST is the model's identity.
    family_id: FamilyId             # OPEN key: "ridge" | "hgb" | "seq_gru" | ...
    hyperparameters: Mapping[str, JsonScalar]      # alpha lives HERE
    feature_set_version: Sha256
    feature_selector: FeatureSelector
    target: TargetDefinition
    lag_depth: int | Literal["full_history"]       # a QUERY parameter, not a schema fact
    preprocessing: tuple[PreprocessStep, ...]      # MOVED OFF THE HARNESS, INTO THE SPEC
    split: SplitPolicy
    training_cutoff: date           # THE point-in-time anchor. NON-OPTIONAL.
    cohort: CohortFilterId
    seed: int

@dataclass(frozen=True, slots=True)
class ModelArtifact:
    artifact_id: Sha256
    spec_hash: Sha256
    family_id: FamilyId
    payload_uri: str                # a DIRECTORY — never assume one .pkl
    payload_sha256: Sha256          # hash of the directory MANIFEST
    serializer_id: SerializerId     # OPEN: pickle | joblib | onnx | safetensors | torchscript
    input_contract: InputContract   # input_kind + feature_order + dtypes
    output_contract: OutputContract
    fit_diagnostics: Mapping[str, JsonScalar]      # ridge coefficients live HERE
    trained_at: AsOf
    eval: EvaluationReport          # the CEILING on any claim from this artifact
    receipt: Receipt

class ModelFamily(Protocol):        # THE seam. Closed by SHAPE, open by REGISTRY.
    family_id: FamilyId
    input_kind: InputKind           # CLOSED: TABULAR | SEQUENCE — this is what code branches on
    def fit(self, spec: TrainingSpec, bundle: FeatureBundle) -> ModelArtifact: ...
    def load(self, artifact: ModelArtifact) -> "Predictor": ...
    def serialize(self, fitted: object, dest: Path) -> tuple[str, Sha256]: ...

class Predictor(Protocol):
    spec_hash: Sha256
    def predict(self, bundle: FeatureBundle) -> tuple["Prediction | Refusal", ...]: ...

@dataclass(frozen=True, slots=True)
class Prediction:
    subject: CanonicalId
    label: LabelId
    horizon: Horizon
    value: Measurement[float, Model]        # lane is Model BY TYPE
    spec_hash: Sha256
    feature_vintage_id: Sha256
    predicted_as_of: AsOf                   # == the vintage's as_of. NOT wall clock.

@dataclass(frozen=True, slots=True)
class Refusal:                              # A DISTINCT TYPE. Not a dict you can .get() to 0.0.
    subject: CanonicalId
    reason: RefusalReason   # CLOSED: NO_MODEL_FOR_COHORT | FEATURES_INCOMPLETE | ENTITY_ABSENT
                            #       | OUT_OF_SUPPORT | ARTIFACT_UNAVAILABLE
    caveats: tuple[Caveat, ...]
    receipt: Receipt
```

**Three deletions this forces, each a real edit:**
- `ridge_alpha: float` and `retrain_mode: Literal["refit_per_fold_fixed_alpha", ...]` come **off** `BacktestResult` into `hyperparameters` / `family_diagnostics`. A gradient-boosted tree cannot produce a valid `BacktestResult` today without lying about alpha.
- `market_source: Literal["fc_native","dp_archive","ktc_community_csv","unavailable"]` becomes `comparators: tuple[ComparatorResult, ...]` keyed by an OPEN source id.
- `engine_used: str` disappears from PVO, replaced by `artifact_id` + `spec_hash`. The two live consumers that branch on the string (`app/api/routes/roster_audit_models.py:264`, `universe_pvo_batch.py:32`) ask `claim` instead. **Land additively** — add `artifact_id` + `claim` first, migrate the branches, regenerate the frontend zod validators, remove the field last.

*Consumer may not assume:* that the model beats a baseline (only `eval.baseline_comparison` says); that every entity has a prediction; that predictions from different `spec_hash`es are on the same scale or comparable; that a horizon means the same thing across specs.

### B5. `league → decision` : `LeagueContext`

```python
@dataclass(frozen=True, slots=True)
class LeagueContext:
    league_id: LeagueId
    as_of: AsOf
    rules: LeagueRules                              # FACTS about the format
    rosters: Mapping[RosterId, tuple[Holding, ...]]
    picks: Mapping[RosterId, tuple[PickAsset, ...]]
    transactions: tuple[TransactionFact, ...]       # WHO / WHAT / WHEN. No motive. No grade.
    coverage: Coverage                              # per-roster; PARTIAL is representable
    receipt: Receipt
```

*Consumer may not assume:* any valuation, any intent, any posture. "Rebuilding" / "contending" / "needs a QB" are DERIVED reads that belong on B7 with their own claim level, **not** in the league artifact set. This is a live violation: `team_posture` publishes `SCHEMA_VERSION = "team_posture.v1"` among the tracked league seeds, guarded only by a market-token string check, and zero-fills missing league facts via `_safe_float(value, default=0.0)`.

### B6. `market → decision` : `Observation`

```python
@dataclass(frozen=True, slots=True)
class Observation:
    subject: CanonicalId
    metric: MarketMetric      # CLOSED: TRADE_VALUE | ADP | POSITION_RANK | OVERALL_RANK
                              #       | VOLATILITY | TREND_DELTA
    value: Measurement[float, Market]     # lane is Market BY TYPE
    venue: SourceId           # OPEN. No Literal["fantasycalc"] anywhere.
    observed_at: datetime
    population: PopulationId  # WHOSE market — never assume it matches the model cohort
    receipt: Receipt
```

**PVO holds `market: tuple[Observation, ...]`, not one `MarketOverlay` object.** A second market source is a compile-and-runtime error today at 26 backend files plus 4 frontend files, because `MarketAssetOverlay.source` and `MarketReconciliation.market_source` are `Literal["fantasycalc"]` all the way into the browser's generated zod validators.

*Consumer may not assume:* freshness; that it values the same thing the model predicts; that its population matches the model cohort; that a rank and a value are interchangeable. **Degradation:** venue disagreement → two Observations, two Comparisons, both carried. **Never averaged.**

### B7. `decision → read_models` : `PVO`, `DecisionOpportunity`

```python
@dataclass(frozen=True, slots=True)
class PVO:                          # what we BELIEVE. Market-independent BY CONSTRUCTION.
    subject: CanonicalId
    as_of: AsOf
    beliefs: Mapping[LabelId, Prediction | Refusal]   # Model lane only.
                                                      # NO Market field is EXPRESSIBLE here.
    claim: ClaimLevel
    caveats: tuple[Caveat, ...]
    receipt: Receipt

@dataclass(frozen=True, slots=True)
class LaneBundle:                   # SEPARATE FIELDS. Composition, never merger.
    model:   tuple[Prediction | Refusal, ...]
    market:  tuple[Observation | Unknown, ...]
    league:  tuple[TransactionFact | Holding | ConstraintFact, ...]
    outcome: tuple[Measurement[float, Outcome] | Unknown, ...]

@dataclass(frozen=True, slots=True)
class DecisionOpportunity:          # DOO — what David COULD do
    opportunity_id: OpportunityId
    action: ActionKind              # CLOSED: ACQUIRE | RELEASE | TRADE_SEND | TRADE_RECEIVE
                                    #       | START | HOLD_NO_ACTION
    subjects: tuple[CanonicalId, ...]
    league_ref: tuple[LeagueId, AsOf]           # pins the exact league vintage
    horizon: Horizon
    lanes: LaneBundle
    constraints: tuple[ConstraintFact, ...]
    comparisons: tuple[Comparison, ...]         # the ONLY cross-lane content
    claim: ClaimLevel
    caveats: tuple[Caveat, ...]
    receipt: Receipt
    # DELIBERATELY ABSENT AND UNADDABLE: score, rank, desirability, fairness, verdict.

@dataclass(frozen=True, slots=True)
class OrderingBasis:                # if a surface must order, it DECLARES the basis
    sort_key: FeatureId | MarketMetric | LabelId    # a SINGLE-LANE key. Never a composite.
    lane: type[Lane]
    direction: Literal["asc", "desc"]
    claim: ClaimLevel = ClaimLevel.DESCRIPTIVE      # ORDERING NEVER UPGRADES A CLAIM
```

**Product law is structural here, not documentary.** `DecisionOpportunity` has no float to sort by, so a desirability rank is unconstructible. `OrderingBasis.sort_key` is typed as a single-lane key, so "sort by model-minus-market" cannot be *expressed* — which is what currently ships as `card_section_counts[0].sort_key = "absolute_model_market_delta_desc"`. `TRADE_PARITY_BAND` ("governs trade fairness math only") is retired; its legitimate use — reducing each lane to a direction label on its own scale — survives inside `bridge()`.

### B8. `read_models → serve` : `Publication[T] | Unavailable`

```python
@dataclass(frozen=True, slots=True)
class Publication[T]:
    name: ReadModelName
    schema_version: SchemaVersion       # "league_opportunity.v3"
    run_id: RunId                       # pins ALL read models from one build
    published_at: datetime
    as_of: AsOf
    claim: ClaimLevel
    coverage: Coverage
    caveats: tuple[Caveat, ...]         # from the ONE kernel catalog
    source_receipts: tuple[ReceiptRef, ...]
    digest: Sha256
    body: T

@dataclass(frozen=True, slots=True)
class Unavailable:
    name: ReadModelName
    reason: UnavailableReason   # CLOSED: NOT_PUBLISHED | SCHEMA_MISMATCH | INTEGRITY_FAILED
                                #       | RUN_MISMATCH
    detail: str

class ReadModelStore(Protocol):
    def read(self, name: ReadModelName, *, schema: SchemaVersion,
             run_id: RunId | None = None) -> Publication[Any] | Unavailable: ...
    def read_set(self, names: Sequence[ReadModelName], *,
                 schemas: Mapping[ReadModelName, SchemaVersion]
                 ) -> Mapping[ReadModelName, Publication[Any]] | Unavailable: ...
    # read_set is ALL-OR-NOTHING on ONE run_id. Mixed vintages are UNREPRESENTABLE.

def publish[T](name: ReadModelName, body: T, **kw) -> Publication[T]: ...
    # atomic tmp -> fsync -> os.replace, ALWAYS. Atomicity lives here so it cannot be forgotten.
```

`read_set` closes a live mixed-vintage read on David's main league surface: `league_pulse.py:50-57` pins one resolution for posture + matrix, then `:59-60` reads `league_opportunity_latest.json` from a hardcoded path **outside the pin**, and that file is not in `TRACKED_SEED_PATHS`, so the pinning mechanism cannot cover it.

*Consumer may not assume:* presence; freshness; that two separate `read()` calls came from the same run. **Degradation:** not published → `Unavailable(NOT_PUBLISHED)` → 503. Schema drift → `Unavailable(SCHEMA_MISMATCH)` → 503, never a best-effort parse. Half-written → impossible by construction. **Partial body is not representable** — a read model is published whole or not at all; degraded *content* rides as `coverage` + `caveats` with a 200, which the repo already gets right.

### B9. `serve → HTTP` : response DTO

```python
def to_dto[T](pub: Publication[T]) -> ResponseModel: ...   # pure projection
# Unavailable -> HTTPException(503, {"error": name, "reason": reason})
```

Serve MAY rename fields, drop fields, format for display, and translate `Unavailable` → 503. Serve MAY NOT compute, fetch, open a file, open a database, import from `sources`/`extraction`/`adapters`/`features`/`modeling`, or invent a caveat token.

The DTO's `receipt` field is **required**, which is what finally makes `MetricCell`'s `receipt?:` safely promotable to required — today it is optional and **no production call site passes one**, so the chain must exist before the prop can change without fabricating strings like `"capture date unavailable"`.

---

## §5. The open registries — append-only DATA, not Python literals

```python
class Registry[R](Protocol):
    def get(self, key: str, *, known_as_of: datetime) -> R | Unknown: ...
    def all(self, *, known_as_of: datetime) -> tuple[R, ...]: ...
    def register(self, row: R, *, declared_by: str) -> Receipt: ...   # APPEND-ONLY

SourceCatalog        : Registry[SourceDefinition]      # + StreamDefinition rows
ProfilerRegistry     : Registry[ProfilerDefinition]    # keyed by sniffed media_type
ExtractorRegistry    : Registry[ExtractorSpec]
FeatureRegistry      : Registry[FeatureDefinition]
TrainingSpecRegistry : Registry[TrainingSpec]
SerializerRegistry   : Registry[SerializerDefinition]
UnitRegistry         : Registry[Unit]
CaveatCatalog        : Registry[CaveatDefinition]      # code -> display text -> claim impact
EvidenceLedger       : Registry[EvidenceRecord]        # the CEILING on every claim
```

**The catalog must acquire teeth.** `SOURCE_REGISTRY` is imported by **zero** production modules (verified: only `feed_cadence`, itself, `eval/qb_validation/execution.py`, and one script). The acceptance test's "1 catalog row" wires *nothing* at runtime today, which is why every source's real path is bespoke and `footballguys_intake.py` is 3,997 lines. And **three parallel registries already disagree about a live source**: `daily_control` declares footballguys `mode="manual_download"`, but `feed_cadence.MANUAL_SOURCES = ("playerprofiler","pff","rotoviz","campus2canton")` omits it — so `daily_control`'s own validator would reject a `held.footballguys` record as "not a known manual source." Two registries in the same package, out of sync 9 days after landing.

```python
@dataclass(frozen=True, slots=True)
class SourceDefinition:             # THE "1 catalog row"
    source_id: SourceId
    lane: type[Lane]                # a TYPE, resolved at import — not a string
    roles: frozenset[SourceRole]
    default_origin: Origin
    claim_ceiling: ClaimLevel       # NOT a per-column allowlist
    acquisition: AcquisitionSpec    # CLOSED kind: http_pull | operator_drop | browser_capture
    media_kinds: frozenset[str]     # sniffed media types this source may produce
    cadence: CadenceSpec            # DECLARATIVE triggers + window. No source-name if/else.
    retention: RetentionClass       # CLOSED: irreplaceable | local_only_with_receipt | derived
    media_budget_bytes: int | None
    prohibited_fields: frozenset[str]
    adapter_ref: str                # dotted path, resolved LAZILY at first use — THE TEETH
    test_gate: str                  # pytest node enforcing this row
```

`daily_control.build_manifest()`, `feed_cadence.MANUAL_SOURCES` and `_declarations()` become **derived views** over `SourceCatalog`. Land as a pure re-expression first — every existing contract test must pass byte-identically before a literal is deleted.

**`adapter_ref` resolves lazily**, never at registry import, so a broken adapter is a degraded-source report (driven by the existing `failure_behavior` vocabulary: `fail_closed | skip_enrichment | use_cached`), not an app-wide import failure.

**`provenance_required` must be enforced or deleted.** It is declared on 20 rows and enforced on data **zero** times — the only assertions are meta-assertions about the registry itself. That is precisely the defect the RED names: "omitting it makes the label decorative."

**Retention classes and the backup gap.** `app/config/backup_manifest.json` is an **allowlist** — a new extraction database is not backed up until a row is added, and its absence is *silence*, not an error. **The ticket that creates the store and the ticket that adds its manifest row are the same ticket.** Still images are `irreplaceable` (a screenshot of a page that has since changed is not re-acquirable — it only looks replaceable); video is `local_only_with_receipt` (the receipt, facts, and audit chain go offsite; on blob loss the archive honestly reports `Availability.ABSENT` with an `INTEGRITY`-free `LIMITATION` caveat and the fact loses claim level automatically and visibly). GC may delete only `derived` renditions — never a blob referenced by a non-superseded fact, never an adjudicated blob.

---

## §6. Composition law

```python
def compose(inputs: Iterable[ClaimLevel], *, ceiling: ClaimLevel,
            bound_by: Mapping[ClaimLevel, ReceiptRef]) -> tuple[ClaimLevel, ReceiptRef | None]:
    """min over MATERIAL inputs, then the evidence-record ceiling. Fail-closed.
       Materiality is DECLARED at the composition site, never inferred; default = everything
       you read is material. Returns the BINDING input so the lattice is debuggable."""

def apply_caveats(level: ClaimLevel, caveats: Iterable[Caveat]) -> ClaimLevel:
    for c in caveats:
        if c.severity is Severity.INTEGRITY:
            raise ValueRefused(c)                 # forces availability = ABSENT
        if c.caps_at is not None:
            level = min(level, c.caps_at)
    return level
```

**Severity composes by MAX (worst wins). ClaimLevel composes by MIN (weakest wins). Dual join operators on dual lattices** — stated in the kernel so nobody writes `max()` on claim. `ClaimLevel.__bool__` raises, so `if claim:` cannot silently invert (`DESCRIPTIVE=0` is falsy, `DIAGNOSTIC=1` is truthy — the exact opposite of `decision_supported`).

**No lane borrows from another.** A `Comparison` is `DESCRIPTIVE` by construction and can only lower a composed claim. **`decision_supported` keeps its name and its `Literal[False]` type**, redefined as a read-only projection `claim is DECISION_SUPPORTED` — everything is descriptive today, so it stays `False` and none of the 399 call sites across 73 files change. Delete the bool last, behind a contract test asserting zero remaining references.

**`ClaimLevel` purity is enforced mechanically, not documented.** A test asserts it is an `IntEnum` with exactly 4 members, no `str` payload, and no member name containing a mechanism/reason token (`retrospective`, `limited`, `pending`, `active`, `market`, engine names). All five existing encodings grew *because* a reason got embedded. The reason has a designated home — `EvidenceRef` and `CaveatCode`, both OPEN — so the pressure has somewhere legitimate to go.

---

## §7. The acceptance test, walked

| Change | Touches | Seam change? |
|---|---|---|
| **New data source** (paid API / manual drop) | 1 `SourceCatalog` row + 1 `SourceAdapter` + crosswalk rows | **No.** `SnapshotRef.source_id` is an opaque key. The kernel names no provider. Cadence, retention, lane and claim ceiling are *columns on the row*, not `if` statements in the engine. |
| **New feature** | 1 `FeatureDefinition` row + a new `FeatureSetVersion` (a computed content hash) | **No.** Old vintages carry their own `definitions()` and stay readable forever. Lag depth is a `TrainingSpec` parameter, not a column. |
| **New model family** (trees, ensembles, sequence models) | 1 `TrainingSpec` row + 1 `ModelFamily` impl + 1 `SerializerDefinition` | **No.** `Prediction` carries `spec_hash`, not a family name. `input_kind` (CLOSED, 2 values) is the only thing consumers branch on, and both projections come off one vintage. |
| **New experiment** | 1 `EvidenceRecord` row | **No code change.** `claim_ceiling` is a *lookup*, never a branch. |
| **Unstructured text** (news, pressers, injury reports) | 1 catalog row + 1 profiler row + 1 extractor row | **No.** `extract()` with `media_type="text/plain"`, `locator={char_start, char_end}`. |
| **Screenshots** | 1 catalog row + 1 extractor row (`image/png` profiler already registered) | **No.** |
| **Video** | 1 catalog row + 1 profiler row + 1 extractor row with `params["frame_sampling"]` | **No.** `Locator` already carries `t_start_ms`/`t_end_ms`; `RawSnapshot` already carries `duration_ms`/`frame_count`, `None` for stills. |

**Why screenshots and video cost zero seam changes:** media is not a new lane and not a new type — it is a **fourth origin** with stricter, checkable trust rules and a locator. `Extracted` sits beside `Observed` in one closed union, and every consumer that already handles `Basis` handles it by construction. The extension points that grow are `params` (inside the spec hash) and the profiler registry — never a reserved-empty field on a seam.

**The four one-time seam changes, done BEFORE any of the above:**
1. `kernel/trust.py` — lift the trust-plane protocols so `modeling` and `extraction` are siblings. Prevents a real dependency cycle; cheap now, structural surgery later.
2. `kernel/vocab.py` + `kernel/origin.py` — the four origins.
3. `SourceDefinition` gains `acquisition`, `media_kinds`, `retention`, `media_budget_bytes`, `lane`, `claim_ceiling`, `adapter_ref` — all of which exist today only as prose in `notes`.
4. `pff_intake`'s `(_profile_csv, _schema_sha256)` pair becomes the profiler registry — a pure refactor guarded by byte-equality against the real ledger.

Four files, once. **If adding a source ever touches fifteen, one of these four was skipped.**

---

## §8. Enforcement — three arms

**(1) Runtime, load-bearing today.** Private constructors; `LaneError` on cross-lane `+`/`-`/`<`; `UnitError` on identity mismatch; `from_json` re-verification; append-only stores that raise on same-key-differing-content.

**(2) Static, dormant until adopted.** Add `mypy --strict` scoped to `src/dynasty_genius/kernel/` **only** — a brand-new, ~600-line, stdlib-only package can be strict from day one with no repo-wide migration and no findings backlog. **Until this lands, Lane safety is runtime-only. Say so plainly rather than implying otherwise.**

**(3) Build-enforced, copying the best mechanism in the repo.** `kernel/vocabularies.py` emits every CLOSED vocabulary from ONE Python source of truth to a JSON that the TS client consumes — the exact shape of `frontend/src/shell/banned_vocabulary.json` + `npm run banned-language`, which the master plan already names as the mechanism to copy. Plus AST scans (a Python contract test driving a Node scanner, as CI already does):

- no `object.__new__(Measurement)` / `Measurement._mint(` / `object.__setattr__` on a Measurement outside `kernel/`
- no filesystem or `sqlite3` under `app/api/routes/**` (expected today: **15 of 32 files**)
- exactly one caveat vocabulary definition (expected today: **2 in serve, disjoint**)
- no `require()` under `serve/`
- `self_reported_confidence` unreachable from the claim composer's import closure

**import-linter contract** (`root_packages = dynasty_genius, app`), gated on three prerequisites that are currently blocking:

```
layers: app.api.routes > read_models > decision > {market, league} > modeling > features
        > identity > extraction > sources > registry > evidence > kernel
forbidden: kernel -> everything (incl. pandas, pydantic, httpx, sqlite3)
forbidden: dynasty_genius -> app          # CURRENTLY FAILS: pvo_assembler.py:15,18
forbidden: app.api.routes -> {sources, extraction, adapters, identity, features,
                              modeling, market, decision, sqlite3}
independence: {market, modeling, features}   # they meet ONLY in decision, via bridge()
forbidden: {features, modeling} -> market
```

**Prerequisites, in order:** (a) cut the genuine `pvo_assembler ↔ roster_auditor` cycle — a layers contract cannot express a graph containing one, and the workaround lazy import is already documented in the code; (b) add `__init__.py` to `src/`, `src/dynasty_genius/`, `models/`, `decision_logic/` plus `[project]`/`[build-system]` and install editable, so `app` is not reachable from `dynasty_genius` by sys.path accident; (c) ship the layers contract only once a Tarjan SCC scan reports zero components of size > 1.

**Delete `LEAKAGE_REGEX` and name-based `PROHIBITED_COLUMNS` — but only after the lane type is load-bearing.** `^ktc_|^adp|_rank$|...` silently drops a paid rankings feed's legitimate `overall_rank`, while `scout_note` blocks a column by spelling and permits identical content named `film_summary`. Leakage must be enforced by the lane type parameter, which cannot be evaded by renaming. **Sequencing hazard:** `engine_a_contract.PROHIBITED_COLUMNS` is imported at module scope by `source_registry.py`, which validates at import time — remove that dependency first, and keep the regex as a redundant belt for one full training cycle.

---

## §9. Ratified conflict rulings

| # | Conflict | Ruling | Why |
|---|---|---|---|
| **R1** | RED test's flat calendar vs shipped competition-scoped validator | **Shipped wins.** Rewrite `REQUIRED_CALENDAR_ANCHORS` as `(competition, anchor)`. | **Verified:** `daily_control.py:673` refuses stray flat `week1_kickoff`/`final_game`/`game_week_completions` with `SCOPE_MISSING`, and `:684` requires a `competitions` block. `test_x1` **cannot pass as written** regardless of origins. The flat form is a fixed bug; promoting it unamended reintroduces it. |
| **R2** | Does adding `extracted` break `test_o1`? | **No, and the test stays unamended.** The kernel owns 4 origins; `cadence_inputs` declares `ORIGINS = frozenset({DERIVED, DECLARED, OBSERVED})` as a **documented admissible subset** — a calendar anchor or a held-season inventory can never be read out of media. `set(m.ORIGINS) == ORIGINS` still holds. | Better than widening a vocabulary the module does not need. But the file **must** be amended anyway for R1, so both land in one commit. |
| **R3** | Extracted ceiling: `HUMAN_CONFIRMED → DECISION_SUPPORTED`? | **No.** `extracted` alone never exceeds `DIAGNOSTIC`; `REPLICATION_CANDIDATE` needs corroboration from an *independent origin*; `DECISION_SUPPORTED` needs an `EvidenceRecord` ratifying the **(field × layout-family)** pair. | A human verifying ONE reading does not establish the extractor read the other 400 correctly. Verification is per-row evidence; the ceiling is a class property. This also makes the one-human bottleneck tractable — adjudicate one blob per layout family, not one per fact. |
| **R4** | `Determinism` declared on the extractor spec vs `Reproducibility` computed per fact | **Computed per fact.** From `replicate_count` + `replicate_agreement`; k=1 mechanically yields `RECORDED`. | A self-declared row claiming `EXACT` for an LLM launders a nondeterministic read into a decision-eligible fact — with a green checkmark on it. Keep `test_gate` as a *second* guard on the declared purity claim, not the primary one. |
| **R5** | Wide-per-entity `FeatureRow` vs long-form vintage | **Long-form wins.** `(entity_id, period, feature_id, value, observed_at, origin_ref)` + `as_tabular` / `as_sequence`. | Measured: 33 columns, lag depth fixed at 2, 60 players with 7 invisible-past-2 seasons, closed-world contract that *already* fails "old vintages stay readable," and a 23-file precedent from the NGS incident. Wide-per-entity cannot express per-period at all. **The period axis living in column names is a second root cause, independent of the registry problem.** |
| **R6** | Median-imputing an absent season | **Forbidden.** Absence is a mask bit in `SequenceBundle`, and `Availability.IMPUTED` where a stand-in is genuinely present. | An absent season is a structural fact (not in the league). Imputing it **fabricates a career**. This is distinct from a missing measurement, and `SimpleImputer(strategy="median")` cannot tell them apart. |
| **R7** | Does the market gate a model claim? | **No.** A `Market` Observation may never raise a `Model` claim. | **Verified live:** `backtest_harness.py:337` `elif g3_result is not True: grade = "ACTIVE_B"` — G3 market superiority decides `overall_grade` — while `:385` on the *same object* comments `g3_market_superiority_pass=g3_result, # DISCLOSED only; never gates model_status`. Two ladders on one object disagreeing about the product's central law. `model_status` is right; `overall_grade` is retired. |
| **R8** | Lane: tag class vs Enum vs Literal | **Tag class**, `Model`/`Market`/`Outcome`/`League`, no default, no value form. | An Enum member is a *value*, and a value can be put in a field — empirically how `SpreadBar.tsx:24` (defaulting to `"model"`) and `player_value_object.py:24` got here. Serialization uses `key: ClassVar[str]`, write-only at the serve boundary. |
| **R9** | `withheld` as an Availability state | **Rejected.** It is a projection at the publication boundary from `(claim, surface.required_claim_level)`. | Fails closure criterion (b). Strictly better: one Measurement, published to a diagnostic surface and withheld from a decision surface, without storing two availabilities. Renders as a named caveat stating both thresholds, so the difference self-explains on the page. |
| **R10** | Is `extraction` a layer or an origin? | **Both, and they are not in conflict.** `extracted` is an **origin** in the kernel (the seam answer, and why screenshots cost zero seam changes). The machinery producing extracted facts is a **layer** between `sources` and `identity` (the implementation answer). | Extraction below identity because extraction emits *mentions*, not players. A blurry screenshot has two independent failure modes — misread glyphs, misresolved name — and collapsing them makes both invisible. |
| **R11** | Fuzzy identity auto-verification | **Prohibited, 5 modules to 1.** Discovery (`MatchCandidate`, scored) and resolution (deterministic) are different types. | `identity/__init__.py:171-178` stamps `VERIFIED` on 0.80 and 0.60 SequenceMatcher scores while five modules prohibit fuzzy resolution. `college_prospect_identity.py:508-524` already has the right shape — generalize it. Confidence is queue priority, never promotion. |
| **R12** | Duplicate `as_of` in a Series | **Raises.** | On an append-only store a genuine duplicate means two captures disagree — a conflict, not a tie-break. Silent last-write-wins is hiding a defect. **Precondition:** land the duplicate-count scan before the invariant. |

---

## §10. Build order — each step independently shippable with byte-identity proof

1. **`kernel/` as a standalone package with ZERO production call sites.** Fully contract-tested; `mypy --strict` scoped to it. The value delivered now is that the types exist and *constrain* the layers as they are written — a store that must eventually emit a Receipt is designed differently from one that must not. `Uncalibrated(UNCALIBRATED)` is the honest pre-interval state and is a first-class constructible value, which is exactly what lets the type ship before the intervals do.
2. **Caveat catalog unification + `kernel/vocabularies.py` → JSON.** Kills the two disjoint `SAFE_TOKENS` sets and the backend's read of a frontend source file at request time. Port the existing falsification matrix first; any string that trips today and would not trip after unification is a matrix row that must be argued, not silently dropped.
3. **ClaimLevel lattice, landed ADDITIVELY beside `decision_supported`.** Nothing new can be added safely until a new input can declare what it may support. 399 sites, so start early — but change none of them.
4. **Long-form `FeatureVintage`, written BESIDE the CSV.** `as_tabular()` must emit a frame byte-identical to today's `engine_b_features_v2.csv`, proven by hash before any consumer switches — the repo's own strict-replacement precedent. Superset-tolerant contracts land here.
5. **Opaque `CanonicalId` + append-only bitemporal crosswalk + `extra="forbid"`.** The silent drop is a live data-loss bug. Never rewrite history: legacy namespace rows. **Do not touch the frozen QB-1 study root** — it is behind a file-path allowlist wall, and amending it is a governance act, not a refactor.
6. **`ModelFamily` protocol; preprocessing off the harness into `TrainingSpec`.**
7. **`SourceCatalog` as a lazy runtime dispatch table + one shared drop pipeline.** Recovers ~4,000 lines and makes every source vector cost the same three files.
8. **`RawSnapshot` bytes-first capture + profiler registry + `extracted`.** Only after step 3 — `extracted` arriving before the claim lattice means it lands with nothing to stop it claiming decision support, which is the one failure mode this architecture exists to prevent.
9. **`Publication` + `ReadModelStore`.** Migrate `morning_tape.py` first (already conformant, zero-risk proof of the pattern), then the other 14 IO routes in ascending size. **Move the three large analyzers wholesale** with imports rewritten and nothing else changed, so their existing contract tests move with them byte-for-byte and prove the move was faithful.
10. **`Measurement[L]` adoption; lift `MarketOverlay` off PVO.** Version the read model (`league_opportunity.v3` beside v2) — never mutate it, since the frontend's generated zod validators fail at *runtime in the browser*, not at build.

---

## CLOSED VOCABULARIES (structured)

### `Lane`

Values: `Model`, `Market`, `Outcome`, `League`

A TYPE PARAMETER, implemented as tag classes with no value form (an Enum member is a value and a value can be put in a field — empirically how SpreadBar.tsx:24 and player_value_object.py:24 got here; SpreadBar even DEFAULTS to "model", so a market value silently inherits model styling). Closure argument: a number about a player states our belief, others' belief, what happened, or what is structurally true of the league — there is no fifth belief-holder. Expert consensus is Market, already ruled empirically at eval/backtest_artifact.py:165-172; mock-draft consensus is pre-classified Market (price discovery). Outcome and League do NOT merge: Outcome is the label lane (what modeling trains and evaluates against, subject to the point-in-time law in a way league facts are not) and is what residual() consumes; League is the constraint lane. Merging would let a box score enter a DOO constraint set and a roster-slot count be used as a training label. Escape hatch so no fifth lane is ever smuggled in as Market: bridge()->Comparison and residual()->Residual need no new lane.

### `Origin`

Values: `derived`, `declared`, `observed`, `extracted`

Partitions by HOW YOU RECHECK: re-run a function, re-ask a person, re-query the world, re-read a representation. There is no fifth way to recheck a fact. Each carries the field that makes it checkable (derivation / declared_by / observed_at / extraction+locator+verbatim). `extracted` earns the fourth slot because it is the only origin needing THREE trust properties at once — re-runnable like derived (but a differing re-run is DISPUTED, not DRIFTED, because the reader is stochastic; calling that "stale" is the same category error test_s1b names), rots like declared (the interpretation can be wrong while the bytes never change), staleness-visible like observed (and the EXTRACTOR can be superseded independently of the media, which observed_at collapses and hides) — plus one property none of the three have: a locator, so a human can look at the same pixels.

### `ClaimLevel`

Values: `descriptive`, `diagnostic`, `replication_candidate`, `decision_supported`

ORDERED IntEnum, composes by min() over MATERIAL inputs then the evidence-record ceiling, fail-closed. __bool__ RAISES so `if claim:` cannot silently invert (DESCRIPTIVE=0 falsy, DIAGNOSTIC=1 truthy — the exact opposite of decision_supported). Closure is CONDITIONAL, not free: all five existing encodings in the repo (model_grade, overall_grade, TierStatus, derive_claim_level, decision_supported) grew precisely BECAUSE a reason got embedded (current_model_retrospective_diagnostic, ACTIVE_B_VALIDATED, diagnostic_grade_active_limited). Enforced mechanically: a test asserts exactly 4 members, no str payload, and no member name containing a mechanism token. The reason has a designated open home — EvidenceRef and CaveatCode.

### `Severity`

Values: `note`, `limitation`, `integrity`

ORDERED, composes by MAX (worst wins) — the DUAL of ClaimLevel's MIN, stated in the kernel so nobody writes max() on claim. Each level has a distinct MECHANICAL consequence: none / caps claim level / forces availability=ABSENT. A fourth level would need a fourth kind of consequence and there is none. Renames the shipped Literal["info","caveat","integrity"] at system_model_provenance_models.py:45, which named one of its own levels after the container it annotates, making `caveat.severity == "caveat"` legal and meaningless. Ordering and the max() composer are lifted unchanged.

### `Availability`

Values: `present`, `imputed`, `absent`, `not_applicable`, `outside_as_of`

WHETHER a slot holds evidence. Consolidates three incompatible hand-rolled vocabularies (fc_forward_capture_store captured/source_omitted/structurally_unavailable, nflverse NOT_APPLICABLE, prediction_snapshot_store missing_legacy_capture/capture_incomplete). `imputed` earns a slot because every consumer must branch on it and the branch would otherwise require reading the derivation registry — a stand-in is present but is NOT evidence. `outside_as_of` earns a slot because it makes the point-in-time law VISIBLE rather than a silent row filter: a value that exists but is future-of-your-as-of is recoverable by widening the window, a value that does not exist is not. REJECTED: `withheld` — derivable as claim < surface.required_claim_level, so it is a publication-boundary projection, not a stored state. The WHY of an absence lives in the OPEN caveat registry, because reasons grow forever (the ReportFreshnessStatus lesson: an 8-value Literal that gained a member every time a new failure mode appeared).

### `Freshness`

Values: `current`, `due`, `not_due`, `undetermined`

LIFTED VERBATIM from the shipped, battle-tested sources/feed_cadence.py:84-85, including its rollup law (`a source rollup may never be quieter than its least-known stream` — absent a governing positive fact, unknown obligation stays UNDETERMINED). Do not redesign it. REJECTED: `carried_forward` as a fifth value — a value whose as_of did not advance while published_at did is, to every consumer, exactly DUE. Coverage stays a separate axis, per the standing in-code ruling at daily_control.py:131-133 that a source can be quiet and incomplete at the same time and collapsing the two destroys the second fact.

### `Calibration`

Values: `calibrated`, `uncalibrated`, `out_of_cohort`, `not_applicable`

Does the UNCERTAINTY statement mean what it says. Lane-parameterized and artifact-backed per ratified constitution (00-product-constitution.md:170): CALIBRATED REQUIRES a CalibrationRef, and a market-lane tier and a model-lane tier are different claims that never reuse each other's calibration. Independent of ClaimLevel — the repo already discovered this split itself with separate validity_spearman_pass (discrimination) and validity_ci_adequacy_pass (interval adequacy) fields on one gate result. Absorbs the hardest extensibility vector without a new value: an extractor's confidence is UNCALIBRATED until an extractor-calibration artifact is ratified. Calibration-artifact staleness is not a fifth value — the CalibrationRef is itself dated and carries its own Freshness.

### `Reproducibility`

Values: `deterministic`, `reproduced`, `recorded`

ORDERED, best first. COMPUTED per fact from (replicate_count, replicate_agreement, extractor_is_pure) — NEVER declared on a registry row, which is the single most important ruling in the extraction design: a self-declared `exact` for an LLM launders a nondeterministic read into a decision-eligible fact with a green checkmark on it. k=1 mechanically yields RECORDED, so cutting sampling cost visibly costs claim level instead of silently costing truth. Exhausts what reproduction can mean: bit-identical (provable by re-running in CI), value-level agreement across k samples after normalization, or ran-once-and-archived (honest floor, never dressed up). Hosted LLM/VLM inference is not bitwise deterministic even at temperature 0 — batching-dependent FP reduction order, mixed precision, MoE routing, server-side updates behind a stable id — so any design promising byte-identical VLM replay is lying.

### `Corroboration`

Values: `none`, `self_consistent`, `second_extractor`, `cross_source`, `human_affirmation`

Independent support for an extracted fact. Corroboration kinds are: the document's own redundancy, another reader, another representation of the fact, a human. This is the vocabulary I am LEAST confident is closed as extraction expands into video and news — so the escape hatch is designed in from the start: the §2.6 ceiling is a TABLE LOOKUP, not a code branch, so demoting Corroboration to an OPEN registry with a claim_ceiling column touches the registry and nothing else. Critically, a second sample of the SAME model is not corroboration — that is reproducibility, already counted. self_consistent alone never lifts a fact above descriptive.

### `Verdict`

Values: `reproduced`, `drifted`, `disputed`, `aged`, `unaffirmed`, `not_checkable`

The result of a recheck, partitioned by origin so the signal stays trustworthy. `.stale` is a property meaning `verdict is DRIFTED`, which makes the in-flight RED's D1/D1b/S1/S1b pass unchanged. DISPUTED exists separately from DRIFTED because an extracted disagreement may be sampling noise rather than data drift, and labelling stochastic disagreement `stale` trains the operator to ignore the signal — the same category error test_s1b already names for declared facts. NOT_CHECKABLE covers both a declared fact with no derivation to re-run and an extracted fact whose blob was evicted; the latter attaches a LIMITATION caveat so a fact whose evidence was deleted loses claim level automatically and visibly rather than silently.

### `IdentityState`

Values: `resolved`, `ambiguous`, `unresolved`, `source_id_collision`

Consolidates four DIVERGENT copies shipping today (league_transactions {canonical_resolved, unknown}; playerprofiler and nflverse_usage {canonical_resolved, conflict, unknown}; outcome_identity_bridge {unresolved, conflict}) plus a fifth state existing in only one module (playerprofiler_roster SOURCE_ID_COLLISION). source_id_collision is genuinely distinct from ambiguous: the defect is in the SOURCE (one native id provably covering two humans), not in our matcher, so the remedy is a vendor conversation rather than a better match. Unresolved rows are CARRIED with canonical_id=None, never dropped and never keyed on the source-native id as a fallback — the rule already ratified at morning_tape_artifact.py:3-6.

### `RefusalReason`

Values: `no_model_for_cohort`, `features_incomplete`, `entity_absent`, `out_of_support`, `artifact_unavailable`

Carried by Refusal, a type DISTINCT from Prediction, so a refusal cannot share the success channel. Fixes a live defect: engine_b_service.py:139 returns {"error": "model_not_found"} and :200 sorts on x.get("predicted_avg_ppg_t1_t2", 0), which RANKS the refusal as 0.0 instead of excluding it. out_of_support is separate from features_incomplete because a rookie with no NFL season is not a data gap — it is outside the model's domain, and the correct response is refusal rather than extrapolation.

### `InputKind`

Values: `tabular`, `sequence`

The only model-family property consumers branch on, and the reason a sequence model needs no seam change. Both projections (as_tabular, as_sequence) come off ONE long-form FeatureVintage, so Ridge and a GRU read one artifact. Closed at two because the question it answers is exhaustive: does this family consume a fixed-width row or a ragged per-period sequence with a presence mask. Family identity itself (ridge, hgb, seq_gru) is an OPEN registry key — the kernel never mentions Ridge.


---

## BOUNDARY INVENTORY (structured)

| From | To | Crossing type | Consumer may NOT assume |
|---|---|---|---|
| `sources` | `extraction / identity` | RawSnapshot (blob: Blob, shape_sha256, lane, role, captured_at, effective_at, published_at, duration_ms\|None, frame_count\|None, basis: Receipt) | that it parses; that the schema matches the last snapshot; that published_at exists (None means unknown, never inferred); that effective_at equals captured_at (a screenshot depicts an unknown EARLIER moment — default availability_time_unknown or a stale page enters an as-of window it does not belong in); that rows are unique, complete, or ordered; that a paid source succeeded. DEGRADATION: missing -> Unknown(ABSENT) naming the last successful snapshot_id, never an empty list. Unparseable -> STILL STORED; parse failure is an identity-layer state, never a capture failure, which is what makes replay possible after an adapter fix. Partial -> rows_claimed != rows_present rides as Presence.PARTIAL on every descendant receipt. lane and role are INHERITED from the catalog row and are IMMUTABLE downstream — otherwise media is a lane-laundering bypass and a KTC screenshot slips into features because nobody thought of a PNG as a market source. |
| `extraction` | `identity` | ExtractionRun -> tuple[ExtractedFact \| ExtractedMention, ...]; fact identity is (blob_sha256, field_path, spec_hash) | that the extractor read correctly; that a re-run reproduces (that is what Reproducibility measures, and it is computed not asserted); that self_reported_confidence means anything (it is review-queue priority, structurally unreachable from the claim composer); that a mention resolves to a player (extraction emits MENTIONS — a blurry screenshot has two independent failure modes, misread glyphs and misresolved name, and collapsing them makes both invisible); that the blob still exists (retained=False -> recheck returns NOT_CHECKABLE, attaching a LIMITATION caveat that caps the fact). A value with no locator is REFUSED AT CONSTRUCTION — an unanchored extraction is unfalsifiable and therefore not evidence. A new spec_hash APPENDS and cannot overwrite, so extractor drift becomes a visible disagreement between two rows over the same span of the same blob rather than a silent rewrite. |
| `identity` | `features` | Resolution (source_key: SourceKey, canonical_id: CanonicalId\|None, state, candidates, basis: MatchBasis, confidence, valid_from/valid_to, asserted_at, superseded_by, receipt) | that every row resolves; that canonical_id is parseable, sortable, or derivable from a name (it is an opaque ULID — dg_id is demoted to a display alias because generate_dg_id derives from MUTABLE attributes and resolves collisions by INPUT ORDER, so adding a source can rename an existing player and a WR->TE reclassification mints a new id for the same human); that today's mapping held last season (query is bitemporal: effective <= E AND asserted_at <= K); that two sources' native ids share a namespace (a live production bug ships both 00-0030061 and sam_roush_te in one field named dg_player_id); that a confidence score is a resolution (confidence is REVIEW-QUEUE PRIORITY, never a promotion — discovery returns MatchCandidate, resolution is deterministic-only). DEGRADATION: unresolved rows are CARRIED with canonical_id=None, never dropped, never keyed on the source-native id as a fallback. |
| `features` | `modeling` | FeatureVintage (feature_set_version, as_of, frame: LongFrame[entity_id, period, feature_id, value, observed_at, origin_ref], coverage, receipt) with as_tabular(spec) -> TabularBundle and as_sequence(spec) -> SequenceBundle | that every entity is present; that a feature is non-null; that an unknown feature_id returns None (it RAISES); that two vintages are comparable unless feature_set_version matches EXACTLY; that lag depth is a property of the data (it is a TrainingSpec query parameter — the period axis lives in the FRAME, never in column names, which is what makes old vintages readable forever and sequences expressible at all); that an absent period is a missing measurement (it is a MASK BIT — median-imputing it FABRICATES A CAREER for a player who was not in the league). DEGRADATION: absent feature -> Unknown, consumable ONLY through null_policy=IMPUTED_DECLARED whose imputation constant lands in the Prediction's receipt. This closes the sharpest live defect: engine_b_service.py:147 turns a missing feature into None via .get(f), then :150 imputer.transform fills it with the training mean, so a 40%-complete vector yields a number indistinguishable from a complete one. |
| `modeling` | `decision` | Prediction \| Refusal (a SUM TYPE, never a dict); ModelArtifact(spec_hash, payload_uri as a DIRECTORY, serializer_id, input_contract, fit_diagnostics, eval: EvaluationReport) | that the model beats a baseline (only eval.baseline_comparison says so); that every entity has a prediction; that predictions from different spec_hashes are on the same scale or comparable; that a horizon means the same thing across specs; that a refusal can be defaulted to a number (Refusal is a DISTINCT TYPE precisely so .get(key, 0) cannot rank it last instead of excluding it); that the artifact is one pickle file (payload_uri is a directory and payload_sha256 hashes its MANIFEST, because a torch sequence model or a native booster is not a .pkl). value.lane is Model BY TYPE, and value.claim <= eval.ceiling. predicted_as_of == the vintage's as_of, NOT wall clock. training_cutoff is NON-OPTIONAL on TrainingSpec — it is the one field that makes the point-in-time law checkable, and it is recorded nowhere in the serve path today. |
| `league` | `decision` | LeagueContext (rules: LeagueRules, rosters, picks, transactions: tuple[TransactionFact,...], coverage, as_of, receipt) | any valuation, any intent, any posture. 'Rebuilding' / 'contending' / 'needs a QB' are DERIVED reads that belong on the decision->read_models boundary with their own claim level, not in the league artifact set — team_posture currently publishes team_posture.v1 among the TRACKED league seeds guarded only by a market-token string check. Also may not assume every roster was captured (check coverage) and may not assume a missing league fact is zero (team_posture._safe_float(value, default=0.0) is used 4x today). DEGRADATION: partial roster -> Presence.PARTIAL on that specific RosterId; every DOO composed over it inherits the caveat and its claim drops. An unresolved player on a roster is carried as a Holding with canonical_id=None plus its Resolution, so the roster COUNT stays honest rather than silently short. |
| `market` | `decision` | Observation (subject, metric: MarketMetric, value: Measurement[float, Market], venue: SourceId, observed_at, population: PopulationId, receipt) | freshness; that it values the same thing the model predicts; that its population matches the model cohort; that a rank and a value are interchangeable; that there is exactly one market source (PVO holds tuple[Observation,...], not one MarketOverlay object — a second vendor is a compile-and-runtime error today at 26 backend files plus 4 frontend files because MarketAssetOverlay.source is Literal['fantasycalc'] all the way into the browser's generated zod validators). value.lane is Market BY TYPE, so it can never be admitted to a FeatureSet and can never be subtracted from a Measurement[float, Model]. DEGRADATION: absent/stale -> Unknown; the DOO shows the market lane absent and the model lane is UNCHANGED — no borrowing in either direction. Thin cohort -> Comparison(agreement=UNDETERMINED), never a computed label on 3 players. Venue disagreement -> two Observations, two Comparisons, both carried. NEVER averaged. |
| `decision` | `read_models` | PVO (beliefs: Mapping[LabelId, Prediction\|Refusal] — Model lane ONLY) and DecisionOpportunity (lanes: LaneBundle with SEPARATE model/market/league/outcome fields; comparisons: tuple[Comparison,...]) | that a DOO is a recommendation; that DOOs are mutually comparable; that PVO and DOO share an as_of unless they name the same one; that a magnitude exists to sort by. PRODUCT LAW IS STRUCTURAL: DecisionOpportunity has no float to sort by, so a desirability rank is UNCONSTRUCTIBLE; OrderingBasis.sort_key is typed as a SINGLE-LANE key so 'sort by model-minus-market' cannot be expressed (which is what ships today as sort_key='absolute_model_market_delta_desc'); OrderingBasis.claim is pinned to DESCRIPTIVE because ordering never upgrades a claim. PVO cannot express a Market field at all, so it is market-independent BY CONSTRUCTION rather than by review. DEGRADATION: model refused -> the DOO still exists with lanes.model holding Refusal and the action still describable from league facts alone, at DESCRIPTIVE. In no case does a lane borrow another lane's freshness, calibration, or support. |
| `read_models` | `serve` | Publication[T] \| Unavailable, via ReadModelStore.read(name, schema, run_id) and read_set(names, schemas) | presence; freshness; that two separate read() calls came from the same run (use read_set, which is ALL-OR-NOTHING on one run_id so mixed vintages are UNREPRESENTABLE — this closes a live mixed-vintage read on David's main league surface where league_pulse.py pins posture+matrix then reads league_opportunity from a hardcoded path OUTSIDE the pin); that a schema mismatch can be best-effort parsed (it returns Unavailable(SCHEMA_MISMATCH) -> 503). DEGRADATION: not published -> 503. Half-written -> impossible by construction (atomic tmp->fsync->os.replace lives in publish() so it cannot be forgotten; two non-atomic write_text publishes ship today). A PARTIAL BODY IS NOT REPRESENTABLE — a read model is published whole or not at all; degraded CONTENT rides as coverage + caveats with a 200, which the repo already gets right. |
| `serve` | `HTTP` | to_dto(Publication[T]) -> ResponseModel with a REQUIRED receipt field; Unavailable -> HTTPException(503, {error, reason}) | nothing beyond the DTO's own declared shape. Serve MAY rename, drop, and format fields and translate Unavailable to 503. Serve MAY NOT compute, fetch, open a file, open a database, import from sources/extraction/adapters/features/modeling, or invent a caveat token — all six of which happen today across 15 of 32 route modules (including a 782-line SQLite analyzer living inside the routes package, a direct import of the FantasyCalc HTTP fetcher so a network call can happen on the request path, and a backend read of frontend/src/shell/banned_vocabulary.json at request time). The DTO's required receipt is what finally makes MetricCell's optional receipt prop promotable without fabricating strings like 'capture date unavailable'. |
| `kernel` | `every layer (cross-cut)` | Measurement[T, L] / Receipt / Maybe[T, L] / Series[T, L] / Comparison / Residual / the 13 closed vocabularies | that a Measurement can be constructed without evidence (there is no public constructor — only observe/derive/declare/extract, each demanding its origin's checkable field as a non-defaulted keyword); that from_json can be trusted (it REQUIRES a ReceiptStore and re-verifies the content address and the frontier, fail-closed); that lanes can be mixed (LaneError on +, -, and <, at runtime, today, with no typechecker installed); that units are interchangeable (identity comparison, so per-game-played vs per-game-in-season fails on the first call — the PPG=ALL-GAMES ruling is exactly a unit-definition problem); that Measurement is cheap enough to use in a compute loop (IT IS A BOUNDARY AND PRODUCT TYPE ONLY — vectorized inner loops stay numpy on plain floats, and Measurements are minted once at the read_models publish step with one Receipt object shared per column-vintage). kernel imports NOTHING but stdlib — not pandas, not pydantic, not sqlite3. |
| `registry + evidence` | `every layer above sources (cross-cut)` | Registry[R].get/all/register (APPEND-ONLY) and EvidenceLedger.ceiling(subject, known_as_of) -> ClaimLevel | that a registry row exists (get returns R \| Unknown); that a row can be updated or deleted (register is append-only and returns a Receipt); that adapter_ref resolves (it resolves LAZILY at first use, never at registry import, so a broken adapter is a degraded-source report rather than an app-wide import failure); that a declared field is enforced (provenance_required is declared on 20 rows and enforced on data ZERO times today — that is the exact 'omitting it makes the label decorative' defect, and it must be enforced at the adapter boundary or deleted); that adding an experiment requires code (EvidenceLedger.ceiling is a LOOKUP, so one row changes what the same code is allowed to claim on the next read). Registry rows must be DATA in an append-only store, not Python literals — that is the mechanical difference between 'add a source = 1 catalog row' and 'add a source = edit a module nothing imports', and today THREE parallel source registries already disagree about a live source. |
