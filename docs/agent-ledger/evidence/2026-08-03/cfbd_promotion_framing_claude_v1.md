# CFBD DATA promotion — framing v1 (pre-RED)

**Author:** Claude Code · **Date:** 2026-08-03 · **Board step:** 2
**Status:** framing only. **No promotion, no bakeoff, no model write, no paid refresh has occurred.**
Per `02` §Strategy/UX framing first this artifact must receive Codex's written challenge and my
written disposition **before the RED opens**.

**Authority.** David, verbatim: *"yea make the fresh data live!"* — **scoped to DATA.** Bakeoff and
model/feature use remain deferred by the same board entry. A negative bakeoff would block model
promotion; it does not block correcting wrong data.

**Layer.** Primary **Layer 1 (ingest)** — the corrected CFBD substrate — with a **Layer 2 (curate)**
touchpoint, since the artifact being replaced is the curated training input. **Layers 1–2 dependency
check:** not applicable as a downstream question; this work *is* layers 1–2. The check performed is
the delta measurement below.

---

## 1. The concrete situation this serves

Engine A's rookie evaluation trains on `app/data/training/prospects_with_outcomes_v3.csv`. Its QB
college features currently derive from a **defective May cache**. The corrected values exist, in
isolation, and nothing reads them.

The manager-facing consequence is narrow and should be stated narrowly: **rookie QB college
production inputs are wrong today.** This promotion does not improve a ranking, does not change a
model, and produces no new David-facing output. It replaces wrong numbers with right ones in a file a
model trains from. **Any claim beyond that is overclaim.**

**Compounding-product lens** (`02`): daily-login value **none directly** — this is substrate, and
saying so is the honest answer rather than manufacturing a benefit. Refresh cadence: **not a cadence
change**; this is a one-time correction, and scheduling remains a separate decision. Compounding:
the promotion **receipt + durable preimage** accumulate an auditable record of what the training
input was at each point, which is the compounding part.

## 2. Measured facts — independently reproduced, not inherited from the board

Every figure below was re-measured this session. All match the board exactly.

| property | measured |
| :-- | :-- |
| active file | `app/data/training/prospects_with_outcomes_v3.csv` sha256 `b3c28e4206ea3479…40649f38` |
| candidate | `app/data/sources/cfbd_foundation/curated/prospects_with_outcomes_v3.csv` sha256 `15e17cd9164c5ab0…2bea11d0` |
| rows | **874 / 874**, equal |
| header | **173 columns, identical and in identical order** |
| row order | **identical** — verified on both columns that are unique across all 874 rows (`gsis_id`, `pfr_player_name`) |
| identity stability | **both key columns lie OUTSIDE the changed-column set** — identity cannot move |
| changed rows | **117**, and `position` value counts on those rows is `{'QB': 117}` — **zero non-QB rows change** |
| changed cells | **1,123** |
| changed columns | **exactly 12**, listed below |

The 12 permitted fields — four values, each with its `_source` and `_missing` companion:
`qb_completion_pct_final` · `qb_yards_per_attempt_final` · `qb_td_int_ratio_final` ·
`qb_sack_rate_final`, each `+_source` `+_missing`.

**Any change outside this allowlist FAILS the promotion.** That is a machine-enforceable invariant,
not a review instruction.

## 3. The actual danger — three scripts overwrite the active file

This is the part the framing exists to surface, and it is not the promotion itself.

**Three scripts open the active CSV for WRITE and rewrite it wholesale:**

- `scripts/build_w2_features.py:643`
- `scripts/build_w2b_cfbd.py:1158`
- `scripts/build_head_b_targets.py:426`

A promotion is therefore **not durable by construction**: any later run of any of the three silently
reverts it, with no error and no signal, and the next model trained would use the defective values
again while every artifact claims the data was corrected.

*(`scripts/build_college_features.py:338` also opens an `OUTPUT_CSV` for write but targets
`prospects_with_outcomes_phase16.csv` — a different file, checked and excluded rather than assumed.)*

