# Run 20260906T214340Z — FAILED ACCEPTANCE (preserved, not a producer)

Root inspected this first actual-data run: identity resolved 0 / unmapped 314, every nonzero Sleeper observation
`unresolved:no_identity`. Cause: the identity map stores `sleeper_id` as a float column and the tool compared
`"11560.0"` with Sleeper's `"11560"`. The tool refused to claim anything, which is the designed failure mode, but the
run proves nothing about scoring. Two further defects root found in the same review are fixed after this run:
`absent_zero` was assignable to an unresolved identity at 0.0 points (1,479 here vs the true 1,233 stat absences), and
the CLI hashed each file then re-opened it for parsing. Fixed with regression tests in checkpoint after 4a357c4a;
superseded by the next `runs/<ts>/dg177_league_scoring_audit/`. The directory is immutable and stays as evidence.
