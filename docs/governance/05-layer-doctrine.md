---
document: Dynasty Genius Layer Doctrine
version: 1.2.1
last_updated: 2026-07-28
authority: SECTION-SCOPED — this file is NOT uniformly standing doctrine; see the two fields below
authority_section_1: standing doctrine — David-verbatim (§1.1 + §1.2), in force now
authority_section_2_onward: PENDING — agent-authored codification, under cockpit review, NOT David-ratified; do not cite as standing doctrine until he ratifies it
verbatim_source: David, 2026-07-28 21:04 — confined to §1 (both §1.1 and §1.2)
codification_author: Claude Code
codification_status: under cockpit review; not yet David-ratified
---

# Dynasty Genius Layer Doctrine

**Read the attribution before citing anything in this file.**

- **§1 is David's own words, verbatim — all of it, and nothing outside it.** Both §1.1 (his standing
  instruction) and §1.2 (the six layers) are his. No agent may paraphrase them into its own
  vocabulary, "clarify" them, or restate them in a summary that then gets cited in their place.
  **Quote them or point at them.**
- **§2 onward is agent-authored codification** — the authority placement, the ritual mechanics, and
  the failure record. Written by Claude Code to give §1 effect. It may be revised by the normal
  governance process; §1 may not.

**Status of §2 onward, stated honestly rather than assumed: agent-authored, under cockpit review, and
NOT yet ratified by David.** He ordered the memorialization and the hardening, and he later gave an
action word — neither is ratification of every agent-authored sentence here. This line is updated only
when a ratification actually happens, and it names the ratification when it does.

*(Three corrections recorded rather than smoothed — all of them the same defect wearing different
clothes: agent-authored text quietly acquiring David's authority.*
*v1.0.0 attributed the whole document to him — exactly the failure §1 bans.*
*v1.1.0 fixed the prose but placed David-verbatim text outside the §1 it had just declared the sole
verbatim section, and claimed a cockpit review and a ratification that had not happened. Fixed in
v1.2.0.*
*v1.2.0 still carried a file-scoped `authority: standing doctrine` header, which granted §2's
unratified codification the standing only §1 has earned. Fixed in v1.2.1 by section-scoping the
metadata. Found by Codex on the fifth review round.)*

---

## 1. David's words — verbatim

*(Everything in §1.1 and §1.2 is David's, recorded 2026-07-28 21:04. Nothing else in this file is.)*

### 1.1 His instruction on standing

> nothing is of higher priority than the memorialization of these rules and after the rules are in
> place - making them a ritual of how we work

### 1.2 The six layers

> 1) we ingest the data - we have a robust dataset available both paid and free and we can expand
> should we choose to. we must set up production grade pipelines that keep our data fresh and of
> high quality at all times
>
> 2) we curate - joins, transformations, loads, modeling, identity graphs, etc. - think of it as
> our bronze->silver->gold data layers. always clean and usable by whatever use case requires it.
> as much of this as it makes sense should be scheduled and automatic.
>
> -- Steps 1 and 2 are the foundation - if we don't have this our app WILL NOT WORK. we shouldn't
> be wasting cycles until we've built this foundation
>
> 3) our models - constantly benchmarking and trying to find edges against real results as they
> land. always trying new ways to improve accuracy and better predictability of future outcomes.
> the data science layer
>
> 4) the data analysis layer - we have all this clean data --- we need to constantly track trends,
> and analyze variables and cohorts, all different types of data analysis to spot edges and
> opportunities for me.
>
> 5) Context - we have a special advantage that we can see manager behavior and specific data
> trends of the 12 teams in this league - an analysis of each manager and overall league data is
> the next advantage point
>
> 6) Front-End - empowering me with layers 1-5.
>
> We cannot lose track of these layers. if we're struggling in layer 4 but we haven't fortified
> and tested layers 1 and 2, we're not thinking correctly.

---

## 2. Authority — resolved by domain, not by blanket precedence

*(Agent-authored codification.)*

Each governance document owns a **domain**. Conflicts are resolved by asking which domain the
question belongs to, never by one document overriding another wholesale.

| Document | Domain it owns |
| :-- | :-- |
| `00-product-constitution.md` | **Analytical truth** — what is true about football, what may be claimed, the No-Verdict Line |
| **`05-layer-doctrine.md`** | **Sequencing, investment priority, and the root-layer check** — what should be worked on, and whether a defect is being addressed at the layer that actually causes it |
| `01-north-star-architecture.md` | **Technical architecture** — engines, feature classes, data platform, contracts |
| `02-agent-operating-loop.md` | **Session workflow** |
| `03-code-hygiene-policy.md` | Code-hygiene mechanics |

**On genuine overlap, an agent stops, logs the conflict, and escalates** (02 §Authority Order,
§Escalation Triggers). It does not silently pick the more convenient rule, and it does not resolve
the overlap by citing this document's rank.

