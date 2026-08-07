# PlayerProfiler `player_season` observed-change pilot (N6) — protocol v3

**Author:** Claude Code, implementing lane · **Layer:** Layer 1 (ingest) inventory
**Supersedes:** v2 (`f3fa28b1…`, NOT CLEAR on R1–R5) · v1 (NOT CLEAR on P1–P8)
**Carries forward from v2 unchanged, and independently passed at v2:** N6 scope · the run-not-asserted
route inventory · the burden choice left to David · the no-closure ceiling · production isolation.

**AUTHORIZES NOTHING.** No catalog edit, checkbox movement, provider call, data access, production
ingest, capture, export request to David, landing, commit, or push. **Both A-C source clocks remain
OPEN; three Sleeper source-publish fields are open per the branch-(b) ruling.**

**⛔ THIS PROTOCOL IS NOT RUNNABLE AS WRITTEN.** §4.1 names a code prerequisite that does not exist and
that this document does not authorize. See §4.1 before planning any execution.

---

## 0. What this is, and the ceiling no execution can exceed

A **three-observation off-season pilot** producing a **bounded observed-change series** for the
PlayerProfiler `player_season` report (**N6**).

**It does NOT close the catalog's source-publish cadence field, and no execution of it can.** Manual
retrieval observes **endpoint state at our retrieval times**, never publication. `pp_player_season`
carries no `published`/`updated`/`modified` column and the ledger records **our** ingest time. On
today's sanctioned capability **no identified route closes N1–N8**. The pilot's value is
**descriptive**.

**N1–N8 stays open even on a perfect execution:** `medical_history`, `roster_week` and `pbp` each need
their own series; N7/N8 are derived identity/capture state, not provider publication clocks.

---

## 1. Route inventory — the scan was RUN, and its hits are disclosed (P1)

**As of `fd260d4`, no tracked executable PlayerProfiler HTTP route exists.** Both legacy routes —
`scripts/probe_playerprofiler.py` and `scripts/enrich_training_data.py` (which carried `PPClient`
*and* published `prospects_with_outcomes_v2.csv`) — were retired under Codex's RED and GREEN CLEAR.

**Scope, stated because a negative claim is only as wide as its search:** every tracked `.py`
mentioning `playerprofiler`/`PlayerProfiler`, tested for `httpx|requests.|urllib|aiohttp`, plus a
whole-repo scan for `admin-ajax|playerprofiler.com`. **Not** a `playerprofiler*` glob — that narrow
glob is what missed `enrich_training_data.py` (P1).

**Four files hit; none is a live route:**

| File | Why it hit | Classification |
| :-- | :-- | :-- |
| `nflverse_usage.py` | `:207`, `:261` prose citing "the same PlayerProfiler discipline" | **nflverse's** HTTP |
| `sources/source_registry.py` | `:142` prose note *"Shadow API: POST wp-admin/admin-ajax.php."* | a string in a note is not a caller |
| `test_legacy_enrichment_route_retirement_red.py` | references the endpoint **to assert its absence** | the control itself |
| `playerprofiler.py` | names the endpoint in prose | **contains NO HTTP client** — all four libraries absent |

**Governed surface:** `scripts/run_playerprofiler_ingest.py` → `src/dynasty_genius/playerprofiler.py`
→ `app/data/playerprofiler.db` (`pp_player_season` **5,476 rows**; ledger `pp_capture` **57 rows**).

**Bounded:** current tree, today's sanctioned capability. **Not** proof a future sanctioned route is
impossible. None is proposed here.

---

## 2. Authority (P2)

David's *"ok do it"* authorizes **this bounded protocol work within the manual-export shape**. It does
not authorize an HTTP fetcher, and — see §4.1 — **it does not authorize the code change this protocol
now depends on.**

The dependency is human input: each observation requires David to export. The next action is a
**concrete export request**, **drafted in §8 and deliberately not sent**.

---

## 3. The observation unit (P4)

**An observation = ONE COMPLETE `player_season` REPORT BATCH** against a manifest declared **before**
collection. Not "three exports."

**Measured grain:** `pp_player_season` spans **9 distinct seasons × 4 distinct positions** — up to
**36 position-season blocks**. `read_export` identifies season and position **from CONTENT, never the
filename** (`playerprofiler.py:226`); a guard for renamed folders and changed filenames exists at
`:623-628`. Three arbitrary files are therefore not three observations of the same thing.

**Declared before the first export, identical at every observation:** report configuration and
filters · exact season set · exact position set · expected block list · completeness rule · missing-
block treatment.

