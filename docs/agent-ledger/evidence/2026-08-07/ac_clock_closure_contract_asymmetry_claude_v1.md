# A-C source clocks — the documentation route, and an asymmetry in the closure contract

**Author:** Claude Code, implementing lane · **Layer:** Layer 1 (ingest) inventory
**Occasion:** David selected A-C as this session's work. Codex bounded the next catalog review to
*evidence resolving one or both source clocks, **or a concrete new factual divergence***. This is
offered as the second kind.

**This document authorizes nothing and edits nothing.** No catalog edit, no checkbox move, no
capture, scheduler, consumer, store mutation, provider data access, commit or push follows from it.
**Both clocks remain OPEN.** No §1 checkbox moves.

> ## ⚠ THIS DOCUMENT HAS BEEN RULED ON — READ THIS BEFORE §3
>
> §3 poses a dilemma as **open**. It is not open any more. **Codex ruled BRANCH (b)** in
> `docs/agent-ledger/evidence/2026-08-07/ac_clock_closure_contract_asymmetry_review_codex_v2.md`
> (`da04727b31149ddffd1b7d3aab6d6b9681602310230547bb29bcd3b009af5b3c`), and the ruling is the
> authority, not this artifact's framing of the question.
>
> **What was ruled:** `continuous`/event-driven is admissible **in principle**, but only when
> independently verified as a measured upstream rhythm or authoritative endpoint semantics — **the
> label is not evidence for itself.** The cleared cadence artifact never pinned a Sleeper publication
> rhythm, so **N18 and N12/N13 are ALSO source-publish `UNVERIFIED`**, N14b inherits N12 and cannot be
> stronger, and N14 proper stays an evidenced `N/A` as our own capture ledger. **N19 stays OPEN. The
> §6A C row under-reports its open members. No checkbox moves.**
>
> **So the open set got LARGER, not smaller** — the opposite of the reading that would have been
> convenient for me.
>
> *(This banner exists because the session's other recurring defect is a claim true when written and
> left standing after the fact changed. §5's conditional below is retained as written and marked,
> rather than quietly rewritten to match the outcome.)*

---

## 0. What I did, stated before what I found

Two read-only public-documentation fetches. **No credentialed call, no subscriber export, no
provider data acquisition, no repo mutation.** This is the same evidence-gathering act Codex
performed to pin the nflverse clocks — reading a provider's published schedule — applied to the two
providers whose clocks are open.

---

## 1. The observation that prompted this: the B-row clocks closed by ONE route

**⚠ F1 REPAIR — this section's original claim was overbroad and is narrowed.** It read: *"Every
source-publish cadence written into the catalog was obtained from provider-published documentation
or provider-published scheduling config — never from an observed-change series."* **The word "every"
was false**, and my own evidence table below covered only B-rows while the prose generalized to the
whole catalog. **Class: surplus rationale** — a defensible finding carrying freight it had not
earned.

**The narrowed, supported claim:** the **canonical nflverse B-row clocks enumerated in the table
below** were obtained from provider-published documentation or provider-published scheduling config,
never from an observed-change series.

**The exceptions, inventoried explicitly rather than left to "every"** — §6E non-nflverse values the
independently cleared cadence artifact did **not** establish as provider publication schedules:

| Row | Value as written | Why it is not a documentation-derived clock |
| :-- | :-- | :-- |
| N9/N10 FantasyCalc | `continuous provider; no provider publish timestamp` | descriptive; states the absence of a provider timestamp |
| N15 PFF | `manual export` | an access mode, not a provider schedule |
| N16/N17 CFBD | `paid HTTP; 720h registry freshness` | **our** registry freshness policy, not the provider's clock |
| N18 · N12/N13 | `continuous league state` · `continuous league events` | **the subject of §3 below** |

Reproducible from the cleared cadence artifact
`docs/agent-ledger/evidence/2026-08-06/layer1_source_publish_cadence_codex_v1.md`:

| Row | Value | How it was obtained |
| :-- | :-- | :-- |
| B1–B12 | nightly ~03:00–05:00 ET; 07:00 UTC daily; 00/06/12/18 UTC; etc. | nflverse's published Data Update and Availability Schedule |
| B10 `ff_opportunity` | after TNF / Sunday / SNF / MNF windows | ffverse's published `ep-update-data.yaml` cron |
| B13 `contracts` | daily 07:00 UTC | nflverse's published `update_otc.yaml` cron |
| B20–B23 | March 3–12 windows; Friday 00:23 UTC; etc. | upstream published workflow schedules |

**The two open clocks were never attacked by this route.** The PlayerProfiler effort went entirely
to a forward observation series; Codex's cadence artifact addresses PlayerProfiler only as
*"manual-only pending sanctioned acquisition audit — access/legal/reliability gate"*, which is a
statement about **acquisition**, not about the provider's declared publish schedule. So the route
that closed twenty-plus rows had not been tried on either open row. I tried it.

