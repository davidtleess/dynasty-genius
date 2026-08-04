# CFBD DATA Promotion GREEN Review — Codex v4

**Date:** 2026-08-03
**Verdict:** **NOT CLEAR**
**Scope:** literal 112/112 implementation audit and separate three-case RED amendment. No production
or real-data mutation; all probes ran beneath pytest `tmp_path`.

Codex independently reproduced Claude's **112 passed / 0 failed** focused result against module
SHA-256 `012d2a0d0002e9662079f627727758916bc76a15e69720371d9ea18ad8bb55a6`.

The prior RED blobs remain unchanged. New amendment:

`tests/contract/test_cfbd_data_promotion_green_review_red_v4.py`
SHA-256 `62f19430fe4ed4d2b7cf009134462a533534965592850fe9b9610a942275ba33`

The file is Ruff-clean and produces **3 failed / 0 errors**. Binding focused census is therefore
**115 collected / 112 passed / 3 failed / 0 errors**.

## G19 — the fixed role gate is not applied by recovery

G16 correctly added `manifest_path` to `_ARTIFACT_ROLES`, but
`recover_cfbd_promotion` never calls `_assert_distinct_paths`. In a post-replace split state with
`lock_path=manifest_path`, confirmed recovery still:

1. treats the manifest as a stale lock and unlinks it;
2. replaces it with lock text;
3. leaks raw `JSONDecodeError` when later provenance validation reads the lock as JSON; and
4. removes the lock on exit, leaving the governed manifest absent.

The role gate must apply to every entrypoint that can acquire the lock, preferably at the lock
primitive itself or explicitly at recovery entry, before any path is opened or unlinked.

## G20 — confirmed promotion does not revalidate governed provenance under lock

G18 rechecks data and evidence paths under lock, but the manifest/raw chain remains an unlocked
measurement. Reproduced in two independent cases between initial validation and lock body:

- changing only the latest manifest `run_id` so it no longer matches the immutable manifest; and
- changing the raw payload bytes so they no longer match `raw_content_sha256`.

In both cases promotion succeeds, moves active bytes, and writes a receipt from the stale pre-lock
report. A governed provenance chain can therefore disappear/change after validation without
blocking the transaction.

Confirmed promotion must revalidate the manifest and raw chain under lock before its first write
and use that under-lock report for the receipt. Calling the full read-only validation again inside
the lock is acceptable and avoids another incomplete hand-selected recheck set.

## Gate disposition

The pending/full gate was launched before this amendment and cannot close landing. Required next:
all **115** focused tests, then a fresh unfiltered suite and ENFORCE on literal final bytes.

Real active/candidate hashes remain pinned; promotion history remains absent. Nothing was promoted.
H2 QB rushing remains **UNDER TEST** with no result.
