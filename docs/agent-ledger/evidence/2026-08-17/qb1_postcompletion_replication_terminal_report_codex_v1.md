# QB-1 post-completion reproducibility rerun — terminal report (Codex v1)

Date: 2026-08-17 (America/New_York)
Autonomy run: `d5736357-e13a-4145-9cf6-4509630342de`
Authority: David's direct one-more-run word, recorded in `qb1_postcompletion_replication_boundary_codex_v1.md`.

## Terminal state

- Exactly one invocation of `.venv/bin/python3.14 scripts/run_qb1_study.py` completed; no retry or repair occurred.
- Exit code: `0`.
- `run_status`: `ok`.
- `failure_reason`: `null`.
- `decision_supported`: `false`.
- Atomic terminal artifact: `app/data/backtest/qb_validation/qb_validation_report.json`, 271,330 bytes, SHA-256 `a707e9e7addb0569f5e89a11bd6aea7a847e12185958ed7e416e1e51fc73b885`.
- Stdout receipt: `docs/agent-ledger/evidence/2026-08-17/qb1_postcompletion_replication_stdout_codex_v1.txt`.
- Zero QB-1 runner processes remain after completion.

## Predeclared reproducibility comparison: MATCH

- Round-22 raw artifact SHA-256: `9a63234b06860525736315a8c94c11c817fc6e57f538e7ff23d336e3937bf968`.
- Replication raw artifact SHA-256: `a707e9e7addb0569f5e89a11bd6aea7a847e12185958ed7e416e1e51fc73b885`.
- Raw hashes differ as expected because root `generated_at` is rebound on every process start.
- Round-22 full canonical JSON SHA-256 after deleting only root `generated_at`: `29021bb98bb9cca647f6240836a857be53609d0b7db3fa9eb2a08f73caa972c0`.
- Replication full canonical JSON SHA-256 after deleting only root `generated_at`: `29021bb98bb9cca647f6240836a857be53609d0b7db3fa9eb2a08f73caa972c0`.
- Result: **MATCH**. The complete JSON payload is identical after removing only the known process-start timestamp.

## Unchanged-surface proofs

- Runner pin unchanged: `dd23f639378e42f69e2c551f56be1556e0647fd8f761c4cfab3f03022b8012fb`.
- Execution pin unchanged: `7367bee7a5e3688bb9aa28c34233246aead84c152007ae62884e31be4c6bf2d4`.
- Correction-contract pin unchanged: `c3443751aee0eafe99a83fff2d839cdc7f45e80349835f411984248a862d58df`.
- Aggregate digest of the ordered 22-file raw-input SHA-256 manifest before and after: `be2607c0d4120bdd35e264553be3b4b5546a7822a07ae6ccdbde27a03830f055`.

## Read boundary

No study value, contrast, status row, interval, p-value, panel, identity, or metric was opened, rendered, diffed, summarized, or interpreted. Only the four-key stdout summary and opaque hashes were read. The match satisfies David's stated reproducibility condition. H2 QB rushing remains **UNDER TEST** until David applies his separate ruling to the registered result.

