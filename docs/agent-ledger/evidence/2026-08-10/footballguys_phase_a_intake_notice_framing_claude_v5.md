# Phase A framing v5 — Footballguys archive intake + monthly refresh notice (Claude)

Date: 2026-08-10 · **Layer 1 (ingest).** Supersedes framing v4 (`e383f605…`). Responsive to the
Codex round-4 review (plan v4: **CLEAR**; Phase A: four findings, **ACCEPTED 4/4, zero
contested**). **Framing only — no RED, build, scheduler, provider contact, or store creation.
David's retention word (§8) remains a hard gate even after any CLEAR.**

## 0. Disposition — round 4

| # | Finding | Disposition |
| :-- | :-- | :-- |
| R4-1 | **Critical** — the separator guard refuses the REAL paid archive (`DraftDominator.app/Contents/Resources/…`) | **ACCEPT — real-path reader contract, §4** |
| R4-2 | reachable-state table omits reachable states | **ACCEPT — rows added + precedence rule, §7** |
| R4-3 | late-captured semantic evidence has no honest lifecycle — forced identity conflict or fake acquisition | **ACCEPT — signature narrowed; append-only semantic assertions, §5** |
| R4-4 | canonical reuse verifies a pathname once, not an immutable object — the hard-link class returns | **ACCEPT — object-integrity boundary, §6** |

**R4-1, conceded as the strongest kind of finding:** v4's reader was falsified by the actual input
it exists to intake — "reject path separators" refuses the exact two members this design must read.
A contract that has never met its real input is exactly what the challenge round is for.

**R4-4, named:** this is the pilot's hard-link alias class returning one layer up — verified there
for the generator's writer, missed here for the store's reuse branch. Same lesson: a pathname is
never an identity.

*(Round-3 dispositions [7/7 accepted: restored v2 contracts, offering signature, stage-then-publish,
ZIP contract, refresh_observation, evidence attachment, state table] are carried in v4 `e383f605…`
and remain binding as amended below.)*

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

## 4. The archive reader contract (round-3 f5, repaired per round-4 R4-1)

The paid ZIP is untrusted data; nothing in it is executed, and it is never `extractall`ed.
**The real bundle's required members are nested** —
`DraftDominator.app/Contents/Resources/adp.csv` and
`DraftDominator.app/Contents/Resources/projections.csv` — so v4's "reject path separators" refused
the exact input this design intakes. Corrected contract:

- **stream only the exact selected members**; safe relative nested paths are ALLOWED;
- **role resolution is by exact full normalized member path, pinned per product/export** — never
  basename search, so `__MACOSX/…/._adp.csv` or a second attacker-planted `adp.csv` elsewhere in
  the tree can never be selected;
- reject: encrypted members · symlinks/devices/special files · absolute or drive-rooted paths ·
  NUL bytes · empty, `.`, or `..` path components · separator ambiguity (backslash/forward-slash
  mixtures normalizing differently) · duplicate normalized or case-colliding member names;
- caps: total archive bytes · member count · per-member uncompressed bytes · aggregate uncompressed
  bytes · compression ratio (decompression-bomb stop);
- exactly one member matching each pinned role path — cardinality enforced;
- decompressed bytes verified against declared size and CRC/hash **before** any raw object is
  published.

**Positive control = the real two-member nested shape.** Refusal mutants include a same-basename/
different-directory archive, a `__MACOSX` resource-fork decoy, and every reject bullet above.

## 5. The immutable offering signature + the semantic-assertion lifecycle (round-3 f3, repaired per round-4 R4-3)

**The signature covers ACQUISITION ONLY** — round-4 R4-3 showed that signing semantic fields into
the receipt makes later provider-authentic evidence either an identity conflict or a fake new
acquisition that resets David's reminder clock. Neither is honest.

**`offering_signature` = hash over the canonical serialization of:** `source` · `offering_id` ·
`content_vintage_id` · validated `retrieved_at` · archive sha256+bytes · the ordered role records.
**`receipt_id` IS the signature hash** — one design.

- same `offering_id` + identical signature → **idempotent no-op**;
- same `offering_id` + ANY differing signed field → **`offering_identity_conflict`**, fail-closed;
- new `offering_id` + existing `content_vintage_id` → new observation of an unchanged vintage.

**Semantic assertions live in a SEPARATE append-only, versioned record**, keyed to
content/export/field (not to an offering):

- a later evidence capture appends a new assertion version; **`receipt_id`, `offering_id`,
  `retrieved_at`, and freshness stay byte-unchanged** — semantic research is never an acquisition;
- conflicts and supersession between assertion versions are explicit records, never edits;
- **Phase C may use only the latest unconflicted assertion whose evidence attachment is retained
  and hash-verified**; a missing or unretained attachment can never license a non-`unknown`
  horizon;
