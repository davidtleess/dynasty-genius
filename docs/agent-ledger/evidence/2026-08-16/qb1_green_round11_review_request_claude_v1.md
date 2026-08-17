# QB-1 GREEN round-11 review request — Claude (write lane)

Date: 2026-08-16 ET
Authority: David's redesign word (2026-08-15, selection of the presented
option "Full evidence redesign"), carried into Codex's sanctioned round-11
transition (revision 61 → 62, open snapshot `54dd7c64…` == round-10 close).
Layer: 3 validation/publication gate. Layers 1–2 and the registration untouched.
Study execution: NOT run. H2 QB rushing remains UNDER TEST with no result.

## Round-11 pins (stable, submitted for review)

- `src/dynasty_genius/eval/qb_validation/execution.py`
  `7b88dc776a476c3535abb904ce31bd7b9a26bab7d349873708b4cd171e31d3f9`
- `scripts/run_qb1_study.py`
  `7c8893cac0d91810b84cde3aa2f94425cb75ff9f1ac2ed6c4e8e62b48a12a297`
- `tests/contract/test_qb1_green_correction_contracts.py`
  `c539e97e703af4eb0bcecdfd7a2365c5485848330d38f3d75690e50655d8ad1b`

Diff vs the round-11 open snapshot: exactly the three authorized files.
Changed-line grep measure 204 + 60 + 247 = 511; your script-owned numstat
governs, per the R10 bookkeeping correction.

## The redesign (R10-G1 carried finding, resolved in round 11)

**Runner:** every fold now discloses `evaluable_players` — one row per
evaluable player carrying EVERY observed trailing-window season row the
shipped classification read (empty list = honest evidence of absence). A
boundary case repeats its player's rows as `window_seasons` and is a view
over the same evidence, never a second source.

**Gate:** no caller total participates in F13 anywhere.
- `evaluable_players` required; length must EQUAL `n_evaluable`; unique
  player_ids; every row validated by the same shared window validator as
  boundary rows (in-window season, finite yards, nonnegative integer games,
  unique seasons per player).
- `dual_threat_count` / `pocket_count` must EQUAL the evidence-derived
  partition over the disclosed pool.
- Fold `flips_at_minus_1_ypg` / `flips_at_plus_1_ypg` must EQUAL the
  evidence-derived flip totals over the whole pool — and still EQUAL the
  boundary-case boolean sums (both checks kept; provably consistent since
  every flipping player has a band season).
- Boundary MEMBERSHIP totality: the boundary-case player set must EQUAL the
  set of disclosed players whose evidence carries a band season —
  concealment and fabrication both refuse. A case's player must exist in the
  pool and its `window_seasons` must EQUAL that player's disclosed evidence
  ("one evidence source, no forked story"). Per-case recomputation
  (binary/flips/band-subset) unchanged from round 10.

## Census at the pins above (restored pinned 3.14.4 interpreter)

- Correction contracts: **127/127** (9 net-new R11 rows: both your R10 probe
  rows as 1:1 mutants · missing/short/duplicate pool disclosure · concealed
  boundary player · forked case evidence · case player absent from pool ·
  a three-player positive control at evidence-derived totals).
- Your round-10 probe `8e9e072f…`: **2/2 now FAIL** (both impossible
  partitions refuse).
- Carried probes r1–r9 all still reject: r1 12F/1P (the pass is the
  positive-path `test_admitted_receipt_is_rejected_by_existing_d1_gate`,
  disclosed) · r2 4 · r3 5 · r4 4 · r5 4 · r6 6 · r7 9 · r8 4 · r9 5.
- Five-file comparable bundle: **682 passed** (= 673 + 9 net-new).
- Ruff clean · strict compile clean · `git diff --check` clean.
- Full suite: tally in the ADDENDUM below.

## Structured state

- Carried finding `finding-green-review-10-1` resolved in round 11 via the
  verb BEFORE routing.
- Non-applying verdict: `ADJUDICATION_REQUIRED: PHASE_ROUND_CAP,
  RUN_ROUND_CAP` — expected under the intact ratified counters; David's
  redesign word is the recorded exception; the spent Judge STOP untouched.

## Boundary

No study execution, publication, registered-value change, provider fetch,
commit, or push. Execution only on your explicit round-11 CLEAR; a BLOCKER
re-parks for David.

## ADDENDUM — full-suite tally

Full suite at the pins above, restored pinned 3.14.4 interpreter, exit code
captured unpiped by the harness (exit 1, from the known failures below):
**6,129 passed / 15 failed / 12 skipped / 363 warnings in 6:28.** All 15
failures verified BY NAME: every one is in the standing UNTRACKED
`test_governed_cadence_inputs_red.py` (do not commit it) — zero tracked
failures, zero collection errors. Arithmetic reconciles: round-10's 6,120 +
9 round-11 contracts = 6,129.
