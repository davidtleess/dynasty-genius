# CFBD promotion + QB-1 board review — Codex v1

Date: 2026-08-03  
Verdict: **NOT CLEAR** — five CFBD/promotion corrections, three QB-1 corrections, and one ordering correction are required before this board is executable.

## Scope and authority read

David's exact word was: **"yea make the fresh data live! then add teh qb 1 study to the to-do list you just created with codex. have codex review all this"**.

- This authorizes making the corrected CFBD dataset live, subject to a safe promotion contract.
- It authorizes adding QB-1 to the to-do board. It does not say to execute QB-1 now. The ratified registration explicitly reserves study execution as a separate David word, so the board must not convert a scheduling instruction into execution authority.
- Neither clause authorizes model promotion or a favorable scientific conclusion.

## Independently reproduced CFBD delta

Fresh: `app/data/sources/cfbd_foundation/curated/prospects_with_outcomes_v3.csv`  
Active: `app/data/training/prospects_with_outcomes_v3.csv`

- Header and column order: identical, 173 columns.
- Rows and identity: 874 / 874, `gsis_id` unique in both, identical key set and identical row order.
- Changed population: exactly **117 players, all QB; zero non-QB rows**.
- Changed cells: **1,123**, not merely “117 changed prospects.”
- The delta is confined to exactly 12 QB columns: four value fields, four `_source` fields, and four `_missing` fields. Counts: completion 111, YPA 111, TD:INT 110, sack rate 87; completion/YPA/TD:INT sources 88 each, sack-rate source 107; completion/YPA/TD:INT missing flags 82 each, sack-rate missing flag 87.
- Fresh manifest binds run `20260802T024342156864Z`, input SHA `b3c28e42…`, curated SHA `15e17cd9…`, 874 rows, 100% identity coverage, and the four QB coverage figures.

## Blocking CFBD findings

### C1 — the deferred-list strike overstates David's authorization

The board strikes `CFBD promotion / bakeoff / model use` as one unit and labels it authorized. David authorized making the fresh **data** live. He did not authorize model promotion, and the wording does not grant a general bakeoff/model-use program. Split the line: move **data-artifact promotion** off the deferral list; retain **model promotion/model use** as deferred. Any non-promoting validation required to prove the data promotion safe is part of the promotion gate, not blanket authority over every model consumer.

### C2 — the nine paths are not a downstream-validation surface

They are a path census with incompatible side effects:

- `run_phase20_bakeoff.py`: relevant non-promoting QB evaluator; writes a bakeoff artifact.
- `run_head_a_bakeoff.py`: its QB contract is baseline-only, so the four changed QB fields are not evaluated.
- `run_head_b_bakeoff.py`: QB is explicitly skipped; non-QB rows did not change.
- `promote_head_a_te_v3.py`: writes a model artifact; it is a promotion command, not validation, and TE inputs did not change.
- `build_w2_features.py`, `build_w2b_cfbd.py`, and `build_head_b_targets.py`: mutate or overwrite the active training CSV; they must not be run as post-promotion validators.
- `run_cfbd_foundation_refresh.py`: paid refresh driver using the active CSV as input, not a downstream evaluator.
- `cfbd_foundation_refresh.py`: isolation/publication wrapper, not a model consumer.

Replace “re-run across the nine consumers” with an explicit command allowlist and expected side effects. At minimum, candidate validation must run against an explicit input-path override or an isolated copy; it must not temporarily replace the active CSV to make a hard-coded runner see the candidate.

### C3 — data correctness and predictive promotion are conflated

The corrected dataset may be promoted even if a Phase-20 QB candidate fails scientifically. A negative bakeoff means “do not promote those features into a model,” not “keep known-bad values in the canonical data input.” Conversely, making the data live does not promote any model. The current runtime Engine A QB scorer remains pick/round/age, and the changed file contains zero non-QB deltas. Record the evaluation outcome, but do not make correct substrate conditional on predictive lift and do not describe data promotion as a regrade.

### C4 — the promotion invariant is prose, not a fail-closed contract

The mechanism must refuse unless all of these hold:

