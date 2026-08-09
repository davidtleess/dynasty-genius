# Manual-feed cadence S8 contract-conflict ruling — Codex v1

Date: 2026-08-08
Layer: 1
Verdict: **S8e governs; repair S8b**

Claude correctly identified an unsatisfiable semantic conflict:

- S8b requires a partially supplied report to contain only the supplied streams.
- S8e requires every declared stream to remain visible even when no evidence was supplied.

The input-shape-dependent behavior needed to satisfy both literally would hide precisely the unobserved streams the status contract exists to expose. That is rejected.

## Required repair

Keep every declared stream in every report. S8b should require:

1. supplied streams appear;
2. serialized stream keys equal `streams_for(source)`;
3. every declared-but-unsupplied stream serializes `cadence=undetermined` and `coverage=unknown`;
4. source rollups remain derived from all serialized streams, never from only the supplied subset.

Use a computed omitted set rather than checking roster alone, so a future declared stream cannot disappear silently.

## GREEN scope authority

The narrow `daily_control` manifest change required by S8 is part of the already-cleared GREEN and David's instruction to proceed. Claude is authorized to remove the flat `refresh_target="daily"` from manual entries and wire the new per-stream cadence/reporting contract. This does **not** authorize scheduler installation, a source capture, paid access, provider contact, or unrelated controller changes.

The pre-availability fix described by Claude is directionally correct: before provider availability, a completed game must not be reported as `current` merely because the season is active.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result and is unrelated.
