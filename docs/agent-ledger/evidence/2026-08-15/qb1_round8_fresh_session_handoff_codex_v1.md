# TW15 QB-1 fresh-session handoff after GREEN round 8

Handoff time: 2026-08-15 08:22 EDT  
Author: Codex review lane  
Repository/worktree: `/Users/davidleess/dynasty-genius-product`  
Run record: `/Users/davidleess/dynasty-genius/.git/worktrees/dynasty-genius-product/dg-autonomy/run.json`

## Start here — do not use chat memory

A fresh session must perform the repository bootstrap before taking any action.
Read, in this exact order:

1. `docs/governance/02-agent-operating-loop.md`
2. `docs/governance/00-product-constitution.md`
3. `docs/governance/05-layer-doctrine.md`
4. `docs/governance/01-north-star-architecture.md`
5. `docs/governance/03-code-hygiene-policy.md`
6. `AGENT_SYNC.md` from line 1 through `⏹ END CURRENT BOARD`, then stop
7. `docs/agent-ledger/2026-08-15.md`
8. This handoff and the round-8 review linked below

Then read the machine state directly:

```bash
cd /Users/davidleess/dynasty-genius-product
"$HOME/.dg-autonomy/bin/dg-autonomy" status
```

Do not infer authority from this handoff, an old goal string, a prior round, or
a non-applying verdict. The machine record and new direct words from David are
the sources of current authorization.

## Terminal state at handoff

- Run id: `f8f7551c-a145-46e2-b9b4-dec427f313ba`
- Revision: **50**
- Role recorded by the run: `claude`
- Phase: `blocked`
- Terminal state: **BLOCKED**
- Reason: `review failed 3 times in green-review`
- Failure counter: `green-review:review = 4`
- Round 8 is closed, not open.
- Round-8 open snapshot: `d937ec4da07094f69b4bc5624d4c47407142befa6376cdc61e7aff2e0d8e3337`
- Round-8 close snapshot: `205d84b2073a567cd205fde01a74984c087fca742cfbbd1902cd1f12a0058f44`
- Measured round-8 churn: **3 files / 657 lines**.
- Findings `finding-green-review-8-1..3` are unresolved.
- No study execution occurred. No QB-1 output was published. No push occurred.
- H2 QB rushing remains **UNDER TEST** with no result.

The installed read-only loop verdict returned `ADJUDICATION_REQUIRED` with an
empty reason list after terminalization. Do not apply or re-docket it. The same
run already has a Judge `STOP` ruling from round 5 (`2026-08-15T02:50:23.167Z`),
and the established machinery rule is one gate, one ruling. The durable outcome
is the terminal `BLOCKED` record above, parked for David.

The run's `goal` string still describes the older “round 4 of 5” continuation.
That text is stale provenance, not live permission. Later bounded exceptions
were recorded as state repairs and are exhausted:

- David authorized the round-5 state repair plus one remediation round (round 6).
- David explicitly authorized one bounded round 7.
- David explicitly authorized one bounded round 8.
- Round 8 ended NOT CLEAR. **No round 9 is authorized.**

## What was reviewed in round 8

Exact pins:

- `src/dynasty_genius/eval/qb_validation/execution.py`
  `913225f529a0c63a30b4ee6b025c3d1ac408a5d6107be15b8a65dc80d83e9f37`
- `scripts/run_qb1_study.py`
  `ef7a8244d5b141eaa7280f37b269531089f5eeeb6649b230b09fcbe50bde86eb`
- `tests/contract/test_qb1_green_correction_contracts.py`
  `513ed1bd255c9c62368bcb68f8cacfbfdc3284aa5c9df3a0c8a36affd46b9b58`

Unchanged supporting pins verified:

- `status.py` `6765182185ad82e048a8f37736f8285795ac4db6dec4c7d47d22ae0a302cba79`
- `__init__.py` `d8876020f1fe3414d75612d5a4abfd26307ce9e9bfbdbfe6480ffcf8c81a9518`
- execution RED `5d3bc660aed3bbb63604ab1d8ac829bf4876213a53469d69ef7c71feffd77c5a`
- program RED `7e95079297a269dc13c26371e6e92a598ffaf8ea14e5dc9a474f0c2eea190dfe`
- inference ratchet `25c4ffde3421f804e3a2fb17a42438c43deb9673188fe099e2903c443b3827f1`
- reinforcement `db351f8c321bd83179a8bab17beffc435709265e23909aff64468ecae981790d`

Round 8 changed exactly the three authorized files relative to its open
snapshot. Do not treat the repository-wide dirty tree as belonging to this
review; it contains unrelated concurrent user/agent work. Do not revert,
clean, stage, or overwrite unrelated changes.

## Round-8 verdict: NOT CLEAR

The full evidence-backed review is:

- `docs/agent-ledger/evidence/2026-08-15/qb1_green_round8_review_codex_v1.md`
- SHA-256 `4f155f1e04fbefeb492675d76a4d9dffa49f69a38f1831cfef008bed7668d47d`

The independent public-runner reproducer is:

- `docs/agent-ledger/evidence/2026-08-15/qb1_green_round8_adversarial_probe_codex_v1.py`
- SHA-256 `750f8213945cccf71c969ce7417ed4f7577ee5e7a709c988418a4b57a1bb254b`

Three unresolved BLOCKERs:

### 1. R8-G1-H5-SPECIAL-CASE

At `execution.py:1291-1335`, the below-fold-floor H5 exception activates when
any inference numeric is missing, but checks only the status and flags. It does
not require all inference numerics to be unavailable and does not enforce
`ni_met=False`.

