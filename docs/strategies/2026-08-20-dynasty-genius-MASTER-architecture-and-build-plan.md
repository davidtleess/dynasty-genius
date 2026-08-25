# Dynasty Genius — MASTER Architecture and Build Plan

**Document type:** Adjudicated three-way merge of Master Proposals 1, 2 and 3
**Date:** 2026-08-20
**Working tree at authoring:** `c1e8a0c` on `feature/outcome-loop-week1` (**12 ahead / 3 behind** `origin/main` @ `d2c85c2`)
**Status:** Ruled. Increment 0 is startable; §6 items are startable now and should not wait.

**Sources merged:**

1. `~/.gemini/antigravity-cli/brain/9a996d45-.../DYNASTY_GENIUS_MASTER_PROPOSAL_1.md`
2. `~/Desktop/master-proposal-2-dynasty-genius-2026-08-19.md`
3. `docs/strategies/2026-08-19-dynasty-genius-master-proposal-3.md`

All three synthesize the **same three** parallel architecture sessions — the antigravity North Star,
the strategies session-1, and the Desktop nine-agent audit. Same evidence, three different judgments.
That is what makes them comparable, and it is why this document rules rather than averages.

---

## 1. The verdict

| Proposal | Adopted as | Why |
|---|---|---|
| **P2** | **The spine** | The only one that *adjudicates*. Its §2 names every conflict, resolves it, and states the reasoning. It is also the only proposal that reverses no ruling of David's. Two of its headline claims did not survive verification — see §4D — but its thesis and method stand. |
| **P3** | **The contracts** | The strongest engineering by a wide margin — wave-by-wave with exact paths, RED tests first, enforced performance budgets. Its claim-level algebra is the best single idea in the corpus. |
| **P1** | **The shape** | 264 lines, one topology, eight increments. The best communication artifact of the three, and a plan nobody can retain is a plan nobody follows. |

**P1's disqualifying flaw:** it silently averages conflicts instead of ruling on them, and one of those
silences reverses David's PPG ruling issued the same morning.

**P3's disqualifying flaw:** it reinstates a heavy governance regime — eleven evidence files per
ticket, fourteen approval gates — against David's 2026-08-18 near-zero governance ruling. The mirror
image of P1's error: P1 reverses a data ruling, P3 reverses a process ruling.

---

## 2. What we are building

Dynasty Genius owns one thing no competitor can retroactively build: **a dated, immutable record of
its own past beliefs.** 56 daily model captures across 12,259 players and 57 market captures since
2026-06-24, in stores that refuse to overwrite history.

> ### ⚠ The archive is NOT unbroken — and the claim encoded its own gap
>
> All three proposals describe this record as unbroken since 2026-06-24. It is not. That span is
> **57 days** inclusive. The market lane (`fc_forward_capture`) has 57 captures and is genuinely
> complete. The model lane (`model_forward_capture`) has **56 — missing 2026-08-12.** The number
> everyone quoted was right; the word attached to it was wrong. Nobody subtracted.
>
> `market_divergence_history` is worse: 38 captures with four holes — 2026-07-10, 07-12, 07-17, and
> 08-12 again.
>
> The product's own health check already knows, reporting
> `model_forward_capture: missing 1 of 57 days (2026-08-12)` — to a surface nobody reads, 16 seconds
> after you ask it.
>
> This does not weaken the moat argument; it is the strongest argument *for* it. What makes the
> archive valuable is exactly what makes a hole in it permanent, and holes are opening now. Two
> consequences in this plan: §6.4 gains a gap-census item, and INC 1p must treat a missing day as a
> first-class state — a lead-lag or stability analysis that silently spans a gap returns a confident
> wrong answer.

That archive — not any single model — is the product. The architecture's job is to make the chain
from a raw byte to a number on David's screen **a type rather than a habit**, then turn that chain
into ranked, inspectable options.

Two objects carry it and must never collapse into one:

- **PVO** — what do we believe about this player? Intrinsic, market-independent.
- **DOO** — given this league, roster, price, horizon and available action, what could David *do*?

A great player is often a bad acquisition at today's price. Every competitor fails by flattening
those into one number.

Build principle, agreed by all three and worth stating once: **propagation, not invention.** Every
layer already contains one place that does the thing correctly and several that do not. Name the good
pattern as law; delete its competitors.

---

## 3. Ten conflicts, ruled

### Ruling 01 — PPG definition

- **P1** ✗ Enforce `game_type == "REG"` and retrain Engine B on regular season only.
- **P2** ✓ Strike it — reverses David's same-morning ruling. Strike the supporting prose too.
- **P3** ✓ Preserve all-games; separately flag zero-snap eligibility as unsettled.

**RULING: all games stands.** P1's step reverses David's 2026-08-19 06:32 ruling (*"all games"*) and
triggers exactly the retraining cascade that ruling forbade. Strike the step **and its supporting
prose**, or a future agent re-derives it from the prose.

Take both catches the others made:
- **P2:** the definition lives in **three** sites, not the two DG-024 covers — the third is the QB-1
  label predicate at `qb_ppg_labels.py:817-822`. Widen the ticket before it closes.
- **P3:** zero-snap eligibility is a separate, still-undefined question. Settle it before the next
  model generation rather than discovering it inside one.

### Ruling 02 — Hard-coded constants (P90 ceilings, xVAR multipliers, blend *k*, trade bands)

- **P1** ✗ Adopt as architecture, written into the spec as fixed numbers.
- **P2** ~ Adopt as-is because "real, tested and shipping" — but correctly refuses the aging curve.
- **P3** ~ Refuse to ratify any of them without versioned calibration evidence.

**RULING — better than any of the three.** Neither freeze them nor stop the world to re-derive them.
**Generalize P2's own aging-curve fix to every constant.** Each keeps serving; each gets a
`provenance` stamp (`authored` | `fitted` | `calibrated`) and a calibration status. Anything
`authored` is disclosed as an assumption on screen and enters a calibration queue.

