# Consultant brief — GEMINI CONSULTANT · cohort history and stability measurement

From Claude (write lane, DG cockpit) · `[w#r1-r2-group]` · 2026-08-19
**Read-only engagement. Telemetry deliverable — facts with paths and timestamps. No verdicts.**

You are outside the DG cockpit. Your output is **fact-bearing, not action-bearing**: it informs the
R1/R2 framing and authorizes nothing. Do not issue review verdicts, CLEARs, framings, recommendations,
or football judgment — that boundary is `02` §Agent Roles and it holds for this engagement.

## Bootstrap

Read `docs/governance/02-agent-operating-loop.md`, `00-product-constitution.md`, and
`05-layer-doctrine.md`, then `AGENT_SYNC.md` from line 1 to `⏹ END CURRENT BOARD`.
Repo: `/Users/davidleess/dynasty-genius-product`.

## Why this lane exists

Two cohorts are being designed around right now, and **both are known only as a single-day snapshot.**
A framing built on one day's numbers is a framing that cannot tell a chronic condition from a
Tuesday. Nobody has measured whether these cohorts are stable, growing, or seasonal.

Today's snapshot (`app/data/valuation_runtime/universe_pvo_runtime.json`,
`captured_at 2026-08-18T13:30:03Z`, 12,222 rows):

- **Cohort A — blank score, live projection:** 115 rows with `dynasty_value_score = None` and a
  present `projection_2y`. 114 of them carry `dvs_engine = "A"`.
- **Cohort B — outside the model entirely:** rows with `dg_status = PRE_MODEL`. 10 of them are
  **rostered** somewhere in the league; one (Tank Dell, `sleeper_id 9502`) is on David's own roster.
- The modeled cohort itself is 583 rows (`identity_status = resolved`), of which 503 carry a
  projection and 468 carry a score.

## What to measure

Use the forward PIT capture stores and any retained daily model/market captures — that accumulation is
exactly what they exist for. Report facts with **paths and timestamps** throughout.

1. **Cohort A over time.** Daily count for every capture date available. Is 115 flat, drifting, or
   seasonal? Studio observed a 1–7 game band stable at 115 of 583 across eleven days — verify that
   independently against the capture store rather than accepting it.
2. **Cohort B over time.** Daily `PRE_MODEL` count, and the rostered subset. **When did Tank Dell first
   become `PRE_MODEL`?** Was he ever in the modeled cohort? If the captures cannot answer, say so — do
   not infer it.
3. **Churn.** How many players changed `dg_status` or `dvs_engine` between consecutive captures, and in
   which direction. A cohort that is stable in size but churning underneath is a different problem
   from a static one.
4. **The 583.** Is the modeled-cohort size itself stable, and what is the earliest capture date
   available for any of these series? Name the coverage floor plainly.
5. **Feed freshness context.** For the streams feeding this store, current freshness against registered
   cadence: `participation`, `pbp`, `player_stats`, `snap_counts`, `rosters`, `depth_charts`. On
   2026-08-18 `participation` was recorded `loaded_empty` and three streams were on 2025 cache. State
   today's status with its marker path and timestamp.

## Return format

A table per series: date · count · source artifact path · capture timestamp. Then a short factual
summary. **No interpretation of what the numbers mean for the product, no recommended action, no
severity ranking.** If a series cannot be built from retained captures, report it unavailable with the
named reason — an honest gap is a usable result and a plausible-looking reconstruction is not.

## Constraints

- Read-only. No writes outside your own report artifact.
- Every number carries its artifact path and timestamp (`02` §Falsification #7).
- No verdicts, no CLEARs, no recommendations, no football judgment.
- Do not read, write, or touch `/Users/davidleess/frontend-studio` (standing wall TW29-WALL-35).
