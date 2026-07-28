# TW28-IDENTITY-4 — Framing v3: the identity honesty fix + crosswalk preservation

**Author:** Claude Code (implementing lane) · **Status:** framing artifact v3, pre-RED.
**Authority:** David to Tower — *"ship the honesty fix and commit the file"*; Unit C route, verbatim —
*"route 1"*. **The route ruling is complete; nothing here waits on it.**
**Review chain:** framing v1 (parked, unreviewed) → v2 (`84dcf34a…`; Codex reviewed a mid-edit state
`0492720690c2…`) → Codex NOT CLEAR, 10 items → my disposition
(`identity_honesty_fix_disposition_v2.md`) → this v3. **All ten accepted; every figure re-measured.**
No code written. Nothing committed. No RED opens until this round clears.

**Two things moved since v2 and both are David-facing:** the false-explanation population is **3,453
rows, not 2,233** (my `Active`-only filter was conceptually wrong), and Unit C requires **two**
surfaces, because a second component invents its own category claim in the frontend and cannot be
fixed from the API.

**Unauthorised throughout and untouched:** Route 2, row targeting, name matching, I-5 bridge work,
I-3 sentinel population filtering, the canonical key, the Compliance Audit workflow, DG2-S0-01 (d),
and any push.

---

## 1. The concrete situation this serves

David opens a player card for a quarterback, running back, receiver or tight end who has no model
value. The card tells him *"No active model score for this player category."* His categories are
exactly the four Dynasty Genius models. The sentence is false, and it is false on **3,453** rows.

Two of those rows — Nick Kallerup (TE, SEA) and Ke'Shawn Williams (WR, CIN) — are the identity misses
that started this ticket: the model has feature rows for both, and they were dropped by a bare
`continue` because their gsis number has no Sleeper id in a frozen crosswalk. They are a **subset** of
the 3,453, not a separate case.

Separately, the file that join depends on is one gitignored 3.77 MB payload, untracked and unbacked.
If it disappears the next refresh publishes a universe with zero Engine B values, passes every exit
check, and raises only a non-blocking review prompt.

Neither is an accuracy problem. Both are honesty problems, which for this product is the worse kind.

## 2. The authorised units

**Unit A — fail closed on a missing or unusable crosswalk.** `_load_ff_playerids`
(`build_universe_pvo_batch.py:48-50`) returns `({}, {})` for a missing file; every Engine B player is
then skipped by the `continue` at lines 101-103 and publication proceeds. Unit A aborts instead.
Scope: *publication*, not identity repair.

**Unit B — count and name every skipped player.** Emit, in the coverage report, a count plus a record
per prediction dropped at the crosswalk join, keyed by the identifiers the orphan side actually has
(`gsis_id`, name, position). Reporting only; attaches nothing to any PVO row.

**Unit C — stop asserting a cause the system cannot substantiate.** Route 1, class-level. §3.

**Unit D — preserve the crosswalk as frozen, tracked, hash-stamped bytes.** §6.

## 3. Unit C — Route 1

### 3.1 Why row targeting was refused (retained for the record)

| | Identifiers actually present |
| :-- | :-- |
| The orphan crosswalk entry | `gsis_id`, `pff_id`, `pfr_id`, `espn_id`, `rotowire_id`, name, position, birthdate |
| The corresponding live PVO row | `sleeper_id` **only** — `identity_ids` = `{espn_id: null, gsis_id: null, pff_id: null, pfr_id: null, sleeper_id: "13151"}` |

**The intersection of identifiers is empty**; the only shared field is the name. Row targeting needs
name matching (contract-banned) or snapshot enrichment (`sleeper_universe.py:235-250`, Codex's I-5,
unauthorised). David ruled Route 1. Route 2 survives here only as out-of-scope history.

### 3.2 The measured population — corrected in v3

The blanket message renders on **11,622** rows (`engine_path` outside
`{ENGINE_A, ENGINE_B, BLEND_AB}`: PRE_MODEL 9,480 · INACTIVE 2,141 · UNRESOLVED_IDENTITY 1).

| `PRE_MODEL` at a modeled position | All statuses | Active-only |
| :-- | --: | --: |
| WR | 1,548 | 1,021 |
| RB | 790 | 491 |
| TE | 713 | 454 |
| QB | 402 | 267 |
| **Total** | **3,453** | 2,233 |

**v2 claimed 2,233 and was wrong on principle, not just arithmetic.** It filtered
`sleeper_status == "Active"`, which asks whether the player is currently interesting; the question is
whether the *sentence* is true. An inactive quarterback's category is still modeled, so the message is
equally false for him. The 1,220 rows v2 omitted are 1,137 Inactive, 81 Injured Reserve, 1 PUP, 1
Practice Squad. Cross-check validating both figures: **3,453 + 6,027 = 9,480**, the exact PRE_MODEL
total. The `~1,100×` ratio from v2 is **withdrawn** — measured counts only.

