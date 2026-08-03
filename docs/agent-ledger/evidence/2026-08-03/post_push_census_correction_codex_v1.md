# Post-push census correction — schema-era replay package

**Recorded:** 2026-08-03 09:32 EDT

**Layer:** 1 — source ingestion and persistence contracts

**Affected commits:** `40fc4d87318681e0471660f88ac04bfa701857e9`,
`3084ae9e6dd74b933adf9b00f9057b95fac42ad4`

**CI:** [run 30817969583](https://github.com/davidtleess/dynasty-genius/actions/runs/30817969583)

## Correction

The exact local census `4312 passed, 12 skipped, 9 xfailed, 0 failed` was a real unfiltered run,
but it occurred **before** the two tests written to kill the mutation pilot's surviving mutants.
The later post-final-edit `scripts/verify_sprint_closeout.py` run returned **ENFORCE PASS** across
the Python suite, Ruff, and standalone scripts, but its captured output did not retain an exact
pytest count.

The public commit message for `40fc4d8` and the contemporaneous handoff/ledger therefore make the
earlier exact census read as though it described the final committed tree. That implication is
wrong. Because the commits were already public when this was identified, history is not rewritten;
this forward record supersedes the timing implication while preserving the original wire history.

## Exact final-tree evidence

GitHub Actions checked out `3084ae9e6dd74b933adf9b00f9057b95fac42ad4`, which includes both
final mutation-survivor tests. Run `30817969583` completed successfully:

- Python checks: **success**
- Frontend checks: **success**
- Exact CI pytest census: **4285 passed, 36 skipped, 9 xfailed, 361 warnings in 125.46s**

The CI count differs from the earlier local count because the CI collection/environment skipped
36 tests while the local environment skipped 12. These are environment-specific censuses, not a
test regression. The load-bearing conclusion is that the exact committed tree passed in CI with
zero failures.

## Records preserved, not silently edited

- `40fc4d8` commit message remains immutable public history; its `Gate: 4312...` line is superseded
  by this correction for final-tree census purposes.
- `msg_claude_final_package_codex_v1.txt` remains the message actually sent.
- `final_ingestion_tooling_clear_codex_v1.md` also described `4312` as preceding only the final
  wording edit. That timing was too narrow because the two survivor tests were later additions;
  the CLEAR's code-surface verdict stands, but this artifact supersedes its census timing.
- `msg_claude_postcommit_census_divergence_codex.txt` preserves the discovery and requested
  correction, including the now-impossible pre-push amendment route.

No production code, test, data, model, consumer, or promoted artifact changed as part of this
correction.