**⚠ BURDEN IS DAVID'S CALL AND I RECOMMEND NEITHER.** Option 2 (adopted here) makes each observation
**the full report** and yields a conclusion about the stream. Option 1 is **one pinned position-season
slice** — far cheaper, conclusion **scoped to that slice only**. Presented in §8.

---

## 4. The instrument

### 4.1 ⛔ CORRECTION TO v2, AND A HARD PREREQUISITE (R1)

**v2 claimed the pilot "does not invent a change detector; it reads the governed one." That was
wrong, and I verified the correction before accepting it.**

The digest's *properties* are as v2 described — `apply_block` (`playerprofiler.py:485-497`) computes

```
sha256("\n".join(sorted(json.dumps(row, sort_keys=True, default=str) for row in rows)))
```

a canonicalized, **order-independent** semantic digest over normalized block rows, immune to row
order, line endings, quoting and column order.

**But it is not an instrument the pilot can use.** Measured: `rg "def .*digest"` over the module
returns **nothing** — there is **no digest function at all**. The computation is **inline inside
`apply_block`**, which **mutates SQLite** and **returns only a status string**. So the pilot could
only obtain a digest by *mutating the production store* — which §4.2 forbids — or by **copying the
formula, which is a parallel hasher** and exactly what v2 said it would avoid.

**PREREQUISITE, pinned as the preferred option:** a **pure, versioned
`semantic_block_digest(rows) -> str` helper**, reused by **both** `apply_block` and the pilot, so one
definition serves both and neither drifts. *(Alternative considered and not preferred: a governed
private scratch DB or root route — it re-introduces a mutation path for a read-only need.)*

**⛔ THAT IS A CODE CHANGE. It is NOT authorized by this protocol, needs its own authorization and
RED/GREEN review, and until it lands THE PILOT CANNOT RUN.** No part of this document may be read as
permission to write it.

### 4.2 Production isolation — and a correction to my own v2 finding (R5)

**Correct and unchanged:** on a changed block `apply_block` does `DELETE FROM {table} WHERE block = ?`
and re-inserts, and `pp_capture` holds **one row per `stream_key` with no history**. **The
current-state DB therefore cannot be authoritative history**, and nothing is ingested into the
production store on the pilot's account.

**⚠ MY v2 CLAIM WAS TOO STRONG.** v2 said an overwrite would "leave no way to recompute observation
1's digest." **Not so, provided the raw bytes are retained (§5):** the digest is recomputable from the
retained raw export. **The defect is that the production DB cannot serve as the record — not that
recomputation becomes impossible.** *(Same class as the overclaims Codex has been correcting all
session: a true finding carrying a stronger consequence than it earns.)*

### 4.3 Provenance — HEAD is NOT parser provenance (R2)

**v2 recorded the HEAD commit SHA. That is the wrong instrument**, for two independent reasons:
**unrelated commits false-invalidate** an interval (HEAD moves when the parser did not), and **dirty
working-tree parser edits evade it entirely** (parser changes while HEAD does not).

**Worse, and verified:** the digest covers normalized rows that include `dg_player_id`,
`identity_status` and `identity_candidates` (`:670-672`), resolved via
`NameIdentityIndex.from_governed_crosswalk` (`:179`, `:202`) from
`GOVERNED_CROSSWALK = app/data/identity/_runs/ff_playerids_20260516.json` (`:72-74`). **A crosswalk
change moves the digest with no source change whatsoever.**

**Recorded per observation, all three:**

| Field | Why |
| :-- | :-- |
| **module-file SHA-256** of `playerprofiler.py` | actual parser bytes, immune to both HEAD failure modes |
| **crosswalk file SHA-256** | the identity inputs the digest demonstrably depends on |
| **named digest / canonicalization version** | so a deliberate formula change is declared, not inferred |

**Any mismatch in any of the three across an interval ⇒ `incomparable`.** HEAD may be recorded as
**audit context only** and never as the provenance test.

### 4.4 Per-observation manifest

UTC observation time · report/filter identity · **the §4.3 provenance triple** · expected vs observed
block list · **file → block mapping** · file count · byte count · row count per block · column/header
hash · **raw SHA-256 per file** · **semantic digest per block** · explicit schema/coverage result
evaluated **BEFORE** any content comparison.

### 4.5 Interval precedence and 36-block aggregation (R3)

**Evaluated strictly in this order; the first matching rule wins:**

1. **`incomparable`** — any endpoint of the interval is invalid, incomplete or unavailable; **or** any
   mismatch in report/filter identity, schema, or the §4.3 provenance triple.
2. **`changed`** — otherwise, **any** expected block differs by **semantic digest**.
3. **`unchanged`** — otherwise, **all** expected blocks are equal.

**Two explicit compatibility rules:**

