# Context-clear handoff — Codex — 2026-08-17

## Resume here

The active thread is the Footballguys first-capture CI repair.

- Pushed head: `d39ff341678a904a1eeac07f263610843f1346f5` (`HEAD == origin/main`).
- Current exact-head CI: run `32073785133` completed **failure**. Frontend passed; Python has exactly one failure: the committed manifest says `objects.required=true`, while the committed Phase A contract still expects `False`.
- Staged, uncommitted remediation: `tests/contract/test_footballguys_phase_a_red.py`, 1 file +13/-13, SHA-256 `36de40c39eaec52a772d975ba98c61f0a4276c851d8c27da486342610a833789`.
- Independent Codex verdict: **CLEAR**. Review artifact: `docs/agent-ledger/evidence/2026-08-17/fbg_cap_f1_remediation_review_codex_v1.md`, final formatting-clean SHA-256 `2dd9105c1b0d6155bce122c3e7f45a4ac924068d6e93ccde9fe09268476bf9d3`. The earlier `993df7a6...` wire pin is the pre-format version; delivered wire files remain byte-verbatim.
- Fresh proof: exact Phase A + anti-rot **665 passed**; focused anti-rot **5 passed**; scoped Ruff and diff-check clean; direct helper probe passed for both current required and historical optional epochs.

## What the two edits do

1. Make `MANIFEST_REQUIREMENTS` match the post-capture repository truth: the retained paid-byte objects store is required backup coverage.
2. Invert the test-helper epoch override so its default is the current post-capture state, while the named S23 historical negative alone forces the objects row optional and still proves raw publication refuses.

No intake was re-fired. No valid capture was removed. Store hashes remain receipts `54522831...`, semantics `f555aef7...`, and one retained object `d8af0985...`; observations remain absent.

## Exact next gates

1. **Before David commits:** restage `docs/agent-ledger/evidence/2026-08-17/fbg_cap_f1_remediation_review_codex_v1.md` and `docs/agent-ledger/2026-08-17.md`. The final index sweep found Markdown-only trailing whitespace in the already-staged review artifact; the worktree now holds the formatting-clean artifact at `2dd9105c...` and the corrected ledger pin, while the index may still hold the earlier `993df7a6...` bytes. Do not commit the stale index version.
2. David commits the reviewed test delta plus its state/evidence record.
3. David pushes the new head.
4. Exact-head CI must pass.
5. Codex performs the post-commit zero-divergence audit against test-file SHA-256 `36de40c3...`.
6. Footballguys horizon adjudication remains a separate David gate and is not opened by this repair.

## Other durable state

- The realized-outcome unattended resolver is intentionally left to fail on undeclared 2025/22 until nflreadpy rollover, per David's ruling; no fix thread is open.
- The roster-capacity and league-opportunity weekly LaunchAgents are installed and loaded; their latest artifacts were refreshed and remain descriptive (`decision_supported=false`).
- The historical `65b8696` divergence audit is CLEAR.
- A pre-existing `caffeinate -dims` process, PID 5914, is active and keeps the machine awake. This session did not create it and must not stop it.
- The standing Studio wall remains absolute: do not inspect or touch the Studio working directory.
- No dg-autonomy run is active.
- The repository contains unrelated parked dirty paths. Preserve them; do not infer they belong to this repair.

## Wire status

The CLEAR message file is `docs/agent-ledger/evidence/2026-08-17/fbg_cap_f1_remediation_clear_wire_codex_v1.md`. The governed sender initially returned `wire_body_mismatch`; the message appeared as Codex's own collapsed paste in Claude's input, and the one permitted submit retry initially appeared not to clear it. No further keypress was made. Claude subsequently recorded ACK (a) in the shared ledger, added `fbg_cap_f1_clear_ack_wire_claude_v1.md`, and staged the repair set, which is positive semantic receipt. The board, ledger, and review artifacts are the durable delivery channel.

A later short formatting-correction awareness message also hit `wire_body_mismatch`; its collapsed paste remains in Claude's input after the one permitted submit retry. No further keypress was made. The correction is durable in this handoff and `fbg_review_format_correction_wire_codex_v1.md`.

## Status vocabulary

Safe to clear conversation context: **yes**. Repository/session status: **parked at the human commit/push gate**, not clean and not technically closed until the repair lands, CI passes, and the post-commit audit is CLEAR.
