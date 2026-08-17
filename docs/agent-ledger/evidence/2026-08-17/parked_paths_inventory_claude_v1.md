# Parked working-tree inventory — 2026-08-17, Claude (write lane), v1

Measured by `git status --porcelain` at 14:0x ET, HEAD `6fbe161`. **45 paths total** =
**4 flush-set paths** (landing in the corrected state-doc flush) + **41 pre-existing parked paths**
(the closeout-gate baseline; **`.tracked_evidence_list.txt` is INSIDE the 41**, per Codex audit
blocker C2 — the earlier "41 + scratch file" phrasing double-counted it and is superseded).
Thread attributions are read from the current `AGENT_SYNC.md` board and the cited ledgers; each
row names its park location (all are this worktree, path below) and next gate.

## Flush set (staged; lands with the corrected state-doc commit — gate: David's commit keystroke)

| Path | Content |
| :-- | :-- |
| `AGENT_SYNC.md` | HND-ccf6255c handoff + flush blocks, 13:54 correction block, Codex audit verdict block |
| `docs/agent-ledger/2026-08-17.md` | 12:5x/13:2x/13:54 Claude entries + 13:54/13:59 Codex audit entries + 14:0x disposition |
| `docs/agent-ledger/evidence/2026-08-17/qb1_session_flush_notice_claude_v1.md` | delivered wire notice, kept verbatim (see C2 disposition) |
| `docs/agent-ledger/evidence/2026-08-17/qb1_closeout_and_6fbe161_audit_codex_v1.md` | Codex audit artifact, SHA-256 `dea60e36…` per its 13:59 ledger postflight |
| `docs/agent-ledger/evidence/2026-08-17/parked_paths_inventory_claude_v1.md` | this inventory (created after the 45-path measurement; lands in the same flush) |

## Pre-existing parked paths (41 — other threads, untouched by this flush)

### Capture-health / backup-health wiring thread (next gate: its own cockpit cycle CLEAR + David's commit word)

- `app/api/routes/system_capture_health.py` (modified)
- `app/api/routes/system_capture_health_models.py` (modified)
- `tests/contract/test_system_capture_health_t1.py` (modified)
- `tests/contract/test_system_capture_health_t4.py` (modified)
- `tests/contract/test_backup_health_capture_surface_red.py` (untracked RED — the 02 §Offsite-Backup ruling-3 named follow-up)
- `frontend/openapi.json`, `frontend/src/lib/api/index.ts`, `frontend/src/lib/api/types.gen.ts`, `frontend/src/lib/api/zod.gen.ts` (regenerated client, modified)
- `frontend/src/what-changed/DailyWhatChanged.test.tsx` (modified)

### Wire-health / delivery tooling thread (next gate: cockpit CLEAR + David's commit word)

- `scripts/dg_delivery.py` (modified)
- `tests/contract/test_wire_health_profile_refresh_red.py` (modified)

### Footballguys pilot thread (next gate: David's landing word for the Phase A pair RED `9e0a861f` / GREEN `a419930b`)

- `.commitmsg` (untracked — stale draft of the Phase A landing commit message)
- `docs/agent-ledger/evidence/2026-08-09/footballguys_identity_census_generator_v3.py` … `_v7.py` (5 untracked)
- `docs/agent-ledger/evidence/2026-08-11/footballguys_green_v19_real_store_probe.py` (untracked)

### Loop-control 02-amendment thread (next gate: draft amendment's cockpit CLEAR + David's word)

- `docs/agent-ledger/evidence/2026-08-12/loop_control_judge_increment_review_codex_v1.md`, `_v2.md`
- `docs/agent-ledger/evidence/2026-08-12/loop_control_review_codex_crash_scrollback_claude_v1.txt`
- `docs/agent-ledger/evidence/2026-08-12/loop_control_review_reroute_wire_claude_v1.md`, `_v2_addendum.md`
(5 untracked)

### Realized-outcome scorer cycle thread (next gate: that thread's evidence/state-doc commit word)

- `docs/agent-ledger/evidence/2026-08-14/` — 12 untracked files: `realized_outcome_scorer_commit_17cfc1e_divergence_audit_codex_v1.md`, `realized_outcome_scorer_commit_3d9b89a_divergence_audit_codex_v1.md`, `scorer_amend_ready_wire_claude_v1.md`, `scorer_clear_qb1_framing_r2_not_clear_wire_codex_v1.md`, `scorer_clear_qb1_r2_notification_codex_v1.txt`, `scorer_clear_qb1_r2_short_wire_codex_v1.md`, `scorer_commit_3d9b89a_not_clear_awareness_codex_v1.md`, `scorer_commit_3d9b89a_not_clear_wire_codex_v1.md`, `scorer_commit_receipt_wire_claude_v1.md`, `scorer_cycle_commit_message.txt`, `scorer_cycle_commit_message_v2.txt`, `scorer_gate_blocker_wire_claude_v1.md`

### David-gated operational items

- `ops/launchd/com.davidleess.dynasty-league-transaction-capture.plist` (untracked; David-gated install/commit)
- `ops/launchd/com.davidleess.dynasty-nflverse-usage-capture.plist` (untracked; David-gated install/commit)
- `.tracked_evidence_list.txt` (untracked scratch; gate: David's pending `rm`)
- `.mcp.json` (modified tracked local MCP config; gate: David's word to commit or discard)

### Deliberately never-commit (by standing board law)

- `tests/contract/test_governed_cadence_inputs_red.py` (the standing untracked cadence RED — its failures are the deliberate signal; gate: none, stays uncommitted by design)

## Count reconciliation

4 (flush set) + 10 (capture/backup-health) + 2 (wire-health) + 7 (footballguys incl. `.commitmsg`)
+ 5 (loop-control) + 12 (scorer) + 4 (David-gated incl. `.tracked_evidence_list.txt` + `.mcp.json`)
+ 1 (never-commit) = **45** — matches the closeout gate's measured 45 exactly. The audit-time
baseline of 44 = these 45 minus the Codex audit artifact, which did not yet exist; its 41
pre-existing figure = 44 − the 3 then-staged flush paths.
