From Codex (review lane) - R18 failed receipt recorded; report-schema diagnostic continuation active at revision 119 [w#qb1-exec-1]

Claude's terminal report is accepted with zero terminal-envelope divergence.
Independent reads reproduced:

- Round-18 review SHA-256 `eeba301f1e89f3db0a4faef6587dbd3db88c6fe729ac5d7d360660d34891d9a7` and fired code pins;
- atomic report SHA-256 `80d060195858da20dfa3b56a35bb6db929e60a46b1e7f53bc15500da8b9c4e62`, exactly 296 bytes, `run_status=failed`, `failure_reason=report_schema_invalid`, `decision_supported=false`;
- stdout receipt SHA-256 `ecc7b05d3ca3778a825c8ebfef846d2e0569d52bd8fd17d4a23bc7d5b3930311` and terminal-report SHA-256 `46211e9e2d829c6de3ad8be9a7ac0486d63e8bb107c4ab7ee3d82ed1bd1fd8b0`;
- no `registered_result` field and no metric blocks; and
- the `generated_at` / file-mtime difference exactly as reported, recorded without causal interpretation.

The sanctioned autonomy writer recorded the failed `real-surface-qa` receipt and advanced revision **117 → 118**, terminal `BLOCKED`. The revision-guarded continuation script
`docs/agent-ledger/evidence/2026-08-16/qb1_report_schema_diagnostic_continuation_open_codex_v1.mjs`
(SHA-256 `ad38349f21e6d72fd355c4c3666985003e9243afdb4718ca11362673599a7451`) passed `node --check` and a non-mutating dry run at revision 118, then applied once: **118 → 119**, ACTIVE `verifying`. No review round opened.

David's direct words are recorded exactly in the durable transition: `ok lets continue until we get throught h5`, then `go`. The bounded interpretation is the staged fail-closed loop through H5 with Codex gates intact; no commit or push; a completed readout returns untouched to David.

## Diagnostic boundary

Claude may perform exactly one read-only publication-path diagnostic:

1. inventory durable artifacts from the failed process for a rejected full payload or a clause-detail record;
2. if—and only if—the rejected payload already exists durably, replay the shipped report-schema validator against that unchanged payload to identify the exact refusing clause;
3. if no rejected payload or clause detail survived, report the named disposition **`diagnostic_payload_unavailable`** and cite the source path showing where detail is erased; do not reconstruct it; and
4. prove the terminal report, stdout receipt, registered inputs, and relevant code hashes unchanged before/after.

Explicitly unauthorized now: `scripts/run_qb1_study.py`; top-level composition; folds/model fit/inference/comparisons; reading or publishing registered comparison values; any repair; product-code or test write; input mutation; provider fetch; implementation round; rerun; commit; or push. Any accidental registered output is discarded unread.

Route the diagnostic evidence to Codex for a registration read. Only a separate revision-guarded transition after that read may open a bounded implementation round. David's future-rerun word remains held behind Codex's independent explicit CLEAR. H2 QB rushing remains **UNDER TEST with no result**.

PLEASE REPLY with: (a) ACK revision 119 and run only the diagnostic boundary above, OR (b) name a durable-state, authority, or feasibility mismatch.
