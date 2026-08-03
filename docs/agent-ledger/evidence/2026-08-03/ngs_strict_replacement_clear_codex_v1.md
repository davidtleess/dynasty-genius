# NGS strict-replacement audit — independent CLEAR

**Reviewer:** Codex (independent technical reviewer)  
**Cleared artifact:** `ngs_strict_replacement_audit_claude_v3.md`  
**Artifact SHA-256:** `0f681bdf8cf2023133a99979bb64be62c5477e934bbbc1b5f3bace5ebe08fc11`  
**Layer:** Layer 1 (ingest)  
**Verdict:** **CLEAR**

This CLEAR is the current board's transition from the read-only strict-replacement audit to David's
already-authorized withdrawal of the three duplicate code/test paths. It is not a post-removal or
post-commit divergence audit; those remain required after the implementing lane acts.

## Enumerated clearance checks

1. **One adapter/store.** Loaded `SOURCE_REGISTRY` directly and found exactly one
   `nfl_nextgen_stats` key, naming the canonical `nflverse_usage.py` adapter and SQLite store. The
   other registry text hit is a prose note. Independent whole-repo text and AST scans found no
   unregistered executable adapter import beyond the withdrawn runner/test.

2. **Exact family/season/row replacement.** Independently compared the preserved duplicate curated
   table with the canonical last-good export. All 30 family-season cells reconcile; key sets are
   identical; there are zero duplicate or one-sided keys; and there are zero shared-payload value
   mismatches across passing/receiving/rushing (25/19/18 shared fields). Direct SQLite controls,
   normalized through the export's typed schema, agree exactly with both export and duplicate.

3. **Identity.** Both routes carry the same canonical GSIS identifier on all 26,723 NGS rows.
   Canonical additionally records 100% `canonical_resolved`, `row_key`, and `season_ingested` under
   the governed identity contract. V3 correctly withdraws v1's false “no identity information”
   claim and states the actual governance/persistence advantage.

4. **Last-good integrity.** `read_last_good_export(verify=True)` returned run
   `nflverse-usage-20260803T0311151108400000`, schema `nflverse_usage.v4`, 314,641 rows. All six
   ready-marker SHA-256 values were independently recomputed and match.

5. **Canonical readers.** The real last-good export loads 5,933 passing, 14,731 receiving, and
   6,059 rushing rows. The two live consumers remain wired in `run_feature_refresh.py` and
   `assemble_engine_b_dataset.py`; downstream code was read/executed only for this read-only wiring
   check.

6. **No caller after withdrawal.** The only production import of the duplicate module is
   `scripts/run_nfl_nextgen_capture.py`, itself withdrawn. AST, dynamic-import-argument, whole-repo,
   scheduler/config, and public-function name scans found no hidden caller.

7. **Provider-field preservation.** The canonical adapter writes the full provider records before
   normalization. All 171 canonical NGS raw snapshots are non-empty and contain the four fields
   omitted from SQLite/export. Latest-per-season snapshots cover all 30 cells and reconcile to the
   duplicate across all 29/23/22 provider fields, including identical provider-side nulls.
   Therefore withdrawal loses no provider column; the four fields are curated-projection
   omissions, not route-level losses.

8. **Deterministic gates.** Independently measured focused contracts **147 passed**, collection
   **4,335 with zero errors**, and Ruff clean. V3 records the unfiltered suite **4,314 passed,
   12 skipped, 9 xfailed, 0 failed** and `verify_sprint_closeout.py` **ENFORCE PASS**; the census
   reconciles exactly to collection.

9. **Scope/honesty boundary.** The audit proves replacement, not predictive value or model/feature
   promotion. NGS remains `context_signal`. The gitignored duplicate data tree remains preserved by
   its independent retention ruling. The stale canonical module docstring is recorded but not
   silently absorbed into Step 1b's `docs/data-inventory.md` scope.

## Transition authorized by this CLEAR

Claude may now execute the board-authorized removal of exactly:

- `scripts/run_nfl_nextgen_capture.py`
- `src/dynasty_genius/capture/nfl_nextgen_capture.py`
- `tests/contract/test_nfl_nextgen_capture.py`

and perform the separately named Step 1b truth repair in `docs/data-inventory.md`. The duplicate
data tree must not be deleted or mutated. After the new artifact state exists, rerun the relevant
falsification/gates and route the actual removal/repair diff for independent review; after commit,
route the exact commit for divergence verification.
