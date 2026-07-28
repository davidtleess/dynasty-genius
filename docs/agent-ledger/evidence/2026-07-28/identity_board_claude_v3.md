# TW28-IDENTITY-1 — Identity: what exists, what it costs today, what to do first (v3)

**Author:** Claude Code · **Date:** 2026-07-28 · **Status:** board for David.
**NOT a repair.** Nothing here has been built, changed, or run against production.
**v3 supersedes v2** (SHA-256 `905e5723d4cb…`), which superseded v1 (`9c873fded263…`).
Review chain: Codex NOT-CLEAR challenge → my disposition → v2 → Codex NOT-CLEAR re-review
(`identity_board_codex_rereview_v2.md`) → this v3. v2's eight folds were confirmed present and
correct; **v3 carries exactly one change**, the I-4 provenance-versus-preservable-bytes correction
below, plus a sweep that found no equivalent wording elsewhere in the document.

**The corrected claim was mine, and I had routed it as an addition rather than a measurement.**
v2's I-4 said the exact operational input "cannot be re-pinned even in principle." That is false and
Codex broke it: unreconstructible *provenance* is not unpinnable *bytes*. The same overreach appears
in my `identity_board_claude_disposition_v1.md` §12; that document stands as the record of what I
said at the time and is superseded on this point by this board. **Two of Codex's findings remain
better than anything in v1**, and one of them made v1 wrong in a worse direction than it was written
— both are called out below rather than quietly absorbed.
**Gemini's own identity record: requested, outstanding.** This board restates no Gemini claim.

Every figure was measured read-only from artifacts on this machine, and independently reproduced by
Codex except where noted. No production script was run by me. Counts are local artifact state.
A scheduled 09:30 PVO refresh rotated the runtime artifact mid-review; the counts at issue were
identical before and after.

---

## 0. Tower's three claims, tested

| Claim | Verdict | Measurement |
| :-- | :-- | :-- |
| `app/data/identity/_runs/ff_playerids_20260516.json` is 3,768,182 bytes, dated 2026-05-15 | **CONFIRMED** | 3,768,182 bytes; mtime 2026-05-15 23:28 local; the file's own metadata says `pull_timestamp: 2026-05-16T03:28:22Z` — the same instant in UTC |
| Gitignored at `.gitignore` line 122 | **CONFIRMED** | `.gitignore:122` = `app/data/identity/_runs/` |
| NOT among the three entries added to the backup manifest yesterday | **CONFIRMED** | yesterday's three (`a73ab02`) are `prospect_identity_review.jsonl`, `pff_exports/`, `league_snapshots/`. No path under `app/data/identity/` appears in the manifest at all |

All three confirmed independently. Nothing to correct.

---

## 1. What identity work actually exists

Eight things wear the word "identity," built at different times for different reasons, and they do
not know about each other.

**① The design on paper.** `docs/identity/identity_contract.md` — v1.0.0, still **DRAFT**, dated
2026-05-15. One permanent id per player; the NFL's `gsis_id` as the bridge to outside data; a fixed
7-step resolution cascade; name-similarity guessing banned from production; anything unresolved goes
to human review instead of being scored. A good document. Nothing enforces it.

**② What production actually runs.** Not ①. Every row in the live universe is keyed by **Sleeper's
own player id**. On the live artifact (12,203 players):

- **581** rows carry a Dynasty Genius id.
- **11,621** carry only a Sleeper id (`dg_player_id: null`).
- **1** is `unresolved` — Sleeper id `"0"`, which is not a player at all (see §2).

The 581 speak **two different id languages**: **501** copy the NFL's gsis number (`00-0038564`,
Engine B) and **80** are name slugs (`carson_beck_qb`, Engine A rookies).

**Corrected from v1 (Codex ch.2).** v1 said there is "no bridge" between them. That was overstated.
There is **no canonical DG-id bridge** — that stands, and `dg_player_id` is not a canonical key in
any real sense. But **production continuity across the Engine A→B transition is real and runs on the
Sleeper id**: `universe_pvo_batch.py:64-70` keys both engine lists by Sleeper id and line 135
concatenates prospects then actives, so an active row replaces the prospect row for the same player;
and `capture/model_forward_capture_store.py:81-103` keys longitudinal capture `sleeper:` before `dg:`.
The vocabulary split is a real defect in the identity layer. It is **not** currently severing model
history.

**③ The single load-bearing file.** The gsis→Sleeper join is one file: 3.77 MB, pulled once on
2026-05-16, named by a hardcoded constant at `scripts/build_universe_pvo_batch.py:31`, gitignored,
not backed up. 7,952 players, **6,117** with a Sleeper id, zero duplicate ids on either side.

**④ The prospect side.** `adapters/prospect_identity_resolver.py`, 103 lines: explicit id → curated
alias bridge → review log. No guessing. Modest and correct. Feeds the rookie surface.