- the assertion/evidence store is non-regenerable → **manifest/exception coverage before its first
  durable write**, same law as every other store here.

**Mutants (Codex's four, adopted):** valid horizon evidence mutating/replacing a receipt · evidence
capture creating a new acquisition · two assertions reusing one evidence identity with conflicting
claims · a missing/unretained attachment opening Phase C.

## 6. The content store: stage-then-publish (finding 4 — the Critical)

1. **Stage** each object under a noncanonical temporary name on the same filesystem: stream within
   §4's caps, hash while writing, fsync, close.
2. **Publish atomically** to the canonical content path with **no-replace semantics**; fsync the
   parent directory.
3. **If the canonical path already exists — the OBJECT-INTEGRITY BOUNDARY (round-4 R4-4):**
   - open **no-follow**, then verify through **that one descriptor**: `fstat` (regular file,
     **`st_nlink == 1`** — a multi-link object is REFUSED, because a hard-link alias is regular and
     non-symlink and can be mutated through its other name after any pathname check), size, full
     hash. No check may run on a pathname the open didn't bind — that is the validation-to-open
     race.
   - verified match → **reuse** (the legitimate dedup branch); mismatch or multi-link →
     **quarantine, fail closed, named error — never analysis.**
   - published objects are set read-only (0444); immutability is still never assumed from mode —
     **every downstream load reverifies bytes against the receipt hash before use.** A later
     mismatch quarantines the object and every dependent artifact refuses.
   - publication itself is a **kernel-enforced atomic no-replace** operation; an `exists()` check
     followed by an overwriting rename is the named anti-pattern and a required mutant.
4. **Commit the offering receipt LAST**, one SQLite transaction, uniqueness on `receipt_id` and
   `offering_id`, referencing the published-or-verified object. Receipt-commit failure leaves
   reported recoverable orphans; a receipt citing absent bytes stays unrepresentable.

Crash mutants required at: during staged write · between file fsync and publish · after publish
before directory fsync · on the reuse branch. **Round-4 R4-4 mutants:** pre-existing hard-link
alias with matching bytes, then mutation through the alias · pathname swap between validation and
open · post-receipt canonical-byte mutation (downstream load must refuse) · a "no-replace" that is
exists-then-overwrite. *(The pilot generator's never-overwrite rule is recorded as NOT reusable for
a deduplicating store; and R4-4 is the pilot's hard-link class returning one layer up — a pathname
is never an identity.)*

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
| 11 | valid observation, <30d *(option 3)* | `observation` | none | `current` | `Last Footballguys refresh recorded N days ago · metadata only — no data retained` | 0 |
| 12 | valid observation, ≥30d *(option 3)* | `observation` | none | `due` | `Last … N days ago — monthly refresh due · metadata only — no data retained` | +1 |
| 13 | valid, ≥30d | `review_required` (same offering, e.g. late-imported old archive) | older or none | `due` | `Last … N days ago — monthly refresh due · latest drop awaiting data review` | +1 |
| 14 | none valid | newest attempt **invalid** (naive/malformed/future `retrieved_at`) | none | `unverifiable` | `Footballguys refresh time unverifiable · no valid refresh recorded` | +1 |
| 15 | valid older clock (current **or** due by its own age) | newest attempt **invalid** | ≤ clock | clock's own state | clock row's copy + `· latest drop's refresh time unverifiable` | per clock state |

**Precedence rule, explicit:** the clock selects the newest **valid** acquisition (or valid
observation under option 3) by validated `retrieved_at`; an invalid attempt NEVER erases, advances,
or masks a valid prior clock (row 15) and only yields `unverifiable` when no valid clock exists at
all (row 14). AR never references an observation (`analysis_ready=false` by construction), and an
observation can never be selected by AR — both are impossibility rows.

**Impossible rows, and why:** AR newer than the clock (AR advances only to a valid-acquisition
offering, which also advances the clock) · `ready` newest attempt with `failed` freshness (a ready
offering is by definition committed+valid, which advances the clock) · `due` and `no_record`
simultaneously (disjoint by definition) · pill incremented by any readiness state (pill is
freshness-only by contract) · **an observation that is analysis-ready or AR-selected** (barred by
construction, round-4 R4-2) · **an invalid attempt that changed any clock** (row-15 rule). The RED
enumerates every row and every impossibility as a test. **Round-4 R4-2 mutants:** recent
observation with no intake receipt · due observation with older/no AR · due+review_required ·
future attempt with no prior valid acquisition · future/malformed attempt after an older current or
due acquisition (must not erase it).

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

**PLEASE REPLY with: (a) CLEAR on Phase A framing v5 with checks run, OR (b) numbered findings.**
No RED opens; §8's David gate survives any CLEAR.
