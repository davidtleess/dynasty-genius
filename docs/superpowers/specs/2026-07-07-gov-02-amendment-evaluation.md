# GOV-02 Deferred-Amendment Evaluation & Proposed Resolution

- **Date:** 2026-07-07
- **Author:** Claude (implementation lead)
- **Status:** RATIFIED — v2 dual-cleared (Codex CLEAN CLEAR per item, technical/process; Gemini advisory no-concerns). **David ratified 2026-07-07: "Ratify + commit, stop there"** — patches applied on branch `gov/02-material-visual-direction-amendment`; push held for David's word; the Daily Open composition artifact is deferred to a dedicated session (NOT opened this session).
- **Ticket:** GOV-02 (AGENT_SYNC.md:10) — evaluate three Gemini-drafted governance-02 amendments before the next governance sweep or the next material visual-process thread.
- **Session context:** David-approved sequenced session goal — resolve GOV-02 first (bounded), then open the Daily Open pre-code composition artifact under the #3 threshold, with a David checkpoint between. Codex scope bound: **#3 is the hard precondition** for Daily Open; **#2** is evaluate/clarify-in-README (hard before David-facing visual preview); **#1** is cockpit hygiene (non-blocking). Defect guard: if any item balloons into a *material 02 doctrine amendment* requiring full ratification, stop at GOV-02-only this session. **Codex round-1 read: #3 is a bounded extension, not a material rewrite — it does not trip the defect guard, provided the exclusion is tightened (done in v2).**

## Method

For each item: (a) establish current enforced state with exact `file:line` evidence, (b) restate the refined disposition (AGENT_SYNC.md:10 / ledger 2026-07-07:321-323), (c) give a verdict, (d) provide exact proposed patch text where a change is warranted. Governing constraint: **refine, do not duplicate, and do not land Gemini's raw over-broad drafts.**

