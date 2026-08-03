# Final ingestion/tooling package — Codex CLEAR

**Date:** 2026-08-03  
**Layer served:** Layer 1 ingestion  
**Verdict:** **CLEAR for the David-authorized commit and push**

I audited the final working-tree implementation, tests, durable evidence, mutation databases, and
the corrected ledger rather than relying on the handoff summary.

## Checks

1. **Injury post-live corrections:** exact era resolution, normalized grain/key construction,
   schema-aware idempotence, v4 artifact surfaces, explicit additive migration, declared empty
   exports, early integer refusal, and two-era store/export round trips remain contract-locked.
2. **Schema-era tooling:** six archived shapes replay capture → normalize → store → export; all
   1,080 pinned `(column, dtype-kind)` variants have witnesses; all five stream loaders come from
   the production registry; the preflight is read-only and its CLI reaches the tested verdict.
3. **Provenance:** baseline verifies 266 pinned snapshots; removed pinned evidence, tampered
   content, per-season dtype drift, and column drift all refuse; added same-shape snapshots pass
   with a truthful note. Verified counts include only files actually read and hash-matched.
4. **Mutation pilot:** real detached worktree, published runner, 116-pass baseline. Round 1 was
   10 killed / 2 survived; after targeted locks, the identical complete 12-mutant census was
   **12 killed / 0 survived / 0 incompetent / 0 timeout**, with every diff non-empty. The earlier
   false-survivor run is correctly attributed to orphaned empty `work_items`, not the tool.
5. **Survivor scope:** exhaustive 16-truncation probe proves zero acceptances under subset matching
   (15 `heterogeneous_batch`, 1 `ambiguous_era`). The evidence now calls this an exact-resolver /
   error-taxonomy gap, not silent data loss. The final stale assertion message was swept and now
   says a subset must not be classified as a known era.
6. **Dependencies:** `hypothesis==6.161.0` is in the CI-installed requirements file;
   `cosmic-ray==8.4.6` is the measured Python-3.14-compatible dev tool, with failed mutmut attempts
   recorded rather than hidden.
7. **Independent verification:** Codex final combined slice **145 passed**; Claude package slice
   **135 passed**; final assertion file **21 passed**; Ruff clean; `git diff --check` clean.
   Unfiltered suite **4,312 passed / 12 skipped / 9 xfailed / 0 failed** before the final wording-
   only assertion edit; post-edit `verify_sprint_closeout.py` returned **ENFORCE PASS** for the
   Python suite, Ruff, and changed standalone scripts.
8. **Prior commits:** Claude independently returned DIVERGENCE-VERIFY CLEAR on `5eaab93` (provider
   contracts) and `a7794e9` (canonical inventory reconciliation).

## Commit boundary

Commit the cleared ingestion/tooling/dependency/tests plus the 2026-08-02/03 ledger and evidence
records. Explicitly exclude the three separately withheld NGS paths:

- `scripts/run_nfl_nextgen_capture.py`
- `src/dynasty_genius/capture/nfl_nextgen_capture.py`
- `tests/contract/test_nfl_nextgen_capture.py`

`docs/data-inventory.md` is already committed in `a7794e9`; do not restage unrelated drift.

After commit: audit the actual commit against this boundary, push `main`, require local HEAD,
`origin/main`, and `git ls-remote` to agree with zero ahead/behind, and wait for terminal green CI.
