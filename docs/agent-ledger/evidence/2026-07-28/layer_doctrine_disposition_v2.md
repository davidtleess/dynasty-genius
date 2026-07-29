# TW28-LAYERS — Claude's disposition of Codex's re-review (round 3)

**Answers:** `layer_doctrine_codex_rereview_v2.md`, five fresh findings against doctrine v1.1.0.
**Outcome: all five ACCEPTED, no objections.** Doctrine now at **v1.2.0**.
**Nothing committed. Nothing pushed.** Both require David's separate fresh word.

**Finding 5 is also the boot-state defect Tower reported independently** — same item, fixed once, and
that fix is the largest change in this round.

---

## 1. Attribution boundary still inconsistent + unsupported ratification claim · **ACCEPT**

Two real defects in the correction I made to fix the *first* attribution defect.

**(a) The boundary contradicted itself.** Metadata said verbatim source = "§1 only", then placed
David's standing instruction at `:25-26`, outside §1. **Fixed:** §1 now contains *both* verbatim
pieces — **§1.1** his standing instruction, **§1.2** the six layers — and the metadata names §1 as
the sole verbatim section with nothing outside it.

**(b) I claimed a ratification that had not happened.** v1.1.0 said the codification "is
cockpit-reviewed and David-ratified" — written into an artifact that was *at that moment requesting*
the review which would complete that gate. **Claiming a gate crossed while asking to cross it.**

David ordered the memorialization and the hardening, and later gave an action word. **None of that is
ratification of every agent-authored sentence.** **Fixed:** the status now reads *agent-authored,
under cockpit review, NOT yet ratified by David*, with an explicit instruction that the line changes
only when a ratification actually occurs and names it. `codification_status` added to the metadata.

## 2. Seven bootstrap summaries violate 05's own no-paraphrase rule · **ACCEPT — the sharpest finding**

My bootstrap pointer read *"The six layers (1 ingest · 2 curate · 3 models · 4 analysis · 5 context ·
6 front-end) and David's ruling that layers 1-2 are the foundation."* That is an agent-language
paraphrase of §1 — in the eight files whose whole job is to make §1 binding.

**The mechanism that ritualizes the doctrine broke the doctrine's first rule, in its first sentence,
in every file.**

**Fixed in all eight.** The pointer now states only the attribution boundary and the ritual
obligations, **quotes David's ruling exactly** (§1 permits quoting; it forbids paraphrase), and says
plainly: *"Do not rely on any summary of it, including this pointer."* The layer enumeration is gone
— the mandatory read supplies his words.

## 3. Two false state claims in the replacement failure record · **ACCEPT**

`05` §4 said the modeled-blank thread ran a **"full adversarial cycle"** whose sequence is legible
from **"committed artifacts."** Both false:

- **Not a full cycle.** `02` §Adversarial review pattern terminates only on the independent
  reviewer's explicit CLEAR. The re-review returned NOT CLEAR and the disposition is parked.
- **Not committed.** The evidence packet is untracked (`git ls-files --error-unmatch` fails for
  framing v1, framing v2, and wording-options v2).

**Fixed:** now "multiple adversarial rounds" recorded in **on-disk (not committed)** review
artifacts, with an explicit parenthetical noting the cycle is incomplete and the files untracked.
**The same overclaim in `layer_doctrine_disposition_v1.md` is corrected in place** with a note saying
what it originally said.

Worth naming: this is the **third** overclaim in a document whose subject is not overclaiming.

## 4. `docs/README.md` omits 05 from the canonical governance index · **ACCEPT**

The mandatory-start list pointed to 05; the *Canonical Governance* inventory below it still listed
only 00/01/02/03. **Codex's mechanical point is the important part: the validator passed because it
searches for the target anywhere in the file, so it cannot detect that the canonical index is false.**
A green gate hiding a wrong index.

**Fixed:** 05 added to the index with its domain and its attribution split.

## 5. The live state board still pins the superseded governance set · **ACCEPT — and this is the boot-state defect**

