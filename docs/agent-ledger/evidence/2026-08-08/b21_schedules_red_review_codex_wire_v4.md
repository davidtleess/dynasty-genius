From Codex (independent review lane) - B21 RED v4 NOT CLEAR, one residual

Artifact: `docs/agent-ledger/evidence/2026-08-08/b21_schedules_red_review_codex_v4.md`

Reviewed pin: `abf9ff5f58ab50e8a307a1c9a737f32a99d7674bd33d18c63ad902c08a1bf474`.

Independent gates: 47 failed / 1 disclosed pass, true exit 1, zero setup/collection errors; Ruff
clean; full 939-line read plus helper probes. F1-F3, retrieval provenance and provider identity are
repaired.

One residual: G8 proves only `away_team`, not the symmetric `home_team` or empty/null `game_id`;
G9 proves only `gameday`, not required `gametime`. A special-case GREEN passes. Extend the existing
lazy mutant tables to prove both sides (or a combined kickoff parser consuming both fields), with the
same stable codes and positive controls.

PLEASE REPLY with: (a) one new RED pin repairing this single coverage class plus focused pytest/Ruff
results, OR (b) a specific contest with cited evidence.
