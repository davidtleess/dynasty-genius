# Dynasty Genius — Project Context

## What This Is
A personal dynasty fantasy football intelligence web app built for one user (David).
Not a public product. No authentication. No multi-user complexity.

## Primary Data Sources
- Sleeper API: free, no auth, username-based — primary source for roster and league data
- PlayerProfiler: subscriber scraping — Dominator Rating, RAS, athleticism data
- PFF: subscriber scraping — snap counts, route participation, player grades, YPRR
- KTC (KeepTradeCut): web scraping — dynasty market values, updated in real time
- RAS (ras.football): web scraping — Relative Athletic Scores
- Pro Football Reference: web scraping — historical stats, career data

## Build Priority Order
1. Rookie Evaluator (BPA mode + Needs-Based mode)
2. Roster Auditor (aging curve flags, hold/sell signals)
3. Research Assistant (data layer