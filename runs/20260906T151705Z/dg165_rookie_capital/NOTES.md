# DG-165 — notes on the corrected candidate (prose; every statistic lives in REPORT.md / EVALUATION.md)

This run answers the round-1 review (REVIEW-2026-09-06-ROUND1.md, lane 24974) item by item. It is a
research candidate: not served, not promoted, not merged; nothing under `app/data` was written.

## What changed since the reviewed tip `9a6a7a4b`

**Identity, not inference (review item 2).** The previous build called 107 prospects "washouts" because
PFR's career-games field was empty and the code filled the blank with zero. The field is a missing record.
Every pick without an NFL id is now resolved through independent sources in a fixed order — the nflverse
players table by draft year and pick, then by name and year, then the 1999–2025 rosters by entry year and
draft number, then by name and year. A resolved identity with no weekly stat row scored zero fantasy points,
which is a measured fact and labels zero. A prospect no source can identify is kept in the cohort with
`label_basis = unresolved`, carries NaN in every label, is counted in the coverage report, and is never
asserted to have failed. The zero treatment survives only as a named sensitivity arm, run and reported
beside the default; the counts and the movement it causes are in REPORT.md.

**One procedure (item 1).** The historical evaluation now calls the same function as final scoring:
one fit per forecast year on the classes before it, labelled with only the seasons complete by then. Each
family inside the model selects its own observable, at-risk rows the same way whether the forecast year
is 2007 or 2026. Every exported column — each per-season probability, each conditional and unconditional
level, each cumulative quantity — is graded against its own label in `out_of_time_predictions.csv` and
summarised in `evaluation.json`. A test proves the evaluation's forecast for a year equals a fresh fit for it.

**Coherent nested events (item 3).** Cumulative probabilities are no longer separate fits. First-appearance
and first-qualification hazards, with re-appearance and re-qualification rates, generate every per-season
and cumulative probability by arithmetic, so "any appearance by h" cannot fall as h grows, a season's
probability cannot exceed the cumulative probability through that season, and the expected number of
qualifying seasons is bounded below by the probability of at least one. The scored file satisfies all of
these on every row, and a test pins them.

**Training baselines (item 4).** The comparator for every quantity is the training set's prevalence or
mean at that forecast year, carried per row and pooled from the rows — never pooled test prevalence. The
per-year baselines are listed in EVALUATION.md. REPORT.md is rendered from the JSON by code; nothing in it
is typed by hand, which is how the earlier report came to quote prevalences its own JSON contradicted.

**Composition claims withdrawn (item 5).** The manifest no longer says how anything here composes with
Engine A, Engine B or the DG-164 cells. Qualifying by season total is not contributing useful weeks, and
Engine A's eight-game condition is not appearance. Instead the file carries the annual target agreed with
the ranking lane (DG-178): the appearance event, the season total and games conditional on appearing, and
the unconditional pair formed only because points and games are exactly zero without an appearance —
nonqualifier weeks are inside it, and nothing is forced to zero. Qualification probabilities and the
conditional rate given qualification remain as descriptive forecasts in their own right.

## The bounded trend experiment

Rookie-year production has risen across draft classes and a model fitted only on the past lags it. The
experiment adds one linear class-year term to every family and lets each training window decide whether
to keep it by validating on its own three most recent complete classes — nothing at or after the forecast
year is read, and a test pins that. Both arms were then graded out of time with the same procedure. The
trend arm improved a majority of the compared metrics, most at the rookie season and least at season three,
and the training windows selected it consistently from the mid-2010s onward. By the rule stated in advance
it replaces the plain model for scoring; the plain arm is fully reported in `trend_experiment.json` so a
reviewer can reverse that choice without a rerun. The gain is real but small, and it is a one-year
extrapolation of a linear term — the kind of correction to re-check each season, not a discovery.

## Why this run replaces 144444Z

The previous run wrote the plain arm's evaluation and predictions before the trend experiment decided, and
then scored the class with the trend model — the integration lane graded the wrong arm. Here the experiment
runs both arms with the one procedure and the arm the pre-stated rule selects supplies `evaluation.json` and
`out_of_time_predictions.csv`; the other arm sits beside them as `evaluation_other_arm_plain.json` and
`out_of_time_predictions_plain.csv`. The scored class is unchanged. One residual to carry: after the trend
term the season-one points bias is small overall but remains clearly negative for quarterbacks, which the
by-position table in EVALUATION.md shows and no further term was added to chase.

## What this run does not do

- It does not model undrafted rookies; there is no defensible population table, and the ranking lane
  measured that none is rostered anywhere in the league today.
- It does not say what a rookie is worth. Replacement level, lineup policy and the discount are the
  ranking lane's typed contract, and the unit mismatch between this file's stat-row denominator and the
  served all-games rate is stated on the manifest for that lane to reconcile.
- It does not resolve the young-QB/TE cell gap for non-rookies (Jaxson Dart); that stays a DG-176 question.
- It does not claim a trading edge. Nothing here has graded a decision against a market outcome.

## Where to look

REPORT.md (rendered record) · EVALUATION.md (every quantity, slice, calibration, baseline, absent pair) ·
trend_experiment.json (both arms) · sensitivity_unresolved_as_zero.json · cohort.csv (every prospect with
its identity basis) · manifest.json (definitions, units, cutoffs, input hashes, git sha).