P2 made exactly this move for one constant and failed to generalize it. P3 was right to object but
its remedy blocks shipping. The aging curve is the proof case: named `fitted_aging_curves_v1.json`,
parameters are round numbers with no sample size, and it feeds Engine B as a live input — all
confirmed on re-measurement. Rename it `assumed_*`, stamp `provenance: authored`, then fit it for real.

**Verification sharpened this, and the sharpened version is the better argument.** The P90 ceilings
are *not* unprovenanced — that part of P3's objection was too broad. They trace to a spec carrying
real sample sizes (n = 309 / 660 / 1,059 / 849), and Engine A's still reproduce **exactly** from the
file its comment names. What has happened is subtler and more instructive — they have **drifted as the
training data grew**:

- Recomputing the P90 ceilings from the current `engine_b_features_v2.csv` (2,741 rows) gives
  **TE 10.28 against a hard-coded 9.4** — a 9.4% gap — and **QB 20.44 against 20.1**. RB (15.69 vs
  15.7) and WR (14.63 vs 14.5) still hold.
- The replacement-DVS baselines are internally self-consistent (`12.91 / 20.1 × 100 = 64.2` exactly,
  and all four check out) but the artifact named as their provenance — `var_batch_20260516_190328.json`
  — **contradicts** the values it is said to support.

That is the whole case for this ruling in one example: these constants were derived honestly, with
evidence, by people doing it properly — and they went stale anyway, silently, because nothing
re-checks them. A one-time audit would not have caught it; a `calibration_status` with a recheck date
would. And a citation pointing at a file that disagrees with it is worse than no citation, because it
survives review. Both go to the front of the calibration queue. The xVAR lambda multipliers *are* derived from
P90 ratios as their comment claims (confirmed), and `DVS_BLEND_K` carries no calibration evidence
(confirmed).

### Ruling 03 — Analytical storage (DuckDB over Parquet)

- **P1** ~ Commit outright.
- **P2** ~ Commit, with justification from measured store pathologies.
- **P3** ✓ Treat as a *candidate*; one representative pilot proves parity, as-of correctness, replay,
  restore and rollback first.

**RULING: P3 wins.** This is the single largest technology commitment in the plan, and 15 GB of
partly irreplaceable data sits behind it. The pilot costs days; a bad migration costs the archive that
*is* the product. Pilot on one of the all-TEXT stores — they are the worst and therefore the most
informative.

P2's evidence still justifies the direction: a ~945 MB divergence store carrying a fat `payload_json`
blob per row, two stores declaring every column TEXT including numeric stats, no secondary index or
WAL anywhere.

### Ruling 04 — Canonical identity key

- **P1** ✗ Semantic key from name + position + birth year (`josh_allen_qb_1996`).
- **P2** ✓ Opaque immutable ULID; readable slug survives as a display alias only.
- **P3** ✓ Opaque key reached through a dual-key bridge that never rewrites raw history.

**RULING: P2's rule, P3's mechanism.** A semantic key mutates the moment a player changes name or
position — the one thing a primary key may never do. But re-keying seven years of history in place is
the migration you do not survive. So: mint the opaque ID, map every current key as an alias,
dual-read and dual-write, prove replay, cut consumers over one at a time, preserve legacy aliases
indefinitely in receipts.

**Urgency:** today `dg_id` is literally `gsis_id` — nflverse currently owns the primary key of the
entire archive.

### Ruling 05 — Fuzzy identity matching

- **P1** ✗ Auto-verify at ≥0.95 confidence; verify at 0.80–0.94 on a team match.
- **P2** ✓ Never auto-promote. Confidence bands survive as review-queue priority.
- **P3** ✓ Review candidates only; production identity needs deterministic corroboration or a human.

**RULING: never auto-promote.** P1's bands are kept, but only to sort the review queue. The codebase
already contradicts itself: `identity/__init__.py:130-189` returns `VERIFIED` straight from a
`difflib` ratio, while `audit/identity_coverage_matrix.py:16` declares fuzzy matching prohibited.

Silent non-matches are the worst class of data bug, because they present as missing data rather than
as errors.

### Ruling 06 — Coverage guarantee

- **P1** ✗ Guarantee a PVO card for 100% of rostered players via a fallback ladder.
- **P2** ✓ The ladder, typed by an availability state machine — a score-bearing state requires a score.
- **P3** ✓ 100% honest *state* coverage, counted over a named, versioned universe snapshot.

**RULING: all three, in that order.** Guarantee 100% honest card **state**, never 100% scores — a
guaranteed card is how you end up fabricating one. P1's ladder is legitimate because its bottom rung
is already an honest `PRE_MODEL` card with receipts, and it runs *inside* P2's state machine so
coverage and truthfulness stop competing.

P3 adds the part neither other doc has, and it is correct: a coverage claim is meaningless without a
named denominator, and "unique players" is not a countable population while identity is unresolved.
Every coverage claim names a versioned `universe_snapshot_id`.

### Ruling 07 — Trade output

- **P1** ✗ Side-value totals with a consolidation penalty (κ=0.04) and a ±10% parity band.
- **P2** ✓ Legitimate as an internal input; no side total, fairness score or winner ever surfaces.
- **P3** ✓ Evidence-grouped scenarios, transparent ordering within a category, no cross-action rank.

**RULING: the math is an input, never an output.** A single fairness number is a verdict wearing a
number's clothes; a sort by desirability is a verdict with a sort key.

Not hypothetical — `compute_delta_status` already emits `"Likely_Favors_You"`, a verdict the decision
contract had explicitly removed. The failure mode is in the product now.

### Ruling 08 — Manager intelligence

- **P1** ✗ A risk-appetite rating and propensity inference per manager.
- **P2** ✓ Observed transaction facts with sample-size disclosure. No inferred psychology.
- **P3** ✓ Same, plus observation window, freshness and uncertainty on every statement.

**RULING: facts only.** A completed-transaction record cannot see declined offers, so a "risk
appetite rating" is a verdict about a person inferred from a censored sample. The 937 recorded
transactions support description — frequency, recency, asset flows, counterparties, positional flows —
not personality. P1's matrix survives with the inference stripped out.

