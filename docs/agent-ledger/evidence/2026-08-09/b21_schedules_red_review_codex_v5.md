# B21 schedules RED v5 — independent review

Date: 2026-08-09 ET
Reviewer: Codex, independent source-integrity lane
Layer: 1 — ingestion
Reviewed pin: `ba5aeaf308ffd8b73dc010ac1e3cddfb1ac924470db3917efef8b5a21c338be6`
Verdict: **NOT CLEAR — one newly evidenced source-time contract defect**

## Independent gates

- Recomputed SHA-256: exact match, `ba5aeaf308ffd8b73dc010ac1e3cddfb1ac924470db3917efef8b5a21c338be6`.
- File length: 988 lines.
- Focused pytest: **52 failed / 1 disclosed pass**, true exit 1, zero setup/collection errors.
- Ruff: clean.
- Full read of the v5 disposition and focused read of every changed contract region.

The requested v4 residual is repaired: G8 now covers both team sides and empty/null `game_id`; G9
covers both `gameday` and `gametime`, both tables have in-test positive controls, and the fixture no
longer invents a full ISO datetime for the provider's time-of-day field.

## Finding — real `gametime` domain is now held, and v5 does not contract it

Claude explicitly requested held evidence of the real lexical shape. It is available from the
provider's primary upstream repository and documentation:

- GitHub API resolved the immutable `nfldata/data/games.csv` revision to commit
  `793d10a99154e8e21240ef03554a0366f98dbe21`, committed `2026-08-08T22:35:12Z` (`Automated data
  update`).
- Temporary review copy: 2,175,368 bytes, SHA-256
  `5486814f531cafc28e12c8b85f798f5dbc4dc19cb58cf318753a3c8ccccaf0a9`.
- Measured with Python `csv.DictReader`: **7,548 rows / 46 columns**.
- `gametime`: **259 empty values**, **7,289 non-empty values**, and **7,289 / 7,289** non-empty
  values match strict 24-hour `HH:MM`; zero non-empty values use any other lexical form.
- 2026 subset in that source revision: **272 rows**, zero empty `gametime`, all non-empty values
  `HH:MM`.
- The official `load_schedules` reference, updated from data at `2026-08-05 18:34:51 UTC`, likewise
  reports a 46-column frame with `gametime <chr>` examples `20:20` and `13:00`:
  <https://nflreadr.nflverse.com/reference/load_schedules.html>.
- Immutable source:
  <https://github.com/nflverse/nfldata/blob/793d10a99154e8e21240ef03554a0366f98dbe21/data/games.csv>.

This creates two concrete holes in G9:

1. **Provider nulls are unproved as valid.** The capture is global, so the 259 historical empty
   `gametime` values arrive in the first offering even though 2026 itself is populated. A GREEN that
   rejects every null/empty `gametime` passes v5 and fails the first real capture. Add an in-test
   positive control proving a null value in a String column is accepted and retained losslessly.
2. **The non-null domain is measured, so the ISO escape hatch is no longer honest uncertainty.** A
   GREEN that accepts an ISO datetime in this separate time-of-day column passes v5 and silently
   accepts a provider semantic drift not present in any of 7,289 held non-null values. Pin current
   non-null values to valid `HH:MM` (or cite contrary provider evidence); keep impossible/unparseable
   mutants and the positive control.

This is one source-time contract class, not a new review round over previously available facts: the
defect became demonstrable only because v5 asked for and triggered primary-source measurement.

## Required disposition

Return one revised RED pin that:

- accepts and losslessly retains provider-null `gametime`;
- accepts a valid non-null `HH:MM` value;
- rejects malformed or impossible non-null values under `source_time_invalid`;
- removes the unmeasured ISO-datetime alternative unless contrary primary provider evidence is
  cited; and
- preserves the existing v5 repairs, focused RED state, Ruff cleanliness and zero collection
  errors.

The current user instruction remains the active authority for the first B21 capture and the later
configured paid CFBD calls. No live release-asset capture, scheduler mutation, provider contact,
commit or push occurred in this review.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
