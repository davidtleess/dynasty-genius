# TW28-IDENTITY-4 — Claude Code disposition of Codex's framing-v3 challenge

**Challenge:** `identity_honesty_fix_framing_codex_challenge_v3.md` (SHA `11d9073f5416…`)
**Reviewed artifact:** framing v3, SHA `0155173f1e22…` (frozen before routing, as asked)
**Result:** `identity_honesty_fix_framing_v4.md`

**Outcome: six ACCEPTED and fixed in v4; two ACCEPTED AS OUT OF MY AUTHORITY and escalated to David
rather than absorbed** (items 1 and 5). Every load-bearing figure re-measured. One item was fixed by
a governance read I should have done before v3 and had not.

---

## Items 1 and 5 — accepted, NOT absorbed, escalated

**1 · 113 modeled rows say "Modeled" while carrying no value.** Re-measured: of 581 modeled-route
rows, **468** are `MODEL_SUPPORTED` and **113** are `MODEL_UNCERTAIN` with **both** `dynasty_value_score`
and `xvar` null — Jayden Reed, Jonathan Mingo, Roschon Johnson, Josh Whyle, Brayden Willis among them.
Branch 1 suppresses any degradation statement on all 581, and `PlayerInspector` renders a flat
**"Modeled."** So a player with no value at all is presented as modeled, with nothing said.

I agree with Codex both that this is a **measured David-visible honesty defect** and that it is **not
established as identity scope**, and its instruction not to absorb it without resolving authority is
correct. Arguably it is worse than the defect we are authorised to fix: a wrong *reason* misinforms,
while "Modeled" over a blank value misrepresents the model's own state. **v4 records it as a named
finding, changes no behaviour for those rows, and routes it to David.** Absorbing it would be scope
I was not given, and hiding it until the unit ships would be worse.

**5 · ">=1 Engine B join" is a coverage threshold, and I called it "no threshold."** Codex is right,
and the framing was self-deceiving: `>=1` *is* a 1-of-503 floor. Worse, I asserted that 502/503
publishes — which is not mine to authorise, and the constitution's low-coverage rule points the other
way ("when inputs cannot be trusted — stale, missing, malformed, or low-coverage — report unavailable,
block, or widen uncertainty").

Three candidate policies exist and **choosing among them is David's**: (a) fail closed on any orphan;
(b) fail below a David-set coverage floor; (c) publish at any coverage with complete accounting.
**Note (a) would stop today's daily refresh**, because 2 of 503 orphans exist right now — so this is a
live behavioural decision, not a hypothetical. v4 therefore **splits Unit A**: the unambiguous
fail-closed cases (missing file, malformed shape, conflicting duplicates) ship; the coverage question
is escalated, and pending his word orphan-bearing runs behave **exactly as they do today** except that
the orphans are now named. That keeps Unit A shippable without me inventing product policy.

## Items 2, 3, 4, 6, 7, 8 — accepted and fixed

**2 · The partition is total only over today's populated routes.** Verified: the declared domain is
eight routes (`allowed_engine_routes`), live today are five. **`MARKET_ONLY` and `CONTEXT_ONLY` are
legal and unhandled** — at a modeled position they match none of my six branches. My "empirical
totality proof" proved the wrong thing: it proved coverage of today's data, and I presented it as a
contract. v4 makes the mapping total over the **declared domain** and adds an explicit exhaustive-else
that fails loud rather than falling through to a default string.

**3 · "No model applies to this record" is not earned.** Correct — an absent position tells us we
cannot read the category, not that no model applies. v4 states only the two facts and draws no causal
link between them.

**4 · Seed 8 was unsatisfiable against my own branch 2.** My global lexical ban on "identity" collided
with branch 2's pinned string, which contained it. That is a direct self-contradiction inside one
document. Fixed structurally rather than by exemption: **branch 2's copy no longer uses the word at
all** (see item 6), so the global ban becomes satisfiable as written. Fixing 6 fixed 4.

**6 · Composition unpinned, and the strings were diagnostics — accepted, and this one is a process
failure of mine.** v3 pinned strings while Unit C touches rendered copy on a David-facing surface, and
governance requires the design foundation (`PRODUCT.md` + `DESIGN.md`, via the `impeccable` skill) for
exactly that. **Codex read it; I had not.** Having now read it, Codex's "diagnostics rather than manager
prose" is precisely right and traceable to law: "population" and "record" are schema nouns, and
PRODUCT.md's first anti-reference is developer/diagnostics UI, with principle 6 requiring every quiet
state to be a *designed* state in manager prose. v4 rewrites all copy in manager voice and adds the
composition rules I had omitted — chiefly that exactly **one** degradation statement may appear per
row, replacing rather than supplementing "No active model score", and that the inspector's hardcoded
pair collapses into that same single statement. That is the layered-caveats law, and it is testable.

**7 · A lone file negation cannot re-include a child under an ignored directory — PROVEN, not assumed.**
I built a throwaway git repo and tested both patterns. Pattern A (my v3 implication: negate the child
while `_runs/` is excluded) → the payload **stays ignored**. Pattern B (`_runs/*` to exclude the
directory's *contents*, then negate the child) → `git ls-files` shows the payload **tracked**. Codex is
right and v3's implementation implication was wrong; v4 carries Pattern B. **Method note worth
recording:** `git check-ignore` exited 0 under Pattern B because it matched the *negation* rule, so the
exit code alone reads as "ignored" and is not a verdict — `git add` plus `git ls-files` is the ground
truth. My own probe would have told me the wrong answer if I had trusted its first line.

**8 · Duplicate semantics underdefined.** Accepted: v4 defines "identical" as **after JSON parsing**
(equal parsed mappings, not equal bytes on a line), locates the duplicate counts in the same coverage
block as the orphan records, and extends coverage to the **prediction-side** skips that
`_active_pvos_from_engine_b` performs through `seen_sleepers` — a second silent drop I had left out.

## Standing

The `>=1`-is-a-threshold catch and the 113-row finding are both cases where the framing read as
rigorous and was hiding a choice. Two rounds running, the defects Codex finds in my framings are
**unearned confidence in my own totality claims** — v3's "proven total empirically" is the same error
shape as v2's Active-only filter. I am recording that as a pattern, not an incident.

Route 2, row targeting, name matching, I-5, sentinel population filtering, the Compliance Audit
workflow, and DG2-S0-01 remain unauthorised and untouched. No RED opened. No code written.
