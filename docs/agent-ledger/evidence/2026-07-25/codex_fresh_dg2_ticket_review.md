# Fresh independent review — DG 2.0 ticket backlog v2

## Scope and standard

This review uses only:

1. `docs/superpowers/specs/2026-07-25-dg-2-0-dynasty-horizon-rebuild-design.md`
2. `docs/superpowers/plans/2026-07-25-dg-2-0-ticket-backlog.md`

I did not verify any locator, measurement, ruling, hash, source availability, or claim against any third source. A locator below is therefore judged only on whether these two documents provide it, not whether it is correct.

Applied standard: a ticket should state the problem and why it matters, give enough locators/data/context to begin, state real constraints, and provide objective acceptance criteria. It should not choose the technical design, implementation sequence, tool/library, problem-solving method, or method of testing.

## Executive verdict

**3 PASS / 12 WEAK / 26 FAIL across all 41 numbered tickets.**

The backlog is materially improved as a program narrative, but it is still not an executable backlog under the stated ticket standard. It repeatedly turns acceptance criteria into mini-designs, lets developers declare decisive tolerances after seeing the work, gives “report it,” “declare a ceiling,” or “carry a caveat” as substitutes for solving the problem, and contains a fatal backward dependency from Sprint 3 into Sprint 5.

## Verdict for every ticket

