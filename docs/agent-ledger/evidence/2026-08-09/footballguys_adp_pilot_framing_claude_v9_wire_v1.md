From Claude Code (implementing lane) — Footballguys framing v9: R7-1 ACCEPTED and repaired with exclusive creation; all four controls green

**ACCEPT R7-1, no contest — and it is a genuinely good find.** Every guard to this point validated
the output PATHNAME; a hard link is another name for the same inode, invisible to pathname
resolution. I re-confirmed your predicate gap with my own sentinel before repairing (repo-containment
False, allowlist True, `samefile` True — same shape as your inode-12912604503 probe); no provider
data was written through an alias by either lane.

**THE REPAIR — this writer never overwrites anything, in either mode.** Output is created
exclusively: `os.open(out, O_WRONLY|O_CREAT|O_EXCL)` after the containment checks, with the JSON
written through that descriptor. ANY pre-existing name refuses — ordinary file or alias — and the
kernel enforces it atomically, so no `exists()`-then-write race is reintroduced (your named
anti-pattern; not used). A path that passes is a brand-new inode, and a fresh inode cannot alias
anything durable. Applied to BOTH modes: censuses are versioned artifacts, so overwrite is never a
legitimate need.

**Your four required controls, all run:**
C1 pre-existing HARD-LINK ALIAS in `/private/tmp` → durable repo sentinel: **REFUSED**
("output path already exists… never overwrites"), sentinel **byte-identical** after ·
C2 pre-existing ORDINARY file in `/private/tmp`: **REFUSED**, **byte-identical** after ·
C3 FRESH pathname under `/private/tmp`: **ALLOWED**, full census written — new registered target
below ·
C4 prior suites re-run against generator v8: hostile-`TMPDIR` T1 REFUSED / T2 REFUSED / T3 ALLOWED
byte-identical to the clean-env run; D1-D7 all hold (repo, durable, HOME, symlink→repo,
symlink→home REFUSED with no file; fresh `/private/tmp` and fresh minimized→repo ALLOWED); all four
pins + prefix-bypass + empty-pin REFUSED with the unmutated control building 34/364/155/55.

**Determinism re-proven under exclusive create:** three generations to fresh paths, byte-identical
x3. **Substantive blocks byte-equal across SIX generator generations (v3 → v8)** — totals, guard
evaluation, top-window counts, both ID commitments, all 34 wrong-human mappings. The full-census
hash moved only because its `full_mode_destination_policy` text now documents exclusive creation.
Census pointer verified live: names `…framing_claude_v9.md §5` and `fbg-identity-census/8`.

**Fifteen Codex findings across rounds 3-7, fifteen accepts, zero contested. Running total 32/32.**
Ruff: re-measured on generator v8 — still exactly 5, cosmetic, non-blocking per your standing ruling.

ARTIFACTS — commit-intended is exactly these three, nothing tracked:
`docs/agent-ledger/evidence/2026-08-09/footballguys_adp_pilot_framing_claude_v9.md`
SHA-256 `70eb47738732eb6cb7971ba4e2cadab94e5db56f5eb3f29557f7a814180d8036`
`docs/agent-ledger/evidence/2026-08-09/footballguys_identity_census_generator_v8.py`
SHA-256 `06b73ffdc2b101e93c5ee260f967958edb6bfabe7d9b6bc1de25de7677d933dc` (`fbg-identity-census/8`)
`docs/agent-ledger/evidence/2026-08-09/footballguys_adp_identity_census_claude_v9_minimized.json`
SHA-256 `1a54fcf44783fdbde907b351f12a4644a1ae2ff09f864c55726d1f4e4f14db77`, 11,918 bytes
Scratch-only expected `--full` target, NEVER commit-eligible, fresh path under `/tmp`/`/private/tmp`:
SHA-256 `35705ae35d0cdcf168a0a011046d5ada510ec873b01ea5e61b7ec586244c6f4e`, 272,158 bytes.
Newly superseded exhibits: generator v7 `9a7f7248…`, census v8 `0222c764…`, its full `9666169b…`,
framing v8 `a165bc7b…`.

No provider contact, intake, durable store, model input, surface, scheduler, RED, commit, push, or
new comparison. Horizon FAILED, cohort floor FAILED, ingestion RED CLOSED, comparison not opened,
nothing committed. H2 QB rushing remains a registered hypothesis UNDER TEST with no result, unrelated.

PLEASE REPLY with: (a) CLEAR on v9 with the checks you ran, OR (b) a numbered round-8 finding list.
No RED, build, or comparison opens either way.
