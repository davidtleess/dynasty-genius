# TW28-IDENTITY-4 — Framing v4: the identity honesty fix + crosswalk preservation

**Author:** Claude Code · **Status:** framing v4, pre-RED. Frozen and hashed before routing.
**Authority:** David — *"ship the honesty fix and commit the file"*; Unit C route — *"route 1"*.
**Chain:** v3 (`0155173f1e22…`) → Codex NOT CLEAR, 8 items (`11d9073f5416…`) → my disposition
(`identity_honesty_fix_disposition_v3.md`) → this v4. **Six items fixed here; two escalated to David
rather than absorbed** (§0).
**Design foundation read for this version** (`PRODUCT.md` + `DESIGN.md` via the `impeccable` skill) —
required for rendered copy and **not done before v3**, which is why v3's strings were diagnostics.
No code written. Nothing committed. No RED open.

**Unauthorised and untouched:** Route 2, row targeting, name matching, I-5, sentinel population
filtering, the canonical key, the Compliance Audit workflow, DG2-S0-01 (d), any push.

---

## 0. TWO ITEMS ARE DAVID'S, NOT MINE — nothing here absorbs them

**0.1 · 113 modeled rows are presented as "Modeled" while carrying no value.** Measured: of 581
modeled-route rows, 468 are `MODEL_SUPPORTED` and **113 are `MODEL_UNCERTAIN` with both
`dynasty_value_score` and `xvar` null** (Jayden Reed, Jonathan Mingo, Roschon Johnson, Josh Whyle,
Brayden Willis…). Branch 1 says nothing on those rows and `PlayerInspector` renders a flat
**"Modeled."** A player with no value reads as modeled.

This is a **measured David-visible honesty defect** and it is **not established as identity scope**.
Arguably it is worse than the defect we are authorised to fix — a wrong reason misinforms; "Modeled"
over a blank value misrepresents the model's own state. **v4 changes nothing for these rows.** It is
named here and routed to David. Absorbing it would be scope not given.

**0.2 · The publication-coverage rule is a policy choice I must not make.** v3 claimed "no coverage
threshold" while requiring `>=1` Engine B join — which *is* a 1-of-503 floor — and asserted that
502/503 publishes. Not mine to authorise, and the constitution points the other way: when inputs are
"stale, missing, malformed, or **low-coverage**", the remedy is "report unavailable, block, or widen
uncertainty."

Three candidate policies, David's to choose: **(a)** fail closed on any orphan; **(b)** fail below a
coverage floor he sets; **(c)** publish at any coverage with complete accounting. **(a) would stop
today's daily refresh** — 2 of 503 orphans exist right now — so this is a live behavioural decision.

**Pending his word, Unit A ships only the unambiguous fail-closed cases** (missing file, malformed
shape, conflicting duplicates). Orphan-bearing runs behave **exactly as today** except the orphans are
now named. No threshold is invented in either direction.

## 1. The situation

David opens a player card for a QB, RB, WR or TE with no model value. It tells him *"No active model
score for this player category."* Those four categories are precisely the ones Dynasty Genius models.
The sentence is false, on **3,453** rows. Two of them — Nick Kallerup (TE, SEA), Ke'Shawn Williams
(WR, CIN) — are the identity misses that opened this ticket, and they are a subset, not a separate case.

Separately, the crosswalk that join depends on is one gitignored, untracked, unbacked 3.77 MB payload.
Lose it and the next refresh publishes zero Engine B values, passes every exit check, and raises only a
non-blocking review prompt.

## 2. Units

- **A — fail closed on a missing or unusable crosswalk** (§5; coverage rule escalated per §0.2).
- **B — count and name every skipped player**, including the prediction-side skips (§5).
- **C — stop asserting causes the system cannot substantiate** (§3).
- **D — preserve the crosswalk as frozen, tracked, hash-stamped bytes** (§6).

## 3. Unit C — Route 1

### 3.1 Why row targeting was refused (record)

The orphan crosswalk entry carries `gsis_id`/`pff_id`/`pfr_id`/`espn_id`/`rotowire_id` + name,
position, birthdate. The live PVO row carries `sleeper_id` **only**. **The identifier intersection is
empty**; the sole overlap is the name. Row targeting needs name matching (contract-banned) or snapshot
enrichment (I-5, unauthorised). David ruled Route 1.

### 3.2 Measured population

The blanket message renders on **11,622** of 12,203 rows. `PRE_MODEL` at a modeled position:
**3,453** (WR 1,548 · RB 790 · TE 713 · QB 402). v2's 2,233 was the Active-only subset and was wrong
on principle — an inactive quarterback's category is still modeled, so the sentence is equally false
for him. Cross-check: 3,453 + 6,027 = 9,480 = the exact `PRE_MODEL` total.

### 3.3 Two surfaces, and the second cannot be fixed from the API

1. `app/api/routes/players.py:285-291` emits the message; `PlayerDetailCard.tsx:37-39` renders it.
2. `PlayerInspector.tsx:22-35` **never reads it** — it computes `model_status === "modeled"` and
   hardcodes *"Unmodeled category"* / *"No active model score"*. "Category" is a frontend literal, so
   an API-only fix cannot reach it.