**⑤ The college substrate — most complete working machinery.**
`identity/college_prospect_identity.py` (1,395 lines) + `prospect_nfl_bridge.py` (970 lines), with
committed registry, promotion log, review queues, conflict files. Does what ① describes: deterministic
cascade, human promotion of every match, full audit trail. Serves research. **Not** wired to the
app's valuation path.

**⑥ The best-designed component, wired to nothing.** `identity/outcome_identity_bridge.py` —
point-in-time validity windows, fail-closed, conflicts quarantined rather than guessed,
provenance-hashed. Exactly the contract's snapshot rule, built properly. Its data source
(`run_realized_outcome_scoring.py:398-401`) returns an empty list, marked "wired at go-live." The
best identity component in the repo resolves nothing.

**⑦ A name-guessing engine inside the canonical module.** `identity/__init__.py` carries a
similarity matcher with 0.95/0.80/0.60 thresholds. The contract bans exactly this from production.
**Narrowed from v1 (Codex ch.6):** the **fuzzy symbols** (`IdentityResolver`, `resolve_by_name`,
`compute_name_confidence`) have **zero callers of any kind**. v1 went too far in saying production
imports "only `generate_dg_id`" — one-shot builders also import `normalize_player_name` and
`assign_collision_suffixes`. The fuzzy engine is a loaded gun in a drawer; nobody has picked it up.

**⑧ Three name normalizers with three different meanings.** **Reclassified from v1 (Codex ch.10).**
v1 called these copy-paste. They are not: `build_college_features` strips accents and suffixes and
keeps spaces; `build_w2b_cfbd` strips every non-alpha character including spaces but keeps suffix
letters; the root normalizer adds first-name aliases and underscore tokenization. `A.J. Brown Jr.`
becomes `aj brown`, `ajbrownjr`, and `aj_brown` respectively. Consolidating them would silently
change joins and cache keys. This is a semantic migration, **not** cleanup.

**Which one production runs:** ② and ③. **Which is best built:** ⑥ by design, ⑤ by completeness.
Neither is in the production path.

---

## 2. What is wrong TODAY

**① Two players are shown a confidently wrong reason.** *(Codex's finding, ch.8 — the sharpest in
the review, and v1 got it wrong in the safer-sounding direction.)*

Nick Kallerup (TE, SEA, Sleeper 13151) and Ke'Shawn Williams (WR, CIN, Sleeper 12971) each have an
Engine B feature row — the model has what it needs to value them. Their gsis number has no Sleeper id
in the frozen May crosswalk, so `build_universe_pvo_batch.py:102-103` skips them with a bare
`continue`. Codex verified these are **exactly** the two such players out of 503 predictions.

v1 said they show "no caveat explaining why." That is wrong, and wrong in the worse direction. The
player card shows a reason, and the reason is **false**: `app/api/routes/players.py:285-291` emits
*"No active model score for this player category."* for any unmodeled row, and
`frontend/src/player/PlayerDetailCard.tsx:37-39` renders it as visible text under an "Experimental"
badge. **So this is on David's screen**, and it attributes an identity-join failure to player
category. A blank cell would have been merely silent. A confident wrong reason is the failure mode
the No-Verdict Line exists to prevent.

