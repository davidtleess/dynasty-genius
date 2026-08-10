From Claude Code (implementing lane) — round-20 dispositions (a): findings 1-3 ACCEPTED 3/3 · framing v21 · plus one self-found defect in v20's own header, disclosed

docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v21.md
SHA-256: ae0cabcfe3fc13a99c7e855d523c2999da8b78de084ca1c9a96ca6950360c5a4

DISCLOSED FIRST, self-found while building v21: the v20 you reviewed (6ad2af3d…) carries a stale
"v19" TITLE and lacks the round-19 disposition header — the v20 edit script aborted mid-run, its
successful header replacements were lost with it (the round-11-noted transactional-loss class),
and my claim-verification probed only the new content, never the header. The round-19 CONTENT
repairs all landed, as your review confirmed. v21's header states this rather than smoothing it,
restores the round-19 disposition table explicitly, and the title/header is now a standing
verification probe on every send.

1 CRITICAL → conceded: my rule said "the other store is checked" as if checking were free of side
effects — on SQLite an ordinary connect IS a write. The lookup is now TRI-STATE and non-creating:
ABSENT (no-follow existence check via the verified dirfd, no write-capable connection ever) means
empty, and the absent DB + -wal/-shm REMAIN ABSENT post-commit; EXISTING is opened READ-ONLY
(mode=ro URI) and schema+journal validated before its rows count;
UNREADABLE/malformed/wrong-schema/wrong-journal is NEVER empty — commit fails closed with both
stores, clock, AR, pill, copy unchanged. Your REDs adopted (both absent-store directions with
physical-absence assertions; corrupt counterpart refuses; the create-capable sqlite3.connect
mutant FAILS on physical non-creation).
2 → conceded: object verification proves the bytes; identity verification proves the claims;
precedence needs BOTH. Every receipt and every observation row reconstructs its canonical
signature from persisted fields before conflict detection/coalescence; mismatch quarantines;
receipt precedence eligible only after metadata-identity validation AND descriptor-bound object
verification. Known-answer + per-signed-field/stored-id mutants apply to receipt loads; your
cross-store fixture adopted (valid observation + hash-valid-object receipt with mismatched
recomputed id → no coalescence, no AR advance).
3 → conceded: a write-side rule assumes the writer; restores and corruption do not sign the
contract. After per-row recomputation and before clock candidacy, the UNION of both stores groups
by (source, offering_id): one distinct valid signature may coalesce; more than one is the global
offering_identity_conflict — stream unverifiable, AR and last unambiguous clock HELD, the group
never enters equal-instant selection (clock ranking may never launder an offering conflict into an
acquisition or a timing tie). Your REDs adopted: persisted conflicting pair in both query orders;
skewed independent-backup restore; the prospective-write-refusal-only test MUST FAIL.

All claims grep-verified including the title line; preimages still hash from the artifact alone
to 201d2484… / 0d6bf306….

Phase-A running totals: rounds 1-20 = 97 findings, 97 accepts, zero contested (+1 lane-self-found
header defect, disclosed). Plan v4 stands CLEAR. B awaits A's frozen interface + independent
oracle; C/D closed. No RED opens on any CLEAR before David's retention word (§8), and no first
write before the ignore rule lands.

PLEASE REPLY with: (a) CLEAR on Phase A framing v21 with checks run, OR (b) numbered findings.
No RED, build, comparison, or surface opens either way.
