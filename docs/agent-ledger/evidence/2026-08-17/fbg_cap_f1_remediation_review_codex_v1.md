# Footballguys FBG-CAP-F1 remediation review — Codex v1

Date: 2026-08-17 ET
Reviewer: Codex (independent lane)
Artifact reviewed: `tests/contract/test_footballguys_phase_a_red.py`
Worktree SHA-256: `36de40c39eaec52a772d975ba98c61f0a4276c851d8c27da486342610a833789`
Diff: 1 file, +13/-13

## Verdict

**CLEAR. FBG-CAP-F1 is resolved at the reviewed worktree pin.**

The two-edit delta makes the contract match the already-landed post-capture repository state while preserving the S23 pre-capture refusal scenario. No capture, store, manifest, production source, or horizon state changed during this remediation or review.

This is pre-commit clearance only. `d39ff341678a904a1eeac07f263610843f1346f5` remains the pushed head and its CI run `32073785133` is red. The test delta must be committed and pushed by David, followed by exact-head CI success and a post-commit divergence audit.

## Checks performed

1. **Scope and byte pin**
   - `git diff -- tests/contract/test_footballguys_phase_a_red.py` shows exactly the reported two edits and no executable production change.
   - The file hashes to the submitted `36de40c3...` pin.
   - `git diff --check` passes.

2. **Repository-truth expectation**
   - `MANIFEST_REQUIREMENTS["app/data/footballguys/objects"]` now expects `("directory", True)`.
   - This matches the committed `d39ff34` manifest, where the objects store is required after the first real retained capture.
   - The adjacent comment now states the post-capture truth and identifies receipt `77984aaf...` without changing any runtime behavior.

3. **Historical negative-fixture mirror**
   - `_write_manifest(..., post_capture_epoch=True)` defaults to the current required-store truth.
   - Only `test_s23_precapture_optional_objects_row_refuses_raw_publication` passes `post_capture_epoch=False`; the helper then forces the objects row to optional for that historical negative.
   - S23 still proves raw publication refuses when the objects store is optional. The edit changes fixture construction, not the refusal semantics.
   - Direct probe reproduced both shapes: post-capture `required=True` in the required list; pre-capture `required=False` in the optional list.

4. **Fresh verification**
   - Exact combined gate: **665 passed** — `test_footballguys_phase_a_red.py` plus `test_backup_manifest_anti_rot_red.py`.
   - Focused anti-rot gate: **5 passed**.
   - Scoped Ruff: **all checks passed**.

5. **CI diagnosis**
   - GitHub Actions run `32073785133` on exact head `d39ff34` is completed/failure.
   - Frontend checks passed. Python failed only `test_p0_option1_manifest_covers_every_durable_store[objects]`: committed manifest `True` versus stale contract `False`.
   - The reviewed first edit changes exactly that expected value; the second preserves the independent S23 pre-capture negative.

6. **Capture/store preservation**
   - Receipts DB remains `54522831...`; semantics DB remains `f555aef7...`.
   - Objects store remains exactly one archive, `d8af0985...`, byte hash unchanged.
   - `observations.db` remains absent; attempts remain zero; semantic assertions and adjudications remain zero.
   - No intake was invoked and no valid capture was deleted or re-fired.

## Falsification matrix

| Input/state | Probe | Result |
|---|---|---|
| Current post-capture manifest | P0 repository-manifest contract + direct helper probe | Required objects row accepted |
| Historical pre-capture optional row | S23 with `post_capture_epoch=False` | Raw publication refused; stores unchanged |
| Missing/other durable stores | Full 665-test parameterized contract set | Passed |
| Backup coverage drift | Focused anti-rot suite | 5/5 passed |
| Scope expansion | Complete one-file diff + store hashes | None found |

## Remaining gates

1. David commits the reviewed test delta and accompanying state record.
2. David pushes the new head.
3. Exact-head CI must pass.
4. Codex audits the committed diff for zero divergence from SHA-256 `36de40c3...`.
5. The separate Footballguys horizon adjudication remains David-gated; this review does not open it.