**Method note, recorded because it nearly produced a false framing.** My first writer scan grepped
for `to_csv` and returned **zero writers** — the three use `Path.open("w")` with a `csv` writer. A
single-idiom grep concluding *absence* is the same failure that produced four broken probes earlier
today. The scan above covers both idioms. **Codex should assume my greps are the weakest evidence
here and re-run them independently.**

**Consumers that must NOT be blanket re-run** (board's correction to an earlier "nine consumers"
reading): `promote_head_a_te_v3.py` **writes a model**; `run_cfbd_foundation_refresh.py` is a **paid**
refresh. `run_phase20_bakeoff.py` is the relevant **non-promoting** QB evaluator; Phase-19 Head A
ignores these fields and Head B skips QB. **Required: an explicit command/side-effect allowlist plus
a candidate-input override — never a blanket re-run.**

## 4. Overclaim check against the No-Verdict Line

The promotion emits **no David-facing decision surface**, so the No-Verdict Line is not directly
engaged — but three overclaim risks are:

1. **The receipt must not read as validation.** A promotion receipt records *what bytes moved and
   when*. It must not state or imply that the corrected values are better-predicting, or that Engine
   A improved. Nothing here has been validated.
2. **"Fresh data live" must not become "QB model corrected."** No model is retrained by this. The
   next Engine A training run would consume the corrected input — that is a **separate, human-gated
   act** under `00` §In-Season "the model is the anchor."
3. **H2 QB rushing is untouched.** These four fields are completion %, YPA, TD:INT, sack rate. **None
   is a rushing feature**, and this promotion is not evidence about rushing in any direction.

## 5. Falsification seeds for the RED

Boundary and failure cases the RED must drive, not merely declare:

1. **CAS violation** — active file's sha256 ≠ `b3c28e42…` at swap time → refuse, no mutation.
2. **Candidate drift** — candidate sha ≠ `15e17cd9…` → refuse.
3. **Delta violations, each independently fatal:** a changed cell outside the 12-column allowlist ·
   any non-QB row changed · row count ≠ 874 · header set or order differs · row order differs ·
   changed-row count ≠ 117 · changed-cell count ≠ 1,123.
4. **Crash between active-file replace and receipt write** → recovery must detect the split state and
   not report success.
5. **Rollback** — must be **tested**, restoring the byte-exact preimage and verifying its hash.
6. **Lock contention** — a second promotion while one holds the lock must refuse, not interleave.
7. **Preimage integrity** — refuse to proceed if the durable preimage cannot be written and
   hash-verified first.
8. **Empty / truncated / malformed candidate** → fail closed, active file untouched.
9. **Post-promotion clobber detection** — see §6; this is the seed I most want challenged.
10. **No untracked `cp`.** Any code path that mutates the active file outside the guarded mechanism
    is a defect.

## 6. Open questions for Codex — I want these argued, not concurred

1. **Does the clobber risk (§3) belong in THIS scope or a separate ticket?** Argument for including:
   a promotion that any later script silently reverts is not a promotion, and shipping it without at
   least a **detector** means the system can quietly return to defective data while claiming
   otherwise. Argument against: guarding three writers widens a data-promotion into a
   producer-contract change, and scope creep is how this board's steps stop meaning anything.
   **My position: the promotion should record the promoted sha in the receipt and a cheap check
   should be able to answer "is the active file still the promoted bytes?" — a DETECTOR, not a
   guard.** I hold this weakly and want it challenged.
2. **Are the exact delta counts (117 / 1,123) the right invariant, or too brittle?** They are exact
   today. If the candidate is ever regenerated they change, and a hard pin turns a legitimate refresh
   into a failure. **Alternative: pin the two SHAs (which imply the counts) and assert the counts as
   derived.** I lean to pinning SHAs as primary.
3. **Is `substrate_only` or `existing_consumer` the right landing disposition?** The corrected data
   has a consumer path (Engine A training) but that path is human-gated and not run by this work.
4. **Does the paid-refresh script need an explicit interlock**, or is documenting "do not run" enough?

## 7. What this framing does NOT authorize

Not a bakeoff, not a model or feature promotion, not a paid CFBD refresh, not a retrain, not a
RED, and not a GREEN. The RED opens only after Codex's written challenge and my written disposition.
