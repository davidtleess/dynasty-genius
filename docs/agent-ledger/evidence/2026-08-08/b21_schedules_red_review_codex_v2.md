# B21 schedules RED review — Codex v2

Date: 2026-08-08
Layer: Layer 1 ingestion
Reviewed artifact: `tests/contract/test_b21_schedules_capture_red.py`
Reviewed SHA-256: `51067f0e85e9333921b2925069fdf1a7d8c800a2f90cc48f14a6780533db1b0e`

Verdict: **NOT CLEAR**.

Independent execution reproduced **26 failed / 1 disclosed pass**, true pytest exit 1, zero
collection errors. Ruff passed. The prior six finding classes were directionally addressed, but the
rewrite still models a different source boundary than the installed B21 route and expands the source
ticket into the next consumer-control ticket.

## Consolidated findings

1. **The offering unit and raw wire format are not B21.** The installed loader calls
   `downloader.download("nflverse-data", "schedules/games")`; its downloader resolves one global
   `schedules/games.parquet` release asset and parses Parquet bytes. The RED instead constructs one
   synthetic JSON array per `(season, week)` and calls it “source-authentic.” A GREEN can satisfy the
   entire suite without fetching, retaining, or parsing the provider artifact B21 actually publishes.
   Pin an injected fetcher to the exact nflverse schedules asset, raw Parquet bytes first, then a
   deterministic season/week projection linked to the one global raw content vintage.

2. **The route is not required to acquire anything.** D2 proves only that a descriptor names a `.py`
   file; S1 starts after arbitrary caller-supplied bytes already exist. No test proves URL/provider
   identity, one HTTP retrieval, response/error handling, source retrieval time, CLI exit state, or
   that the dedicated CLI uses the capture path. This repeats the adapter-without-data failure mode.
   The RED needs an injected transport contract plus a CLI test that runs the fetch→raw→parse→publish
   path. The ticket then closes only on the real 2026 capture already authorized by the current plan.

3. **The normalized schema can discard most of the source.** The authoritative nflverse dictionary
   currently declares **45 fields**. F1 requires only ten and the fixture contains only ten, so a
   parser may silently discard `result`, `total`, overtime, venue, weather, rest, and all provider ID
   fields while passing. The fixture also builds `game_id` as home/away, while nflverse defines it as
   `season_week_away_home`. Require lossless source-column preservation (plus schema hash and measured
   dtypes) and correct source-shaped identifiers. A consumer projection may select columns later;
   Layer 1 may not.

4. **The baseline/finality machinery belongs to the next consumer gate and its singleton freeze is
   wrong for revisions.** B21's source ticket should retain scores without emitting a terminal claim.
   C3–C7 build independently governed terminal-evidence evaluation now, while the supplied order puts
   governed cadence inputs and Realized Outcome migration after B21 capture. B4 also forbids every
   conflicting re-freeze forever, so a real reschedule or membership correction makes the baseline
   permanently stale. Keep this GREEN source-first: publish immutable raw/content vintages and an
   explicit `finality_capability=unverified`; move expected-membership selection and terminal joins to
   their separately reviewed consumer gates. If a baseline primitive remains here, baselines must be
   versioned and retained, never overwritten or globally singleton.

5. **External-data validation is missing.** Caller `season`/`week` are not reconciled to raw rows;
   malformed Parquet, empty payloads, duplicate/conflicting `game_id`s, wrong season/week/game type,
   invalid `observed_at`, schema drift, bad score types/non-finite values, and game-ID/team
   inconsistency are untested. The present contract can publish 2025 Week 2 rows under a 2026 Week 1
   path. Add fail-closed semantic checks with stable error codes and valid counterexamples.

6. **Failed-attempt and last-good behavior are under-specified.** E1 starts from an empty store and
   does not prove that a prior ready marker/vintage survives a later raw/parse/store/index/marker
   failure. It also does not require valid provider bytes that fail parsing/schema validation to be
   retained or quarantined with their hash. Pin: failed attempt audited; raw evidence retained when
   retrieval succeeded; no new accepted vintage; prior last-good marker byte-identical; no partial
   canonical/index files.

7. **No-change replay is not closed end to end.** A1 calls `record_offering` twice and checks only
   vintage count. It does not distinguish a new scheduled retrieval from replay of the same retained
   offering, exercise the CLI/publish path, or require `last_checked` to advance while
   `last_changed`/vintage stay fixed. Pin both cases so monitoring does not lose successful no-change
   checks and replay cannot duplicate check/vintage identities.

8. **Canonical layout, provenance, and protection are not pinned.** S2 accepts any descendant of an
   arbitrary root; the marker omits provider URL, byte count, schema hash and parser version; no test
   rejects path traversal or binds the canonical location. The first retained raw vintage is
   irreplaceable point-in-time evidence, so the same change must add its store to
   `app/config/backup_manifest.json` under the standing manifest-coverage law. Pin exact safe layout,
   complete marker/ledger metadata, backup coverage, and clean-tree behavior.

9. **The authority preamble is stale.** It says the real source call is not authorized and
   David-gated. The current task explicitly requires the first real 2026 capture, CFBD access is
   already configured/paid, and David's recorded all-ingestion word authorizes consumption once the
   route/cadence/access are determined. Keep scheduler installation and downstream use separate, but
   do not leave a false capture gate in the RED.

## Falsification matrix

| Input class | Current coverage | Result |
| :-- | :-- | :-- |
| valid nominal | synthetic JSON only | **OPEN** — not the provider Parquet/global offering |
| missing / wrong-type raw | parsed list rejected | partial; missing/null not pinned |
| malformed contents / schema drift | none | **OPEN** |
| duplicate / conflict | equal-count membership substitution only | **OPEN** at raw row/check identity |
| empty collection | none | **OPEN** |
| cross-component shape | generic-stream exclusion only | **OPEN** for fetcher/CLI/marker and later consumers |
| numeric/time edge | none | **OPEN** |
| synthetic / override | storage fault collaborator | partial; no transport collaborator |
| filesystem atomicity | four injected publish boundaries | partial; no pre-existing last-good or retained invalid raw |
| replay / no-change | direct store calls | **OPEN** end to end |
| path/provenance safety | descendant-only assertion | **OPEN** |

## Evidence checked

- `.venv/lib/python3.14/site-packages/nflreadpy/load_schedules.py:30`
- `.venv/lib/python3.14/site-packages/nflreadpy/downloader.py:18,38-71,101-121`
- `docs/layer-1-data-inventory-catalog.md` B21 rows and §4.4 cadence row
- `scripts/run_realized_outcome_scoring.py:342-364`
- nflverse primary schedule dictionary:
  <https://nflreadr.nflverse.com/articles/dictionary_schedules.html>
- nflverse primary update schedule:
  <https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html#nflverse-gameschedule-data>

## Accept condition for the next RED

Return one revised pin that fixes all nine classes in one pass. The RED should stay bounded to the
source ticket, use a real Parquet/global-offering transport model, require the executable route, and
leave terminal-baseline selection to the separately sequenced governed-input/Realized Outcome gates.
GREEN is not open until this RED is independently CLEAR.