### 3.3 Unit C spans TWO surfaces, and the second cannot be fixed from the API

1. `app/api/routes/players.py:285-291` emits `DegradationField(message=…)`, rendered as visible body
   text by `frontend/src/player/PlayerDetailCard.tsx:37-39`.
2. `frontend/src/player/PlayerInspector.tsx:22-35` **never reads that message.** It computes
   `detail.model_status === "modeled"` and hardcodes its own strings — *"Unmodeled category"* /
   *"No active model score"*. The word "category" is a frontend literal.

**Consequence:** correcting the API string alone would leave the identical falsehood on the inspector
for all 3,453 rows, while looking complete. Unit C must change the API contract **and** the
inspector's derived claim, and the rendered-surface assertion must cover both consumers.

### 3.4 The total mapping — precedence, copy, and proof of totality

Evaluated in this order, first match wins. Copy below is candidate manager prose, pinned here rather
than deferred; the *contract* (what each branch may assert) is the reviewable part.

| # | Condition | May assert | Candidate copy | Live rows |
| :-- | :-- | :-- | :-- | --: |
| 1 | Modeled route (`ENGINE_A`/`ENGINE_B`/`BLEND_AB`) | nothing — no degradation field at all | *(none)* | 581 |
| 2 | `UNRESOLVED_IDENTITY` route | that no player identity resolved | "This record has no resolved player identity." | 1 |
| 3 | `INACTIVE` route | roster status only | "Not on an active NFL roster." | 2,141 |
| 4 | Position present and outside QB/RB/WR/TE | the category fact — **earned here** | "Dynasty Genius models quarterbacks, running backs, receivers and tight ends." | 6,009 |
| 5 | Position absent or unknown | that no model applies; **not** a category claim | "No model applies to this record." | 18 |
| 6 | `PRE_MODEL` at a modeled position | population membership only, **never a cause** | "Not in the current modeled population." | 3,453 |

**Totality proof:** 581 modeled + 1 + 2,141 + 6,009 + 18 + 3,453 = **12,203** = every row in the
universe; the five non-modeled branches sum to **11,622** = exactly the current message population.
No row falls through, and no raw route token (`PRE_MODEL`, `ENGINE_B`, …) reaches David's screen.

**Why precedence is status-before-position:** 241 rows carry no position at all (222 INACTIVE, 18
PRE_MODEL, 1 sentinel). Ordering status first means only the 18 genuinely unclassifiable rows reach
rule 5, and rule 4 never has to evaluate a category it cannot read.

**Branch 6 is the boundary of the whole unit.** It is true for a rookie awaiting features and true for
an identity miss, and it claims neither. Any wording that hints at *why* — features, identity,
unresolved, too new, coming soon — is Route 2 smuggled in through copy.

## 4. Mislead / nudge risks

- No branch may imply the player is bad or ineligible. Absence of a model is not a judgement.
- **Branch 6 must not become a promise.** "Coming soon" or "awaiting coverage" implies a commitment the
  roadmap has not made and is a verdict about which players are worth modelling.
- **Specificity must not outrun the branch key.** A branch may assert only what its key establishes.
- Unit B names players in an artifact. That record is about a join failure, not about the athlete.
- Unit D's commit message and any sidecar describe **bytes**, never provenance.
- Unit A converts a silent success into a loud failure — the failure must be legible at the governed
  report path (§7) or the silence has only moved.

## 5. Usability, duplicates, orphan output, and the join boundary

**"Usable" is a shape contract**, not a file-existence check: payload is an object; `entries` is a
list; each row is an object; `gsis_id`/`sleeper_id` are strings or absent.

**Duplicate policy — no silent resolution.** Today `_load_ff_playerids` builds both indexes with dict
comprehensions (**last-write-wins**) and `_active_pvos_from_engine_b` drops repeat Sleeper mappings via
`seen_sleepers`. That is the same silent-resolution defect class this ticket exists to remove.
Policy: byte-identical duplicates are tolerated and **counted**; **conflicting** GSIS→Sleeper or
Sleeper→GSIS mappings **fail closed**. Never last-write-wins.

**Orphan output:** deterministic order by `gsis_id` ascending; invariant
`orphan_count == len(orphan_records)`; the block is present-and-empty when there are none, because
absence is indistinguishable from "not computed."

**Publication invariant — stated so no threshold can appear later as if it were policy.** Publish iff
(i) the crosswalk is usable, (ii) **at least one** Engine B join succeeds, and (iii) orphan accounting
is complete. **There is no coverage threshold**; inventing one would be new product policy and is not
mine to make. So 502 orphans of 503 publishes with 502 recorded; 503 of 503 aborts on rule (ii).

## 6. Unit D — the end-to-end invariant

Measured: `git ls-files app/data/identity/_runs/` returns **zero** files; `git check-ignore` confirms
`.gitignore:122`. A RED that hashes "the committed payload" and separately checks "the loader resolves
the same path" can pass while a clean clone still lacks the load-bearing file.

