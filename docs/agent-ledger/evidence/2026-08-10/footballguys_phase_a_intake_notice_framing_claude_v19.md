# Phase A framing v19 — Footballguys archive intake + monthly refresh notice (Claude)

Date: 2026-08-10 · **Layer 1 (ingest).** Supersedes framing v18 (`6c9e26d1…`). Responsive to the
Codex round-18 review: four findings, **ACCEPTED 4/4, zero contested** (the round-17 control-flow
Critical is confirmed closed). This round: the observation row gains its own durable identity and
constraints; the legacy A crash matrix gets its scope label (my surviving-sibling class, instance
eleven); the anonymous descriptor gets exactly ONE owner; and the call-trace oracle becomes
refusal-aware so correct pre-stream failures are not rejected. **Framing only — no RED,
build, scheduler, provider contact, or store creation. David's retention word (§8) remains a hard
gate even after any CLEAR.**

> **SELF-CONTAINMENT RULE, adopted after round-5 finding 4.** Twice now a superseding revision has
> dropped an accepted live contract while pointing readers at a retired version (round-3 f2, round-5
> f4). The structural fix: **this artifact carries every live Phase-A contract in full.** Nothing
> operational is incorporated by reference to a superseded framing; prior versions are history and
> disposition provenance only.

## 0. Disposition — round 18

| # | Finding | Disposition |
| :-- | :-- | :-- |
| R18-1 | the observation transaction has no durable identity or idempotency contract | **ACCEPT — `observation_id` = acquisition-signature hash; constraints + conflict rule, §6 B4** |
| R18-2 | the legacy post-crash matrix is unscoped after Branch B; safety sentence lacks the attempt referent | **ACCEPT — scoped to options 1/2; referent added** |
| R18-3 | B2 + B3 specify two success closes; fd reuse makes double-close unsafe | **ACCEPT — one scoped owner, single close, §6 B2/B3** |
| R18-4 | the call-trace oracle rejects correct pre-stream refusals | **ACCEPT — refusal-aware cardinality, §6 step 1** |

**R18-2, conceded as surviving-sibling instance eleven:** v18's wire claimed the sweep; the
unqualified "THE POST-CRASH MATRIX" heading and its one-object/one-receipt conclusion survived
below Branch B. **R18-3, conceded:** two closes in prose is a double-close in code, and a reused
fd number makes that a real resource bug, not a style issue.

## 0-prev17. Disposition — round 17

| # | Finding | Disposition |
| :-- | :-- | :-- |
| R17-1 | **Critical** — linked staging remained "common"; Branch B preceded its own prefix | **ACCEPT — §6 restructured as executable order; call-trace oracle, §6** |
| R17-2 | Branch B closes the descriptor only on success — every refusal leaks the paid inode | **ACCEPT — unconditional finally-class cleanup, §6 branch B** |
| R17-3 | the option-3 matrix confuses logical non-commit with an empty filesystem | **ACCEPT — permitted residue per object class, §6 branch B** |

**R17-1, conceded as additive-editing one structural level lower — the tenth instance:** I split
the branches in headings while the line order still ran B before the "common" step that only A may
execute. Reading order is the contract; a heading cannot rescue it.
**R17-2, conceded:** a cleanup rule stated only on the success path is half a rule — the same
one-branch-of-two defect as round 7's fresh/reuse invariant, recurring in descriptor lifetime.

## 0-prev16. Disposition — round 16

| # | Finding | Disposition |
| :-- | :-- | :-- |
| R16-1 | **Critical** — option 3 is prose beside a lifecycle that still publishes and commits receipts | **ACCEPT — §6 split into a mode-neutral prefix + two terminal branches; matrices scoped, §6** |
| R16-2 | unlink-before-write is not crash-DURABLE without the directory fsync | **ACCEPT — unlinkat + staging-dir fsync BEFORE the first byte, §6 branch B** |
| R16-3 | "no data retained" still describes the whole history while older data is deliberately retained | **ACCEPT — referent-qualified copy, §7 rows** |
| R16-4 | WAL is named but its establishment lifecycle is open | **ACCEPT — establish-verify-refuse at creation; verify on reopen, §6** |

**R16-1, conceded:** the ninth instance of my additive-editing class — a new rule laid beside the
old flow instead of into it. A mode is a branch in the executable lifecycle or it is not a mode.
**R16-2, conceded:** I claimed "every crash state" while my own §6 elsewhere admits pre-fsync
directory-entry uncertainty — the claim used a durability model the same section rejects.

## 0-prev15. Disposition — round 15

| # | Finding | Disposition |
| :-- | :-- | :-- |
| R15-1 | **Critical** — option-3 "stores DO NOT EXIST" erases the accepted retention-transition coexistence state | **ACCEPT — write mode ≠ historical presence, §6** |
| R15-2 | option 3 can show "no data retained" over a crash-resident paid ZIP | **ACCEPT — unlink-before-first-byte staging, §6** |
| R15-3 | "DB + sidecars" misstates the governed SQLite backup mechanism | **ACCEPT — ignore-vs-backup split; WAL frozen; online-backup REDs, §6** |
| R15-4 | the lockfile and sidecar sets are still unpinned | **ACCEPT — `intake/lifecycle.lock`; closed WAL file set, §6** |

**R15-1, conceded:** v15 wrote the option-3 storage rule as a timeless fact when it is a WRITE-MODE
fact — my own accepted coexistence rows (receipts→observations across a retention change) require
historical stores to remain readable. A mode governs what may be WRITTEN next, never what history
exists.

## 0-prev14. Disposition — round 14

| # | Finding | Disposition |
| :-- | :-- | :-- |
| R14-1 | the pinned paid-data namespace is not gitignored — provider bytes commit-eligible | **ACCEPT — ignore rule BEFORE first write, §6 step 0** |
| R14-2 | canonical object root and receipt store are floating paths | **ACCEPT — every runtime location pinned; hash-to-path grammar; same-device assertion, §6** |
| R14-3 | v14 claimed receipt-manifest coverage §6 does not contain — a false live pointer | **ACCEPT — coverage-before-first-write restored for EVERY durable store, §6** |
| R14-4 | the "executable guard" has no closed enforcement surface | **ACCEPT — injected spawn abstraction + static import bar + falsifiable RED, §6 step 0** |
| R14-5 | bootstrap unclosed against the real `0755` tree and concurrent creators | **ACCEPT — per-component predicate; `EEXIST` convergence, §6 step 0** |

**R14-3, conceded as my recurring pointer class:** a live sentence claimed coverage that existed
only in §8 — the eighth instance of an assertion outrunning its referent. The restored rule is now
IN §6 where the stores live, and the sweep checks the pointer's target, not just the pointer.

## 0-prev13. Disposition — round 13

| # | Finding | Disposition |
| :-- | :-- | :-- |
| R13-1 | the retired "detected after the fact" guarantee survives live in the reuse branch | **ACCEPT — deleted; forbidden-phrase sweep added** |
| R13-2 | the superseded "process death releases the lock" rule survives beside its correction | **ACCEPT — deleted; only the last-reference rule remains** |
| R13-3 | the fork RED proves an OS fact, not the implementation boundary | **ACCEPT — enforceable descriptor-ownership boundary + mutation-backed guard test, §6 step 0** |
| R13-4 | "fixed path" is not a bootstrap contract — no name, no parent chain, no missing-root rule | **ACCEPT — namespace identity pinned + creation lifecycle, §6 step 0** |

**R13-1/2, conceded as the pattern they are:** the sixth and seventh stale-sibling instances of
this thread. Presence-verification proves the NEW sentence exists; only absence-verification proves
the OLD one is gone. Both are now run.

