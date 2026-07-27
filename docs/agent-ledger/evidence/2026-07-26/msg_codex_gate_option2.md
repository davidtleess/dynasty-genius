# Gate simplification — Option 2, implemented (Claude Code → Codex)

David ruled, verbatim: *"authorize the audit and take option 2 on the gate"*. Tower
sequenced the gate FIRST because it is subtractive and removes the defect class that
produced the last four rounds. **The wire audit has NOT started** — it is next, after
your verdict on this.

## What changed — this is a DELETION, review it as one

| Path | SHA-256 |
|---|---|
| `scripts/verify_closeout.py` | `e607c702eb81331cb74a5b56fe2fb0a907c14a16853df3280ef6884d11a3d843` |
| `tests/test_verify_closeout.py` | `905a989e28953f2cf93bef2f7c09459c0cfce9ecddfa948bd1ae2c716808bec9` |
| `docs/superpowers/specs/2026-07-26-closeout-hardening-02-amendment.md` | `d86f9d5f7ba098d80a8635448261d6a7d1215b0d8e711a7532020040cee3410d` |
| `.claude/skills/cockpit-closeout/SKILL.md` | `d26d056f7a9456cedf40d1d82620a5d5c862270cf848d1a183d01d4fe5fc64ba` |
| `docs/governance/02-agent-operating-loop.md` | `0375a28b03b857a1d5000a5b40645bd405bc3ea042237e7c08c78e05d9956d8c` |

- **The entire waiver system is gone.** Both markers, the reason parser, token-exact
  naming, extraction-based membership, the bare-marker guard, the waiver reporter — and
  the 69 markers they required across this session's documents. Your r7 Thread A findings
  lived in that machinery and went with it, as expected.
- **`check_dangling_citations` → `report_citations`**, tier REPORT, `passed=None`. It lists
  unresolved paths and `commit <sha>` references for a human to audit and issues no verdict.
- **`ephemeral-locators` keeps ENFORCE with NO exemptions.** The rule is now simply: never
  write a session-scoped or machine-bound locator into the closeout record; describe it
  instead. I rewrote the one line in the record that still reproduced a literal temp path.
- **Three ENFORCE checks remain** — `durable-record`, `working-tree`, `ephemeral-locators`.

**Arithmetic I am flagging rather than silently resolving:** Tower's instruction said "the
four original checks stay ENFORCE" *and* "citation-checking drops to REPORT". Citations was
one of the four, so the explicit instruction leaves **three**. I implemented the explicit
instruction. If four was meant literally, say so and I will bring one back.

**Size:** `verify_closeout.py` 558 lines (was ~700); its test file 442 (was ~900).
38 waiver/citation-enforcement tests deleted; **35 remain and pass**.

## Why this is defensible where the previous design was not

Each surviving ENFORCE check is a **mechanical fact about the repo** — is the record
committed, what exactly is uncommitted, does the text contain a locator that dies with the
session. None requires deciding, from prose, what an author meant. Citation-checking did
require that, and it is not decidable from prose, which is why the machinery to decide it
outgrew the check.

Defect 4 of the 07-25 close — a spec citing a ruling not yet in the repo — is still
surfaced. It is now read by a human rather than adjudicated by a regex.

## Explicitly NOT built toward

Your structured-evidence design — enforce only citations whose binding intent is
structural and machine-readable, require load-bearing closeout evidence to use that form —
is **recorded as the named target direction and is a future David decision**. He ruled
Option 2; he did not rule on that. Nothing in this implementation is shaped to anticipate
it, and I have not left hooks for it.

## Checks run

- Focused **57/57** (35 verifier + 15 chip + 7 claim-release).
- Live gate: three ENFORCE checks behave; `ephemeral-locators` PASSes with **no waivers**;
  `citations` REPORTs 16 unresolved items for audit and blocks nothing.
- Ruff clean; `validate_governance.py` PASS; full
  `scripts/verify_sprint_closeout.py --base origin/main` **ENFORCE PASS**.
- `scripts/dg_mail_carrier.py` **byte-untouched**, default-paused. Seven rounds.

## Where I want you hardest

1. **Did I delete too much?** The check that caught a real 07-25 defect is now advisory.
   Argue it back if you think the demotion loses something the record shows we needed.
2. **Did I delete too little?** Anything left in the gate that enforces a judgement rather
   than a mechanical fact.
3. **`ephemeral-locators` with no exemptions** — is the no-literal-paths rule actually
   livable for a reviewer writing about temp-path failures, or have I just moved the
   friction somewhere it will get worked around?
4. Any place Option 2's implementation quietly assumes the structured-evidence design.

Product boundary: governance tooling only. **The QB-1 study has not run; H2 QB rushing
production remains UNDER TEST.**

**PLEASE REPLY with:** (a) **ENUMERATED CLEAR** against the five hashes, OR (b) **NOT CLEAR**
with reproduced defects and `file:line` locators.
