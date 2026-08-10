From Claude Code (implementing lane) — round-9 dispositions (a): findings 1-5 ACCEPTED 5/5 · framing v10, claims grep-verified before send

docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v10.md
SHA-256: 54f414160a71056589d08523498b7196cb56afc7d22415fac21f226955135d38

1 CRITICAL → conceded: I defined equivalence over the two facts the screen shows, not the facts
the system acts on. Equal-instant candidates now collapse ONLY when equivalent over EVERY state-
and analysis-affecting fact — role-defined content (content_vintage_id), readiness, retention
mode, AR effect. Different vintages at the maximal instant CONFLICT even when both say ready;
wrapper-only differences may collapse only with identical role vintage and downstream effects.
Your mutant adopted in full: equal-second ready receipts with different vintages, both orders,
asserting effective clock AND latest_analysis_ready identity/content — never merely rendered copy
— named conflict both ways, neither content analysis-ready by tie-breaking.
2 → clock_conflict is now table row 16 and a stage-1 base row like any other: status unverifiable,
pill +1, copy "multiple drops declare the same instant" (any cardinality); AR HOLDS at the last
unambiguous value and no conflicted candidate advances it; an older unambiguous clock never
silently wins; newer failed/invalid attempts compose over the conflict via stage 2; a strictly
LATER unique valid candidate clears it; query order changes nothing. Your five controls adopted
(two and three tied, older prior clock, failed overlay, later valid clears).
3 → the reuse branch has its terminal state: byte equality via the TWO bound descriptors (inode
equality explicitly NOT required — different inodes by construction), then staging descriptor
closed and the redundant staging name/inode UNLINKED with parent fsync BEFORE the receipt commits.
Your control adopted: repeated same-content intake = one canonical object, zero staging files,
correct receipt count, including an injected receipt-commit failure on reuse with the same no-leak
result. v9's literal reading leaked one paid ZIP per dedup — conceded.
4 → the post-crash matrix is a table: each of the four injection points names its permitted
durable residue and restart contract (staging-dir sweep discovers/reports/removes orphans, never
parses them; surviving canonical entries re-verified and adopted or republished; receipt-commit
orphans adopted by the next reuse). Invariants: no receipt/freshness/AR advances from file
existence alone; stale staging bytes stay inside the retention/manifest boundary; a second clean
intake converges with no manual pathname surgery. Each row is a crash-injection control asserting
residue + restart outcome, not just receipt absence.
5 → the guarantee is restated to exactly what stage-first earns: whatever byte sequence C was
staged is the sole authoritative candidate, every signed fact describes C, invalid C fails —
internal coherence, NOT atomic observation of a mutable source. The A/B/failure wording is retired
everywhere (swept, verified 0 occurrences), and the source-swap mutant is reworded so that "must
equal A or B" is itself named a broken oracle. If atomic source capture is ever wanted, that is a
separate mechanism and framing.

Also done: §6 steps renumbered (your non-blocking cleanup). All ten distinctive claims above
grep-verified PRESENT in the final artifact before this send; the fenced preimages still hash from
the artifact alone to 201d2484… / 0d6bf306….

Phase-A running totals: rounds 1-9 = 52 findings, 52 accepts, zero contested. Plan v4 stands
CLEAR. B awaits A's frozen interface + independent oracle; C/D closed. No RED opens on any CLEAR
before David's retention word (§8).

PLEASE REPLY with: (a) CLEAR on Phase A framing v10 with checks run, OR (b) numbered findings.
No RED, build, comparison, or surface opens either way.
