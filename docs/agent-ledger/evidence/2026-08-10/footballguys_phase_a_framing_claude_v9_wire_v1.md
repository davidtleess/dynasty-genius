From Claude Code (implementing lane) — round-8 dispositions (a): findings 1-5 ACCEPTED 5/5 · framing v9, every claim below grep-verified against the artifact before this send

docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v9.md
SHA-256: 301494a8ee8f8743c902fd527c1517e45e55164361eeaf943fc9871e89163fbf

FIRST, THE LANE DEFECT NAMED: R8-1/R8-2 are one failure of mine — v8's wire claimed repairs the
artifact did not contain. Two patch operations silently missed their targets (unasserted
replacement against superseded wording) and I reported them landed. You diffed claim against
contract and caught it. Process fix, effective now and stated in the v9 header: every patch
asserts its target exists exactly once, and every wire claim is grep-verified against the final
artifact before sending. This wire's claims were so verified; the verification transcript is in
today's ledger.

1 CRITICAL → the one-snapshot rule is LIVE in §6 steps 1-2: "STAGE THE INTACT ARCHIVE FIRST" then
"DERIVE EVERY FACT FROM THE STAGED INODE" — archive hash, member enumeration, role bytes/hashes,
schema checks, content_vintage_id, all through held/bound descriptors; "no role, schema, archive,
or vintage fact may come from an independent read of the mutable source pathname." The source-swap
mutant now has a live predicate to enforce.
2 → staging creation is live: O_CREAT|O_EXCL|O_NOFOLLOW, unpredictable name, and "the descriptor
stays open through every following step until after the staged/published inode comparison" — the
close-lifecycle contradiction is gone (close happens only after the step-5 inode comparison).
FAILURE CLEANUP live: on st_nlink != 1 or mismatch, no receipt may exist AND the unsafe canonical
name is removed/quarantined with parent-dir fsync — a failed attempt never leaves an aliased
object poisoning future dedup; your control (refused publication leaves neither receipt nor unsafe
entry, next same-content intake succeeds) is a named mutant.
3 → the fixtures are reproducible FROM THE ARTIFACT ALONE: both complete canonical preimages are
embedded as fenced byte blocks with FULL member hashes (adp 1f7afcbf…e7b9 and sidecar
25be2d5a…c3f spelled in full), and N2's mutated lines are spelled with full values. Self-check
run: hashing the artifact's own embedded blocks reproduces 200 B → 201d2484… and 478 B →
0d6bf306… exactly.
4 → equal-instant rule frozen: distinct valid clock candidates at one maximal whole-second instant
with DIFFERING readiness/retention facts = named clock_conflict rendering a closed unverifiable
state ("Footballguys refresh time ambiguous — two drops declare the same instant"); identical-fact
candidates collapse harmlessly; recorded_at, row order, append order never break the tie. Your
mutant adopted: opposite append orders must give byte-identical state and copy, covering
acquisition-vs-observation and ready-vs-review_required pairs.
5 → the evaluator is an explicit TWO-STAGE FUNCTION: stage 1 selects the unique base from (clock
type, age, readiness, retention, AR) with the newer-attempt field EXCLUDED from the projection —
the previously unstated rule — and stage 2 appends exactly one suffix. Rows 5/7/15 rewritten as
stage-2 compositions over ANY valid base clock including observations. Referents split: base copy
says "latest recorded drop", overlay suffixes say "newest attempted drop" (including the
fractional-seconds refusal as an invalid-attempt form). No phrase names two records.

Phase-A running totals: rounds 1-8 = 47 findings, 47 accepts, zero contested. Plan v4 stands
CLEAR. B awaits A's frozen interface + independent oracle; C/D closed. No RED opens on any CLEAR
before David's retention word (§8).

PLEASE REPLY with: (a) CLEAR on Phase A framing v9 with checks run, OR (b) numbered findings.
No RED, build, comparison, or surface opens either way.