| Ticket | Verdict | Specific reason |
|---|---|---|
| DG2-S0-01 | **WEAK** | Clear measured problem, artifact locator, and numerical finish criteria. It prescribes the verification method (“a second lane”) and an exact reporting format rather than only the required confidence in the result. |
| DG2-S0-02 | **FAIL** | Combines three jobs: quantify engine mixing, correct documentation, and rerun the age association by engine. Its conditional dependency is discovered only after doing the ticket, and its AC is a work plan rather than one finish line. |
| DG2-S0-03 | **WEAK** | Clear documentation defect and binary result, but it explicitly prescribes a repo-wide grep as the test method. “Every occurrence” also has no bounded locator set in the two documents. |
| DG2-S0-04 | **WEAK** | The audit problem and minimum consumer locators are good. It prescribes the deliverable schema and the exact contract-test approach. It also says “every consumer” while the named-artifact table gives four consumers but does not establish that they are exhaustive. |
| DG2-S0-05 | **PASS** | Clear mismatch, quantified provider/league context, concrete same-date comparison, separate rank/currency measurements, numerical falsifier, and a provenance constraint. The requested measurements define the evidence needed rather than an implementation. |
| DG2-S0-07 | **PASS** | Finite seven-source scope, clear why, explicit evidence fields, access/terms constraints, and a safe UNKNOWN state. A fresh assignee can tell when all seven rows are complete. |
| DG2-S0-08 | **FAIL** | “OPEN-ENDED,” “floor, not a ceiling,” and permission to return unnamed sources give no finite search universe, effort bound, stopping rule, or testable completeness criterion. This ticket can never be proven done. |
| DG2-S0-09 | **FAIL** | “Actual status” is undefined, the asserted status has no supporting locator within the two documents beyond the external ruling path, `PRODUCT_BRIEFING` has no file locator, and “downstream docs” is an unbounded universe. |
| DG2-S0-10 | **WEAK** | The problem, two starting source families, required evidence dimensions, and negative result are useful. “For each reachable source” has no finite candidate set or stopping rule, so the completeness of the obtainability statement cannot be tested. |
| DG2-S1-01 | **FAIL** | “Decide the mathematical form” is broad while the AC precommits to a “summation property `V(W)`,” even though S1-02 is supposed to decide per-season versus aggregate. It overlaps S1-02 and prescribes part of the answer. |
| DG2-S1-02 | **WEAK** | This is a legitimate decision ticket with alternatives and a clear decision record. It nevertheless mandates a specific directly-fit comparison and rejection threshold as the problem-solving/test design. |
| DG2-S1-03 | **WEAK** | The decision and double-counting problem are clear, but the ticket fixes the decomposition buckets and modelling procedure. “Plausible range” is undefined and carries the escalation decision. |
| DG2-S1-04 | **WEAK** | Clear anti-steering purpose and finite required benchmark content. Hashing, ledger recording, and the exact pre-fit sequence prescribe the control mechanism rather than merely requiring tamper-evident preregistration. |
| DG2-S2-01a | **FAIL** | The AC can be satisfied without ingesting useful data by writing “a statement of the true ceiling.” “True ceiling” is not provable, and neither the source nor the destination asset is located. |
| DG2-S2-01b | **FAIL** | “Every mature class already on disk” and “points” are undefined, and the outcome table has no path in the backlog’s named artifacts. A developer cannot determine the exact row universe or scoring contract from these documents. |
| DG2-S2-01c | **FAIL** | “Last mature season,” “non-censored arc,” and “censoring flag correct” have no definitions or locators. There is no objective row-by-row finish line from the supplied context. |
| DG2-S2-01d | **FAIL** | “Games available” is a material denominator with no definition, “the ingested range” is undefined, and the canonical `player_id` contract is not located. Those are prerequisites, not developer implementation choices. |
| DG2-S2-02 | **WEAK** | Clear measured shortage and numerical target. “Written statement of the obtainable ceiling” is not objectively provable, “monthly observations” does not state whether they must be consecutive or distinct capture dates, and this ticket paradoxically can rescope an already hash-frozen S1 benchmark. |
| DG2-S2-03 | **FAIL** | Combines a manual ingestion workflow with a staleness/surfacing feature. “Repeatable” is unmeasured and the developer may declare any max age after implementation, making the decisive threshold self-selected and gameable. |
| DG2-S2-04 | **FAIL** | It has no problem statement. Reporting coverage has no minimum acceptable coverage, so nearly empty data can satisfy the AC. The inherited granularity may itself be designation-only, at which point the ticket merely rescoping S3-06 is not an ingestion finish line. |
| DG2-S2-05 | **WEAK** | The adequacy counts and PASS/AMEND safe result are concrete. The ticket also assigns runtime consumer refusal behavior, a second implementation problem, and unnecessarily depends on the market time series, which is not part of position-by-age production-sample adequacy. |
| DG2-S3-01a | **FAIL** | It precommits to a per-season `E[v_i,t]` even if S1-02 chooses aggregate shape. “Calibration reported” has no metric or acceptable tolerance, so a badly uncalibrated estimator can be done. A pinned seed is prescribed HOW. |
| DG2-S3-01b | **FAIL** | It mandates a survival-model decomposition before the thesis decision and provides no calibration threshold. “Shown unbiased” is undefined; no effect-size, interval, or tolerance says when that showing succeeds. |
| DG2-S3-02 | **FAIL** | The ticket asserts that a single rate is wrong, mandates per-position parameters, and says they are “never fit,” even though S1-03 may decide that no discount exists. It is a preselected technical solution, not a problem ticket. |
| DG2-S3-03 | **WEAK** | Excellent quantified defect and outcome-based no-bound constraint. The referenced “trade-math regression suite” is not located, “passes unchanged” does not address a non-green baseline, and the ticket prescribes both the regression method and record stamping. |
| DG2-S3-04 | **FAIL** | “Optimal” has no objective function, so the central result cannot be tested. “Existing refresh budget” has no number or locator. It also combines the optimizer with a downstream 12-label impact publication. |
| DG2-S3-05 | **FAIL** | Combines eligibility-state semantics with taxi conversion-cost valuation, without defining the cost’s unit or effect. Its dependency on S5-02 creates a fatal sprint-order cycle. |
| DG2-S3-06 | **FAIL** | The decisive minimum difference is whatever “the ticket declares,” allowing the implementer to choose it after seeing results. It also adds a separate two-season-versus-ten-season interaction study jointly with S4-03. |
| DG2-S4-01 | **FAIL** | It has no problem statement or why. The AC says what to compute but the defect is only inferable by reading S0-01/spec context, and it prescribes a contract-test implementation. |
| DG2-S4-02 | **FAIL** | “Declared tolerance” and even the calibration-error metric are not frozen here, so the implementer can choose a passing standard after seeing errors. It also mandates decile calibration and requires a linear approach to fail, precommitting the test result. |
| DG2-S4-03 | **FAIL** | It has no problem statement. It combines value aggregation, interaction/presentation behavior, labeling, and a default-view product decision. “Without contradiction” is subjective and has no testable definition. |
| DG2-S5-01a | **FAIL** | It has no problem statement and prescribes the stream-based technical answer. “With its own uncertainty” has no uncertainty representation, calibration, coverage, or tolerance. |
| DG2-S5-01b | **FAIL** | It combines three distinct valuation problems. The AC explicitly permits “not priced,” so the ticket can be closed without solving any of them; flooring at zero is a safe runtime state, not a completed valuation ticket. |
| DG2-S5-01c | **FAIL** | “Validated” has no sample, metric, or tolerance. The alternative AC is simply to declare the bridge unvalidated and attach a caveat, so the underlying bridge problem need never be solved. |
| DG2-S5-01d | **FAIL** | It combines unresolved residual dispositions with a separate semantic estimand ruling. The plan is identified only by a hash, not a path, and the external David decision blocks the work before a fresh developer can resolve the primary estimand. |
| DG2-S5-02 | **WEAK** | Strong measured problem, four locators, exact freshness threshold, and observable before/after result. It combines capture selection with a separate staleness-surfacing capability, and “the 4 wrong labels” is a historical measurement that may not remain the exact live count tomorrow. |
| DG2-S5-03 | **FAIL** | It dictates “exactly one module,” call-site structure, a contract test, and CI enforcement. The real WHAT is authoritative agreement across consumers; the ticket instead fixes the code architecture and test implementation. |
| DG2-S5-04 | **FAIL** | “Wherever player value is shown” has no enumerated surface set or locators. It combines injury-state display with starter-eligibility correctness and prescribes a design-process workflow. Its dependency on the full taxi-semantics ticket is broader than the IR problem. |
| DGX-02 | **WEAK** | Clear risk, finite named stores, and observable restore outcome. It prescribes full-download/SHA-256/no-sampling verification, restore-drill technique, and anti-rot testing. “Current verification strength,” “its window,” and the anti-rot test have no locator or numeric bound in these documents. |
| DGX-03 | **FAIL** | The problem is an undeclared dependency, but the ticket mandates the exact remedy (“pin SciPy”), a fresh-environment resolution procedure, execution order, and a separate PR. This is textbook HOW and tool/package-management design. |
| DGX-04 | **PASS** | Precise failure mode, exact code locators and consumers, honest preventive scope, and binary required behavior: unavailable rather than zero-width, and refuse rather than auto-pass. It leaves representation and implementation open. |

