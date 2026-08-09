# League-scoped events GREEN review — Codex v2

**Date:** 2026-08-08 21:19 ET  
**Layer:** Layer 1 ingestion control  
**Verdict:** **NOT CLEAR — two residual contract defects**

## Reviewed pins

- `src/dynasty_genius/sources/feed_cadence.py`
  `59411b3686c7abc6a38d929cef8f8f84c13db30ff6e95930bbaaeb29937dfb44`
- `src/dynasty_genius/sources/daily_control.py`
  `868b675885333170f4ab7f19334d7facffb4f5621e0119ffec48844d434e0ca5`
- `tests/contract/test_league_scoped_events_red.py`
  `7b0536169dbdb013713a3a01e85e92c262f413c8bbea069ee793c8db811f3067`
- `tests/contract/test_manual_feed_cadence_red.py`
  `ff2adf8f81e2ab508bef4c992e79c35fcdc04ba183d55a7eaf15b852f7f2592b`
- `tests/contract/test_layer1_daily_control_red.py`
  `4961677233cb3740bdf952580fef2bd701314ad47c66662cae937f62c6241074`

All pins independently matched. The three contract files passed `175/175`; Ruff on the three
touched paths and `git diff --check` passed. Direct reproduction confirmed the repaired
`player_season` result is `due/draft_complete`; the removed phantom now authorizes and retains
nothing; a real PFF lane remains fully authorized. The grade regression now pins its intended
`ValueError` and diagnostic.

## Residual findings

### F1 — only half of the false declaration annotation was repaired

The function return annotation changed to `list[tuple[Any, ...]]`, but its actual accumulator still
declares:

```python
out: list[tuple[str, str, tuple[str, ...]]] = [
```

and immediately stores four-tuples in it. The local type contract is still false, and the v1 review
explicitly required one truthful declaration alias/union at **both** annotations. Replace both with
the same truthful type; do not leave the accumulator claiming three-tuples.

### F2 — P7 does not pin the undeclared-stream class it claims

The v1 repair condition required regression coverage for both `pff.grades` and an arbitrary unknown
key. P7 tests only `pff.grades`. A future implementation could special-case that historical phantom
and continue authorizing every other undeclared pair while P7/P7b and the reported hardcoded-True
mutation still characterize only the named case.

Add an arbitrary unknown `(source, stream)` counterexample and require all three permission fields
to remain false. The current implementation already passes this behavior; the missing work is the
contract that proves authorization follows declaration generally.

## Ruling

**NOT CLEAR.** The substantive F1/F2 behavior from v1 and the narrowed grade-leakage assertion are
repaired. Correct the remaining accumulator annotation and add the arbitrary-unknown regression,
then return fresh pins and focused gates. No governed input, B21/CFBD capture, scheduler, paid call,
provider contact, commit or push is authorized by this review.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