## 0-prev12. Disposition — round 12

| # | Finding | Disposition |
| :-- | :-- | :-- |
| R12-1 | **Critical** — the lock-replacement RED demands excluded, unenforceable behavior | **ACCEPT — mutant retired; in-model serialization control; detection claim weakened honestly, §6 step 0** |
| R12-2 | the load-bearing `0700` namespace is asserted, never established or verified | **ACCEPT — namespace bootstrap + load predicate, §6 step 0** |
| R12-3 | missing observation identity is both a valid clock candidate and an invalid record | **ACCEPT — identity validated BEFORE clock candidacy, §7a** |
| R12-4 | "process death releases the lock" is false under fork inheritance | **ACCEPT — real lifecycle stated; no-fork-while-locked frozen, §6 step 0** |
| R12-5 | the sweep is not a function for grammar-nonmatching non-regular entries | **ACCEPT — ordered evaluation: grammar first, then type, §6 matrix** |

**R12-1, conceded:** the same defect shape as round 10's — a repair round introduces its own
inconsistency — this time between my threat model and my own required control. The discipline's
job is exactly to iterate until the model, the mechanism, and the tests say one thing.

## 0-prev11. Disposition — round 11

| # | Finding | Disposition |
| :-- | :-- | :-- |
| R11-1 | **Critical** — "bound entry" unlink is still check-then-unlink; a pathname cannot be bound by prose | **ACCEPT — threat model narrowed explicitly; impossible-mutant claim retired, §6** |
| R11-2 | `flock` not bound to a stable lock identity — two intakes can both hold "the" lock | **ACCEPT — closed lockfile contract, §6 step 0** |
| R11-3 | "safely removed" lets a sweep follow a planted entry outside the staging boundary | **ACCEPT — non-resolving sweep contract, §6 matrix** |
| R11-4 | `waits OR intake_busy` = two incompatible APIs; no state disposition | **ACCEPT — deterministic non-blocking `intake_busy`, a non-attempt, §6 step 0** |
| R11-5 | equal-instant equivalence undefined for observation pairs | **ACCEPT — observation equivalence key closed, §7a** |

**R11-1, conceded with the general lesson named:** I wrote "THAT BOUND ENTRY is unlinked" as if
capitalization created a kernel primitive. `lstat`-then-`unlink` is two syscalls with a window, and
the round-10 mutant DEMANDED a concurrent rename the lock cannot forbid — so my own contract
required an adversary my own mechanism could not survive. **A contract may only promise what some
real syscall sequence can enforce**; everything beyond that is a threat-model assumption and must
be declared as one.

## 0-prev10. Disposition — round 10

| # | Finding | Disposition |
| :-- | :-- | :-- |
| R10-1 | **Critical** — content disagreement is not refresh-time ambiguity; freshness stays `current`/`due` | **ACCEPT — remodeled as a readiness conflict over a certain instant, §7/§7a** |
| R10-2 | the conflict row hides the older AR drop it preserves | **ACCEPT — split by AR none / older, dated copy, §7** |
| R10-3 | the startup sweep can destroy a LIVE intake's staging file | **ACCEPT — per-source lifecycle lock before sweep, §6** |
| R10-4 | reuse cleanup returns to pathname identity after descriptor verification | **ACCEPT — unlink bound to the verified inode, §6** |
| R10-5 | receipt-failure residue conflates fresh and reuse branches | **ACCEPT — matrix row split, §6** |

**R10-1, conceded on both sides of the cockpit:** every candidate in the tie declares the identical
validated instant, so the 30-day arithmetic is exact — v10 suppressed a known `due` and inflated the
freshness-only pill, violating the orthogonal-axes contract this framing itself froze in round 2.
The conflict belongs to the READINESS axis, layered over a certain freshness instant.

## 0-prev9. Disposition — round 9

| # | Finding | Disposition |
| :-- | :-- | :-- |
| R9-1 | **Critical** — equal display facts ≠ equal analysis content; same-second `ready` receipts with different vintages collapsed | **ACCEPT — equivalence over every state- and analysis-affecting fact, §7a** |
| R9-2 | `clock_conflict` absent from the table and the two-stage function | **ACCEPT — conflict base row + full precedence, §7** |
| R9-3 | the reuse branch leaks one staged ZIP per dedup — no descriptor terminal state | **ACCEPT — split lifecycle, §6** |
| R9-4 | crash mutants name injection points but not required durable states | **ACCEPT — post-crash matrix, §6** |
| R9-5 | "A, B, or failure" overclaims snapshot semantics — staging yields a coherent C | **ACCEPT — guarantee restated precisely, §6** |

**R9-1, conceded:** I defined equivalence over the two facts the SCREEN shows, not the facts the
SYSTEM acts on — `latest_analysis_ready` could point at different football data by append order
while my mutant asserted only rendered copy. Display equality is not semantic equality.
**R9-5, conceded:** stage-first earns *internal coherence* — every signed fact describes the staged
bytes — not *atomic observation* of a concurrently mutable source. The contract now says exactly
what it earns.

## 0-prev8. Disposition — round 8

| # | Finding | Disposition |
| :-- | :-- | :-- |
| R8-1 | **Critical** — the one-snapshot rule was in the wire, not the live §6 | **ACCEPT — §6 rewritten, rule live** |
| R8-2 | staging hardening absent; fresh check contradicted the `close` lifecycle; no failure cleanup | **ACCEPT — closed descriptor lifecycle + cleanup, §6** |
| R8-3 | fixtures abbreviate their own input bytes | **ACCEPT — full member hashes embedded, §6a** |
| R8-4 | equal-`retrieved_at` candidates make base-row selection order-dependent | **ACCEPT — named clock conflict → unverifiable, §7a** |
| R8-5 | overlay prose vs table predicates specify different evaluators; ambiguous referents | **ACCEPT — two-stage function; rows 5/7 generalized; referents split, §7** |

## 0-prev7. Disposition — round 7

| # | Finding | Disposition |
| :-- | :-- | :-- |
| R7-1 | role records not bound to the retained archive snapshot — coherent-looking incoherent receipts | **ACCEPT — one snapshot boundary, §6** |
| R7-2 | the hard-link invariant missing on the FRESH-publication branch | **ACCEPT — staging creation + post-publication invariant, §6** |
| R7-3 | failed-attempt rows flatten the clock's readiness/retention facts | **ACCEPT — overlay composition generalized, §7** |
| R7-4 | seconds-precision quantization = durable-identity collision | **ACCEPT — fractional seconds REFUSED, §6a** |
| R7-5 | negative vectors require reverse-engineering | **ACCEPT — closed byte fixtures, full hashes, §6a** |

**R7-1, conceded:** each hash was honestly computed and the signed bundle could still be incoherent
— role facts from source ZIP A signed against staged ZIP B. Verification of parts is not coherence
of the whole; the pilot's oldest lesson ("component verified, whole claimed") arriving at the
filesystem layer. **R7-2:** the reuse branch got the descriptor-bound invariant in round 5 and the
fresh branch did not — a guard applied to one branch of two is half a guard.

## 0-prev6. Disposition — round 6

| # | Finding | Disposition |
| :-- | :-- | :-- |
| R6-1 | stale "receipt hash" instruction survived beside the repaired rule | **ACCEPT — swept, §6** |
| R6-2 | "one object per content vintage" contradicts the two identities | **ACCEPT — cardinality frozen, §6a** |
| R6-3 | state rows overlap with conflicting copy — the table is not a function | **ACCEPT — disjoint rows, §7** |
| R6-4 | the spring-DST oracle is INVERTED — 30 NY calendar dates at 29d23h elapsed is DUE | **ACCEPT — paired oracles, §7a** |
| R6-5 | the known-answer vector was asserted but does not exist | **ACCEPT — vectors computed and EMBEDDED, §6a** |
| R6-6 | evidence loss can launder a live conflict out of the reducer | **ACCEPT — reduce over ALL active records, §5** |

