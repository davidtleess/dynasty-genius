# Codex framing CLEAR — Layer-1 six-loader batch

**Artifact reviewed:**
`docs/agent-ledger/evidence/2026-08-04/six_loader_batch_disposition_claude_v2.md`, patched v2 state  
**Scope of verdict:** framing gate only; permission to open the PFR RED  
**Verdict:** **CLEAR — the PFR RED may open.**

## Enumerated checks

1. **C1 batch scope:** all six loaders remain one work/framing/review/full-gate batch; sequential
   implementation is not separate landing (`disposition_claude_v2.md:27-34`, `:197-205`).
2. **C2 market wall:** FantasyPros remains in the batch but routes to a physically separate,
   `market_overlay`-classified PIT store/export with registry and negative Engine A/B consumer gate
   (`:36-52`). This preserves `00:119-123` and `01:157-159`.
3. **C3 depth eras:** v2 recognizes that `StreamEra` already owns era-specific grain and narrows the
   open issue to old-era semantics (`:54-61`).
4. **C4 opportunity classes:** player rows and anonymous/team aggregates are distinguished; the
   declared player grain uses `game_id` (`:63-70`). The aggregate disposition remains a later
   opportunity-RED choice and does not block PFR.
5. **C5 capture axis:** seasonless contracts/rankings now require an effective-date/vintage axis and
   may not be forced through artificial seasons (`:72-82`).
6. **C6 PFR provenance/grain/identity:** raw sha256 is required; grain is
   `(game_id, pfr_player_id)` (`:84-92`). The corrected 2018-2025 row census is now scoped exactly:
   121,688 canonical + 266 source-only + 0 conflict + 0 unknown = 121,954, while the three conflict
   IDs are separately described as global bridge metadata absent from these rows (`:94-131`). Codex
   independently reproduced the same values in `probe_pfr_full_range_codex_v1_output.json`.
7. **C7 FTN identity applicability:** not-applicable identity is explicit, fail-closed, excluded from
   unresolved-player counts/artifacts, and distinct from unknown (`:133-140`).
8. **C8 contracts:** exact duplicates are separated from semantic conflicts; raw retention,
   reconciliation, and nested round-trip obligations are explicit (`:142-151`).
9. **C9 falsification:** corrected seeds and the missing input-class matrix rows are adopted,
   including both capture- and export-stage failure, Boolean/list round-trip, API misuse, empty,
   wrong-type, heterogeneous shape, duplicate classes, invalid identity modes, non-finite values,
   market-boundary crossing, and synthetic failures (`:153-171`).
10. **C10 disposition/compounding:** every stream has a named owner/use gate, no-consumer rationale,
    capture range, meaningful cadence, and accumulation behavior; no scheduler or consumer is
    authorized (`:173-195`).
11. **Authority and overclaim:** the work remains Layer 1 `substrate_only`; no predictive value,
    model use, consumer, commit, push, merge, or scheduler is cleared by this verdict.

The next artifact is the PFR contract/RED plus its seeded falsification matrix. Implementation GREEN
and batch landing still require fresh independent review and the one full-suite/Ruff batch gate.
