# QB-1 execution framing v2 — independent round-2 review (Codex v2)

Date: 2026-08-14  
Work item: `TW14-QB1-1`  
Reviewed artifact: `qb1_execution_framing_claude_v2.md`  
Reviewed SHA-256: `cbd7bb34f8d05f2d9816b6af1af0ae1c2953f35ab74de44636354f49f0facc33`  
Verdict: **NOT CLEAR — two BLOCKERs, one WARN**

This is an execution-mechanics review only. The study was not run, no provider
was contacted, and no registered value was changed. QB rushing production (H2)
remains **UNDER TEST** with no result.

## Integrated round-1 findings

1. QB-R1-B1 is integrated: every machine artifact is under the frozen
   `app/data/backtest/qb_validation` root; `docs/validation/` is success-only
   publication.
2. QB-R1-B2 is integrated: all nine strict XFAILs are named, together with H5
   total status, D5 assembly, orchestration, failure-with-no-metrics, atomic
   terminal writes, and same-change unpark rules.
3. QB-R1-W2 is integrated: the real newline-terminated registration is the
   canonicalization positive control and the two hash failures stay distinct.
4. QB-R1-B3, QB-R1-B4, and QB-R1-W1 are improved but not yet fully resolved for
   the reasons below.

## Independent checks

1. Reproduced the v2 artifact hash exactly.
2. Re-ran the five principal QB validation contract modules: **517 passed, 9
   xfailed**. The XFAIL census is exactly F10/F13/F16/F18/F25/F29/F31/F32/F33.
3. Verified the governed D1 raw root is absent and found no artifact carrying
   `qb_validation_ingest.v2` / `nflreadpy_qb_validation` provenance. Under the
   registration's own admission law and the no-legacy-substitution rule, local
   admission is therefore **0/7 datasets**.
4. Verified the pinned crosswalk at `8ed4b675...`: 7,952 rows, 4,652 non-null
   `fantasypros_id` values, 4,652 unique claims, and zero multi-GSIS claims.
5. Measured the four pinned DP files through the proposed `fp_id` route. QB
   identifier coverage is 77/78, 68/68, 86/86, and 82/82; every DP QB `fp_id`
   is nonblank and unique within its fold.
6. Applied the shipped, registration-pinned F32 `normalize_name` function to the
   joined raw DP and crosswalk names. Mismatches are 2/77 (2.60%) in 2021, 2/68
   (2.94%) in 2022, 2/86 (2.33%) in 2023, and 0/82 in 2024. The named pairs are:
   Phillip Walker/P.J. Walker, AJ McCarron/A.J. McCarron, and Mitch
   Trubisky/Mitchell Trubisky as applicable.

## Findings

### QB-R2-B1 — BLOCKER — B3 still defers a route decision that is already measurable

Round 1 required an honest data route before RED. V2 instead defers the local
admission census to RED time. The governed raw root is absent, no local artifact
carries the registered validation-ingest provenance, and legacy substitution is
barred. The answer is therefore already **0/7 locally admissible**. All seven
registered datasets — weekly, season summary, players, rosters, ff-playerids,
draft picks, and play-by-play — require provider-backed capture under the
current implementation.

**Required correction:** v3 must record 0/7, name all seven requested fetches
with their exact registered temporal scopes, and put that list to David for a
single explicit provider yes/no before RED/run initialization. The RED can pin
the fetch boundary, but it must not be used to postpone the authority decision.

### QB-R2-B2 — BLOCKER — the chosen H5 bridge deterministically fails F32 in three folds

V2 settles Q1 after measuring only identifier coverage and duplicate behavior.
That omits the independent gate the design deliberately preserved. On the real
pinned files and crosswalk, the registered `>2%` F32 threshold excludes 2021,
2022, and 2023. Only 2024 passes, below the registered H5 floor of 3/4. Thus the
currently frozen route deterministically yields `unsupported_power` for every
H5 contrast before any model result exists.

This is not permission to tune normalization, add aliases, change the threshold,
or reopen a registered value. It is a pre-result identity-gate fact.

**Required correction:** v3 must record the four measured F32 rates and the
honest `unsupported_power` consequence; the RED must pin the real-file
preflight and prove no H5 primary metrics are emitted when the fold floor is
unmet. If Claude proposes any alternative identity input or transformation,
that is a registration/authority question and must be put to David rather than
silently substituted.

The coverage RED must also use the registered denominator — the fold's
model-evaluable population — rather than raw DP QB row counts. The counts above
are route-availability measurements, not the final F18 denominator.

### QB-R2-W1 — WARN — the backup-manifest target remains unnamed

V2 pins `raw/dp_values/` but says only that "the backup_manifest entry" lands
with it. Provider-backed D1 capture will place seven additional raw snapshots
beside that child. Pin one required directory entry for
`app/data/backtest/qb_validation/raw` so both the four GPL files and every D1
snapshot are covered; a `raw/dp_values`-only entry would leave the study's
irreplaceable D1 evidence uncovered.

## Gate posture

The scorer amended-commit audit is CLEAR, but QB-1 framing v2 is not. No QB
autonomy run or RED round should open until the two blockers are resolved.
Provider contact, data copy, manifest mutation, study execution, result
publication, commit, and push remain untouched.

