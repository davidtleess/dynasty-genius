# Framing dispositions accepted — Codex v1

**Date:** 2026-08-01  
**Reviewer:** Codex  
**Scope:** Written dispositions only; authorization to author the two v2 framings, not either RED

## Verdict

**DISPOSITION ACCEPTED for both artifacts.** The inert-feature disposition answers all seven
challenge items, and the PFF-NCAA-passing disposition answers all ten. No item is dodged,
rejected, or silently moved into the proposed implementation.

## Inert-feature defect-signal disposition — 7/7 answered

1. It corrects the false historical premise: the May 24 durable record already identified the QB
   arm as dropped and `BLOCKED/SKIP`. The remaining defect is the group-level aggregation and
   reader-ergonomics failure that flattened blocked and executed arms into a “null result.”
2. It separates code state from data state: `968321a` repairs the ingestion path, but no repaired
   refresh has established current source coverage.
3. It adopts the mechanical three-way taxonomy: blocked/unexecuted, no candidate features
   declared, and a separate duplicate/collinearity diagnostic.
4. It preserves the historical artifact and proposes a source-hashed derived assessment rather
   than rewriting history.
5. It requires whole-run `PARTIAL`/`BLOCKED` semantics while still writing durable evidence.
6. It removes the unsupported power-floor seed and preserves the existing coverage-threshold
   distinction.
7. It carries `decision_supported=False` recursively with explicit
   `NOT_RUN`/`BLOCKED`/`EXECUTED_FAIL`/`EXECUTED_PASS` states.

The open exit-code choice is a legitimate v2 design question, not an unanswered challenge item.
The accepted technical direction remains: future runner schema plus a historical reader/linter;
no mutation of the 2026-05-24 artifact.

## PFF NCAA passing disposition — 10/10 answered

1. It demotes the old CFBD population counts to defect evidence and requires repaired,
   QB-cohort-specific coverage before using them comparatively.
2. It limits the 2,954 count to PFF Depth↔Summary consistency and the 840 count to the separate
   all-position identity substrate.
3. It separates the NCAA↔NFL vendor-ID edge from the NFL-vendor↔GSIS edge and refuses ambiguous
   output at either edge.
4. It widens injectivity checks to archive-wide temporal conflicts.
5. It makes the 2017/pre-2017 boundary measurable and prohibits silent cohort truncation.
6. It replaces a grade denylist with an objective box-stat allowlist and treats charted judgments
   as separate hypotheses.
7. It uses parallel, source-qualified lanes with no fallback or coalescing.
8. It uses a deterministic discovery fixture and all eligible resolved overlap rows for semantic
   acceptance, leaving predictive power to later preregistration.
9. It correctly relabels the drift example as a cross-family Receiving observation.
10. It requires exact per-source season scope and refusal on unmatched scopes.

The answers to the three explicit framing questions are incorporated: “replacement” is premature;
the honest candidate shape is two source-qualified lanes plus reconciliation; the all-position
840-ID bridge is a separate identity-substrate thread, with only a bounded QB mapping dependency
inside this thread; and semantic acceptance has no arbitrary minimum-N shortcut.

## Authorization boundary

Claude may author both v2 framing artifacts against these dispositions. **No RED is authorized by
this acceptance.** Each v2 remains subject to independent framing review before a RED opens.

## Related closeout

The separate CFBD post-commit loop is **DIVERGENCE-VERIFY CLEAR** on
`968321a5b2368372fea091022fe94a894f4eaa3f`. GitHub Actions run `30720445012` independently reads
`completed/success` for that exact SHA. This terminal check supplements, rather than rewrites, the
time-accurate earlier audit that recorded the run as in progress.
