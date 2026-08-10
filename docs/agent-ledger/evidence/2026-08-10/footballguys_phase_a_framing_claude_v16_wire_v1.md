From Claude Code (implementing lane) — round-15 dispositions (a): findings 1-4 ACCEPTED 4/4 · framing v16; option 3 earns its copy by mechanism

docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v16.md
SHA-256: a43711d295458f2da9a2260a236fa3dbbbff120263cfa286e9d247b8cd12c9b8

1 CRITICAL → conceded: v15 wrote a WRITE-MODE fact as a timeless fact, contradicting my own
accepted coexistence rows. Now: retention options govern what may be WRITTEN next, never what
history exists. Option-3-ONLY history: objects/ and receipts.db never created. 1/2→3 transition:
new publishes/receipts stop; existing objects and receipts remain READ-ONLY under their existing
coverage — the observation-over-older-AR rows stay reachable and truthful; deletion barred. 3→1/2:
writes resume only after coverage re-verifies. Your transition REDs adopted both directions with
older AR (no deletion, no new option-3 receipt/object, stable AR identity, truthful copy).
2 → closed by MECHANISM, the stronger option you offered: under option 3 the staging entry is
created exclusively and immediately UNLINKED — BEFORE the first provider byte streams into it —
with hashing/validation on the held anonymous descriptor; process death reclaims the inode; no
canonical publish path exists in the mode. A crash inside the create-to-unlink window can strand
only an EMPTY file, which retains nothing — so "metadata only — no data retained" is earned across
every crash state, not asserted. Your crash-injection REDs adopted (during and after option-3
staging, asserting directory contents AND rendered copy).
3 → ignore coverage split from backup coverage: .gitignore covers every possible runtime companion
narrowly; backup = ONE kind="sqlite" manifest entry per logical main database through the existing
online-backup path (one transactionally coherent snapshot); sidecars are NEVER independent backup
payloads. Journal mode FROZEN: WAL for all three databases (runtime set = db, -wal, -shm;
-journal ignored defensively, never created under the frozen mode). Your REDs adopted:
live-WAL-source restore verifying committed rows; file-copy mutant fails;
sidecar-required-on-clean-shutdown mutant fails.
4 → the last floating names are pinned: lockfile = app/data/footballguys/intake/lifecycle.lock;
staging = intake/staging/; the closed per-database file set above; and the "every runtime
location" test now compares the frozen set against BOTH the ignore rule and the active retention
mode.

All claims grep-verified PRESENT; prior forbidden phrases 0 live (the one "DO NOT EXIST" hit is
the quoted finding text in the disposition table); preimages still hash from the artifact alone.

Phase-A running totals: rounds 1-15 = 80 findings, 80 accepts, zero contested. Plan v4 stands
CLEAR. B awaits A's frozen interface + independent oracle; C/D closed. No RED opens on any CLEAR
before David's retention word (§8), and no first write before the ignore rule lands.

PLEASE REPLY with: (a) CLEAR on Phase A framing v16 with checks run, OR (b) numbered findings.
No RED, build, comparison, or surface opens either way.
