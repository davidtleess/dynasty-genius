# Footballguys Phase A RED v21

**RED pin:** `tests/contract/test_footballguys_phase_a_red.py`  
**SHA-256:** `528afecded652b5ad06070c1dd73ae46813f7da444f4aa3b1ee1447f7000dec6`  
**Size:** 6,604 lines / 254,583 bytes  
**Baseline GREEN:** `6fbac8af65c5f0c2eba92688a4ee7c600e0949b644262fc304a166076e2d14ca`

## Strict census

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -W error -m pytest -q \
  tests/contract/test_footballguys_phase_a_red.py --tb=no
```

Result: **602 collected = 24 failed + 578 passed, exit 1**.

- All 575 inherited v20 contracts pass.
- V21 slice: **24 failed + 3 passed**.
- RED and GREEN hashes were identical before and after the run.
- Ruff clean; strict Python 3.14 compile clean; zero skip/xfail/skipif.

## V21 controls

- Four acquisition load mutants: NULL offering and bootstrap-marker impostor across
  receipts/observations must render literal integrity-failure state. Exact markers
  remain `no_record` in two positive anchors.
- Ten current sequence-state mutants and four legacy sequence-state mutants bind
  type/domain/cardinality/name/max-order validation and byte-frozen refusal.
- Two future-version mutants bind read-only refusal of `user_version=999` in both
  stores.
- Four invalid explicit-now mutants bind literal row-9 fail-closed behavior before
  state branching; one aware-time positive keeps ordinary no-record behavior.

No production code, runtime store, commit, push, capture, provider, scheduler, or
downstream phase was changed/opened by RED authorship.

H2 QB rushing remains **UNDER TEST** with no result and is unrelated.
