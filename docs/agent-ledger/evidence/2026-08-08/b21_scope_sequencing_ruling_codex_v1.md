# B21 schedules scope and sequencing ruling — Codex v1

Date: 2026-08-08
Layer: Layer 1 ingestion and provenance
Verdict: **CONCUR WITH B21, WITH REQUIRED SCOPE CORRECTIONS**

## Ruling

Capture B21 once as the canonical upstream schedules dataset and design that capture to serve both
cadence and Realized Outcome. Do not build a cadence-only copy and leave Realized Outcome on a second
live provider read. Consumer activation remains separately gated: the B21 slice establishes the
source-of-truth capture and read adapters; each consumer migrates only after its own parity/finality
contract passes.

## Required correction to the proposed implementation shape

`identity_applicable=False` handles the absence of player identity, but does not solve schedules'
temporal semantics. The current generic store offers:

- `seasonal`: `apply_season` deletes and replaces the current season's normalized rows; and
- `snapshot`: the default fetch invokes the loader with no season argument and the spec cannot
  declare seasonal loader arguments.

Schedules are a third shape: season-bounded **and revision-bearing**. Kickoffs can flex, games can
move, and scores/finality appear later. Both cadence and Realized Outcome need to know which schedule
vintage supported a decision. Therefore the B21 RED must either add an explicitly versioned-seasonal
axis or use a dedicated schedules store/entrypoint. It must not silently route B21 through today's
replacement-only seasonal path, and it must not add B21 to the existing all-stream daily default.

## B21 capture contract (consumer-neutral superset)

1. Raw payload before parsing, exact bytes/hash, source dataset, retrieval time, parser/schema
   version and immutable capture ID.
2. Game-grain normalized records with no player identity. Preserve at minimum the fields required
   by both views: game ID, season, game type, week, game date/time, teams, both scores/result and
   identifiers. Raw retention remains the schema-drift escape hatch.
3. Retain every distinct accepted schedule vintage; identical re-fetch is a no-change observation,
   while a changed kickoff/status/score produces a new vintage. Never rewrite the old vintage.
4. Fail closed on duplicate game IDs, malformed season/week, naive/unparseable kickoff facts and
   schema drift. A partial batch cannot advance the ready marker.
5. A dedicated B21 ready marker is the consumer commit point. It identifies the exact capture and
   content hash. The existing nflverse usage ready manifest must not accidentally become B21's
   provenance surface.
6. Dedicated callable entrypoint, no self-install and no scheduler change in this slice. The
   cadence selected later must not be inherited accidentally from the existing daily multi-stream
   runner.

## Consumer views from the one capture

### Manual-feed cadence

Derive NFL regular-season facts only under an explicit `game_type == REG` rule: season, Week 1
kickoff, regular-season final game, prior-season final game and per-week completion observations.
`game_week_complete` should be the first accepted capture at which the complete expected week is
observed final—not arithmetic from kickoff. Every derived fact carries the B21 capture ID/hash and
derivation version.

### Realized Outcome

Replace the direct `nflreadpy.load_schedules` read with an adapter over a pinned B21 ready vintage.
Its view must produce season/week, game ID, gameday, finality and an expected game count. The expected
count cannot be derived from the same filtered list it is checking, or a missing source row certifies
itself as complete. Finality must require complete score/result evidence for every expected game;
the existing consumer contract then remains fail closed.

## Two limits that must remain explicit

1. B21 is NFL schedules. It does not provide FBS game-week completion facts for the seven NCAA PFF
   lanes. Those lanes still need governed FBS event/availability evidence or must remain
   `undetermined`; B21 must not be presented as completing the whole cadence calendar.
2. The previously routed governed-input RED does not survive unchanged. It currently permits an
   all-declared calendar and manually flattens a provenance-rich object before invoking the
   controller validator. It must pin B21 origins for the five NFL game facts, declared origins for
   the three league-calendar facts, and the real persisted loader path.

## Sequence

1. Repair and CLEAR a B21 canonical-capture RED with the superset contract above.
2. GREEN B21 capture and verify a private/live acceptance without migrating either consumer.
3. Repair the governed-input RED, then generate and atomically land the provenance-bearing input;
   derive its NFL game facts from the pinned B21 vintage and declare the three non-game anchors.
4. Migrate Realized Outcome from the live loader in a separate parity/finality slice.
5. Decide and authorize the B21 scheduler only after measured source-change behavior and both
   consumer deadlines are represented; one capture cadence may serve both consumers.

No capture, provider contact, scheduler action, production artifact write, code edit, commit or push
occurred during this ruling.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result and is unrelated.
