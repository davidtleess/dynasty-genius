# Codex closeout parked inventory — 2026-08-09

Layer: 1 — source integrity, capture review, and evidence durability  
Owner: Codex unless explicitly stated otherwise  
Purpose: exact expected remaining working-tree inventory after the Codex evidence closeout commit  
Status: **parked, not abandoned**

This artifact does not claim a timeless dirty count. It records the exact paths intentionally
excluded from the closeout commit. The resulting commit is verified against this list after commit.

## Frozen on David's word — 2 paths

State: tracked and modified; preserve byte-for-byte.  
Next gate: a new David word and a technical CLEAR that does not currently exist.

- `scripts/dg_delivery.py` — SHA-256
  `b3247ec8bfff67aace2f6089d08d377ee9d5f72b13eb3da79640f96dcf012c3b`
- `tests/contract/test_wire_health_profile_refresh_red.py` — SHA-256
  `fd924eb15a77746e810ade0ed7f1158cfcf9fb4000a73a3df29c260515790591`

## Scheduler definitions — 2 paths

State: untracked and uninstalled.  
Owner / next gate: David; scheduler installation and landing decision.

- `ops/launchd/com.davidleess.dynasty-league-transaction-capture.plist`
- `ops/launchd/com.davidleess.dynasty-nflverse-usage-capture.plist`

## Governed-cadence RED — 1 path

State: untracked; intentionally failing 15 contracts because its GREEN does not exist.  
Next gate: fresh implementation ticket; do not commit the RED alone because it turns CI red.

- `tests/contract/test_governed_cadence_inputs_red.py`

## Uncited Codex evidence — 36 paths

State: untracked, preserved, and not required to resolve any committed citation after this closeout
lands the seven binding evidence files.  
Next gate: a future evidence-retention/cleanup ticket. Do not infer deletion authority from the fact
that these are uncited.

- `docs/agent-ledger/evidence/2026-08-08/b21_schedules_red_review_codex_wire_v2.md`
- `docs/agent-ledger/evidence/2026-08-08/b21_schedules_red_review_codex_wire_v3.md`
- `docs/agent-ledger/evidence/2026-08-08/b21_schedules_red_review_codex_wire_v4.md`
- `docs/agent-ledger/evidence/2026-08-08/manual_feed_audit_hold_codex_v1.md`
- `docs/agent-ledger/evidence/2026-08-08/manual_feed_cadence_green_clear_codex_wire_v1.md`
- `docs/agent-ledger/evidence/2026-08-08/manual_feed_cadence_green_review_codex_wire_v1.md`
- `docs/agent-ledger/evidence/2026-08-08/manual_feed_cadence_green_review_codex_wire_v2.md`
- `docs/agent-ledger/evidence/2026-08-08/manual_feed_cadence_landing_word_codex_wire_v1.md`
- `docs/agent-ledger/evidence/2026-08-08/manual_feed_cadence_post_push_audit_codex_wire_v1.md`
- `docs/agent-ledger/evidence/2026-08-08/manual_feed_cadence_red_clear_codex_wire_v1.md`
- `docs/agent-ledger/evidence/2026-08-08/manual_feed_cadence_red_review_codex_wire_v1.md`
- `docs/agent-ledger/evidence/2026-08-08/manual_feed_cadence_red_review_codex_wire_v2.md`
- `docs/agent-ledger/evidence/2026-08-08/manual_feed_cadence_red_review_codex_wire_v3.md`
- `docs/agent-ledger/evidence/2026-08-08/manual_feed_cadence_red_review_codex_wire_v4.md`
- `docs/agent-ledger/evidence/2026-08-08/manual_feed_cadence_s8_conflict_ruling_codex_wire_v1.md`
- `docs/agent-ledger/evidence/2026-08-08/manual_feed_consumption_authority_clarification_codex_wire_v1.md`
- `docs/agent-ledger/evidence/2026-08-08/manual_feed_refresh_alignment_ping_codex_v1.md`
- `docs/agent-ledger/evidence/2026-08-08/manual_feed_refresh_alignment_request_codex_short_v1.md`
- `docs/agent-ledger/evidence/2026-08-08/manual_feed_refresh_alignment_request_codex_v1.md`
- `docs/agent-ledger/evidence/2026-08-08/manual_feed_refresh_alignment_request_codex_wire_v1.md`
- `docs/agent-ledger/evidence/2026-08-08/manual_feed_unique_datapoint_refresh_audit_codex_v1.artifact.json`
- `docs/agent-ledger/evidence/2026-08-08/manual_feed_unique_datapoint_refresh_audit_codex_v1.html`
- `docs/agent-ledger/evidence/2026-08-08/manual_feed_unique_datapoint_refresh_audit_codex_v1.html.tmp-23347-8a26a51f-2b97-447f-a8d4-73d4f1798da0.verification-failure.png`
- `docs/agent-ledger/evidence/2026-08-08/manual_feed_unique_datapoint_refresh_audit_codex_v1.html.tmp-24881-2c59fdc9-507c-4b8d-a5a8-cc3e8845e3f7.verification-failure.png`
- `docs/agent-ledger/evidence/2026-08-08/pff_grade_contract_ping_codex_v1.md`
- `docs/agent-ledger/evidence/2026-08-08/pff_grade_contract_reply_codex_v1.md`
- `docs/agent-ledger/evidence/2026-08-09/b21_schedules_green_review_codex_wire_v1.md`
- `docs/agent-ledger/evidence/2026-08-09/b21_schedules_green_v5_behavioral_clear_codex_wire_v1.md`
- `docs/agent-ledger/evidence/2026-08-09/b21_schedules_red_clear_codex_wire_v1.md`
- `docs/agent-ledger/evidence/2026-08-09/b21_schedules_red_review_codex_wire_v5.md`
- `docs/agent-ledger/evidence/2026-08-09/b21_schedules_red_v10_review_codex_wire_v1.md`
- `docs/agent-ledger/evidence/2026-08-09/b21_schedules_red_v10_review_codex_wire_v2.md`
- `docs/agent-ledger/evidence/2026-08-09/b21_schedules_red_v11_review_codex_wire_v1.md`
- `docs/agent-ledger/evidence/2026-08-09/b21_schedules_red_v12_clear_codex_wire_v1.md`
- `docs/agent-ledger/evidence/2026-08-09/cfbd_vintage_storage_finding_disposition_codex_wire_v1.md`
- `docs/agent-ledger/evidence/2026-08-09/claude_close_cross_lane_audit_codex_wire_v1.md`

## Expected resulting state

After the closeout commit lands its explicitly staged evidence and state records, the working tree
should contain exactly the 41 paths above: 2 frozen + 2 plists + 1 cadence RED + 36 uncited Codex
evidence paths. A different count or membership requires correction before the lane reports closed.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
