# ftn_charting post-commit review — Codex v1

Date: 2026-08-05  
Target: `edf05e94fd4ab5f93e0c23a0383e37f21ab26fb3`  
Disposition: **NOT CLEAR**

## Scope and checks

- Reviewed `git show edf05e9` from an immutable detached worktree.
- Focused committed contract: **17 passed**.
- Live last-good artifact anchored to run `nflverse-usage-20260805T0326292827190000`:
  185,215 rows across 2022-2025; every identity status is `not_applicable`; zero non-null
  `dg_player_id`; zero FTN rows in `unresolved_identity.parquet`; all 15 declared flags are Boolean;
  NGS consumer frames remain 5,933 / 14,731 / 6,059.
- Repository scan found no FTN consumer outside the adapter. The generic unresolved-identity
  publisher explicitly excludes `NOT_APPLICABLE`; no additional applicability leak was found.

## Blocking findings

### T1 — the Boolean cast is not fail-closed for values outside {0, 1}

The comment at `edf05e9:src/dynasty_genius/nflverse_usage.py:1680-1688` says a value other than
`'0'`/`'1'` becomes null and is caught by non-null reconciliation. That is false for numeric text:
Polars casts `'2'` to Int64 `2`, then Boolean `true`; the non-null count is unchanged.

An end-to-end one-row capture with source `is_motion='2'` returned `status='ok'` and published
`is_motion=true` with Boolean dtype. This invents a valid-looking flag from an invalid source value.
The existing True-count test uses only a clean fixture and cannot falsify the invalid-domain path.

Required closure: refuse Boolean source/store values outside the declared domain before coercion,
and add end-to-end falsifiers for at least `2`, `-1`, and non-numeric text while preserving the
prior ready marker and naming the failed stage.

### T2 — the new min-season/skip mechanism has no committed contract

The new behavior lives at `edf05e9:src/dynasty_genius/nflverse_usage.py:1976-1990` and
`:2085-2115`, and it already produced two disclosed live defects during implementation. Yet
`tests/contract/test_ftn_charting_ingestion_red.py` ends at line 311 without asserting
`min_season`, loader suppression below 2022, exact skip records, terminal marker status, or the
`stream_seasons` versus `stream_seasons_skipped` accounting.

The chosen semantics are acceptable: a declared out-of-domain season is not an ingestion failure;
recording it as skipped and excluding it from the count of actually ingested stream-seasons is the
honest contract. Required closure is a compact regression that proves those semantics and proves
the bound spec retains `min_season=2022`.

## Boundary

The identity-applicability design is accepted, and the live FTN rows need not be removed. Do not
amend the disclosed historical commit; close the Boolean-domain and skip-contract gaps in a
corrective commit, rerun focused/full gates as appropriate, and request fresh review.
