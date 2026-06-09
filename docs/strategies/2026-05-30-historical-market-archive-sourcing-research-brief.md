---
title: Research Brief — Source a Point-in-Time Historical Dynasty Superflex Market-Value Archive
audience: a web-enabled research agent (Claude with browsing) — NO repo access assumed
requested_by: David (Dynasty Genius)
date: 2026-05-30
purpose: Source the historical market data that unblocks Harness-Trust W1/G3 (model-vs-market verdict). See [[project_w1_needs_historical_fc_archive]].
---

# Research Brief: Source a Point-in-Time Historical Dynasty Superflex Market-Value Archive

## 0. Your mission (TL;DR)

Find a downloadable, **point-in-time** archive of **dynasty Superflex** fantasy-football player market values covering **four specific past dates**, so it can be loaded into a backtest that checks whether a valuation model out-ranked the market over time.

The single hardest requirement: the values must be **as they actually stood on those dates** — not today's values relabeled, not back-revised, and not survivorship-scrubbed. Report ranked, vetted sources with exact retrieval steps and a data sample. **Do not fabricate or substitute data; "not found" is a valid answer.**

## 1. Exactly what's needed

**Four target dates** — a capture within **±7 days** of each is acceptable:

- **2021-09-08**
- **2022-09-08**
- **2023-09-08**
- **2024-09-08**

**Format / market settings (must match):**
- **Dynasty** (not redraft), **Superflex / 2-QB** (`numQbs = 2`), **12-team**, **PPR** (`ppr = 1`).
- Superflex is critical — it changes QB values dramatically vs 1-QB. A 1-QB-only or redraft dataset is **not usable**.

