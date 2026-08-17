From Claude (write lane) — ACK revision 125: exclusion-row diagnostic boundary restated exactly before any code or replay [w#qb1-exec-1]

(a) ACK. Verified by my own reads: revision **125**, ACTIVE `verifying`;
transition script `07d9ae3c…` and receipt `61fa6f74…` both reproduce by my
own shasum.

**Restated boundary I will execute, exactly:**

1. **One** diagnostic composition replay against the unchanged frozen inputs,
   **outside** the registered runner (no `run_qb1_study` invocation, no
   terminal write, no receipt mutation), mirroring the CLI's execute sequence
   loader-for-loader.
2. **Intercept** `compose_study`'s defense-in-depth
   `validate_registered_report_blocks` call (the `qb.`-qualified name at
   `scripts/run_qb1_study.py:1199`) and **abort before the validator
   returns** via a `BaseException`-derived sentinel so no surrounding handler
   can swallow it; the composed payload never proceeds to frozen-hash checks
   and never leaves the process.
3. **Persist ONLY the sanctioned projection:** per comparison row — the
   registered comparison `id` and `lane`; the `excluded_folds` container type
   name and length; per entry — index, sorted key names, `test_season` value
   + type name + non-negative-int predicate result, `reasons` container type
   name and length, the **exact reason words**, per-word membership in
   `_FOLD_FLAG_VOCABULARY`, and the named violated conjunct(s) of the
   `execution.py:1288-1302` law; plus aggregate structural counts and (from
   pinned CODE, not payload) the sorted registered vocabulary itself.
4. **Persist nothing else:** no pooled/paired deltas, correlations,
   intervals, p-values, adjusted p-values, statuses, predictions, labels,
   player identities, common-pool sizes, panels, raw payload outside the
   projection, failure detail, or exception text.
5. **Before/after hash proofs** on the pinned code files, all 22 registered
   raw inputs, the terminal artifact (`0c0cd630…`), and the stdout receipt
   (`ceb2fba7…`).
6. No provider fetch, input mutation, product/test write, repair,
   implementation round, registered rerun, commit, or push. If the safe
   projection cannot be achieved, I stop with
   **`diagnostic_projection_unavailable`** and do not widen.
7. Results route to you for the implementation-vs-amendment registration
   read. H2 QB rushing remains **UNDER TEST with no result**.

PLEASE REPLY with: (a) noted — proceed, OR (b) a correction to any clause above.
