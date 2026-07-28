From Codex (independent reviewer) - DG2-S0-01 (a)-(c) review: NOT CLEAR

Artifacts reviewed, uncommitted:

- `src/dynasty_genius/market_divergence_rebase.py`
  `e029a41ffc1c81ea2c9e61664dfd7d613584e237fb33e3c93c2791472342a73d`
- `tests/contract/test_market_divergence_rebase_red.py`
  `732877eedced736e4399cefb03db13a7c59f12c3aeab109e8272baa010166e9a`

**(b) NOT CLEAR to proceed to (d)-(g) on this exact test set.** The implementation
repairs reviewed under (a) and (c) are correct, but two contract defects preserve the
same class of false confidence this pass is meant to remove.

## What independently passes

1. Root-only `sleeper_player_id` is the correct identity contract. Both the committed PVO
   seed and the local runtime PVO carry it at the root on every row and carry no nested
   `player.sleeper_id`. Accepting both locations would make the fabricated fixture shape
   valid again; reject it.
2. The 2026-07-26 `fc_native` local snapshot has 475 rows. Independent replay against the
   local runtime PVO reproduces the stated common cohort and the exact 131 band crossings,
   2 outside-band direction reversals, and 133 union. The two named reversal rows reproduce.
3. `_is_band_crossing` and `_is_direction_reversal` are mutually exclusive and exhaustive
   over finite three-way classification changes, not over unchanged pairs. I checked
   100,196 exact-edge/random finite pairs against `_classify`; zero overlaps and zero
   missed classification changes. Exact `-0.100` is outside the band, so
   `+0.157 -> -0.100` is a direction reversal and not a band crossing.
4. Focused suite: **21/21 PASS**. Broader market-divergence slice: **116 PASS, 2 SKIP**.
   Ruff: **PASS**.

## Reproduced contract defects

1. **Artifact guard skips unnecessarily in CI/fresh clones.**
   `test_the_live_pvo_artifact_is_indexable_by_this_module` points only at the gitignored
   runtime artifact and calls `pytest.skip` when it is absent. I injected an absent
   repo-relative runtime path without moving any file; the test skipped exactly as CI
   would. Meanwhile the committed production fallback
   `app/data/valuation/universe_pvo_latest.json` exists and is indexable.

   This leaves CI's identity defense resting only on fixtures the implementation lane can
   edit alongside the code—the original failure class. Required correction: add a
   mandatory, non-skipping committed-seed test. The runtime-artifact check may remain as
   a second optional host-bound row, preferably reached through the verified
   `resolve_pvo_source` contract rather than bare file existence. Call it a **local runtime
   artifact**, not live/current Sleeper state.

2. **The report-level metric-split row is vacuous.**
   `test_the_report_names_both_counts_and_their_union` produces:
   `band_crossing_count=0`, `direction_reversal_count=0`,
   `classification_change_count=0`. Therefore its key assertion is only `0 == 0 + 0`.
   The predicate unit rows are good, but no committed row proves a nonzero direction
   reversal reaches the row flags and report counters correctly.

   Required correction: a report-level fixture with at least one nonzero band crossing
   and at least one nonzero direction reversal; assert the exact row flags, exact two
   component counts, exact union, and mutual exclusivity. A six-common-player fixture with
   four model-only and four market-only rows readily yields 2 crossings, 1 reversal, and
   union 3, so this is testable without a gitignored artifact.

The remaining synthetic unit rows are appropriate once their input shape is production-
faithful; the issue is not that unit fixtures exist, but that the only end-to-end metric
split currently exercises no split.

PLEASE REPLY with: (a) ACCEPTED and re-frozen hashes after both contract repairs, OR
(b) DISPUTED with the exact production/contract evidence.
