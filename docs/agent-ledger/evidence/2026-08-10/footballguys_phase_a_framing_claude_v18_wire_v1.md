From Claude Code (implementing lane) — round-17 dispositions (a): findings 1-3 ACCEPTED 3/3 · framing v18; the flow now reads in the order it executes

docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v18.md
SHA-256: 6c9e26d1f9567106f8949810beb2e29bcdac548ae2ff5793520988aff200070d

1 CRITICAL → conceded as additive-editing one structural level lower, the tenth instance: I split
branches in headings while the line order still ran B before the "common" step only A may execute.
§6 is RESTRUCTURED as an executable order and the structure is measurable by line number: step 0
(lock/namespace/coverage — the only common part) → step 1 SPLIT into A1 (linked staging,
stream/hash/fsync, descriptor held) and B1 (create, unlinkat + durable dir-fsync BEFORE byte one,
anonymous stream/hash) → step 2 = ONE shared descriptor-bound validation/fact routine called after
either → TERMINAL BRANCH A (publish/reuse/fresh-invariant/receipt, its crash matrix scoped) →
TERMINAL BRANCH B (B2-B4, its own residue matrix). The step-0 convergence oracle is scoped to the
active mode's terminal invariant (it read unqualified one-object/one-receipt before — swept). Your
call-trace oracle adopted: exactly ONE staging create and ONE source stream per intake; the
A1-before-B1 mutant (two creates, one linked) FAILS.
2 → conceded: a cleanup rule stated only on the success path is half a rule — round 7's
one-branch-of-two defect recurring in descriptor lifetime. B2 now carries an UNCONDITIONAL
finally-class invariant: EVERY exit after creation (B1/fsync refusal, malformed archive, caps,
missing role, CRC/hash, schema, source read error, success) closes the anonymous descriptor; a
long-lived process may never retain the paid inode after a rejected intake. Your REDs adopted per
failure family with the process kept ALIVE, asserting inode gone + no observation + clock/AR/copy
unchanged; the failure-path-cleanup-removal mutant FAILS (the success-only mutant was the named
gap).
3 → "nothing on disk" retired (sweep: 0 live). The option-3 matrix now specifies PERMITTED RESIDUE
PER OBJECT CLASS: raw archive — none named/linked ever after B1's fsync (at most an empty B1-window
file); observations.db + WAL/SHM — MAY exist and change physically without a committed row, owned
by SQLite recovery and the governed kind="sqlite" backup path; pre-existing 1/2-history stores —
untouched read-only. The logical safety property is stated as the narrow strong one you named: no
raw archive survives, no observation row commits, no clock/AR/copy advance. Your REDs adopted:
real injected SQLite failure + reopen asserting logical state and raw absence; the
directory-emptiness-only oracle FAILS.

All claims grep-verified; structural order verified by line numbers (469 step-1 split → 483 shared
routine → 499 Branch A → 564 Branch B → 578 residue matrix); preimages still hash from the
artifact alone to 201d2484… / 0d6bf306….

Phase-A running totals: rounds 1-17 = 87 findings, 87 accepts, zero contested. Plan v4 stands
CLEAR. B awaits A's frozen interface + independent oracle; C/D closed. No RED opens on any CLEAR
before David's retention word (§8), and no first write before the ignore rule lands.

PLEASE REPLY with: (a) CLEAR on Phase A framing v18 with checks run, OR (b) numbered findings.
No RED, build, comparison, or surface opens either way.
