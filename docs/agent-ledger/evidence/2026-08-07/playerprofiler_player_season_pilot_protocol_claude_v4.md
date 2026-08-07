# PlayerProfiler `player_season` observed-change pilot (N6) — protocol v4

**Author:** Claude Code, implementing lane · **Layer:** Layer 1 (ingest) inventory
**Supersedes:** v3 (`721a98d7…`, NOT CLEAR on T1–T4) · v2 · v1
**Independently passed and carried forward unchanged:** N6 scope · run-not-asserted route inventory ·
burden left to David · the no-closure ceiling · production isolation · the hard-stop framing, which
Codex directed must remain.

**AUTHORIZES NOTHING.** No catalog edit, checkbox, provider call, data access, production ingest,
capture, export request to David, code, landing, commit, or push. **Both A-C source clocks remain
OPEN; three Sleeper source-publish fields are open per the branch-(b) ruling.**

> # ⛔ NOT RUNNABLE. AND THE PREREQUISITE IS BIGGER THAN v3 SAID.
> §4.1 names a **code prerequisite that does not exist**, that this document does **not** authorize,
> and that **expanded materially at T1** — from one pure digest helper to a **shared normalization
> extraction plus the digest**, with RED/GREEN proving byte-identical rows. **Nothing here is
> permission to write it.** Reported to David as a scope expansion at the moment it happened, per the
> standing obligation not to absorb an expanding gate silently.

---

## 0. What this is, and the ceiling no execution can exceed

A **three-observation off-season pilot** producing a **bounded observed-change series** for the
PlayerProfiler `player_season` report (**N6**).

**It does NOT close the catalog's source-publish cadence field, and no execution can.** Manual
retrieval observes **endpoint state at our retrieval times**, never publication. `pp_player_season`
has no `published`/`updated`/`modified` column; the ledger records **our** ingest time. On today's
sanctioned capability **no identified route closes N1–N8**. The pilot is **descriptive**.

**N1–N8 stays open on a perfect execution:** `medical_history`, `roster_week`, `pbp` need their own
series; N7/N8 are derived identity/capture state, not provider publication clocks.

---

## 1. Route inventory — scan RUN, hits disclosed (P1)

**As of `fd260d4`, no tracked executable PlayerProfiler HTTP route exists.** Both legacy routes —
`scripts/probe_playerprofiler.py` and `scripts/enrich_training_data.py` (which carried `PPClient`
*and* published `prospects_with_outcomes_v2.csv`) — were retired under Codex's RED and GREEN CLEAR.

**Scope:** every tracked `.py` mentioning `playerprofiler`/`PlayerProfiler`, tested for
`httpx|requests.|urllib|aiohttp`, plus a whole-repo scan for `admin-ajax|playerprofiler.com`. **Not** a
`playerprofiler*` glob — that glob is what missed `enrich_training_data.py` (P1).

