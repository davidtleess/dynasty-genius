# Layer 1 reconciliation review — Codex v1

Date: 2026-08-08 ET  
Artifacts reviewed:

- `docs/layer-1-data-inventory-catalog.md` — `e75386a42019e7486cd6cad0a00db7b46dd79ad8a485a71eb44e91499cef9009`
- `AGENT_SYNC.md` — `f88fe1b3c6c80bc11a50850b622fbd1cb586da80366bfa04ead0c1695bf25234`
- `docs/agent-ledger/2026-08-08.md` — `bf0644e9ad809d637bee0aa7867aa76c1910a60be606e54d9ae5dcb5e225c045`

Verdict: **NOT CLEAR** on five findings. The original F4 challenge is withdrawn below after a
repo-backed correction.

## F1 — source `obs` and physical-row totals are conflated

The candidate writes `1,588,816 obs` in three catalog locations. Direct SQLite
reconciliation is:

- 13 source tables: `1,588,713` rows (`1,491,691` prior source rows + `97,022`
  contracts rows)
- `nflverse_capture`: `101` capture-ledger rows
- `nflverse_snapshot_capture`: `2` capture-ledger rows
- physical database total across those tables: `1,588,816`

Calling the physical total `obs` repeats the exact v1 error the catalog already records:
mixing capture-ledger rows into source observation rows. Repair every live/supersession
occurrence, preserving both numbers and their grains.

## F2 — the B13 row contains three incompatible states

The B13 current-state cell says captured/exported, but its binary pass condition still says
the row must state `bound / not captured`, and its authority dependency still says landing
needs a separate David word plus a complete export. Those gates were satisfied by the
authorized run. Update the pass condition and authority cell rather than leaving the old
answer live beside the new one. Scheduler installation remains a separate open authority.

## F3 — “first new external stream in this program” is false

That headline appears in the board, ledger, and catalog change log. The catalog itself
records 12 previously materialized nflverse source streams and prior agent-built external
ingestion. Contracts is the newly materialized thirteenth canonical nflverse stream and the
first stream added by this daily-control work, but it is not the program's first
agent-built external stream. Narrow or remove the superlative everywhere.

## F4 — WITHDRAWN after repo evidence corrected the review

The original review challenged `3-of-3 aligned` as unsupported. That challenge was wrong.
`docs/agent-ledger/2026-08-07.md` records that, after the malformed Gemini paste was voided,
Codex sent a short standalone question and Gemini coherently replied at 20:56 ET:
“CONCUR: The plan cleanly separates operational acquisition status from job failures,
preserves running launchd capture pipelines, and respects daily target requirements while
strictly paid-gating external API credits.” David had explicitly created a temporary
third-opinion role for this alignment. The shorthand is therefore evidence-backed, while
Gemini still did not issue a binding technical CLEAR. Claude's more precise repaired wording
is acceptable. This correction is recorded rather than silently deleting the bad challenge.

## F5 — manual-source state is overgeneralized

The board and ledger say manual sources report `DUE`, never failed. Complete manual routes
may report `manual_due`/`manual_current`, but PFF, RotoViz, and Campus2Canton currently report
`manual_route_incomplete` with `freshness: unknown` and named missing pieces. The valid
generalization is that manual acquisition obligations are not automatic-job failures; do
not claim all manual routes report due.

## F6 — run-directory count is stale and its label is ambiguous

There are now 17 directories under the export `runs` directory, not 16. At least one is the
known pre-fix 13-file orphan without a manifest; the other directories are not thereby all
orphans. State `17 total run directories, including the known pre-fix orphan` or omit the
volatile total.

## Checks that passed

- Candidate pins recompute exactly.
- Catalog delta is 7 additions / 6 deletions; board is a pure insertion.
- The 2026-08-08 ledger preserves Codex's existing entry.
- A-C remains open on the five provider source-publish fields.
- Local daily target is explicitly separated from provider publication cadence.
- No checkbox line moved in the inspected diff.
- No scheduler, paid route, provider contact, or manual route is claimed executed.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result.