**R6-4, conceded precisely:** my control said "29d23h across a DST change — still not due", which
contradicts my own calendar-date rule: 2026-02-07 noon EST → 2026-03-09 noon EDT is 30 New York
calendar dates in 719 elapsed hours, and 30 dates is DUE. I wrote an elapsed-time intuition into a
calendar-date contract. **R6-1 and R6-5 are my two recurring classes again** (sibling-field sweep;
asserted-not-supplied) — both closed by artifact content below, not by promise.

## 0-prev5. Disposition — round 5

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
- **the effective semantic state is a REDUCER over ALL ACTIVE ASSERTION RECORDS for the key —
  never a row filter, and never filtered to currently-usable attachments (rounds 5+6):** ANY
  unresolved conflict yields `horizon=unknown` and keeps Phase C closed; **an active record whose
  evidence is absent, unretained, or hash-failed makes the key unverifiable/`unknown` — evidence
  loss can never restore an older claim.** A record leaves the reducer ONLY through the explicit
  provenance-bound adjudication mechanism, never by losing its attachment. **Supersession is a separate adjudication record**
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
a conflict · **round-6 R6-6: delete/corrupt the newer conflicting attachment and observe the old
horizon reappear · mark the challenger `unretained` and exclude it · garbage-collect evidence
before its supersession parents resolve — all three must keep Phase C closed.**

## 6. The content store: one snapshot, stage-then-publish (rounds 4-8; §rewritten live per R8-1/R8-2)

0. **ACQUIRE THE PER-SOURCE LIFECYCLE LOCK (R10-3; contract closed per round-11 R11-2/R11-4),
   held BEFORE any sweep and through staging, publish/reuse cleanup, receipt commit, and terminal
   cleanup.** The lockfile contract: a fixed name inside the private `0700` intake namespace;
   opened `O_CREAT|O_NOFOLLOW` (never `O_EXCL` — the file persists); `fstat` through the
   descriptor requires a regular file with `st_nlink == 1`, else refuse; then
   `flock(LOCK_EX|LOCK_NB)`; **after acquisition, re-verify that the lock pathname still names the
   locked inode** (`lstat(path).(dev,ino) == fstat(fd).(dev,ino)`) — mismatch releases and retries
   from open. **The lockfile is NEVER unlinked, renamed, or truncated by any conforming writer** —
   no unlink lifecycle means one stable serialization inode. `flock` locks an inode, not a
   pathname (Codex's probe held two "exclusive" locks on distinct inodes after a path swap); the
   re-verify plus never-unlink close that within the declared threat model. Staleness is governed
   ONLY by the last-reference lifecycle below — **never PID reuse or age heuristics** (round-13
   R13-2 deleted the unconditional process-death sentence that lived here beside its correction).
   **Contention is DETERMINISTIC (R11-4): `LOCK_NB` failure ⇒ an immediate named `intake_busy` —
   a CONTROL RESULT, not an attempt:** it mutates no attempt ledger, no clock, no AR, no pill, no
   drawer copy (asserted as a complete-unchanged-state control), and it appears in no state-table
   row by design — that absence is a stated invariant. No blocking mode exists in v1.
   **The lock RED is IN-MODEL only (round-12 R12-1):** the replacement/alias control is RETIRED —
   it demanded behavior the declared threat model excludes and the post-open check cannot resist
   (Codex's probe: both processes pass their checks on distinct inodes after a stable
   replacement). The controls are: two ordinary concurrent intakes serialize on the persistent
   inode (`intake_busy` for the loser, complete-unchanged-state asserted) · two overlapping
   intakes + one crash — the live run is never destroyed and the survivor converges to the ACTIVE
   MODE'S terminal invariant (options 1/2: one object + one receipt; option 3: at most one
   observation row and no provider-bearing residue) (round-17 R17-1 scoped this; it read
   unqualified one-object/one-receipt before). **Out-of-model namespace mutation is outside ALL guarantees and only
   POTENTIALLY detectable later** — v12's "detected after the fact" was overclaimed and is
   corrected here.
   **Lock lifecycle, stated truly (round-12 R12-4; boundary made enforceable per round-13
   R13-3):** `flock` releases when the LAST reference to the locked open file description closes —
   process death releases it only if no descendant inherited the descriptor. **The
   descriptor-ownership boundary:** the lock descriptor is opened **`O_CLOEXEC`**; **duplicating
   it, passing it over any socket, or leaking it to a child is forbidden**; and the enforcement
   surface is CLOSED (round-14 R14-4 — "the lock object's scope asserts" named no interception
   point): **all in-scope production code spawns processes ONLY through a single injected
   process-spawn abstraction**; that abstraction **refuses while the lifecycle lock is held**;
   and **direct spawning APIs (`os.fork`, `os.posix_spawn*`, `subprocess.*`,
   `multiprocessing.*`) are barred from the intake modules by a static import-boundary check that
   runs in the suite** — no thread-global monkey-patching, no ambient hook pretence. **The RED is
   falsifiable both ways:** calling the production abstraction while locked is REFUSED; removing
   the abstraction's lock-state check makes that call succeed and the oracle FAIL. The
   parent/fork/child probe remains only as an explanatory OS-semantics control (a seed that passes
   broken code is the named defect species).
   **The namespace bootstrap and load predicate (round-12 R12-2; identity + creation closed per
   round-13 R13-4).** **The namespace is NAMED: `app/data/footballguys/intake/`** (lockfile and
   `staging/` beneath it), **anchored at the repository root** — the trusted parent is the David-
   owned working tree, whose absolute path comes from configuration, not discovery. **Creation
   lifecycle:** the intake CREATES the chain if missing — walk from the repo-root descriptor one
   component at a time with `openat(…, O_DIRECTORY|O_NOFOLLOW)`, `mkdirat(dirfd, comp, 0700)`
   where absent, fsync the parent, re-open no-follow, and verify each component through its
   descriptor (directory, owner == intake uid, mode exactly `0700` for the intake components) —
   `O_DIRECTORY|O_NOFOLLOW` guards only a final component, so **every component of the chain is
   opened that way**; a symlinked ANCESTOR refuses, not just a symlinked leaf.
   **The per-component predicate, against the REAL tree (round-14 R14-5):** the trusted existing
   parents — the repo root, `app/`, `app/data/`, measured `0755 davidleess:staff` — are opened
   no-follow and verified for TYPE and OWNER only; **their modes are never constrained and never
   chmod'ed** (the real `0755` tree is the positive control). **Exactly these private nodes
   require mode `0700`:** `app/data/footballguys/`, `intake/`, `staging/`, and — under retention
   options 1/2 — `objects/`. **Concurrent first-run creation converges:** `mkdirat` returning
   `EEXIST` means reopen-no-follow-and-verify, never failure and never replacement; RED: two
   simultaneous missing-root creators converge to one verified namespace before ordinary lock
   contention begins.
   **THE IGNORE RULE LANDS FIRST (round-14 R14-1):** a narrow Footballguys runtime rule
   (`app/data/footballguys/` runtime content — staging, lockfile, objects, every ledger and its
   sidecars) **must be committed to `.gitignore` BEFORE the first namespace or staging write** —
   Codex's probe proved a crash-resident paid ZIP is currently commit-eligible, `0700` is no Git
   boundary (same uid), and this repo's own `.gitignore` policy requires a deliberate per-source
   rule, never a blanket vendor ignore. RED: positive `git check-ignore` controls for a staging
   ZIP, the lockfile, a canonical object, and each ledger + sidecar; a NEGATIVE control proving
   commit-intended evidence/config paths remain trackable.
   **EVERY RUNTIME LOCATION IS PINNED (round-14 R14-2; closed per round-15 R15-4):** lockfile =
   **`app/data/footballguys/intake/lifecycle.lock`**; staging dir =
   `app/data/footballguys/intake/staging/`; retained-object root = `app/data/footballguys/objects/`,
   canonical pathname = `objects/<archive_sha256>.zip` (full 64-hex, the frozen hash-to-path
   grammar); logical databases = `app/data/footballguys/receipts.db`, `semantics.db`,
   `observations.db`. **Journal mode is FROZEN: WAL for all three**, so the complete runtime SQLite
   file set per database is `<db>`, `<db>-wal`, `<db>-shm` (with `<db>-journal` ignored
   defensively though the frozen mode never creates it).
   **WAL establishment is a closed lifecycle (round-16 R16-4):** for each newly created logical
   database, `PRAGMA journal_mode=WAL` is issued and the RETURNED effective mode verified to be
   `wal` **before any schema or application write** — refusal otherwise; on reopening an existing
   database the effective mode is verified before any protected write, and an unexpected mode is a
   refusal, never a silent change. Ordering control + mutants: schema/write before WAL
   establishment → caught; requesting WAL but ignoring the returned mode → caught. `<db>-journal`
   stays ignored defensively — the no-journal claim holds only AFTER this boundary, and is stated
   that way.
   **Ignore coverage ≠ backup coverage (round-15 R15-3):** the `.gitignore` rule covers EVERY
   possible runtime companion narrowly; **backup coverage is ONE `kind="sqlite"` manifest entry
   per logical main database**, protected through the existing online-backup path
   (`sqlite3.Connection.backup()` producing one transactionally coherent snapshot) — **sidecars
   are NEVER independent backup payloads** (copying live WAL/SHM as files can restore
   inconsistently). REDs: restore the staged backup from a live-WAL source and verify committed
   rows; a file-copy mutant FAILS; a sidecar-required-on-clean-shutdown mutant FAILS.
   **WRITE MODE ≠ HISTORICAL PRESENCE (round-15 R15-1, the Critical):** retention options govern
   what may be WRITTEN next, never what history exists. In an option-3-ONLY history, `objects/`
   and `receipts.db` are never created. **A 1/2→3 transition stops new raw publishes and receipts
   while existing objects and receipts remain READ-ONLY under their existing coverage** — the
   accepted coexistence rows (an observation clock over an older retained AR) stay reachable and
   truthful; deletion is barred. **A 3→1/2 transition resumes writes only after the selected
   coverage re-verifies.** REDs: both transition directions with an older AR — no deletion, no new
   option-3 receipt/object, stable AR identity, truthful copy.
   `staging/` and `objects/` live under one filesystem, **asserted (`st_dev` equality through the
   held descriptors) BEFORE the no-replace publish**; cross-device is a refusal and a mutant.
   **COVERAGE BEFORE FIRST WRITE, restored live where the stores live (round-14 R14-3):** for
   EVERY conditional durable store — raw objects, `receipts.db` + sidecars, `semantics.db`, the
   observation ledger — **the selected backup-manifest entry or the David-granted named exception
   must already exist before the namespace code performs its first protected publish or
   transaction.** v14's claim that §6 carried this rule was a false live pointer (§8 had it only
   for observations); it is now here, with a mutant per store that attempts its first write one
   step before coverage exists and must refuse.
   **Manifest treatment of transients:** staging content is transient (not a durable store); the
   lockfile is trivial state; neither enters the backup manifest. RED: missing root created
   correctly with the exact chain semantics · symlinked ancestor refuses · symlinked leaf refuses ·
   group/world-writable and wrong-owner PRIVATE nodes refuse — all before any lifecycle
   operation.
