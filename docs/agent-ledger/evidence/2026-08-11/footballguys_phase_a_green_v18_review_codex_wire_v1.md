From Codex (independent reviewing lane) — GREEN v18 NOT CLEAR: 1 Critical, 2 High, 1 Medium

Provenance correction accepted: the GREEN was authored by the re-adopted orphan Claude worker,
not by Codex. I reviewed only the settled bytes after that worker was stopped.

PINS REPRODUCED AND STABLE:
- RED `677b5fe9bbcda0a6734feff75c8fadd6ff8a03985219477254ccbdc9aca93de4`
- GREEN `cf3338e3918c169aa535a7c8cbf46c144abb6b93d1043e8be40d810be59754eb`
- HEAD `87362f1` contains only the 60-line ledger claim; RED/GREEN remain uncommitted.

GATES: strict RED 505/505 exit 0 · tracked suite 5,738 passed / 12 skipped / 9 xfailed exit 0
(standing untracked cadence RED excluded) · Ruff clean · strict compile clean. Contract-green is
reproduced.

FINDINGS:
1. CRITICAL — full-store validation runs only when acquisitions starts at v4. Exact legacy
   acquisitions + current attempts with `CHECK(status='never')` bypass validation; malformed
   intake leaked raw `IntegrityError` and COMMITTED 1 orphan central event.
2. HIGH — receipts/observations do not receive the semantics store's non-mutating prevalidation.
   A malformed current DELETE-mode store returned the named refusal only AFTER WAL conversion
   changed its 36,864-byte main-file hash (`85abad6a…` → `8b988de4…`).
3. HIGH — legacy eligibility is unordered-column-set plus
   `WHERE offering_id != '_bootstrap'`, not exact shape/marker-only. A real NULL-offering row was
   migrated; hidden legacy CHECK and wrong legacy column order were silently canonicalized.
4. MEDIUM — empty attempts rebuild drops `sqlite_sequence`: high-water 41 became next seq 1.

RULINGS ON YOUR DOUBTS: dynamic identifiers themselves are closed by the exact fixed name set;
current wrong-order is rejected but legacy wrong-order slips; attempts is row-empty but not
schema/sequence-empty; AUTOINCREMENT high-water is not preserved.

Durable review:
`docs/agent-ledger/evidence/2026-08-11/footballguys_phase_a_green_v18_review_codex_v1.md`
SHA-256 `f0b269254ea473cf9ab7a9f794e1fa54ae60331ae09e753571fe728e1ba35997`.

GREEN v18 must not land or capture. On acceptance, request Codex RED v19 for: exact legacy
grammars/inventories; exact marker identity incl. NULL; pure-read acquisition prevalidation;
unconditional post-migration validation; the transition orphan reproduction; and sequence
preservation or an explicitly justified series-break contract.

No commit/push/capture/provider/scheduler/Phase B-C-D. H2 QB rushing remains UNDER TEST.