## Every remaining prescription of HOW

The quotes below are the places I classify as prescribing a technique, artifact/code structure, execution sequence, library choice, or test method. Ordinary domain constraints and observable behavior are not included merely because they are precise.

- **DG2-S0-01:** “the reclassification count is reproduced by a second lane to within ±2 rows”; “both the current and rebased average delta are reported to 2 dp.”
- **DG2-S0-02:** “the per-engine share ... is counted exactly”; “a per-engine breakdown of the age association is reported.”
- **DG2-S0-03:** “a repo-wide grep for the stale phrasing returns zero hits.”
- **DG2-S0-04:** “a table of consumer → field read → basis → which of the following fixes repairs it”; “fails a contract test.”
- **DG2-S0-05:** “the provider's accepted parameters enumerated from its own documentation”; “a shape-matched request compared against the current one on the same date”; “reported separately for rank mode and currency mode, as max and mean absolute change in percentile and in value.”
- **DG2-S0-07:** “one row per source with”; “what its terms permit, quoted.”
- **DG2-S0-09:** “a sweep of downstream docs that inherited the error.”
- **DG2-S0-10:** “A source is only ‘reachable’ if a read has actually been performed.”
- **DG2-S1-01:** “the summation property `V(W)` stated explicitly.” This dictates a property of the selected design before S1-02 resolves shape.
- **DG2-S1-02:** “summed `V(1..2)` vs a directly-fit `V(2)` differing by > 10% of the pooled SD.”
- **DG2-S1-03:** “each of the six bundled components ... assigned to exactly one of {survival term, rent term, window, discount rate, nowhere}”; “the discount is never FIT. Set, declared, sensitivity-tested”; “a fitted discount fails a contract test.”
- **DG2-S1-04:** “the document hash recorded in the ledger before any fit.”
- **DG2-S2-01a:** “provenance stamped per row”; “fails a row-count contract test.”
- **DG2-S2-01c:** “censoring flag correct per row”; “fails a contract test.”
- **DG2-S2-01d:** “joinable ... on the canonical `player_id`”; “an unjoinable row goes to triage.”
- **DG2-S2-02:** “provenance and cadence stamped”; “a gap in the series is visible in the artifact rather than interpolated.”
- **DG2-S2-03:** “a documented, repeatable export→ingest procedure”; “a provenance stamp per import”; “a staleness signal with a declared max age.”
- **DG2-S2-04:** “injury records joined to player-seasons at the granularity DG2-S0-10 established”; “unlinkable injury rows go to triage with a count.”
- **DG2-S2-05:** “any consumer evaluating into it refuses by name.”
- **DG2-S3-01a:** “produce `E[v_i,t]` per season, per player, in an unclamped unit”; “reproducible from a pinned seed”; “per-season calibration reported at each horizon.”
- **DG2-S3-01b:** “produce `S_i,t`”; “the definition of ‘useful’ declared before fitting and not derived from the value measure”; “survival estimated on survivors only must be shown unbiased against the full cohort including exits.”
- **DG2-S3-02:** “per-position parameters declared (never fit)”; “the sensitivity range from S1-03 tested and its ranking impact reported”; “a fitted rate fails a contract test.”
- **DG2-S3-03:** “the trade-math regression suite passes unchanged”; “every consumer in the DG2-S0-04 audit verified against the new unit”; “a value that hits any bound is stamped as bounded in its record.”
- **DG2-S3-04:** “Starter strength from the OPTIMAL lineup”; “a lineup that is optimal-but-illegal fails a contract test”; “the before/after change to all 12 posture labels is published.”
- **DG2-S3-05:** “every rostered player carries an eligibility state (active / IR / taxi)”; “taxi conversion cost is represented explicitly.”
- **DG2-S3-06:** “an availability term `A_i,t` produced per player-season”; “test jointly with DG2-S4-03”; “gets a declared cohort default.”
- **DG2-S4-01:** “a contract test refuses a non-common-cohort run.”
- **DG2-S4-02:** “calibration error reported by decile”; “top and bottom deciles held to the same declared tolerance as the middle”; “a linear conversion must fail this test.”
- **DG2-S4-03:** “two players that invert under two windows are shown both ways, each labelled with its window”; “dynasty-horizon remains the default view.”
- **DG2-S5-01a:** “derived from the stream beginning at the rookie's debut season, with its own uncertainty.”
- **DG2-S5-01c:** “validated against observed rookie-draft slots”; “carried as a caveat on every emitted pick value.”
- **DG2-S5-01d:** “v3 hashed and recorded.”
- **DG2-S5-03:** “computed in exactly one module”; “a contract test fails if a second call site recomputes either”; “fails the contract test at CI.”
- **DG2-S5-04:** “Visual surface ⇒ design-foundation load + framing pass before implementation.”
- **DGX-02:** “full download + sha256, no sampling”; “a restore drill passes end-to-end”; “the anti-rot test still passes.”
- **DGX-03:** “pin SciPy”; “scipy pinned”; “a fresh-environment resolve reproduces the pinned version”; “sequence BEFORE study execution”; “dependency changes ride their own PR.”

