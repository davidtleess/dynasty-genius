---
document: Dynasty Genius Layer Doctrine
version: 1.3.0
last_updated: 2026-07-30
authority: SECTION-SCOPED — this file is NOT uniformly standing doctrine; see the two fields below
authority_section_1: standing doctrine — David-verbatim (§1.1 + §1.2 + §1.3), in force now
authority_section_2_onward: PENDING — agent-authored codification, under cockpit review, NOT David-ratified; do not cite as standing doctrine until he ratifies it. The 2026-07-30 order amendment did NOT ratify it.
verbatim_source: David, 2026-07-28 21:04 (§1.1 + §1.2) and David, 2026-07-30 19:05 relayed verbatim via Tower (§1.3) — confined to §1
layer_numbering_in_force: 2026-07-30 order — 1 ingest · 2 curate · 3 models · 4 context · 5 data analysis · 6 front-end. Any layer reference dated before 2026-07-30 uses the 07-28 order, in which 4 and 5 are transposed. See §5.
codification_author: Claude Code
codification_status: under cockpit review; not yet David-ratified
---

# Dynasty Genius Layer Doctrine

**Read the attribution before citing anything in this file.**

- **§1 is David's own words, verbatim — all of it, and nothing outside it.** §1.1 (his standing
  instruction), §1.2 (the six layers) and §1.3 (his 2026-07-30 order amendment) are his. No agent may
  paraphrase them into its own vocabulary, "clarify" them, or restate them in a summary that then gets
  cited in their place. **Quote them or point at them.**
- **§2 onward is agent-authored codification** — the authority placement, the ritual mechanics, the
  failure record, and the 2026-07-30 numbering guidance. Written by Claude Code to give §1 effect. It
  may be revised by the normal governance process; §1 may not.
- **§1.2 and §1.3 use different numbering, and §1.2 has deliberately NOT been renumbered.** His
  07-28 list is preserved exactly as he wrote it. The order in force, and how to read any layer
  number anywhere in this repo, is **§5**. Read it before citing a layer by digit.

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

*(Everything in §1.1, §1.2 and §1.3 is David's. §1.1 and §1.2 were recorded 2026-07-28 21:04; §1.3
was given 2026-07-30 19:05 and relayed verbatim via Tower. Nothing else in this file is his.)*

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

### 1.3 His amendment to the order — 2026-07-30

*(David, 2026-07-30 19:05, relayed verbatim via Tower. Reproduced exactly as given, including its
typing. **§1.2 above is deliberately left unedited** — his 07-28 words are not rewritten to fit a
later decision.)*

> fine - we can swith 4 and 5. but as i said everything must start with a robust and complete
> layer 1 and 2

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
next: an **upper-layer** ticket does not acquire priority over a layer-1 hole by virtue of being
written down. *(This sentence read "a layer-4 ticket" until 2026-07-30. The digit was illustrative,
not load-bearing, and it became ambiguous when 4 and 5 were transposed — so it was replaced with the
numbering-neutral word rather than renumbered. Recorded here rather than changed silently; see §5.)*

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

---

## 5. The 2026-07-30 order amendment — what changed, why, and how to read a layer number

*(Agent-authored codification, carrying the same PENDING status as §2–§4. **The amendment itself is
§1.3 and is David's own word, in force on his authority.** This section records its effect; it does
not add to it. Appended as §5 rather than renumbering §2–§4, because `02-agent-operating-loop.md`,
`CLAUDE.md` and `AGENT_SYNC.md` cite those section numbers and renumbering would silently break every
one of them.)*

### 5.1 The order in force

| # | Layer | Moved? |
| --: | :-- | :-- |
| 1 | Ingest | — |
| 2 | Curate | — |
| 3 | Models | — |
| **4** | **Context — the twelve managers, league behaviour** | **was 5** |
| **5** | **Data analysis — trends, variables, cohorts** | **was 4** |
| 6 | Front-end | — |

**Only 4 and 5 were transposed. Layers 1, 2, 3 and 6 are identical in both schemes.**

### 5.2 What did NOT change, restated because he restated it

**Everything starts with a robust and COMPLETE layers 1 and 2.** §1.3 says so in the same sentence
that grants the swap, and §1.1's standing instruction and §1.2's foundation ruling are untouched.
**The swap re-ranks what happens AFTER the foundation. It moves nothing ahead of it**, and it is not
authority to begin layer-4 context work.

