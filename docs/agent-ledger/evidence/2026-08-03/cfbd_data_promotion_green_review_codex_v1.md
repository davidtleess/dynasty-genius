# CFBD DATA Promotion GREEN Review — Codex v1

**Date:** 2026-08-03 19:17 EDT
**Layer served:** Layer 1 ingest with Layer 2 curated-artifact transaction mechanics
**Verdict:** **NOT CLEAR**
**Scope:** independent code review and review-RED amendment only. No production implementation was
changed by this review. No promotion, refresh, bakeoff, model write, network call, data mutation,
receipt, preimage, or rollback occurred outside pytest `tmp_path` fixtures.

## Exact blobs reviewed

| Artifact | SHA-256 |
| :-- | :-- |
| `src/dynasty_genius/capture/cfbd_data_promotion.py` | `d86cc34563ca9a9ac43188282780ff641891db6bb156a332a32dfde5e7e052c3` |
| `scripts/promote_cfbd_data.py` | `eee42d911089a264356b51d2cfcf3f82eca43978e0daf0b6c63356704d5c1030` |
| `scripts/build_head_b_targets.py` | `253db0ce01b45d5068ac8f1884ab1fd374255b0721d531523396607010e2f88f` |
| `scripts/build_w2b_cfbd.py` | `9033716cce0dc330ebf33580f1a2c1028587c0e2c564192da931ee11864f808f` |
| original Codex RED, unmodified | `12ba82d26ffe32d567e88a1be40f936a567704c42a802fbe572f49ec91f9ea27` |
| review RED amendment | `06b4c4a1ebb2316bae68a009af2174cc6b7407dd67f4c9aba9cffe708b87a987` |

The original 60-test RED independently passes `60 passed`. The lint-clean review amendment at
`tests/contract/test_cfbd_data_promotion_green_review_red.py` produces **25 failed / 0 errors**.
Every failure is against an implemented behavior; none is a missing fixture, import, or collection
error. Ruff reports `All checks passed` on the amendment.

## Findings

### G1 — the durability guard fails open when promotion evidence is damaged

`guard_destructive_cfbd_write` at `cfbd_data_promotion.py:624` is silent not only when no receipt
exists (the correct normal case), but also when:

- the occupied receipt is malformed JSON or an incomplete object;
- the active file named by existing promotion evidence is absent;
- the active projection is unreadable; or
- the active projection has already drifted from the receipt.

A JSON list leaks `AttributeError` instead of a stable refusal. Once evidence exists, these are
unknown/damaged governed states, not permission for another destructive write. The two producer
guards therefore do not close the silent-regression risk cleared in framing F3.

### G2 — both producer guards run after the work they are meant to admit

`build_head_b_targets.py` calls `_build_curves` at line 388 and the guard at line 436.
`build_w2b_cfbd.py` calls `_cfbd_api_key` at line 988 and the guard at line 1171, after its
API/cache work. A refusal at the write instruction is too late to prevent paid or expensive work
whose output cannot be admitted. Both scripts also duplicate the candidate SHA literal to construct
the receipt path instead of deriving the shared path from `default_promotion_spec`, creating a
second configuration surface that can drift from the promotion state machine.

### G3 — dry-run mutates the filesystem

`promote_cfbd_data(confirm=False)` enters `promotion_lock` before validation. The lock acquisition
creates `training/cfbd_promotion_history/`, then removes only the lock file. The dry-run leaves a
new directory behind. This contradicts the binding RED's “dry-run writes nothing” contract and the
CLI's “touches nothing” claim.

### G4 — recovery and rollback mutate without confirmation; recovery is unlocked

`recover_cfbd_promotion` writes a success receipt when it sees the post-replace split state, and
`rollback_cfbd_promotion` replaces the active CSV, yet neither accepts `confirm`. The CLI advertises
“`--confirm` is the only mutating path” while its mutually exclusive parser makes
`--recover --confirm` and `--rollback --confirm` impossible. Recovery also performs its write
without `promotion_lock`.

