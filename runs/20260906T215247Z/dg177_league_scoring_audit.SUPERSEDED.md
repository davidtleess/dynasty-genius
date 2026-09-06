# Run 20260906T215247Z — SUPERSEDED (preserved, not the producer)

Root's final acceptance and the independent reviewer found disclosure and accounting defects that this run carries:
`quarantine_reaudit.csv` called unknown special-teams splits "nonzero" (36 claimed vs 6 known nonzero + 30 unknown) and
overwrote original missing values with 0 in the output; recovery sides were compared as a sum; a null player id was
counted through a status that an ambiguity could overwrite; attributed events with no weekly row were absent from the
unattributed ledger. The successor run (next `runs/<ts>/dg177_league_scoring_audit/`) corrects all of it; the main
Sleeper reconciliation was sound and its counts are re-derived there. Directory immutable, kept as evidence.