**Preferred market source:** **FantasyCalc** values (matches the system's forward data collection, for apples-to-apples). **Acceptable alternatives** if FantasyCalc history can't be obtained — *provided they are point-in-time and clearly labeled*: **KeepTradeCut (KTC)** or **DynastyProcess** dynasty-SF values. Always state which source any data came from.

**Per-player fields wanted** (target schema — one row per player per date):

| Field | Required? | Notes |
|---|---|---|
| `sleeper_id` | Strongly preferred | Sleeper player ID. If absent, provide whatever player ID(s) the source uses (KTC id, FantasyCalc id, MFL id, gsis_id) and/or full name + position so it can be crosswalked downstream. |
| `value` | **Required** | The dynasty-SF value number as published on that date (integer). |
| `position` | **Required** | QB / RB / WR / TE. |
| `archive_publish_date` | **Required** | The date the values were actually published/captured (YYYY-MM-DD). Must fall within ±7 days of one target date. |
| `overall_rank` | Optional | Market overall rank on that date. |
| `position_rank` | Optional | |
| `updated_at` | Optional but valuable | A per-row "last updated" timestamp if the source has one — used to detect post-hoc revision (any `updated_at` later than the publish date = revised = rejected). |

One file per date, or one combined file with `archive_publish_date` per row. Note: only the *internal ranking* within each date's snapshot matters for the analysis, so the absolute value scale need not match across sources or dates — but using one consistent source/methodology across all four dates is cleanest.

## 2. The non-negotiable: point-in-time integrity

This is make-or-break. The data judges whether a model beat the market *historically*; if the "history" is actually today's values relabeled, the verdict is worthless and actively misleading. Apply these tests to every candidate source:

1. **As-published, not recomputed.** Values must be what the market showed on/around the date — not a current snapshot with an old date stamped on it.
2. **No survivorship bias — THE key test.** Players valued on that date who have since retired, been cut, or left the league **must still appear at their then-current value.** Concretely: a genuine 2021-09-08 dynasty snapshot should still contain players relevant in 2021 who are now gone. If the dataset lists only currently-active players, it has been survivorship-scrubbed → **reject it.**
3. **Verifiable capture timestamp.** Prefer intrinsic, trustworthy dating — a git commit date, an archived-page capture date, a dated file — over a hand-typed date.
4. **No live / "current" endpoints.** An API that returns only *today's* values cannot supply history, however it's queried. Do not reconstruct history from a current endpoint.

## 3. Candidate sources to investigate (leads — verify, don't assume)

Ranked by likely point-in-time soundness. Report what you actually find for each.

1. **DynastyProcess open data — highest priority.** A public GitHub data repo (search `github.com/dynastyprocess/data`) historically publishes player value CSVs. Its **git commit history** may yield genuine dated snapshots — checking out the commit nearest each target date could give true point-in-time values. Investigate: does it cover dynasty **Superflex**? Include `sleeper_id` (or a crosswalk)? Do commits exist near the four dates? Does old history retain since-departed players (survivorship test)?
2. **nflverse / community dynasty-value datasets on GitHub.** Search for repos snapshotting KTC / FantasyCalc / dynasty values over time via dated files or git history. Same checks.
3. **FantasyCalc directly.** Their public API (`/values/current`) is current-only. Investigate whether they offer **historical** values via a documented endpoint, a paid tier, a data export, or on request to the maintainer. If yes, capture the four dates in SF dynasty.
4. **KeepTradeCut historical.** KTC publishes dynasty SF values; investigate community CSV exports / archives that captured KTC SF values over time (dynasty forums, Discords, GitHub). Confirm SF + dating.
5. **Internet Archive / Wayback Machine — fallback.** Captures of `fantasycalc.com` or `keeptradecut.com` on/near the four dates. Fragile and partial, but may recover a date or two; extract values from the captured page and confirm the capture date.
6. **Dynasty community (r/DynastyFF, dynasty Discords, hobbyist archivists).** People sometimes archive value history; a pointer to such a dataset (integrity checks met) counts.

## 4. Source-validation checklist (apply to each candidate)

- [ ] Covers dynasty **Superflex / 2QB** (not 1-QB, not redraft).
- [ ] Has data within **±7 days** of at least one target date.
- [ ] Passes the **survivorship test** (since-departed players still present at historical value).
- [ ] Dating is **intrinsic / verifiable** (git date, capture date, publish date) — not merely asserted.
- [ ] Player keying is `sleeper_id` or crosswalkable (name + position at minimum).
- [ ] **Licensing / redistribution** terms noted. (Data will be used locally and not redistributed; flag if a source forbids even that.)

## 5. What to report back

1. **Ranked shortlist of viable sources.** For each: URL / access method, which of the four dates it covers, SF-dynasty?, key format (sleeper_id?), the integrity assessment **with evidence** (especially the survivorship test), and a licensing note.
2. **For the top source(s): exact retrieval steps** — e.g., "clone repo X; `git checkout` the commit dated nearest 2021-09-08; file `values.csv` has columns […]."
3. **A small data sample** (5–10 rows) from the best candidate per date, to confirm the schema, the SF-dynasty nature, and the presence of since-departed players.
4. **Coverage map:** which of the four dates are obtainable and which are not.
5. **Honest gaps and risks.** It is fully acceptable to conclude a date is **not recoverable** — partial coverage is fine (uncovered dates are simply skipped in the backtest). Say so plainly rather than forcing a weak source.

## 6. Explicit non-goals / guardrails

- **Do not fabricate, synthesize, estimate, or interpolate values.** "Not found" is a valid, useful answer.
- **Do not substitute current values** for any historical date.
- **Do not use any source that can't establish point-in-time provenance** — even if it's the only thing available. A confidently-wrong archive is worse than a missing one.
- Respect source licensing; flag redistribution limits.
- You need NOT produce the final loadable file (column-mapping / sleeper_id crosswalk happens later, locally). Your job is to **find, vet, and document** the source(s), how to retrieve them, and a sample.

## 7. Why the bar is this high (context, optional)

This archive feeds a "does our model beat the market?" backtest for a dynasty fantasy valuation system. The whole point is an honest verdict. A revised or survivorship-scrubbed "history" would make a mediocre model look prophetic (or vice versa) — the exact false-confidence failure the project exists to prevent. That's why a *missing* date is acceptable but a *wrong* one is not.
