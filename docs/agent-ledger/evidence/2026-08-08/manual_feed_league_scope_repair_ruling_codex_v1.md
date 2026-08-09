# Manual-feed league-scoped event repair ruling — Codex v1

Date: 2026-08-08
Layer: Layer 1 ingestion control
Verdict: **OWN BOUNDED REPAIR, BEFORE B21/GOVERNED INPUT**

The reproduced defect is latent because the governed input is absent, but it is independent landed
consumer behavior. It must be repaired in `feed_cadence`/`daily_control` under its own RED and GREEN,
not compensated for inside the future artifact generator.

## Scope of the defect

The class is broader than `game_week_completions`:

- `_last_event` reads one global completion list for every weekly policy;
- `season_final` reads one global `final_game`; and
- `_in_active_window` reads one global `week1_kickoff` and `final_game`.

Thus NCAA PFF lanes can inherit NFL weekly events, season-final events and active-window boundaries.
Tagging a derived artifact `league=nfl` does nothing because the shipped engine does not consult the
tag.

## Required RED contract

1. Add an explicit closed competition/event scope to every game-calendar policy. Pin the total map:
   PlayerProfiler weekly streams and NFL PFF lanes use `nfl`; NCAA PFF lanes use `fbs`; a game-
   triggered policy may never be unscoped.
2. Replace flat game calendar facts with competition-scoped facts. Scope `week1_kickoff`,
   `final_game` and `game_week_completions` together. Do not retain a flat fallback.
3. Behavioral isolation:
   - an NFL completion can make NFL/PlayerProfiler lanes due but cannot affect NCAA;
   - an FBS completion can make NCAA due but cannot affect NFL/PlayerProfiler;
   - NFL/FBS season-final and active-window boundaries are independently isolated;
   - missing facts for one competition yield `undetermined` for that scope, never borrowed facts.
4. The controller validator rejects the legacy flat representation, unknown competition keys,
   malformed scoped containers and timestamps; full controller failure remains isolated and
   fail-closed.
5. Resolve `pff.grades` explicitly. It currently carries weekly triggers without a league identity.
   Split it by competition, bind it to measured lanes, or leave it undetermined; do not silently
   assign one competition or let it borrow both calendars.
6. Mutation-prove that removing the scope selection causes the cross-competition isolation tests to
   fail. Include valid two-competition and missing-one-competition counter-cases.

## Sequence

1. League-scoped-event RED/GREEN and landed CI.
2. Rewrite and review the B21 RED against the corrected NFL-scoped consumer contract.
3. B21 GREEN/private acceptance.
4. Repaired governed-input RED and actual artifact; FBS remains undetermined until governed FBS
   evidence exists.

No production input exists today, so this is not an active data incident. No provider access,
capture, scheduler, production artifact, code edit, commit or push occurred in this ruling.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result and is unrelated.