1. Source manifest status/run/hash are exact and the fresh file hashes to its recorded `curated_sha256`.
2. The active file still hashes to the refresh manifest's `input_sha256` (compare-and-swap; prevents overwriting a newer active edit).
3. Same 173-column header/order, 874 unique `gsis_id`s, identical key set and row order, zero added/deleted rows.
4. Every changed row is QB and every changed cell is in the exact 12-column allowlist above; zero unexplained deltas.
5. Fresh QB range, collision, coverage and identity gates are re-run locally without a paid call.
6. The replace is atomic and lock-protected.
7. A durable preimage is written and hash-verified before replacement; rollback is an explicit tested operation, not merely a backup file.
8. A promotion receipt binds source run, source/active pre-hashes, post-hash, exact delta summary, code revision, validation commands/results, timestamp, and recovery state.
9. Crash recovery is defined for the active-file/receipt boundary; no success may be reported for an unreceipted or hash-mismatched replacement.

### C5 — the board is not enough to open implementation

This creates a new governed producer/CLI and mutates the canonical training input. Open a focused promotion framing and RED contract before GREEN. The RED must include positive controls for stale-active CAS, an out-of-allowlist cell, row reordering, partial/failed receipt publication, rollback, and a validator that attempts to mutate the candidate.

## Blocking QB-1 findings

### Q1 — scheduling is not execution authority

The direct object of David's instruction is **add the study to the to-do list**. The board may say `SCHEDULED`; it must not say “Execution is David's word.” The ratified registration says execution requires a separate David word. Keep `study execution: pending David` until he explicitly says to run it.

### Q2 — “machinery is BUILT” overstates readiness

Thirteen library modules exist, but repository search finds no end-to-end study runner/orchestrator. The registration itself names the standalone DynastyProcess H5 loader bridge as unbuilt execution-time work. State: **analytical primitives/contracts are built; executable orchestration and the registered H5 source bridge remain to be completed and reviewed**. An item can be scheduled without pretending it is runnable.

### Q3 — the result ceiling needs the two omitted locks

Keep the existing UNDER TEST, veteran-cohort and separate-ruling language, and add:

- the target is the counterfactual pinned **2026** scoring rule applied to every study season, not historical league scoring;
- no registered contrast tests H2's marginal/conditional contribution, so no result can license “rushing adds value on top of other features”; partial/interim output is not a result and `decision_supported=False` remains recursive.

The canonical registration hash independently reproduces as `37065566…` after sorted compact JSON canonicalization. The raw file-byte SHA differs by design because the checked-in JSON has a trailing newline.

## Board ordering finding

The board still says “four steps, then STOP,” then inserts A and B after step 4 without assigning either a position. That is not one executable order and overloads the board by ambiguity. Record one total order or separate **authorized immediate work** from **scheduled backlog**. David's syntax puts CFBD first; QB-1 is added to the list, not necessarily ahead of the foundation sequence. If its exact position is material, ask David rather than infer it.

## Required disposition

Revise the board; do not promote, run a bakeoff, change a model, or execute QB-1 from the current text. Return the corrected board and the focused CFBD promotion framing for another review round.

## Round 2 residual audit

Claude accepted all nine findings and closed their substance. Two exact-line residues remain in the
actual corrected file:

1. `### The order — four steps, then STOP` now precedes numbered items 1 through 5. Change `four`
   to `five`; the heading otherwise contradicts the total order it introduces.
2. The backlog line still says `QB-1 study execution (block B)` while the next clause and block B
   correctly say execution is not authorized. Rename the item `QB-1 study (block B; execution
   pending)` or equivalent. Scheduling a study onto a backlog must not leave the execution noun as
   the scheduled object after the authority correction.

No other residual found. On those two line edits, the board is CLEAR; the CFBD promotion framing
still returns separately before any RED or implementation.

### Round 2 result

Both exact lines are corrected in the file and `git diff --check` is clean. **BOARD CLEAR.** One
non-board authority correction remains for the handoff prose: David's existing “make the fresh data
live” word already authorizes CFBD data promotion after the registered framing/RED/GREEN/CLEAR gate;
it does not require a new post-CLEAR promotion word. Commit/push authority remains a separate matter.
