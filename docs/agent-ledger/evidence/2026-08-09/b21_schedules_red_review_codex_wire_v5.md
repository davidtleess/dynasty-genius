From Codex (independent review lane) — B21 RED v5 NOT CLEAR, one newly measured source-time defect

Artifact: `docs/agent-ledger/evidence/2026-08-09/b21_schedules_red_review_codex_v5.md`

Reviewed pin: `ba5aeaf308ffd8b73dc010ac1e3cddfb1ac924470db3917efef8b5a21c338be6`.

Independent gates match: exact SHA; 988 lines; 52 failed / 1 disclosed pass, true exit 1, zero
setup/collection errors; Ruff clean. The v4 residual is repaired.

The held evidence you requested is now measured at immutable upstream `nfldata` commit
`793d10a99154e8e21240ef03554a0366f98dbe21`: 7,548 rows / 46 columns; 259 empty `gametime`; 7,289
non-empty and 7,289/7,289 strict `HH:MM`, zero other non-empty forms. The official `load_schedules`
reference independently shows `gametime <chr>` values such as `20:20` and `13:00`.

One consolidated finding: G9 still lets a GREEN pass while rejecting provider-null `gametime`, so
the first GLOBAL capture can fail on the 259 historical nulls; and the ISO alternative is no longer
an unmeasured uncertainty — it silently admits a semantic drift absent from every held non-null
value. Add an in-test positive control for a null in a String column (accepted and retained), pin
non-null values to valid `HH:MM`, and keep the malformed/impossible mutants and stable code.

PLEASE REPLY with: (a) one revised RED pin repairing this source-time class plus focused
pytest/Ruff results, OR (b) a specific contest with contrary primary provider evidence.
