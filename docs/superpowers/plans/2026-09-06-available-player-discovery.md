# DG-178 — Available players: unowned-player discovery on the research preview (native test-first plan)

Released 2026-09-06 (David: "ok go") by `~/dg-build/AVAILABLE-PLAYERS-BUILD-2026-09-06.md`. Start `3688e542` on
`ticket/DG-178`, tree clean; accepted preview run `214512Z` stays pinned on 8787 until root authorizes a candidate pin.
Worktree `~/dg-wt/DG-178`; every command below runs from its root unless stated.

## Invariants (asserted, never assumed)

- The 825 accepted forecasts, references and annual terms are untouched: the catalog READS the accepted report
  (`runs/20260906T214512Z/dg178_audit/report.json`, sha `19e032a4…`) and the producers' frozen CSVs; it composes nothing.
- Ownership filters availability only; it never changes a forecast. Existing impact math and reference choices unchanged.
- An NFL free agent is never equated with an unowned fantasy player; an unmatched NFL identity is never "available".
- Now = 2026 projected championship-window points; Future = the named years 2027–2030 summed only when every year is
  present, else undefined (never zero, never partial). P(appears) is never relabelled. Missing / zero / negative stay distinct.
- Local-only watchlist; no network mutation, no FAAB, no drop or lineup recommendation.

## Facts checked before writing this plan

- Census 202057Z unowned members: active 242, practice squad 135, IR 56, cut 68, retired 6, unknown 3 (= 510 of 784).
  Default pool = active + practice squad + IR = **433** (349 with a research estimate, 84 without). Archive: 3,373 uncovered
  Sleeper-eligible ids; 141 NFL rows without a Sleeper identity — disclosures, never availability.
- The accepted report's `all_inspectable` rows carry sleeper_id, readiness, value and per-season margins; producer values
  come from `basic_forecasts.csv` (195728Z, sha `a43f3126…`) and `rookie_scores_2026.csv` (195904Z, sha `db96647d…`), whose
  shas the report records under `annual_producers[*].csv_sha256`.

## Tasks (red → green → refactor; exact commands)

### T1 — `src/dynasty_genius/ranking/available_catalog.py` (new) + `tests/ranking/test_available_catalog.py` (new)

`AvailableCatalog.build(report_path, census_dir, producer_csvs, *, snapshot_path)`:
- re-hashes the report and requires its `provenance`/`current_census.census_csv_sha256` to match the census dir it binds
  (same bytes as the audit); the census is loaded through `CensusBinding` (ownership reconciled against the snapshot);
- population = census members NOT owned; default pool = classes {active, practice_squad, injured_reserve}; `cut`,
  `retired`, `unknown` are separate inspectable populations; archive counts (uncovered ids, unmatched NFL rows) are
  disclosures with their dated sources;
- each row joins its forecast by verified identity (Sleeper id → the report row → producer row by gsis / (draft_season,
  pick)); values are the PRODUCER's `e_points_year{j}`, `p_appear_year{j}`, `e_points_year{j}_given_appear`,
  `e_games_year{j}` for j = 1..5 (2026–2030) read from the CSV whose sha the report records (refused on sha / arm /
  forecast-year mismatch; non-finite refused); `now_points` = 2026 `e_points`; `future_points` = Σ 2027–2030 only when all
  four are finite, else `None` with `future_reason`; the accepted impact (h2 / h5) rides along for consistency;
- a member without a verified forecast is RETAINED with a plain reason (the producer's stated reconciliation reason when
  present, else "no forecast from the selected producers; no reason stated");
- `report()` gives denominators per population × position × has-forecast, consistent with the rows.

Red: `.venv/bin/python -m pytest tests/ranking/test_available_catalog.py -q` (ImportError). Green: same; then
`.venv/bin/python -m pytest tests/ranking -q`.

### T2 — `scripts/dg178/build_available_catalog.py` (new): immutable `runs/<UTC>/dg178_available_catalog/{catalog.json, catalog.csv, report.json}`

Records provenance (git head, dirty, argv), input hashes (report, census files, producer CSVs, snapshot), denominators and
freshness dates (snapshot captured_at, roster capture Last-Modified, census run). Refuses a `latest` path.

### T3 — `app/api/routes/research_available.py` (new) + `tests/contract/test_research_available_route.py` (new)

`GET /api/research/available` serves the newest catalog whose `source_report_run` equals the served preview's run
(pinned or `?run=`), else 404 with the reason; payload: populations with counts, rows (identity, league position,
fantasy positions, NFL team/status/date, ownership as-of, forecast seasons, now/future with the named years, impact h2/h5,
missing reason), freshness caveat, disclosures. Ownership date and NFL status date named.

### T4 — frontend: `frontend/src/research/availableHelpers.ts` + `.test.ts`, `AvailablePlayers.tsx` + `.test.tsx` + `AvailablePlayers.css`; a labelled "Available players" tab in `ResearchPreview.tsx`

- Pure helpers: `filterAvailable(rows, {query, positions, statuses, watchedOnly, missingOnly})`, `sortAvailable(rows,
  basis)` with bases `now` (2026 points), `future` (2027–2030 points), `impact2`, `impact5`, `name`; exact ties broken by
  name then id and reported as tied; missing-forecast rows ordered separately (after, by name); `watchlist` storage
  (localStorage, safe parse, versioned; corrupt data → empty + a notice), `watchStatus(row, watched)` → available |
  now_owned | left_pool with explicit wording.
- Component: search input, position and NFL-status filter groups (default active + practice squad + IR), watched-only
  and missing-only toggles, a sort control with the basis stated beside it ("sorted by 2026 projected points; raw points
  are not cross-position dynasty value"), counts consistent with the visible rows, clear / no-match states, table via
  the existing `TableScroll` / `PlayerIdentity`, per-row watch toggle, a Why disclosure with the season path and the
  missing reason, freshness line (ownership as of snapshot date; NFL status as of roster capture date).
- Tab: `ResearchPreview` gains a two-tab strip (Research board | Available players) above the horizon toggle; the
  research board is unchanged when its tab is active.

Red: `cd frontend && npx vitest run src/research --reporter=dot`. Green: same; `npx tsc --noEmit`; `npx biome check
src/research`; `npx vitest run src/styles src/research`; `npm run build`.

### T5 — actual data, QA, checkpoint

1. `scripts/dg178/build_available_catalog.py --report runs/20260906T214512Z/dg178_audit/report.json --census-dir
   runs/20260906T202057Z/dg178_current_census --snapshot <league snapshot> --producer-csv <basic 195728Z>
   --producer-csv <rookie 195904Z>` → new immutable run; denominators must read 433 default (349 + 84) before any identity
   correction; cut 68 / retired 6 / unknown 3 separate; archive disclosures.
2. Restart the isolated server on HEAD with `DG178_PREVIEW_RUN=20260906T214512Z` (pin unchanged); browser QA desktop
   1280 / phone 390 incl. filters, sort, watch, Why open, no overflow (capture script inside `frontend/`).
3. Focused checks: `tests/ranking`, both route test files, vitest `src/research src/styles`, tsc, biome, full backend suite
   from the root; product-scoped diff check.
4. Commit with explicit paths; ticket entry with run id, hashes, denominators, URL; cross-review requests to lanes
   (rookie: rookie rows' now/future vs its export; veteran: veteran rows vs its export).

## Out of scope (refuse if tempted)

Changing impact math or the reference; any invented upside / breakout / momentum; a live news or transaction feed; FAAB or
lineup advice; consuming a DG-165 cold-start candidate before root accepts it; edits outside DG-178-owned files.
