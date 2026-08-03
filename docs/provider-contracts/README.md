# Provider-contract evidence

Layer 1 source adapters must be built against provider evidence, not memory. This directory pins
the evidence needed to distinguish a provider change from an adapter defect before a full capture
or paid refresh is attempted.

`index.json` is the machine-readable entry point. The bundle currently covers:

- **CFBD:** the complete public OpenAPI document embedded in the official Swagger UI, its API
  version and SHA-256, the exact endpoints Dynasty Genius uses, and a value-free catalog of
  dynamic `/stats/season` names observed in the successful 2026-08-02 raw capture.
- **PFF:** one redacted entry per exact paid-export schema: header hash, column count, report,
  league, scope, seasons, payload count, and a hash/aggregate of observed value kinds.
- **PlayerProfiler:** the same redacted evidence for every observed export schema across all five
  manual streams.

## What the paid manifests do not contain

PFF and PlayerProfiler rows, player identifiers, source filenames, and complete paid headers do
not enter Git. A value-kind profile records only whether cells in the first 200 rows of each file
were blank/null tokens,
integers, decimals, booleans, or text. A column can exhibit more than one kind, so the per-kind
column counts are not expected to sum to the schema width. Full paid files stay in the existing
gitignored and backed-up private stores.

The redaction has a deliberate consequence: CI can prove that a known schema is pinned and that
the public manifest has not been altered, but only a machine holding the private exports can
recompute the paid header/profile hashes. This is preferable to committing subscription data.

## CFBD two-part contract

OpenAPI proves routes, parameters, response roots, and named response fields. It does **not**
enumerate the values CFBD returns in the dynamic `statName` field. The second artifact,
`cfbd/team-stat-catalog.json`, fills that gap from raw provider responses while omitting all stat
values. Both halves are required:

- `/stats/season` exists; `/stats/team/season` does not.
- `sacksOpponent` and `passAttempts` were observed.
- `sacksAllowed` was not observed and is explicitly rejected by the contract test.

## Refresh

Download the official public Swagger initialization bundle, then rebuild from the existing raw
and private sources:

```bash
curl -sS https://api.collegefootballdata.com/swagger-ui-init.js \
  -o /private/tmp/cfbd-swagger-ui-init.js
.venv/bin/python3.14 scripts/build_provider_contract_bundle.py \
  --cfbd-swagger-init /private/tmp/cfbd-swagger-ui-init.js
```

Refreshing is an evidence change, not a mechanical update. Any changed OpenAPI version, path,
header hash, schema width, or value-kind profile must be reviewed as provider drift before the new
bundle replaces the old one. The generator makes no paid API call and mutates no ingestion store.

## Review targets

Provider-contract changes should be reviewed against a frozen target produced by
`scripts/freeze_review_target.py`. The target records the base commit, exact scoped patch, patch
hash, and post-patch file hashes. A reviewer materializes it in a detached worktree and verifies
the hashes before reading; concurrent edits in the main worktree cannot move that review surface.
