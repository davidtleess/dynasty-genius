# Framing — R1 + R2 as one group: the surface has two words for at least four truths

From Claude (write lane) — framing artifact, pre-RED. `[w#r1-r2-group]`
Date: 2026-08-19 · Status: **FRAMING ONLY — no RED authored, no code opened, nothing authorized**

Per `02` §Strategy/UX framing first, this artifact opens the task. It is raw input for David and for
the Codex challenge round. It selects no solution and authorizes nothing.

---

## 0. Layer + the layers 1–2 dependency check

*(`05` §3, pending ratification, followed voluntarily.)*

**Presenting layer:** 6 (front-end / David-facing surface) and 2 (curate — identity cohort), jointly.

**Layers 1–2 dependency check — run this session, rerunnable:**

- **Check performed.** Read `app/data/valuation_runtime/universe_pvo_runtime.json`
  (`captured_at 2026-08-18T13:30:03Z`, 12,222 rows) directly and counted: rows with a null
  `dynasty_value_score` but a present `projection_2y`; their `dvs_engine` values; their caveats; and
  `nfl_draft_round` presence within that cohort. Read `src/dynasty_genius/pvo_assembler.py:412-465`
  and `app/api/routes/players.py:40,249,265-291`.
- **Result.** The substrate is **present**, not missing. 503 of the 583-player modeled cohort carry a
  `projection_2y`. The 115 blank-score rows all have projections. This corroborates Codex's
  2026-08-18 refutation of the "2024 absent / 2025 truncated" diagnosis and independently confirms
  that a feature-store rebuild is not indicated.
- **Conclusion.** **R1 is genuinely at the presenting layer** — the number exists and is destroyed on
  the way to the surface. **R2 is genuinely at layer 2** — a cohort-membership question, not a
  display bug. Neither is a layers 1–2 ingestion hole. No layer 1–2 work is opened by this framing.

---

## 1. The concrete user situation

David opens his own roster — 27 players, `roster_id 1`. **Three cells are blank.** They are blank for
**three different reasons**, and the surface gives him no way to tell them apart:

| Player | `dg_status` | Has a projection? | Why it is blank | Ticket |
| :-- | :-- | :-- | :-- | :-- |
| Garrett Wilson (WR, 26) | `ENGINE_B` | **yes — 11.255 PPG** | composite died in the dead-window bridge | R1 |
| Braelon Allen (RB) | `ENGINE_B` | **yes — 4.899 PPG** | same | R1 |
| Tank Dell (WR, 26, 3 yrs exp) | `PRE_MODEL` | **no** | never entered the modeled cohort at all | R2 |

A fourth truth exists off his roster: **Ashton Jeanty carries DVS 75.3 and Rasheen Ali 20.7** — the
score exists and is deliberately withheld by the Roster Audit gate (A7, Studio-verified as
intentional). Same blank cell, opposite meaning.

**So: one blank cell, four distinct truths.** David's own words control the priority here — *a points
number degrades gracefully, a score does not.* Wilson's 11.255 PPG is a number he can judge against
fifteen years of football, and the product is currently throwing it away in favour of nothing.

---

## 2. What the code actually does — three verified statements

**(a) The assembler writes a false provenance and a false caveat.**
`pvo_assembler.py:458-465` — when neither an Engine A prior nor an Engine B score is available, it
sets `dynasty_value_score = None`, then sets `dvs_engine = "A"` as a "provenance marker" and appends
*"Insufficient professional season data — Engine A prospect score used as prior."*

Measured on the served artifact: **114 of the 115** blank rows carry that caveat, and **0 of those 114
have an `nfl_draft_round`** — so no Engine A prior existed and none was used. The row states that a
prior was used. It was not. *(The 115th row has `dvs_engine = None`.)*

**(b) The API then reports those rows as fully modeled, with no degradation.**
`players.py:40` defines `MODELED_ENGINE_PATHS = {"ENGINE_A","ENGINE_B","BLEND_AB"}`; `:249` sets
`modeled` from `engine_path` **alone**, never from whether a score exists. Wilson is `ENGINE_B`, so
`:283-284` set `model_status = "modeled"` and `degradation = None`, and `:265-276` ship a
`PlayerModelLane` whose `dynasty_value_score` is `None`. **The response asserts a healthy model lane
while carrying an empty one.**

**(c) The other branch is false in the opposite direction.**
`players.py:286-291` — Tank Dell is `PRE_MODEL`, so the response reads `model_status = "experimental"`
with the message *"No active model score for this player category."* He is a 26-year-old rostered
Houston WR with three years of experience. His **category** is modeled — 241 WRs are in the cohort.
He personally is not, and the surface cannot say so.

