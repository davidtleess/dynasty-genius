# CFBD DATA Promotion GREEN — Independent Implementation CLEAR

**Date:** 2026-08-03
**Reviewer:** Codex, independent RED/review lane
**Verdict:** **IMPLEMENTATION CLEAR**

## Exact implementation cleared

| File | SHA-256 |
| :-- | :-- |
| `src/dynasty_genius/capture/cfbd_data_promotion.py` | `2901c8abfeed98d980522986f89f05c9ac9ebdfdbd46ef0519ab9cf55d0e4f0d` |
| `scripts/promote_cfbd_data.py` | `1fce5603adec0168410a7308c8a37880886fd3bc8beb559f235cb0e518ccfe4b` |
| `scripts/build_head_b_targets.py` | `6b66f31faa57840fa43bc183935e20fc141a7b653414c08351485d0ab98a0516` |
| `scripts/build_w2b_cfbd.py` | `636b2ad2d7a50488d2312e621626c61bababf0756826f2d0aa9c2332a10b072d` |

Codex independently verified the four hashes and reviewed the literal final module/CLI/writer
integrations.

## Contract and gate evidence

The five RED files are preserved as independent contract layers:

- original 60-case RED, current binding SHA `4c6b5f72...`;
- review v1, 25 cases, SHA `06b4c4a1...`;
- review v2, 15 cases, SHA `0be1bbf8...`;
- review v3, 12 cases, SHA `a0111472...`; and
- review v4, 3 cases, SHA `62f19430...`.

Codex independently reran the focused gate on the final implementation: **115 collected / 115
passed / 0 failed / 0 errors**.

Claude's fresh literal-final-tree gate then landed:

- full unfiltered suite: **4,424 passed / 12 skipped / 9 xfailed / 0 failed**;
- collection: **4,445**, zero collection errors;
- reconciliation: `4,424 + 12 + 9 = 4,445`;
- delta from the pre-cycle tree: `+115` collected and `+115` passed, exactly the five RED files;
- `verify_sprint_closeout.py`: **ENFORCE PASS** (`python-suite`, `ruff`,
  `standalone-scripts` all PASS);
- `ruff check src app`: clean;
- touched-file Ruff: clean; and
- `git diff --check`: clean in the independent review workspace.

No pre-existing test changed state in either direction.

## What is cleared

The implementation now provides a pinned, offline, dry-run-default DATA transaction with:

- exact full-file and canonical projection pins;
- complete manifest/raw provenance validation and under-lock revalidation;
- exact row/header/order/identity/QB-only/allowlist/count gates;
- complete path/resolved-path/inode role separation, including the governed manifest;
- lock/CAS protection across active data and evidence paths;
- durable preimage, sibling atomic replacement, fsync, post-readback, crash recovery, and guarded
  rollback;
- semantically validated, provenance-bearing, non-predictive receipts;
- fail-closed destructive-writer admission before expensive/paid work; and
- an offline CLI where every action is read-only unless `--confirm` is explicit.

## Boundary

This CLEAR covers the **built mechanism only**. It is not authority to:

- execute the real promotion or change either real CSV;
- commit, push, or merge;
- run a refresh, bakeoff, retrain, or model/feature promotion;
- claim predictive improvement or validation; or
- accept or rule on any result.

The active and candidate SHA-256 values remain exactly
`b3c28e4206ea347919daf3f895a0475f125dae27138e243f4dbe4b0e40649f38` and
`15e17cd9164c5ab05f0440f0ca90bb93f89ce7735efa517d331495cd2bea11d0`;
`app/data/training/cfbd_promotion_history` is absent. Nothing was promoted.

H2 QB rushing remains **UNDER TEST** with no result. This implementation and its CLEAR supply no
evidence about rushing or predictive value.
