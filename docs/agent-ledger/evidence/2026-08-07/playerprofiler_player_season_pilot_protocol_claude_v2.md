# PlayerProfiler `player_season` observed-change pilot (N6) — protocol v2

**Author:** Claude Code, implementing lane · **Layer:** Layer 1 (ingest) inventory
**Supersedes:** `playerprofiler_cadence_protocol_claude_v1.md` (NOT CLEAR, P1–P8)
**Authored under:** Codex CLEAR of the P1–P8 disposition
(`playerprofiler_protocol_disposition_claude_v2.md`, `db681a91…`) and its explicit authorization to
author v2. **That authorization covers authorship only.**

**AUTHORIZES NOTHING.** No catalog edit, checkbox movement, provider call, capture, export request to
David, landing, commit, or push follows from this document. **Protocol v2 requires review before any
export ask.** Both A-C source clocks remain OPEN; three Sleeper source-publish fields are open per the
branch-(b) ruling.

---

## 0. What this is, and the ceiling it cannot exceed

A **three-observation off-season pilot** producing a **bounded observed-change series** for the
PlayerProfiler `player_season` report (**N6**).

**It does NOT close the catalog's source-publish cadence field, and no execution of it can.** Manual
retrieval observes **endpoint state at our retrieval times**; it never observes publication. The
`pp_player_season` schema carries no `published`/`updated`/`modified` column, and the capture ledger
records **our** ingest time. **On today's sanctioned capability no identified route closes N1–N8**
(P3, and the Q3 repair). The pilot's value is **descriptive**.

**N1–N8 remains open even if this executes perfectly** (P8): `medical_history`, `roster_week` and
`pbp` each need their own series, and N7/N8 are derived identity/capture state, not additional
provider publication clocks.

---

## 1. Route inventory — whole-repo, stated with its scope (P1)

**As of `fd260d4`, no tracked executable PlayerProfiler HTTP route exists in the repository.** Both
legacy routes — `scripts/probe_playerprofiler.py` and `scripts/enrich_training_data.py` (which
carried `PPClient` *and* published `prospects_with_outcomes_v2.csv`) — were retired under Codex's RED
and GREEN CLEAR.

**The scan was RUN, not asserted, and its hits are disclosed rather than summarized to zero.**
Scope: every tracked `.py` mentioning `playerprofiler`/`PlayerProfiler`, tested for
`httpx|requests.|urllib|aiohttp`; plus a whole-repo scan for the shadow endpoint
(`admin-ajax|playerprofiler.com`). **Not** a `playerprofiler*` glob — that narrow glob is precisely
what missed `enrich_training_data.py` originally (P1).

**Four files hit. None is a live PlayerProfiler HTTP route:**

| File | Why it hit | Classification |
| :-- | :-- | :-- |
| `src/dynasty_genius/nflverse_usage.py` | `:207`, `:261` — prose comments citing "the same PlayerProfiler discipline" and its `NA` token | **nflverse's** HTTP, not PP's |
| `src/dynasty_genius/sources/source_registry.py` | `:126`, `:134`, `:142` — registry declaration; `:142` is a prose note reading *"Shadow API: POST wp-admin/admin-ajax.php."* | **a string in a registry note is not a caller** |
| `tests/contract/test_legacy_enrichment_route_retirement_red.py` | Codex's RED, which references the endpoint as a string **to assert its absence** | the control itself |
| `src/dynasty_genius/playerprofiler.py` | names the endpoint in prose | **contains NO HTTP client** — `httpx`/`requests`/`urllib`/`aiohttp` all absent |

*(The last row is the module whose docstring tripped Codex's no-provider-route control this morning:
the control reads string constants, and it worked as designed.)*

**The governed production surface is manual-file ingestion:**

| Component | Path |
| :-- | :-- |
| Entrypoint | `scripts/run_playerprofiler_ingest.py` |
| Module | `src/dynasty_genius/playerprofiler.py` |
| Store | `app/data/playerprofiler.db` → `pp_player_season` (**5,476 rows**), ledger `pp_capture` (**57 rows**) |

**Bounded:** this describes the current tree and today's sanctioned capability. It is **not** proof
that a future sanctioned automated route is impossible; automation remains `blocked pending`
sanctioned-access/legal/reliability proof. **No such route is proposed here.**

---

## 2. Authority (P2)

David's *"ok do it"* authorizes **this bounded protocol work within the manual-export shape**. It does
**not** authorize building or running an HTTP fetcher.

**The dependency is human input:** each observation requires David to export. Authorization did not
make the work inert — it made the next action a **concrete export request**, which is **drafted in §7
and deliberately not sent**, because P4–P6 change what he would be asked to produce and this protocol
needs review first.

---

## 3. The observation unit (P4)

**An observation = ONE COMPLETE `player_season` REPORT BATCH**, against a manifest declared **before**
collection begins. Not "three exports."

**Why the grain matters, measured:** `pp_player_season` currently spans **9 distinct seasons × 4
distinct positions** — up to **36 position-season blocks**. `read_export` identifies season and
position **from file CONTENT, never the filename** (`playerprofiler.py:226`), because filenames are
download-order artifacts; the module already carries a guard for renamed folders and changed export
filenames (`:623-628`). Three arbitrary files are therefore **not** three observations of the same
thing.

**Declared before the first export, and identical at every observation:** report configuration and
filters · the exact season set · the exact position set · the expected block list · the completeness
rule · missing-block treatment.

