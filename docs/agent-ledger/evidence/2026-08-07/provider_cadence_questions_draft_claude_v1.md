# Provider cadence questions — DRAFTED, NOT SENT

**Author:** Claude Code, implementing lane · **Layer:** Layer 1 (ingest) inventory
**David's instruction, verbatim:** *"Reconcile the catalog and board, and draft the provider
questions. Don't send them."*

> ## ⛔ NOT SENT. SENDING IS DAVID'S ACTION ALONE.
> These are drafts on disk. **No message has been sent, no support channel opened, no account or
> contact form used, no email addressed.** Sending is contact with an external party on David's
> behalf and is his action, not mine — and he explicitly withheld it. **Nothing here authorizes a
> provider call, an automated route, a scheduler, a capture, a catalog edit, or a checkbox move.**

---

## 1. Why these exist, and what would actually close the field

Every source-publish cadence in the catalog was obtained from **provider-published documentation or
scheduling config**. That route was tried on both open clocks for the first time on 2026-08-07 and
came back **negative — bounded to the searches run**: the inspected public Sleeper API page carries
no server-side publication cadence, and no PlayerProfiler publish-cadence statement was found in
public search.

**What remains untried is asking the provider directly.** Codex's ruling is explicit that the public
negative *"does not prove that no declaration exists or can be obtained."*

**⚠ READ THIS BEFORE SENDING — A REPLY MAY NOT CLOSE ANYTHING.** Under §6A/M4 a source-publish value
must be **independently verified as the measured upstream change rhythm, or as authoritative endpoint
semantics.** An informal answer from a support agent is **not automatically either.** Whether a given
reply qualifies is a **reviewer judgment, not a foregone conclusion** — so the honest expectation is:

| Reply shape | Likely disposition |
| :-- | :-- |
| A **published schedule or docs page** the provider points to | strongest; plausibly closes the field |
| A **specific, unambiguous statement of publish times/frequency** attributable to the provider | candidate; needs review |
| *"It varies"* / *"in real time"* / *"as data comes in"* | **does not close** — that is a description, not a cadence |
| Polling advice (*"check once a day"*) | **does not close** — a different clock under R3; this is what the public docs already gave |
| No reply | the field stays `UNVERIFIED`; nothing is lost |

**Both questions are therefore written to make the useful answer easy to give and the unhelpful
answer easy to recognize.** They ask for a *schedule*, and they say why.

---

## 2. DRAFT — Sleeper

*Covers the four rows the branch-(b) ruling left open on this provider: N18, N12/N13, N14b, N19.*

> **Subject:** Question about server-side update frequency for the read-only API
>
> Hello,
>
> I use the public Sleeper API to read data for a single private league of my own — read-only, well
> under the documented rate limits, no writes and no automation beyond a once-daily read.
>
> My question is about **how often Sleeper itself updates the data server-side**, rather than how
> often I should call. The documentation covers the latter (the 1000-calls-per-minute guidance, and
> the note to fetch the player list no more than once a day), but I could not find anything about the
> former.
>
> Specifically, for these endpoint families, is there a published or internal update schedule you can
> share — for example a fixed interval, a nightly batch, or event-driven-on-write?
>
> - the global player list (`/players/nfl`)
> - league, rosters and users
> - drafts and traded picks
> - matchups
> - transactions
>
> Even a rough answer helps — for instance, *"rosters and transactions update immediately when a
> manager acts; the player list is rebuilt nightly at approximately HH:MM UTC."* What I am trying to
> avoid is assuming a refresh rhythm that does not match how you actually publish.
>
> If any of this is already documented somewhere I have missed, a pointer is just as good.
>
> Thank you,
> David

**Notes for David, not part of the message:**
- **It asks about publication, not polling** — that distinction is exactly what the public docs did
  not answer, and stating it up front is what makes the question answerable.
- It **volunteers our usage as modest and read-only** so the question does not read as scoping an
  aggressive scraper.
- The example answer shows the *shape* of a useful reply, which materially raises the chance of
  getting one.
- **"Event-driven-on-write" is offered as a legitimate answer.** If they confirm it, that is a
  provider statement about publication — materially stronger than our inference from event
  timestamps, which cannot distinguish event-driven from periodic publishing.

---

## 3. DRAFT — PlayerProfiler

*Covers N1–N8. Scoped to `player_season`, the report the pilot targets.*

> **Subject:** How often is the Data Analysis Tool export refreshed?
>
> Hello,
>
> I am a subscriber and use the Data Analysis Tool to export player-season data for my own analysis.
>
> Could you tell me **how often the underlying data behind that export is updated**? I am trying to
> work out how often it is worth re-exporting, so I am not re-downloading the same numbers or missing
> a refresh.
>
> A few specifics, if you know them:
>
> - Is there a regular schedule — for example weekly, or after each game week?
> - Does it differ **in-season versus off-season**? My current interest is the off-season.
> - Are prior seasons ever **revised** after the fact — corrections, reclassifications, metric
>   changes — or are completed seasons stable once published?
>
> If there is a status or changelog page that shows when data was last updated, that would answer it
> completely.
>
> Thank you,
> David

**Notes for David, not part of the message:**
- **The third question is the one I would most want answered** and it is not in the pilot at all: if
  completed seasons are ever revised, that has consequences for retention and for how any historical
  export is interpreted. It costs nothing to ask alongside the others.
- The framing — *"so I am not re-downloading the same numbers"* — is true and is the subscriber's
  natural reason to ask. **It implies no automated access**, which matters given that both legacy
  scripted routes were retired at `fd260d4` and no automated route is proposed.
- **Nothing in it requests API access, bulk data, or anything beyond the subscription David already
  has.**

---

## 4. If a reply arrives

1. **Do not write it into the catalog directly.** A provider reply is new evidence and goes through
   the normal cycle: recorded as a durable artifact, then reviewed, then written to the cell if the
   reviewer judges it satisfies M4.
2. **Quote it exactly.** Paraphrasing a provider statement into our vocabulary is how a hedged answer
   becomes a firm one — the failure mode this catalog has caught repeatedly.
3. **A cadence answer closes at most the source-publish field for the named endpoints.** It does not
   close A-C, move a §1 checkbox, authorize a scheduler or capture, or open Layer 2.
4. **A PlayerProfiler answer does not make the N6 pilot unnecessary or necessary** — those are
   separate questions, and the pilot's own prerequisite remains unauthorized.

---

## 5. Boundaries

1. **NOT SENT.** No channel used, no address applied, no account touched.
2. **No automated provider route** is proposed, revived or implied by either draft.
3. **No catalog edit follows from this document**; all five source-publish fields stay OPEN.
4. **No §1 checkbox moves.**
5. These are **drafts for David to send, edit, or discard** — including discarding them entirely,
   which is a legitimate outcome given that a reply may not satisfy M4 anyway (§1).

**H2 QB rushing remains a registered hypothesis UNDER TEST with no result.**
