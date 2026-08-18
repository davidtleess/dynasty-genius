# DVS clamp-disclosure GREEN re-review — Codex v4

Date: 2026-08-18  
Thread: `w#dvs-disclosure-1`  
Verdict: **NOT CLEAR — named mutations caught; true propagation remains unguarded**

## Closed from v3

All three named Round-3 mutations are now caught by the intended assertions:

- Primary Engine A assembler consumer restored to rounded-score inference: two
  connected assertions fail.
- Dead-window consumer restored to rounded-score inference: its path-witnessed
  assertion fails.
- V3 producer hardcoded false: the above-100 assertion fails.

The V3 exact-100 boundary also kills a `>` to `>=` mutation. Additional hostile
checks confirmed the V2 boundary, Engine B exact-P90 boundary (via the existing
Phase-14 contract), and serializer true pass-through are mutation-sensitive.

Reviewer instrumentation disclosure: the first in-memory replay of the two
assembler mutations registered the replacement module in `sys.modules` but did
not attach it to its parent package. The tests failed during monkeypatch target
resolution, which is not valid mutation evidence. The harness was corrected and
both mutations rerun; the failures then came from the intended value assertions
with the expected 2-test / 1-test split above.

## Finding F5 — either Engine A consumer can discard true producer evidence

The added Engine A assembler and dead-window tests inject only
`score=100.0, clamped=False`. They prove that the consumers do not re-infer a false
positive, but do not prove that either consumer preserves `True`.

Independent in-memory mutations:

```python
# primary consumer only
dvs_clamped_val = False

# dead-window consumer only
dvs_clamped_val = False
```

Each mutation independently left the entire clamp bundle at **19 passed**. Thus
either seam can silently discard genuine truncation while all declared contracts
stay green.

Required before CLEAR: parameterize or add positive controls for both Engine A
consumer sites. Stub Engine A with `score=100.0, clamped=True`; the normal
Engine-A path and `games_t == 0` fallback must each produce
`dvs_clamped=True` and `xvar_ceiling_bound=True`. At least one should continue
through `build_universe_pvo_batch` and assert the serialized true value. Re-run
the two hardcoded-false mutations independently; each must fail for its own path.

## Checks independently run

- Unmodified clamp suite: **19 passed**.
- Adjacent Surface 3 / market-divergence bundle: **33 passed**.
- Three Round-3 named mutations: independently reproduced as caught by the
  intended assertions after harness correction.
- V2 `>`→`>=`, V3 `>`→`>=`, Engine B `>`→`>=`, and serializer forced-false
  mutations: each caught by a relevant contract.
- Primary Engine A consumer forced false: **19 passed** (finding).
- Dead-window Engine A consumer forced false: **19 passed** (finding).
- Ruff on all changed production/test paths: **pass**.
- `git diff --check`: **pass**.
- Pins exact: connected test `4b6f847c…`, assembler `8baf25c7…`, Engine A
  `77a48c51…`; zero mutation residue in repository source.

Round-1 fixture/API-boundary dispositions remain unchanged. Nothing was committed
or pushed. No implementation, generated frontend contract, product artifact,
store, scheduler, or parked path was changed by this review.
