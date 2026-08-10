# Phase A framing v6 — Footballguys archive intake + monthly refresh notice (Claude)

Date: 2026-08-10 · **Layer 1 (ingest).** Supersedes framing v5 (`a1ec47ec…`). Responsive to the
Codex round-5 review: five findings, **ACCEPTED 5/5, zero contested**. **Framing only — no RED,
build, scheduler, provider contact, or store creation. David's retention word (§8) remains a hard
gate even after any CLEAR.**

> **SELF-CONTAINMENT RULE, adopted after round-5 finding 4.** Twice now a superseding revision has
> dropped an accepted live contract while pointing readers at a retired version (round-3 f2, round-5
> f4). The structural fix: **this artifact carries every live Phase-A contract in full.** Nothing
> operational is incorporated by reference to a superseded framing; prior versions are history and
> disposition provenance only.

## 0. Disposition — round 5

| # | Finding | Disposition |
| :-- | :-- | :-- |
| R5-1 | **Critical** — archive-wide symlink refusal rejects the real 259-entry ZIP (3 framework symlinks); caps have no values | **ACCEPT — rules scoped to selected members; numeric caps frozen, §4** |
| R5-2 | observation rows omit the older-AR coexistence state | **ACCEPT — coexistence rows + literal mutants, §7** |
| R5-3 | "latest unconflicted assertion" launders an active conflict | **ACCEPT — effective-state reducer, §5** |
| R5-4 | the closed monthly-clock contract was dropped in supersession (again) | **ACCEPT — restored in full, §7a + the self-containment rule above** |
| R5-5 | receipt signature hash conflated with content hash | **ACCEPT — exact object model + hash edges, §6a** |

**R5-1, conceded with the pattern named:** round 4's Critical was "the reader refuses the real
members"; my repair validated against a two-member fixture and was falsified by the full real
archive one round later. **A positive control that is not the real input is not a positive
control** — the acceptance control is now the complete real ZIP (or a byte-faithful full-structure
fixture of its measured shape).

**R5-4, conceded with the pattern named:** the second superseding-drop. The self-containment rule
above is the structural fix, not another promise to be careful.

*(Round-4 disposition history follows; its repairs remain live and are carried IN THIS ARTIFACT.)*

## 0-prev. Disposition — round 4

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

