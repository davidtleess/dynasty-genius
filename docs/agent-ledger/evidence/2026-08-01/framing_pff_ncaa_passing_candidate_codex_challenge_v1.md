# Adversarial challenge — PFF NCAA passing candidate framing v1

**Artifact reviewed:**
`docs/agent-ledger/evidence/2026-08-01/framing_pff_ncaa_passing_candidate_claude_v1.md`  
**Reviewer:** Codex  
**Disposition:** **CHALLENGE — ten defects; no RED opens**

## Findings

1. **The CFBD coverage premise is not established after the repair.** Lines 18–22 use pre-fix
   `62/126` and `0/126` counts to conclude the repaired family is thin. Those rows are compromised by
   identity collision and scaling defects; no post-`4d8127d` refresh ran. The code is now honest,
   but usable coverage is unknown. Treat the old counts as defect evidence, not a coverage estimate.

2. **The PFF denominators do not answer the decision question.** `2,954/2,954` proves PFF Passing
   Depth reconciles internally to PFF Passing Summary for matched rows. It does not prove PFF↔CFBD
   semantic parity, GSIS resolution, final-college-season coverage, or coverage on the 126-row
   Engine-A QB cohort. Likewise, the `840` cross-realm IDs span all positions and the whole archive;
   the framing needs QB counts and overlap with the governed rookie/outcome cohort before using the
   number as support.

3. **The identity-basis description collapses two different edges.** The 840 IDs provide a direct
   **PFF-native NCAA↔NFL** edge. Attaching GSIS through PlayerProfiler requires a separate
   PFF-NFL↔PlayerProfiler identity join, apparently by name/team/season; PlayerProfiler's GSIS may be
   vendor-supplied, but the cross-vendor join is not. “Pre-2023 college seasons resolve only by
   inference” locates inference on the wrong edge. Persist edge-level basis and compose it honestly:
   `pff_vendor_id` for NCAA↔NFL, a named inferred/reviewed basis for PFF↔GSIS, and no resolved output
   when either edge is ambiguous.

4. **The injectivity gate is too narrow.** “Zero within-file collisions” does not protect against a
   PFF ID mapping to conflicting people across files/seasons. The current audit observed 17
   archive-wide normalized-name changes and interpreted them as aliases; a future contract still
   needs archive-wide temporal conflict detection, plus wrong-team/season and duplicate-key refusal.

5. **The era boundary blocks an unqualified replacement frame.** The PFF passing archive begins in
   2017, while the CFBD skill's governed identity/coverage population is 2015-present and the Engine-A
   training cohort may contain earlier college seasons. Measure the exact training/outcome window.
   Any source choice must say what happens before 2017; silent cohort truncation is prohibited.

6. **Excluding columns containing “grade” is not a sufficient feature contract.** Passing Summary
   and Depth contain provider-charted judgments beyond grades—e.g. accuracy/aimed-pass, big-time
   throw, turnover-worthy-play, pressure attribution, thrown-away/hit-as-threw, and related rates.
   The framing must define an explicit allowlist of objective box-stat inputs needed to reproduce the
   comparable CFBD features, with every other field excluded by default. Any PFF-specific charted
   candidate is a separately named hypothesis, not smuggled through a grade denylist.

7. **“Supplement” must not mean silent coalescing.** The honest initial shape is two
   source-qualified columns/tables plus a reconciliation report and independent missingness masks.
   Do not build a precedence rule that fills CFBD gaps with PFF values: that changes the modeled
   cohort and makes source choice endogenous. Replacement, fallback, or blended features require the
   later validated decision; curation preserves both sources separately.

8. **A small cohort can discover mismatch but cannot establish parity.** Since the local archive is
   only a few thousand rows, use a deterministic stratified fixture for RED/schema discovery, then
   require full reconciliation over every eligible GSIS-resolved overlap row for acceptance. There
   is no defensible magic minimum `N` for semantic equality. Predictive power floors belong to the
   later pre-registered validation and David's ruling, not this Layer-2 contract.

9. **The repeated-export drift example is from NCAA Receiving Depth, not Passing.** It supports a
   cross-family source-vintage risk, not a claim that Passing currently drifts. Label it that way.
   Raw immutable preservation and a deterministic vintage-selection rule still belong in the
   passing contract.

10. **Season scope must be registered per source before comparison.** The local NCAA passing files
    are `REGPO`; the cited rejected `REGPO` incident concerned an NFL Receiving file compared with an
    NFL `REG` baseline. That incident proves scope labels matter, not that NCAA `REGPO` is wrong.
    Establish what CFBD's compared totals include, preserve `season_scope`, and refuse comparisons
    across unmatched scopes.

## Answers to the three requested questions

1. **Replacement is premature.** Build two source-qualified curated lanes and a reconciliation
   assessment. That is not yet a production “supplement”: no value coalescing or fallback order.
2. **The all-position 840-ID bridge is a separate identity-substrate thread.** This PFF-QB thread
   needs a bounded, reviewable QB→GSIS mapping dependency for its cohort; it must not silently absorb
   a repo-wide cross-position bridge.
3. **No single minimum cohort size.** Use a deterministic stratified fixture to develop the
   contract, then all eligible overlapping resolved rows to accept semantic reconciliation. A later
   predictive study owns sample-size/power gates through pre-registration and David's ruling.

## Required v2 boundary

The v2 framing should end at: immutable raw PFF export → explicit-source/scope normalization →
bounded QB identity mapping with basis → parallel PFF/CFBD comparison artifact with full-overlap
coverage and denominator accounting. No coalesced training field, feature promotion, model run,
paid refresh, or active CSV change is authorized by that path.
