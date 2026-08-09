# Codex board and ticket report — 2026-08-08

## Scope and method

Layer: Layer 1 ingestion and its control plane.

This is Codex's independent reading of `AGENT_SYNC.md` from line 1 through the authoritative
`END CURRENT BOARD` marker at line 1215, plus the canonical Layer 1 catalog and shipped code at
`268def2ae13515ebbd36dfe332fd7c919621678d`. Text below the marker was not used as live state.
Within the live region, precedence is newest-first; a lower block's old `READ FIRST` label does not
override newer blocks above it.

## 1. Board as read

The highest live reconciliation is Session 8b: PFF has an operable manual intake/backfill route,
main was repaired, Layer 1 makes no selection among source observations, and RotoViz plus
Campus2Canton remain incomplete. Session 8 records the contracts capture and the daily controller.
The most recent code state goes beyond both blocks: the manual-feed cadence engine and
competition-scoped event isolation are now landed and exact-SHA CI-green at `268def2`.

The block beginning `CURRENT HANDOFF / EXECUTION BOARD ... READ FIRST` around line 711 is still
physically above the end marker, so it remains evidence in the live region, but its execution
instructions are stale. It says to begin with six free loaders and carries now-false states for
contracts, depth charts and later work. Newer blocks above it prove that work has already happened.
Its `READ FIRST` wording is therefore stale-but-shouting, not the current router.

Nothing below line 1215 is live unless a current block explicitly reopens it.

## 2. Where B21 is

B21 is nflverse `schedules`. The canonical catalog records it with no canonical store, zero rows,
no raw capture and no export; it is `future-live / uncaptured`. It is already read directly by the
loaded Realized Outcome job, although current runs gate before source access while prediction
snapshots are absent. The catalog says it must be canonical before the first prediction-bearing
run and classifies it as an `automatic_candidate`, not an installed job.

It is absent from `build_streams()` and should remain outside that generic daily stream set. A
schedule is season-bounded but revision-bearing: flexes, postponements and score corrections need
immutable vintages. The proper route is a dedicated versioned-seasonal entrypoint and marker.

B21 is not a ticket anywhere in the current `AGENT_SYNC.md` board. It is only a catalog row plus an
untracked RED file whose prior pin was withdrawn after review. There is no valid current B21 RED,
GREEN module, capture, store or scheduler.

The decided design uses three identities:

1. each raw offering/check;
2. each immutable content vintage;
3. an independently frozen expected-schedule baseline keyed by expected game IDs.

Counts alone are insufficient because an equal-count game substitution must be detected.

On the measured 21-stream cadence registry, B21 supplies the free NFL game facts needed by 10
streams: three PlayerProfiler game-driven streams and seven NFL PFF lanes. Seven FBS PFF lanes
remain honestly undetermined until dated FBS schedule evidence is enabled through the separately
cost-gated CFBD route. Four non-game-triggered streams do not depend on B21.

B21 also blocks migration of Realized Outcome away from a direct source read. The current loader in
`scripts/run_realized_outcome_scoring.py` sets `expected_game_count = len(games)` from the same
frame being judged. A partial frame therefore self-certifies. That is latent because the job gates
before access today, but it must be repaired before the first prediction-bearing run.

### Schedule-completion time

The nflverse schedule schema supplies `gameday` and `gametime` as kickoff facts, plus scores/result
after finalization; it does not supply a game-end timestamp. The honest derived event is therefore:

- finality: every independently expected game ID is present and has final result evidence in one
  accepted schedule vintage;
- `completion_observed_at`: the raw offering/check timestamp of the first accepted vintage proving
  that condition, bound to the content-vintage ID/hash and expected-baseline ID/hash;
- latest scheduled kickoff: retained only as a lower bound/context, never represented as the
  completion instant;
- actual game-end time: unavailable/unknown.

This is conservative but observable. It must not be replaced with kickoff plus a guessed duration
or recurring weekly arithmetic. Primary schema reference:
<https://nflreadr.nflverse.com/articles/dictionary_schedules.html>.

## 3. Open ticket list

### Immediate and sequenced

1. **Documentation evidence closeout — open now.** Commit `268def2` is code- and CI-green, but its
   committed ledger introduced 32 distinct evidence references absent from the committed tree.
   All files exist locally. A docs-only follow-up must land the 32 referenced artifacts, the
   post-push audit and ledger entries, with reference-resolution proof and exact-SHA CI.
2. **B21 canonical schedules capture — next implementation slice.** David approved capture-and-
   derive. Rewrite and review the RED under the three-identity model, then GREEN and private
   acceptance. No source run is authorized merely by writing the route.
3. **Governed cadence input — blocked on B21 for NFL game facts.** The earlier RED was withdrawn.
   The artifact must derive NFL kickoff/finality/completion facts from pinned B21 vintages and
   declare `league_year_open`, `draft_complete` and `combine_complete` with provenance. An absent
   FBS block is valid and yields undetermined, never invented evidence.
4. **Realized Outcome schedule migration/finality repair — after B21/governed facts.** Replace the
   direct live loader and self-certified count with a pinned B21 projection plus an independent
   expected game-ID baseline.