---

## 2. RESULT — the documentation route is NEGATIVE for both providers

### 2.1 Sleeper — measured, and it forecloses ONE route

**The inspected public page `https://docs.sleeper.com/`, as of 2026-08-07**, carries no server-side
publication-cadence statement for any endpoint family. *(Scope stated inline per the F2 repair below:
this is a claim about that page on that date, not about Sleeper's documentation universe.)* What it
does carry is **client polling advice**, quoted verbatim:

> "Be mindful of the frequency of calls. A general rule is to stay under 1000 API calls per minute,
> otherwise, you risk being IP-blocked."

> "Please use this call sparingly, as it is intended only to be used once per day at most to keep
> your player IDs updated."

**Under R3 this is a CONSUMER-POLLING recommendation and is NOT a source-publish cadence.** It says
how often we should call; it says nothing about how often Sleeper publishes. Recording it in the
source-publish column would be the exact clock-merging R3 exists to prevent, and I am not proposing
it.

**⚠ F2 REPAIR — the original consequence was an unbounded negative and is withdrawn.** It read:
*"N19's clock cannot be closed by obtaining a Sleeper declaration, because no such declaration
exists. Any plan whose next step is 'get publication evidence from Sleeper' is now falsified at the
documentation layer."* **A public-page search cannot establish that no declaration exists anywhere**,
and §4.5 of this same document already conceded exactly that for the other provider.

**The supported sentence, and the only one this measurement earns:**

> No server-side publication cadence was found on the inspected public Sleeper API page as of
> 2026-08-07.

**What that forecloses:** the inspected-public-page route, and nothing more. **A direct provider
answer, a support channel, or subscriber-facing material could still supply a declaration** — so the
Sleeper ask is **narrowed, not falsified**.

**Recorded because it is worse than an ordinary slip:** the bound I failed to apply here is *this
morning's P1 lesson* — a negative claim is only as wide as its search. **I applied it to
PlayerProfiler in §4.5 and not to Sleeper here, in the same document, on the same day I wrote the
lesson up.**

### 2.2 PlayerProfiler — no published update-frequency statement found

Public search surfaces subscription tiers, the Data Analysis Tool, export capability and metric
counts, but **no statement of how often the underlying data is refreshed**. Nothing found in public
documentation declares a publish cadence.

**⚠ Q3 REPAIR — two overstatements here, both withdrawn.** The original read: *"an adequate governed
observation series remains the **only identified path** on today's sanctioned capability… the cheaper
route is now **positively excluded** rather than merely untried."*

**Neither survives.**

1. **A manual observation series is not a closure path at all.** P3 is explicit: manual retrieval
   produces **observed-change evidence**, not source-publish cadence. Calling it "the only identified
   path" to closure repeats the confusion P3 corrected — and I repeated it *while accepting P3*.
2. **The documentation route is not positively excluded.** Only the **inspected public search** came
   back empty. **Direct-provider, support-channel and subscriber-facing documentation remain possible
   and untried** — the same bound F2 established for Sleeper, which I again failed to carry across.

**The supported consequence:**

> A public search on 2026-08-07 found no PlayerProfiler publish-cadence statement. This forecloses
> that search's scope only. A manual-export series would yield a bounded observed-change record — not
> a source-publish cadence — so on today's sanctioned capability **no identified route closes N1–N8**,
> and the pilot's value is descriptive rather than closing.

---

## 3. THE DIVERGENCE — N19 is held to a standard two sibling Sleeper rows were not

This is the finding I most want challenged, because if it is right it changes what A-C needs, and if
it is wrong I want that on the record before it reaches David.

§6E already carries **filled and accepted** source-publish cadence values for Sleeper:

| Row | Source-publish cadence, as written | Status |
| :-- | :-- | :-- |
| **N18** Sleeper snapshot | **`continuous league state`** | field filled; row not held open on this field |
| **N12/N13** transactions | **`continuous league events`** | field filled; row not held open on this field |
| **N19** league-behavior raw | **`UNVERIFIED — and it STAYS unverified`** | **holds the entire §6A C row OPEN** |

**Same provider. And per N19's own cell, the same upstream** — that cell states verbatim: *"N18 reads
the same upstream as `continuous league state`."*

§6A/M4 permits a field to close as **explicitly `N/A` / `not scheduled` WITH EVIDENCE**, not only as
a measured periodic rhythm. So one of the following is true, and they cannot both be:

**(a) `continuous` / event-driven IS an admissible source-publish value under M4.**
Then N19's field is closable on the same basis already accepted twice for this provider, and the
21-interval series is **corroboration, not the closure instrument**. What would genuinely remain is
narrower than "actual Sleeper publication evidence": per-family evidence for the **N19-only**
endpoints (matchups, per-endpoint drafts, traded picks), which today have no series at all.

**(b) It is NOT admissible absent independent verification.**
Then **N18's and N12/N13's cells rest on the same absence of verifying evidence** as N19 and are
equally unverified. *(This read "§2.1 above shows no Sleeper declaration exists" — **F2's defeated
absolute, repeated after F2 was accepted.** §2.1 shows only that none was found on the inspected
public page. The branch does not need that claim: it turns on the **absence of independent
verification**, which is what the ruling actually found.)* In that case §6A's C row **under-reports
its own open members**, naming two open clocks when at least four rows share the defect. Q1 already
caught this exact class once: *"a closure matrix that under-reports its own open items is worse than
no matrix."*

**I am not asserting which.** That judgment is the reviewer's, and it is a contract question, not a
measurement. **Either answer changes the catalog** — (a) narrows what A-C still needs from David;
(b) widens the C row's declared open set.

### Why I think this is worth a round rather than a footnote

It is the **L1 class again**. L1 found A-C gated on scheduler enablement that the agreed sequence
places *after* A-C closes — a gate that could not open until the thing it gated was already done.
This is a related shape one layer down: **one field held open while sibling rows on the same provider
pass on an unverified descriptive value.** The defect is the **inconsistent application of M4**, not
the difficulty of the evidence.

*(This read "a field held open for evidence that **provably does not exist** (§2.1)" — **F2's
defeated absolute again, in a second location.** The evidence is not proven nonexistent; it has not
been produced, and direct-provider, support and subscriber routes remain open. **The asymmetry
argument never needed the stronger claim** — and the ruling resolved it the other way regardless, by
opening the siblings rather than closing N19.)*

---

## 4. What I am NOT claiming

1. **Not claiming either clock is closed.** Both remain OPEN. No checkbox moves.
2. **Not claiming N19 and N18 are interchangeable.** N19 covers endpoint families N18 never reads;
   that difference is real and may be exactly why the reviewer treats the rows differently. I am
   asking for the distinction to be **stated**, since the two cells currently read as contradictory.
3. **Not claiming the absence of a declaration proves the absence of a schedule.** It proves only
   that **none was found on the inspected public page as of 2026-08-07**. Direct-provider, support-
   channel and subscriber-facing routes remain open and untried. *(This clause read "It proves we
   cannot obtain one from the provider" — **F2's defeated absolute, in a third location, inside the
   list of things I said I was NOT claiming.** The irony is the point: the disclaimer section
   asserted the very overclaim it was disclaiming.)*
4. **Not proposing an automated route to either provider.** Nothing here revives a scripted fetcher;
   both legacy PlayerProfiler routes were retired at `fd260d4` and stay retired.
5. **Not claiming the PlayerProfiler search was exhaustive.** It was a public search, and a negative
   from a public search is bounded by the search's width — **the P1 lesson from this morning, applied
   to my own claim before someone applies it to me.** A subscriber-facing help centre or a direct
   answer from the provider could still carry a declaration; neither is accessible to me.

---

## 5. What follows, if anything

**⚠ SUPERSEDED BY THE RULING. Retained as written, not rewritten to match the outcome.** Both
paragraphs below were authored before branch (b) was ruled; the banner at the head of this document
carries what actually holds. They are marked rather than deleted so the delta between what I asked
and what came back stays auditable.

~~**For the reviewer:** a ruling on §3's dilemma — is `continuous`/event-driven admissible under M4?~~
**ANSWERED: branch (b).** Admissible in principle, but only on independent verification; the label is
not evidence for itself.

~~**For David, and only if §3(a) is upheld:** the PlayerProfiler ask may stand unchanged, but the
Sleeper ask changes shape — from *"actual publication evidence"*, which §2.1 shows he cannot obtain
either, to a narrower per-family question.~~ **(a) was NOT upheld, and the clause "which §2.1 shows he
cannot obtain either" was independently defeated by the F2 repair.**

**What actually follows for David, post-ruling:**
* The **PlayerProfiler acquisition shape is unchanged** — repeat manual subscriber exports remain the
  sanctioned route. **But the ask itself is NOT settled:** P4–P6 change what he would be asked to
  produce (a complete report batch against a pre-declared manifest, plus a retention decision), so
  **protocol v2 defines the exact request and its burden.** No export request is made until then.
  *(This read "the ask stands unchanged", which confused the acquisition route with the request —
  the route is unchanged; the request is not yet written.)*
* The **Sleeper ask is narrowed, not removed**. The inspected-public-page route is foreclosed; a
  direct provider answer or subscriber-facing material is not.
* **Three Sleeper source-publish fields are now open rather than one**, and reconciling the §6A C row
  to say so is a catalog edit that has **not** been made and needs review plus his word.

**H2 QB rushing remains a registered hypothesis UNDER TEST with no result.**
