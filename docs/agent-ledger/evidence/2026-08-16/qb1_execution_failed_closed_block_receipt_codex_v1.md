# QB-1 first execution failed-closed — block receipt

Date: 2026-08-16 08:51 EDT

- Run: `f8f7551c-a145-46e2-b9b4-dec427f313ba`
- Durable revision: **76**
- Phase / terminal state: `blocked` / `BLOCKED`
- Round-12 review remained CLEAR; the later real-surface execution check is
  FAILED.
- Atomic terminal artifact:
  `app/data/backtest/qb_validation/qb_validation_report.json`
- Artifact SHA-256:
  `fb222a60957e2ae4a353ed730ff5ddccdfac5cb9bbc803cdc2cefe6c62306244`
- Artifact status: `run_status=failed`, `failure_reason=label_row_invalid`,
  `decision_supported=false`; no metric blocks and no result.
- Independently reproduced exact refusal: weekly row 1026 has
  `player_id=nan`, season 2015, week 1.
- Independently reproduced census: **236 / 199,868** admitted weekly rows are
  provider team-aggregate sentinels (`player_id` null,
  `player_name="Team"`, position null), 21–22 per season, 2015–2025.
- Registration classification: **implementation, not amendment**, only when
  the exact sentinel is classified at the label-builder input boundary. The
  pinned pool remains intact for the registered all-position, pre-QB-filter
  team aggregation; every other unusable identity remains fail-closed.
- Classification evidence:
  `qb1_team_aggregate_registration_read_codex_v1.md`, SHA-256
  `cb64ddf51e0e662dd776c6fd8cfd09a0a2aff67be1f90ab3f1c82928c2324425`.
- No code fix, input mutation, provider fetch, registered-value change,
  commit, push, or rerun.
- Parked for two separate David words: (1) bounded implementation round under
  the pinned boundary; (2) rerun authority after independent CLEAR.
- H2 QB rushing remains **UNDER TEST with no result**.
