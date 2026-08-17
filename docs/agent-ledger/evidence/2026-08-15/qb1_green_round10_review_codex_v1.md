# QB-1 GREEN round-10 independent review — Codex

Date: 2026-08-15 ET
Verdict: **NOT CLEAR — one F13 evidence-totality BLOCKER.**
Layer: 3 validation/publication gate. Layers 1–2 and the registration were not
changed. The registered study was not executed. H2 QB rushing remains **UNDER
TEST with no result**.

## Submitted packet and scope

The routed request reproduced at SHA-256
`b0f2765dcf496fe5227eb7aeed162ccfa4f564916907ccfffebb713de4ae4877`.
All three submitted pins reproduced independently:

- `execution.py` — `68c72468c8022ad815ac96eb6594782b618354ae151320bf17c3aae085665eae`
- `run_qb1_study.py` — `c9720e1bc08cd0e85c7a4929c6d4bd219b4dca9ffdea3bf59f900b97203fa4cc`
- correction contracts — `5246eaa5ca2f577f15635f185ac2ed72b6e5a3257c786d4aa1f03887e428f1e9`

The diff against the round-10 open snapshot is confined to exactly those three
authorized files. One non-semantic packet mismatch: standard
`git diff --no-index --numstat` measures 129+50, 24+19, and 302+37 = **561**
changed lines, not the request's 529. The pins and file scope match.

## Independent verification

- Restored interpreter: Python 3.14.4 baseline retained.
- Exact five-file comparable census: **673 passed / 0 failed** in 43.57s.
- Carried round-9 public-runner probe: **5/5 tests fail at their former `ok`
  assertion**, each mutant now publishing `run_status=failed` as required.
- `uvx ruff check`: clean on all three scoped files.
- strict `py_compile`: clean on all three scoped Python files.
- `git diff --check`: clean on all three scoped files.
- Routed full-suite evidence: 6,120 passed / 15 failed / 12 skipped; all 15
  failures are the standing untracked governed-cadence RED file, with no new
  failure class.

R9-G1 is corrected: the H5 gate binds the registered pool floor, recomputes the
producer-shaped delta, requires exact equality including nullness, and derives
evaluable folds from that reconciliation. The carried three H5 mutants refuse
and the floor-edge positive controls pass.

The F13 window disclosure materially improves the gate: it replaces the
trusted high-season count, validates unique player/season rows and window
membership, binds the exact boundary subset, recomputes each disclosed binary
classification and flip, and reconciles both flip aggregates.

## BLOCKER R10-G1 — F13 base-classification aggregates still trust caller totals

`execution.py:1688-1695` checks only that caller-supplied
`dual_threat_count + pocket_count == n_evaluable`. The gate later recomputes
each boundary player's `binary_dual_threat` from its full window evidence at
`execution.py:1863-1876`, but never reconciles those booleans to the two fold
counts. Only flip aggregates are derived from case rows at
`execution.py:1902-1914`.

Fresh public-runner probe
`docs/agent-ledger/evidence/2026-08-15/qb1_green_round10_adversarial_probe_codex_v1.py`
at SHA-256
`8e9e072f963077b1fc703ab4c39c41c5e4161509142460c11d79c495ab51d362`
passes **2/2**, demonstrating both impossible directions publish `ok`:

1. `n_evaluable=1`, sole disclosed boundary player recomputes **dual=True**,
   while the fold claims `dual_threat_count=0, pocket_count=1`.
2. `n_evaluable=1`, sole disclosed boundary player recomputes **dual=False**,
   while the fold claims `dual_threat_count=1, pocket_count=0`.

Both payloads are impossible under the shipped producer. They retain valid
window evidence, exact boundary subset, exact case booleans, exact flip
aggregates, unique ids/seasons, and a valid partition total; the remaining
trusted fold counts are the only bypass. This is the unresolved part of the
R9-G2 requirement to derive classifications, counts, and fold aggregates from
rows rather than trusting caller totals.

## Smallest honest remediation / disposition

A boundary-only disclosure cannot derive exact dual/pocket totals because
non-boundary players are absent. Exact totality requires per-evaluable-player
classification evidence (with unique player ids and the producer-read window
rows), from which the gate derives `dual_threat_count`, `pocket_count`,
boundary cases, and both flip totals. Merely adding lower-bound checks against
boundary rows would reject these two probes but would not satisfy exact
aggregate totality.

Round 10 is the user-sanctioned final bounded round. This finding therefore
re-parks for David as a redesign decision; it is **not** a request for round 11.
No CLEAR is issued. No study execution, publication, commit, or push is
authorized.
