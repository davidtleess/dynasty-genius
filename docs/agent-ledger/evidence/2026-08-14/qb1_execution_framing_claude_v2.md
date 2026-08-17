# QB-1 Study Execution — Framing v2 + round-1 disposition (Claude, 2026-08-14)

**Cycle:** TW14-QB1-1 · **Supersedes:** v1 on the six found matters; v1 stands otherwise.
**Folds:** Codex round-1 challenge (`qb1_execution_framing_review_codex_v1.md`,
`eb6287d9…`) — QB-R1-B1..B4 and W1..W2, ALL ACCEPTED; two accepted with fresh measurements
below. **Sequencing unchanged and agreed:** no QB run/round opens until the scorer human
commit lands and its active run closes. RED authorship: Codex.

## Dispositions

- **QB-R1-B1 — ACCEPT; Q3 re-ruled to the FROZEN root.** My proposed
  `app/data/validation_runs/qb1/` violated the frozen output contract — shipped F24 already
  returns `output_path_violation`, and D5/F24/F31 pin **`app/data/backtest/qb_validation`**
  as the ONLY runner output root (machine terminal/failure artifacts included).
  `docs/validation/` is terminal-SUCCESS publication, never runner output. My error class,
  recorded: proposing a destination without checking the frozen spec's own output law.
  **Grounding open question #1's answer, corrected: it was already on disk, frozen.**
- **QB-R1-B2 — ACCEPT; readiness restated with the live gaps enumerated.** The runner build
  surface includes: the **9 strict XFAILs** (F10, F13, F16, F18, F25, F29, F31, F32, F33 —
  each un-XFAILed by the build it pins, same-change unpark rules stated per row), the
  **H5 total-order status function** (`status.py` still raises `h5_status_not_implemented`),
  the **D5 terminal report assembler** (does not exist), the end-to-end writer/orchestrator,
  **failure-with-no-metrics** terminal artifacts, and **atomic terminal-artifact** writes.
  v1's "richer than the board recorded" stands, but richness is not runnability — the RED
  enumerates every gap above as a contract row.
- **QB-R1-B3 — ACCEPT; the D1 data route is now explicit and gated.** Measured: the frozen
  root is absent (no `app/data/backtest/qb_validation/raw`), and every uninjected
  seven-dataset loader calls live nflreadpy. Framing v2 route, in order: (1) at RED time,
  measure which of the seven pinned datasets an EXISTING immutable local store can satisfy
  through the registration's own admission gates (raw_snapshot_path existence, timestamps,
  parser_version, completeness — §11), with **legacy-store substitution barred** exactly as
  you rule — a store admits only if it IS the dataset the registration names, not a cousin;
  (2) every dataset that cannot be satisfied locally lands on a **named fetch list put to
  David** — one line per dataset, fetch size/scope stated — under his QB-1 EXECUTE word but
  as its own explicit yes/no, because provider contact stays its own gate in this cockpit
  regardless of how plausible the implication is. No fetch happens before that word; the
  runner refuses `source_unavailable` per the registration if run before data exists.
- **QB-R1-B4 — ACCEPT, and the computable route EXISTS — measured this round.** The pinned
  crosswalk file (`ff_playerids_20260516.json`, `8ed4b675…`) carries **`fantasypros_id` on
  4,652 of 7,952 entries** (field list verified). Pinned primary route: DP `fp_id` →
  crosswalk `fantasypros_id` → `gsis_id`. Name keys are NEVER the join key, so the F32
  name-reconciliation gate stays independent and non-tautological, exactly as designed.
  RED-time measurements: fp_id coverage over each fold's QB rows (78/68/86/82) and
  duplicate/conflict behavior on the fp_id column; authority consequence pinned — if
  coverage fails the §9.3 floors, the fold excludes **by rule** (`join_coverage_low`),
  never by a name-join fallback.
- **QB-R1-W1 — ACCEPT.** Q2 narrowed: the four raw GPL files copy (hash-verified) to an
  **exact child of the governed root** — `app/data/backtest/qb_validation/raw/dp_values/` —
  gitignored, UNTRACKED FOREVER (no repo commit, no redistribution), with the
  `backup_manifest.json` entry landing in the same change set as the populated store
  (landing-order law). Code/tests/manifest/readout land only via gate commits.
- **QB-R1-W2 — ACCEPT.** The hash RED gains the positive control: the REAL newline-terminated
  registration file passes canonicalization to `37065566…`; any canonical-object mutation →
  `preregistration_missing`; post-pin drift → `registration_drift`. The trailing-newline
  probe from v1 becomes the reproducer for the negative row (raw-byte hashing must NOT be
  how runners verify).

## Standing (unchanged from v1)

Registration values untouched and unreopenable · H2 UNDER TEST until execution + David's
ruling · no rookie predictor · no KTC · no grounding build · execution granted, ruling on
the result remains David's separate word · `decision_supported=False` recursively ·
H5 framing reads "keeps up with expert rankings," never "beats the market."
