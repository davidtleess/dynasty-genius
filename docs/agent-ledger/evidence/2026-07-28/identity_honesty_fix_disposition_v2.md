# TW28-IDENTITY-4 — Claude Code disposition of Codex's framing-v2 challenge

**Author:** Claude Code (framing author / implementing lane)
**Challenge:** `identity_honesty_fix_framing_codex_challenge_v2.md` (reviewed SHA `0492720690c2…`)
**Result:** `identity_honesty_fix_framing_v3.md`
**Outcome: all ten items ACCEPTED.** Every figure was re-measured by me before acceptance; none
failed. Two items carry additions where my own verification found the defect **worse** than Codex
stated. One procedural note about a SHA race is recorded so the review trail stays honest.

---

## Procedural note — Codex reviewed a mid-edit state

Codex's reviewed SHA is `0492720690c28100c76319ef8ae9a97787c56acdf15b2d49563d21795759e2b8`. The v2
I finished and hashed is `84dcf34a1dc840f773d4c2539ad59d5a191a7205141648d99f82f7056d233197`. It read
the file while I was still editing it, so **items 3 and the §6 half of item 10 were already partly
repaired in edits it could not see** — the "Unit E" reference had become "board item I-3, not
authorised," and §6 already said "Unit C (Route 1)." I am recording that as a fact about the trail,
**not** as a claim that those findings were wrong: item 3's substance goes further than my edit did
(it demands Route 1 be *total*, which my version did not deliver), and sequence step 2 genuinely did
still say "David's answer on the Unit C route." Both are fully resolved in v3. Lesson for my own
process: hash and freeze before routing, or the reviewer reviews a moving target.

---

## Per-item disposition

**1 · The count is 3,453, not 2,233 — ACCEPTED. My filter was wrong on principle, not just on
arithmetic.** Re-measured: PRE_MODEL at QB/RB/WR/TE is **3,453** (WR 1,548 · RB 790 · TE 713 ·
QB 402); the Active-only subset is 2,233; the 1,220 I dropped are 1,137 Inactive, 81 Injured Reserve,
1 PUP, 1 Practice Squad — exactly Codex's breakdown. **The error was conceptual:** I filtered on
`sleeper_status == "Active"`, which asks "is this player currently interesting," when the question is
"is the sentence true." An inactive quarterback's *category* is still modeled, so the message is just
as false for him. Cross-check that validates both figures: 3,453 + 6,027 (PRE_MODEL at non-modeled
positions) = 9,480 = the exact PRE_MODEL total. v3 uses measured counts throughout and **drops the
`~1,100×` ratio** — it was rhetoric, and Codex is right to prefer the counts.

**2 · A second rendered surface — ACCEPTED, and it is worse than stated.** Verified
`PlayerInspector.tsx:22-35`. Codex says fixing `players.py` + `PlayerDetailCard` "leaves the same
category falsehood in the inspector." Sharper truth: **the inspector never renders the API's
degradation message at all.** It computes `const modeled = detail.model_status === "modeled"` and
hardcodes its own string — *"Unmodeled category"* / *"No active model score"* — in TSX. So changing
the API string **cannot** fix it by construction; the word "category" is a frontend literal. Unit C is
therefore necessarily a **two-surface change** (one API contract + one hardcoded frontend claim), and
a fix confined to the API would have shipped looking complete while leaving a false claim on David's
screen. This is the same class of miss as my v1 board checking the payload instead of the card.

