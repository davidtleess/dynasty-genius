# 02 amendment — Surface Parity + Governance Digest (David standing orders, 2026-07-15)

**Status: DRAFT v3 — cockpit cycle OPEN on David's word (via Tower). Both orders are
David-ruled substance, effective immediately as directives; this amendment codifies them into
`docs/governance/02-agent-operating-loop.md` (v1.2.0 → v1.3.0).** Commit/push/merge = David's
word after unanimous CLEAR.

## 1. What this codifies

**Order 1 — SURFACE PARITY.** Every backend contract cycle includes a user-visible
verification pass before the cycle is called done. Scope (Codex-hardened through digest
v2→v4): every direct David-facing renderer of the changed fields, captured rendering the real
contract output (never embedded copies), in the nominal state plus every changed
missing/degraded state the contract defines; desktop AND mobile viewports for responsive
renderers; mid-scroll capture wherever sticky/overlay/scroll-container composition can affect
the changed field; each capture paired with a payload or contract assertion; zero-consumer
contracts declare N/A only with a recorded consumer-graph check, are never "parity-satisfied,"
and must name any known planned consumer, to which the obligation attaches.

**Order 2 — GOVERNANCE DIGEST.** `docs/governance/governance-digest.md` (DRAFT v4, Codex
technical CLEAR on wording 2026-07-15) becomes a tracked governance artifact. License:
bounded subtasks only — nonsemantic text/state writes + non-mutating fact probes; reviews
gather facts only; any finding/recommendation/CLEAR/action requires full bootstrap first;
license expires the moment bounded work surfaces a decision. Validity: tracked + no
staged/unstaged diff + all six corpus pins re-hash clean; any failure voids it back to full
reads. Digest edits are governance amendments.

## 2. Proposed 02 text changes

- **New subsection under "Execution: During Work" → "Surface-parity verification pass":** the
  Order-1 scope above, verbatim-tight, plus: the pass is part of cycle completion — a contract
  cycle without it is incomplete, not "done pending screenshots."
- **New subsection under "Required Reading Order" → "Bounded-subtask digest":** the Order-2
  license/validity, pointing at the digest file as the single source; the reading-order list
  itself gains one line: "For bounded subtasks as defined by the governance digest, the digest
  (when valid) may stand in for reads 1–5; AGENT_SYNC and today's ledger are always read."
- **Version bump** 1.2.0 → 1.3.0, changelog line naming David's 2026-07-15 order.
- **Digest regeneration rule:** any change to a pinned corpus file regenerates the digest's
  pin table in the same change set (else the digest self-voids repo-wide — honest but noisy).
- **Bootstrap-entrypoint sweep (enumerated, not aspirational):** every file that states the
  reading order gets the one-line digest reference in the same change set — `docs/governance/
  02-agent-operating-loop.md` (Required Reading Order + Claude Code Bootstrap Requirement
  sections), root `CLAUDE.md` (project bootstrap protocol), root `AGENTS.md` (states the full
  reading order — verified present), `GEMINI.md` (if it restates the
  order), and `.clauderules` if present. The sweep list is verified by grep at implementation;
  a missed entrypoint that still mandates unconditional full reads is a drift defect.
- **Digest lifecycle:** the agent landing any corpus change owns the pin regeneration in that
  change set; additionally, any regeneration whose corpus delta **changes an item the digest
  summarizes** (rule added/removed/reworded — version bump or not) triggers a digest **content**
  re-review for faithfulness; a delta touching only unsummarized prose may regenerate pins
  alone. Pins verify bytes, review verifies meaning.
- **Durable parity evidence storage:** parity captures land under `docs/design-audits/` in a
  per-cycle folder (or the cycle's existing evidence bundle) and are referenced from the
  cycle-closing ledger entry — never left as unreferenced scratch files.

## 3. Named RED (Codex authors, per the loop)

`tests/contract/test_governance_digest_pins_red.py`:
1. Digest file exists and is tracked.
2. Each pin row's sha256 equals the hash of the corresponding worktree corpus file — FAIL on
   any drift (this is the anti-rot core: corpus change without digest regeneration = red).
3. Pin table parse is strict (six rows, full 64-char hashes, exact paths) — malformed = red.
4. Digest contains the license-void sentence verbatim (guards against a silent scope
   relaxation edit).
5. Git-clean validity condition is testable: the test asserts the digest path reports no
   staged/unstaged modification (`git status --porcelain` empty for the path). In CI the tree
   is clean by construction, so the assertion's teeth are local/pre-commit — stated honestly
   in the test docstring rather than implied as a CI guarantee.
Falsification rows: corpus edited without digest bump; digest edited without corpus change
(caught by review + close-the-loop, test asserts pin-table integrity only — stated
out-of-scope with owner); truncated hash; reordered table; deleted row; renamed corpus file.

## 4. Out of scope

- No change to the No-Verdict line, visual-audit gates, closeout motion, or backup law.
- The digest never substitutes for reads on spec/plan/governance/contract/analytical/
  David-facing-surface work (restated, not new).
- Surface parity does not replace the unanchored fresh-agent visual audit — parity is a
  cycle-completion floor (does the surface show the contract truthfully); the audit remains
  the aesthetic/composition gate.

## 5. Falsification seeds (review matrix)

1. A backend cycle closed with contract tests green + no captures — must be called incomplete.
2. A parity pass with desktop-only captures of a responsive surface — incomplete (v4 clause).
3. "No consuming surface" claimed without the consumer-graph record — invalid N/A.
4. A digest-licensed agent states a review finding without full bootstrap — violation.
5. Corpus file edited, digest untouched, RED must go red (test seed 2).
6. Digest staged-but-modified — validity predicate must void (staged diff counts).
7. A future 02 edit that forgets the digest regeneration → RED red; changelog rule catches.

## 6. Sequence

Cockpit adversarial review (this spec + digest v4 together) → Codex authors the RED →
unanimous CLEAR → David ratifies → one branch off main: 02 edit + digest file (tracked,
pins regenerated against the post-amendment corpus — NOTE: committing the 02 edit changes
02's hash, so the digest's own pin table MUST be regenerated in the same commit; the RED
enforces this) → PR → CI → post-commit divergence audit → close the loop.
