# DVS clamp-disclosure GREEN re-review — Codex v2

Date: 2026-08-18  
Thread: `w#dvs-disclosure-1`  
Verdict: **NOT CLEAR — Engine A fixed; blend disclosure remains semantically false**

## Closed from v1

The Engine A producer repair is correct. Both scorer heads now derive
`dvs_clamped` from `raw_score > 100.0` before rounding/clamping, and the assembler
consumes producer truth at both Engine A sites. The exact v1 counterexample now
returns `False`; raw exactly 100 returns `False`; raw above 100 returns `True`.

The file pins in the request match:

- `scoring/engine_a.py`: `77a48c513b2c515588…`
- `pvo_assembler.py`: `419a8b8c3b9a76207c…`
- `test_dvs_clamp_truth_red.py`: `7e2faf67c2a1205275…`

## Finding F2 — `dvs_clamped` changes meaning on blend rows

The public contract remains `PlayerValueObject.dvs_clamped: True if raw DVS
exceeded 100 before clamping`. The batch comment likewise says a true value means
the DVS is truncated. The new blend rule instead sets that field true when either
already-clamped input component was truncated, even though the blended DVS itself
was not.

Independent assembler-to-batch reproduction with Engine A clamped at 100 and
Engine B at 50:

```text
dvs_engine = blend
dvs_blend_weight_b = 0.444
dynasty_value_score = 77.8
dvs_clamped = true
xvar_ceiling_bound = true
```

The final 77.8 was never clamped. A consumer of the documented field therefore
receives a false claim. The same problem reaches `xvar_ceiling_bound`, whose
contract says DVS was clamped before xVAR. The single `dvs_p90_ref` also cannot
identify which blend input was truncated.

Preferred disposition:

1. Keep `dvs_clamped` about the shipped DVS. Under the current arithmetic the
   blend itself never clamps, so a blend row should not report `True` on this field
   (use `False`, or `None` only if the contract explicitly declares the field
   inapplicable to blends).
2. If component truncation must be retained, expose it through separately named
   blend provenance (ideally component-specific), rather than overloading
   `dvs_clamped`.

## Contract gap — the requested connected boundary remains untested

The new four tests exercise only `EngineAScorer.score`; they do not call
`assemble_pvo` or `build_universe_pvo_batch`, do not exercise `EngineAV3Scorer`,
and do not test blend semantics. The separate disclosure contracts still inject
hand-authored final booleans. Thus scorer, assembler, and serializer can diverge
again while both files remain green.

Before CLEAR, add connected scorer/controlled-raw → assembler → batch assertions
for Engine A below/exact/above 100, the V3 head, Engine B exact/above P90, and blend
cases with neither/A/B/both inputs truncated. The blend assertions must match the
chosen public semantics.

## Checks independently run

- New clamp-truth + disclosure bundle: **9 passed**.
- Broader scorer/assembler bundle (`phase14_dvs`, `phase15_xvar`, Engine A V3,
  clamp truth, disclosure): **50 passed**.
- Adjacent Surface 3 / market-divergence bundle: **33 passed**.
- Ruff on all changed production/test paths: **pass**.
- `git diff --check`: **pass**.
- Direct blend assembler→batch counterexample reproduced as stated above.

Round-1 dispositions remain unchanged: the Surface-3 fixture widening is
legitimate; the artifact-only split is acceptable only as a half-close, with the
API/frontend increment still separate. Nothing was committed or pushed. No
implementation, generated frontend contract, product artifact, store, scheduler,
or parked path was changed by this review.