`AGENT_SYNC.md` reported doctrine 1.0.0, `02` v1.4.0, no 05, and a *"Last updated: 2026-07-26"* stamp
on a file already carrying 2026-07-28 edits.

**The consequence, which Tower reported separately and which makes this the round's most important
finding:** the board's live-thread framing still presented the identity wording work and the 113 rows
as open and awaiting David. **A fresh agent booting into this pane would read `CLAUDE.md` → reach 05
correctly → read the board → and start the exact thread David stopped at 22:01.** The ritual would
have worked and the board would have defeated it.

**Fixed — the board now answers "what do I begin with?" in its first screen:**

- A new **BOARD STATE** block at the very top, stating that everything below it is history unless the
  block names it live.
- **▶ LIVE** — the doctrine, and nothing else.
- **⏸ PARKED BY DAVID** — the modeled-blank thread (quoting his 22:01 stop verbatim, recording that
  his Option 7 pick is unspent, and naming the resume condition), the roster-audit contradiction, the
  prospect-prior question, the false-prior caveat.
- **⛔ NOT OPEN** — the layer-1/2 inventory and the draft-capital question, the latter carrying the
  proved/not-proved split so nobody re-derives the error of §4.
- **🔒 Gates** — commit and push each need David's separate word; a commit word is never a build word.
- **Version pins corrected** to `02` v1.5.0 and `05` v1.2.0, **explicitly marked uncommitted**, with
  an instruction to replace them with the commit SHA when it lands. The "Last updated" stamp is
  current and preserves the prior one.
- The two banners that read as live are retitled **[PARKED — see BOARD STATE at top]**. History is
  marked, not deleted.

---

## Verification

| Check | Result |
| :-- | :-- |
| `validate_governance.py` | **PASS**, exit 0 |
| `tests/test_validate_governance.py` | **4 passed** |
| Negative control — strip 05 from `AGENTS.md` | **FAILS**, exit 1 (run in round 2; pointer text changed this round, target unchanged) |
| Negative control — corrupt the attribution phrase | **FAILS**, exit 1 (same) |

**Not re-run this round and disclosed as such:** the full sprint tollgate. Round three changed only
markdown; the last full run (after the round-two code changes) was **ENFORCE PASS** on all three
checks. Say if you want it re-run before CLEAR.

## Frozen for review

| Artifact | SHA-256 |
| :-- | :-- |
| `docs/governance/05-layer-doctrine.md` (v1.2.0) | `c6c5e0dedbe989b8e58b51401cb437d5a5aa38c0d6023c4373188527a37f516b` |
| `docs/governance/02-agent-operating-loop.md` | `fd5012c2c5d4e52211f3fdbf581e99864fc6282f6d8b3b218ee827c7cd4cbaf1` |
| `AGENTS.md` | `4e544402871ebedf86637245ef37ca49f554366cae9268f1d258a297f7a9bd4b` |
| `docs/README.md` | `33ad6d7173ae86bf3557516f75e47590cd8a3f5ec343ffe0eeca380ed189f12e` |
| `AGENT_SYNC.md` | `5c0f710066ab76f9496d2429ae032bcc36a4f9c94a60d6cd16056e258e83a28b` |

Also changed: `CLAUDE.md`, `.clauderules`, `AI_CONTEXT.md`, the session starter, `GEMINI.md`,
`layer_doctrine_disposition_v1.md`.

## Running count, since this document is about honesty

Across three rounds Codex has found **sixteen** defects in my doctrine work: six, then five, then
five. Three separate overclaims, two false attributions, one self-refuting rule, one unenforceable
ritual. **Every one was in a document arguing for checking before asserting.** The review is doing
exactly what David asked it to do.

## Still owed, parked not dropped

My disposition of Codex's five findings against **modeled-blank framing v2**. All five verified and
accepted on my side; write-up pending. **That thread is parked by David and does not resume without
his word** — the disposition is a debt to the record, not a resumption.
