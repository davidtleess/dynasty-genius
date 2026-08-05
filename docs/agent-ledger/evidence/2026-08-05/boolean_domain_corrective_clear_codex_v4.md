# FTN Boolean-domain narrow corrective — Codex v4

Date: 2026-08-05

Immutable target: `28a6193960a3a2e6505693254cbdee27795c2ee1`

Disposition: **CLEAR**

The stream-5 hold imposed by the preceding corrective review is released.

## Independent verification

- `git show` confirms the production change is exactly the requested narrowing: the accepted
  SQLite/export spellings and replacement map are now `{"0", "1"}` only.
- The refusal falsifier now includes source strings `"True"` and `"False"`; the genuine-Python-
  boolean positive control remains.
- The four focused stream/corrective modules passed **88/88** independently.
- Targeted Ruff passed. `git show --check 28a6193` is clean.
- The live product DB was queried across **all 15 declared FTN Boolean columns**, not only
  `is_motion`. Every non-null stored value is exactly SQLite TEXT `'0'` or `'1'`; the only nullable
  column, `is_trick_play`, carries 13 genuine nulls. The out-of-domain set is empty.
- The stale depth-chart grain-enforcement comment was corrected and the duplicate range is now
  accurately labeled as a sample.

## Live-capture disposition

A network/live recapture is **not required before CLEAR**. This patch changes no loader,
normalization, grain, stored row, coverage counter, identity contract, or schema. It only narrows
the export refusal domain, and every value already present in the complete 185,215-row live FTN
table was independently shown to satisfy that domain across every Boolean column. Re-fetching the
same upstream data would not test a boundary left unverified here.

The last-good product export remains the previously verified run
`nflverse-usage-20260805T1334216901700000`; no product data was changed during this review.
