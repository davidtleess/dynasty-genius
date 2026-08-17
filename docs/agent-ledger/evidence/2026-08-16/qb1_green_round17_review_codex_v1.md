# QB-1 green-review Round 17 — independent Codex verdict

Date: 2026-08-16 13:43 ET  
Run: `f8f7551c-a145-46e2-b9b4-dec427f313ba`  
Round: green-review 17, revision 104  
Verdict: **CLEAR**

## Scope and pins

The open snapshot is
`225761eeeb7d334e16dab11a8ef2449c38e8743b868a9c9dc5aa8dfb18728688`.
The current two-file pins reproduce Claude's request:

- `study_matrix.py`:
  `6c607badab90342e9f5508d09278614236be1095fd44702949910a5dca54a89d`
- correction contracts:
  `200c6deec425c0d2c2c57ffe7f0e904bee3a9925648df9bad589d205307eba22`

Snapshot-to-current diff is exactly those two files: matrix +52/−1 and
contracts +170/−0, 223 changed lines total. Claude's request described matrix
as +61/−3; direct snapshot numstat governs. The discrepancy is non-semantic
and non-blocking. Out-of-scope labels and runner pins remain `e5cb3955…` and
`7de911cc…`. No dependency, configuration, secret, input, registration,
publication, commit, or push change is present.

## Code and contract review

The implementation matches the registration read exactly:

- private matrix predicate only;
- missing player id;
- valid season under both `_valid_label_season` and `_STUDY_SEASONS`;
- missing position;
- null `passing_cpoe` under the shipped stage-1b null law;
- `games` accepted only through `_lossless_int` and `>=256`;
- names do not participate;
- filtering occurs after F1, F14/F15, and exact season coverage, immediately
  before stage-1b identity/duplicate/CPOE validation;
- the defensive frame and admitted pool are not mutated;
- every near miss remains in the records and reaches existing fail-closed
  validation.

No target, cohort, feature, fold, estimator, inference, threshold, registered
value, or publication-gate semantic changes. This is implementation of the
registered player-season/CPOE join boundary, not an amendment.

## Independent verification

1. Exact five-file bundle rerun:
   `704 passed` in 49.00s.
2. Round-17 contracts alone:
   `5 passed, 144 deselected` in 7.54s. These cover classifier privacy and
   placement, positive variants, 16 one-field near misses, analytic equality,
   and public-composition refusal for content-bearing/sub-league near misses.
3. Real-store stage-1b replay rerun independently from the final pins:
   exactly 11 exclusions at the census indices, first 1845; zero residual
   unusable identities; all 21,366 kept rows pass identity, duplicate, and CPOE
   law with 21,366 distinct keys; admitted frame digest unchanged; exit 0.
4. Claude's full suite receipt is internally reconciled:
   6,151 passed / 15 failed / 12 skipped in 8:37. All 15 failures are by name
   from the standing untracked
   `tests/contract/test_governed_cadence_inputs_red.py`; zero tracked failure.
5. Scoped Ruff, strict `py_compile`, `git diff --check`, current hashes, and
   snapshot diff scope all pass.

The evidence proves the measured season-summary identity wall is closed. It
does not claim no non-identity wall exists later in composition.

## Verdict

**CLEAR.** No BLOCKER or WARN finding. The one fresh rerun authorized by David
may fire only after this verdict and close are durable. The registered readout,
or a named fail-closed terminal artifact, goes to David untouched for his
ruling. H2 QB rushing remains **UNDER TEST with no result** until a registered
run completes and David rules.
