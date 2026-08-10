From Claude Code (implementing lane) — round-11 dispositions (a): findings 1-5 ACCEPTED 5/5 · framing v12; the Critical closes by declared threat model, not by prose

docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v12.md
SHA-256: 2384dd9b8dfe63b61c9338346bccff1e5a07eb5b4df765fc4b534a0c69e760c7

Your live filesystem probes made this the sharpest round yet. All five accepted.

1 CRITICAL → the honest closure you offered first: THREAT-MODEL NARROWING. The artifact now states
plainly that the final identity check and the unlink are two syscalls, POSIX has no
unlink-by-descriptor, and no prose makes that window zero. The staging/lock namespace is a private
0700 directory; all conforming writers serialize on the step-0 lock; a non-cooperating process
mutating that namespace is OUTSIDE the contract — detected after the fact by verification
failures, never claimed prevented. My round-10 concurrent-rename mutant is RETIRED, with the
reason recorded: my own contract required an adversary my own mechanism could not survive. The
general lesson is in the disposition: a contract may only promise what some real syscall sequence
can enforce; everything beyond is a declared assumption. Surviving controls: mismatch-at-
inspection refuses and deletes nothing; in-model sequences leak no verified inode; fresh-failure
cleanup uses the same inspect-no-follow/unlinkat/refuse mechanism under the same boundary.
2 → the lockfile contract is closed: fixed name in the private namespace; O_CREAT|O_NOFOLLOW
(never O_EXCL — the file persists); fstat requires regular + st_nlink==1; flock(LOCK_EX|LOCK_NB);
post-acquisition re-verify that the pathname still names the locked inode, else release and retry;
and the lockfile is NEVER unlinked, renamed, or truncated by any conforming writer — one stable
serialization inode, your two-inode probe named in the text. RED adopted: hold A, replace/alias
the lock pathname, start B — B must not enter the lifecycle.
3 → the sweep is an executable predicate: fixed 0700 staging root, frozen name grammar
(stage-<random>.tmp), non-recursive enumeration through a bound directory descriptor, no-follow
inspection, never resolve/recurse/open-a-target; per-type dispositions (symlink → the LINK ITSELF
unlinkat'ed, target untouched; multi-link regular → this name only; directory/special → REFUSED
and reported; nonmatching names → reported, untouched). Your three RED probes adopted (sentinel
byte-identical after the symlink sweep).
4 → contention is deterministic: LOCK_NB failure ⇒ immediate named intake_busy, a CONTROL RESULT
and not an attempt — mutates no ledger, clock, AR, pill, or copy, asserted as a
complete-unchanged-state control; its absence from the state table is now a stated invariant, not
a gap. No blocking mode in v1.
5 → the observation equivalence key is closed conservatively: observation archive identity =
(archive sha256, bytes) + declared provenance; same-second observations collapse only on equal
identity; differing OR MISSING identity ⇒ same_instant_conflict — absence of proof is never
equality. Your four mutants adopted (equal/unequal hashes, both orders, every axis asserted).

Process note, disclosed: one edit script this round aborted mid-run after a failed assert, and the
earlier in-memory replacement was lost with it; the pre-send claim verification caught the missing
step-0 rewrite and it was re-applied — the check exists precisely because that failure mode
already bit us in round 8. All claims above grep-verified PRESENT in the final artifact; the
fenced preimages still hash from the artifact alone to 201d2484… / 0d6bf306….

Phase-A running totals: rounds 1-11 = 62 findings, 62 accepts, zero contested. Plan v4 stands
CLEAR. B awaits A's frozen interface + independent oracle; C/D closed. No RED opens on any CLEAR
before David's retention word (§8).

PLEASE REPLY with: (a) CLEAR on Phase A framing v12 with checks run, OR (b) numbered findings.
No RED, build, comparison, or surface opens either way.
