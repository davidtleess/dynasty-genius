# Adversarial challenge — inert-feature / bakeoff execution-status framing v1

**Artifact reviewed:**
`docs/agent-ledger/evidence/2026-08-01/framing_inert_feature_defect_signal_claude_v1.md`  
**Reviewer:** Codex  
**Disposition:** **CHALLENGE — seven defects; no RED opens**

## Findings

1. **The concrete-situation premise is contradicted by the contemporaneous record.** Framing
   lines 27–29 say the record read as “we tested QB college passing and it did not help.” The
   committed Phase-20 JSON already carries all four `dropped_features`, their coverage, both models
   `skipped: true`, and `reason: enriched_features_equal_baseline`. More decisively,
   `docs/agent-ledger/2026-05-24.md:994-1004` says QB was **“BLOCKED/SKIP”**, says all four features
   were dropped, and names coverage expansion as the next option. The group-level phrase “null
   result” was imprecise, but the QB arm was not recorded as tested-and-useless. This session's miss
   was the later `39.5`-as-importance misread. Reframe the defect as **multi-arm headline/status
   aggregation and reader ergonomics**, not absent execution evidence.

2. **“The ingest cause is fixed” overstates current data state.** Commit `4d8127d` fixes the code
   path; no post-repair paid refresh, active-CSV rebuild, or promotion ran. The active candidate data
   remain the old bad input, and usable post-repair CFBD coverage is unknown. State those separately.
   The layer-3 contract should also be source-agnostic: a blocked arm is blocked regardless of why
   its candidate columns disappeared.

3. **The false-positive boundary is not mechanically coherent yet.** In this runner,
   `enriched_features_equal_baseline` means the *surviving feature-name set* equals the baseline set
   (`scripts/run_phase20_bakeoff.py:123-145`). A declared enrichment whose candidate-name delta is
   empty is not “legitimately enriched”; it is a no-op/misconfigured experiment and should have a
   distinct refusal such as `no_candidate_features_declared`. If distinct candidate columns survive
   but happen to carry values identical to baseline columns, the feature sets are not equal and this
   branch does not fire. Pin the taxonomy mechanically:
   - declared candidate delta non-empty, surviving candidate delta empty → blocked/unexecuted;
   - declared candidate delta empty → invalid/no-op configuration;
   - surviving distinct columns with duplicate values → separate duplicate/collinearity diagnostic.

4. **Historical-artifact handling must preserve immutability.** The 2026-05-24 artifact is already
   self-describing at the raw-field level. Do not rewrite it to add a status. A reader/linter may
   derive a new assessment from `spec_features`, `baseline_features`, `available_features`,
   `dropped_features`, and `gate_results`, but that assessment must cite/hash the immutable input.
   Future runners can add an explicit per-arm execution status and overall run status.

5. **Whole-run semantics are missing.** This was a three-arm artifact: two arms executed and failed;
   one was blocked. “No passing candidates” is true but insufficient, and a single “null result” is
   ambiguous. The framing must define whether a required blocked arm yields `PARTIAL/BLOCKED`,
   whether the artifact is still written, and whether the command exits non-zero after preserving
   the completed arms. Do not solve a reporting defect by aborting before durable evidence is
   written.

6. **Seed 6 conflicts with the stated boundary.** No Phase-20 power floor is registered in the
   inspected runner. Adding one changes a gate threshold, while lines 67–69 declare threshold
   changes out of scope. Remove that seed or explicitly open a separate David-owned threshold
   decision; `n_eligible_rows` can be reported without inventing a pass/fail floor.

7. **The No-Verdict treatment is incomplete.** If a new reader or generated assessment is a
   running-software output/written artifact, it must itself carry `decision_supported=False`
   recursively, not merely say the existing value is “unaffected.” Status copy must distinguish
   `NOT_RUN`, `BLOCKED`, `EXECUTED_FAIL`, and `EXECUTED_PASS` without implying a feature would have
   worked.

## Position on the open technical question

Use two surfaces without mutating history:

- **Future runner/artifact schema:** explicit per-arm execution status plus an overall status that
  cannot flatten blocked and executed-negative arms into one “null” label.
- **Historical reader/linter:** derive the same taxonomy from existing fields and emit a new,
  source-hashed assessment. The old artifact already contains enough evidence for the Phase-20 QB
  classification; it does not need a rerun or rewrite.

This is not a gate-threshold change, bakeoff rerun, feature promotion, or model change.
