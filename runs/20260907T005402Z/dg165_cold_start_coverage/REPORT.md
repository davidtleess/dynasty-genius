# DG-165 unowned cold-start coverage

Missing default-pool players audited: 84.

## By route

- dormant_drafted: 6
- dormant_no_draft_record: 5
- existing_forecast_join_failure: 4
- never_appeared_drafted: 11
- never_appeared_no_draft_record: 55
- unknown_identity: 3

## By draft status (positive evidence only)

- drafted_verified: 19
- no_draft_record_1_source: 34
- no_draft_record_2_sources: 28
- unknown_identity: 3

## By NFL availability class

- active: 20
- injured_reserve: 14
- practice_squad: 50

## By position

- QB: 15
- RB: 21
- TE: 15
- WR: 33

## DG-177 full-NFL source reason (beside the window view)

- left_cohort_two_absent_seasons: 12
- no_nfl_history: 68
- not_in_dg177_universe: 4

## Entry seasons of never-appeared players

- 2019: 1
- 2021: 1
- 2022: 1
- 2023: 3
- 2024: 3
- 2025: 22
- 2026: 35

## Existing-forecast join failures (recovered from the original producer rows, not refitted)

- Alec Ingold (sleeper 6109, gsis 00-0035125): DG-177 2025 row, e_points_year1 3.9432079815143126
- Kyle Juszczyk (sleeper 1379, gsis 00-0029892): DG-177 2025 row, e_points_year1 22.631300520976374
- Michael Burton (sleeper 2471, gsis 00-0031595): DG-177 2025 row, e_points_year1 0.0
- Adam Prentice (sleeper 8025, gsis 00-0036727): DG-177 2025 row, e_points_year1 10.197681979436744

## Definitions

- **no_draft_record**: no positive draft record in the sources that know the id; a statement about the sources, never a claim that the player was passed over in the draft
- **never_appeared**: no championship-window stat row in the common outcome artifact; not observed zero production
- **full_nfl_source_reason**: DG-177's own reason from its universe reconciliation (any REG stat line, e.g. week 18) — kept beside the window view, never merged
