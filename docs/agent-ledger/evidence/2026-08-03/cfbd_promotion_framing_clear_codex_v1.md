# CFBD DATA promotion framing — Codex CLEAR v1

**Reviewer:** Codex (independent lane)
**Reviewed:** 2026-08-03
**Target:** `cfbd_promotion_framing_claude_v2.md`
**Target SHA-256:** `e797d6cf0d1be65199eab5b36720f86024e9498f217f77fe809281b5bd0e7413`
**Verdict:** **FRAMING CLEAR — the RED may open under David's existing DATA-scoped authority.**

This clears the framing and its test contract, not an implementation. It is not a promotion,
refresh, bakeoff, model/feature use, model write, RED result, GREEN, commit, or validation verdict.

## Enumerated checks

1. **F1 closed:** v2 retracts the false three-reverter claim and correctly distinguishes total
   destruction (`build_head_b_targets.py`), targeted CFBD overwrite (`build_w2b_cfbd.py`), and a
   whole-file rewrite that preserves already-present CFBD projection fields
   (`build_w2_features.py`).
2. **F2 closed:** v2 requires full-file before/candidate/after hashes for byte provenance plus a
   separate versioned keyed-projection digest for CFBD retention and drift classification.
3. **F3 closed:** durable closure requires guarding/repointing the two destructive producers or
   enforcing the projection state at every permitted consumer boundary. Detector-only closure is
   withdrawn; absent that protection, the only honest disposition is "applied but not durable."
4. **F4 closed:** the two full SHAs and every semantic invariant — 117 rows, 1,123 cells, QB-only,
   exact 12-column allowlist, row/header/order/identity stability — are independently recomputed,
   fatal gates in a reviewed one-time promotion specification. Regeneration requires a new spec.
5. **F5 closed:** landing disposition is `existing_consumer` at
   `scripts/run_phase20_bakeoff.py`, permitted only for separately authorized non-promoting QB
   evaluation and not invoked here. The TE promotion script is correctly excluded.
6. **F6 closed:** no unnecessary paid-refresh interlock is added. The promotion entrypoint itself
   must be offline by construction and executable tests make refresh/network/subprocess/model/
   bakeoff side effects fatal.
7. **F7 closed:** the RED seed set now includes the source-manifest chain, post-validation TOCTOU,
   post-replace readback, idempotence preserving the original preimage, rollback CAS, the full 3x3
   active/receipt recovery matrix, stale-lock behavior, write/fsync/directory-sync failure,
   projection-aware drift, identity ambiguity, path/inode/filesystem safety, and immutable
   receipt/preimage collision handling.
8. **Boundary preserved:** DATA-only authority, receipt-not-validation, no model write, and no
   inference about predictive value all remain explicit. H2 QB rushing remains **UNDER TEST** with
   no result; none of the promoted fields is a rushing field and this work supplies no evidence
   about rushing.

## Projection digest canonicalization supplied for the RED

The earlier Codex values (`32ea9f23...` / `56758151...`) used source row order and compact JSON of
only the row arrays, with an ad hoc ordered field list. They were reproducible within that probe but
not a written cross-implementation contract. They are **superseded and must not be load-bearing**.

Adopt this candidate specification for the RED:

- `projection_digest_version = "cfbd_qb_projection.v1"`.
- Required ordered fields:
  1. `gsis_id`
  2. `qb_completion_pct_final`
  3. `qb_completion_pct_final_source`
  4. `qb_completion_pct_final_missing`
  5. `qb_yards_per_attempt_final`
  6. `qb_yards_per_attempt_final_source`
  7. `qb_yards_per_attempt_final_missing`
  8. `qb_td_int_ratio_final`
  9. `qb_td_int_ratio_final_source`
  10. `qb_td_int_ratio_final_missing`
  11. `qb_sack_rate_final`
  12. `qb_sack_rate_final_source`
  13. `qb_sack_rate_final_missing`
- Parse the CSV as UTF-8/RFC-4180 strings. Every required cell must exist and be a string. Preserve
  it exactly: no trimming, numeric coercion, Unicode normalization, or null folding. Empty string is
  exactly `""` and is distinct from a missing cell. Missing/`None` is fatal.
- `gsis_id` must be nonblank and unique. Sort row arrays by the UTF-8 byte sequence of `gsis_id`.
  This intentionally makes the projection digest insensitive to file-row reordering; whole-file
  SHA and the promotion's separate row-order gate still detect/order-govern that event.
- Construct this three-element JSON array:
  `[projection_digest_version, ordered_fields, sorted_row_arrays]`.
- Serialize with Python's reference operation
  `json.dumps(payload, ensure_ascii=False, separators=(",", ":"))`, with no trailing newline;
  encode the resulting text as UTF-8; SHA-256 those exact bytes.
- The digest covers `gsis_id`, not `pfr_player_name`. The promotion's separate identity gate still
  requires both identity columns to remain present, unique, ordered, and unchanged. A display-name
  change therefore produces whole-file/identity drift without falsely claiming that the keyed CFBD
  values disappeared.

### Independently measured values under `cfbd_qb_projection.v1`

- active: `683384b89c860f67bf963d2e03022c9fc119572b52b3afc95c26b919d347f3b3`
- candidate: `f2239463bf8da3a48d114b613cb75782d3bccc797cef059c071c1d08795c1dd0`

Claude must independently reproduce both before the digest becomes load-bearing.

### Golden vector

Exact serialized bytes (shown as UTF-8 text):

```json
["cfbd_qb_projection.v1",["gsis_id","qb_completion_pct_final","qb_completion_pct_final_source","qb_completion_pct_final_missing","qb_yards_per_attempt_final","qb_yards_per_attempt_final_source","qb_yards_per_attempt_final_missing","qb_td_int_ratio_final","qb_td_int_ratio_final_source","qb_td_int_ratio_final_missing","qb_sack_rate_final","qb_sack_rate_final_source","qb_sack_rate_final_missing"],[["a","0.650","cfbd","0","8.0","cfbd","0","3.0","cfbd","0","0.04","cfbd","0"],["b","0.600","cfbd","0","7.5","cfbd","0","2.0","cfbd","0","","","1"]]]
```

Expected SHA-256:
`fed6b75a7b9d038ea4e59807a594aae16ee1e3ab924c44f6b41600af484f2945`.

The RED may improve this candidate canonicalization only by naming the change, publishing a new
version/golden vector, and obtaining convergence before implementation depends on it. It may not
silently reuse `cfbd_qb_projection.v1` for different bytes.
