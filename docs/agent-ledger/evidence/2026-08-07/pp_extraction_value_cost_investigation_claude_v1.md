# §4.1 PlayerProfiler extraction — value/cost investigation

**Author:** Claude Code, implementing lane · **Layer:** Layer 1 (ingest)
**Occasion:** David: *"lets investigate this."* Read-only investigation, relayed and scoped by Codex.
**Delivery:** the Codex wire is blocked (pane in copy-mode, `input_not_verifiable`, an unverifiable
paste chip in its composer, Codex at 17% context). Its instruction authorized a repo artifact **if
delivery fails**. This is that.

**AUTHORIZES NOTHING.** No code, RED/GREEN, export request, subscriber-data access, provider contact,
catalog or checkbox edit, commit, or push. **Nothing was executed** — see §0.

---

## 0. Factual correction, and the limit of this investigation

**The cited input path `src/dynasty_genius/sources/playerprofiler.py` DOES NOT EXIST.** The module is
**`src/dynasty_genius/playerprofiler.py`** (732 lines). There is no `sources/` variant; siblings are
`playerprofiler_gamelog.py`, `_pbp.py`, `_roster.py`.

**Everything below is established by reading code, NOT by executing it.** Executing the ingest
requires David's private subscriber exports, which are out of scope. **§5's alternative is therefore
verified structurally and NOT proven by a run** — the named one-command test that would prove or
falsify it is in §5.3.

---

## 1. What must move into a pure interface

Everything producing production-equivalent rows is inline in `run_playerprofiler_ingest`
(`:630-674`), plus the digest inside `apply_block` (`:441-468`). **None of it is exposed.**

| Behavior | Site |
| :-- | :-- |
| export discovery | `discover_exports(export_paths)` `:630` |
| schema + duplicate-block validation | `check_player_season_schema` / `check_medical_schema` / `check_no_duplicate_blocks` `:632-634` |
| identity index construction | `NameIdentityIndex.from_governed_crosswalk()` `:637` |
| per-row identity resolution | `identity.resolve(name, draft_year=…, college=…)` `:656` |
| column-name slugging | `_slug` `:641`, `:644`, `:670` |
| block derivation | `f"{position}-{season}"` `:654` |
| row-key construction | `f"player_season\|{block}\|{_norm_no_suffix(name)}"` `:657` |
| **cross-export dedup, first-occurrence-wins** | `seen: set[str]` `:651`, `:667-669` |
| identity field injection | `dg_player_id` / `identity_status` / `identity_candidates` `:670-672` |
| block grouping | `by_block[(stream, block)]` `:674` |
| **semantic digest** | `sha256("\n".join(sorted(json.dumps(row, sort_keys=True))))` `:446-448` |

**A digest helper alone is useless** — it needs `rows`, and producing `rows` requires all of the above.

---

## 2. Size, surface, and regression risk

**MEDIUM-to-LARGE. Not a helper function.**

**⚠ CORRECTED — I listed the REGRESSION surface as though it were the MODIFICATION surface, which
inflated the cost.** The two are separate and only the first requires edits:

**NECESSARILY MODIFIED:** `src/dynasty_genius/playerprofiler.py` (the core ingest function, in a
732-line module) · its **focused contract test** (`tests/contract/test_playerprofiler_ingest_red.py`)
· plus the new RED/GREEN proving byte-identical rows, digests, identity, dedup outcome and grouping.

**REGRESSION SURFACE — exercised, NOT necessarily edited:** the **4 caller scripts**
(`run_playerprofiler_ingest.py`, `_gamelog_`, `_pbp_`, `_roster_`) and the **other 4 test files**
(`_gamelog_red`, `_pbp_red`, `_roster_red`, `test_playerprofiler_decision_gate.py`). These
transitively exercise `PlayerProfilerStore`; **that makes them things the change can BREAK, not
things it must TOUCH.**

*(The do-not-build conclusion does not depend on the inflated count and stands on the corrected
one.)*

**Highest regression risks, in order:**

