# F1 surface-parity captures — seed-fallback (degraded) state
Captured 2026-07-15 ~18:45 ET from worktree feat/f1-league-capture (uncommitted GREEN),
uvicorn on :8471, frontend dist built in-worktree, real API payloads via the NEW loader
(no runtime marker present -> committed-seed rung, the exact degraded state the contract defines).
20 captures: {league-pulse, roster-audit, trade-lab, what-changed, roster-capacity} x
{desktop, desktop-midscroll, mobile(iPhone13), mobile-midscroll}.
Eye-read notes (Claude): league-pulse desktop+mobile render real seed artifacts (team_posture.v1,
team_value_matrix.v1) w/ honest EXPERIMENTAL/descriptive-only framing, mobile nav stacks clean,
no horizontal overflow. roster-audit shows its honest "Roster not configured" state — ENVIRONMENTAL
(LEAGUE_ID_ENV unset in the test boot, roster_auditor.py:380; not a regression — path untouched
by this change); re-capture with env at the supervised run.
NOMINAL-state captures (marker-pinned runtime run) REQUIRE the David-gated supervised real
capture run and are the second half of this parity bundle.
