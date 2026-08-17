From Codex (review lane) [w#qb1-exec-1] — QB-1 report-schema diagnostic registration read: IMPLEMENTATION, not amendment; Round-19 metric-free observability boundary

# QB-1 report-schema diagnostic registration read — Codex v1

Date: 2026-08-16 (America/New_York)  
Run: `f8f7551c-a145-46e2-b9b4-dec427f313ba`  
Input state: revision 119, ACTIVE `verifying`, terminal state `null`

## Decision

The measured `diagnostic_payload_unavailable` disposition is accepted. The next correction is **IMPLEMENTATION, not amendment**, but only under the bounded observability design below.

The registered study, frozen inputs, contrasts, metric definitions, status vocabulary, inference contract, terminal-report schema, and decision law do not change. In particular, the failed terminal report remains the existing metric-free six-key `qb_validation_report.v1` object. The implementation adds only a non-metric, process-local failure-origin channel used by the CLI stdout receipt when a run fails.

H2 QB rushing remains **UNDER TEST with no result**.

## Independent registration read

- Claude diagnostic: `qb1_report_schema_diagnostic_claude_v1.md`, SHA-256 `1fee12534ceab241972289dfbf7baaf31e7ff09b943ae3671e88b803d590b734`.
- Frozen registration: `docs/validation/2026-07-21-qb-1-study-registration.md`, SHA-256 `319ab63f35c0e47a72e0a6d3f9340e49d635556f069bb940874b16221e828e02`.
- Failed terminal report: SHA-256 `80d060195858da20dfa3b56a35bb6db929e60a46b1e7f53bc15500da8b9c4e62`.
- Failed stdout receipt: SHA-256 `ecc7b05d3ca3778a825c8ebfef846d2e0569d52bd8fd17d4a23bc7d5b3930311`.
- Fired publication code: `execution.py` SHA-256 `12df03a0258c62f375675cfa7b068ba4564db83e2474da29959ef1537831e3e8`; `run_qb1_study.py` SHA-256 `7de911cccdcb17ae0e37ca48b5816a50420dbcd0e61303f663553d381c97a798`.
- The output store contains the terminal envelope and the 22 frozen registered inputs; no durable rejected payload or clause-detail artifact exists. Validator replay therefore had no admissible input and was correctly not performed.
- `QBValidationFailure` carries `reason` and `detail`; both publication catches retain only `reason`. The execute-path catch and publication-gate catch consequently produce indistinguishable durable envelopes. The exact catch and exact raise site remain unmeasured.
- The existing terminal-report contract requires a failed report to contain exactly `schema_version`, `generated_at`, `registration_hash`, `run_status`, `failure_reason`, and `decision_supported`, with no metric blocks or disclosures. That contract remains unchanged.

## Why raw `.detail` is forbidden

The raw exception detail is not a safe diagnostic channel. Several `report_schema_invalid` details interpolate registered payload or comparison values, including deltas, confidence intervals, p-values, status fields, exclusion rows, and H5 values. Copying `.detail` into the failed report, stdout, a sidecar, logs, or any other durable artifact could publish a partial registered result after a failed run and would defeat the metric-free failure law.

Round 19 therefore must not serialize, hash, truncate, paraphrase, log, or otherwise persist `failure.detail`, the rejected payload, exception messages, local-variable representations, or comparison values. A digest of raw detail is also out of scope because it creates an unnecessary content-derived side channel.

## Authorized Round-19 implementation boundary

Exactly these files may change:

1. `src/dynasty_genius/eval/qb_validation/execution.py`
2. `scripts/run_qb1_study.py`
3. `tests/contract/test_qb1_green_correction_contracts.py`

The implementation may add an optional in-memory observer/sink to the publication function. On a failed run, it may expose one closed diagnostic object to the CLI, and only the CLI stdout summary may persist it:

```json
{
  "phase": "execute | publication_gate",
  "sites": [
    {"path": "repo/relative/path.py", "function": "function_name", "line": 123}
  ]
}
```

Closed semantics:

- `phase` is exactly `execute` for the first publication catch or `publication_gate` for the second.
- `sites` is the ordered, non-empty set of Python traceback frames inside the repository, from outermost in-repository frame to the raise origin. Each site has exactly `path`, `function`, and positive integer `line`.
- `path` is repository-relative and may not be absolute, contain `..`, or identify a path outside the repository.
- `function` is the runtime code-object name only. No source line, expression, argument, local variable, object representation, or exception text is included.
- The last site is the in-repository raise origin. Helper-mediated refusals retain the in-repository caller frames needed to distinguish the caller from the helper.
- The diagnostic is emitted only for a failed run. The successful report and successful stdout summary remain unchanged.
- Observer/sink absence or failure may not prevent the metric-free terminal report from being written. Process-control exceptions retain their established behavior.
- The terminal JSON artifact remains byte-shape compatible at exactly six keys on failure. The diagnostic must never be passed to `assemble_terminal_report`, `validate_report_output`, or `write_terminal_report_atomic`.
- No diagnostic sidecar is authorized.

## RED-first acceptance matrix

Before implementation, focused contracts must fail for the missing behavior and cover all of the following:

1. An execute-path `QBValidationFailure` yields `phase=execute`, an exact repository-relative traceback tail, and the unchanged six-key failed report.
2. A publication-gate `report_schema_invalid` yields `phase=publication_gate`, an exact repository-relative traceback tail, and the unchanged six-key failed report.
3. A helper-mediated refusal retains the caller and raise-origin sites needed to locate the refusing clause.
4. Sentinel metric values placed in `failure.detail`, rejected payloads, and ordinary exception messages occur nowhere in the terminal artifact or captured stdout diagnostic.
5. An ordinary exception produces the established `execution_error` reason without serializing its message or local state.
6. A missing or deliberately throwing observer does not suppress or corrupt the failed terminal artifact.
7. A successful execution does not emit the failure diagnostic and leaves the existing success surface unchanged.
8. Paths are repository-relative; absolute paths and traversal components are refused or omitted.

Required proof is the focused correction bundle plus a CLI-level synthetic probe of both catch phases. No registered composition, folds, fit, inference, comparison, provider fetch, input mutation, or registered rerun is part of Round 19.

## Next gate

Claude may implement this one revision-guarded Round 19 test-first. Codex then independently reviews the diff, focused contracts, unchanged frozen pins, exact failed-report shape, and CLI-level synthetic proofs. A fresh registered rerun remains held until Codex issues explicit CLEAR. David's standing continuation word supplies the conditional rerun authority; it does not waive the review gate or authorize a second fire.

No commit or push is authorized. Any registered result remains routed untouched to David for his separate ruling.

PLEASE REPLY with: (a) ACK revision 120 and implement exactly this bounded Round 19, or (b) a named state, scope, schema, or feasibility mismatch before writing product code.
