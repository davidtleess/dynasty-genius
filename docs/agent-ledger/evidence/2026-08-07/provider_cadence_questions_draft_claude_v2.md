# Provider cadence questions — v2. DRAFTED, NOT SENT.

**Author:** Claude Code, implementing lane · **Layer:** Layer 1 (ingest) inventory
**Authority:** repaired under David's deliberate repo-work word — ***"ok drive this through claude and
codex with a reasonable role for gemini too. commit and push when appropriate"*** — as scoped by
Codex to Layer 1 inventory/evidence.

> ## ⛔ NOT SENT. NO AUTHORITY TO SEND OR CONTACT.
> **No message has been sent. No support channel, contact form, email address or account has been
> used. No provider has been contacted in any form.** That word has **not** been given, and this
> document does not create it. **Sending is David's action alone.**

> ## ⚠ v1 IS PRESERVED BYTE-UNTOUCHED AND IS NOT SUPERSEDED BY REPAIR
> `provider_cadence_questions_draft_claude_v1.md` was written under an **ACCIDENTAL, REVOKED** paste —
> David: ***"wait - i just sent that to claude by accident."*** It is **not David-directed work**, is
> left **unedited**, and **v2 does not inherit its authority**. v2 exists because the scope defect in
> v1 is worth fixing on the record, **not** because v1 became valid.

---

## 1. What v1 got wrong, and why it matters

**v1 claimed it "Covers N1–N8". That was false.** It asked about **one** report — the Data Analysis
Tool export (**N6**) — while `N1–N8` is a **group spanning FIVE distinct upstream report families,
plus a derived table and our own capture ledger**.

**A single question about one family cannot close that row.** **Explicit FAMILY-LEVEL COVERAGE for all five families is required — regardless of how many replies or documents supply it.** ONE authoritative reply or one provider document MAY cover several or all five; what is not acceptable is coverage of one family being read as covering the row *(F2: this read "five families need five answers", which over-specified the MECHANISM when the contract is the COVERAGE)*.

| Catalog | Provider report family | A provider question? |
| :-- | :-- | :-- |
| **N1** | Game log | **YES** |
| **N2** | Roster / weekly | **YES** |
| **N3 + N4** | Play-by-play (**ONE** family, two tables) | **YES** |
| **N5** | Medical history | **YES** |
| **N6** | Data Analysis / player-season | **YES** |
| **N7** | `pp_identity_bridge` — **derived from the roster export, inherits N2** | **NO** |
| **N8** | `pp_capture` / `pp_pbp_capture` — **our own capture ledger** | **NO** |

**N7 and N8 must never appear in a provider question.** Asking a vendor about our derived table or our
ledger would be incoherent and would signal we do not know our own boundary.

---

## 2. DRAFT — Sleeper

*Covers N19, N18, N12/N13. The goal is **endpoint-family-specific publication semantics**, not polling
advice — the public documentation already gave the latter and it is a different clock under R3.*

> **Subject:** Server-side update semantics for specific read-only API endpoints
>
> Hello,
>
> I read a single private league of my own through the public API — read-only, well under the
> documented limits, roughly one pass a day.
>
> Your documentation covers **how often clients should call** (the per-minute limit, and fetching the
> player list no more than daily). My question is the other side of that: **when does Sleeper itself
> update the data server-side**, and does the answer differ by endpoint family?
>
> For each of these, is the data **published on a fixed schedule** (e.g. a nightly rebuild at a set
> time), or **written as events occur** (updated at the moment a manager acts)?
>
> - the global player list (`/players/nfl`)
> - league, rosters and users
> - drafts and traded picks
> - matchups
> - transactions
>
> If some are event-driven-on-write and others are batch, that distinction is exactly what I am
> trying to get right. If any of it is already documented somewhere I have missed, a pointer is
> perfect.
>
> Thank you,
> David

**Evaluation note — not part of the message.** An **attributable, unambiguous** answer of the form
*"rosters and transactions are written as events occur; the player list is rebuilt nightly"* is a
statement of **endpoint semantics** and **may qualify under M4 after review**. It must be
distinguished from two things that do **not** qualify: a vague **"real time"** or **"as data comes
in"**, and any restatement of **client polling advice**. **Whether a given reply qualifies is the
reviewer's judgment, not automatic.**

---

## 3. DRAFT — PlayerProfiler

*Covers all five report families. **N7 and N8 are deliberately absent.***

> **Subject:** How often is each data export refreshed?
>
> Hello,
>
> I am a subscriber and export several of your data products for my own analysis. I am trying to work
> out how often it is worth re-exporting each one, so I am not re-downloading unchanged numbers or
> missing a refresh.
>
> Could you tell me, **for each of these separately**, how often the underlying data is updated?
>
> - the **Data Analysis Tool** player-season export
> - the **medical history** export
> - the **game log** export
> - the **roster / weekly** export
> - the **play-by-play** export
>
> For each, three things would answer it completely:
>
> 1. Is there a **regular schedule** — weekly, after each game week, nightly — or is it updated **as
>    events occur**?
> 2. Does it differ **in-season versus off-season**? My current interest is the off-season.
> 3. Are **completed seasons ever revised** afterwards — corrections, reclassifications, metric
>    changes — or is a finished season stable once published?
>
> If there is a status or changelog page showing when each was last updated, a pointer to it would
> help as well.
>
> Thank you,
> David

**Note — not part of the message.** A status/changelog page is **supporting evidence, not
 necessarily an answer**: showing when data last changed need not state the **cadence**, the
 **seasonal variation**, or the **revision policy**. The three questions are asked in the message for
 that reason and are not delegated to a page. Question 3 matters beyond cadence: **if completed seasons are
revised, any historical export is a point-in-time artifact** and that bears on retention and on how
any archived export may be interpreted. It costs nothing to ask alongside the others. Nothing here
requests API access, bulk data, or anything beyond the subscription already held.

---

## 4. If David later authorizes contact

1. **Preserve the reply EXACTLY.** Store the verbatim text, the date, and who sent it. **Paraphrasing
   a provider statement into our vocabulary is how a hedged answer becomes a firm one** — the failure
   mode this catalog has caught repeatedly.
2. **Preserve provenance:** channel used, address or form, and the exact question sent, so a later
   reader can judge the answer against what was actually asked.
3. **Do not write a reply into the catalog directly.** It is new evidence: record it as a durable
   artifact, route it for review, and write it to a cell only if the reviewer judges it satisfies M4.
4. **A cadence answer closes at most the source-publish field for the families it names.** It does not
   close A-C, move a §1 checkbox, or authorize a scheduler, capture, or pilot.
5. **Coverage is judged per family, not per reply.** A reply closes only the families it
   explicitly covers — one authoritative document may cover several or all five, and one family's
   answer never stands in for the row.

---

## 5. Boundaries

1. **NOT SENT. No contact made. No authority to send exists.**
2. **v1 preserved byte-untouched**; v2 does not inherit its revoked authority.
3. **No automated provider route** is proposed, revived or implied by either draft.
4. **No catalog edit follows from this document.** All five member fields stay OPEN; **no §1 checkbox
   moves.**
5. These are **drafts for David to send, edit, or discard** — discarding is a legitimate outcome,
   since a reply may not satisfy M4 anyway (§2).

**H2 QB rushing remains a registered hypothesis UNDER TEST with no result.**
