# PFF scope-selection correction — Codex CLEAR v3

**Catalog:** `docs/layer-1-data-inventory-catalog.md`

**SHA-256:** `a472ae5c455ffaa5c223f8fc039892763429407f8bcde181ac2b4829d64846bb`

**Verdict:** **CLEAR for the PFF P1–P8 correction cycle.** This is not a CLEAR of the full Layer 1
catalog, a push authorization, or an aggregation-design decision.

## Independently verified

- The catalog cleanly separates 134,392 publishable raw payload rows from the unadopted 106,867
  policy output.
- The withdrawn double-count/20.5% claim remains explicitly withdrawn everywhere it appears.
- The three-mechanism model is consistent: raw payload versioning, same-scope current-state
  selection, and optional cross-scope aggregation are separate problems.
- Exhaustive profiling confirms exactly three unique same-scope conflict keys:
  - NCAA `receiving_depth`, 2017, `REGPO`, player IDs 39935 and 48267;
  - NCAA `receiving_summary`, 2025, `REG`, player ID 198423.
- The publication rule now permits the 134,392 raw payload-row sum at its labelled raw grain and
  blocks only a deduplicated/current-state cross-payload total pending a design decision.
- After a fresh fetch, `origin/main=0e8a7fa`, `HEAD=a04347c`, and the branch is four commits ahead.
- `git show --check --format='' a04347c` and `git diff --check origin/main..HEAD` are clean.

## Historical whitespace disclosure

Commit `71806b8` remains individually whitespace-dirty, while `e06ebeb` repairs the current file.
The cumulative pending-push tree is clean. The independent lane accepts this follow-up-cleanup shape
under the current tree/diff gate and does not require a local-history rewrite; it does not represent
`71806b8` as published or individually clean.