*(Round-3 dispositions [7/7 accepted] are historical provenance; every surviving contract from them
— the restored v2 read-path/composition boundary, the offering signature, stage-then-publish, the
ZIP contract, `refresh_observation`, the evidence attachment, the state table — appears IN FULL in
this artifact's sections. No live rule lives only in a retired version.)*

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
- **type/encryption rules are SCOPED TO SELECTED ROLE MEMBERS (round-5 R5-1):** each selected role
  entry must be a regular, non-encrypted, non-symlink file; **unselected entries are never opened
  and never fail intake for their type** — the real archive legitimately contains three framework
  symlinks, none of them a role member;
- whole-archive central-directory rules cover ONLY extraction-free hazards: exact-role
  duplication/ambiguity · duplicate normalized or case-colliding names AT the pinned role paths ·
  absolute/drive-rooted paths, NULs, empty/`.`/`..` components, separator ambiguity **on selected
  paths and their resolution** · structural parse validity · the resource caps;
- **caps, frozen numeric, inclusive boundaries** *(real input measured: 8,540,590 archive bytes ·
  259 entries · 24,723,646 aggregate uncompressed · 12,376,512 largest member · max ratio
  11.8766:1)*: archive ≤ **64 MiB** · entries ≤ **2,048** · per-member uncompressed ≤ **64 MiB** ·
  aggregate uncompressed ≤ **256 MiB** · per-member compression ratio ≤ **100:1**, and **a nonempty
  member with compressed size 0 is REFUSED** (never treated as a finite ratio);
- exactly one member matching each pinned role path — cardinality enforced;
- decompressed bytes verified against declared size and CRC/hash **before** any raw object is
  published.

**Acceptance control = the COMPLETE real ZIP** (or a byte-faithful full-structure fixture with the
measured 259-entry/3-symlink/resource shape); the small two-role ZIP remains a unit positive only —
round 5 proved a partial fixture is not a positive control. Refusal/behavior mutants: reject any
unselected symlink (must NOT refuse intake) · accept a selected-role symlink (must refuse) · a cap
set below the known-good archive (acceptance control must fail the mutant build) · one cap omitted ·
zero-compressed-size nonempty member treated as finite ratio · any inspection/extraction of an
unselected member · same-basename/different-directory decoy · `__MACOSX` resource-fork decoy.

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
- **the effective semantic state is a REDUCER over all assertion versions for the active key,
  never a row filter (round-5 R5-3):** ANY unresolved conflict among retained assertions yields
  `horizon=unknown` and keeps Phase C closed — an older unconflicted claim can never win by the
  exclusion of the evidence that challenged it. **Supersession is a separate adjudication record**
  with its own identity, provenance, authority, and explicit parent versions; append order and
  evidence retrieval time never resolve a conflict by themselves. Assertion writes are idempotent
  on (key, assertion_id); ordering is by explicit version, not arrival;
- **Phase C may use only the reducer's effective state**, and only when its supporting attachment
  is retained and hash-verified; a missing or unretained attachment can never license a
  non-`unknown` horizon;
- the assertion/evidence store is non-regenerable → **manifest/exception coverage before its first
  durable write**, same law as every other store here.

**Mutants (Codex's rounds 4+5, adopted):** valid horizon evidence mutating/replacing a receipt ·
evidence capture creating a new acquisition · two assertions reusing one evidence identity with
conflicting claims · a missing/unretained attachment opening Phase C · **old unconflicted + new
conflicting assertion still emitting the old horizon** · a late-arriving older document silently
superseding · changed claims reusing an assertion id · an unproven `superseded=true` flag clearing
a conflict.

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
before directory fsync · on the reuse branch.

### 6a. The object model and every hash edge (round-5 R5-5)

**The retained canonical object is the intact provider ZIP** — one immutable content-addressed
object per content vintage. **Decompressed roles are regenerable views, not stored objects**: they
are streamed from the archive at read time and verified against their role records.

| Edge | Hash used | Never |
| :-- | :-- | :-- |
| receipt → canonical object | `archive_object_sha256` (the ZIP's content SHA-256, stored in the receipt) | `receipt_id` |
| role read from the archive | that role's member `sha256` from the ordered role records | archive or receipt hash |
| `content_vintage_id` | hash over the canonical ordered `(role, member_sha256, bytes)` records | archive hash alone |
| offering identity | `receipt_id` = hash of the canonical offering-signature serialization | any content hash |

**Downstream loads rehash the object against `archive_object_sha256` — never against `receipt_id`**
(the round-5 conflation: identity hashes identity fields; content hashes bytes; an implementation
comparing payload bytes to `receipt_id` rejects every valid object).

**`receipt_id` serialization is frozen with an independent known-answer vector** that does NOT call
the production serializer: explicit field order and types, UTF-8, fixed separators, decimal integer
representation, and timestamps normalized to one canonical UTC form so `…Z` and `…-04:00` spellings
of the same instant produce ONE identity. Mutants: object bytes compared to `receipt_id` · only
decompressed roles retained where the contract requires the intact archive · `adp`/`identity_sidecar`
role hashes swapped · equivalent instants in `Z` and offset forms yielding different receipt ids. **Round-4 R4-4 mutants:** pre-existing hard-link
alias with matching bytes, then mutation through the alias · pathname swap between validation and
open · post-receipt canonical-byte mutation (downstream load must refuse) · a "no-replace" that is
exists-then-overwrite. *(The pilot generator's never-overwrite rule is recorded as NOT reusable for
a deduplicating store; and R4-4 is the pilot's hard-link class returning one layer up — a pathname
is never an identity.)*

## 7a. The clock contract — restored IN FULL per round-5 R5-4 (no reference to retired versions)

- **Clock source:** the latest **valid** acquisition — or valid `refresh_observation` under
  retention option 3 — selected by validated declared `retrieved_at`; `recorded_at` is processing
  provenance only and never freshness.
- **Advance predicate:** a committed offering with all required bytes present and hash-verified,
  valid cohesion, and valid `retrieved_at` advances freshness. Horizon-unknown or
  schema/identity review pending → intake `review_required`, `latest_analysis_ready` unchanged,
  freshness still advances. Missing roles / invalid provenance / hash mismatch / write failure /
  absent bytes → `failed`, advances nothing. Naive, malformed, or future `retrieved_at` makes that
  offering freshness-unverifiable and cannot advance or erase any clock.
- **Due rule:** `due` ⇔ (today's **America/New_York calendar date** − the clock offering's
  `retrieved_at` **local calendar date**) ≥ **30 calendar days** — calendar-date arithmetic, not
  elapsed hours. **Day 30 is due (inclusive). No grace. Season-flat** — no in-season tightening
  without a new David word.
- **Delivery:** a persistent state, not an event — no toasts, notifications, or daily nags; no
  snooze or dismissal exists in v1; repeated reads remain `due` until a later valid
  acquisition/observation advances the clock.
- **Boundary controls (RED rows):** 29 vs 30 local calendar days · 29 days 23 hours across a DST
  change (still not due — calendar dates govern) · spring and fall DST boundaries · month and year
  boundaries · same instant written as `Z` vs `-04:00` normalizing to one New York calendar date ·
  season-flat probe · no-grace probe · repeated-read stability.

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
| 11b | valid observation, <30d | `observation` | **older retained receipt** | `current` | `Last … N days ago · metadata only — no data retained · analysis uses the <date> drop` | 0 |
| 12 | valid observation, ≥30d *(option 3)* | `observation` | none | `due` | `Last … N days ago — monthly refresh due · metadata only — no data retained` | +1 |
| 12b | valid observation, ≥30d | `observation` | **older retained receipt** | `due` | `Last … N days ago — monthly refresh due · metadata only — no data retained · analysis uses the <date> drop` | +1 |
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
due acquisition (must not erase it). **Round-5 R5-2 mutants, literal:** recent observation + older
AR, and due observation + older AR — each must advance freshness, leave AR byte-unchanged, disclose
BOTH facts in the copy, and never make the observation analysis-ready. Retention-mode coexistence
(receipts then observations, or the reverse, across a David retention change) is thereby a
first-class state, not a migration hole.

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

**PLEASE REPLY with: (a) CLEAR on Phase A framing v6 with checks run, OR (b) numbered findings.**
No RED opens; §8's David gate survives any CLEAR.