Reproducer:
`test_h5_below_floor_partial_evidence_can_claim_ni_met`.

Invalid accepted report: two evaluable folds, finite `pooled_delta` and `p_ni`,
missing adjusted/one-sided evidence, `ni_met=True`, yet `unsupported_power`
publishes successfully.

Smallest correction: the direct below-floor exception must require all
inference numerics null, `ni_met=False`, the registered status, and exactly the
registered below-floor flag. Complete evidence must go through the shipped
total function; partial evidence must refuse.

### 2. R8-G2-EVALUABLE-RECONCILIATION

At `execution.py:1388-1468`, H5 fold reconciliation counts contrast-key
presence. The per-fold validator permits a keyed row with
`paired_delta=None`, both Spearmans null, and `common_pool_n=0`, so key presence
is not mechanical evaluability.

Reproducer: `test_h5_key_presence_counts_a_non_evaluable_fold`.

Invalid accepted report: c11 claims four evaluable folds while one of four
keyed fold entries is mechanically non-evaluable.

Smallest correction: derive the exact evaluable season set from the emitted
metric content using the producer's admission invariant, require equality with
the aggregate contributing/evaluable claim, and make excluded seasons the
registered complement. Do not add exclusions to a key-presence count.

### 3. R8-G3-F13-TOTALITY

At `execution.py:1630-1727`, recomputation checks a flip only when the submitted
boolean is true. False negatives are trusted. Aggregate flip counts also are
not required to equal the sums of boundary-case booleans.

Reproducers:

- `test_f13_false_negative_flip_publishes`
- `test_f13_aggregate_flip_count_disagrees_with_cases`

Invalid accepted reports: a 401-yard/five-game case mechanically flips at the
+1-yard/game threshold but may report false; an honestly true case may coexist
with an aggregate count of zero.

Smallest correction: recompute both per-case flip booleans and require exact
equality in both directions, then require per-fold aggregate flip counts to
equal the sums across boundary cases.

## Independent verification already completed

Focused submitted/frozen bundle:

```bash
.venv/bin/python3.14 -m pytest -q \
  tests/contract/test_qb1_green_correction_contracts.py \
  tests/contract/test_qb1_execution_red.py \
  tests/contract/test_qb_validation_program_red.py \
  tests/contract/test_qb_validation_inference_red.py \
  tests/contract/test_qb_validation_green_reinforcement_red.py
```

Result: **646 passed**, 14 known numerical warnings, exit 0.

Prior round-7 probe:

```bash
PYTHONPATH=. .venv/bin/python3.14 -m pytest -q \
  docs/agent-ledger/evidence/2026-08-15/qb1_green_round7_adversarial_probe_codex_v1.py
```

Result: **9 failed as expected**; all nine prior invalid examples now reject.

Fresh round-8 probe:

```bash
PYTHONPATH=. .venv/bin/python3.14 -m pytest -q \
  docs/agent-ledger/evidence/2026-08-15/qb1_green_round8_adversarial_probe_codex_v1.py
```

Result: **4 passed**. Passing is the defect: each test asserts that an invalid
report reached public `run_status=ok`.

Ruff on the three scoped files plus the probe, strict Python compilation, and
`git diff --check` were clean. The full suite was not independently rerun after
the public-boundary blockers reproduced; Claude's submitted full-suite tally is
author evidence only and was not used for the verdict.

## Durable records

- Current board top block: `AGENT_SYNC.md`, “QB-1 GREEN ROUND 8 NOT CLEAR”.
- Daily ledger: `docs/agent-ledger/2026-08-15.md`, Codex 08:09 ET entry.
- Claude round-8 request:
  `docs/agent-ledger/evidence/2026-08-15/qb1_green_round8_review_request_claude_v1.md`
  (`38b49bc9858d1b8e4276990c505a2265172d4ecd0794aee22b515e2e14dec7dd`).
- NOT CLEAR wire:
  `docs/agent-ledger/evidence/2026-08-15/qb1_green_round8_not_clear_wire_codex_v1.md`
  (`6db45bb5b77994ef312d4183fe03147ba78f39743f525699347eebc2bec90f0b`).
- Pre-final checkpoint, superseded by the complete review:
  `docs/agent-ledger/evidence/2026-08-15/qb1_round8_review_checkpoint_codex_v1.md`
  (`31df4b6a1b80566db7f6f7ca8697455f2e0f7c0eb7e2bef8784fdbf977637e39`).
- QB-1 registration:
  `docs/validation/2026-07-21-qb-1-study-registration.md`.

The NOT CLEAR message was positively verified in Claude's transcript under the
Wire Rule. Claude had already begun read-only verification from durable state
and independently confirmed R8-G1 by code read. No further action depends on a
chat acknowledgment.

## Safe resume action

Until David gives new direct authority, the fresh session should report exactly
one terminal state: **BLOCKED**. It may perform read-only verification, but it
must not:

- open round 9;
- resolve the three findings;
- edit the three product/test files;
- run the QB-1 study;
- publish a result;
- claim H2 is established;
- commit or push;
- apply or re-docket the empty-reason adjudication verdict.

Smallest resume action: David directly authorizes a specifically bounded next
step. If he authorizes another remediation round, record that exact word through
the revision-guarded sanctioned mechanism, carry the three unresolved finding
ids unchanged, limit writes to the explicitly authorized files, and require a
fresh independent review. Study execution remains held until an explicit Codex
`CLEAR` under whatever new authority David supplies.
