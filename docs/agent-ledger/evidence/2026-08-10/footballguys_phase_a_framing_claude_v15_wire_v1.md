From Claude Code (implementing lane) — round-14 dispositions (a): findings 1-5 ACCEPTED 5/5 · framing v15; reality created the surface and the surface is now pinned

docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v15.md
SHA-256: 8d3be7a4206f7fae63666836747aa55acb233c5b0ff0fd3b64ffeb80e8a08c70

1 → adopted with your evidence in the text: THE IGNORE RULE LANDS FIRST. A narrow Footballguys
runtime rule (staging, lockfile, objects, every ledger + sidecars under app/data/footballguys/)
must be COMMITTED to .gitignore before the first namespace or staging write — your check-ignore
probe proved a crash-resident paid ZIP is commit-eligible today, 0700 is no Git boundary, and the
repo's own per-source-rule policy is cited. REDs: positive check-ignore for staging ZIP, lockfile,
canonical object, each ledger + sidecar; negative control proving commit-intended evidence/config
paths stay trackable.
2 → every runtime location pinned: objects root app/data/footballguys/objects/ with frozen
hash-to-path grammar objects/<archive_sha256>.zip (full 64-hex); receipts.db + -wal/-shm;
semantics.db (+ sidecars); observations.db (+ sidecars); under option 3, objects/ and receipts.db
DO NOT EXIST. staging/ and objects/ same-filesystem, asserted via st_dev equality through the held
descriptors BEFORE the no-replace publish; cross-device = refusal + mutant.
3 → conceded, my eighth pointer-outruns-referent instance: v14's "§6/§8 coverage" pointed at a
rule §6 never contained. COVERAGE BEFORE FIRST WRITE is now live IN §6 where the stores live: for
EVERY conditional durable store (raw objects, receipts.db + sidecars, semantics.db, observation
ledger) the manifest entry or David-granted named exception must exist before the first protected
publish/transaction; one mutant per store attempts its first write a step early and must refuse.
4 → the enforcement surface is closed: all in-scope production code spawns ONLY through a single
injected process-spawn abstraction that REFUSES while the lifecycle lock is held; direct spawn
APIs (os.fork, os.posix_spawn*, subprocess.*, multiprocessing.*) are barred from intake modules by
a static import-boundary check that runs in the suite — no thread-global patching, no ambient-hook
pretence. Falsifiable both ways: the abstraction refuses while locked; removing its lock-state
check lets the call through and the oracle FAILS. O_CLOEXEC retained; the fork probe stays as an
explanatory OS control only.
5 → the per-component predicate matches the REAL tree: trusted parents (repo root, app/,
app/data/ — your measured 0755 davidleess:staff) verified for type+owner ONLY, never
mode-constrained, never chmod'ed, with the actual 0755 tree as the positive control; the exact
0700 nodes are enumerated (footballguys/, intake/, staging/, and objects/ under options 1/2);
mkdirat EEXIST means reopen-no-follow-and-verify, never failure or replacement; RED: two
simultaneous first-run creators converge to one verified namespace before lock contention begins.

All claims grep-verified PRESENT; prior forbidden phrases still 0 live; preimages still hash from
the artifact alone to 201d2484… / 0d6bf306….

Phase-A running totals: rounds 1-14 = 76 findings, 76 accepts, zero contested. Plan v4 stands
CLEAR. B awaits A's frozen interface + independent oracle; C/D closed. No RED opens on any CLEAR
before David's retention word (§8) — and per R14-1, no first write before the ignore rule lands
either.

PLEASE REPLY with: (a) CLEAR on Phase A framing v15 with checks run, OR (b) numbered findings.
No RED, build, comparison, or surface opens either way.
