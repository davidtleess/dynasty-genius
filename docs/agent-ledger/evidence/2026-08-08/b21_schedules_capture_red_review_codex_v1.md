# B21 schedules capture RED review — Codex v1

Date: 2026-08-08
Layer: Layer 1 canonical capture and provenance
Verdict: **NOT CLEAR**

Reviewed artifact:

- `tests/contract/test_b21_schedules_capture_red.py`
- SHA-256: `59e945097800ff5fb6c2a08d28585c0d19a449a758b095bfea69be1ff672b93c`
- Independent run: 23 failed, 0 passed, 0 skipped, zero collection errors; every failure is at
  the missing-module boundary.
- Independent Ruff: clean.

## Blocking findings

1. **“Raw before parse” is not exercised.** `capture()` receives `rows`, so the caller has already
   parsed the provider payload. Serializing those dictionaries cannot prove retention of upstream
   bytes or that raw was written before interpretation. No dedicated production entrypoint/fetch
   boundary is tested either. The RED must drive raw bytes through an injected parser, or drive a
   dedicated runner that writes exact transport bytes before parsing and hands the resulting raw
   reference to the store. A parser failure must preserve those exact bytes and hash—not merely any
   `.json` or `.raw` file.

2. **The independent-expectation rule contradicts its counter-test.** E1b captures one all-final
   slate and immediately requires finality. E3 tests zero captures, not one first capture. Therefore
   a GREEN can still certify finality from the same first observation it judges. Seed a prior
   scheduled baseline, then a later all-final observation; separately require a single first
   all-final observation to remain undetermined. Several fixtures also report final scores on
   2026-09-08 for games dated 2026-09-13, so the RED currently licenses evidence from before kickoff.

3. **Expected count is insufficient; expected membership is the invariant.** Two 16-game lists can
   contain different game IDs. Freeze the expected `(season, game_type, week, game_id)` set from the
   accepted schedule baseline and compare later observations by missing and unexpected IDs. A same-
   count substitution must fail finality. Membership changes require an explicit reviewed revision,
   not automatic replacement of the baseline.

4. **No-change capture collapses two identities.** V2 correctly avoids a second content vintage,
   but does not require a second successful observation/check record or marker advancement. Without
   that, a scheduled unchanged check cannot prove the route ran and the controller's acquisition
   freshness remains old. Pin separate content-vintage and capture-attempt identities: unchanged
   content keeps the vintage ID, while the successful check records its later `observed_at` and the
   ready/status surface reports `content_changed=false` without inventing a new vintage.

5. **Atomic publication is not tested under failure.** “No temp file after success” is not atomicity.
   Inject failures after raw persistence, normalized-store commit, manifest creation and ready-marker
   promotion. Every case must leave the previous ready marker byte-identical, expose no readable
   partial vintage, retain the raw object as explicitly unindexed evidence, and report cleanup
   failure loudly.

6. **The REG and NCAA guards are proxies, not behavioral protections.** C1 searches for `PRE` inside
   completion timestamp strings, so it passes regardless of whether a preseason row affected the
   result. Use a full-final REG slate plus a non-final PRE row and still require one REG completion;
   use an incomplete REG slate plus final PRE and require none. C5 merely checks that the returned
   dictionary does not spell `ncaa`. The shipped cadence engine ignores that tag and, absent an FBS
   availability fact, applies the one global `game_week_completions` list to NCAA streams. The later
   governed-input/controller contract must use league-scoped events and prove NCAA remains
   undetermined; the current string assertion cannot claim that guarantee.

7. **Derived-anchor provenance is decorative.** C4 requires only a nonempty `derivation` string on
   the aggregate. Each derived fact must bind to the exact B21 vintage ID, raw/content hash,
   derivation version, league and game-type filter so it can actually be re-derived. The Realized
   Outcome projection likewise needs the selected vintage ID and observation time.

8. **Route separation and evidence validation are incomplete.** S1 is a substring check over table
   names and can miss a daily spec named `games`; no dedicated CLI is required. Pin the exact B21
   spec/route identity, the dedicated script and injected fetch boundary, and absence from the daily
   default by exact key. At the capture boundary reject season mismatch, duplicate game IDs,
   malformed/naive observation and kickoff times, invalid game type/week, one-sided scores,
   score/result disagreement and final evidence observed before kickoff. Add valid counter-cases so
   the validator cannot pass by refusing everything.

## Required RED shape

Use three identities explicitly:

- **raw offering/check** — exact bytes, retrieval/observation provenance and status;
- **content vintage** — canonical semantic schedule content, immutable and deduplicated; and
- **expected schedule baseline** — frozen game membership used to judge later finality.

Then prove a dedicated runner performs raw-first capture, atomic publication and no-change check
accounting; prove finality only against an earlier accepted membership baseline; and prove the two
consumer projections retain exact vintage provenance without yet rewiring either consumer.

No GREEN, live capture, provider access, scheduler action, production artifact write, consumer
rewiring, commit or push occurred during this review.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result and is unrelated.