This doctrine **outranks every plan, spec, ticket, and backlog** on questions of what to work on
next: a layer-4 ticket does not acquire priority over a layer-1 hole by virtue of being written down.

**Priority is not authorization.** §3 explicitly permits upper-layer work. Establishing that
something is a priority never by itself authorises building it — David's word does that, and this
document changes nothing about who authorises actions.

---

## 3. The ritual

*(Agent-authored codification. Enforcement mechanics live in `02-agent-operating-loop.md`
§Layer discipline so they bind the working loop rather than sitting in a file read once.)*

**Rule 1 — every preflight names the layer.** State the **primary (presenting) layer** the work
serves. Multiple layers may be named when the work genuinely spans them, and **`cross-layer` or
`governance`** is a valid answer for work that governs how layers are chosen rather than sitting at
one. *(This document's own creation is `governance` — v1.0.0's single-layer rule could not express
that, which is how the defect was found.)*

**Rule 2 — the layers 1–2 dependency check, for work at layers 3–6.** Answer, on the record, as
three separate things:

1. **The check performed** — what was actually run or read, cited so another agent can rerun it.
2. **The result** — what it showed.
3. **The conclusion** — whether the work proceeds at the presenting layer, or whether it is a
   symptom of layers 1–2.

"It is genuinely at this layer" is a legitimate conclusion. The rule is that the question is **asked
and answered from evidence**, not assumed.

**Proportionality.** Where a framing artifact exists, its omission of the check is a **finding** the
independent reviewer raises. For mechanical work with no framing (a typo, a formatting pass, a state
update), a one-line preflight statement is sufficient — a rule that demands ceremony from trivial
work decays into a box-tick, which is the same death as a poster on a wall.

**A conclusion is not a licence to fix.** Concluding that a defect originates at layers 1–2 records a
finding; opening work on it is a separate thread needing David's word.

---

## 4. The failure that produced this — 2026-07-28

*(Agent-authored record. A rule without the failure that produced it decays into a poster.)*

**What happened.** The cockpit ran **multiple adversarial rounds** on a **layer-6** problem — the
wording shown for 113 players whose model value is withheld. The sequence is recorded in on-disk
review artifacts under `docs/agent-ledger/evidence/2026-07-28/`: framing v1 → an eight-finding
challenge → a disposition → framing v2 → a five-finding re-review → two rounds of wording options.
Careful work, correctly executed, adversarially reviewed.

*(Precision, because this document has already been wrong twice by overclaiming: that cycle is **not
complete** — `02` §Adversarial review pattern terminates only on the independent reviewer's explicit
CLEAR, the re-review returned NOT CLEAR, and the disposition is parked. Those artifacts are **on
disk, not committed**, at the time this sentence was written.)*

**What broke the premise.** David applied two sentences of football knowledge and asked why these
players could not be valued. Every agent had been working correctly *within its layer*. **Nobody had
asked whether the layer was right. David caught it and no agent did.** That is the failure this
doctrine exists to prevent.

**What the follow-up measurement established — and what it did NOT.**

*Proved.* In the artifact the API actually serves (`app/data/valuation_runtime/universe_pvo_runtime.json`,
`captured_at` `2026-07-28T13:30:04Z`, 12,203 rows), independently reproduced by two lanes:

| Field | Engine B | Engine A | Universe |
| :-- | --: | --: | --: |
| `nfl_draft_round` | **0 / 501** | 80 / 80 | 80 / 12,203 |
| `nfl_draft_pick` | **0 / 501** | 80 / 80 | 80 / 12,203 |
| `draft_class` | **0 / 501** | 80 / 80 | 80 / 12,203 |

*NOT proved, and stated plainly because v1.0.0 of this file asserted it:* that this absence is a
layer-1/2 hole, or a defect at all. **The probe proves field absence in a served artifact. It does
not establish intended materialization or a root layer.** Two governance facts cut against the quick
reading: `00-product-constitution.md` §Rookie Evaluation Rules frames draft capital as the strongest
**rookie** predictor, and `01-north-star-architecture.md` §Engine B expressly disallows *"rookie-only
pre-NFL features leaking into active-player training unless explicitly modeled as a prior."* Engine B
is the active-player forecast. The absence may be governance-compliant by design.

**Recorded, not opened.** Whether the field should be materialized for serving or analysis — a
different question from whether it is a training feature — is uninvestigated. It is a separate thread
requiring David's word. This document does not open it.

**The lesson survives the correction, and is sharper for it.** The original error was working a
layer-6 problem without checking beneath it. The second error, made while writing the rule against
the first, was **asserting a root layer without doing the check the rule demands.** Both are the same
failure. The check is cheap: the measurement that broke the premise ran in under a minute once
someone thought to run it.
