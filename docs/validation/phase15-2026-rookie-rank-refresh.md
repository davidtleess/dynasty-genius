# Phase 15.1 — 2026 Rookie Rank Refresh

Generated: 2026-09-05T01:17:50Z
Identity source: `resources/prospect_identity_2026.json` (snapshot: 2026-05-09)
2026 cohort: 80 total · 80 scored · 0 PRE_MODEL (age-data blockers)
2027 watchlist: 2 entries, excluded from 2026 rankings

## Identity Stability Check

- Source: `nfl_data_py_verified_nfl_draft`, snapshot `2026-05-09`
- 80 verified 2026 draft picks; pick/round confirmed against existing artifact
- Age source: preserved from `prospect_cards.json` where present; computed from `birth_date` in identity file for newly unblocked players
- `player_id` values preserved from existing cards for Rookie Board continuity
- DVS drift warnings (>0.01): 0
- No DVS drift — all 74 scored players match baseline exactly

## DVS Top 24

| DVS# | xVAR# | Name | Pos | Pick | DVS | xVAR | Δ |
|---|---|---|---|---|---|---|---|
| 1 | 1 | Jeremiyah Love | RB | 3 | 74.9 | 29.7 | 0 |
| 2 | 4 | Fernando Mendoza | QB | 1 | 70.7 | 9.7 | +2 |
| 3 | 2 | Jadarian Price | RB | 32 | 66.6 | 21.4 | -1 |
| 4 | 8 | Ty Simpson | QB | 13 | 65.6 | 4.6 | +4 |
| 5 | 3 | Carnell Tate | WR | 4 | 55.1 | 10.1 | -2 |
| 6 | 5 | Jordyn Tyson | WR | 8 | 54.4 | 9.4 | -1 |
| 7 | 6 | Makai Lemon | WR | 20 | 52.3 | 7.3 | -1 |
| 8 | 7 | KC Concepcion | WR | 24 | 51.6 | 6.6 | -1 |
| 9 | 32 | Drew Allar | QB | 76 | 49.4 | -11.6 | +23 |
| 10 | 33 | Carson Beck | QB | 65 | 48.9 | -12.1 | +23 |
| 11 | 9 | Denzel Boston | WR | 39 | 45.0 | 0.0 | -2 |
| 12 | 10 | Omar Cooper Jr. | WR | 30 | 44.9 | -0.1 | -2 |
| 13 | 11 | Kaelon Black | RB | 90 | 44.7 | -0.5 | -2 |
| 14 | 12 | Germie Bernard | WR | 47 | 43.6 | -1.4 | -2 |
| 15 | 13 | Antonio Williams | WR | 71 | 43.5 | -1.5 | -2 |
| 16 | 14 | De'Zhaun Stribling | WR | 33 | 42.0 | -3.0 | -2 |
| 17 | 17 | Jonah Coleman | RB | 108 | 41.2 | -4.0 | 0 |
| 18 | 16 | Ted Hurst | WR | 84 | 41.2 | -3.8 | -2 |
| 19 | 18 | Chris Bell | WR | 94 | 39.5 | -5.5 | -1 |
| 20 | 51 | Cade Klubnik | QB | 110 | 39.4 | -21.6 | +31 |
| 21 | 19 | Malachi Fields | WR | 74 | 39.0 | -6.0 | -2 |
| 22 | 20 | Caleb Douglas | WR | 75 | 38.8 | -6.2 | -2 |
| 23 | 15 | Kenyon Sadiq | TE | 16 | 38.2 | -3.6 | -8 |
| 24 | 22 | Zachariah Branch | WR | 79 | 38.1 | -6.9 | -2 |

## xVAR Top 24

> rank_delta = xvar_class_rank − dvs_class_rank. Positive = fell in xVAR ordering. Negative = rose.