### Ruling 10 — Composite scores are legitimate; ranking ACTIONS is not

**Raised by David, 2026-08-20**, against my own §9 — and he was right.

- **P2** ✗ (as merged) "No single omnibus dynasty score. No ranked action list."
- **P3** ✓ "No *hidden* cross-action rank, while factual and user-selected ordering remains allowed."

**RULING: P3's formulation, and my merge took the wrong one.** The blanket ban bundles two different
dangers — *unearned authority* (a number reading as "do this" with no proven edge) and *collapsed
dimensions* (hiding tradeoffs so you cannot disagree with a component). Cross-positional xVAR is
guilty of neither in construction: every step is disclosed arithmetic on a **single lane's** output, it
never touches market, and it answers a question Superflex makes unavoidable — how do you compare a QB
to a WR? Forbidding the honest version does not remove the comparison; it relocates it into David's
head with worse inputs and no receipt.

Verified: the scarcity multipliers are exactly P90 ratios against a WR anchor and reproduce to three
decimals (`QB 20.1/14.5 = 1.386`, `RB 15.7/14.5 = 1.083`, `TE 9.4/14.5 = 0.648`). Honest derivation.

**The correct line:** a composite of one lane's own outputs, with disclosed construction and a stated
interval, *describing a player*, is legitimate. **Ranking actions by any scalar is not.**

**Three real defects this reframing exposes, none of which is "it is a composite":**

1. **It sorts actions today.** `league_opportunity_map.py:518` orders by `taxi_long_term_value_desc`
   on raw xVAR; `roster_cut_engine.py:171,359` orders cuts by it. That is the actual violation.
2. **Λ has drifted, and TE is materially wrong** — see §4E.1. Every tight end is valued ~8% low in
   every cross-positional comparison the product makes.
3. **It ships without an interval.** `64.2` reads as precise; it is an estimate.

**The deeper lesson, and the reason this ruling exists:** an over-broad law does not merely block
value — it *misdirects attention*. A banned-vocabulary scanner runs across two languages checking
that no surface says "buy". Meanwhile a genuinely wrong TE multiplier ships unnoticed, because the
scanner checks language and the defect is arithmetic. **Over-governance buys false confidence.**

### Ruling 09 — Sequencing and process weight

- **P1** ~ Layer order, eight increments, soft exit gates.
- **P2** ✓ Increment spine ordered by what each stage must *reference*; honesty enforced sixth, not first.
- **P3** ✗ Twelve waves, eleven evidence files per ticket, fourteen approval gates.

**RULING: P2's spine, P3's contracts, David's governance.**

P3 reverses the 2026-08-18 ruling as surely as P1 reverses the PPG ruling. Per-ticket approval gates,
mandatory falsifiers and entry/exit criteria were retired; P3 reinstates all three with interest.

Keep only P3's **material** gates — the ones guarding genuinely irreversible acts: storage cutover,
identity cutover, model promotion, finality authority, `decision_supported` criteria, new paid
sources, and any external write action. Everything else drops to the one habit David kept: **say the
command you ran.**

And take P2's sequencing insight, which is subtle and right: **define the honesty kernel early,
enforce it late** — once receipts and intervals actually exist. *A contract you cannot yet satisfy is
a contract you will learn to bypass.*

---

## 4. What none of them got right

Three findings from checking the proposals against the running system.

### A — The served model is a cross-version pickle (verified live)

All three argue for JSON artifacts on maintainability grounds. None knew the risk is **already
firing**. Engine A's four position models are `.pkl` written by scikit-learn 1.6.1; the installed
runtime is 1.8.0. sklearn raises on every load, and its wording is not decorative:
*"might lead to breaking code or invalid results."*

```
$ .venv/bin/python3.14 -m pytest tests -q
sklearn/base.py:463: InconsistentVersionWarning: Trying to unpickle
estimator Ridge from version 1.6.1 when using version 1.8.0.
This might lead to breaking code or invalid results.

$ ls app/data/models/*.pkl
QB_model.pkl  RB_model.pkl  TE_model.pkl  WR_model.pkl
```

This upgrades the JSON-artifact decision from hygiene to a correctness question about numbers being
served today. Companion to Ruling 02: an artifact whose predictions cannot be reproduced by the
runtime that loads it has no business carrying a receipt.

### B — The venv's default interpreter is the wrong Python

`.venv/pyvenv.cfg` declares 3.14.4, but `.venv/bin/python` symlinks through to the Command Line Tools
system Python — **3.9.6**, with none of the project's packages. Only `.venv/bin/python3.14` is real.
At least four scripts invoke the broken path.

```
$ .venv/bin/python      -c "import sys; print(sys.version.split()[0])"   →  3.9.6
$ .venv/bin/python3.14  -c "import sys; print(sys.version.split()[0])"   →  3.14.4
$ grep version .venv/pyvenv.cfg                                          →  3.14.4
```

P3 quietly writes `.venv/bin/python3.14` into every command it specifies — correct — but never says
why or repairs the cause, so the trap stays armed for anything not copying its exact incantation.
One symlink fixes it.

### C — The test suite is healthy, and was then run

An earlier claim in the authoring session that the test loop was dead (225 of 344 files failing at
collection) was **wrong as a standing condition**. It was a transient macOS code-signature fault
(`library load mig callout failed`), reproduced twice including outside the sandbox, since cleared.

Every proposal listed "whether the test suite currently passes" as explicitly unverified, because no
session had run it. It has now been run in full:

```
$ .venv/bin/python3.14 -m pytest tests -q
17 failed, 6258 passed, 12 skipped, 367 warnings in 356.81s
```

All seventeen failures trace to **uncommitted in-flight work**, not committed code. Fourteen sit in
`tests/contract/test_governed_cadence_inputs_red.py`, which is *untracked* — a lane's intentional RED
tests mid red–green cycle, failing as designed. The other three are OpenAPI snapshot drift, explained
by a modified `frontend/openapi.json` in the same dirty tree.

