# CFBD FBS schedules RED v7 + GREEN v3 repair packet

Date: 2026-08-09  
Layer: 1 — source capture and retained provenance  
Implementation lane: Codex  
Review answered: `cfbd_fbs_schedules_green_review_codex_v1.md`

## Pins and gates

- RED: `tests/contract/test_cfbd_fbs_schedules_capture_red.py`, 1,601 lines,
  `26a61170336cd6e2bfa2bcc299e6243ea88c8ac017cd2972617f8e9700d80335`.
- Module: `src/dynasty_genius/sources/cfbd_schedules_capture.py`, 1,007 lines,
  `22aff76c0a1beb863390044470177dc540b1e705ffa79986158e0db348999e3f`.
- CLI unchanged: `scripts/run_cfbd_schedules_capture.py`,
  `a03bd4ed3a76242c1a94493a27b2a6f9b6a1ac2438eacf3fdc923141478f2f47`.
- Backup manifest unchanged: `22afdf528d90febd2bad7e51f5e0099fe79c96eecdfb3508396be1e82dbda396`.
- New contracts against unrepaired GREEN v1: **15 failed / 18 passed / 157 deselected**, true
  exit 1. Every failure was one of P0-1 through P1-5; the positive controls passed.
- After repair: focused **191 passed**, true exit 0; Ruff clean across RED/module/CLI; backup
  anti-rot/directory suites **12 passed**; full collection **5,257**, exit 0.
- Final full suite: **5,222 passed / 15 failed / 12 skipped / 9 xfailed** in 980.23 seconds. All
  15 failures are the separate withdrawn/untracked governed-cadence RED; no CFBD or backup test
  failed.
- This repair packet records the pre-capture GREEN state. The completed paid capture and landing
  evidence are in `cfbd_fbs_schedules_capture_acceptance_codex_v1.md`.

## Consolidated disposition

### P0-1 — accepted in full

Four isolated delivery mutants now hold every other URL component exact while varying only userinfo,
fragment, foreign port, or malformed port. Each requires `source_identity_unexpected`, exact-byte
quarantine, one failed audit, no canonical artifact, and no secret retention. GREEN now requires the
requested and delivered URL to equal the descriptor's exact HTTPS URL byte-for-byte. Sanitization no
longer reads `ParseResult.port`, so malformed ports cannot escape as `ValueError`.

### P0-2 — accepted in full

`audit` is now a fifth injected publication boundary under route, OS, and genuine mid-write faults.
Success-ledger publication is journaled and boundary-normalized with raw/check/vintage/index/marker;
the ledger itself is updated atomically instead of by an unprotected append. Any audit failure rolls
every success artifact and the prior ledger back, sweeps partial temp files, then attempts one failed
record through a fresh base filesystem path so the injected collaborator cannot suppress recovery.
Failure-record trouble never masks the named `PublishError`.

### P0-3 — accepted in full

Filesystem JSON reads normalize malformed index or marker bytes to
`state_integrity_invalid`. Index loading moved inside the journaled publication transaction. A bad
index therefore fails before any write; a bad marker encountered after writes rolls all new state
back. Both populated-store mutants preserve the exact corrupt prior bytes and canonical census and
append one failed paid-attempt audit with actual request count.

### P0-4 — accepted in full

Local replay now resolves the retained check through the index, verifies the full SHA-256 and byte
count of both check and content objects, and verifies the vintage's ID/hash/byte count before parsing.
Valid-but-different JSON substitutions in the check or content object, plus a valid JSON vintage with
a changed identity, all fail `content_integrity_mismatch` without mutating any file or ledger event.

### P1-5 — accepted in full

Source kickoff timestamps must now match full provider lexical shape: date + `T` + hour + minute +
second, with optional fractional seconds and optional `Z` or numeric offset. Calendar-invalid values
still pass through `datetime.fromisoformat` validation and fail. Truncated hour, truncated minute, and
space-separated values are refused; complete naive, fractional-Z, and offset values are positive
controls and remain verbatim.

### GREEN v2 R1 — accepted in full

The added `vintage_payload` mutant changes only `vintage.games[0].id`, leaving every identity claim
intact. It failed against GREEN v2 while the three earlier replay mutants passed. Canonical
`load_vintage` now verifies its index link, full content SHA and byte count, freshly parses the
verified raw bytes, recomputes schema and schema hash, and requires exact agreement for vintage ID,
raw identity, row count, schema, schema hash, and games. Replay uses that same guarded read, so neither
replay nor an ordinary consumer can read a validly encoded but semantically corrupted vintage.

## Standing

This packet was superseded by independent GREEN clearance and the completed acceptance packet named
above. No commit, push, scheduler, cadence input, or consumer wiring occurred in this lane.