1. **Dedup ordering.** `seen` is first-occurrence-wins and therefore **order-dependent**. A pure
   helper that reorders exports or rows silently keeps a **different surviving row**, and digests
   diverge for reasons unrelated to the source. *(Keys are namespaced `player_season|…` vs
   `medical|…`, so splitting the streams is safe — but that is a property to be **proven**, not
   assumed.)*
2. **The single-pass loop serves BOTH streams.** Extracting `player_season` alone splits a loop that
   currently walks every export once.
3. **Identity determinism.** Digests embed `dg_player_id`/`identity_status`/`identity_candidates`
   from `GOVERNED_CROSSWALK`; any drift in resolution changes digests with no source change.
4. **`apply_block`'s `"unchanged"` short-circuit** is the store's change gate. Refactoring around it
   risks turning a no-op into a rewrite.
5. **Blast radius on the largest external dataset we hold** — `playerprofiler.db` is ~1.5M rows
   (`pp_player_season` 5,476 · `pp_gamelog_week` 44,462 · `pp_pbp_slot` 949,041 · `pp_roster_week`
   230,394 · `pp_pbp_play` 280,868 · `pp_medical_history` 9,768 · `pp_identity_bridge` 3,290).

---

## 3. Reusable production value beyond the N6 pilot

**DEMONSTRATED REUSE: NONE.** The PlayerProfiler store has **no production consumer outside
ingestion** — the measured state carried on the current board. Nothing today would call either
extracted function.

**SPECULATIVE REUSE, labelled as such:** a shared semantic-digest helper could serve change detection
for other manual-export sources (PFF is also manual-export). **But PFF has its own module and its own
shape**, no such consumer is designed, and no ticket exists. **This is an argument for a future
refactor, not a justification for this one.**

**Honest summary: the extraction's only demonstrated beneficiary is a pilot that cannot close the
field it was built to close.**

---

## 4. Recommendation — DO NOT BUILD IT NOW

**My lane's recommendation: do not authorize the §4.1 extraction.** Three independent reasons, any
one of which is sufficient:

1. **§5's alternative preserves normalization and semantic-digest fidelity EXACTLY**, because it is
   the production path rather than a reimplementation — so it needs **no parallel hasher and no §4.1
   extraction**. *(⚠ REPAIRED: this read "delivers the same descriptive result with **ZERO new code**"
   and "is **strictly stronger**". **Both are withdrawn.** It does NOT deliver v5's evidence envelope:
   a **small governed sidecar/procedure** is still needed for the file→block map, raw-header multiset,
   raw file SHAs and the duplicate/slug-collision validation, and **v5 requires amendment plus
   re-review**. CLI use additionally needs `root` pass-through code and a test. See the companion
   ruling artifact.)*
2. **The output cannot close M4 under any execution** (protocol §0), and **every `changed` verdict
   retains unmitigated silent-truncation risk** (§4.6) — there is no independent completeness
   evidence for `player_season`.
3. **Zero demonstrated reuse** (§3), against a medium-to-large change on the module guarding our
   largest external dataset.

**EVIDENCE THAT WOULD REVERSE THIS — stated so it can be tested, not argued:**

- **§5's alternative FAILS on execution** — e.g. a production write I did not find, or `pp_capture`
  digests that do not answer the pilot's question. *(This is the single most likely reverser, and it
  is cheap to test — §5.3.)*
- **A second, independent consumer for the digest emerges** (e.g. a PFF change-detection need David
  wants), converting speculative reuse into demonstrated reuse.
- **David rules the descriptive series has independent product value** sufficient on its own, at
  which point §5 still gets there cheaper and the extraction remains unnecessary.

---

## 5. The cheaper alternative — run the PRODUCTION path against a throwaway store

### 5.1 It already exists as a parameter

`run_playerprofiler_ingest(*, export_paths, identity=None, db_path=DEFAULT_DB_PATH, root=DEFAULT_ROOT)`
— **`db_path` and `root` are already parameters**, and `scripts/run_playerprofiler_ingest.py` already
exposes **`--db-path`**.

Point both at throwaway paths per observation and you get:

- **production-identical normalization, identity, dedup and grouping — because it IS the production
  code path**, not a reimplementation;
