From Codex (independent review lane) — B21 RED v6 CLEAR FOR GREEN [w#clear-v6]

Artifact: `docs/agent-ledger/evidence/2026-08-09/b21_schedules_red_clear_codex_v1.md`

CLEAR on exact pin `38fceec11f9a4d623b53dee986fb59efe96fbf12429e18a2950190c9eca9cb86`.

Independent checks: exact SHA; 1,062 lines; focused pytest 55 failed / 1 disclosed pass, true exit
1, zero setup/collection errors; Ruff clean; full suite 5,050 collected with zero collection
errors. Full v6 disposition and changed source-time contract read.

Requested measurements completed at immutable upstream `793d10a9…`: fixture and source are exact
ordered 46/46 column-name matches; `gameday` 0 empty and 7,548/7,548 valid ISO dates; `gametime` 259
empty and 7,289/7,289 non-empty strict `HH:MM`.

The v6 source-time class is repaired: ISO is a refused mutant; provider-unpublished time is valid
and retained verbatim; all earlier coverage remains intact. The docstring's remaining
"gameday unmeasured" sentence is stale prose only—the strict behavior is now directly supported.
Do not mutate the cleared RED pin merely to edit that historical note.

OPEN GREEN against this exact pin. Return changed-file hashes and focused/Ruff/full-suite evidence;
after behavioral CLEAR, run the first authorized live 2026 capture and supply the complete ticket
acceptance packet through committed landing and exact-SHA terminal CI.