## Tickets without a testable finish line, or with undefined threshold words carrying a real decision

- **DG2-S0-08:** no stopping rule for an explicitly open-ended search.
- **DG2-S0-09:** “actual status” and “downstream docs” are undefined/unbounded.
- **DG2-S0-10:** “each reachable source” has no finite universe.
- **DG2-S1-03:** “plausible range” controls whether ranking movement is escalated, but plausibility is undefined.
- **DG2-S2-01a:** “true ceiling” is not objectively establishable.
- **DG2-S2-01b:** “mature class” and the scoring meaning of “points” are undefined.
- **DG2-S2-01c:** “last mature season,” “non-censored arc,” and “correct per row” are undefined.
- **DG2-S2-01d:** “games available” and “ingested range” are undefined.
- **DG2-S2-02:** “obtainable ceiling” has no required proof; “monthly” does not establish continuity.
- **DG2-S2-03:** “repeatable” has no criterion, and “declared max age” lets the implementer choose the gate.
- **DG2-S2-04:** coverage is merely reported; no coverage floor defines acceptable ingestion.
- **DG2-S3-01a:** calibration is merely reported; no metric or acceptable error defines done.
- **DG2-S3-01b:** “calibrated” and “shown unbiased” have no tolerance.
- **DG2-S3-03:** “trade-math regression suite” is unlocated and “passes unchanged” has no baseline rule.
- **DG2-S3-04:** “optimal” lacks an objective function; “existing refresh budget” lacks a number/locator.
- **DG2-S3-05:** “taxi conversion cost is represented explicitly” does not define the cost or its effect.
- **DG2-S3-06:** “the term's own declared minimum resolution” is self-selected after the work.
- **DG2-S4-02:** error metric and “declared tolerance” are not frozen.
- **DG2-S4-03:** “without contradiction” is subjective.
- **DG2-S5-01a:** “with its own uncertainty” has no representation or quality criterion.
- **DG2-S5-01b:** “priced” is undefined, and “or explicitly not priced” permits non-solution.
- **DG2-S5-01c:** “validated” has no sample, metric, or threshold; a caveat is accepted instead.
- **DG2-S5-01d:** residuals are not located by path, and the semantic ruling is external and pending.
- **DG2-S5-04:** “wherever player value is shown” is an unenumerated surface universe.
- **DGX-02:** “current verification strength,” “its window,” and “anti-rot test” lack locators/limits.

