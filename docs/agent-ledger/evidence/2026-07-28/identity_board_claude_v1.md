# TW28-IDENTITY-1 — Identity: what exists, what it costs today, what to do first

**Author:** Claude Code (implementing lane) · **Date:** 2026-07-28 · **Status:** board for David.
**NOT a repair.** Nothing in this document has been built, changed, or run against production.
**Codex adversarial challenge:** requested, outstanding at time of writing.
**Gemini record:** requested. Gemini's own finding record is the authority on the origin of this
priority; this board is measured independently from the repo and does not restate Gemini's claims.

Every number below was measured from artifacts on this machine today, read-only. No production
script was run. Measurement scripts were session-scoped and are described, not cited as evidence;
every figure is reproducible from the artifact paths named inline.

---

## 0. Tower's three claims, tested

| Claim | Verdict | Measurement |
| :-- | :-- | :-- |
| `app/data/identity/_runs/ff_playerids_20260516.json` is 3,768,182 bytes, dated 2026-05-15 | **CONFIRMED** | 3,768,182 bytes; mtime 2026-05-15 23:28 local; the file's own metadata says `pull_timestamp: 2026-05-16T03:28:22Z` — the same moment in UTC |
| Gitignored at `.gitignore` line 122 | **CONFIRMED** | `.gitignore:122` = `app/data/identity/_runs/` |
| NOT among the three entries added to the backup manifest yesterday | **CONFIRMED** | yesterday's three (`a73ab02`) are `app/data/prospect_identity_review.jsonl`, `app/data/pff_exports/`, `app/data/league_snapshots/`. The only identity string anywhere in `app/config/backup_manifest.json` is line 165, the prospect review log. The crosswalk is in no entry, and neither is any other file under `app/data/identity/` |

My measurement agrees with Tower on all three.

---

## 1. What identity work actually exists

Eight things wear the word "identity." They were built at different times for different reasons and
they do not know about each other.

**① The design on paper.** `docs/identity/identity_contract.md` — v1.0.0, still marked **DRAFT**,
dated 2026-05-15. It says Dynasty Genius owns one permanent id per player, that the NFL's `gsis_id`
is the bridge to outside data, that resolution runs a fixed 7-step cascade, that name-similarity
guessing is banned from production, and that anything unresolved goes to a human review queue
instead of being scored. It is a good document. Nothing enforces it.

**② What production actually runs.** Not ①. Every row in the live player universe is keyed by
**Sleeper's own player id**. Measured on the live artifact
`app/data/valuation_runtime/universe_pvo_runtime.json` (written 2026-07-27 19:32, 12,203 players):

- **581** rows carry a Dynasty Genius id.
- **11,621** rows carry only a Sleeper id (`identity_status: sleeper_resolved`, `dg_player_id: null`).
- **1** row is `unresolved` — Sleeper id `"0"`, a junk row that has been riding along in the universe
  and shows up in the divergence artifact as its own signal type.

And the 581 that do have a Dynasty Genius id have it in **two incompatible vocabularies**:
**501** copy the NFL's gsis number (`00-0038564`, the Engine B path) and **80** are hand-made name
slugs (`carson_beck_qb`, `elijah_sarratt_wr`, the Engine A rookie path). There is no bridge between
the two vocabularies in the production path. The canonical id is not canonical — it is whatever the
engine that produced the row happened to have.

**③ The single load-bearing file.** The join from the NFL's gsis number to Sleeper's id is one file:
`app/data/identity/_runs/ff_playerids_20260516.json`, 3.77 MB, pulled once from a community source
on 2026-05-16, named by a hardcoded constant at `scripts/build_universe_pvo_batch.py:31`. It holds
7,952 players, **6,117** of whom have a Sleeper id. It is gitignored and it is not backed up. If it
goes missing, `_load_ff_playerids` returns empty (lines 48–50) and **every** model value in the app
disappears — silently, because the builder's response to an unjoinable player is a bare `continue`
(lines 101–103) and its response to a missing file is an empty dictionary.

**④ The prospect side.** `src/dynasty_genius/adapters/prospect_identity_resolver.py` — 103 lines:
explicit id, then a human-curated alias bridge, then a review log. No guessing. Modest and correct.
Feeds the rookie API surface.

**⑤ The college substrate — the most complete working machinery.**
`src/dynasty_genius/identity/college_prospect_identity.py` (1,395 lines) plus
`prospect_nfl_bridge.py` (970 lines), with a committed registry, promotion log, review queues, and
conflict files under `app/data/identity/`. This one does what ① describes: deterministic cascade,
human promotion of every match, full audit trail. It serves research and backtests. It is **not**
wired to the app's valuation path.

**⑥ The best-designed component, wired to nothing.**
`src/dynasty_genius/identity/outcome_identity_bridge.py` — point-in-time validity windows per
player, fail-closed on unresolved, conflicts quarantined rather than guessed, provenance-hashed.
It is exactly the contract's snapshot rule, built properly. Its data source in the scheduled scorer
is `_default_identity_snapshot_loader` at `scripts/run_realized_outcome_scoring.py:399`, which
returns an empty list with the comment "wired + validated at go-live." The best identity component
in the repo currently resolves nothing, by design.

**⑦ A name-guessing engine sitting inside the canonical module.**
`src/dynasty_genius/identity/__init__.py` carries a similarity matcher with 0.95 / 0.80 / 0.60
confidence thresholds and a `__main__` demo. The contract bans exactly this from production paths.
Measured: **no production caller uses the matcher** — production callers import only
`generate_dg_id`. It is a loaded gun in a drawer, not a live defect.

**⑧ Copy-pasted identity logic in scripts.** `scripts/build_college_features.py` and
`scripts/build_w2b_cfbd.py` each define their own local `normalize_player_name`. The contract's rule
is one mapping layer and no adapter-local identity logic.

