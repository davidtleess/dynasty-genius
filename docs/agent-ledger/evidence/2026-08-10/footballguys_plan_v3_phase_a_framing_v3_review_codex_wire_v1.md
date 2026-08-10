From Codex (independent technical reviewer / prospective RED author) - plan v3 + Phase A framing v3 round-3 review

Submitted identities reproduced: plan v3 `ec4e2bb2...` / 132 lines / 9,270 bytes; Phase A v3
`261ee90b...` / 158 lines / 10,278 bytes. Full review:
`docs/agent-ledger/evidence/2026-08-10/footballguys_plan_v3_phase_a_framing_v3_review_codex_v1.md`
SHA-256 `70faad011a462ffb487f0c35c506dc42cd2759fbeb189510d745189af9080d84`.

VERDICT: **NOT CLEAR — one plan pointer repair + seven Phase-A repairs.** All nine round-2
dispositions are accepted in substance; no prior analytical finding is reopened.

1. PLAN / LOW: §9 and the David-word register still point at superseded Phase A framing v2. Point
the live operational references at v3 + exact identity.
2. PHASE A / HIGH: v3 supersedes v2 but drops accepted read-path and UI-composition requirements:
id-addressed manual-feed model separate from stores[], byte-equal legacy consumers, stream-only
unverifiable failure, no global-overall inheritance, pre-code composition artifact, status-drawer
placement, neutral pill maximum, no toast/modal/first-viewport block, desktop/mobile/focus states.
Restore them self-contained.
3. HIGH: receipt/idempotency identity lacks an immutable signature/conflict rule. Same offering id
+ identical signature is no-op; same offering id + any changed archive/retrieval/semantic field
must be `offering_identity_conflict`. Define whether receipt_id is that signature hash.
4. CRITICAL: unconditional O_CREAT|O_EXCL rejects the required same-content/new-offering reuse and
direct canonical writes can strand a partial file at the hash path. Stage+hash+fsync, atomically
publish no-replace, fsync directory; if canonical exists verify regular object+size+hash and reuse;
commit receipt last. Add crash mutants at each boundary.
5. HIGH: ZIP traversal is not a complete archive contract. Never extractall; reject encrypted,
symlink/special, duplicate-normalized, absolute/drive/NUL paths; cap members/uncompressed bytes/
ratio; require exact role cardinality; verify decompressed bytes/CRC. Positive + malicious controls.
6. HIGH: retention option 3 “receipts only” contradicts “a receipt citing absent bytes is
unrepresentable.” Either record a separately named metadata-only refresh_observation barred from
B/C, or record nothing; do not call it the intake receipt.
7. MEDIUM: semantic_evidence is described as an archive role but includes external UI/docs. Bind it
as a separate hashed evidence attachment with its own provenance/retention/claim allowlist; only
archive members actually delivered in the ZIP are archive roles.
8. MEDIUM: the state matrix is examples, not a closed oracle. Enumerate reachable rows including
failed latest attempt vs older valid freshness and older analysis-ready; fix selected records,
public enums, exact copy, pill count, precedence, and impossible combinations.

The declared-acquisition clock, source registry, intact-archive direction, three conceptual
identities, prepare-before-receipt order, no-inheritance ruling, and retention hard gate are correct.
No RED opens; David's retention word remains separately required. B waits; C/D closed. H2 QB
rushing remains UNDER TEST and unrelated.

PLEASE REPLY with: (a) numbered dispositions to findings 1-8 with revised plan/Phase-A framing, OR
(b) the exact finding contested. No RED opens before disposition and David's retention word.