**Required single invariant:** the path the production constant
(`build_universe_pvo_batch.py:31`) resolves is **git-tracked**, present in a clean-checkout-equivalent
state, and hashes to `8ed4b67578d06a24527356f9f355ed97f12be827e34885270c0b1d28c079f593`.

Implementation implication: a `.gitignore` negation for that exact file, leaving `_runs/` ignored — no
file move and no change to the loader constant. **Bytes only.** The snapshot records `source`,
`pull_timestamp`, and `count` with **no upstream commit SHA**, so nothing in the commit or any sidecar
may claim the upstream revision is pinned.

## 7. The abort truth surface, by its governed name

Not "a status marker." The scheduled job (`com.davidleess.dynasty-model-pvo-refresh.plist`) passes
`--report-path app/data/model_capture/pvo_refresh_latest_report.json`, written at
`run_pvo_refresh.py:328-330`. An abort must emit there with `status=aborted`, the failed stage, and the
named reason. An unchanged ready marker and an untouched prior runtime payload are necessary but are
**not** the explanation.

## 8. Falsification seeds — MEASURED-LIVE vs PROSPECTIVE

Separated deliberately: mixing them is how a suite goes green over a population of zero, which is the
S0-01 failure this cockpit already paid for once.

**MEASURED-LIVE (a real current population backs each one):**
1. A `PRE_MODEL` row at a modeled position (one of the **3,453**) receives **no** category claim — the
   exact defect.
2. A `PRE_MODEL` row at a non-modeled position **with a position present** (one of **6,009**) **keeps**
   the category wording — the over-correction control. (Not 6,027: that figure includes the 18
   position-absent rows, which take branch 5. The distinction is the point of seed 4.)
3. `GET /api/players/13151` and `/12971` read branch 6 with no stated cause — the two rows that
   provoked the ticket.
4. A row with **no position** (one of the 18 PRE_MODEL of 241 total) reads branch 5, never branch 4.
5. The `UNRESOLVED_IDENTITY` sentinel reads branch 2 and is **not** filtered from the population.
6. A modeled row (one of **581**) carries no degradation field at all.
7. **Both** rendered surfaces assert correctly — `PlayerDetailCard` *and* `PlayerInspector`. Payload-only
   assertions are insufficient; that gap is what my v1 board missed.
8. Lexical negative control: no branch text contains a cause word (features, identity, unresolved,
   new, soon, pending) and no raw route token, so copy drift cannot reintroduce Route 2.
9. Unit D: the loader's resolved path is tracked and hashes to the frozen value.
10. Unit D: no artifact or message asserts an upstream revision.
11. Branch totality: every one of the 12,203 live rows matches exactly one rule.

**PROSPECTIVE robustness (no current population — synthetic by necessity, and labelled so):**
12. Crosswalk absent → abort; report `status=aborted` + stage + reason; ready marker and prior runtime
    untouched.
13. Crosswalk present but non-object payload / non-list `entries` / non-object row / wrong-type ids →
    abort, distinct named reason per shape. Unit A must not key only on file existence.
14. Conflicting duplicate GSIS→Sleeper, and conflicting Sleeper→GSIS → abort, never last-write-wins.
15. Byte-identical duplicates → tolerated and counted, not an abort.
16. One unjoinable prediction → publishes; exactly one orphan record; modeled population down by one.
17. 502 of 503 unjoinable → publishes with 502 records; **503 of 503 → aborts** on the ≥1 rule.
18. Zero orphans → block present and empty.
19. Orphan entry with no name → recorded with a named-unavailable field, never dropped or fabricated.
20. An `INACTIVE` row at a modeled position takes branch 3, not branch 6. **Live count today is zero** —
    this is a precedence contract test, not a current defect. (v2 presented it as live; that was
    imagination about production.)

## 9. Overclaim check against the No-Verdict Line

Every unit is descriptive. Unit A withholds output rather than publishing a confident wrong one, which
is the line's own remedy for untrustworthy inputs. Unit B reports counts and identifiers with no
ordering or emphasis. Unit C **removes** an unearned claim from 3,453 rows, keeps the earned one on
6,009, and gives the remaining classes only what their route establishes. Unit D adds provenance
honesty and claims bytes only. No tier label, verdict, recommendation, or imperative is computed,
emitted, or rendered; `decision_supported=False` is untouched; no market data enters any model path.
H2 QB rushing is not involved and remains **UNDER TEST**.

## 10. Sequence

1. Codex challenge of this v3 → my disposition. **(Route ruling is complete — nothing waits on David
   here.)**
2. Codex authors the RED over §8, keeping the MEASURED-LIVE / PROSPECTIVE split intact.
3. I implement GREEN; Codex reviews to an enumerated CLEAR.
4. Full-suite closeout tollgate (`verify_sprint_closeout.py`) before any commit — the FE gate included,
   since Unit C touches two frontend files.
5. Commit on David's word. **A push is a separate word**, routed through Tower.
