# Source preparation for the common outcomes (dg179_source_preparation_v1)

Capture `runs/20260906T191723Z/weekly_source_capture`; schedule `https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv` captured 2026-09-06T19:44:54.876269+00:00 (sha256 `446ff5d6fd8e…`).

Admitted seasons 2001–2025; excluded {1999: ['1999_01_BAL_STL'], 2000: ['2000_03_SD_KC', '2000_06_BUF_MIA']} (never zero-labelled). Cancelled and excluded explicitly: ['2022_17_BUF_CIN'].

| season | schedule REG | cancelled | completed | weekly REG | missing | unexpected |
|---|---:|---|---:|---:|---|---|
| 2001 | 248 | [] | 248 | 248 | [] | [] |
| 2002 | 256 | [] | 256 | 256 | [] | [] |
| 2003 | 256 | [] | 256 | 256 | [] | [] |
| 2004 | 256 | [] | 256 | 256 | [] | [] |
| 2005 | 256 | [] | 256 | 256 | [] | [] |
| 2006 | 256 | [] | 256 | 256 | [] | [] |
| 2007 | 256 | [] | 256 | 256 | [] | [] |
| 2008 | 256 | [] | 256 | 256 | [] | [] |
| 2009 | 256 | [] | 256 | 256 | [] | [] |
| 2010 | 256 | [] | 256 | 256 | [] | [] |
| 2011 | 256 | [] | 256 | 256 | [] | [] |
| 2012 | 256 | [] | 256 | 256 | [] | [] |
| 2013 | 256 | [] | 256 | 256 | [] | [] |
| 2014 | 256 | [] | 256 | 256 | [] | [] |
| 2015 | 256 | [] | 256 | 256 | [] | [] |
| 2016 | 256 | [] | 256 | 256 | [] | [] |
| 2017 | 256 | [] | 256 | 256 | [] | [] |
| 2018 | 256 | [] | 256 | 256 | [] | [] |
| 2019 | 256 | [] | 256 | 256 | [] | [] |
| 2020 | 256 | [] | 256 | 256 | [] | [] |
| 2021 | 272 | [] | 272 | 272 | [] | [] |
| 2022 | 271 | [] | 271 | 271 | [] | [] |
| 2023 | 272 | [] | 272 | 272 | [] | [] |
| 2024 | 272 | [] | 272 | 272 | [] | [] |
| 2025 | 272 | [] | 272 | 272 | [] | [] |

identified_weekly.parquet: 442,167 rows, 150 original columns, sha256 `6f7c76cca4f1…`

Quarantine: 530 rows (524 zero placeholders, 6 reviewed nonzero). Signed / absolute point exclusions by season:

| season | rows | signed | absolute | nonzero rows |
|---|---:|---:|---:|---:|
| 2001 | 21 | -2.32 | 5.68 | 3 |
| 2002 | 21 | +0.00 | 0.00 | 0 |
| 2003 | 21 | -0.10 | 0.10 | 1 |
| 2004 | 21 | +0.00 | 0.00 | 0 |
| 2005 | 21 | +6.00 | 6.00 | 1 |
| 2006 | 21 | +0.00 | 0.00 | 0 |
| 2007 | 21 | +0.00 | 0.00 | 0 |
| 2008 | 21 | +0.00 | 0.00 | 0 |
| 2009 | 21 | +0.00 | 0.00 | 0 |
| 2010 | 21 | +0.00 | 0.00 | 0 |
| 2011 | 21 | +0.00 | 0.00 | 0 |
| 2012 | 21 | +3.10 | 3.10 | 1 |
| 2013 | 21 | +0.00 | 0.00 | 0 |
| 2014 | 21 | +0.00 | 0.00 | 0 |
| 2015 | 21 | +0.00 | 0.00 | 0 |
| 2016 | 21 | +0.00 | 0.00 | 0 |
| 2017 | 21 | +0.00 | 0.00 | 0 |
| 2018 | 21 | +0.00 | 0.00 | 0 |
| 2019 | 21 | +0.00 | 0.00 | 0 |
| 2020 | 21 | +0.00 | 0.00 | 0 |
| 2021 | 22 | +0.00 | 0.00 | 0 |
| 2022 | 22 | +0.00 | 0.00 | 0 |
| 2023 | 22 | +0.00 | 0.00 | 0 |
| 2024 | 22 | +0.00 | 0.00 | 0 |
| 2025 | 22 | +0.00 | 0.00 | 0 |

Reviewed nonzero records (research-only exception, not a tolerance):

- 2001 w11 GB vs DET Team +1.68 (row 10277, file sha 5a9f2cfc6630…)
- 2001 w14 ARI vs NYG unnamed -2.00 (row 13176, file sha 5a9f2cfc6630…)
- 2001 w16 BAL vs TB unnamed -2.00 (row 15110, file sha 5a9f2cfc6630…)
- 2003 w4 PHI vs BUF Team -0.10 (row 3897, file sha 3113e4a054db…)
- 2005 w1 LV vs NE Team +6.00 (row 1042, file sha 5646a8f2c0f4…)
- 2012 w6 TEN vs PIT D.Bryant +3.10 (row 5926, file sha b33f939c2ec0…)

research_qualified = true; individual_stat_completeness_proven = false; no exact-league scoring claim.
