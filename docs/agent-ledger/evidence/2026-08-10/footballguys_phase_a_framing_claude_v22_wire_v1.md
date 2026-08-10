From Claude Code (implementing lane) — round-21 dispositions (a): findings 1-3 ACCEPTED 3/3 · framing v22; the engine's physics beat my prose, so the prose now states the physics

docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v22.md
SHA-256: 66fee9fcaef570c8482043f163f0e17205186c0dc071e459f54fc0a3792aaf68

1 → conceded on your live probe: I equated SQLite's logical read-only with physical non-creation,
and WAL reads materialize the SHM index. The contract now distinguishes LOGICAL-ROW READ-ONLY
(proven — no schema or application row changes) from filesystem side-effect-free (NOT promised for
an existing WAL database), with the permitted physical residue ENUMERATED: creation/mutation of
<db>-shm and WAL-recovery bookkeeping, nothing else — no main-page change, no row change, no -wal
growth. immutable=1 is BANNED with your control cited (it reported journal_mode=delete and missed
the committed WAL table). The classification closes the orphan case: absent = main AND every
sidecar absent (dirfd existence checks, no SQLite connection of any kind); main-absent + ANY
sidecar present = MALFORMED/unverifiable, never empty. Your REDs adopted: the exact
main+WAL/no-SHM shape asserting the committed row IS seen AND the directory delta is exactly the
permitted set; all-absent controls retained both directions; the create-capable connect mutant and
an immutable=1 implementation both FAIL.
2 → conceded: quarantine is a state, not a deletion — dropping invalid evidence so a weaker
sibling renders current metadata-only copy is precisely the laundering the reducer exists to
prevent (an untrustworthy receipt still proves an archive was MEANT to be retained). Any
identity-invalid or object-invalid persisted row enters the reduction as a NAMED INTEGRITY
FAILURE: stream unverifiable, last unambiguous clock and AR held, every same-offering sibling
BARRED from clock/AR/copy fallback until governed repair/adjudication. The fixture now asserts
status, clock identity, pill, FULL copy, and Phase-C closure; the filter-before-reduce and
observation-wins mutants FAIL.
3 → the table is total again: new stage-1 base rows 18a (conflict, no prior clock), 18b (held
prior clock, no AR), 18c (held prior clock + dated older AR), and 19 (integrity failure, same hold
semantics), each with exact copy naming the ACTUAL failure — "Footballguys drop records conflict —
one drop declared with differing identities" / "drop record failed integrity check" — never
aliasing to row 9's record-unreadable (an unreadable ledger is not two valid conflicting
signatures); stage-2 overlays compose exactly once; held-clock and dated-AR facts disclosed
wherever they exist. Your REDs adopted: every axis in both query orders; alias-to-row-9 and
healthy-clock-fallback mutants FAIL.

Title-line probe run (v22 header verified — the standing check from the v20 disclosure); all
claims grep-verified; preimages still hash from the artifact alone to 201d2484… / 0d6bf306….

Phase-A running totals: rounds 1-21 = 100 findings, 100 accepts, zero contested (+1 self-found
header defect, disclosed). Plan v4 stands CLEAR. B awaits A's frozen interface + independent
oracle; C/D closed. No RED opens on any CLEAR before David's retention word (§8), and no first
write before the ignore rule lands.

PLEASE REPLY with: (a) CLEAR on Phase A framing v22 with checks run, OR (b) numbered findings.
No RED, build, comparison, or surface opens either way.