5. **Scheduler decision — after the routes and markers exist.** The two loose launchd plists remain
   untracked and uninstalled. Installation is David-gated.

### Other live Layer 1 work

6. **Contracts windowed capture — open, no valid RED yet.** David ruled full-payload retention in
   perpetuity, twice yearly near league-year/free-agency opening and pre-Week 1. It must leave the
   daily default, gain a dedicated windowed route/marker and retain both legacy vintages as
   `legacy_unassigned`. The first RED outline was not clear; no code is built.
7. **RotoViz and Campus2Canton manual routes — incomplete.** Neither has a first-drop inventory,
   importer/marker or evidentiary cadence. Their honest state is unknown/undetermined.
8. **CFBD dated FBS schedule evidence — David cost decision.** A `/games` capability exists, but
   current held cache material has no dated game rows. Until enabled and captured, seven FBS PFF
   lanes remain undetermined.
9. **PlayerProfiler medical coverage — inadequate.** Held medical history ends in 2023, leaving
   2024–2026 uncovered. Freshly re-ingesting the same archive cannot cure the coverage gap.
10. **PFF YPRR materialization — separate open consumer gap.** Intake is complete, but the active
    `yprr_college` materialization remains 0/874.
11. **Provider cadence questions — optional information, not a Layer 1 ingestion blocker.** The
    board still carries A–C and draft provider questions as open. Later team alignment established
    that observable event windows can govern ingestion without provider email; exact unobservable
    revisions cannot be guaranteed. The board should reconcile this conflict rather than silently
    treating email as required.
12. **QB-1 study — authorized backlog, not the next Layer 1 slice.** The study has not run. H2 QB
    rushing remains a registered hypothesis UNDER TEST with no result.

Lower-priority retention/cleanup decisions remain open, including historical export partials and
retained old source representations; none authorizes pruning.

## 4. What is actually next

The earlier sequence still holds. Step one, competition-scoped engine repair, is complete and
exact-SHA CI-green at `268def2`. The next technical sequence is:

1. close the dangling-evidence documentation defect so current history is self-contained;
2. B21 RED rewrite/review under the three-identity model;
3. B21 GREEN and private acceptance;
4. governed cadence-input RED/GREEN and actual artifact;
5. Realized Outcome migration/finality repair;
6. scheduler decision.

The docs repair should precede new code because it is a bounded closeout of the already-landed
slice, not a competing product build.

## 5. Stale or wrong board claims

- B21 and the approved capture route are missing from the live board.
- Session 8b's PFF `manual_due` based on a blanket seven-day age clock is stale. Until governed
  per-stream facts land, PFF and PlayerProfiler are honestly undetermined; age is informational.
- Session 8 says PFF has no importer; the PFF intake/indexer now exists.
- Session 8 carries contracts daily retention as an unresolved 17.7M-row/year question. David has
  settled the product decision: full payload, twice yearly, retained forever. The code ticket to
  implement that decision remains open.
- The old line-711 `READ FIRST` loader batch is superseded and dangerous as an execution router.
- Old full-suite counts are historical measurements, not current invariants.
- The board's provider-publication A–C blocker language conflicts with the later aligned ruling
  that provider email is not required to finish Layer 1 ingestion.
- The catalog's canonical B13 table still says contracts are absent/never run/zero rows while later
  rows and the newer board record two captured vintages. That internal contradiction needs repair.
- The board does not record the `268def2` scoped-engine landing, its terminal CI success, or the
  live 32-reference documentation defect.
- RotoViz/Campus2Canton are unknown/undetermined, not overdue; PlayerProfiler medical is inadequate,
  which is independent of ingest age.

## 6. Gemini Operations and Telemetry comparison

Gemini independently agrees on the material board facts: B21 appears zero times in the current
board; it is catalog-only, uncaptured and `automatic_candidate`; it now governs 10 of 21 cadence
streams in addition to Realized Outcome; the board's suite count is historical; and `268def2` is
missing from the board.

Its marker inventory is consistent with the shipped manifest: seven sources declare marker paths
and all seven files exist locally; the other thirteen sources declare no success marker. Embedded
timestamps, rather than mtimes, were reported.

One scheduler claim is wrong. Gemini reported ten tracked plists and zero untracked plists. Direct
Git measurement shows eight tracked plists and two additional untracked files:

- `ops/launchd/com.davidleess.dynasty-league-transaction-capture.plist`
- `ops/launchd/com.davidleess.dynasty-nflverse-usage-capture.plist`

The user's `~/Library/LaunchAgents` directory contains eight Dynasty plist files, matching the eight
tracked names. The current Codex shell's `launchctl list` returned zero matching labels, so this
audit does not independently endorse Gemini's stronger statement that eight jobs are presently
loaded. Installed plist presence and live loaded state must remain separate facts.

Gemini's pane is currently idle with an empty composer and no permission dialog, and it received
and answered the prompt. That retires the board's current-permission-dialog diagnosis. It does not
root-cause the carrier's earlier `pane_state_unknown` and `wire_body_mismatch` refusals; pane health
and delivery reliability are different claims.

No capture, scheduler, paid call, provider contact, source execution, code edit, commit or push was
performed for this report.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result and is unrelated.