- the **real semantic digest per block**, since `apply_block` writes `pp_capture.content_hash` and
  **`captures()` does `SELECT *`**, returning `content_hash` (it pops only `coverage_json`);
- **no parallel hasher and no §4.1 extraction**;
- **zero production mutation ONLY when BOTH `db_path` AND `root` are redirected** — which today means
  **direct function invocation**, since the CLI exposes `--db-path` but not `--root` (§5.3);
- **per-observation isolation of the DIGESTS**, since each throwaway DB is its own artifact — which
  addresses the protocol's §4.2 "production store cannot hold the series" problem **for the digests
  only**.

**⚠ REPAIRED — what this list previously overclaimed.** It read *"**zero production mutation**, **zero
new code**, **no parallel hasher**, **no RED/GREEN**"* and *"per-observation isolation **for free**"*.
**Withdrawn:**

- **"zero new code" is false** as a route to v5. A **small governed sidecar/procedure** is still
  required to produce v5's evidence envelope — file→block map, raw-header multiset, raw file SHAs,
  duplicate-header and slug-collision validation — and **v5 needs amendment plus re-review** before
  this route satisfies it. *(It can invoke the existing public `read_export`/`discover_exports`, so it
  is far smaller than §4.1 — but it is not nothing.)*
- **"zero production mutation" holds only under direct invocation with both parameters redirected**,
  not via the CLI as it stands.
- **"for free" is wrong** — the isolation covers digests, not the manifest.

### 5.2 Falsification I ran against my own claim

I attempted to break it by finding a write outside those two parameters. **Every write site in the
module is parameterized or a read:**

| Site | What it is |
| :-- | :-- |
| `:403` `self.db_path.parent.mkdir(...)` | under `db_path` |
| `:108-113` `_atomic_write_json(path, …)` | the status marker, path derived from **`root`** (`status_marker_path(root)` `:524-525`, called `:613`) |
| `:247` `path.open(newline="", …)` | **read** of export CSVs |
| `_connect` | `sqlite3.connect(self.db_path)` |
| `_REPO_ROOT` (`:69`) | used ONLY for the three defaults and `GOVERNED_CROSSWALK` (`:70-73`), which is **read** |

**No unparameterized write found.** That is the whole basis of the recommendation, and it is the
thing to attack.

### 5.3 The one test that proves or kills it — NOT RUN

```bash
.venv/bin/python3.14 scripts/run_playerprofiler_ingest.py \
  --exports <a folder holding ONE report batch> \
  --db-path /tmp/pp_pilot_obs1.db
```
then read `content_hash` per block from that DB's `pp_capture`, and confirm
`app/data/playerprofiler.db` and `app/data/playerprofiler/playerprofiler_status_latest.json` are
**byte-unchanged** before and after.

**Not run here:** it needs David's private exports, and `--exports` has **no `--root` flag** —
`root` is a function parameter the CLI does not expose, so a CLI-only run would still write the
production **status marker**. **That is a real gap and the one concrete thing standing between this
alternative and "zero production mutation" via the CLI.** *(⚠ REPAIRED: this read "Closing it is a
**one-line argparse addition**". **Withdrawn** — it needs an `add_argument("--root", …)` line **and**
threading `root` into the `run_playerprofiler_ingest(...)` call at
`scripts/run_playerprofiler_ingest.py:66`, which today passes only `export_paths` and `db_path`, plus
a contract test and a check of the `--summary` branch. **Two code lines minimum plus a test**, not
one line. This same claim was corrected in the companion ruling artifact and **left live here — the
unswept-class defect, third instance in these two documents.**)* It remains far smaller than the §4.1
extraction, and it is **still code, so it is not authorized here and is not proposed as done.**

---

## 6. Boundaries

1. **Nothing executed. Nothing built. No subscriber data touched.**
2. **A-C unchanged:** all five open source-publish fields remain OPEN; no §1 checkbox moved.
3. The N6 protocol remains **CLEAR at v5 and NOT RUNNABLE**; this document does not alter it.
4. **The recommendation is a lane position, not a decision.** David rules.

**H2 QB rushing remains a registered hypothesis UNDER TEST with no result.**