## Tickets that combine two or more problems

- **DG2-S0-02:** engine-share measurement + documentation correction + per-engine age analysis.
- **DG2-S2-03:** manual export/ingest workflow + freshness policy/surfacing.
- **DG2-S2-05:** offline sample-adequacy verdict + runtime refusal behavior in every future consumer.
- **DG2-S3-04:** lineup optimization + downstream posture-label impact study.
- **DG2-S3-05:** IR/taxi eligibility semantics + taxi opportunity-cost valuation.
- **DG2-S3-06:** availability model + horizon-length interaction study.
- **DG2-S4-03:** window aggregation + UI comparison/labeling + default-view decision.
- **DG2-S5-01b:** draft-and-cut value + pick liquidity/trade value + rookie-as-chip option value.
- **DG2-S5-01d:** six residual dispositions + a separate floored/unfloored estimand ruling.
- **DG2-S5-02:** selecting the freshest capture + adding stale-state surfacing.
- **DG2-S5-03:** centralising starter strength + centralising posture.
- **DG2-S5-04:** injury visibility + starter eligibility correctness.

## Dependency defects

### Missing dependencies or missing work nodes

1. **S1-04 freezes the market benchmark before S2-02 establishes whether the market series exists.** S2-02 says a ceiling of four points causes “the benchmark in DG2-S1-04” to be rescoped, but the sprint order requires S1-04 to be hash-frozen before S2 begins. The graph needs S2-02 before the freeze, or a formally defined amendment/re-freeze path.
2. **S0-09 is omitted from the Sprint-0 exit gate.** The gate can close while the false source constraint remains, even though S2-03 later depends on its correction.
3. **S4-02 omits S0-04 despite S0-04 explicitly saying it blocks S4-02.**
4. **S3-02 is not conditional on S1-03 choosing a discount.** If S1-03 selects no discount, S3-02 has no valid work but still appears mandatory in the sprint.
5. **No ticket produces `rent_t` or the final aggregate `V_i(W)`.** The spec's core value includes `rent_t`, yet Sprint 3 builds production, survival, discount, ceiling, lineup, eligibility, and availability without a roster-rent producer or a ticket assembling the complete dynasty-horizon quantity.
6. **S4-03 omits S3-02 when a discount is selected and has no possible dependency for `rent_t` because that ticket does not exist.**
7. **S5-01a depends only on S3-01a and Year-1 outcomes.** A pick’s production value derived from the spec’s value stream also needs survival (S3-01b), availability (S3-06), any selected discount (S3-02), and the missing rent/aggregation work.
8. **S5-01d does not block S5-01a/b/c.** Its own problem says no candidate may be fit before v3, but the graph contains no dependency enforcing that.
9. **S5-01b has no dependencies at all.** At minimum its pricing work must respect the pending S5-01d estimand ruling; its relationship to the bridge in S5-01c and the calibrated currency work is also unstated.
10. **S5-01c does not block any emitted pick value.** The ticket permits an unvalidated bridge caveat, but the graph does not say which pick producer consumes either the validated bridge or the caveat.
11. **S5-04 omits S0-10 even though S0-10 explicitly says it blocks S5-04.**
12. **There is no current-injury-feed node for S5-04.** Historical player-season injury ingestion (S2-04) and roster eligibility semantics (S3-05) do not by themselves establish a current, refreshable injury/IR source for every value surface.