1. **ACQUIRE STAGING IN THE MODE BRANCH (round-17 R17-1 — staging acquisition IS mode
   behavior; only lock/namespace/coverage selection is common):**
   **A1 (options 1/2):** create the LINKED staging file **exclusively and no-follow**
   (`O_CREAT|O_EXCL|O_NOFOLLOW`) under an **unpredictable name** on the same filesystem; stream
   the source within §4's caps, hash while copying, fsync. **The descriptor stays open through
   every following step until after the staged/published inode comparison** — it is the identity
   being verified, and closing it early is the round-8 contradiction this rewrite removed.
   **B1 (option 3):** create the staging entry exclusively and no-follow the same way, then
   **`unlinkat` it and DURABLY FSYNC the bound staging-directory descriptor — BEFORE the first
   provider byte streams in (R16-2)** — then stream and hash on the held **anonymous** descriptor
   within the same §4 caps. A SYSTEM crash after the fsync recovers no named provider-bearing
   inode; the create→unlink→fsync window strands at most an empty named file.
   **Call-trace oracle (R17-1; refusal-aware per round-18 R18-4): AT MOST one staging create and
   AT MOST one source stream per attempt; exactly one create for attempts that reach creation; and
   exactly one stream ONLY after the active branch's pre-stream guards succeed** — a correct B1
   create/unlink/fsync refusal performs ZERO streams, and a correct A1 create failure likewise;
   the oracle must accept those and REJECT a stream that begins after a failed durability guard.
   The A1-before-B1 mutant (two creates, one linked) still FAILS; create-, unlink-, and
   fsync-refusal traces are added.
2. **THE SHARED VALIDATION/FACT ROUTINE — one routine, called after EITHER A1 or B1, operating
   only on the held descriptor(s) (round-17 R17-1). DERIVE EVERY FACT FROM THE STAGED INODE (the
   one-snapshot boundary, R7-1/R8-1):**
   `archive_object_sha256`, member enumeration, the selected role bytes/hashes, schema checks, and
   `content_vintage_id` are all computed from the staged bytes through the held/bound
   descriptor(s). **No role, schema, archive, or vintage fact may come from an independent read of
   the mutable source pathname.** **The guarantee, stated precisely (round-9 R9-5): whatever byte
   sequence C was staged becomes the sole authoritative candidate; every signed fact describes C;
   an invalid C fails.** Stage-first earns **internal coherence**, not atomic observation of a
   concurrently mutable source — a source mutated in place mid-stream may stage a hybrid C, and if
   C is a valid archive it is a legitimate (if odd) candidate whose facts are all C's own. What can
   never happen is A's roles signed to B's archive. *(If true A-or-B atomic source capture is ever
   required, that is a separate source-snapshot mechanism with its own framing and controls.)*
   Mutant reworded to match: mutate the source during streaming — the receipt, if any, must be
   internally coherent over the staged bytes; asserting "must equal A or B" is itself the broken
   oracle.
**— TERMINAL BRANCH A (retention options 1/2 ONLY; round-16 R16-1 — steps 3–6 do not exist under
option 3) —**

3. **Publish atomically** to the canonical content path with **kernel-enforced no-replace
   semantics**; fsync the parent directory.
