# CFBD Foundation GREEN Clearance — Codex Independent Review

**Date:** 2026-08-01  
**Layer:** 1–2 source ingestion and data-artifact foundation  
**Disposition:** GREEN CLEAR, uncommitted  
**Network/data boundary:** no live or paid CFBD request, refresh, CSV copy/promotion, consumer wiring, bakeoff, or model action

## Outcome

The final working tree satisfies G1–G7 plus eleven adversarial rows added during independent review. The repair is clear for commit review; commit and push remain separate actions requiring David's word.

## Independent checks

- Review contract: `tests/contract/test_cfbd_qb_ingest_green_review.py` — 11/11 passed.
- Original RED plus review and four pre-existing CFBD suites — 129 passed, 2 skipped.
- Full repository suite with the two standing nflreadpy collection exclusions — 4,173 passed, 12 skipped, 9 xfailed, zero failed in 429.26s.
- Ruff on all production and test files in the CFBD diff — clean.
- `git diff --check` — clean.
- Source review confirmed both pre-existing test edits strengthen the fixtures/contract: provider identity was added without removing value assertions, and HTTP failure now asserts a typed failure while legitimate no-data cases remain unchanged.

## Review defects closed after the first GREEN claim

1. Unresolved identity accepted a lone unattributed stat vector.
2. Non-list provider payload collapsed into no-data.
3. Collision grouping crossed seasons.
4. Raw QB payloads could be lost when normalization failed.
5. The wrapper rejected scalar cache families still emitted by its builder.
6. Games-count cache used a fabricated provider-shaped derivative rather than the provider response.
7. TPA cache used the same fabricated derivative pattern.
8. TPA transport failure was persisted as valid empty data.
9. Games transport failure was persisted as valid empty data.
10. Exact-name identity on the wrong team could resolve after team narrowing failed.
11. Strict team refusal lacked canonical college-name normalization, which would have darkened valid aliases such as `Florida St.` / `Florida State`.

## Scope and blast-radius disposition

The final production repair spans four necessary files: the QB adapter, receiving adapter, foundation wrapper, and W2b builder. That is a disclosed expansion from the original two-file sentence, justified by G2/G6 because the raw responses and derived cache writers live at those boundaries.

The receiving adapter now raises on transport/schema failure. Two untouched callers therefore also fail loudly instead of returning `None`; this is accepted as the intended G2 behavior, not an unauthorized feature change. No consumer or model code was modified.

Legacy scalar cache files remain readable to avoid a paid refetch, but production writers can no longer manufacture raw-looking arrays from derived scalars. The raw publication validator still refuses legacy derivatives in a staged raw directory.

## Remaining boundaries

- No isolated curated CSV has been promoted or copied.
- No paid refresh has run; provider behavior beyond the mocked/contracted interface is not claimed as live-verified.
- No bakeoff or model remediation is needed from the proven blast radius.
- PFF NCAA passing as a replacement source and `enriched_features_equal_baseline` as a defect signal remain separate unopened threads.
- QB rushing remains a hypothesis **UNDER TEST**, not an established finding.