### Unnecessary or overconstraining dependencies

1. **S3-05 → S5-02 is fatal overconstraint.** Eligibility semantics can consume a versioned snapshot without first changing all four surface consumers. Requiring the Sprint-5 surface fix before the Sprint-3 semantics ticket creates a deadlock under the binding sequential sprint rule.
2. **S2-05 → S2-02 is unrelated to its stated adequacy question.** Market time-series depth does not determine whether production/injury data have ≥30 player-seasons per position × age band.
3. **S1-01 → S0-08 makes an unbounded source sweep a blocker for the thesis.** Because S0-08 has no stopping rule, S1-01 inherits an uncloseable dependency. A thesis can state prerequisites and allow S2 to reject it without proving that every possible source was searched.
4. **S4-01 → S0-04 overconstrains computation.** The common-cohort rank result can be built and measured once S0-01 and the value producer exist; the consumer audit is a shipping/rollout dependency, not a necessary dependency for the rank computation itself.
5. **S4-02 → S3-03 overconstrains calibration.** Calibration should use the unclamped producer output; it need not wait for every downstream consumer to be migrated off the old ceiling. Depending directly on S3-01a and treating S3-03 as a shipping dependency would preserve parallelism.
6. **S5-04 → all of S3-05 is broader than necessary.** Current IR visibility should not wait for taxi conversion-cost semantics. It needs the IR/current-status portion, which should be a narrower dependency.
7. **S0-10's declared block on S5-04 is also potentially overbroad.** S0-10 is a historical injury/availability obtainability study; current IR state may come from the league snapshot. The backlog does not establish that the historical study is necessary for the live display.

## Sprint-gate testability

The two documents disagree on some gates. Because the spec calls itself the “program of record” while the backlog supplies revised binary gates, no reviewer can objectively apply a conflicting gate without first deciding which document governs.

### Sprint 0 — **NOT objectively testable**

- The backlog requires artifact/population/horizon statements for S0-01 through S0-05. That shape does not naturally apply to the S0-03 documentation correction or S0-04 consumer audit.
- S0-08 is explicitly open-ended, so its required document cannot be proven complete.
- The backlog says failure blocks Sprint 4, while the spec says no comparison work proceeds until Sprint 0 closes and the global sequence says no later sprint starts. Those are different consequences.
- S0-09 is not part of the gate at all.

