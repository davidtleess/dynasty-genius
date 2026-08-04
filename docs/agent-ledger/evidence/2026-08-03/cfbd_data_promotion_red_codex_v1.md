# CFBD DATA promotion — Codex RED v1

**Author:** Codex (independent RED lane)
**Date:** 2026-08-03
**Test:** `tests/contract/test_cfbd_data_promotion_red.py`
**Test SHA-256:** `12ba82d26ffe32d567e88a1be40f936a567704c42a802fbe572f49ec91f9ea27`
**Basis:** `cfbd_promotion_framing_claude_v2.md` at
`e797d6cf0d1be65199eab5b36720f86024e9498f217f77fe809281b5bd0e7413`, cleared by
`cfbd_promotion_framing_clear_codex_v1.md` at
`ea7cadea401147c6f528c09cbd36b878103069cdc99a87ddeaa744b6ef5f6d48`.

**Verdict:** **RED ESTABLISHED — Claude owns GREEN.**

## Scope and boundary

Only the RED test, this evidence artifact, the wire record, and an additive ledger entry were
written. No production module, script, writer guard, data, promotion, refresh, bakeoff, model,
receipt, preimage, rollback, or GREEN was created. The test uses synthetic files only beneath
`tmp_path`; it performs no network call or subprocess.

H2 QB rushing remains **UNDER TEST** with no result. The four promoted values are completion %, YPA,
TD:INT, and sack rate; this RED supplies no evidence about rushing or predictive value.

## RED census

```text
60 tests collected
60 failed
0 errors
0 collection errors
ruff: All checks passed
```

Failure attribution:

- **57** require the absent core file/API
  `src/dynasty_genius/capture/cfbd_data_promotion.py`;
- **2** require the absent pre-write integration call in `build_head_b_targets.py` and
  `build_w2b_cfbd.py`; and
- **1** requires the absent thin CLI `scripts/promote_cfbd_data.py`.

The first run produced 11 failures + 47 fixture-setup errors because the fixture imported the
missing module. That was an instrument defect, not a useful RED distinction. The import now occurs
inside each test body: the final census is 60 failures / zero errors.

## Required GREEN surface

The core module must provide:

- `PROJECTION_DIGEST_VERSION`, `PROJECTION_FIELDS`;
- `CfbdPromotionError` carrying a stable `.reason`;
- immutable `PromotionSpec` with the paths, hashes, projection hashes, exact semantic counts,
  allowlist, and identity columns named in the test fixture;
- `default_promotion_spec(root=...)` carrying the real one-time 874/173/117/1,123 pins;
- `projection_digest(path)` implementing `cfbd_qb_projection.v1` exactly;
- `validate_promotion(spec)` — read-only, recomputes rather than trusts every gate;
- `promote_cfbd_data(spec, confirm=False, fault_hook=None)`;
- `recover_cfbd_promotion(spec)`;
- `rollback_cfbd_promotion(spec)`;
- `promotion_lock(spec)`; and
- `guard_destructive_cfbd_write(active_path=..., receipt_path=..., writer_name=...)`.

The CLI must be read-only by default and expose only `--confirm`, `--recover`, and `--rollback` over
the core. It may not import/call refresh, network, subprocess, model, or bakeoff code.

## Contract groups

### 1. Canonical projection digest

- cross-lane golden vector exactly `fed6b75a...f2945`;
- row-order-independent via UTF-8 `gsis_id` byte sorting;
- exact CSV strings, no coercion or empty/null folding;
- missing required cells, blank IDs, and duplicate IDs are named fatal errors; and
- default real pins include active/candidate projection hashes `683384b8...` / `f2239463...`.

### 2. Manifest and semantic gate

- full and projection hashes are independently fatal;
- latest manifest and immutable run manifest must agree on schema/run/input/curated/raw chain;
- raw snapshot bytes are recomputed with the refresh pipeline's filename-plus-file-SHA algorithm,
  excluding the later `manifest.json` envelope rather than trusting two mutually consistent
  manifests;
- row count, header set/order, row order, both identity columns, QB-only changes, exact allowlist,
  changed-row count, and changed-cell count each have an isolated failing mutation; and
- secondary identity blank/duplicate cases are distinct from projection-key failures.

### 3. Transaction and durable evidence

- dry-run writes nothing and carries no validation/model verdict;
- confirm writes a hash-verified preimage before active replacement, re-reads the active bytes and
  projection after replacement, then writes an honest receipt;
- receipt explicitly records `decision_supported=false`, `model_changed=false`,
  `bakeoff_run=false`, `predictive_validation_run=false`, and
  `promotion_decision=not_applicable_data_movement`;
- exact file side effects are active + preimage + receipt; locks/temps disappear;
- every atomic replacement uses a sibling temp on the target filesystem;
- idempotent rerun preserves the original evidence byte-for-byte;
- active and candidate TOCTOU each fail closed at the last pre-swap CAS;
- post-replace corruption cannot receive a success receipt;
- file and parent-directory fsync are load-bearing; and
- preimage/receipt collisions never overwrite prior evidence.

### 4. Recovery, rollback, locking, and aliases

- crash after active replace and before receipt is a named recoverable split state;
- all nine active `{old,new,unknown}` × receipt `{absent,valid,corrupt}` states are specified;
- rollback is CAS-guarded, restores the exact preimage, preserves the promotion receipt, and emits
  a separate rollback receipt;
- rollback cannot erase intervening bytes;
- a live lock refuses while an abandoned lock does not deadlock forever; and
- same path, hardlink, and symlink aliases between active/candidate are fatal.

### 5. Legacy writers and offline boundary

- the two destructive writers must call the shared guard before their `open("w")` boundary;
- `build_w2_features.py` is deliberately not assigned that destructive premise;
- the core has a static import denylist for scripts, refresh, network, subprocess, models, and eval;
  and
- the thin CLI is dry-run by default and routes only the three governed actions.

## Data non-mutation control

After RED execution:

- active SHA-256 remains
  `b3c28e4206ea347919daf3f895a0475f125dae27138e243f4dbe4b0e40649f38`;
- candidate SHA-256 remains
  `15e17cd9164c5ab05f0440f0ca90bb93f89ce7735efa517d331495cd2bea11d0`.

No full-suite claim is made: this intentionally failing RED is the focused gate. GREEN must first
make this exact test blob pass, then run the proportionate focused/full closeout gates before any
promotion is even considered.