4. **If the canonical path already exists — the OBJECT-INTEGRITY BOUNDARY (round-4 R4-4), with the
   REUSE branch's own terminal state (round-9 R9-3):**
   - open **no-follow**, then verify through **that one descriptor**: `fstat` (regular file,
     **`st_nlink == 1`** — a multi-link object is REFUSED, because a hard-link alias is regular and
     non-symlink and can be mutated through its other name after any pathname check), size, full
     hash. No check may run on a pathname the open didn't bind — that is the validation-to-open
     race.
   - verified match → **reuse** (the legitimate dedup branch): byte equality is verified through
     the TWO bound descriptors (staged + canonical); **inode equality is NOT required on reuse** —
     they are necessarily different inodes; then — with the staging descriptor still open — the
     staging directory entry is inspected **no-follow through a bound directory descriptor**
     (`fstatat(dirfd, name, AT_SYMLINK_NOFOLLOW)`), compared to the held descriptor's
     device/inode, and on match removed via `unlinkat(dirfd, name)`; parent fsynced; descriptor
     closed; receipt commits. **STATED HONESTLY (round-11 R11-1): the final check and the unlink
     are two syscalls — POSIX has no unlink-by-descriptor, and no prose makes that window zero.**
     What closes it is the **DECLARED THREAT MODEL**: the staging/lock namespace is a private
     `0700` directory owned by the intake; all conforming writers serialize on the step-0 lock;
     **a non-cooperating process mutating the private namespace is OUTSIDE EVERY GUARANTEE and may
     only POTENTIALLY be detected later — no detection is promised** (round-13 R13-1 deleted the
     surviving stronger claim; the forbidden-phrase sweep now proves its absence). The round-10
     concurrent-rename mutant is **RETIRED as demanding semantics POSIX cannot supply** (my
     contract required an adversary my mechanism could not survive). Surviving controls:
     identity-mismatch at inspection ⇒ cleanup refuses, deletes nothing, reports the displaced
     state; in-model sequences leak no verified inode. §6 step 5's fresh-failure removal uses this
     same inspect-no-follow/`unlinkat`/refuse-on-mismatch mechanism under the same boundary.** A literal reading of v9 leaked one full paid ZIP per
     deduplicated receipt; the reuse branch now has an explicit terminal state. Control: repeated
     same-content intake yields ONE canonical object, ZERO staging files after return, and the
     correct receipt count — and an injected receipt-commit failure on reuse yields the same
     no-leak result. Mismatch or multi-link → **quarantine, fail closed, named error — never
     analysis.**
   - published objects are set read-only (0444); immutability is still never assumed from mode —
     **every downstream load reverifies bytes against the `archive_object_sha256` carried IN the
     receipt** (never against `receipt_id`, which hashes identity fields — round-6 R6-1 swept the
     stale wording here; the mutant is an implementation that follows the old sentence literally
     and must be caught by the independent valid-archive load). A later mismatch quarantines the
     object and every dependent artifact refuses.
   - publication itself is a **kernel-enforced atomic no-replace** operation; an `exists()` check
     followed by an overwriting rename is the named anti-pattern and a required mutant.
5. **FRESH branch only — before the receipt transaction, the NEWLY PUBLISHED object passes the
   SAME descriptor-bound
   invariant as the reuse branch** (R7-2): regular file, **`st_nlink == 1`**, size, full hash —
   **comparing the still-held staging descriptor's inode with the published inode**, never
   revalidating an unrelated pathname. Only after this comparison is the staging descriptor closed.
   **Failure cleanup (R8-2):** if this check finds `st_nlink != 1` or any mismatch, **no receipt
   may exist**, and the unsafe canonical name is removed/quarantined with the parent directory
   fsynced again — a failed attempt must never leave a permanently aliased canonical object
   squatting on the hash path and refusing every future dedup.
6. **Either A-branch path (fresh or reuse): commit the offering receipt LAST**, one SQLite transaction, uniqueness on `receipt_id` and
   `offering_id`, referencing the published-or-verified object. Receipt-commit failure leaves
   reported recoverable orphans; a receipt citing absent bytes stays unrepresentable.

