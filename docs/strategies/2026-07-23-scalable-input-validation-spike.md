# Research Spike — Scalable, Reusable Input-Validation & Data-Quality

**Date:** 2026-07-23 · **Nature:** research spike (no implementation; does NOT gate D3-b) · **Author lane:** Claude (implementing/spokesperson), with two independent research lanes (external tooling survey + repo-state scan) and a Claude contract-compat read. **Codex** contract confirmation and **Gemini** ingestion-facts flagged where recommended.

## Question David is deciding

D3-a's input validation was hand-hardened over **6 Codex review rounds** against one family of defects (leakage-exclusion invariants · type/finiteness robustness · numeric-edge totality · hostile-value rendering). David has **decided to KEEP full fail-closed-on-all-inputs rigor** (including currently-impossible inputs) because DG may later ingest new, less-trusted sources. The question: **is there a more elegant, scalable, reusable way to KEEP that rigor** — across the remaining QB-1 increments and broader ingestion — instead of hand-hardening each increment? If no clean scalable solution exists, David falls back to "real-data-reachable-correctness-first" (his option B).

## The reframe that decides it (Validated — both lanes independently)

**The 6-round pain is not one problem; it is four, and no single tool covers them:**

| Defect class (from D3-a) | Nature | What can industrialize it |
|---|---|---|
| **(2) type / shape / range / finiteness** | per-record/column **schema** | **Runtime declarative schema** (Pydantic for records, pandera for DataFrames) — the large repetitive half, genuinely commoditizable |
| **(1) leakage-exclusion invariants** (draft-capital never imputed; train-only fit) | semantic/relational **+ pipeline/temporal** | *No schema library covers the pipeline half.* Column-set part → schema/contract; fit-must-not-see-test → bespoke assertion, **proven by property/stateful tests** |
| **(3) numeric-edge totality** (median overflow/underflow) | **algorithm correctness** | *No validation library fixes the median.* The tool that **finds** the edge is a property-based test generator |
| **(4) hostile refusal rendering** (huge-int repr, raising `__repr__`) | **error-path code robustness** | Not schema-shaped. A property-based test generator **finds** it generically |

**Headline:** runtime schemas erase most of class (2). But classes (1-pipeline), (3), (4) — *exactly the ones Codex kept finding one at a time* — are **property/algorithm** problems. The tool that actually changes the "6-rounds-doesn't-scale" economics is **property-based testing (Hypothesis) at the test layer**, not any runtime schema library. The two are **complementary**: runtime schemas guard the boundary; Hypothesis replaces the human adversary who keeps discovering the boundary is thin.

## Repo ground truth (Validated — repo-state lane, file:line)

- **Pydantic v2 is already a first-class dependency** (`requirements.txt:8` → `pydantic==2.13.4`), used pervasively in `app/` with strict `extra="forbid"` contract models. **But NOT in `qb_validation`** (100% hand-written), **and the team has already documented Pydantic's data-validation coercion gaps** (`roster_capacity.py:76` "accepts NaN/Infinity strings by coercion", `:94` "silently ignores extra keys"). Pydantic-for-data is **not a free win** — it needs the same custom-validator hardening.
- **pandera, Great Expectations, Hypothesis: entirely absent** — not declared, not imported, not installed.
- **The real reuse gap:** DG's fail-closed pattern is hand-written gates emitting **named string reasons** with `decision_supported=False`. The two clean seams — `QBValidationFailure` (`errors.py`) + the `guards.py` validators (path/shape/column/temporal/no-verdict) — are **package-local and not yet reused anywhere**. Named reasons are **free strings with no shared enum/registry**, validated only by the RED. Per-subsystem `*Error(Exception)` classes are fragmented (≥6 separate declarations).
- **Leakage-contract precedent already exists** in the model layer: `engine_b_contract.py` (`ENGINE_B_PROHIBITED_FEATURES`, `validate_no_temporal_leakage`), `engine_a_contract.py`, `feature_validation.py` (independent fail-closed integrity gates, multi-failure collect). DG has an in-repo pattern to *extend* for the leakage half — not invent.
- **Data is DataFrame-shaped only at the thin D1/adapter/study-matrix edge** (`study_matrix.py:114` `frame.to_dict("records")`), then drops to list-of-dict immediately. So **pandera fits only that ingestion edge**; `folds.py`/`identity.py`/`status.py`/`qb_ppg_labels.py` are dict-level semantic logic pandera does not replace.

## Contract-compatibility (Validated in-repo; Codex confirmation recommended)

- The **sealed registration pin `37065566a9b3…` hashes only the study-design JSON body** (hypotheses/features/scoring; `head -c 11008 … | shasum` reproduces it exactly). **Validation internals are NOT in the pin** — any validation refactor is **pin-safe**.
- The only contract surface is the **RED behavioral contract**: 24 exact reason-string assertions + the `TypeError` (API-misuse) vs `QBValidationFailure` (data-corruption) split. Anything adopted must **preserve those named reasons and that exception split** or the RED breaks.
- **Hypothesis = ZERO contract risk:** purely additive test layer; it *proves* the existing RED contract holds over a generated space, changing no production code or reason. It would have caught C5/C7/C8/C9/C10 in one property test instead of five rounds.
- **Runtime schema adoption into D3-a** would need an adapter mapping library errors → the pinned reasons + exception split, **and re-opens an already-CLEARed increment** (re-review cost). Better applied at **new boundaries**, not retrofitted into cleared code.

## The three options

