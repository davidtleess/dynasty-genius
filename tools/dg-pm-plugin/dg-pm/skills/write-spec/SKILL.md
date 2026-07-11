---
name: write-spec
description: Author a Dynasty Genius spec of record from a problem or change idea. Use when turning an idea, bug, or David directive into a docs/superpowers/specs/ design doc that feeds cockpit-TDD — problem (measured), design, out-of-scope, falsification seeds (the RED matrix), the cockpit-TDD sequence, and risks. Not a generic PRD.
argument-hint: "<feature, defect, or change idea>"
---

# Write a DG spec of record

> Sources are DG's own artifacts, not SaaS connectors — see [SOURCES.md](../../SOURCES.md). Governance (`docs/governance/00`–`04`) and the No-Verdict Line win over anything here.

Produce a **design spec of record** at `docs/superpowers/specs/YYYY-MM-DD-<slug>-design.md`. It is the artifact the cockpit reviews and that David authorizes work against. It is falsification-first, not a feature wish list.

## Before you write

1. **Complete the governance bootstrap first — do not shortcut it.** Per `CLAUDE.md`/`AGENTS.md`, the full Required Reading Order precedes any spec authoring, code, PR review, or analytical recommendation: governance `02-agent-operating-loop` → `00-product-constitution` → `01-north-star-architecture` → `03-code-hygiene-policy` → root `PRODUCT.md`/`DESIGN.md` (if the surface is visual) → `AGENT_SYNC.md` → today's ledger. For *this* spec specifically, ground hardest in `00` (immutable football rules + the No-Verdict Line) and `AGENT_SYNC.md` (current thread); load `PRODUCT.md`/`DESIGN.md` via the `impeccable` skill for any visual surface.
2. **Measure the problem — do not infer it.** Reproduce it. Read the actual code at `file:line`. Quote the real marker/output/test. A spec that opens with a reproduced failure and exact line references is worth ten that open with a hunch. **The reproduction is a gate, not a formality:** the `Reproduced` block must contain a real command and its captured output. If you genuinely cannot reproduce yet, you must **label the section `Reproduction pending` (never `Reproduced`)** and mark the spec **NOT a spec of record — it cannot go to cockpit CLEAR until a real command + output is pasted.** A `Reproduced` heading over a placeholder is the exact failure this skill exists to prevent.
3. **Name the authoring lane.** Claude authors the spec; **Codex authors the RED**; Gemini is advisory/non-binding. State this so the reader knows who does what next.

## Spec structure

Write these sections. Keep it scannable — a busy reviewer should get the gist from headers and bold.

### Header block
- **Title**, **Date**, **Status** (`DRAFT — awaiting cockpit CLEAR, then David authorization`), **Authoring lane** (Claude spec · Codex RED · Gemini advisory), **Scope** (one line: what subsystem, and explicitly what it is *not*).

### 1. Problem (measured, not inferred)
- The user/system problem in 2–3 sentences, grounded in evidence (a reproduced failure, a real marker, a metric, a David directive quoted verbatim).
- **Root cause** at `file:line`. **Reproduced (not asserted)** — show the command and the exact output (or, if not yet reproduced, label it **`Reproduction pending`** and flag the spec as not-yet-a-spec-of-record per step 2 — never a `Reproduced` heading over a placeholder). **Consequence** — what is actually at risk today.

### 2. Design
- The change, concretely. Prefer **injectable seams** so the RED can be hermetic (no network, no gitignored artifact, no real external effect). Show the key function signatures / data shapes.
- If several shapes are viable, name them and state which the cockpit should pick (or which you recommend and why).

### 3. Out of scope (named, not hidden)
- 3–5 adjacent things this change explicitly does **not** do, each with a one-line reason. Silent scope is how DG specs rot. If a deeper layer exists (e.g. "whether auth succeeds"), name it and say it will surface *by name* later, not as a mystery.

### 4. Falsification seeds — the RED matrix
- A table `F1..Fn` of the failing tests the RED must contain. Each row: the seed (inputs/state) and the required behavior. **All hermetic** — injected seams, no real external effect, no gitignored artifact asserted.
- Include the adversarial cases, not just the happy path: wrong types, missing fields, traversal/escape, ordering (a failure must not mask a different failure), fail-closed defaults.
- State the **test path** (usually `tests/contract/test_<slug>_red.py`) and the **test-construction law** for any gitignored surface (drive the function directly / monkeypatch the path; never assert the live artifact).

### 5. Sequence (cockpit-TDD)
Spell out the loop so the next agent knows the gates:
1. Cockpit CLEAR on this spec (Codex technical; Gemini advisory if relevant).
2. **David authorizes** the RED.
3. Codex authors the RED (F1..Fn), demonstrably red on `main`.
4. Claude implements GREEN; runs the focused suite + full gate where a locked surface is touched; self-probes the falsification matrix.
5. Codex independent review → CLEAR.
6. **Only then, David-authorized:** the real action (commit/push/PR/merge/run). CI is the merge gate, not local-green.

### 6. Risks
- A table of the real risks and their mitigations (path rot, hidden deeper defect, contract break, false-green). Be honest about what this does *not* prove.

## Non-negotiables to bake in (the DG reframe)

- **No-Verdict Line.** `decision_supported=false` end-to-end. No action directives, verdicts, tiers, or nominated targets in running-software output. Calibrated lexicon (Generational/Elite/Cornerstone/Starter/Depth) only where a ratified 00 amendment allows it, always word+number with receipts.
- **No market-data leakage.** Market/consensus values never enter Engine A/B training features. If the change touches features, prove the boundary holds — leakage is a defect, not a tradeoff.
- **Reversibility + authorization gates.** Flag anything hard-to-reverse or outward-facing (commit, push, merge, branch-delete, run, schedule, backup, LaunchAgent). Each is David's explicit call; reviewers CLEAR content, David authorizes actions.
- **Honesty substrate (visual surfaces).** Contract-green ≠ visual-green. The whole viewport is the review unit; an unanchored fresh-agent visual audit is the standing pre-David gate. Never let the product read like a diagnostics console in a fantasy skin.
- **Frozen-model constitution.** A change must not retroactively rewrite what a frozen model "said"; realized-outcome grading is against frozen predictions.

## Scope discipline

- Be ruthless about the RED matrix, not the feature list. The tighter and more adversarial the seeds, the faster the GREEN converges and the less latent failure ships.
- If the idea is too big for one spec, spec the first increment and name the rest as out-of-scope follow-ups (a parking lot David sequences).
- Additive/versioned over in-place for any load-bearing model output (e.g. emit `x_raw` + a basis version rather than mutating an emitted field). Mutating a model-output contract needs its own spec + RED + basis metadata.

## Output

Markdown. Write to `docs/superpowers/specs/YYYY-MM-DD-<slug>-design.md`. Then offer to route it to the cockpit (Codex for CLEAR + RED authorship, Gemini advisory) — but **do not commit or route without David's word**. Writing the spec file is content; routing and committing are actions.

## Tips

- Open with the reproduced failure. It is the single highest-signal thing in the doc.
- Every falsification seed you can name now is a defect you will not ship later.
- "Out of scope, named" is as important as the design. The next agent trusts what you excluded only if you said why.
- If you find yourself writing success metrics like "adoption" or "NPS," stop — this is a single-user tool. Success is a passing RED→GREEN, an honest marker, and a David CLEAR. Model/data quality lives in `dg-pm:metrics-review`, descriptively.
