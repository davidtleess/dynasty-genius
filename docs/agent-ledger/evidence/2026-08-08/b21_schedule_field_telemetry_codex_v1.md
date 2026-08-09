# B21 nflverse schedule field telemetry — Codex — 2026-08-08

## Scope

Layer: Layer 1 ingestion. Read-only inspection of installed `nflreadpy`, shipped repository code and
official nflverse/nfldata documentation. No provider fetch, capture, scheduler mutation, paid call
or production edit.

## Measured facts

Installed `nflreadpy.load_schedules()` downloads the single `nflverse-data` asset
`schedules/games`, filters by season and returns the frame. It adds no status or completion field.
Its own docstring routes to the official schedule dictionary.

The official nfldata dictionary defines:

- `game_id`: NFL-assigned primary game identifier;
- `season`, `game_type`, `week`;
- `gameday` and `gametime`, where `gametime` is kickoff time in Eastern time;
- `away_score`, `home_score`, `result` and `total`, documented as missing before an unplayed game;
- no actual game-end timestamp;
- no explicit scheduled/in-progress/final status field.

The official nflverse availability page says Game/Schedule data updates every five minutes during
the season. That cadence means a RED must not silently assume non-null scores are terminal unless a
separate authoritative provider contract proves the release writes scores only after finalization.
The dictionaries inspected do not provide that guarantee.

The current repository loader at `scripts/run_realized_outcome_scoring.py:342-360` creates its own
status as `final` whenever `home_score` is non-null. This is an inference made by our code, not a
field delivered by B21. It also sets `expected_game_count` to the length of that same fetched frame,
so a truncated observation self-certifies.

## RED consequence

B21 canonical capture can and should proceed: raw offerings, immutable content vintages, stable
game IDs and independently frozen expected membership are all valuable. But the RED must separate
capture from finality certification.

Without an authoritative terminal indicator, the honest states are at least:

- `scheduled`: result fields absent;
- `result_observed_unverified`: result fields present but terminal semantics not independently
  established;
- `final`: only when a separately governed terminal fact proves completion.

`completion_observed_at` may be assigned only to the first accepted offering that contains that
separately proven final state for every expected game ID. Latest kickoff remains context/lower bound,
never completion time. No guessed duration or weekly arithmetic is allowed.

If Claude finds a primary source contract proving nflverse scores appear only after games are final,
that evidence can close the terminal gap and the RED can use the first accepted scored vintage.
Absent such evidence, B21 capture lands first while the derived completion anchor remains
`undetermined` rather than manufacturing finality.

## Gemini telemetry comparison

Gemini independently confirmed the missing explicit status and missing game-end timestamp, and
reported that live games can carry interim non-null scores. It then proposed that non-null scores
plus `gameday < current_date` or a Tuesday post-MNF check prove finality. That proposal is **not
accepted**: neither condition is a source terminal fact. A game can cross a calendar boundary, be
postponed or remain unresolved, and a Tuesday clock is the same kind of arithmetic proxy the
competition-scoped cadence repair removed. The terminal-evidence gap therefore remains real.

Gemini also described `game_id` as `{season}_{week}_{away}_{home}` and stable across ordinary time
flexes. The baseline should retain all available external identifiers as provenance and treat any
week/team/ID change as a revision or conflict, rather than assuming the composite can never change.

## Sources

- Installed `nflreadpy.load_schedules` source, inspected with `inspect.getsource`.
- `scripts/run_realized_outcome_scoring.py:339-364`.
- <https://nflreadr.nflverse.com/articles/dictionary_schedules.html>
- <https://github.com/nflverse/nfldata/blob/master/DATASETS.md#games>
- <https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html#nflverse-gameschedule-data>

H2 QB rushing remains a registered hypothesis UNDER TEST with no result and is unrelated.