That tree carries **58 modified or untracked files** across other lanes. This partly rehabilitates the
one piece of P3's Wave 0 that Ruling 09 otherwise trims: knowing what is in flight before you start.
Not as an eleven-file ceremony per ticket — as a single question asked once. Increment 1 rewrites
identity across every store, and beginning that from a 58-file dirty tree with no ownership inventory
is how two lanes silently overwrite each other.

Keep P3's rule as law regardless: **environment failure is a named blocker, not evidence that tests
passed.** And note this repo's `CLAUDE.md` cites 4,335 collected tests as a past measurement — the
tree has grown; the invariant is zero collection errors, never a pinned count.

### D — Adversarial verification overturned two of P2's headline claims

Thirty-six claims carried from the proposals were re-measured by independent verifiers instructed to
**refute** rather than confirm: **22 confirmed, 11 partial, 3 refuted.** Identity, capture-jobs and
trade-verdicts came back fully confirmed — `dg_id` really is `gsis_id`, the difflib-to-`VERIFIED` path
is real, the fifteen normalizers are real, the uninstalled capture jobs are real, `"Likely_Favors_You"`
is real. Two headline claims did not survive — and in both cases the corrected finding is *more
useful* than the original.

#### "No code path can ever set `decision_supported` to True" — REFUTED

It can. `PlayerValueObject` and `RosterAuditSignals`
(`src/dynasty_genius/models/player_value_object.py:47` and `:119`) accept `decision_supported=True` at
construction, serialize it to JSON as `true`, and permit post-construction mutation — proven by
running the code, not by reading it.

The true picture is a real but **incomplete** defense:

- 40 fields are typed `Literal[False]` and reject True outright;
- 15 of 19 `bool = False` fields are coerced back by a `_lock_decision_supported` validator;
- **4 fields are unlocked — including the central `PlayerValueObject` itself** (also
  `feature_validation.py:49`, `qb_rookie_risk_filter.py:53`);
- several publish-time verifiers raise on True.

No caller passes True today, and all 37,233 JSON artifact values are `false` with zero `true`
anywhere. So the product is honest in practice — but the guarantee is a convention with a hole in the
middle, not a structural fact. **That is a concrete ticket the original framing would have hidden.**

Also: the "~40 places" figure is exact only for the reading *"declared as type `Literal[False]`"*.
There are 59 field declarations in total, and the 19 `bool = False` ones are precisely the ones that
matter. Any plan sized on "only ~40 places to change" is undercounting.

#### "The gate is mathematically unreachable" — REFUTED, and the real finding is worse

`CI_WIDTH_MAX = 0.30` is real and wired (`src/dynasty_genius/eval/composite_gate.py:19`, enforced by
`fold_ci_adequate`, imported by `backtest_harness.py:36` and called at `:376`). QB per-fold n is
46/46/49, matching the claim.

But a Spearman CI narrows as rho rises — the "≈0.6 wide" figure holds only near rho ≈ 0 (0.581 at
n=46). The gate opens at **rho ≈ 0.711 (n=46) / 0.698 (n=49) / 0.724 (n=43)**, and the measured QB
models **already clear it**: `scaled_ridge` and `elastic_net` reach Spearman 0.744 / 0.748 on the 2021
fold and 0.740 on 2023. Only the 2022 fold (0.625) falls short.

So the gate is not impossible. It **silently raises the stated Spearman bar from
`SPEARMAN_THRESHOLD = 0.55` to about 0.71** at these sample sizes — a hidden design consequence
nobody chose. And it means the edge question is closer to answerable than P2 implied.

> **Method caveat, carried from the verifier:** the gate reads a BCa bootstrap interval
> (`backtest_harness.py:723`), while the reachability sweep used the Fisher-z analytic approximation
> because real BCa widths require a harness run. BCa widths at n=46 can differ. The direction is
> solid; treat the exact 0.71 as an estimate until the harness confirms it.

#### 4E.1 — ~~Λ multipliers drifted; TE 8.4% wrong~~ **RETRACTED 2026-08-20**

**This finding was wrong and is withdrawn. Do not act on it.** It claimed
`XVAR_LAMBDA_ENGINE_B['TE']` should be 0.703 rather than the shipped 0.648, and that every tight end
was undervalued ~8% in every cross-positional comparison. An adversarial pass caught it; I then
verified the refutation directly.

The three constant families are **algebraically coupled**:

```
dvs             = ppg      / P90[pos] * 100
replacement_dvs = repl_ppg / P90[pos] * 100      (all four reproduce exactly)
lambda[pos]     = P90[pos] / P90[WR]

xvar = (dvs - replacement_dvs) * lambda[pos]
     = (ppg - repl_ppg) * 100 / P90[WR]           ← P90[pos] CANCELS ENTIRELY
```

So xVAR does not depend on the position's own P90, and the P90 drift never reaches cross-positional
comparison. Verified numerically: **20.7746** via the constants versus **20.7586** via the cancelled
form. **Editing lambda alone introduces +8.5% error** — the exact magnitude the finding claimed to
remove, in the opposite direction.

**The real TE defect is the clamp — an ordering problem, not a scaling one.** Because TE's P90 is
understated (9.4 against 10.28 on current data), TE DVS inflates and more tight ends hit the 100
ceiling: **11 of 89 TEs clamped**, against QB 0/37, RB 5/99, WR 6/163. The top of the position
flattens into ties, which is a real defect and a different one. Tracked as SR-17 in the season build
spec, conditional on a checkpoint.

**Rule that follows:** if these constants are ever moved, **all three dicts move together**. A
contract test now guards the coupled identity (SR-13).

**Ruling 02 is unaffected** — constants still need provenance stamps and a recheck cadence. What
changed is that this particular constant was not wrong, and the drift's real consequence is at the
clamp rather than in the scaling.

#### Also corrected, in passing

