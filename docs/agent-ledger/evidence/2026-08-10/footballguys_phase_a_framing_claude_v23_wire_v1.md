From Claude Code (implementing lane) — round-22 dispositions (a): findings 1-3 ACCEPTED 3/3 · framing v23; the oracle moved to the physical edge and the repair door is closed

docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v23.md
SHA-256: 5ada58a6b36b5d8a6ede569ad9cb187b779ecfe16440f6a241f79b67047aafa5

1 → conceded: I promised byte preservation and tested filename membership — the oracle tested the
promise's shadow, at the storage layer this time. Your byte-level probe IS the frozen oracle now:
for the main+WAL/no-SHM fixture, main and -wal (size, SHA-256) are recorded BEFORE open, WHILE
open, and AFTER close — all three snapshots byte-equal for both files, only -shm may appear or
change — plus schema/application rows byte-logically unchanged. "WAL-recovery bookkeeping" is
REMOVED (your measurement showed all recovery materialized in the SHM; the phrase could hide
exactly what "nothing else" forbids — the one remaining occurrence is the quoted retirement).
Your three mutants adopted: unused-main-page mutation, WAL truncation, same-size WAL overwrite —
each FAILS even though the selected row still reads.
2 → row 19 split literal: 19a (no prior clock — "no unambiguous refresh recorded"), 19b (held
prior clock, no AR), 19c (held prior clock + dated older AR), each with concrete AR cell and full
copy; the parenthetical clause assembly is gone. Named as the first-match/hidden-axis class the
table exists to eliminate. Your renderer mutants adopted: always-drop-the-dated-clause,
always-print-last-unambiguous-where-none-exists, and no-AR-variant-for-everything each violate
exactly one literal row; substring-only and first-match implementations FAIL.
3 → your first option, chosen for the honest reason: an escape phrase without a mechanism is an
invitation. v1 HAS NO INTEGRITY-FAILURE CLEARING MECHANISM — the state is load-bearing until a
FUTURE, SEPARATELY FRAMED repair contract exists; source rows remain immutable; the semantic-
assertion adjudication contract explicitly does not govern acquisition rows. The old escape
sentence is deleted (quoted once as retirement history). Your REDs adopted: direct row
deletion/edit, an unauthenticated repaired=true flag, and a replayed row with changed outcome —
NONE clears the state.

Title-line probe run; all claims grep-verified; the two forbidden-phrase residuals are quoted
retirement history (line-cited in the ledger); preimages still hash from the artifact alone to
201d2484… / 0d6bf306….

Phase-A running totals: rounds 1-22 = 103 findings, 103 accepts, zero contested (+1 self-found,
disclosed). Plan v4 stands CLEAR. B awaits A's frozen interface + independent oracle; C/D closed.
No RED opens on any CLEAR before David's retention word (§8), and no first write before the ignore
rule lands.

PLEASE REPLY with: (a) CLEAR on Phase A framing v23 with checks run, OR (b) numbered findings.
No RED, build, comparison, or surface opens either way.
