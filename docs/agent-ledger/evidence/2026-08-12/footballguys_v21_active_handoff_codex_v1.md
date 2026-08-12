# Active handoff — Footballguys Phase A RED/GREEN v21

**Date:** 2026-08-12  
**Purpose:** compact-safe continuation record; operational summary, not a new authority.

## Authority and scope

David authorized Codex and Claude to work freely until this is production grade. The
direct RED/GREEN/adversarial-review loop is open. No commit, push, first capture,
provider contact, scheduler, or Phase B/C/D is authorized by this loop. H2 QB rushing
remains UNDER TEST and unrelated.

## Current frozen pins

- RED v21: `tests/contract/test_footballguys_phase_a_red.py`
  - SHA-256 `528afecded652b5ad06070c1dd73ae46813f7da444f4aa3b1ee1447f7000dec6`
  - 6,604 lines / 254,583 bytes
- Baseline GREEN v20: `src/dynasty_genius/sources/footballguys_intake.py`
  - SHA-256 `6fbac8af65c5f0c2eba92688a4ee7c600e0949b644262fc304a166076e2d14ca`

Codex must not edit the RED until Claude returns the complete v21 gate with hashes
verified before and after every run.

## Baseline census

- Strict module: **602 collected = 24 failed + 578 passed, exit 1**.
- V21 slice: 24F/3P; all 575 inherited v20 controls pass.
- RED and GREEN hashes matched before and after.
- Ruff and strict compile clean; zero skip/xfail/skipif.

## Four v21 findings

1. Critical: acquisition `WHERE offering_id != '_bootstrap'` filters NULL rows and
   bootstrap impostors before validation, falsely rendering `no_record`.
2. High: attempts `sqlite_sequence` state is ungoverned; invalid types/domain,
   duplicates, ghost rows, and high-water below max are accepted and can reset order.
3. High: current schema with future `user_version=999` is silently downgraded to 4.
4. Medium: invalid public `read_model(now=...)` values render `no_record` on empty
   state instead of literal row-9 fail-closed output.

## Delivery state

Combined review/RED wire:
`docs/agent-ledger/evidence/2026-08-12/footballguys_phase_a_green_v20_review_red_v21_codex_wire_v1.md`.
The helper returned `input_not_verifiable`; Codex positively saw its own collapsed
paste, sent the one permitted Enter, and then captured Claude’s recipient transcript.
The full distinctive content is visible there and marked queued while Claude finishes
an unrelated scoring command. Delivery is confirmed from transcript content. Wait for
Claude’s acknowledgment/reproduction before treating GREEN work as begun.

## Next actions

1. Claude reproduces frozen RED v21 as 24F/578P before editing.
2. Claude repairs all four or contests before GREEN.
3. Claude gates strict module, tracked suite, Ruff, strict compile, diff check, and
   real-store byte-copy probe with RED/GREEN hashes before/after.
4. Codex adversarially reviews the returned stable GREEN; only then either CLEAR or
   author next frozen RED.

No landing or publication action is implied.
