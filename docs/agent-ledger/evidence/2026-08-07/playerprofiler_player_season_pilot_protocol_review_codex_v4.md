# Re-review — PlayerProfiler `player_season` pilot protocol v3

**Reviewer:** Codex · **Date:** 2026-08-07 · **Layer:** Layer 1 ingestion inventory

**Reviewed artifact:**
`docs/agent-ledger/evidence/2026-08-07/playerprofiler_player_season_pilot_protocol_claude_v3.md`
at SHA-256 `721a98d7e24419484038400485f7d5f983f0ece17742d87853d2d7b2e2a01470`.
The supplied pin reproduces exactly.

## Verdict

**NOT CLEAR — T1 HIGH, T2–T3 MEDIUM, T4 LOW.** R1–R5 are substantially accepted. The authority hard
stop is strong and should remain; the issue is that §4.1 names only half of the missing read-only
instrument. No export questions should go to David yet because his burden choice would be against a
protocol whose executable prerequisite is still incomplete.

No code, export request, subscriber-data access, production ingest, provider call, capture, catalog
edit, checkbox movement, landing, commit, or push is authorized.

## T1 — a digest helper still cannot obtain production-equivalent normalized rows · **HIGH**

`semantic_block_digest(rows)` solves the inline-hasher problem only after the exact normalized rows
exist. They do not currently exist behind a pure/read-only interface.

`run_playerprofiler_ingest` performs source parsing/schema checks, identity resolution, slugging,
row-key construction, deduplication through `seen`, and block grouping inline at
`playerprofiler.py:630-674`; it then constructs the store and calls `apply_block`. There is no pure
normalization/block-preparation helper. A pilot with only `semantic_block_digest` must therefore
either duplicate that normalization logic—another drift-prone parallel instrument—or enter the
ingest/store path §4.2 forbids.

Expand the separately authorized prerequisite to include one shared pure preparation boundary, for
example `prepare_player_season_blocks(exports, identity) -> {block: rows}`, reused by production and
pilot, plus the shared versioned digest helper. An equivalent pure read-only manifest builder is also
acceptable. RED/GREEN must prove the pilot and `apply_block` receive byte-identical normalized rows
and digests for the same exports, including identity, deduplication, and block grouping.

**Answer on prerequisite framing:** the repeated no-authority/no-run banners are strong enough. Keep
them. The missing piece is prerequisite scope, not warning strength.

## T2 — schema precedence and column-reorder compatibility remain ambiguous · **MEDIUM**

Rule 1 makes any schema mismatch `incomparable`; the next section says column reorder is not a
change. That does not quite say whether a reordered header bypasses Rule 1 or becomes
`incomparable`. Pin schema identity as an order-insensitive canonical column-name set (or another
exact order-insensitive definition). Then:

- reorder-only header/raw differences remain comparable and representation-only;
- added, removed, renamed, or duplicate columns are schema mismatches and make the interval
  `incomparable` before semantic comparison.

This makes §4.5's first-match precedence deterministic.

## T3 — “partial block” has no detection contract · **MEDIUM**

The exact expected block list detects a missing block, and parse/schema checks can detect malformed
files. But a valid-looking file with fewer rows is observationally ambiguous: it may be a genuine
source-state change or a truncated/partial export. Row count alone cannot distinguish them. The
blanket statement that every partial block reads `incomplete` therefore promises a classification
the instrument has not defined.

Pin evidence that proves completeness (for example, a provider/export UI completion count or other
declared signal), or narrow the rule to **detectably** missing/malformed/incomplete blocks. If no
independent completeness signal exists, disclose silent truncation as a threat to validity; a
schema-valid row-content difference otherwise follows the semantic rule and reads `changed`, not an
unsupported `incomplete`.

**Answer on §4.5:** aggregation and first-match order are otherwise complete after T2–T3.

## T4 — code citations are stale · **LOW**

Current `playerprofiler.py` places `PlayerProfilerStore.apply_block` at lines 441–468 and the digest
at 446–448, not 485–497. `read_export` begins at line 240 and derives blocks at 254–265; line 226 is
the section heading. Correct these references so the eventual RED/GREEN targets the actual surface.

## Repairs that pass

- The top banner, §2, §4.1, §7, and §9 consistently state that v3 is not runnable and authorizes no
  helper implementation.
- Module-file SHA, crosswalk SHA, and named digest version correctly replace HEAD as comparability
  provenance.
- Production DB isolation and the corrected recomputability rationale are accurate.
- Backup-covered versus single-copy/non-recoverable is honest; local read/hash authorization is
  reconciled with the no-copy/no-transport boundary.
- The append-only record has create-only immutable semantics, unique observation ID, atomic write,
  complete manifest content, file→block mapping, and raw-retention relation.
- `incomparable > changed > unchanged` is the correct batch-level precedence once T2–T3 define the
  observation predicates.
- The descriptive/no-source-publish-closure ceiling remains absolute and adequate.

Return v4 after T1–T4 only. No new data or code is needed for the protocol repair.

**H2 QB rushing remains a registered hypothesis UNDER TEST with no result.**
