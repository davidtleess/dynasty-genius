# DVS clamp-disclosure GREEN review — Codex v1

Date: 2026-08-18  
Thread: `w#dvs-disclosure-1`  
Verdict: **NOT CLEAR — one blocking semantic finding**

## Finding F1 — the newly exposed Engine A flag can make a false truncation claim

`PlayerValueObject.dvs_clamped` is defined as true only when raw DVS **exceeded**
100 before clamping. The new batch serializer faithfully passes that field through,
but the Engine A producer does not compute that meaning. Both Engine A scorers first
clamp and round the score (`scoring/engine_a.py:112-113`, `:210-211`), after which
`pvo_assembler.py:362` and `:442` infer the flag with
`engine_a_result["dynasty_value_score"] >= 100.0`. A raw score below 100 can round to
100.0, so the artifact would say it was clamped when it was not. The blend path has
the same output-based inference at `pvo_assembler.py:429` and needs an explicit
semantic disposition too.

Independent assembler-to-batch counterexample:

```text
p90 = 14.6
raw_ppg = 14.5994
reconstructed raw DVS = 99.99589041095889
shipped DVS = 100.0
serialized dvs_clamped = true
```

The new five-test contract cannot catch this because it injects already-final PVO
dictionaries with hand-authored booleans rather than composing the scorer,
assembler, and serializer.

Required before CLEAR:

1. Derive and carry Engine A clamp truth from the pre-clamp/pre-round raw value,
   rather than the shipped score.
2. Define and test the blend meaning instead of inferring it from the rounded blended
   result.
3. Add cross-component contracts covering raw just below 100 but rounding to 100,
   raw exactly 100, raw above 100, and the existing Engine B exact-P90/above-P90
   distinction.

The 23-row current census is 22 Engine B rows with `projection_2y` present and one
Engine A row with `projection_2y` absent. Therefore this is not a theoretical
dead-path concern: the disclosure increment reaches an Engine A ceiling row, even
though the retained card currently labels that row true.

## Requested dispositions

- **Fixture widening: legitimate.** `test_surface3_pvo_preservation.py` still exact-
  compares the entire non-Surface-3 projection and still proves the ten Surface-3
  keys are the only keys contributed by that feature. Updating its current baseline
  for an independently authorized additive valuation-schema change does not weaken
  that invariant.
- **Artifact-only boundary: accepted as a bounded partial increment, never as R1
  closure.** `PlayerModelLane` and its constructor omit both disclosure fields, and
  the three generated frontend contracts are concurrently modified by the parked
  capture-health thread. Deferring that collision-prone API increment is correct.
  The honest status remains **half-closed** after this artifact increment is repaired;
  the user-readable API still ships a bare ceiling value.
- **No-Verdict ceiling:** the two keys disclose that truncation occurred and identify
  the reference, but an Engine A row has no serialized raw numerator/projection, so
  this increment must not be described as full delivery of unclamped arithmetic.

## Checks independently run

- Reviewed the complete three-file diff and verified pins:
  `188307a5…`, `dbfa0ba2…`, `60dceec5…`.
- Focused plus upstream DVS contracts: **17 passed**.
- Claimed adjacent bundle (Surface 3 endpoint, market-divergence rebase, exact-shape
  preservation): **33 passed**.
- Ruff on the production file and both touched contracts: **pass**.
- `git diff --check`: **pass**.
- Runtime census re-derived: **12,220 rows; 23 ceiling rows; 22 Engine B / 1 Engine
  A; 22/22 B ceiling rows carry `projection_2y`; the A ceiling row does not**.
- Confirmed the API omission at `app/api/routes/players.py:65-74` and `:265-276`, and
  confirmed the three generated frontend contract files are already dirty in the
  parked capture-health work.

Nothing was committed or pushed. No implementation, product artifact, generated
frontend contract, store, scheduler, or parked-path content was changed by this
review.
