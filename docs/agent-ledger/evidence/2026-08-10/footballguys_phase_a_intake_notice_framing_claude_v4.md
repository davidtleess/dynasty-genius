# Phase A framing v4 — Footballguys archive intake + monthly refresh notice (Claude)

Date: 2026-08-10 · **Layer 1 (ingest).** Supersedes framing v3 (`261ee90b…`). Responsive to the
Codex round-3 review: Phase A findings 2–8, **ACCEPTED 7/7, zero contested** (finding 1 is plan
v4's). **Framing only — no RED, build, scheduler, provider contact, or store creation. David's
retention word (§8) remains a hard gate even after any CLEAR.**

## 0. Disposition

| # | Finding | Disposition |
| :-- | :-- | :-- |
| 2 | superseding v3 dropped accepted read-path/composition contracts | **ACCEPT — restored VERBATIM, §2** |
| 3 | receipt idempotency has no immutable signature | **ACCEPT — offering signature frozen, §5** |
| 4 | **Critical** — `O_CREAT\|O_EXCL` canonical writes break dedup and can poison the hash path | **ACCEPT — stage-then-publish, §6** |
| 5 | intact-ZIP boundary is not a safe reader contract | **ACCEPT — archive reader contract, §4** |
| 6 | retention option 3 contradicts the receipt invariant | **ACCEPT — `refresh_observation` model chosen, §8** |
| 7 | `semantic_evidence` straddles two provenance boundaries | **ACCEPT — external evidence attachment, §3** |
| 8 | state matrix asserted, not enumerated | **ACCEPT — reachable-state table, §7** |

**Finding 2, named as the process defect it is:** v3 silently narrowed the accepted boundary while
claiming to supersede it — the same "superseding artifact quietly drops cleared content" class the
post-commit divergence audit exists to catch, this time caught in framing. Restored verbatim below;
a superseding contract carries the whole accepted boundary or names exactly what it removes.

**Finding 4, conceded plainly:** I reused the pilot generator's "never overwrite any output" rule
for a deduplicating content store, where it is wrong twice — a legitimate second offering of the
same bytes must *reuse* the canonical object, and a crash between partial write and verification
would leave a corrupt object squatting on the hash path, refusing every retry.

## 1. David's words served (unchanged)

*"keep it as a paid source of mine - have a reminder or refresh notice come up once a month"* ·
*"determine how to plan and execute your recmmendation in #2"*.

## 2. Read path and surface composition — v2's accepted contracts, RESTORED VERBATIM

- the manual-feed read model is **id-addressed and separate from capture-health `stores[]`**;
- existing capture-health facts and `stores[0]` consumers remain **byte-equal**;
- corrupt/missing Footballguys state degrades **only this stream** to `unverifiable`;
- global `overall_status` **does not inherit it** (Codex-accepted ruling);
- a **reviewed pre-code composition artifact precedes any component RED**;
- detail lives in the **existing status drawer**; at most a **neutral count** reaches the status
  pill; it is **never** a toast, modal, verdict-colored warning, or first-viewport block;
- desktop/mobile, keyboard/focus behavior, and **all** display states are part of that composition
  review.

Also unchanged from v3: canonical `SOURCE_REGISTRY[footballguys]` role=`market_overlay`, fail-closed
field boundary, projection values barred beyond identity, Engine A/B alias mutant, PP/PFF
byte-equality proof, `source=footballguys` / `stream=bundle` with the dotted form as composed
read-model id only.

## 3. Roles and evidence provenance (finding 7)

**Archive-member roles are exactly `adp` and `identity_sidecar`.** Semantic evidence is a
**separate hashed evidence attachment**, never an archive role: its own retrieval provenance
(what was captured, from where, when, by whom), retention classification, and **allowed-claim
fields** (only `product_family` / export / field names / format / scoring / `horizon`). If a future
provider archive happens to contain a qualifying semantic member, it binds through the same
attachment contract — an attachment whose source is an archive member — and is **never folded into
`content_vintage_id`**, which remains a hash over the two role records alone. No implication that
external screenshots or pages arrived inside the archive.

## 4. The archive reader contract (finding 5)

The paid ZIP is untrusted data; nothing in it is executed, and it is never `extractall`ed:

- **stream only the exact selected members**;
- reject: encrypted members · symlinks/devices/special files · duplicate **normalized** member
  paths · absolute/drive paths · NUL bytes · path separators after normalization;
- caps: total archive bytes · member count · per-member uncompressed bytes · aggregate uncompressed
  bytes · compression ratio (decompression-bomb stop);
- exactly one distinct member per required role — cardinality enforced;
- decompressed bytes verified against declared size and CRC/hash **before** any raw object is
  published.

Every guard gets a positive ordinary-archive control AND one malicious-archive mutant.

## 5. The immutable offering signature (finding 3)

**`offering_signature` = hash over the canonical serialization of:** `source` · `offering_id` ·
`content_vintage_id` · validated `retrieved_at` · archive sha256+bytes · the ordered role records ·
semantic-contract fields · evidence-attachment references. **`receipt_id` IS the signature hash** —
one design, the slash is gone.

- same `offering_id` + identical signature → **idempotent no-op**;
- same `offering_id` + ANY differing signed field → **`offering_identity_conflict`**, fail-closed —
  never a silent retry, never an overwrite;
- new `offering_id` + existing `content_vintage_id` → new observation of an unchanged vintage (§v3
  rule, unchanged).

## 6. The content store: stage-then-publish (finding 4 — the Critical)

1. **Stage** each object under a noncanonical temporary name on the same filesystem: stream within
   §4's caps, hash while writing, fsync, close.
2. **Publish atomically** to the canonical content path with **no-replace semantics**; fsync the
   parent directory.
3. **If the canonical path already exists:** require a regular non-symlink file, verify size+hash,
   and **reuse it** — the legitimate dedup branch. Mismatch = corruption, fail closed, named error.
4. **Commit the offering receipt LAST**, one SQLite transaction, uniqueness on `receipt_id` and
   `offering_id`, referencing the published-or-verified object. Receipt-commit failure leaves
   reported recoverable orphans; a receipt citing absent bytes stays unrepresentable.

Crash mutants required at: during staged write · between file fsync and publish · after publish
before directory fsync · on the reuse branch. *(The pilot generator's never-overwrite rule is
recorded as NOT reusable for a deduplicating store — that reuse was this round's Critical.)*

## 7. The reachable-state table (finding 8)

Freshness clock = latest **valid** acquisition (`retrieved_at`); attempt = newest intake attempt;
AR = `latest_analysis_ready`. Pill counts freshness states `{no_record, due, unverifiable}` only;
readiness never increments the pill (it is drawer detail — composition artifact renders both axes).

| # | Clock source | Newest attempt | AR | Status | Exact copy (banned-language-scanned) | Pill |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| 1 | none | none | none | `no_record` | `No Footballguys refresh recorded` | +1 |
| 2 | none | `failed` | none | `no_record` | `No Footballguys refresh recorded · last intake attempt failed` | +1 |
| 3 | valid, <30d | `ready` (same) | same | `current` | `Last Footballguys refresh recorded N days ago` | 0 |
| 4 | valid, <30d | `review_required` (same) | older or none | `current` | `Last … N days ago · latest drop awaiting data review` | 0 |
| 5 | valid, <30d (older offering) | `failed` (newer attempt) | ≤ clock | `current` | `Last … N days ago · last intake attempt failed` | 0 |
| 6 | valid, ≥30d | `ready` (same) | same | `due` | `Last … N days ago — monthly refresh due` | +1 |
| 7 | valid, ≥30d | `failed` (newer) | ≤ clock | `due` | `Last … N days ago — monthly refresh due · last intake attempt failed` | +1 |
| 8 | valid, <30d | `review_required` (same) | **older offering** | `current` | `Last … N days ago · latest drop awaiting data review · analysis uses the <date> drop` | 0 |
| 9 | ledger unreadable | — | — | `unverifiable` | `Footballguys refresh record unreadable` | +1 |
| 10 | any healthy row | any | any | unchanged | unchanged — **global app-health degradation changes nothing here, and vice versa** | unchanged |

**Impossible rows, and why:** AR newer than the clock (AR advances only to a valid-acquisition
offering, which also advances the clock) · `ready` newest attempt with `failed` freshness (a ready
offering is by definition committed+valid, which advances the clock) · `due` and `no_record`
simultaneously (disjoint by definition) · pill incremented by any readiness state (pill is
freshness-only by contract). The RED enumerates every row and every impossibility as a test.

## 8. Retention — option 3 model chosen (finding 6); DAVID'S WORD still the gate

The v3 contradiction is resolved: **option 3 = `refresh_observation`, a separately named
metadata-only record** (archive hash+bytes, declared acquisition provenance, `raw_retained=false`,
`analysis_ready=false`) sufficient for the monthly reminder and **permanently ineligible for Phase
B/C**. It is never called an intake receipt; the §6 receipt invariant governs byte-retained intake
receipts only. As a non-regenerable store, the observation ledger itself needs **manifest coverage
before its first write**.

**David's choice, unchanged and still required before any RED:** (1) full offsite raw backup ·
(2) named local-only exception with the loss model written in · (3) `refresh_observation` only.

## 9. Out of scope (unchanged)

Phase B/C/D · any delta or horizon claim · scheduler installs · provider contact · PP/PFF designs ·
Studio.

**PLEASE REPLY with: (a) CLEAR on Phase A framing v4 with checks run, OR (b) numbered findings.**
No RED opens; §8's David gate survives any CLEAR.
