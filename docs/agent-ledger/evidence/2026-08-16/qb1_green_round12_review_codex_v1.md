# QB-1 GREEN round-12 independent review — Codex

Date: 2026-08-16 08:36 EDT
Run: `f8f7551c-a145-46e2-b9b4-dec427f313ba`
Round: `green-review` 12
Verdict: **CLEAR**

## Governing ruling and review boundary

David ruled, verbatim:

> i rule the publication gate's registered guarantee is coherence + registration conformance - provenance grounding is out of the gate's scope; source truth stays with the pinned inputs, the shipped composition, and the end-to-end contracts. open one bounded round per your sanctioned mechanism for claude to document the boundary in the gate, then re-review under this ruling - execution only on your clear

This review therefore treats the Round-11 source-substitution probe as an
executable boundary case, not a publication-gate defect. The gate must still
enforce internal coherence and frozen-registration conformance. No study
execution is part of this review.

Layer served: Layer 3, the validation/publication gate. The Layers 1–2
dependency check reproduced the frozen admission, registration, and scoped
opening pins and exercised the shipped composition and end-to-end contracts;
no source or curation change is in this round.

## Independent findings

No blocking finding remains.

1. Durable state is coherent: revision 71, ACTIVE `green-review`, Round 12
   open, exact authorized scope, and Round-11 finding
   `finding-green-review-11-1` resolved in Round 12 only after the boundary
   documentation landed.
2. All submitted pins reproduce exactly:
   - `execution.py` —
     `b0c641743dbaf332d47d3508a6ca69c94b4e9797fd28582ec39e7fb9974965da`
   - `run_qb1_study.py` —
     `7c8893cac0d91810b84cde3aa2f94425cb75ff9f1ac2ed6c4e8e62b48a12a297`
   - correction contracts —
     `88a39cb88a7c5e1eb3a07b7e1dee80634bf27b8238f1aac702218e1ab160d5af`
   - Claude review request —
     `91fa37d32a02c4893d9f8e3a696fdcfaa352a978af1fef8fdbbabcac0363b45f`
3. The complete diff against the script-owned Round-12 opening snapshot is
   exactly two authorized files: 31 added docstring lines in `execution.py`
   and 116 added contract lines. `scripts/run_qb1_study.py` is byte-identical
   to its opening snapshot. There is no semantic, schema, calculation, input,
   output, dependency, configuration, or secret change.
4. Both publication-boundary docstrings state the exact guarantee—internal
   coherence plus conformance to the frozen registration—and explicitly put
   provenance grounding outside the gate for every block. They name the
   pinned admitted inputs, shipped composition, and end-to-end contracts as
   the source-truth owners.
5. The three Round-12 contracts prevent silent boundary drift: documentation
   presence, unchanged gate/runner signatures, and the ruled disposition of
   both Round-11 source-substitution shapes.
6. Fresh independent verification:
   - correction contracts: **130 passed**;
   - five-file QB-1 bundle: **685 passed**;
   - prior Round-11 source-totality probe: **2 passed**, now the expected
     out-of-scope disposition under David's ruling;
   - Ruff: clean;
   - strict Python compilation: clean;
   - `git diff --check`: clean.
7. Claude's broader census reports **6,132 passed / 15 failed / 12 skipped**;
   all 15 failures are the standing untracked cadence RED file and there are
   zero tracked failures or collection errors. The independent targeted
   census above covers every Round-12 change and the relevant QB-1 suite.
8. The existing passing bundle includes frozen input/hash admission, shipped
   composition, terminal metadata propagation, and end-to-end publication
   contracts. The dirty worktree is pre-existing and preserved; Round 12 did
   not broaden into it.
9. The first attempt to record CLEAR was correctly refused by the loop safety
   hook because three Round-8 findings, substantively corrected in the
   David-authorized Round 9, had never received their structured `resolve`
   verbs. A fresh run of the original Round-8 adversarial probe confirmed all
   four impossible payloads now refuse (**4/4 expected assertion failures**).
   No code change was needed. The three stale records were resolved through
   the sanctioned verb in Round 12 (`revision 68 -> 71`); the durable run now
   has zero unresolved BLOCKER findings. This state reconciliation does not
   alter the Round-12 scoped snapshot or product behavior.

## Verdict

**CLEAR.** The bounded documentation round implements David's ruling exactly,
preserves the coherence/conformance gate, and introduces no semantic change.
This CLEAR satisfies David's held execution trigger; it is not a football
finding and is not permission to commit, push, or publish any result beyond
the registered study's own atomic execution path.

H2 QB rushing remains **UNDER TEST with no result** until the registered study
executes and David separately rules on its registered output.