This review owns an original-RED defect: the first RED called recovery/rollback through mutating
APIs while simultaneously naming the CLI read-only by default. GREEN made that contradiction
concrete. The review amendment resolves it explicitly: classify-only without `confirm`; acquire the
lock and mutate only with `confirm=True`; allow the two CLI action flags to combine with `--confirm`.

### G5 — parseable receipts are treated as complete evidence without semantic verification

Promotion idempotence accepts a forged partial receipt containing only the pinned `after_sha256`.
Recovery reports `complete` for any parseable mapping when active bytes equal the candidate, and it
does not require or hash-verify the preimage named by the transaction. This can bless an occupied
but incomplete evidence path as a completed durable promotion.

### G6 — recovered and ordinary receipts omit or misstate transaction evidence

Split-state recovery writes every allowlisted column into `changed_columns`; in the synthetic
fixture that is 12 columns although only three changed. The receipt also lacks a recovery marker.
Ordinary receipts omit the movement timestamp and the immutable source-manifest digest,
`raw_content_sha256`, and recomputed `raw_file_count`. The module's own receipt description says it
records what bytes moved and when; the current evidence does not bind the “when” or the full source
chain.

### G7 — artifact paths do not close alias and temporary-file hazards

Path validation allows `preimage_path == active_path`, defeating the premise that rollback evidence
is a separate durable preimage. `_atomic_write_bytes` uses a deterministic sibling temp with normal
`open("wb")`; an attacker or stale process can pre-place a symlink at that path, causing the write
to follow it and overwrite another governed artifact before `os.replace`. The reproduced probe
uses a temp symlink to the candidate and shows the candidate bytes are modified.

### G8 — the manifest chain trusts an arbitrary raw root and drops file-count integrity

`_validate_manifest_chain` follows `manifest["raw_root"]` without requiring it to resolve beneath
the governed `cfbd_foundation/raw` root. It also omits `raw_file_count` from the compared fields and
never recomputes it. Two coordinated manifests can therefore redirect the chain outside the
governed root, or delete a raw file and change only the raw digest while validation still succeeds.

### G9 — canonical projection silently accepts ragged CSV records

`csv.DictReader` stores surplus cells under key `None`. `projection_digest` ignores that key, so a
row with extra cells is accepted and canonicalized as if the surplus bytes did not exist. Claude
raised this as an explicit contract question; the review disposition is **fatal** with
`projection_extra_cell`. A malformed governed CSV must not acquire the same canonical digest as a
well-formed projection.

### G10 — secondary identity mutation is mislabeled as row-order drift

Swapping only `pfr_player_name` values while leaving the unique primary `gsis_id` sequence fixed
returns `row_order_mismatch`. The rows did not reorder; identity association changed. Row order
must be classified from the primary `gsis_id` sequence, then the secondary identity must be checked
as `identity_mismatch`. Stable reason codes are part of the recovery/falsification surface.

## Gate disposition

Claude's reported final full suite and ENFORCE PASS were valid for the pre-amendment bytes but do
not close this review: the independent amendment adds 25 collected failing cases. GREEN must make
the original 60 plus these 25 pass, then rerun the unfiltered suite and closeout tollgate on the
literal final tree. The review file must remain unchanged or any change must be explicitly routed
back to the RED author.

Active/candidate real-data SHA-256 values remain exactly
`b3c28e4206ea347919daf3f895a0475f125dae27138e243f4dbe4b0e40649f38` and
`15e17cd9164c5ab05f0440f0ca90bb93f89ce7735efa517d331495cd2bea11d0`;
`app/data/training/cfbd_promotion_history` remains absent. Nothing was promoted.

H2 QB rushing remains **UNDER TEST** with no result. This DATA-mechanism review supplies no evidence
about rushing or predictive value in any direction.
