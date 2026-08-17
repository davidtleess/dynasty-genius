# QB-1 PBP Parse-Seam Round 15 Open Receipt — Codex v1

Date: 2026-08-16  
Run: `f8f7551c-a145-46e2-b9b4-dec427f313ba`

## Authority

David's exact word:

> approved - open one bounded round per your sanctioned mechanism: claude implements the pbp parse seam exactly per your registration read's boundary, claude also runs a read-only diagnostic sweep enumerating every remaining named wall in the composition (results discarded unread, no repairs), and on your explicit clear a fresh rerun fires - the registered readout then comes to me for my ruling

## Pinned pre-state

- Revision `88`, `blocked/BLOCKED`.
- Round 14 CLEAR/closed, close snapshot
  `6147a09aa7c2fcc88a56cd6418430d333642bfc970d43d1f843904c3cb848f23`.
- Round-14 review SHA-256
  `2a9f535ec7a228f7d400646a7e39af03d03fbb7c7834c4df7a23c6355d93d88f`.
- Failed rerun artifact SHA-256
  `ce4369becf5618de0a9a08042655556cfa3b22054607b28efa98a3e710ca112b`:
  `manifest_column_missing`, detail `pbp: offense_team`, no result.
- Registration read SHA-256
  `fe95c24b436af3e8355fbffd8ee432675da8edeae41200335ebbebf53042016f`.

## Transition

Revision-guarded opener
`qb1_pbp_parse_round15_open_codex_v1.mjs` passed `node --check` and its
default non-mutating dry run. Applied once through `persistRun`: revision
`88 → 89`, ACTIVE `green-review`, Round 15 open.

Exact scope and opening pins:

- `src/dynasty_genius/adapters/nflreadpy_qb_adapter.py`
  `51af156bcdc044975fd42d21b77fe69901b5f5c231ac67c216cd82a6d2293735`
- `src/dynasty_genius/eval/qb_validation/execution.py`
  `b0c641743dbaf332d47d3508a6ca69c94b4e9797fd28582ec39e7fb9974965da`
- `tests/contract/test_qb1_green_correction_contracts.py`
  `3a9c51f9ec8a2b943871ad9aa8f546166de00468e043a2697b0ffd65b59d039a`

Open snapshot SHA-256:
`bae7112c4e2c397162417544cd47703993906915ebc0ba27873776c090b1e769`.
An independent post-apply recomputation matched it exactly.

## Boundaries

- Implement the shared adapter's already-registered PBP parse semantics after
  receipt admission and before the parsed-frame source gate/matrix, on a
  defensive copy: REG filter plus exact `posteam → offense_team` rename.
- Preserve hash-before-parse admission, raw inputs, provenance, registration,
  and every named fail-closed guard. No second parser or competing rename table.
- Contract-pin normalize-once, no fork, non-REG exclusion, and the registered
  named refusal for missing source columns.
- Run one read-only diagnostic sweep enumerating every remaining named wall in
  the composition. Study results are discarded unread; no repair, provider
  fetch, input mutation, publication, commit, or push.
- The fresh registered rerun remains held until Codex's explicit CLEAR. Its
  registered readout returns to David for a separate ruling.
- H2 QB rushing remains **UNDER TEST with no result**.
