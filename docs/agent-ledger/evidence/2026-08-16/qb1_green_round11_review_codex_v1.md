# QB-1 GREEN Round 11 Independent Review — Codex v1

Date: 2026-08-16 ET  
Verdict: **NOT CLEAR**  
Study execution: **NOT RUN**  
H2 QB rushing: **UNDER TEST with no result**

## Submitted state reproduced

- Review request SHA-256:
  `484ba2ffa1fadd1681a7180dc480880a6c2c390209eaa581e71c2b89483dc36c`.
- Exact submitted pins reproduced:
  - `execution.py`: `7b88dc776a476c3535abb904ce31bd7b9a26bab7d349873708b4cd171e31d3f9`
  - `run_qb1_study.py`: `7c8893cac0d91810b84cde3aa2f94425cb75ff9f1ac2ed6c4e8e62b48a12a297`
  - correction contracts: `c539e97e703af4eb0bcecdfd7a2365c5485848330d38f3d75690e50655d8ad1b`
- Scope against the script-owned Round 11 open snapshot is exactly the three
  authorized files. Independent `--numstat`: execution `+173/-34`, runner
  `+37/-23`, contracts `+264/-7` = **3 files / 538 changed lines**.
- No study execution, publication, provider fetch, registered-value change,
  commit, or push occurred in this review.

## Contract-conformance checks

- Independent five-file bundle: **682 passed** in 69.50s.
- Carried Round 10 probe: **2/2 failed as assertions**, which is the expected
  refusal behavior; the two impossible caller partitions no longer publish.
- Ruff: clean on the three submitted files plus the fresh probe.
- Strict Python compilation: clean on the same files.
- Claude's full-suite addendum reports **6,129 passed / 15 failed / 12 skipped**;
  the 15 are the disclosed standing untracked cadence RED. This is cited as
  write-lane evidence, not represented as an independent Codex full-suite run.

The submitted implementation correctly derives dual/pocket totals, boundary
membership, and flip totals from the *disclosed* rows. It also requires cases
to be views over the same disclosed rows. That closes the exact Round 10
opposite-partition examples.

## BLOCKER — R11-G1-F13-SOURCE-TOTALITY

**Criterion:** the David-authorized redesign requires one evidence row for
every evaluable player containing every observed trailing-window season row
the shipped producer read. The public runner's contract says returned payloads
are untrusted and invalid evidence is never atomically blessed
(`execution.py:2224-2230`).

**Defect:** the validator checks only that `len(evaluable_players) ==
n_evaluable` and then derives all F13 values from those caller-controlled rows
(`execution.py:1775-1860`). It never reconciles the disclosed player IDs or
window rows to an independently known fold/input census. Therefore a returned
payload can replace the producer's complete evidence with a different,
internally consistent story and still publish `ok`.

**Reproduction:** fresh public-runner probe
`qb1_green_round11_adversarial_probe_codex_v1.py`, SHA-256
`84a68be5965600345de1ccf04f5b7a4f727e4ecc642c92fcd298f811fbce98c7`,
passes **2/2** (passing is the defect):

1. The shipped producer first computes a one-player `401 rushing yards / 5
   games` fold: dual=1, boundary=1, plus-flip=1, with a non-empty observed
   window. The mutant deletes that window, changes the same player to
   pocket=1 / boundary=0 / flips=0, and publishes `ok`.
2. The shipped producer's `qb-real` evidence and all derived totals are kept,
   but both pool and case identity are changed to `qb-substitute`; the report
   publishes `ok` with the actual evaluable player absent.

This is not a demand that the gate detect an arbitrary fabricated study result.
It is the exact newly introduced F13 evidence object crossing the documented
untrusted-return boundary: whole observed evidence and the required evaluable
identity can each be substituted while every new Round 11 check remains green.
The words “EVERY observed row” and “every evaluable player” are therefore not
mechanically earned.

**Smallest remediation boundary:** bind the F13 `evaluable_players` identities
and per-player window rows to an independently supplied/recomputed fold-input
census at the publication boundary, then derive the partition, boundary set,
and flips from that bound census. Another caller-provided count or commitment
does not close the defect. This review does not authorize that work or a new
round.

## Falsification matrix

| Row | Check | Result |
|---|---|---|
| Valid nominal | Submitted three-player positive + five-file bundle | PASS |
| Boundary | 399/401-yard carried Round 10 mutants | Refuse as expected |
| Missing | Missing/short pool contracts | Refuse, but complete observed window concealment publishes — **BLOCKER** |
| Null/None | Carried five-file suite | PASS; no new null defect established |
| Wrong type / malformed | Submitted row-shape contracts + Ruff/compile | PASS |
| Duplicate/conflict | Duplicate player, season, and case contracts | Refuse as expected |
| Empty collection | Empty window is admitted as claimed absence | Valid shape, but indistinguishable from concealed evidence — **BLOCKER** |
| Cross-component shape | Case-to-pool evidence equality | Refuse on mismatch as expected |
| Numeric edges | Carried low/zero-game and non-finite rows | PASS/refuse per contract |
| Synthetic/override | Fresh producer-output mutations through public `execute` boundary | **2/2 publish `ok` — BLOCKER** |

## Verdict

**NOT CLEAR.** `R10-G1-F13-AGGREGATE-TOTALITY` is fixed relative to disclosed
rows, but the full-evidence redesign does not establish source totality for
those rows. No execution CLEAR exists. The round re-parks for David after the
structured finding, round close, and failed review receipt are recorded.