**Four hits; none is a live route:** `nflverse_usage.py` `:207`/`:261` (prose; **nflverse's** HTTP) ·
`sources/source_registry.py` `:142` (prose note *"Shadow API: POST wp-admin/admin-ajax.php."* — a
string in a note is not a caller) · `test_legacy_enrichment_route_retirement_red.py` (references the
endpoint **to assert absence**) · `playerprofiler.py` (names it in prose; **contains NO HTTP client**).

**Governed surface:** `scripts/run_playerprofiler_ingest.py` → `src/dynasty_genius/playerprofiler.py`
→ `app/data/playerprofiler.db` (`pp_player_season` **5,476 rows**; ledger `pp_capture` **57 rows**).

**Bounded:** current tree, today's capability. Not proof a future sanctioned route is impossible; none
is proposed.

---

## 2. Authority (P2)

David's *"ok do it"* authorizes **this bounded protocol work within the manual-export shape**. It does
not authorize an HTTP fetcher, and **it does not authorize §4.1's code work.**

Human input is the dependency: each observation requires David to export. The next action is a
**concrete export request**, **drafted in §8 and deliberately not sent**.

---

## 3. The observation unit (P4)

**An observation = ONE COMPLETE `player_season` REPORT BATCH** against a manifest declared **before**
collection.

**Measured grain:** `pp_player_season` spans **9 seasons × 4 positions** — up to **36 position-season
blocks**. `read_export` (`:240`) derives season and position **from CONTENT, never the filename**
(block derivation `:254-265`), because filenames are download-order artifacts. Three arbitrary files
are not three observations of the same thing.

**Declared before the first export, identical at every observation:** report configuration and
filters · exact season set · exact position set · expected block list · completeness rule ·
missing-block treatment.

**⚠ BURDEN IS DAVID'S CALL; I RECOMMEND NEITHER.** Option 2 (adopted) = full report per observation,
conclusion about the stream. Option 1 = one pinned position-season slice, far cheaper, conclusion
**scoped to that slice only**. Presented in §8.

---

## 4. The instrument

### 4.1 ⛔ THE PREREQUISITE — EXPANDED AT T1, AND STILL NOT AUTHORIZED

**v3 said one pure `semantic_block_digest(rows)` helper would suffice. That was wrong, and T1 is
correct: it solves only half the problem.**

**Verified at `playerprofiler.py:630-674`** — everything that turns exported files into
production-equivalent normalized rows is **inline in one function, exposed nowhere**:

| Step | Evidence |
| :-- | :-- |
| export discovery | `discover_exports(export_paths)` `:630` |
| schema + duplicate-block checks | `:632-634` |
| identity enrichment | `NameIdentityIndex.from_governed_crosswalk()` `:637`, `identity.resolve(...)` `:656`, `:663` |
| column slugging | `_slug(c)` `:641`, `:644`; `{_slug(k): v ...}` `:670` |
| block derivation | `f"{row['position']}-{row['season']}"` `:654` |
| row-key construction | `f"player_season\|{block}\|{_norm_no_suffix(name)}"` `:657` |
| **cross-export dedup** | `seen: set[str]` `:651`, `:667-669` |
| block grouping | `by_block[(export.stream, block)]` `:674` |

**A digest helper is useless without `rows`, and producing `rows` requires all of the above.**

**⚠ AND ONE PROPERTY THAT MAKES THIS SHARPER THAN T1 STATES:** the `seen` dedup is
**order-dependent across exports** — first occurrence wins, and it spans **all exports and both
streams in a single pass**. So a pure helper must **preserve `discover_exports` ordering and the
cross-export dedup semantics**, or it will silently produce a different surviving row than production
did, and the digests will diverge for a reason that has nothing to do with the source.

**PREREQUISITE, as T1 specifies:** a **shared pure `prepare_player_season_blocks` helper (or
equivalent read-only manifest builder)** reused by **both** production and the pilot, **plus** the
shared versioned digest. **RED/GREEN must prove byte-identical normalized rows and digests, including
identity resolution, dedup outcome, and block grouping.**

**⛔ THIS IS A CODE CHANGE, IT IS NOT AUTHORIZED HERE, AND IT IS LARGER THAN v3 IMPLIED.** Until it
lands, **the pilot cannot run**. No part of this document is permission to write it.

### 4.2 Production isolation (R5, with my v2 overclaim corrected)

On a changed block, `apply_block` (`:441-468`) does `DELETE FROM {table} WHERE block = ?` and
re-inserts; `pp_capture` holds **one row per `stream_key`, no history**. **The current-state DB cannot
be authoritative history**, and nothing is ingested into the production store on the pilot's account.

**My v2 claim that an overwrite would "leave no way to recompute observation 1's digest" was too
strong** — with raw bytes retained (§5) the digest **is** recomputable. The defect is narrower: the DB
cannot serve as the record.

### 4.3 Provenance — HEAD is NOT parser provenance (R2)

HEAD fails two ways: **unrelated commits false-invalidate** an interval, and **dirty working-tree
parser edits evade it**. And the digest covers rows carrying `dg_player_id`, `identity_status`,
`identity_candidates` (`:670-672`) resolved from
`GOVERNED_CROSSWALK = app/data/identity/_runs/ff_playerids_20260516.json` (`:72-74`) — **a crosswalk
change moves the digest with no source change.**

**Recorded per observation:** **module-file SHA-256** of `playerprofiler.py` · **crosswalk file
SHA-256** · **named digest/canonicalization version**. **Any mismatch across an interval ⇒
`incomparable`.** HEAD is **audit context only**.

### 4.4 Per-observation manifest

UTC observation time · report/filter identity · the §4.3 provenance triple · expected vs observed
block list · **file → block mapping** · file count · byte count · row count per block · **canonical
schema identity** (§4.5) · **raw SHA-256 per file** · **semantic digest per block** · explicit
schema/coverage result evaluated **BEFORE** any content comparison.

### 4.5 Schema identity, interval precedence, and 36-block aggregation (R3 + T2)

**Schema identity is an ORDER-INSENSITIVE CANONICAL COLUMN-NAME SET** (T2). Concretely: the sorted set
of `_slug`-normalized column names per block.

*(This must be defined here rather than inherited: `check_player_season_schema` signs schemas with
`sha256("|".join(e.columns))` at `:311`, which is **order-SENSITIVE** and would classify a pure
reorder as a schema difference — contradicting the reorder rule below.)*

| Condition | Result |
| :-- | :-- |
| column **reorder only** | **comparable**; representation-only, **not** `changed` |
| column **added / removed / renamed / duplicated** | **`incomparable`** |

**Interval precedence — strict first match wins:**

1. **`incomparable`** — any endpoint invalid, **detectably** incomplete, or unavailable; **or** any
   mismatch in report/filter identity, **canonical schema identity**, or the §4.3 provenance triple.
2. **`changed`** — otherwise, **any** expected block differs by **semantic digest**.
3. **`unchanged`** — otherwise, **all** expected blocks are equal.

**A raw-SHA-only difference with identical semantic digests is a REPRESENTATION change**, recorded as
such and **never promoted to `changed`**.

### 4.6 ⚠ Completeness — the detection contract, and a threat I cannot mitigate (T3)

**What IS detectable:** a missing block (exact expected-block list) · a malformed file (parse/schema)
· a changed canonical schema identity. **These ⇒ `incomparable` via rule 1.**

**What is NOT detectable, stated plainly rather than papered over:** a **silently truncated** export
that parses cleanly and carries a plausible row count. **A row-count change alone CANNOT distinguish
truncation from real source change**, and this protocol has **no independent completeness evidence**
for `player_season` — no provider-declared row count, no total to reconcile against.

**Therefore:** completeness classification is **narrowed to detectably incomplete inputs**, and
**silent truncation is disclosed as an UNMITIGATED VALIDITY THREAT to every `changed` verdict.** A
`changed` result means *the compared representations differed* — it does **not** exclude truncation as
the cause. **Row count is recorded as evidence, never as a classifier.**

*(This is a real weakness of the pilot and it is stated in the protocol rather than discovered in the
result. It is another reason §0's ceiling holds.)*

### 4.7 The append-only pilot record (R5)

One named path **outside** `app/data/playerprofiler.db`, declared before collection · **create-only
and immutable** · **unique observation ID** · **atomic** write-temp-then-rename · the complete §4.4
manifest including file→block mapping · and a record of **where** the raw bytes are retained under
which §5 disposition.

---

## 5. Retention of private raw evidence (P6, corrected by R4)

**Historical export bytes are NOT regenerable** — a subscriber export is point-in-time; last week's
cannot be re-downloaded. *(v2 inherited the word "regenerable" from P6; Codex corrected its own
wording at R4 and the error is withdrawn.)*

| Item | Requirement |
| :-- | :-- |
| Location | one named private local path, declared before collection |
| **Access** | David owns the bytes. **Local agent read + hash + coverage processing in place is REQUIRED for the instrument to function.** Agents **read and hash in place**; agents **never copy, excerpt, or transport** subscriber rows |
| Duration | exact delivered bytes retained at least until the pilot is reviewed and closed |
| **In Git** | **NEVER** — hashes and counts only |

**⚠ DECISION FOR DAVID, with the real consequence:**

> **Backup-covered, or single-copy and non-recoverable?**
> Covering places **subscriber data into the offsite backup manifest** — his ruling, engaging the
> manifest-coverage law. **Not** covering means a single local copy whose loss is **permanent**: the
> export cannot be regenerated, **replayability of that observation is lost forever**, and its
> intervals become permanently `incomparable`.

---

## 6. Shape and outputs (P7)

**Three observations → two intervals. Weekly. Off-season.** Weekly is an **operational choice**
balancing burden against informativeness — **not derived from source evidence**, and nothing here
claims it is.

**Valid per-interval outputs:** `changed` · `unchanged` · `incomparable` (§4.5).

**No sample-count pass criterion.** Two intervals cannot infer a recurring cadence, and **no number of
intervals converts observed change into source-publish cadence** (§0).

**Ceilings:** `unchanged` is **weak and non-diagnostic** at this sample size · nothing finer than the
sampling interval is detectable · the window is **entirely off-season** · results cover
**`player_season` only** · **every `changed` carries §4.6's unmitigated truncation threat.**

---

## 7. Execution preconditions — ALL must hold before observation 1

1. **§4.1's shared normalization helper AND shared digest exist**, separately authorized, with
   RED/GREEN proving byte-identical rows and digests including identity, dedup and grouping.
2. **This protocol is CLEAR.**
3. **David has answered §8's two questions.**
4. §4.7's record location and §5's retention path are declared and created.

**Until all four hold, no export is requested and no observation is taken.**

---

## 8. The export request — DRAFTED, NOT SENT

1. **Burden (§3):** full report batch per observation — conclusion about the stream — **or** one
   pinned position-season slice, cheaper, conclusion scoped to that slice?
2. **Retention (§5):** backup-covered, or single-copy and non-recoverable with permanent loss of
   replayability accepted?

Once answered **and** §7 is satisfied, the request is mechanical: export the same configuration three
times, one week apart, into three distinct folders, and tell me where they are.

---

## 9. Boundaries

1. **No source-publish closure.** N1–N8 stays OPEN; no §1 checkbox moves.
2. **No automated provider route** proposed, revived, or implied.
3. **No production ingest** on the pilot's account.
4. **No code written.** §4.1 is a named prerequisite, not an authorization — and it grew at T1.
5. **No catalog edit**, including the three Sleeper fields the ruling opened.
6. **No export request** until §7 holds.

**H2 QB rushing remains a registered hypothesis UNDER TEST with no result.**
