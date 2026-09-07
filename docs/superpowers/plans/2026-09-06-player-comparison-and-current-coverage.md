# DG-178 — player comparison board and current-coverage binding (native test-first plan)

Released 2026-09-06 by `~/dg-build/PLAYER-COMPARISON-BUILD-2026-09-06.md` under the design in
`~/dg-build/NEXT-INCREMENT-PROPOSAL-2026-09-06.md`. Start `d10e8b42` on `ticket/DG-178`; default preview run
`203007Z` stays pinned until root verifies the candidate. Worktree `~/dg-wt/DG-178`; every command below runs there.

## Invariants (asserted, not assumed)

- Every one of the 825 existing estimates, every full-precision annual term, every reference identity and the
  two-/five-year prefix consistency are unchanged: the new audit is diffed against `203007Z` the way `203007Z` was diffed
  against `202257Z` (all boards' values, margins, actions, readiness, references, counts, board target, artifact identity).
- All 274 league records retained on both views. No value, reference, eligibility or placement rule changes.
- No shared writes, installs, merge, promotion, publication, production restart. New run directories only.

## Facts checked before writing this plan (run 203007Z, census 202057Z)

- The API serves all 274 league players per view; the page renders roster + top 40. 99 of 274 league values are 0.0; none
  missing on this board; 0 exact-zero season cells among 4,800 served cells.
- `margin + reference_series[j]` reproduces the producer's `e_points_year{j}` on 2,515 of 2,515 veteran cells (0 mismatches).
- Braelon Allen: 0.0 on two years (−53.61, −3.50), 48.8226 on five (+6.80, +18.02, +24.00).
- Kareem Hunt (Sleeper 4098) is NOT a census member: uncovered, "no verified join to the captured 2026 roster (Sleeper flags
  Active/- are not membership)". The page's "Active" beside him is Sleeper's flag copied onto the reference — a certainty
  error, not a reference error.
- Census coverage per position (unowned census members): QB 68 with forecast / 20 without (9 active, 4 PS, 2 IR, 4 cut,
  1 retired); RB 78 / 32; WR 154 / 55; TE 102 / 21. The page instead quotes universe counts (QB 368 …) that include
  inactive and retired Sleeper ids.

## Tasks (each: red test → green → refactor; commands exact)

### T1 — `src/dynasty_genius/ranking/current_census_binding.py` (new) + `tests/ranking/test_current_census_binding.py` (new)

`CensusBinding.load(run_dir, *, season, league_snapshot_sha256)`:
- refuses a path containing `latest` (mutable) or a run dir without `census.csv`, `uncovered.csv`, `report.json`;
- recomputes sha256 of `census.csv` and requires equality with `report.json["census_csv_sha256"]`; recomputes the
  nflverse roster, Sleeper eligibility and league snapshot hashes from the paths in `report.json["sources"]` and requires
  equality with the recorded ones; requires `report.season == season` and every row's league snapshot identity to match
  the audit's snapshot sha; refuses duplicate `sleeper_id` in `census.csv` or `uncovered.csv`;
- exposes `member(sleeper_id)`, `attachment(sleeper_id)` → `{"status": <availability_class> | "unverified",
  "basis": join_basis | "no verified join", "note": …}` (an uncovered id or an unknown/contested member is unverified);
- exposes `coverage(board_rows, owned_ids, positions)` → per position three separate populations: `league_owned`
  (owned ids: in census by class, with/without forecast), `listed_unowned` (census members not owned: by class ×
  with/without forecast), and `unmatched_nfl_records` (count, kept separate, never added to a denominator);
  `archive` is filled by the caller from the universe census and labelled "Sleeper-eligible ids incl. inactive/retired".

Red: `.venv/bin/python -m pytest tests/ranking/test_current_census_binding.py -q` (ImportError → red).
Green: same command passes; `.venv/bin/python -m pytest tests/ranking -q` still passes.

### T2 — `scripts/dg178/audit_roster_coverage.py`: `--census-dir`

- Loads the binding (T1) with `season` = forecast year and the audit's snapshot sha; writes `report["current_census"]`
  {run dir, hashes, identity checks, coverage per position, unmatched count, uncovered count} and, per view,
  `reference_attachment[pos]` from `binding.attachment(bar sleeper id)` — the bar player himself is NOT changed.