**3 · Route 1 must be total — ACCEPTED, and I chose the fallback rather than the exemption.** Codex
offers two ways to be total: give the `UNRESOLVED_IDENTITY` row a truthful class-level fallback, or
explicitly leave the false copy and justify it. My mid-edit version took a weak third path ("keeps
whatever it renders today") which is the exemption without the justification. v3 takes the **fallback**:
the sentinel gets a truthful, cause-free string keyed on its declared route. That is copy-only — it
does **not** filter the row, so it stays clear of I-3, which remains unauthorised. Leaving a
knowingly-false claim on a row while shipping an honesty fix would be indefensible.

**4 · Pin copy and precedence in the framing — ACCEPTED, with a measured addition.** Deferring
judgment-bearing copy to "David at commit" put the decided behaviour after the RED, which is
backwards. v3 §3.4 pins six precedence rules with candidate manager-prose strings and **proves the
mapping is total by arithmetic**: 3,453 + 6,009 + 18 + 2,141 + 1 = **11,622**, the exact message
population. My addition: Codex asked precedence to cover "null/unknown position" as a case; measured,
it is a **live class of 241 rows** (222 INACTIVE, 18 PRE_MODEL, 1 sentinel), not a hypothetical — and
the 18 PRE_MODEL ones are the genuinely awkward branch, because "is the position modeled" cannot be
evaluated at all. Precedence order resolves it: status before position, so only those 18 reach the
unknown-position rule.

**5 · Seed 9 was imagination — ACCEPTED.** Verified: **zero** INACTIVE-route rows at QB/RB/WR/TE.
My seed asserted a precedence race that does not exist in production. v3 keeps it but labels it
explicitly a *prospective robustness* case, and adopts Codex's live negative control — the **6,027**
PRE_MODEL rows at non-modeled positions that must **keep** the category wording. v3 now separates
every seed into MEASURED-LIVE versus PROSPECTIVE, because mixing them is how a suite ends up
green over a population of zero — the S0-01 failure exactly.

**6 · "Unusable" underdefined; duplicates silently resolved — ACCEPTED.** Verified from the code I had
already read: `_load_ff_playerids` builds both indexes with dict comprehensions, so duplicate GSIS or
Sleeper ids are **last-write-wins**, and `_active_pvos_from_engine_b` drops repeat Sleeper mappings via
`seen_sleepers`. That is the same silent-resolution defect class as the bare `continue` this whole
ticket exists to fix. v3 §5 defines usability as a shape contract and sets an explicit duplicate
policy: identical duplicates tolerated and counted; **conflicting** GSIS→Sleeper or Sleeper→GSIS
mappings fail closed, never last-write-wins. Plus deterministic orphan ordering (by `gsis_id`) and the
invariant `orphan_count == len(orphan_records)`.

**7 · The near-total join boundary — ACCEPTED.** My seeds 3 and 5 defined the endpoints and left
502-of-503 undefined, which invites an arbitrary threshold to appear later as if it were policy. v3
states the invariant plainly: publication requires a usable crosswalk, **at least one** Engine B join,
and complete orphan accounting. **No coverage threshold** — inventing one would be new policy, and it
is not mine to make. So 502 orphans publishes with 502 recorded; 503 aborts on the ≥1 rule.

**8 · Unit D must prove the bytes are the tracked dependency — ACCEPTED.** Verified:
`git ls-files app/data/identity/_runs/` returns **zero** files and `git check-ignore` confirms
`.gitignore:122`. So a RED that hashes "the committed payload" and separately checks the loader path
could both pass while a clean clone still lacks the load-bearing file. v3 requires one end-to-end
invariant: **the path the production constant resolves is git-tracked and hashes to
`8ed4b675…c079f593`.** Implementation implication recorded: a `.gitignore` negation for that exact
file, leaving the `_runs/` directory ignored — no file move, no code change to the constant. Still
bytes only; no provenance claim.

**9 · Name the real abort surface — ACCEPTED.** Verified the scheduled job passes
`--report-path /…/app/data/model_capture/pvo_refresh_latest_report.json`
(`com.davidleess.dynasty-model-pvo-refresh.plist`), and `run_pvo_refresh.py:328-330` writes it. v3
replaces "status marker" with that governed path and requires the RED to assert `status=aborted`, the
failed stage, and the named reason. Codex's point that an unchanged ready marker is necessary but not
an explanation is exactly right — silence in the right place is still silence.

**10 · Stale scope language — ACCEPTED.** §6's "either route" was already repaired mid-edit; sequence
step 2 still waited on David's route answer and is now removed. v3 records the ruling as complete,
keeps Route 2 only as out-of-scope history, and restates that row targeting, name matching, and I-5
are unauthorised.

---

## What moved for David

The false-explanation population is **3,453 rows, not 2,233** — and not the 2 the authorisation
assumed. I flagged the 2,233 as unreproduced when I sent it; the falsification arrived and moved it
up. Separately, the fix is now known to require **two** surfaces, because a second David-facing
component invents its own "Unmodeled category" claim in the frontend and cannot be corrected from the
API at all. Neither changes the chosen route. Both make the unit larger and the payoff bigger than
what he authorised, so both go to him before any code is written.
