# Review — PlayerProfiler `player_season` observed-change pilot protocol v2

**Reviewer:** Codex · **Date:** 2026-08-07 · **Layer:** Layer 1 ingestion inventory

**Reviewed artifact:**
`docs/agent-ledger/evidence/2026-08-07/playerprofiler_player_season_pilot_protocol_claude_v2.md`
at SHA-256 `f3fa28b1b60ee5b41441f191af2f2c654e6e24ef3c1187d9d5937b5e65195342`.
The supplied pin reproduces exactly.

## Verdict

**NOT CLEAR — R1–R5.** The N6 scope, human dependency, full-batch/slice choice, route inventory,
descriptive ceiling, and production-store isolation are directionally sound. The remaining defects
are in the executable measurement contract and private-evidence handling, not in the decision to run
a bounded pilot.

No export request, subscriber-data access, production ingest, provider call, capture, catalog edit,
checkbox movement, landing, commit, or push is authorized.

## Direct answers to the three requested challenges

1. **Finding 1 reads the digest's mathematical properties correctly, but overstates the available
   instrument.** `PlayerProfilerStore.apply_block` (not `DurableStore`) computes an order-independent
   sorted-row JSON digest, but exposes no read-only digest function and returns only
   `inserted`/`updated`/`unchanged`. Obtaining that exact digest currently requires entering a
   mutation method or duplicating its inline formula.
2. **Finding 2's isolation requirement is correct:** the production DB is a current-state store and
   cannot be the pilot's history. But observation 2 does not make observation 1 unrecomputable while
   its exact raw files are retained; that destructive rationale is overstated. An external immutable
   observation record is still required.
3. **Section 6's interpretive ceilings are strong enough in substance**—especially the absolute
   no-closure rule—but the interval decision function and comparability provenance are not yet strong
   enough to produce trustworthy `changed`/`unchanged`/`incomparable` outputs.

## R1 — no read-only route to the claimed governed digest · **HIGH**

Protocol lines 112–124 say the pilot will “read” the governed detector rather than invent one.
Code inspection confirms the formula at `playerprofiler.py:441-468`, but it is inline inside
`PlayerProfilerStore.apply_block`; the method opens SQLite, may delete/reinsert a block, replaces the
single `pp_capture` row, and returns only a status string. The raw SHA is computed in `read_export`
and retained in the in-memory `ExportFile`, but production ingest does not persist it.

Before execution, choose and pin one route:

- extract a pure, versioned `semantic_block_digest(rows)` helper used by both `apply_block` and the
  pilot, with contract tests proving byte-for-byte identity to today's formula; or
- run the existing ingest against a fresh private scratch DB/root per observation, read its
  `pp_capture` hashes, and explicitly govern the derived-row scratch copy and its disposal/retention.

The first option is cleaner but is a code change requiring separate authorization/review. The second
contradicts the current “no agent copies raw subscriber rows anywhere”/no-store-mutation framing
unless the protocol explicitly admits and governs that private scratch store. Copying the formula
into an ad hoc pilot script is the parallel hasher the protocol says it avoids.

## R2 — commit SHA does not pin the inputs to this digest · **HIGH**

Lines 142–156 make repository commit SHA the comparability key. That is both over- and
under-inclusive:

- an unrelated commit changes HEAD and would force `incomparable` although the parser is identical;
- an uncommitted edit to `playerprofiler.py` leaves HEAD unchanged and could produce a false
  `changed`/`unchanged` comparison.

More importantly, the digest covers every normalized row dictionary. Those dictionaries include
`dg_player_id`, `identity_status`, and `identity_candidates` (`playerprofiler.py:650-674`), derived
from `GOVERNED_CROSSWALK`. A crosswalk change can therefore move the digest with identical vendor
bytes even when `playerprofiler.py` is unchanged.

Each observation must record at least:

- exact SHA-256 of `src/dynasty_genius/playerprofiler.py`;
- exact SHA-256 of the governed crosswalk actually loaded;
- a named semantic-digest/canonicalization version; and
- optionally HEAD as audit context, but not as the comparability key.

Any required provenance mismatch makes the interval `incomparable`. If the pilot instead defines a
source-only digest excluding local identity fields, it is a new detector and must be separately
specified/tested rather than called the existing production digest.

## R3 — interval output function and precedence are missing · **HIGH**

The protocol says the only interval outputs are `changed`/`unchanged`/`incomparable`, while line 158
says a missing/partial block reads `incomplete`/`unavailable`. It never maps observation status to
the interval result or defines how 36 block comparisons aggregate.

Pin the decision function, for example:

1. validate report/filter identity, exact expected block set, file-to-block mapping, schema/coverage,
   and R2 provenance at both endpoints;
2. any invalid/incomplete/unavailable endpoint or provenance/schema mismatch → `incomparable`;
3. otherwise any per-block semantic-digest difference → `changed`;
4. otherwise all expected block digests equal → `unchanged`.

State whether header column reordering is schema-compatible (the semantic digest is order-immune),
and that raw-SHA-only representation changes do not produce `changed`. The slice option uses the same
function over its one predeclared block.

## R4 — “regenerable-only” is false for historical observations · **MEDIUM**

This corrects language from my own P6 review as well as the protocol: an exact export captured at a
past observation time cannot be regenerated later after endpoint state changes. A new download is a
new observation, not recovery of the old bytes.

Present David's choice as **backup-covered** versus **single-copy/not backup-covered**, with the
second option explicitly accepting permanent loss of replayability if those files disappear. Also
resolve the access contradiction: the table says “David only,” while §7 says the agent will hash and
compare. Pin authorized local processing by David and the explicitly tasked local agent process,
with no external transfer and no copying except any separately governed scratch route chosen under
R1.

## R5 — append-only pilot record is not yet a reproducible artifact contract · **MEDIUM**

Lines 135–137 require an append-only record but do not name its location, file shape, observation ID,
write/immutability rule, or raw-file-to-block mapping. Pin these before collection: one create-only
immutable manifest per observation (or an equivalently enforced append-only format), atomic write,
unique observation ID, exact file→block association, all §4.4 fields, and where the manifests live
under the R4 retention/backup choice.

Retain production isolation, but replace “observation 2 destroys observation 1 and leaves no way to
recompute it” with the accurate reason: production tables and `pp_capture` retain only current state,
so they cannot be the authoritative history; the immutable pilot record plus retained exact bytes
are that history.

## Checks that pass

- Whole-repo Python scan and retirement control support the bounded no-tracked-executable-route
  statement; disclosed hits are non-callers.
- Live DB measurements reproduce: 5,476 `pp_player_season` rows, 9 seasons, 4 positions, 36 blocks;
  `pp_capture` has one primary-keyed row per stream key and 36 `player_season` entries.
- `apply_block` does delete/reinsert changed block state and replace the capture row; production DB
  isolation is warranted.
- Raw hashing and semantic hashing are distinct operations; row/key ordering and CSV representation
  do not move the semantic digest when normalized rows remain equal.
- Complete-batch versus one-slice burden is presented to David without a hidden recommendation.
- Three observations/two weekly off-season intervals carry no sample-count pass criterion.
- Section 0 and Section 6 correctly forbid source-publish closure regardless of outcome; N1–N8
  remains open.

Return protocol v3 after R1–R5 only. No execution or new data is needed for the repair.

**H2 QB rushing remains a registered hypothesis UNDER TEST with no result.**
