# Framing v2 — PFF NCAA passing as a second QB college-production lane

**Lane:** Claude Code · **Supersedes:** v1
**Authored against:** `disposition_pff_ncaa_passing_candidate_claude_v1.md`, accepted 10/10 by Codex
**Status:** v2, returning for independent framing review. **No RED opens on this acceptance.**
**Layers served: 1-2 (ingest + curate).** The layers 1-2 dependency check does not apply — this *is*
layers 1-2; stated explicitly so its absence is not read as an omission (`05` §3).

**The frame changed between v1 and v2.** v1 asked "replace or supplement?". Both were wrong. v2 builds
**two source-qualified lanes plus a reconciliation assessment**, and defers any source *choice* to a
later decision that is David's.

---

## 1. The concrete situation

`00` §Rookie Evaluation Rules ranks QB inputs: draft capital, then age at entry, then
**position-specific production and efficiency**. That third input is served today by CFBD alone.

What is actually known about CFBD's QB passing family, stated without inflation:
- The **code path** was repaired in `968321a` — it now binds identity and refuses ambiguity.
- **Usable coverage after the repair is unknown.** No post-repair refresh has run. The pre-fix
  counts (62/126 populated, `sack_rate` 0/126) come from rows that were misattributed *and*
  mis-scaled: they are **defect evidence, not a coverage estimate**, and v2 does not use them as one.
- The historical block was measured: 25.4% coverage against a registered 50% threshold.

What is known about PFF NCAA passing:
- Passing Summary and Passing Depth are complete **2017-2025**, stable schema.
- `2,954/2,954` QBs reconcile `base_attempts`, `base_dropbacks`, `player_game_count` — this proves
  **internal** consistency between two PFF families on matched rows. It proves nothing about
  PFF↔CFBD parity, GSIS resolution, or coverage of the Engine-A QB cohort.
- `840` PFF ids span NCAA and NFL — **all positions, whole archive**. Not a QB number.

**The question this thread answers:** *do the two sources agree, and where do they differ and why?*
It does **not** answer which source Engine A should use.

## 2. Mislead / nudge risks

- **"Better verified" is not "better predictive."** PFF's reconciliation record describes internal
  consistency. Treating it as evidence of forecasting value is the central risk, and it is seductive
  precisely because CFBD just failed publicly.
- **Impressive denominators standing in for the measurement that decides.** `2,954` and `840` are
  archive-wide; the decision needs **QB-cohort** counts. v1 let the big numbers do argumentative work
  they cannot do.
- **Charted judgment entering as measurement.** PFF carries provider judgments well beyond columns
  named "grade" — accuracy/aimed-pass, big-time throw, turnover-worthy play, pressure attribution,
  thrown-away/hit-as-threw. A "grade" denylist would let all of these through.
- **Silent cohort change.** Filling CFBD gaps with PFF values would make **source choice endogenous**
  to the modeled population — the cohort changes without anyone deciding it should.
- **Silent era truncation.** PFF passing starts 2017; the training cohort may reach earlier.
- **Vendor disagreement is not vendor error.** A mismatch most likely exposes a different
  **denominator**. Definitions before values.
- **Paid-source dependency** is a durability decision for David, not a data decision for us.

## 3. Falsification seeds for the RED

1. **Identity injectivity, archive-wide and temporal.** Refuse when one PFF id maps to conflicting
   humans *across files or seasons* — not merely within a file. The 17 observed name changes were
   *interpreted* as aliases; interpretation is not a contract. PlayerProfiler taught this at cost:
   its vendor id was not one human, and only a cross-file check found it.
2. **Edge-level identity basis.** Two distinct edges, never merged: `pff_vendor_id` for NCAA↔NFL
   (vendor-carried), and a **named inferred/reviewed basis** for PFF↔GSIS (a cross-vendor join, even
   though PlayerProfiler's GSIS is itself vendor-supplied). **No resolved output when either edge is
   ambiguous.**
3. **Season scope registered per source**, with refusal on unmatched-scope comparison. Local NCAA
   passing files are `REGPO`; what CFBD's compared totals include must be established, not assumed.
4. **Objective box-stat allowlist**, everything else excluded by default. A test fails if any
   non-allowlisted PFF column reaches a comparison field. Charted metrics are separately named
   hypotheses, never denylist survivors.
5. **Era boundary measured.** Compute the exact training/outcome window and state what happens before
   2017. Silent cohort truncation refuses.
6. **No coalescing.** Two source-qualified lanes with **independent missingness masks**; no
   precedence, no fallback order, no blended field.
7. **Raw immutability + deterministic vintage selection.** Repeated exports must be preserved. (The
   three-hash 2017 specimen was **NCAA Receiving Depth** — cross-family vintage risk, not a claim
   that Passing drifts.)
8. **Denominator accounting** on every comparison row: what each source counted, over what scope,
   with what population.
9. **Discovery vs acceptance.** A deterministic stratified fixture develops the contract; acceptance
   requires **every eligible GSIS-resolved overlap row**. No magic minimum N.

## 4. Overclaim check against the No-Verdict Line

Curating a source and comparing it to another makes **no claim** that any derived feature has value.
`decision_supported=False` holds; no tier, grade, rank or player-facing value moves. The comparison
artifact reports agreement, disagreement, coverage and denominators — it does **not** name a winner.
Under `00` §Backtesting and `01` §Validation Gates, **feature promotion requires a pre-registered
validation David ratifies**; that is a separate word, after this, and v2 does not pre-authorize it.

## 5. Boundary — where this thread ends

immutable raw PFF export → explicit source/scope normalization → **bounded** QB identity mapping with
recorded basis → parallel PFF/CFBD comparison artifact with full-overlap coverage and denominator
accounting.

**Nothing beyond that:** no coalesced training field, no feature promotion, no model run, no paid
refresh, no active CSV change.

**Explicitly not absorbed:** the all-position `840`-id NCAA↔NFL bridge is a **separate
identity-substrate thread**. This one takes only a bounded, reviewable QB→GSIS mapping for its own
cohort.

## 6. What David gets, and when

Not a recommendation. A measured answer to *"do these two sources agree about the same
quarterbacks, and where they disagree, is it a different denominator or a different fact?"* — with
coverage on both sides. **Whether Engine A then uses one, both, or neither is his decision, informed
by that artifact and gated behind a pre-registered validation.**