### 3.4 The mapping — total over the DECLARED domain, not just today's data

v3 proved coverage of today's populations and presented it as a contract. Corrected: the declared
domain is **eight** routes (`allowed_engine_routes`); five are populated today. **`MARKET_ONLY` and
`CONTEXT_ONLY` are legal and were unhandled.** Precedence, first match wins:

| # | Condition | May assert | Copy (manager voice) | Live |
| :-- | :-- | :-- | :-- | --: |
| 1 | `ENGINE_A`/`ENGINE_B`/`BLEND_AB` | nothing | *(none — but see §0.1)* | 581 |
| 2 | `UNRESOLVED_IDENTITY` | that it is not a player | "This entry isn't a player." | 1 |
| 3 | `INACTIVE` | roster status only | "Not on an NFL roster right now." | 2,141 |
| 4 | `MARKET_ONLY` | that only market data exists | "Market price only — no Dynasty Genius value." | 0 |
| 5 | `CONTEXT_ONLY` | that only league context exists | "League context only — no Dynasty Genius value." | 0 |
| 6 | Position present, outside QB/RB/WR/TE | the category fact — **earned here** | "Dynasty Genius values quarterbacks, running backs, receivers and tight ends." | 6,009 |
| 7 | Position absent or unknown | the two facts, **no causal link** | "No Dynasty Genius value. Position unknown." | 18 |
| 8 | `PRE_MODEL` at a modeled position | non-existence only, **never a cause** | "No Dynasty Genius value for him." | 3,453 |
| — | **exhaustive else** | nothing — **fail loud** | *(no string; a route outside the declared domain is a defect, not a copy case)* | 0 |

**Totality is now over the contract**, and the else-branch refuses rather than defaulting. Live rows
still sum: 581 + 1 + 2,141 + 0 + 0 + 6,009 + 18 + 3,453 = **12,203**.

**Copy notes, traceable to law:**
- v3's "population" and "record" were **schema nouns** — PRODUCT.md's first anti-reference is
  developer/diagnostics UI, and principle 6 requires every quiet state to be a *designed* state in
  manager prose. Rewritten accordingly.
- **Branch 8 says "for him," not "yet."** "Yet" is a promise about future coverage, which is a verdict
  about which players are worth modelling (my own named nudge risk).
- **Branch 2 no longer contains the word "identity"**, which is what made v3's seed 8 unsatisfiable
  against v3's own branch 2. Structural fix, not an exemption.
- No branch names a route token, a field, or a cause.

### 3.5 Composition rules — what the whole viewport says (missing from v3)

Strings alone are not the contract; the layered-caveats law is about what a reader sees together.

1. **Exactly one degradation statement per row.** The branch string **replaces** "No active model
   score" — it never stacks beneath it.
2. **The inspector's hardcoded pair collapses to that same single statement.** "Unmodeled category" is
   deleted, not supplemented; both surfaces render one identical sentence for a given row.
3. **"Experimental" is a model-status badge, not a reason**, and may coexist with exactly one
   statement — never with two.
4. No branch string may appear in the first-viewport hero region; these are row/inspector states.
5. Both surfaces stay in Plex Sans — this is prose, not a numeric value, so mono is wrong per DESIGN.md.

## 4. Mislead / nudge risks

- Absence of a model is never a judgement about the player.
- Branch 8 must not become a promise ("yet", "coming soon", "awaiting coverage").
- A branch may assert only what its key establishes; any hint at *why* is Route 2 through copy.
- Unit B names players in an artifact — that record is about a join failure, not the athlete.
- Unit D describes **bytes**, never provenance.
- Unit A's loud failure must be legible at the governed report path (§7), or the silence has only moved.

## 5. Usability, duplicates, orphans

**Usable** is a shape contract: payload is an object; `entries` is a list; each row an object;
`gsis_id`/`sleeper_id` strings or absent.

**Duplicates — "identical" means after JSON parsing** (equal parsed mappings, not equal source bytes).
Today `_load_ff_playerids` builds both indexes with dict comprehensions — **last-write-wins** — and
`_active_pvos_from_engine_b` silently drops repeat Sleeper mappings via `seen_sleepers`. Policy:
parsed-identical duplicates are tolerated and **counted**; **conflicting** GSIS→Sleeper or
Sleeper→GSIS mappings **fail closed**. Never last-write-wins.

**Reporting:** orphan records and duplicate counts live in the same coverage block, ordered
deterministically by `gsis_id`; invariant `orphan_count == len(orphan_records)`; the block is
present-and-empty when there are none. **Unit B also covers the prediction-side `seen_sleepers` skips**
— a second silent drop v3 omitted.

**Publication:** requires a usable crosswalk and complete accounting. **The coverage rule is escalated
(§0.2)** and unchanged pending David's word.

## 6. Unit D — the end-to-end invariant

