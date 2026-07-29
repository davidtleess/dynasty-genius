# TW28-LAYERS — Claude's durable disposition of review rounds 5 and 6

**Supersedes the chat/message summaries for these rounds.** Written because Codex round-6 finding 3
is correct and is the session's own lesson turned on me: **the chat summary is not the durable
artifact.** Round 5 was dispositioned in a cockpit message and only partially patched into
`layer_doctrine_disposition_v3.md`; that left the durable record incomplete.

- `layer_doctrine_disposition_v3.md` remains the disposition of **round 4** (3 findings), plus one
  in-place correction to its own text that round 5 forced.
- **This document is the durable disposition of round 5 (2 findings) and round 6 (3 findings).**

**Nothing committed. Nothing pushed. All four gates open.**

---

## Round 5 — two findings, both accepted

### R5-F1 · File-scoped `authority:` header granted standing doctrine to unratified agent text · **ACCEPT**

`05`'s frontmatter read `authority: standing doctrine` — file-scoped — while the prose said §2 onward
was unratified. Codex named it correctly as the **authority analogue** of the original attribution
defect.

**Checked before changing:** `validate_governance.py` does not reference `authority`, and no
frontmatter parser reads `05`; no tooling depends on the field.

**Fixed** — metadata is now section-scoped and presumes neither Codex's CLEAR nor David's
ratification:

```
authority: SECTION-SCOPED — this file is NOT uniformly standing doctrine; see the two fields below
authority_section_1: standing doctrine — David-verbatim (§1.1 + §1.2), in force now
authority_section_2_onward: PENDING — agent-authored codification, under cockpit review,
  NOT David-ratified; do not cite as standing doctrine until he ratifies it
```

**Recorded in `05` as the third instance of one recurring defect**, not a third unrelated item:
agent text quietly acquiring David's authority — v1.0.0 whole-document attribution, v1.1.0
verbatim-text-outside-§1 plus a claimed ratification, v1.2.0 file-scoped authority header. Doctrine
→ **v1.2.1**.

### R5-F2 · Disposition v3 invented the rule it confessed to breaking · **ACCEPT**

v3 said `02` §Post-fix sweep requires grepping the *"entire document set."* **Verified `02:257`
myself: it says "the entire document" — singular**, pre-commit, author-side; the dependent-document
scan at `:259` is a reviewer **SHOULD, post-commit**, and no commit has occurred. The miss was real;
**the obligation was not.** Corrected in place in v3, saying what it originally said.

**Codex offered "extend the rule or stop claiming it." I did the second only, deliberately** —
extending the pre-commit sweep to dependent documents is a governance **amendment** to `02`, outside
tonight's memorialize-and-ritualize fence, and David's call. Recorded as a named candidate amendment;
**adopted nothing. Codex has since agreed it is not severe enough to route inside this fence.**

---

## Round 6 — three findings, all accepted

### R6-F1 · `02` activated pending §2 authority before ratification · **ACCEPT — the substantive one**

`05:5-10` said §2 onward is pending, unratified, and must not be cited as standing doctrine. But
`02:57` and `02:74-79` stated that authority and made its mechanics binding **without qualification**
— and **a fresh agent reads `02` before `05`**, so it received pending codification as law before ever
reaching the warning. The board's gate 2 also named only "05 §2 onward" while the enforcement
amendment lives in `02` v1.5.0.

This is the **package-activation** problem: I split one amendment across several files and marked the
status on only one of them.

**Fixed in three places, and the scope question is handed to David rather than answered:**

1. **`02` frontmatter** — a `pending_activation` field naming the v1.5.0 delta **precisely** (§Layer
   discipline, Authority Order entry 2, Required Reading 2a, the preflight/ledger layer fields, the
   discipline-reset entry) and stating that **everything else in `02` is in force and unaffected**.
   The pending marker is scoped to the delta, not to the whole file.
2. **`02` Authority Order entry 2** — prefixed `[PENDING DAVID'S RATIFICATION — not yet in force]`.
3. **`02` §Layer discipline** — an activation banner at its head: `05` §1 is in force now; this
   section and the `05` §2+ it gives effect to are **pending and not yet binding**.

**Codex correctly said the ratification scope is David's, not his.** I have therefore **presented the
package without choosing it.** The board now enumerates exactly what is on the table — `05` §2–§4,
`02` v1.5.0's delta, the eight bootstrap pointers, the validator pins — and states that **`05` §1
needs no ratification because it is his own words**, and that he may ratify all, part, or none.

### R6-F2 · The board reported the previous round · **ACCEPT**

`AGENT_SYNC.md` still described round 4 (3 findings, awaiting review) at a freeze whose live state was
round 5. I synced the version pins that round and **not the state prose** — a partial sweep, which is
the same failure shape as R6-F3 and as round 4's findings.

**Fixed:** the board now reports rounds run, the latest verdict, and the running defect count, in a
form that does not go stale on the next round.

### R6-F3 · The durable disposition did not record round 5 · **ACCEPT — and it is this session's own lesson**

`layer_doctrine_disposition_v3.md` remained a round-4 disposition: no R5-F1 entry, stale freeze hashes,
a defect count of 19/four rounds against a submitted 21/five. Round 5's real disposition existed only
in a cockpit message.

**Codex's sentence is the finding:** *"The chat summary is not the durable artifact."* That is exactly
what this whole session has been about — a record that lives only in a conversation does not survive
it.

**Fixed:** this document. v3 keeps its round-4 scope and its one in-place correction; rounds 5 and 6
are dispositioned here with current hashes and a current count.

---

## Verification

| Check | Result |
| :-- | :-- |
| `validate_governance.py` | **PASS**, exit 0 |
| `tests/test_validate_governance.py` | **4 passed** |
| Multiline-safe sweep: cycle overclaim in `docs/governance/` | no hits |
| Multiline-safe sweep: shorthand layer enumeration | no hits |

**Not re-run, disclosed:** the full sprint tollgate — rounds 5 and 6 changed only markdown. The last
full run (after the round-2 code changes) was **ENFORCE PASS** on python-suite, ruff, and
standalone-scripts.

## Running count

**24 defects across six rounds — 6 · 5 · 5 · 3 · 2 · 3.** The families, which matter more than the
number:

- **Authority leak** (agent text acquiring David's standing) — 4 instances, including R6-F1. The most
  persistent by a distance, and the one the document exists to prevent.
- **Overclaim** (a gate, a cycle, or a state asserted ahead of evidence) — 4.
- **Partial sweep** (a fix declared global from a single-file change) — 4, including both R6-F2 and
  R6-F3.
- Plus a self-refuting rule, an unenforceable ritual, an invented obligation, and an unsound probe.

**Round 6 introduced no new error.** All three findings are residue: one activation boundary I split
across files, and two records I updated in one place instead of all of them.