**② A pseudo-player answers as if it were human.** *(Codex's finding, ch.7.)* Sleeper id `"0"` is an
empty-starter sentinel, not a person. `sleeper_universe.py:90-107` admits it because the string
`"0"` is truthy, so it is carried through as rostered and in starters, tagged
`UNRESOLVED_IDENTITY`, and propagated into the divergence artifact as its own signal type.
`GET /api/players/0` returns **HTTP 200**.

v1 named this row in §1 but then wrote "the whole visible cost today is two players," which the 200
contradicts. **One addition of my own:** `build_model_player_key` **already excludes `'0'` as a
pseudo-id by name** — so one layer of the system knows it is a sentinel while the ingestion layer
admits it. This should be filtered as a sentinel, **not** routed to human identity triage.

**Everything else I checked and cleared:**

- **9,478 of the 9,480** `PRE_MODEL` rows lack Engine B features — a coverage gap, not identity.
  (v1 said 9,480; the two players above have features, so they cannot be counted there. Codex ch.3.)
- The 12,201 → 12,202 → 12,203 spread across seed, divergence, and runtime is **vintage, not
  corruption**: seed→divergence adds only Jeremiah Franklin, divergence→runtime adds only Tyler Moore,
  zero removals, zero duplicates. I suspected a defect here and withdrew it; Codex confirmed the
  withdrawal was correct.

**What is one command from being visible.** Lose that one gitignored crosswalk and
`_load_ff_playerids` returns empty (lines 48-50). **Corrected from v1 (Codex ch.4):** the result is
**zero Engine B values and 80 surviving Engine A values** — not "every model value gone." All Phase
17.2 exit booleans still pass. There *would* be one observable signal: Engine B falling 501→0 is a
coverage delta of 501 against a `>=10` threshold (`run_pvo_refresh.py:170`), and Daily What-Changed
surfaces that block when it fires (`what_changed/report.py:158-185`). But the code calls that trigger
**"review-prompt only"** at line 61 — it does **not** block, so the bad candidate publishes. I went
looking for that wiring to be missing, which would have made the case more urgent; it is present.

**What is structurally blocked but costing nothing yet.** **Reframed from v1 (Codex ch.11):** the
realized-outcome scorer already resolves `prediction.sleeper_id` → gsis at capture date
(`realized_outcome_scorer.py:217-228`). The missing input is therefore a **point-in-time
Sleeper→GSIS mapping** for ⑥, which is a separate problem from the slug-vs-gsis vocabulary split.
v1 fused the two. Nothing on screen is wrong from this today; the loop is already waiting on
forward-capture accrual.

---

## 3. Ordered by leverage

### Immediate containment — cheap, no model change

**I-1a · Fail closed on a missing crosswalk.** Abort publication rather than shipping a model-less
universe that passes every exit check. Cheap and deterministic. *Gate: David — it changes a
production artifact's publication contract.*

**I-1b · Report the orphans.** Count and name every skipped player, keyed by GSIS and name, in the
coverage report. Cheap. Turns a silent skip into a named one. *Gate: David — new artifact field.*

**I-2 · Fix the false reason on the player card.** Distinguish "no model for this player category"
from "identity unresolved" in the degradation contract, so the two players stop being told something
untrue. This is the only item that changes what David reads today. *Gate: David — David-facing copy.*

**I-3 · Filter the `"0"` sentinel at ingestion** and stop it answering HTTP 200, matching what the
capture layer already does. *Gate: David — it changes universe population by one row.*

**I-4 · Protect the exact vintage.** Backup-manifest entry, or preserve it as a committed
hash-stamped snapshot. **Honest ambiguity, not a settled exemption (Codex ch.12):** the file is
re-pullable from nflverse, which *may* put it outside the manifest law's narrow disaster-loss
mandate. The call is David's. *Gate: David.*

Three distinct facts, kept separate — **corrected in v3, because v2 collapsed them into a single
overreaching claim of mine** ("cannot be re-pinned even in principle"), which Codex's re-review broke:

- **Provenance is unrecoverable.** The snapshot records only `source`, `pull_timestamp`, and `count`
  — no upstream commit SHA. The upstream source revision behind today's values cannot be
  reconstructed from what the file carries.
- **The bytes are preservable right now.** The exact operational file exists and hashes to
  `8ed4b67578d06a24527356f9f355ed97f12be827e34885270c0b1d28c079f593` (independently reproduced by
  me and by Codex). Committing or backing it up today pins the input permanently. **This is the fact
  my v2 wording denied, and it makes I-4 more actionable, not less** — protection is available now
  and needs no new machinery.
- **The loss condition is one-way.** If the payload is lost *before* preservation, a re-pull from
  mutable `master` cannot be assumed to reproduce this vintage. A hash alone would not restore lost
  bytes either — it proves what was there, it does not rebuild it.

The practical reading: the window to make this input permanent is open today and closes the moment
the file is gone.

### Bridge work — not cheap, do not present it as such

**I-5 · Deterministic row attachment.** *(Split out of v1's I-1 per Codex ch.9.)* Attaching a caveat
to the *right* row is not currently possible by identifier: the crosswalk row has no Sleeper id, and
the materialized snapshot discards the Sleeper payload's gsis (`sleeper_universe.py:235-250`). Doing
it by name would recreate the prohibited failure mode. Needs deterministic snapshot enrichment first.

### Structural — decision before design

**I-6 · Decide the canonical key.** One id per human, stable from prospect to active player, source
ids in one mapping table. The north star sequences this *before* feature ingestion; it was skipped,
and ② is the consequence. *Gate: David — the key itself, and whether to migrate artifacts keyed the
old way.*

**I-7 · Give ⑥ its point-in-time Sleeper→GSIS input** and retire the stub loader. Independent of I-6.
*Gate: David — realized-outcome-loop scope.*

**I-8 · Unify the three normalizers as a semantic migration** with an explicit contract and
regression fixtures — **behind** I-6, never before it. *Gate: David.*

**I-9 · Promote the contract from DRAFT to enforced.** Meaningful only after I-1a/I-1b.

**Explicitly demoted:** removing the unused fuzzy matcher (v1's I-3) is preventive hygiene with zero
callers. It is **not** evidence that production is unsafe today, and it is lower leverage than
everything above.

---

## 4. What needs David's gate

I-1a, I-1b, I-2, I-3, I-4, I-6, I-7, I-8, I-9 — all of them. I-5 is design work that needs I-6's
answer first. Nothing here is cockpit-clearable without his word, because every item either changes a
production publication contract, a David-facing string, the universe population, or a governance
document's binding status.

## 5. Deliberately not touched

The failing Codex Compliance Audit workflow and DG2-S0-01 unit (d) — parked by David's sequencing,
neither opened. The S0-01 identity-key defect from 2026-07-27 is a different problem from ②: that one
was a test-fixture shape, this is the production key vocabulary. It stays parked.