`git ls-files app/data/identity/_runs/` returns **zero**; `git check-ignore` confirms `.gitignore:122`.
**Required invariant:** the path the production constant (`build_universe_pvo_batch.py:31`) resolves is
**git-tracked**, present in a clean-checkout-equivalent state, and hashes to
`8ed4b67578d06a24527356f9f355ed97f12be827e34885270c0b1d28c079f593`.

**Implementation, corrected and proven.** v3 said "a file negation"; that cannot work — git will not
re-include a child whose parent directory is excluded. Tested in a throwaway repo: negating the child
under `_runs/` leaves it **ignored**; excluding the directory's *contents* (`_runs/*`) and then negating
the child leaves it **tracked**. Pattern B it is — no file move, no change to the loader constant.
*Method note:* `git check-ignore` exits 0 on matching a **negation** rule, so its exit code is not a
verdict; `git add` + `git ls-files` is ground truth. **Bytes only** — no upstream SHA exists to pin.

## 7. The abort truth surface

`app/data/model_capture/pvo_refresh_latest_report.json`, per the scheduled job's `--report-path`
(`com.davidleess.dynasty-model-pvo-refresh.plist`) and `run_pvo_refresh.py:328-330`. An abort emits
`status=aborted`, the failed stage, and the named reason. An unchanged ready marker is necessary but is
not an explanation.

## 8. Falsification seeds — MEASURED-LIVE vs PROSPECTIVE

**MEASURED-LIVE:**
1. A `PRE_MODEL` row at a modeled position (of **3,453**) receives no category claim — the defect.
2. A `PRE_MODEL` row at a non-modeled position **with a position present** (of **6,009**) keeps the
   category sentence — the over-correction control. (Not 6,027: that includes the 18 position-absent
   rows, which take branch 7.)
3. `GET /api/players/13151` and `/12971` read branch 8 with no stated cause.
4. A position-absent row (of the 18) reads branch 7, never branch 6.
5. The `UNRESOLVED_IDENTITY` row reads branch 2 and is **not** filtered from the population.
6. A modeled row (of 581) carries no degradation statement.
7. **Both** surfaces assert identically — `PlayerDetailCard` and `PlayerInspector`. Payload-only
   assertion is insufficient; that gap is what my v1 board missed.
8. **Composition:** exactly one degradation statement renders; "Unmodeled category" and "No active
   model score" appear **nowhere**; "Experimental" may coexist with exactly one statement.
9. Lexical control: no branch string contains a cause word (features, identity, unresolved, new, soon,
   pending) or a route token. Satisfiable as written — branch 2 no longer uses "identity".
10. Unit D: the loader's resolved path is tracked and hashes to the frozen value.
11. Unit D: nothing asserts an upstream revision.
12. Branch totality over live data: each of the 12,203 rows matches exactly one rule.

**PROSPECTIVE (no live population — synthetic by necessity):**
13. `MARKET_ONLY` and `CONTEXT_ONLY` rows at a modeled position read branches 4/5 — **zero rows today**,
    both routes declared legal.
14. A route outside the declared eight → the exhaustive else **fails loud**, emits no string.
15. Crosswalk absent → abort; report `status=aborted` + stage + reason; ready marker and prior runtime
    untouched.
16. Non-object payload / non-list `entries` / non-object row / wrong-type ids → abort, distinct reason
    each. Unit A must not key only on file existence.
17. Conflicting duplicate GSIS→Sleeper, and conflicting Sleeper→GSIS → abort, never last-write-wins.
18. Parsed-identical duplicates → tolerated and counted, not an abort.
19. Prediction-side `seen_sleepers` skip → counted and named like a crosswalk orphan.
20. One unjoinable prediction → behaves as today, with the orphan named. **No coverage threshold is
    asserted in either direction** pending §0.2.
21. Zero orphans → block present and empty.
22. Orphan entry with no name → recorded with a named-unavailable field, never dropped or fabricated.
23. An `INACTIVE` row at a modeled position takes branch 3, not branch 8 — **zero rows today**; a
    precedence contract test, not a current defect.

## 9. No-Verdict check

Unit A withholds output rather than publishing a confident wrong one — the line's own remedy. Unit B
reports counts and identifiers with no ordering or emphasis. Unit C **removes** an unearned claim from
3,453 rows, keeps the earned one on 6,009, and gives every other class only what its route establishes.
Unit D claims bytes only. No tier label, verdict, recommendation, or imperative anywhere;
`decision_supported=False` untouched; no market data enters any model path. H2 QB rushing is not
involved and remains **UNDER TEST**.

## 10. Sequence

1. Codex challenge of this v4 → my disposition. **David's word needed on §0.1 and §0.2** — §0.2 gates
   Unit A's coverage behaviour only; §0.1 gates nothing here and changes no row.
2. Codex authors the RED over §8, preserving the MEASURED-LIVE / PROSPECTIVE split.
3. I implement GREEN; Codex reviews to an enumerated CLEAR.
4. Full-suite tollgate **including the FE gate** — Unit C touches two frontend files.
5. Commit on David's word. **A push is a separate word** via Tower.
