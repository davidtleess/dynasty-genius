## CH1 per-stream isolation — Codex GREEN CLEAR v3

### Reviewed pins

- `scripts/run_feature_refresh.py`:
  `ce9caf74c2482d3950281da250f2aa7056189a7aa8be65e724fe09d95cfba5cc`
- `src/dynasty_genius/features/feature_refresh_runner.py`:
  `019229c2c47d9c1daa9c9c18876c0a76e0891093d47d8356bbd7c777f18751d0`
- Codex RED-v2:
  `a14261e52c3d0cc17e291b8da205771f20dd6fe9f8322585b6a9d55667e33fd4`

### Independent checks

- Branch/base: `fix/ch1-per-stream-season-isolation` at base `4bee0bebb226d1a83be5f09bf3dfb4b4fc8d05b9`.
- All pins matched; parked wire hashes remained `b3247ec8...` / `fd924eb1...`.
- RED-v2: **10 passed**.
- Focused runner/scheduler/isolation/feature-assembly slice: **41 passed**.
- Ruff on both production files plus RED-v2: clean.
- `git diff --check`: clean.
- Code inspection confirmed returned-data-derived effective seasons, `None` for loaded-empty,
  actual-attempt fallback accounting, preserved triggering error on successful fallback, and
  controlled refusal for any stream still unavailable after bounded attempts.
- A direct production-assembler probe replaced each of the five inputs in turn with a
  schema-correct empty frame. All five paths completed without an uncaught exception
  (`player_stats` produced zero rows; the other four produced the fixture's four rows), proving
  `loaded_empty` reaches normal downstream handling rather than passing only through a fake runner.
- The dynamic no-`--season-end` control proves player-stats can fall back to 2025 while healthy
  roster/PBP provenance remains at 2026.
- NGS remains on the last-good local-export route.

Claude's full-suite count was not independently rerun by Codex and is not used as independent
evidence for this CLEAR.

### Verdict and boundary

**GREEN CLEAR** for the pinned CH1 code and RED-v2 content.

This CLEAR covers only the authorized containment behavior. It does not authorize commit, push,
capture, store, scheduler/plist, consumer migration, Option A work, or Layer 2. GitHub Actions still
provides no verdict during the outage; local green is not represented as CI. H2 QB rushing remains
UNDER TEST with no result.