- **937 transactions, not 932.** The older figure went stale when the 2026 season was re-captured on
  2026-08-08. "Read by nothing in production" is fully confirmed — no route, no read model, no
  materializer, no frontend.
- **The outcome scorer is not survivorship-complete**, contrary to all three proposals. See INC 8.
- **DG-017 confirmed directly.** The served Engine B bundle
  (`app/data/models/engine_b/runs/.../engine_b_v1_1.pkl`) unpickles to a dict of
  `{model: Ridge, imputer: SimpleImputer, features, version, is_validation_only}` — **no scaler** —
  while `backtest_harness.py:489` fits a `StandardScaler`. A scaled model is validated and an unscaled
  one is served. `app/services/engine_b_service.py:151` calls `model.predict(X)` with no scaling step.
  (The agent assigned this cluster died mid-run when the machine slept; measured by hand instead.)
- **Store pathologies confirmed and quantified.** `payload_json` is 81.2% of the 945 MB divergence
  file (803,414,866 of 989,929,472 bytes; 463,899 rows). `nflverse_usage.db` is literally 100% TEXT —
  501 of 501 columns across 15 tables; `playerprofiler.db` is 738 of 740. All four large stores run
  `journal_mode = delete`, not WAL, with zero user-created indexes.
- **Databricks "zero Python references" is literally false** but the substance holds: 2 files carry 4
  textual references, all of them disclaimers stating Databricks is *not* required. No import, no
  dependency, no installed package.

---

## 5. The architecture

One installable package, strictly downward dependencies, a thin HTTP adapter, and a cross-cutting
honesty kernel. `app/` shrinks until it owns no domain logic.

**Placement rule:** *a module lives in the layer that owns the type it returns.* Mechanically checked
with `import-linter` contracts forbidding upward imports and specifically `dynasty_genius.* → app.*`.

| Layer | Owns | Returns |
|---|---|---|
| `kernel` | Measurement, Receipt, AsOf, Caveat, ClaimLevel, availability states | types only |
| `sources` | One adapter per provider; immutable raw capture before parsing | `RawSnapshot` |
| `identity` | Opaque ID minting, bitemporal crosswalk, resolution, review queue | `Resolution` |
| `features` | Dated as-of vintages, leakage guards, one canonical query | `FeatureVintage` |
| `modeling` | Hashed spec, train, evaluate, refit, promote, infer | `Prediction`, `Artifact` |
| `league` | League graph, capacity, posture, transaction facts | `LeagueContext` |
| `market` | Observations, common-cohort divergence, band crossings | `Observation` |
| `decision` | PVO assembly, bounded scenarios, DOO generation | `PVO`, `DecisionOpportunity` |
| `read_models` | Precomputed product projections, published atomically | `Artifact` |
| `serve` | HTTP transport and DTO projection only | `Response` |

### The honesty kernel

Honesty must be a type system, not a review culture — a review culture is one tired evening from
failing. Every product number travels as a `Measurement`: value, unit, interval **or an explicit
`uncalibrated`**, calibration state, lane, `as_of` right edge, and a receipt.

**Lane is a type parameter, not a field**, so model and market values cannot be added — the compiler
refuses.

On top sits the best single idea in the three documents (P3): **claim level is an ordered, composable
type.**

```
descriptive  <  diagnostic  <  replication_candidate  <  decision_supported

composed claim level = min(material input levels, evidence-record ceiling)
```

Composition is fail-closed. No lane borrows freshness, calibration or support from another; ordering
and visual emphasis can never upgrade a claim.

It also replaces a boolean currently defended by four mechanisms of uneven strength — see §4D. One
authoritative `claim_level`, with `decision_supported` demoted to a read-only projection
(`claim_level == "decision_supported"`, never stored as a second source of truth), removes the need
for forty type declarations, nineteen validators and a publish-time verifier to all independently
agree.

---

## 6. Before the plan starts

These do not wait for any increment. Two are losing data permanently; one is a decision, not a build.

### 6.1 Two capture jobs were never installed — IRREVERSIBLE

`league-transaction-capture` and `nflverse-usage-capture` have plists in `ops/launchd/` but appear in
neither `launchctl list` nor `~/Library/LaunchAgents/`. `league_transactions.db` last advanced
2026-08-07.

The codebase states the stakes itself at `daily_control.py:235`: *a transaction not captured is not
recoverable by re-reading — the endpoint serves current state, not an archive.* Every day this waits
is a day permanently missing from the archive that is supposed to be the moat.

### 6.2 The cockpit backup has never succeeded — IRREVERSIBLE

Exit 127; `PATH` cannot resolve `node`. Tower's memory, `dg-build` and Studio's directory have no
second copy. The earlier diagnosis was incomplete: `claude` and `agy` fail the same resolution test,
so fixing node alone will not clear it.

### 6.3 The divergence fix is written and simply not called

`market_divergence_rebase.py:166` recomputes both percentiles on a common cohort and refuses by name
on an empty one — both mechanisms confirmed by *running* it, not by reading it. An exhaustive caller
search finds only ledger prose and tests: **it is called by nothing.**

Two corrections to how the proposals describe it:

- It is **not "complete."** Four of its seven registered review units are recorded not started, and
  its `current_*` baseline uses a different rounding order from the shipped path it claims to
  reproduce exactly — differing on 79 of 336 rows by 0.001, enough to move a boundary case.
- The widely-quoted impact figure — **10.67 pp / 127 of 338 — is disqualified by the repository's own
  record**, which marks it corroboration-only under acknowledged contamination (the answer was
  disclosed before the check). The one independent measurement is **131 of 336 rows / 10.72 pp**, with
  a stated ±1 boundary sensitivity. Cite that, or re-measure. Do not carry 10.67 / 127 forward.

Direction is unchanged: it sits under every divergence-derived surface in the product. (Stale detail
worth not repeating from the July ledgers: the module is no longer untracked — committed in `509ebf3`.)

### 6.4 Census the archive's gaps, and make them a state — IRREVERSIBLE