- **Column reorder is NOT a change.** The digest sorts keys within each row and sorts rows, so column
  and row order cannot move it.
- **A raw-SHA-only difference is NOT `changed`.** Differing raw bytes with identical semantic digests
  is a **representation** change and is recorded as such, never promoted to `changed`.

**A missing or partial block reads `incomplete`/`unavailable` ⇒ rule 1 — never `changed`.**

### 4.6 The append-only pilot record (R5)

| Property | Requirement |
| :-- | :-- |
| Location | one named path **outside** `app/data/playerprofiler.db`, declared before collection |
| Shape | **create-only and immutable** — an observation is never edited or deleted once written |
| Identity | a **unique observation ID** per observation |
| Write | **atomic** (write-temp-then-rename), so a crash cannot leave a half-observation |
| Content | the complete §4.4 manifest, including the file→block mapping |
| Relation to raw | records **where** the raw bytes are retained and under which §5 disposition |

---

## 5. Retention of private raw evidence (P6, corrected by R4)

**⚠ R4 IS CODEX CORRECTING ITS OWN P6 WORDING, AND IT MATTERS: historical export bytes are NOT
regenerable.** A subscriber export is a point-in-time artifact; last week's cannot be re-downloaded.
v2 inherited the word "regenerable" and repeats an error at David's expense. **Withdrawn.**

| Item | Requirement |
| :-- | :-- |
| Location | one named private local path, declared before collection |
| **Access** | David owns the bytes. **Local agent read + hash + coverage processing is REQUIRED for the pilot to function and is hereby stated explicitly** *(v2 said "David only; no agent copies raw subscriber rows", which contradicted a protocol whose whole instrument is me hashing them — the resolution is: agents may **read and hash in place**; agents never **copy, excerpt, or transport** subscriber rows)* |
| Duration | exact delivered bytes retained at least until the pilot is reviewed and closed |
| **In Git** | **NEVER.** No subscriber rows in any commit, artifact, ledger or review packet — hashes and counts only |

**⚠ DECISION FOR DAVID — stated with the real consequence, not the softened one:**

> **Backup-covered, or single-copy and non-recoverable?**
> Covering places **subscriber data into the offsite backup manifest** — his ruling, engaging the
> manifest-coverage law. **Not** covering means a single local copy whose loss is **permanent**: the
> export cannot be regenerated, so **replayability of the affected observation is lost forever** and
> the interval becomes permanently `incomparable`.

---

## 6. Shape and outputs (P7)

**Three observations → two intervals. Weekly. Off-season.**

Weekly is an **operational choice** balancing burden against informativeness. **It is not derived from
source evidence** and nothing here claims it is.

**Valid per-interval outputs, pre-stated:** `changed` · `unchanged` · `incomparable` (§4.5).

**No sample-count pass criterion.** Two intervals cannot infer a recurring cadence, and **no number of
intervals converts observed change into source-publish cadence** (§0). Any recurring-rhythm question
afterwards is a separate, burden-aware decision for David.

**Ceilings:** an `unchanged` interval is **weak and non-diagnostic** at this sample size · nothing
finer than the sampling interval is detectable · the window is **entirely off-season** · results cover
**`player_season` only**.

---

## 7. Execution preconditions — all must hold before observation 1

1. **§4.1's `semantic_block_digest` helper exists**, separately authorized and RED/GREEN reviewed.
2. **This protocol is CLEAR.**
3. **David has answered §8's two questions.**
4. The §4.6 record location and §5 retention path are declared and created.

**Until all four hold, no export is requested and no observation is taken.**

---

## 8. The export request — DRAFTED, NOT SENT

Two questions must reach David **before** any export, because each changes what he produces and what
becomes of it:

1. **Burden (§3):** full report batch per observation — conclusion about the stream — **or** one
   pinned position-season slice, cheaper, conclusion scoped to that slice?
2. **Retention (§5):** backup-covered, or single-copy and non-recoverable with permanent loss of
   replayability accepted?

Once answered *and* §7 is satisfied, the request is mechanical: export the same configuration three
times, one week apart, into three distinct folders, and tell me where they are.

---

## 9. Boundaries

1. **No source-publish closure.** N1–N8 stays OPEN regardless of outcome; no §1 checkbox moves.
2. **No automated provider route** proposed, revived, or implied.
3. **No production ingest** on the pilot's account.
4. **No code written** — §4.1's helper is named as a prerequisite, not authorized.
5. **No catalog edit**, including the three Sleeper fields the ruling opened.
6. **No export request** until §7's preconditions hold.

**H2 QB rushing remains a registered hypothesis UNDER TEST with no result.**
