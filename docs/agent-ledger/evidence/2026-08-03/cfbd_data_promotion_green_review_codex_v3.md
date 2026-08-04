# CFBD DATA Promotion GREEN Review — Codex v3

**Date:** 2026-08-03
**Layer served:** Layer 1 ingest with Layer 2 transaction mechanics
**Verdict:** **NOT CLEAR**
**Scope:** literal final-byte audit plus a separate review-RED amendment. No production code or real
data was changed by this review. All mutation probes ran beneath pytest `tmp_path`.

## Verified input and passing baseline

The implementation hashes supplied by Claude match the workspace:

- `src/dynasty_genius/capture/cfbd_data_promotion.py`:
  `ac4051196ac575f22090f5a3d44d9d870d24b05008bd07b7da209b11f8b2cd42`;
- `scripts/promote_cfbd_data.py`:
  `1fce5603adec0168410a7308c8a37880886fd3bc8beb559f235cb0e518ccfe4b`.

Codex independently reran the three existing RED files: **100 passed / 0 failed**. The final full
suite and ENFORCE evidence is accepted as measured for those bytes, but it does not close the new
residuals below.

The earlier RED files remain unchanged. A separate third amendment was added:

`tests/contract/test_cfbd_data_promotion_green_review_red_v3.py`
SHA-256 `a0111472476d09e2ee26b4a64cd092bd35a1502ec3161e387eada66a35808f17`

It is Ruff-clean and produces **12 failed / 0 errors**. Binding focused census is now **112
collected / 100 passed / 12 failed / 0 errors**.

## G16 — `manifest_path` is omitted from the distinct-role gate

`_ARTIFACT_ROLES` names active, candidate, preimage, promotion receipt, rollback receipt, and lock,
but omits the governed source manifest. Reproduced with `lock_path=manifest_path`:

1. validation successfully reads the manifest;
2. lock acquisition sees the manifest file, finds no `pid=`, labels it stale, and unlinks it;
3. the promotion proceeds; and
4. lock cleanup removes the replacement lock, leaving the governed manifest absent.

The function returns success rather than `path_alias`. `manifest_path` must participate in the same
path/resolved-path/inode distinctness matrix before anything is opened. The probe additionally
requires active, candidate, manifest, preimage, and receipt to remain unchanged on refusal.

## G17 — the receipt's promised complete honesty/spec binding is still optional

GREEN v2 added value checks, but `REQUIRED_RECEIPT_KEYS` still omits `model_changed`, `bakeoff_run`,
`predictive_validation_run`, `promotion_decision`, `active_path`, and `candidate_path`.
`_assert_receipt_matches_spec` checks the three boolean fields only **if present**, does not require
`promotion_decision`, and does not check active/candidate paths at all.

Consequently, idempotent success accepts receipts with any of those honesty fields removed or with
active/candidate paths rewritten to foreign locations. This contradicts the G13 disposition that a
receipt must bind this exact transaction and carry the full honesty block. Required resolution:

- require all receipt fields emitted by the honesty block;
- require each boolean to be exactly false;
- require `promotion_decision="not_applicable_data_movement"`; and
- require active, candidate, and preimage paths to equal this spec.

The writer guard has no `PromotionSpec`, but it must at least require the full receipt structure and
honesty values before treating occupied bytes as promotion evidence.

## G18 — mutation-relevant evidence is not revalidated under lock

G11 was only partially closed. Active/candidate CAS rechecks now occur under lock, but concurrent
evidence changes between unlocked classification and lock acquisition are still overwritten or
consumed:

- **promotion:** a concurrently occupied preimage or receipt path is overwritten; the promotion
  succeeds instead of refusing `evidence_collision` before the first write;
- **recovery:** a concurrently changed preimage leaks `ValueError`, while a concurrently occupied
  receipt is overwritten by a success receipt;
- **rollback:** a concurrently changed preimage is copied over active, destroying the promoted
  bytes, before post-readback reports `post_replace_verification_failed`.

Every confirmed entrypoint must re-establish its complete mutation premise inside the lock before
writing:

- promotion: active/candidate pins **and** receipt absence **and** preimage absent-or-valid policy;
- recovery: active candidate pin, receipt absence, and preimage pinned to the original active;
- rollback: active candidate pin, preimage pinned to the original active, and rollback-receipt
  absence.

Stable refusals must occur while governed bytes and any concurrent evidence remain untouched.

## Gate disposition

Claude's full-suite census (`4,409 passed / 12 skipped / 9 xfailed`) and ENFORCE PASS predate this
12-test amendment and are superseded for landing. Required next gate is all **112** focused tests,
then a fresh unfiltered suite and ENFORCE on literal final bytes.

Real active/candidate hashes remain exactly
`b3c28e4206ea347919daf3f895a0475f125dae27138e243f4dbe4b0e40649f38` and
`15e17cd9164c5ab05f0440f0ca90bb93f89ce7735efa517d331495cd2bea11d0`;
promotion history remains absent. Nothing was promoted.

H2 QB rushing remains **UNDER TEST** with no result. This mechanism audit supplies no evidence about
rushing or predictive value.