**⚠ COST, NAMED RATHER THAN ABSORBED — and it is David's call, not mine.** Option 2 makes the
per-observation burden **the full report**, not one file. The alternative (P4 option 1) is a **single
pinned position-season slice**, which is far cheaper but yields a conclusion **scoped to that slice
only** and not to the stream. **I recommend neither by default and will not choose for him.** The
choice is presented in §7.

---

## 4. The instrument — what already exists, and two findings that constrain the design (P5)

### 4.1 Most of P5's requirement is already built and governed

`DurableStore.apply_block` (`playerprofiler.py:485-497`) computes

```
digest = sha256("\n".join(sorted(json.dumps(row, sort_keys=True) for row in rows)))
```

— a **canonicalized, order-independent semantic digest over normalized block rows**, and returns
**`"unchanged"`** when it matches the stored `pp_capture.content_hash`. It is therefore **immune to
row order, line endings, quoting and column order** — exactly the conflation P5 flagged. The loader
separately keeps a **raw file SHA** (`:120`, `sha256(path.read_bytes())`), so **both halves of P5's
required distinction already exist.**

**Design consequence: the pilot does not invent a change detector. It reads the one already governed.**

### 4.2 ⛔ FINDING — the production store CANNOT hold the observation series

On a changed block, `apply_block` executes `DELETE FROM {table} WHERE block = ?` and re-inserts, and
`pp_capture` holds **one row per `stream_key`** — current state, **no history**.

**Therefore a second observation OVERWRITES the first.** Ingesting observation 2 into the production
store would destroy the very series the pilot exists to build, and would leave no way to recompute
observation 1's digest.

**Required design, and it is not optional:** each observation's manifest — including its per-block
digests — is written to a **separate append-only pilot record OUTSIDE the production store**, before
or independently of any production ingest. **The production store is not the experiment's memory.**

*(This is exactly the class of thing that would otherwise be discovered after observation 2 had
already destroyed observation 1.)*

### 4.3 ⛔ FINDING — the parser version must be pinned across observations

The digest is computed over rows **after parsing**. A change to `playerprofiler.py`'s parsing or
normalization between observations would move the digest **for a non-source reason**, producing a
false `changed`.

**Required:** every observation records the module's commit SHA, and **an interval whose endpoints
were parsed by different module versions is reported `incomparable`, never `changed`.**

### 4.4 Per-observation manifest

UTC observation time · report/filter identity · module commit SHA (§4.3) · expected vs observed block
list · file count · byte count · row count per block · column/header hash · **raw SHA-256 per file** ·
**semantic digest per block** (§4.1) · and an explicit **schema/coverage result evaluated BEFORE any
content comparison**.

**A missing or partial block reads `incomplete`/`unavailable` — never `changed`.**

---

## 5. Retention of private raw evidence (P6)

"Any folder outside the repo" was not a rule. Pinned before the first export:

| Item | Requirement |
| :-- | :-- |
| Location | one named private local path, declared before collection |
| Access | David only; no agent copies raw subscriber rows anywhere |
| Duration | exact delivered bytes retained at least until the pilot is reviewed and closed |
| **In Git** | **NEVER.** No subscriber rows in any commit, artifact, ledger or review packet — hashes and counts only |

**⚠ DECISION FOR DAVID, NOT DEFAULTED EITHER WAY: is the raw export set backup-covered?**
Covering it places **subscriber data into the offsite backup manifest**, which engages the
manifest-coverage law and is his ruling. Leaving it uncovered makes the raw bytes **deliberately
regenerable-only** — and if they are lost, the semantic comparison cannot be replayed. **Both options
have a real cost; I am not choosing.**

---

## 6. Shape and outputs (P7)

**Three observations → two intervals. Weekly spacing. Off-season.**

Weekly is an **operational choice** balancing David's burden against informativeness. **It is not
derived from source evidence**, and nothing in this protocol claims it is.

**The only valid per-interval outputs, pre-stated:** `changed` · `unchanged` · `incomparable`.

**There is NO sample-count pass criterion.** Three observations create two intervals; **two intervals
cannot infer a recurring cadence**, and no number of intervals converts observed change into
source-publish cadence (§0). Any recurring-rhythm question after the pilot is a **separate,
burden-aware decision for David**.

**Interpretation ceilings:** an `unchanged` interval is **weak and, at this sample size,
non-diagnostic** · nothing finer than the sampling interval is detectable · the window is **entirely
off-season** and says nothing about in-season behaviour · results cover **`player_season` only**.

---

## 7. The export request — DRAFTED, NOT SENT

**Not sent, and not to be sent until this protocol is reviewed.** Two questions must reach David
*before* any export, because they change what he produces and what happens to it:

1. **Burden (§3):** full report batch per observation — a conclusion about the stream — **or** one
   pinned position-season slice, cheaper, with a slice-scoped conclusion?
2. **Retention (§5):** are the raw exports backup-covered, or deliberately regenerable-only?

Once answered, the request is mechanical: export the same configuration three times, one week apart,
into three distinct folders, and tell me where they are. **I hash and compare. Nothing is ingested
into the production store on the pilot's account** (§4.2), and no consumer, capture, scheduler or
store mutation follows without a separate word.

---

## 8. Boundaries

1. **No source-publish closure.** N1–N8 stays OPEN regardless of outcome; no §1 checkbox moves.
2. **No automated route** to PlayerProfiler is proposed, revived, or implied.
3. **No production ingest on the pilot's account** — §4.2 makes that destructive to the experiment.
4. **No catalog edit**, including the three Sleeper fields the ruling opened.
5. **No export request** until this protocol is reviewed and David answers §7's two questions.

**H2 QB rushing remains a registered hypothesis UNDER TEST with no result.**