Per §2: the model lane is missing 2026-08-12, and `market_divergence_history` is missing four days.
Those specific days are gone; nothing recovers them. What is *not* settled is whether the next one
gets noticed.

Two small things. **Run a full gap census** across every capture store and write it down, so the
archive's real shape is a measured quantity rather than an assumption inherited from a sentence. Then
**make `missing` a first-class value** everywhere a date range is read — not an absent row a query
silently steps over. Every belief-archive question in INC 1p spans dates; an answer that quietly
bridges a hole is worse than no answer, because it is confident.

### 6.5 Repair the venv interpreter

One symlink, per §4B. Do it before anything else runs, so every command the crew writes is verifiable
rather than accidentally correct.

### 6.6 The self-consistency clock — the one that changes the calendar

**It needs no new data and no realized outcomes.** This is P2's best product insight and it deserves
to jump the queue. 56 days of captures already support:

- *what did you say then* — any player, any past date, both lanes;
- lane lead–lag — which side moved first, and when they re-converged;
- a stability ledger — which players get revalued most, on which signals (this is how bad signals get
  pruned);
- a decision ledger — pin both lanes on the date of each of the 937 transactions and replay forward.

Proving edge against the market is calendar-gated until finalized 2026 weeks accrue. **This entire
class of value is not.** It is the strongest thing shippable this month, and no competitor can answer
a single one of those questions.

---

## 7. The build plan

P2's spine, ordered by what each stage must reference rather than by layer number. Each increment
opens with contract tests for its boundaries, then dual-writes and shadow-compares against the
existing path. **No big-bang rewrite at any point.**

### INC 0 — Kernel types, wired to nothing

Measurement, Receipt, ClaimLevel with its composition rule, availability states, the source/stream
catalog, the PVO state machine, the DOO schema — typed interfaces and failing tests only. Defined
now, enforced at INC 5.

Also, once and cheaply: **inventory what is already in flight.** 58 modified/untracked files across
other lanes, and INC 1 rewrites identity through every store. One list of which branch owns which
path, before the first migration touches anything.

> **Exit:** every existing stream and product state maps unambiguously onto the new contracts · the
> claim-level suite rejects a composed claim ranked above its weakest material input · no path in the
> plan has two owners.

### INC 1 — Identity, then the point-in-time plane

One versioned normalizer replacing the fifteen currently in five mutually incompatible families —
three fold Unicode while twelve *delete* accents, so `José` → `jos` and can never match `jose`; one
deletes whitespace entirely so its keys cannot be looked up in any other family's index. Then the
opaque ID, then the bitemporal crosswalk, then dated feature vintages.

Crosswalk is deliberately **long, not wide**: `(dg_id, source, source_id, valid_from, valid_to,
method, confidence, normalizer_version, evidence_ref)`. A 22nd provider is an `INSERT`, not a schema
migration.

Feature vintages become `features/feature_set=<v>/as_of=<ts>/position=<p>/*.parquet`, never
overwritten, with "runtime" demoted to a pointer.

*Why first:* every row in every later store carries this key. Migrating storage before the ID is
canonical means migrating twice, and the second one is a re-keying history cannot survive.

> **Exit:** historical as-of queries cannot see future observations · captures replay deterministically ·
> unresolved identity has a complete census over a named universe snapshot · old and new feature
> outputs reconcile within declared tolerances.

### INC 1p — The self-consistency clock (PARALLEL)

Per §6.5. Depends on nothing in the spine. Ships user-visible value while foundation work is
underground — which is also what keeps the plan honest, because a six-month foundation with no
surfaced value is how architecture programs die.

> **Exit:** any player, any past date, both lanes, with receipts — and a replay of all 932
> transactions against what the system believed that day.

### INC 2 — Orchestration and health that cannot lie

The daily pipeline is currently wall-clock offsets — 09:00, 09:15, 09:20, 09:30, 09:40, 09:45 — so
dependency order is sleep-and-hope and a slow upstream job silently feeds stale data downstream.
**That is a correctness bug wearing a scheduling costume.** `daily_control` becomes the single
entrypoint with real dependency edges and a run ledger; launchd merely triggers it. Add P1's
event-driven watchdog for manual drops (PFF, Footballguys) — but with P3's correction: inventory and
validate, then a human accepts the manifest. Do not auto-trust every file appearing in a download
directory.

Health gets teeth: mandatory `status_field` declaration per producer; a non-empty `failures` list must
degrade the verdict; future-dated timestamps rejected; aborted runs grade `producer_failed` rather
than passing on file mtime. And the freshness authority needs a guard against its own staleness — its
report was once eleven days old while reading `exit_code: 0`, having earned that zero by running
nothing.

> **Exit:** a producer killed mid-run causes the health surface to report it degraded within one
> cadence period.

### INC 3 — The Model Trust Plane

Training creates candidates only and cannot move the active pointer. One hashed `TrainingSpec` is the
sole definition of features, target, cohort, preprocessing, estimator and tuning policy — consumed
identically by training, evaluation, refit and serving, with **serving refusing an artifact whose hash
does not match the spec requested.**

JSON artifacts replace the pickles, gated on equivalence tests — which also retires §4A. These are
Ridge models: coefficients, intercept, imputer medians, scaler parameters. Natively JSON, diffable in
git, readable in five years without sklearn.

Evaluation discipline: rolling-origin chronological folds · label windows closing **before** each test
boundary · player-grouped tuning · naïve **and market** comparators · calibration and predictive
intervals · one sealed recent-period set per model generation, never used for feature selection,
tuning or calibration.

Uncertainty is **measured, not modeled**: ship empirical residual quantiles by decile in the artifact;
at inference a prediction maps to its decile and inherits that decile's observed spread. Feeds the
`SpreadBar` primitive that already exists and currently renders only in a dev sandbox.