### Option A — Property-based testing (Hypothesis) + promote the existing seams to shared infra  ★ RECOMMENDED
- **Add `hypothesis` (dev dependency).** Write the invariants **once** as property tests + `RuleBasedStateMachine` stateful tests: *"every input validates or raises TypeError/QBValidationFailure with a named reason — never a bare exception"*; *"every numeric output is finite or a named refusal"*; *"the draft-capital set is never imputed across any fit/transform sequence"*; *"refusal rendering never crashes."* A reusable strategy library carries to D3-b/c/D4/D5 and future ingestion.
- **Promote the hand-written seams** into a shared `dynasty_genius/validation/` module tested once: the reusable helpers (`_safe_repr`, `_is_finite_real`, total `_median`, plain-string check, named-refuse), a **shared named-reason failure base** (unifying the fragmented `*Error` classes), and a **reason registry** (the free-string reasons get a home). Extend the existing `engine_*_contract` leakage pattern rather than inventing.
- **Cost:** LOW. Hypothesis is additive — **no behavior change to CLEARed D3-a, zero contract/pin risk, does not slow the study.** The seam-promotion is a standalone refactor increment (out of the study's critical path), not mixed with study work.
- **Payoff:** directly cures the "6-rounds" pain — the adversarial-discovery job Codex did by hand is automated and reusable everywhere. Keeps David's full rigor *and* makes it scale.
- **Honest caveats:** Hypothesis is a mindset shift, not infra — you must *articulate* the invariants (the 6 rounds already enumerated them, so this is largely free). Needs `@settings`/deadline + seed policy for CI determinism. The seam-promotion touches multiple subsystems → do it as its own reviewed increment.

### Option B — Runtime declarative schemas at the DATA-INGESTION boundary (new sources)
- **pandera** at the `study_matrix`/adapter DataFrame edge (dtype/range/finiteness/null-policy, `lazy=True` collect-all). **Pydantic** (already present) for record/API and the **new less-trusted external sources** David named — strict mode + `FiniteFloat` + custom validators, catch→re-raise `QBValidationFailure`.
- **Cost:** MEDIUM-HIGH. New dependency (pandera); a named-reason adapter layer; retrofitting D3-a re-opens a cleared increment. Pydantic-for-data needs hardening against its documented coercion gaps.
- **Payoff:** best fit for the **broader ingestion vision** (declarative per-source contracts at the untrusted edge). **But it does NOT touch classes 3/4 and only partially class 1** — so on its own it does **not** cure the 6-round pain.
- **Verdict:** adopt at **new boundaries as they arrive**, not as a retrofit. Over-investing here mistakes the problem.

### Option C — Great Expectations (product-wide ingestion governance)  ✗ NOT RECOMMENDED NOW
- Heavyweight Data-Context/Suite/Checkpoint ceremony; its real value is **Data Docs + multi-team governance**, which a single-user local-first system does not need. Both lanes + external consensus flag it as **over-adopted** for this scale. If ingestion ever moves to Databricks, native **DLT expectations** are the lighter path. **Defer** until a real multi-source + shareable-reporting need exists.

## Recommendation

**Do NOT fall back to David's option B — a clean scalable solution exists and is cheap.** Adopt **Option A now**: Hypothesis (test-layer) is the elegant, reusable, low-cost, **zero-contract-risk** cure for the actual pain, and it lets David **keep full fail-closed rigor while making it scale**. Fold **Option B's runtime schemas in at new ingestion boundaries** as they arrive (pandera at the DataFrame edge; Pydantic — already present, hardened — for external sources), never retrofitted into cleared D3-a. **Defer Option C.**

This does **not** gate D3-b: D3-b proceeds hand-written as before; Hypothesis + seam-promotion land as a **separate, David-sequenced infra increment** whose payoff compounds across every later increment.

## Evidence grades · disagreements · cheapest probe

- **Validated:** the 4-class reframe; Pydantic already a dep + its documented coercion gaps; pandera fits only the thin edge; the package-local/free-string reuse gap; GX over-adoption for single-user; the pin is validation-internals-safe; the RED owns the reasons.
- **Provisional:** *"Hypothesis would have caught C5/C7/C8/C9/C10 in one test."* Strong by tool design and the class-3/4 mapping, but **not yet empirically run in this repo.**
- **Possible shared blind spot** (both lanes are tooling surveys): neither costed the **seam-promotion refactor** across ≥6 subsystems (a real build), the **long-run CI-flakiness/maintenance** of Hypothesis, or how hard **articulating the leakage pipeline-invariant** for stateful testing actually is. Treat A's seam-promotion as its own scoped increment, not a free rider.
- **Cheapest falsifying probe (~1 hr, if David wants proof before committing):** write **one** Hypothesis property test — *"`fit_train_only_imputer` / `_median` never return a non-finite value and never raise a bare exception"* — and run it against a **pre-C5 snapshot** of `folds.py`. If Hypothesis surfaces the huge-int/subnormal/overflow counterexamples automatically, the core claim is confirmed; if not, Option A's premise is wrong.

## Recommended next cockpit action

David decides A / B / C. If **A**: `dg-pm:write-spec` a "reusable validation infrastructure" increment (Hypothesis property/stateful harness + shared `dynasty_genius/validation/` seam-promotion + reason registry), **sequenced after** the immediate QB-1 increments so it never blocks the study — with the ~1 hr Hypothesis probe as an optional de-risking pre-step. **Codex** confirms the contract-surface read (reasons + exception split preserved; pin untouched); **Gemini** supplies ingestion-boundary/freshness facts if/when Option B's new-source schemas are scoped. No commit/push/advance/execution — this brief is a map, not a build authorization.