**Which one production runs:** ② and ③ — Sleeper-keyed rows, joined to the model through a frozen
community file. **Which one is best built:** ⑥ for design, ⑤ for completeness. Neither is in the
production path.

---

## 2. What is wrong TODAY as a consequence

**Two players you can name.** On the live artifact, `Nick Kallerup` (TE, SEA, Sleeper 13151) and
`Ke'Shawn Williams` (WR, CIN, Sleeper 12971) appear in the app with **no model value**
(`dvs_engine: null`, `dg_player_id: null`) and **no caveat** (`caveats: null`) explaining why.
Both have Engine B inference feature rows — the model has what it needs to value them. Their NFL
gsis number simply has no Sleeper id in the May crosswalk, so the builder skipped them. Nothing in
the app, the coverage report, or any triage file says their name. That is the whole visible cost
today, and its size is two players.

The count is small; the **kind** is the problem. Governance says the opposite twice — the north
star says unresolved rows are "rejected to triage, not silently scored" and that "silent
substitution is forbidden"; the constitution says when inputs cannot be trusted, "report
unavailable" rather than a tidy number. A blank cell with no reason is neither.

**Honest answer to the rest of the question: nothing else David sees today is wrong because of
identity.** Specifically:

- The 9,480 `PRE_MODEL` players (no model value) are **not** an identity failure — they have no
  Engine B features. That is a coverage question, not an identity question.
- The 12,201 / 12,202 / 12,203 row-count differences between the committed seed, the divergence
  artifact, and the live PVO are **vintage, not corruption** — the seed is from 2026-06-26, the
  divergence run finished one minute before the PVO refresh, and Sleeper added players in between
  (e.g. `Jeremiah Franklin`, TE, NE). I checked this specifically because it looked like an identity
  defect; it is not one. Zero duplicate keys in either artifact.
- The Engine A slug vs Engine B gsis split does not break anything on screen, because every row also
  carries its Sleeper id and that is what the app joins on.

**What is one command away from being visible:** the crosswalk's absence fails **open**. Delete or
lose that one gitignored 3.77 MB file and the next refresh ships an app with zero model values and
no error anywhere. The file is not in the backup manifest.

**What is structurally blocked but costing nothing yet:** a rookie cannot be followed by id from his
Engine A row into his Engine B row (`carson_beck_qb` vs `00-00…`), and the point-in-time bridge that
would join model calls to realized NFL outcomes has no data source. That is precisely the join the
compounding model-vs-market track record needs. It costs nothing on screen today because the
realized-outcome loop is already waiting on forward-capture accrual.

---

## 3. Ordered by leverage

### Cheap and protective — hours, no model change, no migration

**I-1 · Stop the silence.** Make a missing crosswalk fail closed instead of returning empty; count
and name every skipped player in the coverage report; put a caveat on the affected rows so a blank
model value reads as "identity unresolved" instead of nothing. Turns a silent hole into a visible
one. *Gate: David — it changes a production artifact's contract and adds a David-facing caveat.*

**I-2 · Protect the file.** Either add the crosswalk to the backup manifest or re-pin it as a
committed, hash-stamped snapshot. **Honest wrinkle, stated rather than buried:** the manifest
coverage law covers stores that cannot be regenerated "from the repo plus public sources," and this
one *can* be re-pulled from nflverse — so it is arguably outside the law's letter. But re-pulling
yields a *different vintage*, which breaks reproducibility of every value the app has shipped. The
reproducibility tenet is why I still put this second. *Gate: David — manifest-law reading, plus
whether to vendor 3.8 MB into git.*

**I-3 · Empty the drawer.** Remove or quarantine the unused name-guessing matcher in the canonical
identity module. Zero production callers today; a contract violation the first time someone reaches
for it. *Cockpit-clearable.*

**I-4 · One normalizer.** Fold the two script-local `normalize_player_name` copies into the identity
module. *Cockpit-clearable.*

### Deep and structural — weeks, and each needs a decision before design

**I-5 · Decide the canonical key.** One id per human, minted once, stable from prospect through
active player, with every source id in one mapping table. This is the north star's Identity
Resolution Layer, and the architecture explicitly sequences it *before* broad feature ingestion —
it was skipped, and ② is the consequence. *Gate: David — what the key is, and whether the migration
of every artifact keyed the old way is worth it now.*

**I-6 · Give the good bridge real input.** Stand up the identity-snapshot producer so ⑥ has data and
the stub loader can be retired. This is what unblocks joining model calls to realized outcomes.
*Gate: David — this is realized-outcome-loop scope.*

**I-7 · Promote the contract from DRAFT to enforced.** A test that scans production paths for the
three prohibitions the contract already names: no name-guessing, no adapter-local identity, no
silently-dropped unresolved rows. Cheap to write; only meaningful after I-1. *Gate: David for the
DRAFT → binding status change.*

---

## 4. What needs David's gate before anyone touches it

- **I-1** — production artifact contract + a new David-facing caveat string.
- **I-2** — manifest-law reading; vendoring a 3.8 MB file into git.
- **I-5** — the canonical-key decision itself, and whether to migrate.
- **I-6** — realized-outcome-loop scope.
- **I-7** — DRAFT → binding for `docs/identity/identity_contract.md`.
- **I-3, I-4** — no David gate needed; cockpit CLEAR is sufficient. Committing still needs his word.

## 5. Deliberately not touched

Per David's sequencing: the failing Codex Compliance Audit workflow, and DG2-S0-01 unit (d). Neither
was opened, read for this board, or acted on. The S0-01 identity-key defect from 2026-07-27 is a
different problem from this board's ② — that one was a test-fixture shape, this one is the
production key vocabulary — and it stays parked.
