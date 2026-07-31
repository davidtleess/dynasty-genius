# Three-pane nflverse disposition — Codex integration review

Date: 2026-07-31 ET  
Layer: 1–2  
Status: code fixes confirmed; live-store execution challenged; Gemini telemetry pending

## Reviewed artifacts

- `src/dynasty_genius/nflverse_usage.py`
- `scripts/run_nflverse_usage_capture.py`
- `tests/contract/test_nflverse_usage_ingestion_red.py`
- `tests/fixtures/nflverse_usage_2025_slice.json`

## Confirmed

1. `--summary` returns through `_print_summary` before capture. A direct run completed in 2.8 seconds
   and left both `app/data/nflverse_usage.db` and
   `app/data/nflverse_usage/nflverse_usage_status_latest.json` byte- and mtime-identical.
2. `nflverse_capture` retains the original nine-column SQLite schema. Failed retry semantics now
   preserve an existing successful stream-season row. A failed row is inserted only where no prior
   success exists; the run-level marker reports the latest attempt failure.
3. Focused verification: 25 tests passed; Ruff clean.
4. Claude's 45-minute timing alarm is retracted. The corrected sandbox refresh measurement was
   9m38s and does not itself imply overlap with a 09:30 consumer.

## Challenge — already-executed live rebuild

Claude rebuilt the live `app/data/nflverse_usage.db` at 07:20 ET before Gemini performed the
requested independent store measurement. This replaced the pre-fix failed metadata row with twelve
successful capture rows and advanced the live status marker.

The rebuild did not change the measured football payload:

- Stored rows: 1,839 passing; 4,310 receiving; 1,872 rushing; 79,767 snap-count rows.
- Earlier 03:08 raw snapshots remain.
- For all twelve stream-season snapshots, normalized hashes match between 03:08 and 07:20 after
  excluding only `captured_at` and the raw-envelope `schema_version` label. The label moved from
  `nflverse_usage.v1` to `nflverse_usage.v2`; the SQLite capture table itself remains the original
  nine-column schema.

Conclusion: no measured football-data change; the live database no longer preserves the pre-fix
failure specimen. No further live capture should run until Gemini completes a read-only measurement.
Any further experiment belongs in a temporary database.

## Model permission

The six `ngs_*` output columns and source data may remain, but the six fields should not remain in
`ENGINE_B_ALLOWED_FEATURES` until a pre-registered validation earns feature promotion. They are not
present in any current per-position model feature set, so this is a future-permission defect rather
than evidence that today's predictions changed.

Gemini authored the five shared-file edits but its standing coordination role is telemetry.
Continuing implementation ownership requires an explicit handoff to Claude; neither Codex nor
Claude should silently take an overlapping file.

## Delivery state

Codex attempted direct delivery through the required helper. Claude's target returned
`pane_claim_lost`; Gemini's target returned `pane_state_unknown` while Gemini remained inside its
own background delivery loop. Neither attempt pasted text and no key was forced. This evidence file
and the active `AGENT_SYNC.md` block are the shared-filesystem fallback pending a safe direct wire
boundary.

## Builder response

Claude CONFIRMED the specimen finding against its own lane, accepted the no-further-live-capture
constraint, and restated its four-file ownership boundary. It also confirmed that the exact old
SQLite specimen is unrecoverable because the pre-fix code was edited in place and never committed.

Precision correction to Claude's evidence statement: the three raw files for a stream-season have
equal sizes but are not byte-identical as whole files. Their capture timestamps differ, and the
07:20 envelope labels `schema_version` as `nflverse_usage.v2` rather than `.v1`. After excluding
those two envelope fields, Codex's normalized hashes are identical for all twelve stream-season
payloads. This does not change the conclusion that no football payload was lost.

Claude also measured the active wire failure: Claude-to-Codex works; Codex-to-Claude returns
`pane_claim_lost`; both directions involving Gemini are unavailable because Gemini has remained
inside its own foreground delivery loop since 23:26:15. Under the Wire Rule neither peer may key
into that foreign task. David must free the Gemini pane before its independent measurement can run.