- Refuses a `latest`-style path; records the census run id in provenance.

Red: none unit-level (script); green = the new audit run + the identical-rows diff against `203007Z` (see T5).

### T3 — `app/api/routes/research_preview.py` + `tests/contract/test_research_preview_route.py`

- `_sentence`: zero → "Zero impact on this board: an actual forecast that does not exceed the next available {pos} in
  the {n} seasons shown (2026: {his} vs {ref}; …). Not missing data, not zero points, not zero trade value." Exact tie in
  every season → "equal to the reference". Near-zero → the sentence quotes one decimal with sign. Missing → the producer's
  stated reason verbatim, else "no forecast from the selected producers for this window; no reason stated" — never "no
  2025 stat line" unless the producer said so.
- Each season gains `player_expected_points` and `reference_expected_points`, derived from the full-precision
  `expected_margin` + the reference series only when both are finite; absent otherwise.
- View gains `coverage` (league-owned → listed unowned by status → archive) from `report["current_census"]`, and
  `reference[pos].nfl_attachment` from `reference_attachment` (Hunt: unverified, "no verified join …; Sleeper lists
  Active with no team"). `nfl_status` stays what it is (Sleeper's flag) but is labelled `sleeper_status`.

Red: `.venv/bin/python -m pytest tests/contract/test_research_preview_route.py -q` (new tests fail).
Green: the same; then `.venv/bin/python -m pytest tests/ranking tests/contract/test_research_preview_route.py -q`.

### T4 — frontend: `frontend/src/research/researchHelpers.ts` (new, pure) + `researchHelpers.test.ts` (new) + `ResearchPreview.tsx` + `ResearchPreview.css`

- `filterLeague(rows, query)`: trims, case-insensitive on name / team / position; deterministic order (value desc, then
  name, then player_id); empty query → `[]` (default view unchanged); no match → `[]` with the caller rendering a no-match
  line.
- `marginLabel(margin)`: exact 0 → "equal to reference"; |m| < 0.05 → "within 0.1 of reference"; otherwise "above" /
  "below reference" with `formatMargin` showing one decimal below 1 point and a signed integer otherwise — no rounded
  "0 above/below" ever.
- Component: one labelled text input ("Find a league player", clear control, `aria-controls` the results table) above a
  "League players" section that renders matches through the existing `PlayerTable`; both horizons; no-match state;
  Why row shows per season "his {player_expected_points} vs reference {reference_expected_points}"; reference line uses
  `nfl_attachment` wording; a coverage line: league-owned first, then listed players by status, then archive scope.
  Existing tokens/components only; CSS census ledgers updated if raw values change.

Red: `cd frontend && npx vitest run src/research --reporter=dot` (helper tests fail to import).
Green: same; `npx tsc --noEmit`; `npx biome check src/research`; `npx vitest run src/styles src/research`;
`npm run build`.

### T5 — new immutable candidate + QA + checkpoint

1. `.venv/bin/python scripts/dg178/audit_roster_coverage.py … --census-dir runs/20260906T202057Z/dg178_current_census
   --window championship_week17 --forecast-date 2026-09-06` (same inputs as `203007Z` plus the census).
2. Diff vs `203007Z`: identical values/margins/actions/readiness/references/counts/target/artifact on both boards.
3. Restart the isolated server on HEAD with `DG178_PREVIEW_RUN=20260906T203007Z` (pin unchanged); capture the candidate at
   `?run=<new>` desktop 1280 / phone 390 with the capture script (must run inside `frontend/`), incl. a search interaction.
4. Focused checks: `tests/ranking`, route tests, vitest `src/research src/styles`; full backend suite from the root.
5. Commit with explicit paths; ticket entry with run id, hashes, command, receipts; message lanes for cross-review
   (veteran: new per-season player/reference details vs its frozen export; rookie: search/placement and rookie expected
   points vs its frozen export).

## Out of scope (refuse if tempted)

Changing the reference or its policy, eligibility/placement rules, any forecast value; market blends, ordinal ranks,
tiers; a new layout; screenshots before the build exists; consuming a mutable "latest" path.