Crash mutants required at: during staged write · between file fsync and publish · after publish
before directory fsync · on the reuse branch. **Round-7 mutants (source-swap oracle reworded per R9-5):** replace or mutate the source ZIP
mid-intake — the receipt, if any, must be internally coherent over the staged bytes C (never A's
roles on B's archive; "must equal A or B" is itself a broken oracle) · pre-plant the staging name as a symlink to a
sentinel (sentinel must be untouched, no receipt) · hard-link the fresh staged inode before
publication then mutate through the alias (no receipt, no altered canonical object) · **R8-2
cleanup control: a refused fresh publication leaves NEITHER a receipt NOR an unsafe canonical
entry — the next intake of the same content succeeds.**

**— TERMINAL BRANCH B (retention option 3; R16-1/R17-1 — no object path, no receipt transaction;
follows B1 + the shared step-2 routine) —**

**B2.** The shared routine's refusals apply; **the anonymous descriptor has exactly ONE OWNER
(round-18 R18-3): a single scoped owner whose finally-class cleanup performs THE one close on
EVERY exit after creation** — B1/fsync refusal, malformed archive, resource cap, missing role,
CRC/hash failure, schema failure, source read error, success. Two closes in prose is a
double-close in code, and a reused fd number makes `close(fd)` twice a real resource bug — so no
step outside the owner ever calls close. A long-lived process may never retain the paid inode
after a rejected intake. REDs per failure family, keeping the process ALIVE, asserting the raw
descriptor/inode is gone, no observation committed, clock/AR/copy unchanged — **plus an FD-reuse
probe asserting exactly one close of the owned descriptor**; the double-close mutant AND the
failure-cleanup-removal mutant both FAIL.
**B3.** On success: **the owner's single close executes BEFORE anything becomes visible** — B3
requests the owner's close; it does not perform an independent second one.
**B4.** Commit the **observation transaction** to `observations.db` LAST — the only
state-advancing act — under a **durable observation identity (round-18 R18-1):**
**`observation_id` = the hash of the SAME frozen acquisition-signature bytes** (§6a grammar; the
row is still never called a receipt — identity reuse, vocabulary kept). The store persists the
signed fields (source, `offering_id`, `content_vintage_id`, validated `retrieved_at`, archive
sha256+bytes, role records) so the identity is independently reproducible from the row. DB
constraints: UNIQUE(`observation_id`), UNIQUE(`offering_id`). Semantics identical to the receipt
rules: same offering + same signature ⇒ ONE idempotent row · same offering + any differing signed
field ⇒ `offering_identity_conflict`, fail closed · new offering + same content ⇒ a new
observation of the unchanged vintage. This is what makes step 0's "at most one observation row"
invariant TRUE rather than asserted — the lock serializes writers; the constraint deduplicates
sequential resubmission. REDs: two sequential identical B intakes → one row, one clock candidate ·
changed signed field under the same offering → refusal, state unchanged · append order immaterial ·
mutants removing the unique constraint or the conflict check FAIL.

**Option-3 crash/residue matrix — PERMITTED RESIDUE PER OBJECT CLASS (round-17 R17-3; "nothing on
disk" is retired — logical non-commit is not an empty filesystem):**

| Object class | Permitted residue after any B failure/crash |
| :-- | :-- |
| raw provider archive | **none named or linked, ever, after B1's fsync**; at most an EMPTY named file from B1's window, swept as an orphan |
| staging entries | as above — no provider-byte-bearing entry |
| `observations.db` + WAL/SHM | **MAY exist and MAY change physically without a committed row** — a failed WAL transaction can touch main/WAL/SHM; SQLite recovery and the governed `kind="sqlite"` backup path own that residue; the ledger reopens with NO observation row committed |
| pre-existing historical stores (1/2→3 history) | untouched, read-only, exactly as the transition rule preserves them |

Logical safety property: **no named/raw provider archive FROM THIS ATTEMPT survives (older raw
archives preserved by a 1/2→3 history are untouched, per the adjacent row) · no observation row
commits · clock/AR/copy do not advance.** REDs: inject a REAL SQLite transaction failure, reopen, assert the
logical state plus raw-archive absence; **a mock whose only oracle is directory emptiness FAILS.**
Branch-violation mutants (each must FAIL): a publish under option 3 · a receipt transaction under
option 3 · a linked provider-byte-bearing staging entry after B1 · a still-open raw descriptor at
observation commit · the directory fsync omitted or moved after the first byte (injected
filesystem oracle; a SIGKILL-only probe stays explanatory).**

**THE BRANCH-A POST-CRASH MATRIX — OPTIONS 1/2 ONLY (round-9 R9-4; scoped per round-18 R18-2 —
this heading read unqualified below Branch B, my surviving-sibling instance eleven). Each injection
point names its permitted durable residue and required restart behavior; "no receipt" alone is
never a passing oracle. No option-3 test may be parameterized with any row of this matrix or with
the one-object/one-receipt convergence oracle — that absence is itself a RED assertion:**

| Crash point | May remain on disk | Restart contract |
| :-- | :-- | :-- |
| during staged write | a partial staging file under the unpredictable name | discovered by the staging-directory sweep at next intake start — **run only under the held lifecycle lock, so a LIVE run's staging file is never swept (R10-3)**; **reported as a recoverable staging orphan and safely removed** — never parsed, never a committed offering |
| after staging fsync, before publish | a complete staging file | same sweep: reported and removed (its content re-stages from source on the next intake; a staging file is never promoted in place) |
| after publish, before parent-dir fsync | the canonical entry may or may not persist | next same-content intake re-verifies through the §6.4 descriptor-bound check and either REUSES the surviving object or republishes; **no receipt exists either way, so no state advanced** |
| receipt-commit failure — **FRESH branch** | a newly published canonical object with no referencing receipt | **reported as a recoverable canonical orphan**; adopted by the next same-content intake's reuse branch |
| receipt-commit failure — **REUSE branch** (round-10 R10-5) | **no new object and no staging residue** — the canonical object already carries its prior receipt(s) | the existing reference set remains exactly unchanged; **the healthy shared object is NEVER reported as an orphan** (a pre-existing orphan stays an orphan only if that was the starting state). Control: one object + one receipt, a second offering through reuse, receipt transaction failed → one object, one original receipt, zero staging files, no new orphan report |

**THE SWEEP CONTRACT (round-11 R11-3; evaluation ORDERED and TOTAL per round-12 R12-5):** the
staging root is the verified private `0700` dirfd (§step 0); staged names follow a frozen grammar
(`stage-<random>.tmp`); the sweep **enumerates non-recursively through the bound directory
descriptor**, and evaluates each entry in a FIXED ORDER — **grammar first: every
grammar-NONMATCHING name is reported and untouched REGARDLESS of type** (nonmatching symlinks,
multi-link files, directories, special files included — the previous per-type table applied only
after the name test, which the text left unstated, making two rows claim one entry). **Only a
grammar-MATCHING name proceeds to the no-follow type table** (`fstatat(…, AT_SYMLINK_NOFOLLOW)`;
never resolve, never recurse, never open a target): single-link regular → reported as a staging
orphan, `unlinkat(dirfd, name)` · **symlink → the LINK ITSELF `unlinkat`ed; its target never
opened, parsed, mutated, or deleted** · multi-link regular → reported and `unlinkat`ed (this name
only) · directory or special → **REFUSED and reported — never recursed, never deleted**. RED: the
matching-name probes (symlink→sentinel with sentinel byte-identical after; multi-link;
directory/special) PLUS nonmatching regular, symlink, multi-link, directory, and special entries —
all untouched.

Invariants across every row: **no receipt, freshness, or AR state advances from file existence
alone**; stale staging bytes remain inside the selected retention/manifest boundary (they are
provider content) and are never parsed as an offering; **a second clean intake converges to one
canonical object and one valid receipt with no manual pathname surgery — ALL OF THIS OPTIONS 1/2
ONLY.** Each row is a RED
crash-injection control with its residue and restart outcome asserted, not just receipt absence.**

### 6a. The object model and every hash edge (round-5 R5-5)

**The retained canonical object is the intact provider ZIP, keyed one-per-distinct
`archive_object_sha256`** — never by `content_vintage_id` (round-6 R6-2): two ZIPs can carry
byte-identical role members while differing in unselected bytes, giving **one role vintage, two
distinct archive objects**, both preserved and attributable. Cardinality frozen: N offering
receipts → 1 archive object; M archive objects → 1 `content_vintage_id`. Mutant: two ZIPs with
identical selected roles and one differing unselected byte must be preserved as distinct objects
with the unchanged role vintage reported honestly — never collapsed, never called corruption.
**Decompressed roles are regenerable views, not stored objects**: they are streamed from the
archive at read time and verified against their role records.

| Edge | Hash used | Never |
| :-- | :-- | :-- |
| receipt → canonical object | `archive_object_sha256` (the ZIP's content SHA-256, stored in the receipt) | `receipt_id` |
| role read from the archive | that role's member `sha256` from the ordered role records | archive or receipt hash |
| `content_vintage_id` | hash over the canonical ordered `(role, member_sha256, bytes)` records | archive hash alone |
| offering identity | `receipt_id` = hash of the canonical offering-signature serialization | any content hash |

**Downstream loads rehash the object against `archive_object_sha256` — never against `receipt_id`**
(the round-5 conflation: identity hashes identity fields; content hashes bytes; an implementation
comparing payload bytes to `receipt_id` rejects every valid object).

**The serialization grammar is frozen and the known-answer vectors EXIST below (round-6 R6-5),
computed by a hand-concatenating oracle that imports no production serializer** (none exists yet;
when one does, it must reproduce these bytes, not define them):

- **Grammar:** line-delimited UTF-8; each line `name=value` + LF (0x0A); fixed field order; values
  restricted to `[A-Za-z0-9_.:;=-]` with `;` only as the role-record field separator — no value can
  contain a line delimiter, so no escaping exists;
- **`content_vintage_id`** = SHA-256 over the role records in fixed role order (`adp`, then
  `identity_sidecar`), one line each: `role=<r>;sha256=<hex>;bytes=<decimal>`;
- **offering signature** = the canonical lines `source`, `offering_id`, `content_vintage_id`,
  `retrieved_at` (canonical UTC `YYYY-MM-DDTHH:MM:SSZ` — offset spellings normalize BEFORE
  serialization; **a fractional-seconds input is REFUSED at validation, never truncated or rounded
  (round-7 R7-4)** — a declared `retrieved_at` must be an exact whole-second instant, and a
  refusal advances no clock; quantizing a signed field would let two distinct instants collapse to
  one `receipt_id` and misread an identity conflict as an idempotent no-op), `archive_sha256`,
  `archive_bytes` (decimal, no padding), then the two role-record lines; **`receipt_id`** =
  SHA-256 over those bytes. Mutant: the same offering identity at two distinct subsecond instants
  within one second — both REFUSED, never collapsed.

**Positive vector — the COMPLETE canonical input bytes, reproducible from this artifact alone
(R8-3).** The `content_vintage_id` preimage is exactly these two lines (LF-terminated):

```
role=adp;sha256=1f7afcbfdd7b9c6d08dc21a0017f05d4a30fa64e0cd580c6295c5a5fc3a57eb9;bytes=30388
role=identity_sidecar;sha256=25be2d5a10f92b9787009edbb6144f516f53e4421afe5f39549b6eb6ca019c3f;bytes=260688
```

The offering-signature preimage is exactly these lines (LF-terminated):

```
source=footballguys
offering_id=fbg-offering-2026-08-05-a
content_vintage_id=201d2484e202fc456b4c3f0d901afe0d577e6b78bb66ead011a194a45516e7ab
retrieved_at=2026-08-06T00:57:00Z
archive_sha256=d8af09851ec1e4d2df20d91940def997206f9d698671fed397fd27234772a54c
archive_bytes=8540590
role=adp;sha256=1f7afcbfdd7b9c6d08dc21a0017f05d4a30fa64e0cd580c6295c5a5fc3a57eb9;bytes=30388
role=identity_sidecar;sha256=25be2d5a10f92b9787009edbb6144f516f53e4421afe5f39549b6eb6ca019c3f;bytes=260688
```

*(Declared retrieval `2026-08-05T20:57:00-04:00` normalized to the canonical `Z` form above.)*

| Quantity | Expected value |
| :-- | :-- |
| `content_vintage_id` bytes | 200 |
| **`content_vintage_id`** | `201d2484e202fc456b4c3f0d901afe0d577e6b78bb66ead011a194a45516e7ab` |
| offering-signature bytes | 478 |
| **`receipt_id`** | `0d6bf3065b2c432f64262e7de427c064eda121cb1014c20d74d1fce4e3ef596e` |

**Negative vectors — CLOSED BYTE FIXTURES (round-7 R7-5): each names its exact mutation and full
expected SHA-256; no reverse-engineering:**

| # | Exact mutation of the positive bytes | Expected SHA-256 |
| :-- | :-- | :-- |
| N1 | **line-order swap**: the two complete role-record lines exchanged (sidecar line first, each line's own data intact) | `content_vintage_id` = `86d18b7e0949cbedb64141d8ca3a934f6a2181516c0835019f98ee341c6b8605` |
| N2 | **assignment swap under the fixed role order** — the preimage becomes exactly: `role=adp;sha256=25be2d5a10f92b9787009edbb6144f516f53e4421afe5f39549b6eb6ca019c3f;bytes=260688` then `role=identity_sidecar;sha256=1f7afcbfdd7b9c6d08dc21a0017f05d4a30fa64e0cd580c6295c5a5fc3a57eb9;bytes=30388` | `content_vintage_id` = `fb6b16f63985abf2efd72b1d311217bcb8cc151c9dc58f57dfb7b8bbc6f1d86f` |
| N3 | `retrieved_at=2026-08-05T20:57:00-04:00` serialized literally instead of normalizing | `receipt_id` = `d5785e03a72b74e968b5afe8d47f06d3e84e4c93c519ab47f7334f9668bac5c8` |
| N4 | `archive_bytes=08540590` (zero-padded; padding a ROLE byte count is a different, unlisted hash) | `receipt_id` = `d87163c387735c4d9a10774d130b0b60d02886d11700f18ccc9637a04a81caf0` |

Further mutants: object bytes compared to `receipt_id` · only decompressed roles retained where the
contract requires the intact archive · delimiter-collision probe (a value containing `\n` must be
UNREPRESENTABLE, not escaped). **Round-4 R4-4 mutants:** pre-existing hard-link
alias with matching bytes, then mutation through the alias · pathname swap between validation and
open · post-receipt canonical-byte mutation (downstream load must refuse) · a "no-replace" that is
exists-then-overwrite. *(The pilot generator's never-overwrite rule is recorded as NOT reusable for
a deduplicating store; and R4-4 is the pilot's hard-link class returning one layer up — a pathname
is never an identity.)*

## 7a. The clock contract — restored IN FULL per round-5 R5-4 (no reference to retired versions)

- **Clock source:** the latest **valid** acquisition — or valid `refresh_observation` under
  retention option 3 — selected by validated declared `retrieved_at`; `recorded_at` is processing
  provenance only and never freshness.
- **Equal-instant rule (round-8 R8-4, equivalence corrected per round-9 R9-1):** distinct valid
  clock candidates sharing the same maximal whole-second `retrieved_at` collapse harmlessly ONLY
  when they are equivalent over **every state- and analysis-affecting fact**: role-defined
  analytical content (`content_vintage_id`), readiness result, retention mode, and AR effect.
  **Different `content_vintage_id` values at the maximal instant CONFLICT even when both rows say
  `ready`** — display equality is not semantic equality; wrapper-only archive differences may
  collapse only when role vintage and every downstream effect are identical.
  **The conflict is a READINESS/CONTENT conflict over a CERTAIN instant (round-10 R10-1 — Codex
  correcting its own round-9 remedy, adopted here):** every tied candidate declares the identical
  validated `retrieved_at`, so the freshness axis is EXACT — the tied instant IS the clock,
  freshness renders `current` or `due` by the ordinary rule, and the pill follows the freshness
  axis only. What conflicts is which content/readiness fact governs analysis: a non-equivalent tie
  renders the **named `same_instant_conflict`** on the READINESS axis (§7 rows 16-17), Phase C
  closed, AR held per the standing rule. `recorded_at`, row order, and append order may never
  break the tie. **Mutants:** non-equivalent tied candidates at 10 days AND at 31 days, each in
  both append orders, asserting freshness status, pill, readiness conflict, AR identity/content,
  Phase-C closure, and copy INDEPENDENTLY — the 10-day tie must show `current` with NO extra pill;
  the 31-day tie must still say `monthly refresh due`; plus acquisition-vs-observation,
  ready-vs-review_required, and two equal-second `ready` receipts with different
  `content_vintage_id` (named conflict both orders; neither content analysis-ready by
  tie-breaking).
- **Observation equivalence key (round-11 R11-5, ordered per round-12 R12-3):** identity is
  validated **BEFORE clock candidacy** — a record missing its archive sha256, byte count, or
  required provenance is an **INVALID ATTEMPT** (§7a advance predicate: advances nothing) and
  **never enters the same-instant equivalence cohort at all**; v12's "missing identity ⇒ conflict"
  made an invalid record a valid clock candidate, a contradiction with §8's own definition of a
  `refresh_observation`. For VALID candidates: analytical identity = **(archive sha256, bytes) +
  declared provenance**; same-second observations collapse only on equal identity; differing
  identity ⇒ `same_instant_conflict`. Mutants: one valid + one missing-identity observation at the
  same second, two missing-identity observations, each with and without a prior valid clock — the
  invalid records never create or move any clock; plus equal- and unequal-hash valid pairs in both
  append orders, every axis asserted.
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
- **Boundary controls (RED rows) — the DST pair corrected per round-6 R6-4** *(my v6 control wrote
  an elapsed-time intuition into a calendar-date contract; Codex computed the counterexample)*:
  29 vs 30 local calendar days · **spring-forward pair: 2026-02-07 12:00 EST → 2026-03-09 12:00 EDT
  = 30 NY calendar dates in 719 elapsed hours (29d23h) → DUE**, and any span of fewer than 30 local
  dates → NOT due regardless of elapsed duration · **fall-back complement: 30 calendar dates
  exceeding 30×24h elapsed → still DUE for the same calendar reason** · month and year boundaries ·
  same instant written as `Z` vs `-04:00` normalizing to one New York calendar date · season-flat
  probe · no-grace probe · repeated-read stability.

## 7. The reachable-state table (finding 8)

Freshness clock = latest **valid** acquisition (`retrieved_at`); attempt = newest intake attempt;
AR = `latest_analysis_ready`. Pill counts freshness states `{no_record, due, unverifiable}` only;
readiness never increments the pill (it is drawer detail — composition artifact renders both axes).

| # | Clock source | Newest attempt | AR | Status | Exact copy (banned-language-scanned) | Pill |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| 1 | none | none | none | `no_record` | `No Footballguys refresh recorded` | +1 |
| 2 | none | `failed` | none | `no_record` | `No Footballguys refresh recorded · last intake attempt failed` | +1 |
| 3 | valid, <30d | `ready` (same) | same | `current` | `Last Footballguys refresh recorded N days ago` | 0 |
| 4 | valid, <30d | `review_required` (same) | **none** | `current` | `Last … N days ago · latest recorded drop awaiting data review` | 0 |
| 5 | **any valid base clock**, <30d (acquisition OR observation) | `failed` (newer attempt) | *(from base row)* | `current` | **stage-2 composition: base row's copy** + `· newest attempted drop failed intake` | 0 |
| 6 | valid, ≥30d | `ready` (same) | same | `due` | `Last … N days ago — monthly refresh due` | +1 |
| 7 | **any valid base clock**, ≥30d (acquisition OR observation) | `failed` (newer) | *(from base row)* | `due` | **stage-2 composition: base row's copy** + `· newest attempted drop failed intake` | +1 |
| 8 | valid, <30d | `review_required` (same) | **older offering** | `current` | `Last … N days ago · latest recorded drop awaiting data review · analysis uses the <date> drop` | 0 |
| 13a | valid, ≥30d | `review_required` (same) | **none** | `due` | `Last … N days ago — monthly refresh due · latest recorded drop awaiting data review` | +1 |
| 13b | valid, ≥30d | `review_required` (same) | **older offering** | `due` | `Last … N days ago — monthly refresh due · latest recorded drop awaiting data review · analysis uses the <date> drop` | +1 |
| 9 | ledger unreadable | — | — | `unverifiable` | `Footballguys refresh record unreadable` | +1 |
| 10 | any healthy row | any | any | unchanged | unchanged — **global app-health degradation changes nothing here, and vice versa** | unchanged |
| 11 | valid observation, <30d *(option 3)* | `observation` | none | `current` | `Last Footballguys refresh recorded N days ago · latest drop metadata only — its archive was not retained` | 0 |
| 11b | valid observation, <30d | `observation` | **older retained receipt** | `current` | `Last … N days ago · latest drop metadata only — its archive was not retained · analysis uses the <date> drop` | 0 |
| 12 | valid observation, ≥30d *(option 3)* | `observation` | none | `due` | `Last … N days ago — monthly refresh due · latest drop metadata only — its archive was not retained` | +1 |
| 12b | valid observation, ≥30d | `observation` | **older retained receipt** | `due` | `Last … N days ago — monthly refresh due · latest drop metadata only — its archive was not retained · analysis uses the <date> drop` | +1 |
| 14 | none valid | newest attempt **invalid** (naive/malformed/future `retrieved_at`) | none | `unverifiable` | `Footballguys refresh time unverifiable · no valid refresh recorded` | +1 |
| 15 | **any valid base clock** (current **or** due by its own age) | newest attempt **invalid** (incl. fractional-seconds refusal) | *(from base row)* | clock's own state | **stage-2 composition: base row's copy** + `· newest attempted drop's refresh time unverifiable` | per clock state |
| 16a | tied instant <30d — **`same_instant_conflict`** (cardinality ≥ 2) | *(the tied candidates)* | **none** | `current` | `Last Footballguys refresh recorded N days ago · multiple drops at that time disagree — data review required` | 0 |
| 16b | tied instant <30d — conflict | *(tied)* | **older retained receipt** | `current` | `Last … N days ago · multiple drops at that time disagree — data review required · analysis uses the <date> drop` | 0 |
| 17a | tied instant ≥30d — conflict | *(tied)* | **none** | `due` | `Last … N days ago — monthly refresh due · multiple drops at that time disagree — data review required` | +1 |
| 17b | tied instant ≥30d — conflict | *(tied)* | **older retained receipt** | `due` | `Last … N days ago — monthly refresh due · multiple drops at that time disagree — data review required · analysis uses the <date> drop` | +1 |

**THE EVALUATOR IS AN EXPLICIT TWO-STAGE FUNCTION (round-8 R8-5):**
**Stage 1** selects the unique base row from (clock type, clock age, readiness, retention, AR) —
**the newer-attempt overlay field is EXCLUDED from this projection**, which is the rule the table's
`Newest attempt` column previously left unstated. **Stage 2** appends exactly one suffix for a
newer failed or invalid attempt. Rows 5/7/15 are stage-2 compositions over ANY valid base row —
including metadata-only observation bases — so a table-driven and a prose-driven evaluator now
compute the same function.
**Referents are split so no phrase names two records (R8-5):** base-row copy speaks of the
**recorded drop** (`latest recorded drop awaiting data review`); overlay suffixes speak of the
**newest attempted drop** (`newest attempted drop failed intake` · `newest attempted drop's refresh
time unverifiable` — including a fractional-seconds refusal, which is one of the invalid-attempt
forms). The former "latest drop"-for-both wording is retired.

**Overlay composition is the general rule (round-6 R6-3 + round-7 R7-3):** a newer FAILED or
INVALID attempt is an OVERLAY over exactly one uniquely selected base row (the clock's full
readiness/retention state — ready, review-required, older-AR, or metadata-only observation), whose
copy it preserves in full and extends with the failure fact exactly once. A transport failure never
erases the truth that the clock is review-required, metadata-only, or backed by an older
analysis-ready drop. **R7-3 mutants:** current review-required clock + older AR + newer failed
attempt (copy must carry BOTH base facts + the failure) · current metadata-only observation + older
AR + newer failed attempt (likewise).

**The table is a FUNCTION (round-6 R6-3): predicates are pairwise disjoint** — every
review-required row is split by AR none vs older, row 15 composes over exactly one base row, and
the first-match mutant (an evaluator whose row order silently selects the less-informative copy)
must be caught.

**Observation-copy referent rule (round-16 R16-3):** every observation row's copy names its exact
referent — **`latest drop metadata only — its archive was not retained`** speaks of the LATEST
recorded drop's archive, never the source's whole history, so the coexistence rows may truthfully
disclose retained older analysis in the same sentence. Tested for option-3-only AND 1/2→3
histories, including stage-2 failed/invalid overlays; **a copy oracle that checks only a substring
must FAIL** — full-string assertions per row.

**`same_instant_conflict` precedence (rounds 9-10) — stage-1 base rows like any other:** the tied
instant IS the clock — freshness exact, `current`/`due` by the ordinary rule, pill freshness-only
(R10-1); while the conflict stands, **AR holds at the last unambiguous value**, no tied candidate
advances it, **and the copy discloses the older AR drop's date whenever one exists** (rows
16b/17b — R10-2: a preserved fact the copy hides is the hidden-second-axis defect again); **an
older unambiguous instant never governs freshness while a newer tied instant exists** (the tie is
the maximal clock; falling back would let ordering pick data); **newer failed/invalid attempts
compose over the conflict rows** via stage 2; **a strictly LATER unique valid candidate clears the
conflict** (the tied instant stays recorded history); query order changes nothing. Controls: two
and three tied candidates · 10-day and 31-day ties in both orders, every axis asserted
independently · older ready R + two tied non-equivalent candidates → AR remains R and the copy
states R's date, under current AND due, with and without failed/invalid overlays · a newer failed
attempt over the conflict · a later unique valid acquisition clearing it.

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

**PLEASE REPLY with: (a) CLEAR on Phase A framing v19 with checks run, OR (b) numbered findings.**
No RED opens; §8's David gate survives any CLEAR.
