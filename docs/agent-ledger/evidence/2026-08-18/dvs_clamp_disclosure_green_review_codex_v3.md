# DVS clamp-disclosure GREEN re-review — Codex v3

Date: 2026-08-18  
Thread: `w#dvs-disclosure-1`  
Verdict: **NOT CLEAR — blend fixed; two mutation-surviving seams remain**

## Closed from v2

The blend implementation now matches the public contract: `dvs_clamped=False`
because the shipped blended score is not itself truncated. Consequently
`xvar_ceiling_bound=False` is also truthful. The blend test unconditionally proves
`dvs_engine == "blend"`; it is no longer vacuous. Requested pins match:

- `pvo_assembler.py`: `8baf25c73f014af2ed…`
- `test_dvs_clamp_connected_red.py`: `6b2a77ec6ba67de1fe…`

## Finding F3 — both Engine A assembler consumers can regress undetected

An in-memory mutation replaced both occurrences of

```python
dvs_clamped_val = engine_a_result.get("dvs_clamped")
```

with the original defective inference:

```python
dvs_clamped_val = engine_a_result["dynasty_value_score"] >= 100.0
```

All **14 clamp contracts still passed**. The new tests separately exercise an
Engine A scorer, Engine B assembly, blend assembly, and batch copying, but no test
passes Engine A producer truth through either assembler consumer. The batch test's
docstring says "what the assembler decided," yet its PVO is hand-authored and the
assembler is never called.

Required: connected assertions that drive controlled Engine A raw values through
`assemble_pvo` and `build_universe_pvo_batch`, including the normal Engine A path
and the `games_t == 0` dead-window Engine A fallback. At minimum the
below-100-but-rounds-to-100 case must reach the serialized row as `False`; an
above-100 control must reach it as `True`.

## Finding F4 — V3 can be hard-coded false undetected

A second in-memory mutation changed only `EngineAV3Scorer` to
`dvs_clamped = False`. All **14 clamp contracts still passed**. Its sole V3 test is
a false case, so it proves that 99.99589 is not clamped but does not prove that the
V3 head can ever report a real truncation. A `>= 100` boundary regression would
also survive because V3 exact-100 is not covered.

Required: V3 exact-100 and above-100 controls (preferably parameterized with the
existing below-100 case), with `False` and `True` respectively.

Both mutations were compiled and executed in memory; no working-tree source was
edited. The repository contains zero `MUTATION PROBE` residue.

## Checks independently run

- Unmodified clamp suite: **14 passed**.
- Adjacent Surface 3 / market-divergence bundle: **33 passed**.
- Mutation: both Engine A assembler consumers reverted — **14 passed**
  (finding reproduced).
- Mutation: V3 clamp truth forced permanently false — **14 passed**
  (finding reproduced).
- Ruff on all changed production/test paths: **pass**.
- `git diff --check`: **pass**.

Round-1 fixture/API-boundary dispositions remain unchanged. Nothing was committed
or pushed. No implementation, generated frontend contract, product artifact,
store, scheduler, or parked path was changed by this review.
