From Codex (independent source-integrity lane) — B21 v6 requested gameday measurement

Same immutable upstream snapshot and parser as the v5 review (`nfldata` commit
`793d10a99154e8e21240ef03554a0366f98dbe21`, 7,548 rows):

- `gameday` empty/null at CSV boundary: **0 / 7,548**.
- strict lexical `YYYY-MM-DD`: **7,548 / 7,548**.
- other non-empty lexical forms: **0**.

Conclusion: keep `gameday` required and strict. Only `gametime` has the measured 259 unpublished
values. This closes the uncertainty named in the v6 docstring before the pin freezes.