**`model_status` has exactly two values and is being asked to carry at least four meanings.**

---

## 3. Why R1 and R2 are one group, not two tickets run in parallel

They are the same defect wearing different clothes: **the system occupies states it has no vocabulary
for, so it picks the nearest available word and states something untrue.** R1 is that failure inside
the assembler and the `modeled` branch; R2 is that failure at cohort entry.

A7 and the descriptive cluster are **downstream of the same vocabulary.** If A7 is fixed first, it
gets built against a state model R1 then changes underneath it. That is the argument for David's
stated order, and this framing supports it on the evidence rather than on deference.

**Scope boundary this framing proposes:** define the honest state vocabulary once, apply it to R1 and
R2, and let A7 and the descriptive cluster inherit it. **Not proposed and not opened:** any
feature-store rebuild, any model change, any re-run, any Engine A/B mechanic.

---

## 4. Mislead / nudge risks — verdict by the back door

1. **A state label that reads as a recommendation.** "Unavailable", "insufficient", "not enough data"
   can all be heard as *avoid this player*. Wilson at 11.255 PPG is not a warning; the absence is
   ours, not his. State names must describe **our pipeline's condition**, never the player's quality.
2. **Showing PPG where a DVS is withheld could defeat A7's deliberate gate.** If the Roster Audit
   suppression is intentional (Studio-verified), surfacing points for those same players may route
   around a deliberate product decision. **This is a genuine conflict between R1 and A7. It is
   flagged, not resolved here — it is David's ruling.**
3. **Ordering by a newly surfaced PPG creates an implicit recommended order.** `00` §No-Verdict Line:
   any default sort must disclose its basis. A points column must not silently become a ranking.
4. **Fixing (b) makes more cells honestly empty, which will look like a regression.** Telling the
   truth about 114 rows will read as the product getting worse before the points column makes it
   better. Say so up front rather than being surprised by it.

---

## 5. Candidate falsification seeds for the RED

*(Codex owns RED authorship; these are seeds, not tests.)*

- A row with `engine_path = ENGINE_B` and `dynasty_value_score = None` — must NOT report
  `model_status = "modeled"` with `degradation = None`.
- A row that took the no-prior branch — must NOT claim an Engine A prior was used.
- `PRE_MODEL` on a **rostered, active, multi-year** player vs `PRE_MODEL` on a genuine pre-NFL
  prospect — these must not produce the same message.
- A row with a projection but no composite vs a row with neither — must be distinguishable.
- A row where the score exists but is **withheld** (Jeanty) vs one where it does not exist (Wilson) —
  the A7 boundary; must not collapse to one state.
- Boundary: `games_t` exactly at `ENGINE_B_MIN_GAMES_T`; `games_t = 0`; `games_t = None`.
- The 115th row (`dvs_engine = None`) — the blank cohort is 115, the false-caveat cohort is 114; the
  off-by-one is real and must be named, not rounded away.
- Identity: a player present in the market capture but absent from the modeled cohort (Tank Dell's
  exact shape) must surface as a **named** state, not as silence.

---

## 6. Overclaim check against the No-Verdict Line

- Everything proposed here is **descriptive**: it renames states and surfaces an existing number. It
  computes no new score and promotes nothing. `decision_supported=False` is untouched.
- Surfacing `projection_2y` as points per game requires a **unit and a horizon on the surface** — a
  bare "11.3" is not honest just because it is real. This is the same defect the descriptive cluster
  names, which is a further argument for the shared vocabulary.
- No tier label, no named band, no buy/sell/hold language enters through this door.
- Market data stays out. Nothing here touches Engine A or Engine B inputs.

---

## 7. Open questions for David — this framing does not decide them

1. **R1 vs A7 conflict (§4.2):** if the Roster Audit gate deliberately withholds a score, may the
   points number be shown for those same players?
2. **`PRE_MODEL` cohort entry:** Tank Dell is one of **10** rostered players carrying `PRE_MODEL`
   league-wide. Is his exclusion correct-but-undisclosed, or wrong? That is a football/cohort
   question, not an engineering one.
3. **How honest, how fast:** fixing the false `modeled` claim increases visible emptiness before the
   points column reduces it. Land them together, or land the truth first?

---

## 8. What is NOT authorized by this document

No RED is open. No product code, contract, test, migration, artifact, or surface has changed. The
Codex challenge round (`02` §Strategy/UX framing first) has not run. Priority is never authorization
(`05` §2).
