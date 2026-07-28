From Codex (RED author / independent reviewer) - TW28 Units A/B/D RED v1; GREEN requested

DAVID'S WORD: "split it".

THREAD BOUNDARY:
  Units A, B and D only.
  Unit C remains in its own challenge rounds and does not gate this work.
  The threads must not share a commit.

RED TEST:
  tests/contract/test_identity_crosswalk_hardening_red.py
  SHA-256 1b75f20b87675ac7ad8f50d6227557ce4e30b13f6e940285383dd400fa50ba6c

CONTRACT + FALSIFICATION MATRIX:
  docs/agent-ledger/evidence/2026-07-28/identity_abd_red_contract_v1.md
  SHA-256 67387d861bfb3b05fdbbcb9c969a79a7bbc3280535ea20e4d7b222d023618a60

ATTRIBUTABLE RED:
  focused: 18 failed, 1 passed
  sibling regression slice: 22 passed
  Ruff on RED: clean

THE ONE PASS is a preservation control: JSON null identifiers remain absent and are
not stringified to "None".

THE FAILURES pin:
  A. missing/malformed/conflicting crosswalk input aborts with named reasons;
  B. deterministic coverage.engine_b_identity_join accounting, including orphans,
     parsed-object-identical duplicate counts, prediction-side duplicate handling,
     zero-orphan present-empty output, empty-prediction and zero-join refusal;
  D. the production loader's exact path is tracked, present, hash-pinned to
     8ed4b67578d06a24527356f9f355ed97f12be827e34885270c0b1d28c079f593,
     while sibling _runs files remain ignored.

IMPORTANT POLICY BOUNDARY:
  Zero successful joins aborts because David's split rationale explicitly names the
  empty-board risk. The RED does NOT encode 502/503 publication or any partial-
  coverage threshold. Do not add one and do not claim there is no threshold.

EXPECTED GREEN SCOPE:
  scripts/build_universe_pvo_batch.py
  .gitignore only if needed for exact-path tracking while retaining sibling ignore
  the exact frozen crosswalk bytes
  this RED if implementation reveals a genuine contract mistake, but do not edit it
    merely to make GREEN easier; route a challenge first
  your ledger/state evidence

Do not touch players.py, PlayerDetailCard, PlayerInspector, or any Unit C artifact.
Do not run a production refresh. Focused GREEN first; Codex owns independent
falsification and CLEAR, then the full-suite tollgate, then the A/B/D-only commit
under David's already-issued sequencing word.

PLEASE REPLY with: (a) your independent technical read plus GREEN implementation and
focused results, OR (b) a specific RED contract challenge with file:line evidence
before changing the test.
