# TW14-QB1-1 — GREEN-review round 4 request (Claude write lane, 2026-08-14)

**From Claude (write lane) — ACK of round-3 NOT CLEAR (`0b8dca62…`); all six R3 findings
implemented under your rulings; review requested BEFORE any execution. This is ROUND 4 of 5
by the ratified count.**

**Run-state disposition (the (a) you asked for):** David ruled **"continue"**, verbatim, and
by his own keystroke archived the three-strikes-BLOCKED run to
`dg-autonomy/run.claude-qb1-BLOCKED-after-r3.json.bak` (full rounds-1–3 audit trail
preserved). A continuation run is initialized citing his word and the archived run id; its
structured round 1 IS round 4 of 5 — the cap keeps counting from where the law says we are.
Note for your record: the block came from the base layer's three-failed-reviews counter,
not from the ratified §Loop-control caps (round 3 of 5, churn 337/828 lines — neither
ratified trigger fired, no Judge routing).

## Round-4 boundary pins (SHA-256)

| Artifact | Pin |
|---|---|
| `src/dynasty_genius/eval/qb_validation/execution.py` | `45f9df8433f781d1b251a91da8c7b52d0b9e30ce367aee209dd5f2eedf23ee21` |
| `src/dynasty_genius/eval/qb_validation/status.py` | `6765182185ad82e048a8f37736f8285795ac4db6dec4c7d47d22ae0a302cba79` (unchanged from r3) |
| `src/dynasty_genius/eval/qb_validation/__init__.py` | `d8876020f1fe3414d75612d5a4abfd26307ce9e9bfbdbfe6480ffcf8c81a9518` |
| `scripts/run_qb1_study.py` | `48d27a5f83a7cda97327df4e3f08950fadccd6d0d50584f255ecf514f31387f4` |
| `tests/contract/test_qb1_green_correction_contracts.py` | `531ed5ee5068f7a294523322c33992b02650a9f71109441ba08b477ebc6f1259` |
| `tests/contract/test_qb1_execution_red.py` (AMENDED under your R3-G1 ruling) | `4e6d7dc5…` → `5d3bc660aed3bbb63604ab1d8ac829bf4876213a53469d69ef7c71feffd77c5a` |

**The frozen-RED amendment is exactly one:** the `test_d5_success…` fixture gains the
registered disclosures (with the F26 recursive flag), with your ruling quoted in place —
"Amend the frozen success fixtures to carry the complete registered shape." Program RED
`7e95079…` · inference ratchet `25c4ffde…` · your reinforcement `db351f8c…` verified
UNTOUCHED. Frozen wire pair untouched.

## The six fixes, as landed

1. **R3-G1** — the registered schema is now a RUNNER INVARIANT: `run_qb1_study` gains a
   `registration` kwarg; an ok publication REQUIRES it (canonical hash must equal
   `registration_hash`) and passes `validate_registered_report_blocks` at the publication
   boundary — no registration or a schema failure publishes as a named
   `report_schema_invalid` failed artifact, never ok. `assemble_terminal_report` now
   REQUIRES disclosures for ok (your fixture amendment covers the frozen row). `main()`
   loads the registration under an OUTER terminal-artifact boundary (your R2-G1
   parenthetical: load failure → re-raise inside a trivial runner invocation → named
   artifact; process-control never converted), then hands it to the runner.
2. **R3-G2** — the D5 fold-flag vocabulary is CLOSED in the validator
   ({fold_starved, join_coverage_low, join_reconciliation_failed, degenerate_input});
   production emits the registered reason ITSELF as the flag (the prefix string is gone);
   arbitrary flags refuse.
3. **R3-G3** — `lane_manifest_missing` (module-level, directly pinned) reads the ridge
   mapping's `count`; an unreadable shape REFUSES named, never zeroes. Your count-7 case
   is the regression row.
4. **R3-G4** — F25 is the REGISTERED five-artifact set, runner-owned: `F25_FROZEN_SET`
   pins exactly your five paths at your independently measured hashes, resolved against
   the script's OWN repo root (caller cannot select/reduce/redirect), validated before the
   analytics and again pre-publication. The DP/crosswalk pins remain as separate INPUT
   admission (defense in depth, no longer framed as F25). A standing contract row asserts
   set equality with your five and runs the real-repo validation.
5. **R3-G5** — `build_season_rushing` counts ONLY registered qualifying games
   (`(attempts + sacks_suffered) >= 1 OR carries >= 1`); rushing yards still sum over all
   REG rows (the shipped gate reads season totals). Your 398.5-yards example is the
   regression row: one qualifying game → shifted threshold 399 → no flip, no boundary
   membership.
6. **R3-G6** — the package `__init__` docstring is corrected (stale text quoted as
   superseded, not silently deleted).

## Census (measured this session, final tree)

- Frozen bundle (with the one sanctioned amendment): **211/211** · your reinforcement
  **344/344** · correction contracts (now 51 rows: a regression row per R2 AND R3
  finding) **51/51**.
- Your round-3 probe `e6683d06…`: **5/5 reproducers now FAIL.** Your round-2 probe:
  4/4 still fail. Round-1 probe: 1 pass / 12 fail, unchanged (the survivor is the
  by-design raw-pipe refusal).
- Full suite (488s): **6,053 passed / 15 failed / 12 skipped / 0 collection errors** —
  all 15 named failures are `test_governed_cadence_inputs_red.py` (the standing untracked
  RED); zero tracked failures.
- Ruff + strict compile clean on every round-4 file (one real F821 fragility Ruff caught
  in the outer boundary — except-target lifetime — fixed before this request).
- Continuation run: green-review round open (= round 4 of 5), scope recorded.

## The ask

Green-review round 4 of 5: verify the six fixes against your round-3 findings and probe,
audit the single frozen-RED amendment against your own ruling, re-probe the runner
invariant and the F25 set ownership, and rule. **NO execution before your CLEAR** —
David's trigger (re-affirmed verbatim: "run the study when it clears") fires on it. A
round-4 BLOCKER makes round 5 the cap round.

PLEASE REPLY with: (a) CLEAR with enumerated checks, OR (b) NOT CLEAR with
BLOCKER/WARN/STYLE findings and reproducible evidence.

H2 QB rushing remains **UNDER TEST** with no result. `decision_supported=False` throughout.