## Round-1 cockpit findings integrated in v2
- **Codex D1 (#3 exclusion too abusable):** mechanical exclusions could bypass framing even when they change what David notices first. Added a preservation clause + expanded the material list (typography scale/weight, row density/format, component substitution, motion, responsive/mobile composition) grounded in DESIGN.md:37-43, 49-54, 64-66.
- **Codex D2 (#1 `clearance` inconsistency):** unified language to "raw authorization words" (not "verbs"); `clearance` stays in the *excluded* raw-word set, not the banned list.
- **Codex refinements:** added a narrow `validate_governance.py` required phrase for #3 + test (no validator phrase for #2); replaced approximate line refs with exact ranges.
- **Gemini advisory (#3 category adds):** layout density & row formats, color-palette/hue mappings, and lexicon/tier classifications — all folded into the material list.

---

## Item 1 — Gemini lane cordon (banned-declaration tripwire wording)

### Current enforced state (evidence)
- `scripts/cockpit_hygiene_check.py:32-42` — `BANNED_GEMINI_DECLARATIONS`, a literal case-insensitive substring list, scoped (`:47-68`) to **Gemini-attributed ledger sections only**. Entries: `consensus lock`, `team consensus`, `unanimous`, `Status: APPROVED`, `Trust Consensus`, `Governance CLEAR`, `governance confirmed`, `post-merge confirmation`, `the loop is closed`.
- `docs/governance/02-agent-operating-loop.md:272` (§Falsification #7.5) enumerates the banned declarations; `:273` (#7.6) describes the tripwire as flag-only ("it only flags, it does not adjudicate").
- The list contains **no raw authorization word** (`clear` / `cleared` / `clearance` / `go` / `approved`) as a bare substring. Every entry is a multi-word gate phrase or a consensus-lock phrase.

### Refined disposition
Narrow the §7.5 patch to gate/authorization uses of `clear/cleared/clearance/go/approved` only — **not** the raw substring `clear`.

### Verdict: ALREADY SATISFIED — durable fix is to document the exclusion rationale (non-material)
The tripwire already implements the narrow intent: gate/consensus **phrases** only, no bare authorization words. Raw `clear/cleared/clearance/go/approved` are deliberately excluded because they occur in legitimate Gemini prose ("cleared with David", "David's go", "approved by David", "it is clear that") and a per-line in-section scan would false-flag them. The real failure mode is **regression** — a future agent re-adds raw `clear` from Gemini's original over-broad draft. Durable fix: encode the exclusion rationale at the source.

### Proposed patch 1a — `scripts/cockpit_hygiene_check.py` (comment only; no behavior change)
Replace the comment at lines 29-31 with:
```python
# Gemini lane re-scope (02-agent-operating-loop.md §Falsification #7): banned overreach
# declarations. The tripwire flags these ONLY inside Gemini-attributed ledger sections —
# a literal, case-insensitive substring flag, NOT an adjudicator of quoted/contextual use.
# DELIBERATELY NARROW: only multi-word gate/consensus PHRASES are listed. The raw
# authorization words (clear, cleared, clearance, go, approved) are excluded on purpose —
# they appear in legitimate Gemini prose ("cleared with David", "David's go", "approved
# by David") and a per-line in-section scan would false-flag them. Add only multi-word
# gate/authorization forms with a real observed-overreach basis; never a bare
# authorization word as a raw substring. (GOV-02 #1.)
```

### Proposed patch 1b — `docs/governance/02-agent-operating-loop.md` §Falsification #7.6 (one clarifying clause)
Append to the tripwire sentence in #7.6: "The tripwire is deliberately scoped to multi-word gate/authorization and consensus-lock phrases; the raw authorization words (`clear`, `cleared`, `clearance`, `go`, `approved`) are intentionally excluded to avoid false-flagging legitimate prose, and must not be added as raw substrings."

### Not changing: the banned list itself
`clearance` is **not** added to `BANNED_GEMINI_DECLARATIONS` — no observed `clearance` overreach exists, and adding an unused pattern is speculative. It stays in the *excluded raw-word* set described above. If Codex later cites a real `clearance` overreach, revisit then.

---

## Item 2 — Visual-preview law (engineering evidence vs David-facing readiness)

### Current enforced state (evidence)
- `PRODUCT.md` / `DESIGN.md` (v4, tracked): contract-green is never a visual GREEN; whole viewport is the review unit; mandatory unanchored fresh-agent visual audit with mid-scroll captures; shape-before-code composition artifact (`DESIGN.md:62-66`).
- `docs/design-audits/README.md:1-24` — tracked home for visual-audit bundles; requires desktop+mobile+mid-scroll captures, scored seven-dimension rubric, benchmark-delta, David verdict; "The review unit is the whole viewport, not the diff."
- `scripts/validate_governance.py` requires `docs/design-audits/README.md` to exist and the foundation phrases to be present (`REQUIRED_GOVERNANCE_PHRASES`).

### Refined disposition
Mostly already law; **clarify not duplicate**; primitive/sandbox fixtures remain valid **engineering/contract** evidence (not David-facing visual-readiness previews); relocate any refinement to the foundation/audit README, not raw 02.

### Verdict: NEEDS A SMALL README CLARIFICATION (non-material)
The genuine gap the "unstyled sandbox previews" concern surfaces: nothing states in one place that a **primitive sandbox / isolated component fixture** may prove an *engineering contract* but may **never** be presented to David as *visual readiness*. Add that distinction to `docs/design-audits/README.md`. No 02 change. Gemini (advisory) confirmed this is the correct product framing. **No `validate_governance.py` phrase for #2** (Codex: not needed; keep enforcement minimal) — the README section itself is the durable artifact.

### Proposed patch 2 — `docs/design-audits/README.md` (append a section)
```markdown
## Engineering evidence vs David-facing visual readiness

Two kinds of evidence are NOT interchangeable:

- **Engineering / contract evidence** — primitive sandboxes, isolated component
  fixtures, Storybook-style renders, unit-rendered snapshots. Valid for proving a
  primitive *works* or a contract *holds*. It is not a visual-readiness preview and
  must never be presented to David as one.
- **David-facing visual-readiness preview** — the real, composed surface rendered in
  the real app shell, at full viewport, with mid-scroll captures, scored on the
  seven-dimension rubric. This is the only artifact that supports a "ready for David"
  visual claim.

An unstyled or sandbox fixture may support a contract-green claim; it may never
support a visual-GREEN claim. Contract-green is never a visual GREEN.
```

---

## Item 3 — Anti-solo-drift / material visual-direction threshold (the hard Daily Open precondition)

### Current enforced state (evidence)
- `docs/governance/02-agent-operating-loop.md:140-146` ("Strategy/UX framing first (feature/design tasks)") requires a Gemini framing pass **before the RED** for "anything shipping a **new** David-facing surface, output, artifact, scheduled report, or decision-adjacent contract." Task order: Gemini frames → Codex RED → Claude GREEN → adversarial review → David authorizes.
- `:121-131` ("When the cockpit applies") covers specs, governance, non-trivial branch code, contract/schema/invariant changes — but does not explicitly name a *material re-composition of an existing visual surface*.
- The ratified foundation makes composition part of visual direction: density/row grammar (`DESIGN.md:37-39`), first-viewport order & lane symmetry (`:41`), layered caveats (`:42`), mobile composition (`:43`), motion policy (`:49-54`), and the shape-before-code gate (`:64`).

### The gap
The framing-first trigger keys on a **new** surface. A **material change to the visual direction of an existing surface** — re-composing the first viewport, changing IA/row order, renaming sections, changing the hero/emphasis model, lane semantics, **row density/format, typography scale, color/hue mappings, or David-facing value-band lexicon** — can slip the trigger and be **solo-drifted** by one agent without cockpit framing. This is exactly the failure the Daily Open rebuild must not repeat.

### Refined disposition
**Reject** Gemini's "any styling change" draft (over-broad). **Replace** with a *material visual-direction* threshold routed through cockpit framing **before implementation**, with a tightened mechanical-styling exclusion.

### Verdict: MINIMAL BOUNDED EXTENSION of an existing 02 mechanism — NOT a new doctrine amendment
It extends the ratified "Strategy/UX framing first" mechanism to cover material re-composition of existing surfaces, introduces no new authority/role/invariant, and explicitly excludes truly mechanical styling. Codex round-1 concurred: bounded extension, does not trip the defect guard once the exclusion is tightened (v2 does this). It touches 02 → still requires cockpit review + David ratification. **Defect-guard tripwire (unchanged):** if the debate expands into new authority, new visual law beyond the threshold, or a broader rewrite of framing-first, stop at GOV-02-only.

### Proposed patch 3 — `docs/governance/02-agent-operating-loop.md`, new subsection immediately after "Strategy/UX framing first (feature/design tasks)" (ends at :146)
```markdown
### Material visual-direction changes route through framing (existing surfaces)

The framing-first rule above triggers on a *new* David-facing surface. It also applies
to a **material visual-direction change** to an existing surface — a change to what
David notices first. Such a change must route through a cockpit framing pass + a
pre-code composition artifact (DESIGN.md shape-before-code gate) before implementation.

A change is material when it alters any of:

- the first-viewport story or the 5-second answer
- information architecture, or row/section order
- section naming or surface labeling
- the hero / emphasis model (what is visually foregrounded)
- lane semantics (model/market framing, lane symmetry, what a lane means)
- typography scale or weight in a primary content region
- row or layout density, or row format (e.g. swapping 32px tabular rows for cards,
  changing the desktop two-pane split, or the row-height scale)
- component substitution in a primary content region
- motion that changes what is foregrounded, or its timing/character
- responsive breakpoint or mobile composition
- color-palette, position-hue, or accent mappings (anything touching the
  model-blue / market-amber lane axis or the position-hue families)
- David-facing value-band lexicon or tier/grade thresholds (new labels or changed
  model-grade thresholds alter the manager-voice prose and must not be solo-drifted)

**Preservation clause.** An otherwise-mechanical change is STILL material if it alters
the existing 5-second answer, focal hierarchy, or first-viewport order / lane symmetry.

A change is **not** material — and does not require a framing pass — only when it is
mechanical AND preserves the 5-second answer and focal hierarchy: a copy typo fix (no
lexicon/tier/label change), an accessibility-attribute fix that changes no visible
composition, a token-compliant sub-pixel alignment that changes no density/hierarchy/
color mapping, or a like-for-like refactor with zero visible change. When unsure, route
it — the cost of a framing round-trip is small; a solo-drifted visual direction is
exactly the failure the design foundation exists to prevent. This is a bounded extension
of the framing-first mechanism, not a new authority.
```

### Proposed patch 3b — `scripts/validate_governance.py` (lock #3 durably) + test
Add to `REQUIRED_GOVERNANCE_PHRASES["docs/governance/02-agent-operating-loop.md"]` the phrase:
```python
"material visual-direction change",
```
This is satisfied by the patch-3 subsection body/heading. Update `tests/test_validate_governance.py` to keep the phrase-presence assertion green (the existing pass test covers it; add the phrase to any explicit phrase-coverage list the test maintains). No #2 validator phrase (per Codex).

---

## Rollup

| Item | Verdict | Change | Daily Open precondition? |
|---|---|---|---|
| #1 Gemini cordon | Already satisfied | Comment (1a) + one 02 clause (1b); no behavior change; banned list unchanged | No (cockpit hygiene) |
| #2 Visual-preview law | Small clarification | Append section to `docs/design-audits/README.md`; no validator phrase | Hard before David-facing visual **preview**, not before the internal composition artifact |
| #3 Anti-solo-drift | Bounded 02 extension | New subsection (3) + `validate_governance` phrase-lock (3b) + test | **YES — hard precondition** |

**None require a material doctrine rewrite** (Codex round-1 concurred on #3). On dual CLEAR + David ratification, the on-ramp to the Daily Open composition artifact opens.

## Proposed files touched on ratification
- `docs/governance/02-agent-operating-loop.md` (#1 clause 1b, #3 subsection 3)
- `scripts/cockpit_hygiene_check.py` (#1 comment 1a; no behavior change)
- `docs/design-audits/README.md` (#2 section)
- `scripts/validate_governance.py` + `tests/test_validate_governance.py` (#3 phrase-lock 3b)
- `docs/superpowers/specs/2026-07-07-gov-02-amendment-evaluation.md` (this record)
- ledger + AGENT_SYNC state update

## Open questions for the cockpit (v2)
1. **Codex (technical/process):** Are D1 and D2 fully resolved? Does the expanded #3 material list + preservation clause close the bypass, without over-broadening into "any styling change"? Is the `validate_governance` phrase `"material visual-direction change"` the right lock, and does the test edit need to guard the exact 02 substring? Any remaining evidence-line inaccuracy?
2. **Gemini (advisory):** Are the three category adds (density/format, color/hue mappings, lexicon/tier) captured correctly, and is any first-viewport visual-direction vector still missing?
