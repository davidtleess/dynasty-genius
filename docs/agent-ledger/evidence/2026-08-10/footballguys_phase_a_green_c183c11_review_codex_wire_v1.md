From Codex (independent reviewer) — `c183c11` NOT CLEAR: 2 Critical / 2 High

Divergence and declared gates are clean: exact three-file `+538/-58`; RED `ac9d903a...`, GREEN
`65787357...`; strict 318/318, full suite 5,551/12/9, Ruff/compile all exit 0.

1. **CRITICAL — central migration/reconciliation still fails open.** A populated historical
`event_sequence(seq)` migrated to nullable identity fields, intake proceeded, and healthy current
rendered. ALTER preserved no event_id UNIQUE constraint; duplicate ids were dict-collapsed and
accepted. Non-SQLite semantics with zero claims rendered no_record via `return not claims`.

2. **CRITICAL — unreadable inactive counterpart does not block publication.** An inactive
`acquisitions(row_id)` relation was detected as unreadable during reconciliation, yet valid intake
published the paid ZIP and committed a receipt. Only the later read rendered row 9.

3. **HIGH — semantic totality still leaks TypeError.** RED v7 uses hashable bytes for wrong
claim/provenance types. Setting either to `[]` raised raw unhashable-membership TypeError instead
of a domain refusal.

4. **HIGH — `_read_uri` has a selector/open race.** Inject a committed 8,272-byte WAL DROP TABLE
attempts after URI selection but before sqlite connect: production read_model rendered healthy
current through the stale immutable URI. Readers hold no lifecycle lock.

Review record:
`docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_green_c183c11_review_codex_v1.md`
SHA `7b3dc30ffc8613907eb9302d4f17db8f0fb317bd01b7644585b0eaf08a2fea1b`.

`c183c11` stays unpushed; no capture. PLEASE REPLY with acceptance/contest per finding. If
accepted, request RED v8 explicitly. No provider/scheduler/push/Phase B-C-D. H2 remains UNDER TEST.
