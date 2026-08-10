# Footballguys plan v3 + Phase A framing v3 — Codex round-3 review

Date: 2026-08-10

Reviewed artifacts and reproduced identities:

- `footballguys_horizon_divergence_plan_claude_v3.md` — SHA-256
  `ec4e2bb2c727979d19be3bdf8c9345e468a5836e476a80fa1b1eeeef4bcc7cd2`, 132 lines,
  9,270 bytes.
- `footballguys_phase_a_intake_notice_framing_claude_v3.md` — SHA-256
  `261ee90b319ead848470bfaf107447fcc97dee4606d41a09e08221ca218498d1`, 158 lines,
  10,278 bytes.

## Verdict

**NOT CLEAR: one plan pointer repair and seven Phase-A repairs.** The nine round-2 dispositions are
accepted in substance. No prior analytical finding is reopened. The declared-acquisition clock,
three conceptual identities, source-registry cordon, intact-archive direction, prepare-before-
receipt ordering, and retention hold are all correct.

No RED, build, intake, store, scheduler, comparison, or surface opens.

## Findings

### 1. Plan / Low — v3's live phase pointers still name superseded Phase A v2

Plan v3 §9 says “Phase A: framing v2 authored,” and the David-word register also points to Phase A
framing v2. The live companion is v3. These are operational provenance pointers, not historical
disposition citations; following them sends a future lane to superseded retention and transaction
rules. Point both at Phase A framing v3 and its exact hash/version.

### 2. Phase A / High — the superseding v3 drops accepted read-path and surface-composition contracts

V3 says it supersedes v2, but it omits material requirements that v2 carried from the seven notice
findings:

- the manual-feed read model is id-addressed and separate from capture-health `stores[]`;
- existing capture-health facts and `stores[0]` consumers remain byte-equal;
- corrupt/missing Footballguys state degrades only this stream to `unverifiable`;
- global `overall_status` does not inherit it;
- a reviewed pre-code composition artifact precedes any component RED;
- detail lives in the existing status drawer, at most a neutral count reaches the status pill, and
  it is never a toast, modal, verdict warning, or first-viewport block;
- desktop/mobile, keyboard/focus, and all states are part of that composition review.

The disposition paragraph mentions two of those, but a superseding contract must preserve the
whole accepted boundary. Restore them verbatim or state that exact v2 sections remain binding; the
former is safer because this repo's bootstrap rule forbids relying on summaries/superseded files.

### 3. Phase A / High — the receipt idempotency contract still has no immutable signature

`receipt_id / idempotency key` is not a derivation or a conflict rule. “Same offering retried” can
mean the same `offering_id` with changed archive bytes, retrieval time, or semantic declaration.
That must conflict, not silently no-op.

Freeze an immutable offering signature over at least source, `offering_id`,
`content_vintage_id`, validated `retrieved_at`, archive hash/bytes, role records, and semantic
contract/evidence references. Repeating the same offering id and identical signature is a no-op;
the same offering id with any different signed field is `offering_identity_conflict`. Define
whether `receipt_id` is the signature hash or a separate key; do not leave the slash as two
interchangeable designs.

### 4. Phase A / Critical — the content-store algorithm conflicts with same-content/new-offering and can strand a partial canonical object

Section 4 requires a new offering of existing content to succeed. Section 6 says every
content-addressed object is created with `O_CREAT|O_EXCL`. A canonical object already exists for
that content, so an unconditional exclusive create rejects the legitimate second offering.

Writing directly through an exclusively created canonical filename has a second crash defect: a
crash after a partial write but before verification leaves a corrupt file occupying the hash path.
Every retry then refuses the pre-existing name; the canonical namespace is poisoned.

The closed algorithm needs two branches:

1. stage a new object under a noncanonical temporary name in the same filesystem; stream, bound,
   hash, fsync, and close it;
2. atomically publish it to the canonical content path with no-replace semantics and fsync the
   parent directory;
3. if the canonical path already exists, require a regular non-symlink object, verify size/hash
   and reuse it; mismatch is corruption and fails closed;
4. commit the offering receipt last, referencing either the newly published or verified-existing
   object.

Add crash mutants during the staged write, between file fsync and publish, after publish before
directory fsync, and on the existing-content reuse branch. The earlier pilot generator's “never
overwrite any output” rule is not directly reusable for a deduplicating content store.

### 5. Phase A / High — an intact ZIP boundary is not yet a safe archive-reader contract

Traversal rejection closes only one archive hazard. Phase A handles a paid but still untrusted ZIP
and must never blindly extract it. Before RED, specify:

- stream only the exact selected members; never `extractall`;
- reject encrypted members, symlinks, devices/special files, duplicate normalized member paths,
  absolute/drive paths, NULs, and path separators after normalization;
- cap archive bytes, member count, each uncompressed member, aggregate uncompressed bytes, and
  compression ratio to stop decompression bombs;
- require one distinct member per required role and exact cardinality;
- verify decompressed bytes and archive CRC/hash before publishing any raw object.

Each guard needs a positive ordinary-archive control and one malicious mutant. The archive is data;
nothing from it is executed.

### 6. Phase A / High — retention option 3 contradicts the durable receipt invariant

Option 3 says “no durable raw intake yet — receipts only.” Section 6 says a receipt pointing to
absent bytes is unrepresentable and commits the receipt only after durable content exists. Both
cannot govern the same receipt type.

Choose one explicit model for option 3:

- **no intake receipt:** store only a separately named `refresh_observation` sufficient for the
  monthly reminder, with hash/size and declared acquisition provenance but
  `analysis_ready=false`, `raw_retained=false`; it can never feed Phase B/C; or
- **no record at all:** the reminder remains `no_record` until durable intake is authorized.

Do not call a metadata-only observation the byte-retained intake receipt. If the separate refresh
observation is non-regenerable, its own store still needs manifest coverage before first write.

### 7. Phase A / Medium — `semantic_evidence` straddles two incompatible provenance boundaries

Section 3 says all roles derive from the intact provider archive, but defines semantic evidence as
captured UI metadata or provider documentation. Those will usually be external to the archive.
Treat archive-member roles as `adp` and `identity_sidecar`. Bind external semantic evidence as a
separate hashed evidence attachment with its own retrieval provenance, retention classification,
and allowed-claim fields. If the provider archive itself contains a qualifying semantic member, it
may use the same attachment contract; do not imply an external screenshot or page was delivered in
the archive or fold it silently into `content_vintage_id`.

### 8. Phase A / Medium — the “full state matrix” is asserted but not actually enumerated

The examples cover current/due with ready/review-required plus no-record/unreadable, but not the
reachable precedence rules involving a failed newest attempt, an older valid acquisition, and an
older analysis-ready bundle. A RED cannot derive exact copy or state from “e.g.”.

Publish the reachable-state table before RED. For each row fix:

- selected freshness offering and its clock;
- latest attempt state;
- latest analysis-ready offering;
- public status enum(s), exact manager copy, and whether the neutral pill count increments;
- impossible combinations and why they are impossible.

Required cases include: no valid acquisition + failed attempt; due last-valid acquisition + failed
new attempt; current acquisition + review required; current acquisition + older analysis-ready;
unreadable ledger; and healthy Footballguys state while global app health is independently
degraded. This is where the accepted no-inheritance and two-axis rulings become executable rather
than merely narrative.

## State

- Plan v3: one stale-pointer repair.
- Phase A framing v3: seven repairs; David's retention word remains a separate hard gate.
- Phase B waits for A's frozen interface and independent oracle.
- Phase C/D remain closed.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.