| DVS# | xVAR# | Name | Pos | Pick | DVS | xVAR | Δ |
|---|---|---|---|---|---|---|---|
| 1 | 1 | Jeremiyah Love | RB | 3 | 74.9 | 29.7 | 0 |
| 3 | 2 | Jadarian Price | RB | 32 | 66.6 | 21.4 | -1 |
| 5 | 3 | Carnell Tate | WR | 4 | 55.1 | 10.1 | -2 |
| 2 | 4 | Fernando Mendoza | QB | 1 | 70.7 | 9.7 | +2 |
| 6 | 5 | Jordyn Tyson | WR | 8 | 54.4 | 9.4 | -1 |
| 7 | 6 | Makai Lemon | WR | 20 | 52.3 | 7.3 | -1 |
| 8 | 7 | KC Concepcion | WR | 24 | 51.6 | 6.6 | -1 |
| 4 | 8 | Ty Simpson | QB | 13 | 65.6 | 4.6 | +4 |
| 11 | 9 | Denzel Boston | WR | 39 | 45.0 | 0.0 | -2 |
| 12 | 10 | Omar Cooper Jr. | WR | 30 | 44.9 | -0.1 | -2 |
| 13 | 11 | Kaelon Black | RB | 90 | 44.7 | -0.5 | -2 |
| 14 | 12 | Germie Bernard | WR | 47 | 43.6 | -1.4 | -2 |
| 15 | 13 | Antonio Williams | WR | 71 | 43.5 | -1.5 | -2 |
| 16 | 14 | De'Zhaun Stribling | WR | 33 | 42.0 | -3.0 | -2 |
| 23 | 15 | Kenyon Sadiq | TE | 16 | 38.2 | -3.6 | -8 |
| 18 | 16 | Ted Hurst | WR | 84 | 41.2 | -3.8 | -2 |
| 17 | 17 | Jonah Coleman | RB | 108 | 41.2 | -4.0 | 0 |
| 19 | 18 | Chris Bell | WR | 94 | 39.5 | -5.5 | -1 |
| 21 | 19 | Malachi Fields | WR | 74 | 39.0 | -6.0 | -2 |
| 22 | 20 | Caleb Douglas | WR | 75 | 38.8 | -6.2 | -2 |
| 28 | 21 | Eli Stowers | TE | 54 | 35.2 | -6.6 | -7 |
| 24 | 22 | Zachariah Branch | WR | 79 | 38.1 | -6.9 | -2 |
| 25 | 23 | Ja'Kobi Lane | WR | 80 | 37.9 | -7.1 | -2 |
| 26 | 24 | Mike Washington Jr. | RB | 122 | 37.5 | -7.7 | -2 |

## Rank Movers (|rank_delta| > 10)

| DVS# | xVAR# | Name | Pos | Pick | DVS | xVAR | Δ |
|---|---|---|---|---|---|---|---|
| 20 | 51 | Cade Klubnik | QB | 110 | 39.4 | -21.6 | +31 |
| 10 | 33 | Carson Beck | QB | 65 | 48.9 | -12.1 | +23 |
| 9 | 32 | Drew Allar | QB | 76 | 49.4 | -11.6 | +23 |
| 55 | 74 | Cole Payton | QB | 178 | 19.9 | -41.1 | +19 |

## TE xVAR Impact

ENGINE_A_REPLACEMENT_DVS[TE] = 98.8. All 2026 TEs with DVS < 98.8 produce negative xVAR — correct Superflex behavior. A TE with DVS 100.0 would produce xVAR ≈ +0.9.

| DVS# | xVAR# | Name | Pick | DVS | xVAR | Δ |
|---|---|---|---|---|---|---|
| 23 | 15 | Kenyon Sadiq | 16 | 38.2 | -3.6 | -8 |
| 28 | 21 | Eli Stowers | 54 | 35.2 | -6.6 | -7 |
| 31 | 25 | Max Klare | 61 | 33.4 | -8.4 | -6 |
| 32 | 27 | Sam Roush | 69 | 33.0 | -8.8 | -5 |
| 34 | 29 | Eli Raridon | 95 | 31.6 | -10.2 | -5 |
| 36 | 30 | Marlin Klein | 59 | 30.5 | -11.3 | -6 |
| 37 | 34 | Oscar Delp | 73 | 29.2 | -12.6 | -3 |
| 40 | 36 | Nate Boerkircher | 56 | 28.2 | -13.6 | -4 |
| 42 | 38 | Tanner Koziol | 164 | 27.6 | -14.2 | -4 |
| 43 | 39 | Justin Joly | 152 | 26.7 | -15.1 | -4 |
| 44 | 40 | Will Kacmarek | 87 | 26.2 | -15.6 | -4 |
| 48 | 45 | Matthew Hibner | 133 | 22.8 | -19.0 | -3 |
| 51 | 46 | Josh Cuevas | 173 | 22.2 | -19.6 | -5 |
| 52 | 47 | Riley Nowakowski | 169 | 21.9 | -19.9 | -5 |
| 53 | 48 | Seydou Traore | 180 | 21.9 | -19.9 | -5 |
| 54 | 49 | Joe Royer | 170 | 21.6 | -20.2 | -5 |
| 56 | 55 | Bauer Sharp | 185 | 19.4 | -22.4 | -1 |
| 57 | 56 | Max Bredeson | 159 | 19.3 | -22.5 | -1 |
| 58 | 57 | Jaren Kanak | 225 | 19.2 | -22.6 | -1 |
| 61 | 58 | Carsen Ryan | 248 | 18.3 | -23.5 | -3 |
| 64 | 59 | Jack Endries | 221 | 17.9 | -23.9 | -5 |
| 70 | 64 | Dallen Bentley | 256 | 14.4 | -27.4 | -6 |

## Age-Data Blockers — All Resolved

All 6 age-data blockers resolved. All 80 2026 prospects are now scored.

| Name | Position | Pick | Round |
|---|---|---|---|

## 2027 Watchlist — Excluded from 2026 Rankings

| Name | Position | Draft Class | Grade |
|---|---|---|---|
| Ryan Williams | WR | 2027 | PRE_MODEL |
| Jeremiah Smith | WR | 2027 | PRE_MODEL |