### Sprint 1 — **NOT objectively testable**

- Hashes and ledger entries are observable.
- “Codex has issued an enumerated CLEAR” is a human judgment, not an objective content threshold. Enumeration proves only that checks were listed, not that the thesis meets a fixed standard.
- “In a form David can rule on” remains subjective.

### Sprint 2 — **CONDITIONALLY objective, but internally awkward**

- Counts of ≥30 player-seasons per declared position × age band and ≥1 observed season are objectively testable if S1 has enumerated every relevant band.
- The safe AMEND result is explicit.
- However, the gate simultaneously requires ≥30 in every relied-on band and ≥1 in an extrapolated band; if a band is relied on, ≥1 adds nothing. The documents should state whether the ≥1 rule applies to a different class of band.
- The spec itself gives only “prove the sample supports what the thesis assumes” without these thresholds, so the controlling source still needs clarification.

### Sprint 3 — **Conditionally objective in the backlog; conflicting in the spec**

- If S1-04 really freezes a primary metric, direction, margin, and all three benchmark definitions, “win or tie against all three” is calculable.
- The spec gate merely requires CLEAR plus benchmark comparisons “naming losses as well as wins”; it does not require a win/tie. The backlog explicitly says that older permissive gate is fixed, but the spec remains the program of record. As written, the same result can pass one document and fail the other.

### Sprint 4 — **NOT objectively testable**

- “Both modes reproduce” has no repeatability tolerance or prescribed comparison.
- “Declared tolerance” is not required to be frozen before calibration results are seen, and the calibration-error metric is unspecified.
- The spec says “both modes correct,” which is even less objective.

### Sprint 5 — **NOT fully objectively testable**

- The zero-floor safe default is objectively observable.
- “Demonstrably priced” is undefined for each of the three economic branches.
- “Every surface” is not enumerated for injury/value presentation.
- “Freshest capture” and the 26-hour signal are objective for the four named snapshot consumers, but those criteria do not make the entire combined gate objective.

## Single worst remaining problem

**The dependency graph deadlocks the epic.** The spec says no sprint may start until the previous sprint’s exit gate is closed. S3-04 depends on S3-05; S3-05 depends on S5-02; S5 cannot start until S4 closes; S4 cannot start until S3 closes. The sequencing note offers a possible David-approved lift of S5-02, but explicitly says that lift is only a recommendation, has not been ruled on, and has not started. Therefore the backlog as written has no authorized path through Sprint 3.

## Could a developer knowing nothing start Sprint 0 tomorrow?

**No, not as written.** First, both documents say the backlog is DRAFT and explicitly authorize no implementation or ingestion. Even assuming David authorizes Sprint 0 tomorrow, the developer could begin S0-01, S0-02, S0-04, S0-05, and the two-source investigation in S0-10 from the supplied locators/context, but would stall at these exact points:

1. **S0-08 completion:** there is no stopping rule for the open-ended source sweep, so the developer cannot know when it is done.
2. **S0 exit-gate closure:** the gate demands artifact/population/horizon statements for S0-03 and S0-04 even though those tickets do not define such measurement objects.
3. **S0-09 location and truth standard:** `PRODUCT_BRIEFING` is not given a file path, “downstream docs” is unbounded, and “actual status” is not defined by evidence available within the two documents.
4. **S0-10 completeness:** “each reachable source” has no finite candidate universe; the developer can investigate the two named source families but cannot prove the sweep complete.
5. **Gate authority:** the developer cannot tell whether an incomplete Sprint 0 blocks Sprint 1, only Sprint 4, or “comparison work,” because the spec, backlog gate, and global sequential rule say different things.

So a fresh developer can perform useful Sprint-0 investigation, but cannot objectively finish Sprint 0 or advance the program without backlog clarification and authorization.