### 5.3 The reasoning — attributed honestly

**This subsection is NOT David's verbatim words.** His reasoning was relayed by Tower on 2026-07-30
in Tower's wording; only §1.3 is his. It is recorded because a doctrine that carries a decision
without its reason decays into a poster (§4's lesson):

> Generic trend and cohort analysis is where every public tool in this category already competes,
> while league-behaviour context cannot be copied because it requires HIS league — and it depends far
> more on layer 1 than on generic analysis. Ordered the old way, the roadmap goes through the crowded
> room first.

### 5.4 How to read any layer number in this repo

**Every layer number written before 2026-07-30 uses the 07-28 order.** The rule is mechanical:

- A **pre-2026-07-30** reference to **layer 4** means *generic data analysis* — **now layer 5**.
- A **pre-2026-07-30** reference to **layer 5** means *context / manager behaviour* — **now layer 4**.
- References to layers **1, 2, 3, 6** need no translation in either direction.
- From 2026-07-30, cite the new order; where ambiguity would cost a reader, name the scheme.

**Annotation of §1.2, made here rather than in his text:** where his 07-28 list numbers *"4) the data
analysis layer"* and *"5) Context"*, and where his closing sentence says *"if we're struggling in
**layer 4** but we haven't fortified and tested layers 1 and 2"*, he was using the 07-28 numbering —
that layer is **now layer 5**. **His sentences are preserved exactly and are not renumbered.** The
point that closing sentence makes is about the foundation and survives the swap unchanged.

### 5.5 Mechanics unaffected by the swap

§3's **layers 1–2 dependency check applies to work at layers 3–6**. Both endpoints of that range are
unmoved, so the rule's scope is identical under either numbering and needs no amendment. §4's failure
record concerns a **layer-6** problem and **layers 1–2** — also unmoved.

### 5.6 Repo artifacts that now carry an ambiguous layer digit — FLAGGED, NOT EDITED

Measured 2026-07-30 by grep over `*.md` and `*.py`. **These files were deliberately not edited**;
this list exists so a reader tomorrow knows to apply §5.4 rather than guess. Every hit below is a
pre-2026-07-30 reference and therefore uses the 07-28 numbering.

| Artifact | Digit used | Reads as, under the order in force |
| :-- | :-- | :-- |
| `AGENT_SYNC.md:120` | layer 5 | **layer 4** — transactions never ingested, so context has no substrate |
| `docs/agent-ledger/2026-07-29.md` (5 refs) | layer 5 | **layer 4** — `activity_recency_score = 0.0`; one preflight layer-naming at line 287 |
| `docs/agent-ledger/evidence/2026-07-29/layers_1_2_census_claude_v1.md` (5 refs) | layer 5 | **layer 4** — the no-substrate finding and the named edge |
| `docs/agent-ledger/evidence/2026-07-29/layer_1_2_inventory_claude_v1.md` (2 refs) | layer 5 | **layer 4** — the layer-5-symptom / layer-1-gap conclusion |
| `docs/agent-ledger/evidence/2026-07-29/minimum_ingestion_contract_proposal_claude_v2.md` | layer-5 gap | **layer 4** |
| `docs/agent-ledger/evidence/2026-07-30/stream_declarations_claude_v1.md`, `_v2.md` | layer 5 | **layer 4** — manager behaviour has no substrate |

**Notably, every ambiguous digit found in the repo means *context* — the layer that just moved up.**
That is the amendment's own subject, and it is the reason this flag list exists rather than a note.

**Not a doctrine reference, checked and excluded:** `docs/superpowers/specs/2026-06-02-gemini-enforced-controls-design.md:73` ("Layer 4; docs") predates this doctrine by
almost two months and uses the word in an unrelated sense. Frontend hits under `frontend/` are
z-index/visual layers, not doctrine layers.

### 5.7 What this amendment did NOT do

**It did not ratify §2 onward.** David amended the order inside §1; the agent-authored codification in
§2–§5 remains **PENDING his ratification and NOT binding**, exactly as before. An instruction to
change his own doctrine is not a ruling on ours — and this file has already recorded three separate
occasions of agent-authored text quietly acquiring his authority. This is the fourth chance to make
that mistake and it is declined here in writing.
