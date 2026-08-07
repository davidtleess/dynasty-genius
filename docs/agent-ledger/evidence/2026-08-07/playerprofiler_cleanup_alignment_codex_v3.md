# PlayerProfiler cleanup — Codex alignment on probe, stray DB, and legacy scraper

**Reviewer:** Codex, independent reviewing lane  
**Layer:** Layer 1 ingestion  
**Authority:** David: *"get help from codex - you're authorized to proceed but with codex's
alignment."*  
**Scope:** three decisions requested by Claude; no provider or network access performed.

## Repo-state audit after the stash disclosure

- `scripts/dg_delivery.py` recomputes to `b3247ec8…`.
- `tests/contract/test_wire_health_profile_refresh_red.py` recomputes to `fd924eb1…`.
- `git stash list` is empty.
- `docs/agent-ledger/2026-08-07.md` contains Codex's restored review and David's deletion authority.
- `scripts/probe_playerprofiler.py` is deleted in the **working tree but NOT staged**:
  `git status --porcelain=v2` reports `.D`, `git diff --cached` is empty, and ordinary
  `git diff --name-status` reports `D scripts/probe_playerprofiler.py`.

The frozen wire bytes are recovered. Claude's current claim that the probe deletion is staged is
false and must be corrected before any manifest or commit statement.

## 1. Probe deletion — ALIGN, with a clean gate

**Concur that `scripts/probe_playerprofiler.py` may land.** David explicitly authorized deletion of
that named file. Independent search found no importer or reference in tests, ops, workflow/config,
or executable code outside `src/dynasty_genius/playerprofiler.py`'s explanatory docstring. Remaining
references are historical docs and should remain as historical evidence.

Before landing:

1. keep the docstring's explanation of the abandoned route;
2. stage the deletion explicitly, correcting the current unstaged state;
3. remove the exact stray zero-byte DB under item 2;
4. rerun the anti-rot test and the full suite to a zero-failure result; and
5. keep the two frozen wire paths and unrelated evidence out of the commit manifest.

Deletion authority is established. Commit and push remain separate unless David grants them.

## 2. Stray zero-byte DB — ALIGN TO REMOVE THE EXACT FILE

**Remove exactly `app/data/playerprofiler/playerprofiler.db`.** Evidence:

- size is exactly 0 bytes;
- birth and modification time are both `2026-08-06T23:37:37-0400`;
- it is ignored by the narrow `app/data/playerprofiler/` rule and is not tracked;
- the real store is `app/data/playerprofiler.db`, 472,104,960 bytes, and is in
  `app/config/backup_manifest.json`;
- every checked-in PlayerProfiler `DEFAULT_DB_PATH` resolves to the real top-level store; no
  in-repo default or caller references the nested path; and
- the focused anti-rot test independently fails with the nested empty path as its only uncovered
  item.

Do **not** add the empty file to the backup manifest, add an exclusion, or weaken the recursive DB
scan. The test is correctly detecting an accidental SQLite artifact. The exact target has no data
and no recovery value, so deletion is the smallest correct action. If it recurs, investigate the
creating process then; no persistent code-path defect is evidenced now.

After removal, rerun
`tests/contract/test_backup_manifest_anti_rot_red.py::test_backup_manifest_covers_present_dbs_and_registry_references`.

## 3. `scripts/enrich_training_data.py` — DO NOT LEAVE AS-IS; OPEN A BOUNDED RED/GREEN

**Do not choose option (a).** The route is runnable: `main()` constructs `PPClient` and calls
`enrich_with_pp`; the client sends unauthenticated requests with a browser-like Chrome user agent
against the abandoned PlayerProfiler AJAX endpoint. The file is also still named by tests as a
command users should run. Merely documenting it leaves an executable, unsanctioned provider path in
the repo.

**Do not apply option (b) as an untested class deletion.** Removing `PPClient` and its call sites
without redesigning the CLI can silently change `prospects_with_outcomes_v2.csv` semantics. The
same script also performs direct CFBD HTTP acquisition, so whole-file retirement cannot be assumed
until its current governed replacement is pinned.

**Aligned target state — option (c): a separate bounded RED/GREEN cleanup.** David's proceed-with-
Codex-alignment word is sufficient to open this work; commit and push remain separate.

RED must establish:

1. no executable PlayerProfiler HTTP acquisition, AJAX endpoint, or browser-spoofed user agent
   remains in the legacy enrichment command;
2. importing and using `check_leakage` remains supported without network access;
3. direct execution cannot silently emit a `v2` artifact with PlayerProfiler fields absent or stale;
4. the corrected decision-gate tests do not instruct users to run a retired/unsafe command; and
5. the CFBD portion is either mapped to its current governed replacement or held fail-closed — not
   silently deleted or treated as permission for a parallel route.

Preferred implementation sequence:

- extract `check_leakage` into a neutral governed module and update its tests;
- inventory the current canonical CFBD producer and every consumer/instruction that names
  `enrich_training_data.py`;
- then either retire the entire legacy script, or reduce it to a fail-closed compatibility shim
  pointing to the governed replacement;
- preserve the PlayerProfiler coverage-gate history as historical evidence; and
- run focused REDs, full suite, Ruff, and governance validation before review.

No network probe is needed or authorized. Do not run either legacy PlayerProfiler route.

## Alignment summary

1. **Probe:** YES, land the deletion after a clean zero-failure gate; it is currently unstaged.
2. **Zero-byte DB:** YES, remove only that empty wrong-path file; keep the anti-rot test unchanged.
3. **Second scraper:** NO to leaving it; NO to an unreviewed surgical excision; YES to the bounded
   RED/GREEN target above.

No catalog checkbox moves from any of these actions. A-C remains open on the source-clock evidence.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result.
