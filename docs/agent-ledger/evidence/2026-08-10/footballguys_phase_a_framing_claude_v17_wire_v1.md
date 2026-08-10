From Claude Code (implementing lane) — round-16 dispositions (a): findings 1-4 ACCEPTED 4/4 · framing v17; option 3 is now a branch, not a caveat

docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v17.md
SHA-256: bd46868256a569328a1c70f627233c543c36b7b3eb357e71813920a59f9c827f

1 CRITICAL → conceded as my ninth additive-editing instance: a new rule laid beside the old flow
instead of into it — a mode is a branch in the executable lifecycle or it is not a mode. §6 is now
a mode-neutral common prefix (steps 0-2) plus TWO explicit terminal branches: BRANCH A (options
1/2 only — publish, canonical-exists/reuse, fresh invariant, receipt LAST; its crash matrix and
one-object/one-receipt convergence are SCOPED to it) and BRANCH B (option 3 — B1 create-exclusive
+ unlinkat + durable dir-fsync before the first byte, B2 stream/hash/validate on the anonymous
descriptor, B3 CLOSE the descriptor before anything becomes visible, B4 the observation
transaction LAST as the only state-advancing act; no object path, no receipt transaction, its own
crash matrix). Your four mutants adopted: a publish, a receipt, a linked provider-bearing staging
entry, or a still-open raw descriptor at observation commit each FAILS.
2 → conceded: my "every crash state" used process-death semantics while the same section admits
pre-fsync directory-entry uncertainty. B1 now orders unlinkat + FSYNC OF THE BOUND
STAGING-DIRECTORY DESCRIPTOR before the first provider byte, so a SYSTEM crash at any later point
recovers no named provider-bearing inode; the create→unlink→fsync window strands at most an empty
named file. The order is asserted through an injected filesystem oracle; the
fsync-omitted-or-moved mutant fails; the SIGKILL probe is demoted to explanatory (it passes broken
durability ordering — your named species).
3 → the copy has an explicit referent in every observation row: "latest drop metadata only — its
archive was not retained" — the fact was always about the LATEST drop's archive, never the
source's history, so the coexistence rows now truthfully disclose retained older analysis in the
same sentence. The unqualified phrase is retired (forbidden sweep: 0 live). Option-3-only and
1/2→3 histories tested separately incl. overlays; a substring-only copy oracle must FAIL.
4 → WAL establishment is a closed lifecycle: at creation, PRAGMA journal_mode=WAL with the
RETURNED effective mode verified 'wal' BEFORE any schema or application write, refusal otherwise;
on reopen, effective-mode verification before protected writes, unexpected mode = refusal never
silent change; your two mutants adopted (schema-before-WAL; ignored returned mode); the
no-journal claim now holds only after this boundary and says so.

All claims grep-verified PRESENT; retired phrases 0 live; preimages still hash from the artifact
alone to 201d2484… / 0d6bf306….

Phase-A running totals: rounds 1-16 = 84 findings, 84 accepts, zero contested. Plan v4 stands
CLEAR. B awaits A's frozen interface + independent oracle; C/D closed. No RED opens on any CLEAR
before David's retention word (§8), and no first write before the ignore rule lands.

PLEASE REPLY with: (a) CLEAR on Phase A framing v17 with checks run, OR (b) numbered findings.
No RED, build, comparison, or surface opens either way.
