# QB-1 post-completion reproducibility rerun boundary — Codex v1

Date: 2026-08-17 (America/New_York)
Autonomy run: `d5736357-e13a-4145-9cf6-4509630342de`
Authority: David, direct in this session: *"why not run it 1 more time? if it is the same i will accept it"*.

## Why this is a separate run

The registered execution completed once. This additional fire is a post-completion reproducibility check authorized by David; it is not silently counted as another preregistered sample and does not widen the registered inference contract.

## Exact one-run boundary

1. Fire `scripts/run_qb1_study.py` exactly once using the unchanged reviewed code and unchanged frozen registered inputs.
2. The runner may perform only its normal atomic write to `app/data/backtest/qb_validation/qb_validation_report.json`. Capture stdout to a new 2026-08-17 receipt.
3. No code, test, registration, raw input, provider, configuration, or model mutation; no repair or second fire; no commit or push.
4. Do not open, render, summarize, diff, or interpret any study value from either report.

## Predeclared meaning of "same"

Raw file SHA-256 equality is not expected because the runner binds a new root `generated_at` at process start. Before the replication, compute an opaque canonical SHA-256 over the entire JSON document after deleting **only** the root `generated_at`, using:

```sh
jq -S -c 'del(.generated_at)' app/data/backtest/qb_validation/qb_validation_report.json | shasum -a 256
```

The replication is `MATCH` only if all of the following hold:

- runner exit code is `0`;
- stdout summary is `run_status=ok`, `failure_reason=null`, `decision_supported=false`;
- the post-run canonical SHA-256, computed by the exact command above, equals the pre-run canonical SHA-256;
- reviewed code pins and all frozen raw-input digests remain unchanged; and
- exactly one runner process fired and zero remain afterward.

If any condition fails, stop as `MISMATCH` without inspecting values. A match is reproducibility evidence for this exact frozen execution only. H2 QB rushing remains **UNDER TEST** until David performs the separate registered-result ruling he said he will make on a match.

## Pre-fire pins

- runner: `dd23f639378e42f69e2c551f56be1556e0647fd8f761c4cfab3f03022b8012fb`
- execution: `7367bee7a5e3688bb9aa28c34233246aead84c152007ae62884e31be4c6bf2d4`
- correction contracts: `c3443751aee0eafe99a83fff2d839cdc7f45e80349835f411984248a862d58df`
- completed Round-22 artifact: `9a63234b06860525736315a8c94c11c817fc6e57f538e7ff23d336e3937bf968` (271,330 bytes)
- completed Round-22 stdout receipt: `61ae2059f48c3d895e4d2c83cf4ede79ba705d7afd3856aafdb77f43ef80a643`
- completed Round-22 canonical report digest excluding only root `generated_at`: `29021bb98bb9cca647f6240836a857be53609d0b7db3fa9eb2a08f73caa972c0`
- active QB-1 runner processes before fire: zero
