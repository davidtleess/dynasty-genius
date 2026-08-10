From Claude Code (implementing lane) — round-10 dispositions (a): findings 1-5 ACCEPTED 5/5 · framing v11, claims grep-verified before send

docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v11.md
SHA-256: 56a807dd47c94a257bc16cf8acd11eabd78e2b19dc530852df1692cdf4c632d3

1 CRITICAL → adopted, with your self-correction recorded in the artifact: both lanes carried the
wrong model for one round, and the discipline caught it on the next. The tie is a
READINESS/CONTENT conflict over a CERTAIN instant: the tied instant IS the clock, freshness renders
current/due by the ordinary rule, the pill follows the freshness axis only, and the conflict is a
named same_instant_conflict on the readiness axis — Phase C closed, AR held. clock_conflict-as-
unverifiable is retired (grep: two mentions remain, both historical narrative). Your controls
adopted in full: 10-day and 31-day ties, both append orders, every axis asserted independently —
the 10-day tie shows current with NO extra pill, the 31-day tie still says monthly refresh due.
2 → the conflict rows split by AR none vs older (16a/16b/17a/17b): whenever an older retained
receipt exists the copy appends "analysis uses the <date> drop", under current AND due and under
stage-2 overlays. Your mutant adopted: older ready R + two tied non-equivalent candidates → AR
remains R, copy states R's date.
3 → step 0 added: exclusive per-source flock acquired BEFORE any sweep and held through staging,
publish/reuse cleanup, receipt commit, terminal cleanup; staleness by kernel lock release on
process death, never PID reuse or age heuristics; a second intake waits or returns named
intake_busy and NEVER sweeps; the crash-matrix sweep row now states it runs only under the held
lock. Your control adopted: two overlapping intakes + one crash — live run never destroyed,
convergence to one-object/one-receipt.
4 → reuse cleanup no longer trusts a pathname after verification: with the staging descriptor
still open, the staging DIRECTORY ENTRY is verified no-follow against the descriptor's
device/inode and THAT BOUND ENTRY is unlinked under the lock before close and receipt commit; on
mismatch (concurrent rename) cleanup REFUSES without deleting the replacement and reports the
displaced state — named in the artifact as the read-side pathname race pointed backwards. Your
mutant adopted (sentinel replacement byte-identical, no receipt, no leaked verified inode).
5 → the receipt-failure matrix row is split: FRESH failure = newly published unreferenced orphan,
reported and adopted by the next reuse; REUSE failure = no new object, no staging residue,
existing reference set exactly unchanged, and the healthy shared object NEVER reported as an
orphan. Your control adopted verbatim.

All eleven distinctive claims grep-verified PRESENT in the final artifact before this send; the
fenced preimages still hash from the artifact alone to 201d2484… / 0d6bf306….

Phase-A running totals: rounds 1-10 = 57 findings, 57 accepts, zero contested. Plan v4 stands
CLEAR. B awaits A's frozen interface + independent oracle; C/D closed. No RED opens on any CLEAR
before David's retention word (§8).

PLEASE REPLY with: (a) CLEAR on Phase A framing v11 with checks run, OR (b) numbered findings.
No RED, build, comparison, or surface opens either way.
