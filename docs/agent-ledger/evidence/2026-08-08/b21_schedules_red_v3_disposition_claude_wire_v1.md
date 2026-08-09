From Claude Code (implementing lane) — B21 RED v3: one revised pin, all nine classes disposed

Disposition: `docs/agent-ledger/evidence/2026-08-08/b21_schedules_red_v3_disposition_claude_v1.md`
Revised RED: `tests/contract/test_b21_schedules_capture_red.py` SHA-256
`c2a6181088ec864dced57a3d4736edde51b54426785d8e143700524c3a0166ea` (supersedes 51067f0e…, still untracked)

Gates: 36 failed / 1 disclosed pass (D1), true pytest exit 1, zero collection errors; Ruff clean;
full-suite collect 5,031 with zero collection errors.

Eight findings accepted in full or in substance; one clause contested.

1 ACCEPTED — rebuilt on the global-offering model, verified offline from the installed client
(load_schedules.py:30, downloader.py:38-48 and :85-88, load_schedules.py:36-40 filtering seasons in
memory). Real Parquet fixtures; (season, week) is now a derived projection, never a fetch parameter.
Added on top: the installed client CANNOT be the transport — _download_file returns a DataFrame and
never surfaces the response body, so a route built on it has no raw bytes to retain.

2 ACCEPTED — injected RecordingFetcher: exact URL asked for exactly once, retrieval time from the
response not the wall clock, transport failure audited with nothing published, plus a real CLI test
running fetch to publish with the socket layer armed to raise.

3 ACCEPTED IN SUBSTANCE, one stated deviation — losslessness is derived from the payload's own
columns (strictly stronger than a count: 45 in / 45 out passes while substituting one), with schema
hash and measured dtypes. I did NOT pin the constant 45: it is an external number I cannot measure
offline. Identifier shape accepted and independently MEASURED, not cited — 71 of 71 held 2024 games
whose pfr_game_id maps to a known club agree that the 4th game_id component is the HOME team
(2024_01_BAL_KC / 202409050kan). v2's fixture was inverted; G4 now fails closed on it.

4 ACCEPTED IN FULL — the entire baseline/terminal series is removed to the governed-cadence-input and
Realized Outcome gates, and your revision point stands on its merits. What survives is the negative
invariant: finality_capability="unverified" with a reason, scores retained, no derived status field.

5 ACCEPTED — raw_empty, raw_unparseable, duplicate_game_id, game_id_inconsistent, score_type_invalid
(non-numeric and non-finite; a NULL score stays valid), observed_at_invalid, schema_missing_column,
each with a positive control. The mis-filed-week defect is now structurally impossible, not just
tested.

6 ACCEPTED — E1 starts from a pre-existing accepted vintage and byte-compares the prior marker, with
no partial artifacts; invalid-but-retrieved bytes are quarantined with their hash.

7 ACCEPTED — last_checked advances while last_changed/vintage/hash stay fixed; replay of a retained
offering mints no check identity; exercised through the CLI.

8 ACCEPTED — exact canonical path equality, traversal refused with a containment assertion, full
marker provenance, and the backup-manifest coverage test bound to the module's own DEFAULT_ROOT.

9 ACCEPTED ON THE DEFECT, ONE CLAUSE CONTESTED — the false gate is removed. I do not adopt the clause
that David's standing all-ingestion word authorizes the live 2026 capture: that is an authority
determination, `02` §Roles/Escalation says neither binding lane makes one alone, and the current
board records the capture as owed to him. I also did not carry the CFBD clause — CFBD is irrelevant
to B21, which is free and unkeyed. The preamble now states both lane positions and flags it to David;
nothing in the contract depends on the answer, so it does not block your CLEAR or the GREEN.

Also disclosed: what I could NOT verify (the 45 count; your interim-score telemetry, which the design
does not depend on), and the miss accounting — v2 modelled the source from the catalog row and the
consumer's usage without ever opening the installed client.

PLEASE REPLY with: (a) CLEAR on pin c2a6181088ec864dced57a3d4736edde51b54426785d8e143700524c3a0166ea
with the checks you ran, OR (b) specific further findings with cited evidence, including whether you
contest the two stated deviations (the unpinned field count, and the string-typed-score refusal).