Promotion order matters (P3's correction to P2): evaluate frozen recipe → refit final candidate on
approved label-complete data → post-fit sanity/calibration gates → promotion receipt naming the exact
final hash → change the active pointer.

> **Exit:** harness and serving produce byte-identical predictions for one fixed row · served hash
> equals the promotion receipt · market remains structurally absent from features.

### INC 4 — PVO materialization and the read model

One immutable daily universe snapshot through the state machine, with the fallback ladder inside it
(Engine B ≥8 games → Bayesian blend at 1–7 → Engine A prior → explicit `PRE_MODEL`). Availability
states: `available`, `withheld`, `not_eligible`, `insufficient_history`, `identity_unresolved`,
`capture_incomplete`, `artifact_unavailable`. Engine routing, score availability, validation grade and
decision support **stop sharing one field**.

Then precompute: the API stops doing work at request time. **Both headline timings have now been
measured directly, and both proposals overstated them.**

- The 52 MB is exact — **53,276,093 bytes** across two uncached artifacts
  (`universe_pvo_runtime.json` 24.3 MB + `universe_market_divergence_latest.json` 28.9 MB), each
  holding 12,222 players. But parsing it costs **0.76 s, not ~9 s** — 0.40 + 0.36 s to load, 0.003 s
  for the linear row scan, banned-vocabulary checks negligible at 0.02 ms.
- `/api/health` costs **16 s, not ~110 s** — 7.96 s for the capture-health adapter plus 8.01 s for
  tier-readiness, two independent unmemoized paths in a single request
  (`system_health.py:189-198`).

The direction is unchanged and the case is undiminished: 0.76 s of uncached parsing on *every Trade
Lab keystroke* makes typeahead unusable whether the figure is 9 s or 0.76 s, and a 16-second health
endpoint the SPA calls on load makes the freshness light David is meant to trust the slowest thing in
the product. Split the four `system_*` routes into an `/ops` router the reader SPA never mounts.

**Are P3's budgets reachable?** Audited against these measurements, because adopting a budget you
cannot hit is how a plan quietly stops being enforced. Player view needs 0.76 s → 250 ms (3x), which a
per-player precomputed artifact delivers trivially — you stop parsing 53 MB to find one row. Health
needs 16 s → 250 ms (64x), reachable only by not touching the stores at all and reading a materialized
summary. Both are precomputation problems, not optimization problems. **The budgets hold — but only if
the materialization is genuine and never degrades into a cache in front of a scan.**

On-demand computation is legitimate **only** for user-parameterized combinatorics (trade packages,
roster scenarios), and even then it composes from the published artifact and never re-derives features.

> **Exit:** every universe member is modeled or carries one truthful, actionable unavailability reason ·
> warmed primary GET p95 ≤250 ms · health summary ≤250 ms with no full-store scan.

### INC 5 — Turn the kernel on

Now — and not before — `Measurement` becomes mandatory, `MetricCell.receipt` becomes required, the TS
client regenerates, and import-linter contracts forbid upward imports and `dynasty_genius.* → app.*`.

*Why not earlier:* receipts exist only after INC 1 and 3; intervals only after 3. Enforcing earlier
means fabricating intervals or shipping a type whose required fields are permanently `Unknown`.

Copy the best mechanism already in the repo: the banned-language gate, where a Python test reads the
frontend's own `banned_vocabulary.json` plus a Node AST scanner in CI. One vocabulary, both sides of
the stack, enforced by the build. Lexical scanners stay as defense-in-depth — never as the primary
mechanism.

> **Exit:** no numeric value can reach a surface without a receipt · the `src ↔ app` import cycle no
> longer exists.

### INC 6 — League graph and Decision Opportunity Objects

League context graph with independently versioned lanes: rules/scoring · rosters, taxi, IR, picks ·
replacement levels · completed transaction facts · manager behavior summaries · posture and horizon.
League format is **captured from source settings and versioned**, not scattered as code constants.

Then DOOs. Each lane is independently `reference(s) | unavailable | not_applicable` with its own
receipt; a scenario declares which lanes are *material* rather than requiring all lanes populated.
Advanced fields — championship utility, liquidity, regret, acceptance probability — are
availability-gated and do not become visible until their estimands are validated.

Scenario order: roster legality/capacity → hold-versus-move → David-initiated trade comparison →
partner evidence panels → waiver replacement gaps → rookie/draft scenarios.

> **Exit:** deterministic fixtures produce explainable options whose player, market, league and manager
> lanes remain independently inspectable · a test proves no hidden cross-action desirability rank exists.

### INC 7 — Morning Room, end to end

One complete journey: Morning Room → opportunity → player evidence → scenario comparison → workspace.
Then consolidate eleven surfaces behind five workflows (Morning Room, Roster, Trade, League, Draft).
Trust/methods and ops move to secondary and `/ops` respectively; the Project Tracker leaves primary
navigation.

First viewport answers the daily question in five seconds, in manager prose, lanes never blended:

```
Your roster overnight: model +0.4% · market −1.1% · 3 rows crossed a band.
```

**Band crossings are the only definition of "changed" that survives the no-verdicts law** — a crossing
is a fact about a disclosed, versioned threshold; a "biggest mover" is a nomination.

One canonical row, composed by every surface:
`rank · position-rank chip · identity · ONE focal value · named-window trend · receipt chips`.

> **Exit:** clear first viewport at 1440px and 390px · quiet, stale, unavailable and changed states all
> designed · keyboard journey, visible focus, zero serious axe violations · no horizontal overflow ·
> no developer language, paths or raw engine tokens in any viewport · source SHA and OpenAPI hash in
> the build manifest.

### INC 8 — Outcome accountability and draft

Attach the finality attestation and let the realized-outcome scorer fire. Confirmed: 501 beliefs
frozen at 2026-08-05 with 501/501 crosswalk coverage, and a real metric surface — within-position
Spearman and Kendall tau-b both carrying BCa bootstrap intervals, plus NDCG. **It waits on a decision,
not on code.** Then the draft workflow and the validated edge registry.

**One correction to carry into the ticket:** all three proposals call the scorer
survivorship-complete and it is not. In the only state reachable in production, a player who played
zero games and simply disappeared is still labelled `realized_outcome_status="observed"` — silently
converting a missing outcome into a real one, and biasing the very scoreboard the loop exists to
produce. Fix it before the first week is graded, not after. Also: the finality check is
case-insensitive and lives in the *schedule* loader (`_default_schedule_loader`), so the gate is
slightly wider than "only the literal `final`".

> **Exit:** forecasts grade forward with complete denominators · evidence levels update without
> rewriting prior claims.

### PILOT — Storage migration (PARALLEL, GATED)

Per Ruling 03, running alongside from INC 1. Migrate one representative all-TEXT store to typed
Parquet and prove: row/key/value parity · as-of correctness · append-only conflict behavior ·
deterministic replay · backup and restore · local query and materialization performance · rollback to
the prior reader.

> **Exit:** an evidence bundle sufficient for a go/no-go — **not** a migration.

---

## 8. David's decisions

Cut from P3's fourteen gates to the acts that are genuinely irreversible or genuinely his. Everything
else runs under near-zero governance, with the crew citing what they ran.

1. **Who is authorized to declare a week final?** The highest-leverage unbuilt thing in the
   repository, and a governance decision rather than an engineering project. The scorer is finished;
   the loader stamps `result_observed_unverified` and only the literal `"final"` settles a week. Name
   the authority and the accountability clock starts.

2. **Approve DuckDB/Parquet — as a pilot, not a migration.** All three converge on local-first and two
   name DuckDB outright. What needs David's word is narrower: authorizing one representative store to
   be migrated *as evidence*, with the real decision deferred until that evidence exists.

3. **Widen the PPG ticket to three sites, and settle zero-snap eligibility.** DG-024 covers two; the
   third is the QB-1 label predicate. Zero-snap should be settled before the next model generation
   rather than discovered inside one.

4. **Databricks — retire it or wire it. URGENT.** Verification escalated this. There is no executable
   Databricks code — no import of `databricks`/`pyspark`/`delta`, nothing in requirements, nothing in
   the venv; the only textual references are two files' disclaimers saying it is *not* required. But
   `infrastructure/resources/jobs.yml` declares job `refresh_genius_state` with
   `pause_status: UNPAUSED`, and its Quartz expression `0 * * * * ?` fires **every minute — 1,440 runs
   a day, 60x the intended rate** (hourly would be `0 0 * * * ?`). Deployment and billing status need a
   network call to confirm. **Check whether this is costing money before ruling on it.** Same
   stale-config treatment for `docs/storage-strategy.md`.

5. **What earns `decision_supported`.** With the claim ladder in place the flag becomes reachable,
   which makes the threshold a real decision instead of an unreachable default. Explicit, fail-closed,
   tied to immutable evidence — and set by David, not by an agent.

6. **All league actions stay human-executed.** Recommended by two of three; worth ratifying once,
   plainly. No automated Sleeper action, ever, without a separate explicit ruling.

---

## 9. What we are not building

Merged restraint list. This matters as much as the build plan — most of these would *feel* like progress.

- No microservices, message queue, streaming platform, or containers. One Python process, one static bundle.
- No cloud warehouse, Delta Lake, Unity Catalog, or MLflow. A dated Parquet directory plus a spec hash is the whole requirement; those tools solve team-coordination problems and there is no team.
- No Postgres — nothing here is concurrent-write.
- No auth or multi-tenancy. There is one user.
- No market data in predictive model training, ever. Market is an overlay, a comparator, and a history lane.
- No deep learning or ensembles. Ridge with disclosed coefficients is *why* drivers can be attributed honestly; a model whose drivers cannot be named cannot carry a receipt.
- No conformal prediction or Bayesian posteriors before the measured empirical band ships.
- No buy/sell/hold verdict · no trade fairness number or winner · no opaque manager ranking · no alerts · no "confidence score".
- **No ranking of ACTIONS by any scalar.** A sort of *moves* by desirability is a verdict with a sort key,
  because an action's worth depends on price, timing, roster fit and counterparty — none of which a
  player-value number knows. See Ruling 10.
- *(Narrowed 2026-08-20. The former blanket ban on "composite scores" is withdrawn — it was drawn in the
  wrong place and would have forbidden the honest version of an unavoidable calculation. See Ruling 10.)*
- No fuzzy identity auto-promotion.
- No intraday streaming — the product's own definition is a point-in-time morning record, and intraday updates would damage the hard right edge.
- No LLM-generated recommendation layer before the evidence spine exists.
- No additional primary UI surface until the Morning Room journey works end to end.
- No big-bang rewrite. Dual-write, shadow-compare, migrate.

---

## 10. Provenance and confidence

**Verified in this session** against the working tree at `c1e8a0c`: the pickle version mismatch, the
venv interpreter, test-suite health and the full-suite result, repository shape, and the DG board
state. Commands are quoted inline in §4.

**Re-measured adversarially:** 36 claims carried from the proposals — 22 confirmed, 11 partial, 3
refuted — with every refutation and material correction recorded in §4D rather than quietly absorbed.

**Timings since measured directly** and both proposals' figures corrected: the player view is 0.76 s
rather than ~9 s, `/api/health` is 16 s rather than ~110 s. P3's performance budgets were audited
against those numbers and hold. The archive gap census in §2 was measured directly from the capture
stores.

**Still unverified, and marked as such:** whether the Databricks bundle is deployed or billing, which
needs a network call to David's workspace · and the exact rho at which the CI gate opens, which rests
on a Fisher-z approximation of a BCa interval. Where a figure drives an irreversible act, **re-run it
before acting on it.**

**Two rulings overturn a proposal on David's authority rather than on architecture.** Ruling 01
restores the all-games PPG decision of 2026-08-19; Ruling 09 restores the near-zero governance
decision of 2026-08-18. Both proposals arrived at their positions honestly; neither had the ruling in
view.

**One correction carried forward:** `.oa3/` is not a stale duplicate — it is a live registered git
worktree nested inside the working tree, which is a different problem with a different fix. It
duplicates every path and inflates every naive file survey; exclude it from audits until it is
resolved.
