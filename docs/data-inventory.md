# Data Inventory — what we actually have

**Measured 2026-07-30 evening from the code and from disk. Claude Code.**
This is the list. One row per source. Plain language.

---

# ★ DAVID'S LIST — the layer 1–2 target

**His words, 2026-07-25 15:14. This is the target. Everything else in this file is context for it.**

> "it also seems to me that Dynasty Genius has neglected one of its core advantages - I pay for
> multiple premium data sets. Dynasty Genius, PFF, collegefootballdata.com, playerprofiler,
> FantasyPros, Footballguys. --- we can also look at public data like NFL Next Gen Stats"

**Original record found:** `/Users/davidleess/.claude/projects/-Users-davidleess/07b583c0-cc2f-4818-83a4-a09e1147ce47.jsonl:2838`
(also indexed at `/Users/davidleess/.claude/history.jsonl:5623`).

The adjacent direction is at the same transcript's line 2847 and
`/Users/davidleess/.claude/history.jsonl:5624`:

> i would force you to continue using sources that are free and work, as well as new ones like dynastyprocess (their GITHUB TOO)  and nfl next gen stats. even if i have to set up a claude code manual export in off cases. I also want a full blown sweep of github for valuable repos

Search covered the repo's source contracts, strategies, roadmap, ledger and evidence; Claude
history, project transcripts, file history and Tower files; Codex history and sessions; Gemini
transcripts; `dg-cockpit`; and temporary text/task/scratch files. No credential or secret file was
opened.

## ONE OF SIX.

**Six sources on his list. Five he pays for — PFF, CFBD, PlayerProfiler, FantasyPros, Footballguys —
plus NFL Next Gen Stats, free. We are getting ONE of the six, and it is reading a two-month-old
cache.** That is the only number on this page that matters.

| # | Source | Getting it today? | Why not | What it would take | What we lose without it |
| --: | :-- | :-- | :-- | :-- | :-- |
| 1 | **collegefootballdata.com (CFBD)** | **YES — the source is live.** But we are eating from a **2-month-old cache** (810 files, last moved 2026-05-24) | Nothing is broken. The key works — I called the live API tonight: **HTTP 200, 681 teams returned.** Nobody scheduled a refresh, so the pipeline reads a May snapshot | **Hours.** Re-run the college feature build against the live API. Making it *stay* fresh is a scheduler decision, which is your word | Every rookie is being graded on May college numbers — breakout age, dominator, target share. We are scouting the 2026 class with last spring's stats |
| 2 | **PFF** | **BY HAND ONLY** — 3 files you exported yourself, newest **2026-05-23** | The documented automated credential path is absent. A parser and real manual data exist; there is no live feed to point it at | **4–8 hours** per refresh once you export. A tested authenticated path is roughly **2–4 days**, subject to PFF's terms and subscription tier | Snaps, routes, route participation, YPRR, and grading a box score cannot show. Without them we cannot see *how* a WR or TE won, only that a target arrived |
| 3 | **PlayerProfiler** | **HISTORICAL ONLY** — old caches and a v2 training table contain real values; the current path is broken | The current probe returned **874 parse errors out of 874 players**. The documented credential directory is absent, and the existing adapter has no current product caller | **2–4 days** to restore authentication, update the parser, and run identity/coverage QA; a manual HTML export could reduce this to **about 1 day** | Breakout age, speed score, target share, and college dominator — rookie evidence we are paying for and currently modelling without |
| 4 | **FantasyPros** | **HISTORICAL ONLY** — 2,185 rows on four dates through DynastyProcess; no live feed | We built only a four-date archive and never built an authorized current export/feed | **1–2 days** if the paid account exposes a usable export; **3–5 days** if browser-authenticated retrieval is required | Current consensus rankings, positional ECR, and an independent draft/trade/waiver view. Today that comparison leans on FantasyCalc alone |
| 5 | **Footballguys** | **NO** | **Zero code references anywhere.** Its *thinking* is deep in us — mortality tables / expected years remaining, Superflex replacement level, seasonal value multipliers, cited across 16 strategy docs. Its *data* was never ingested | **UNVERIFIED — I cannot size this without you.** Tell us what your subscription actually lets you download (export? API? articles only?) and it becomes a real estimate | UNVERIFIED until we know what it serves. The age/replacement-level framing we already borrowed is doing real work in our valuation |
| 6 | **NFL Next Gen Stats** | **NO** | Never switched on. **And it is already sitting in the box** — `nflreadpy.load_nextgen_stats()` ships in a library we already depend on and call every morning | **Hours. This is the cheapest tank on the board and it is free.** One function call, plus the join we already do for every other nflreadpy table | Separation, cushion, air yards, time-to-throw. Real athleticism-and-usage signal for WR and QB that we currently proxy at |

**CORRECTION, recorded rather than quietly erased (David, 2026-07-30 22:41).** This table originally
carried a seventh row for **"Dynasty Genius"**, filed as an unidentified third-party subscription and
marked UNVERIFIED, with a request that David explain it. **"Dynasty Genius" is the name of this
product.** The row has been struck. **The list is six sources, not seven.**

**The finding underneath the correction — it is not an apology.** Three independent lanes read the
name of the product they work in every day, sitting inside a sentence David wrote, and each filed it
as an unknown outside vendor. Two of those lanes marked it UNVERIFIED and asked David to explain his
own product to them. Nobody read the sentence; everyone pattern-matched a comma-separated list into
table cells. **This is the same defect as every instrument this week that reported a state it had
never established** — the shape was processed, the meaning was not. It belongs in the record next to
the others.

**Free data we already pay nothing for, already have installed, and have never called once:**
`load_nextgen_stats` · `load_ff_opportunity` · `load_ff_rankings` · `load_pfr_advstats` ·
`load_ftn_charting` · `load_contracts` · `load_injuries` · `load_depth_charts` — **0 references each.**
Eight loaders, same library, already a dependency.

**One correction to a doc, not to you:** `docs/data-source-contracts.md` says credentials live in
`~/.config/dynasty-genius/`. **That directory does not exist on this machine.** This cross-check
tested directory existence only; it did not open or report any credential file.

---

It replaces nothing and proposes nothing — it reports. Where a cell could not be established, it says
`UNVERIFIED` rather than guessing. Rows marked **(corroborates Tower)** were confirmed only after
reading Tower's sweep; everything else was measured first-hand.

> **"Last moved" means the CONTENT changed**, not that a job ran. A job that fires perfectly every
> morning onto data that has not moved in two months is the failure this column exists to expose.

---

## The table

| Source | Paid or free | Ingested today? | Where it lands | How it refreshes | What reads it | Last time content moved |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| **Sleeper** (league, rosters, users, players) | Free | **YES** | `app/data/league_runtime/` (108 files) | LaunchAgent `dynasty-league-capture`, 09:20 daily | League Pulse, roster surfaces, identity | **2026-07-30 09:36** |
| **Sleeper transactions** | Free | **YES — as of tonight** | `app/data/league_transactions.db` | **NOTHING** — manual command only | NOBODY yet (layer-1 substrate) | **2026-07-30 22:16** (4 seasons, 932 txns) |
| **FantasyCalc** (market values) | Free public API | **YES** | `app/data/fc_forward_capture.db`, `universe_market_divergence_latest.json` | LaunchAgent `dynasty-market-divergence-refresh` 09:40 + `dynasty-fc-snapshot` 09:00 | Market divergence / margin | **2026-07-30 09:40** |
| **nflverse via nflreadpy** (NFL stats, PBP, rosters, draft picks) | Free | **YES** | `app/data/features_runtime/` | LaunchAgent `dynasty-feature-refresh`; today's run was a no-op | Engine B features, outcome capture | **2026-07-10 09:21** |
| **CFBD — collegefootballdata.com** | **PAID** (David's list; exact tier UNVERIFIED) | **YES, from a stale local cache** | `app/data/cfbd_cache/` (810 files) | **NOTHING scheduled** | Engine A college features (from cache) | **2026-05-24** — 2 months |
| **PFF** | **PAID** | **BY HAND ONLY** | `app/data/pff_exports/` (3 files) | **NOTHING automatic** — David exports by hand | `scripts/build_college_features.py` only | **2026-05-23** — 2 months |
| **PlayerProfiler** | **PAID** | **HISTORICAL ONLY** | Old caches and `app/data/training/prospects_with_outcomes_v2.csv`; current probe is **874/874 parse errors** | **NOTHING current** | NOBODY in current v3 | **2026-05-11** |
| **FantasyPros** | **PAID** (David's list) | **HISTORICAL ONLY** | `app/data/fc_snapshots.db`, source `dp_archive`: 2,185 rows on four dates | One manual archive load; **NOTHING current** | Backtest/trust-surface code | Local load **2026-05-30**; newest source date **2024-09-08** |
| **Footballguys** | **PAID — UNVERIFIED** (David named it 07-25; he added the URL again 22:21 tonight) | **NO** | nowhere | **NOTHING** | **NOBODY** — its *ideas* are cited in 16 strategy docs; its *data* was never ingested | **never** |
| **MyFantasyLeague (MFL)** — rookie ADP | Free public export API | **NO** (adapter exists, fixture-backed) | no production store | **NOTHING** | NOBODY outside adapter/tests | **never** |
| **RAS — ras.football** | Free | **NO** — fixture-backed only | `tests/fixtures/` | **NOTHING** | Risk-flag context | fixture, static |
| **RotoViz** | **UNVERIFIED** (likely paid) | **NO** | nowhere | **NOTHING** | **NOBODY** — declared in the registry, no fetch code exists | **never** |
| **Campus2Canton** | **UNVERIFIED** | **NO** | nowhere | **NOTHING** | **NOBODY** — declared in the registry, no fetch code exists | **never** |
| **KeepTradeCut (KTC)** | Free | **NO** | nowhere live | **NOTHING** | NOBODY — and by constitution it may never enter a model | **UNVERIFIED** |
| **NFL Next Gen Stats** | Free (David named it as public data) | **NO** | nowhere | **NOTHING** | **NOBODY** | **never** |
| **Sleeper CDN** (player images) | Free | **YES** | `app/data/assets/` (263 files) | **NOTHING** — built once | Front-end player images | **2026-07-06** |
| **Sportradar** | Enterprise — never contracted | **NO** | nowhere | **NOTHING** | **NOBODY** — name only, in the registry | **never** |
| **Genius Sports** | Enterprise — never contracted | **NO** | nowhere | **NOTHING** | **NOBODY** — name only | **never** |
| **Stats Perform** | Enterprise — never contracted | **NO** | nowhere | **NOTHING** | **NOBODY** — name only | **never** |
| **Rolling Insights** | Enterprise — never contracted | **NO** | nowhere | **NOTHING** | **NOBODY** — name only | **never** |
| **Dynasty Data Lab** | **UNVERIFIED** | **NO** | nowhere | **NOTHING** | **NOBODY** — name only | **never** |
| **ESPN** | Free | **NO** | nowhere | **NOTHING** | **NOBODY** — appears only in prose/research | **never** |
| **Rotowire** | **UNVERIFIED** | **NO** | nowhere | **NOTHING** | **NOBODY** — appears only in prose/research | **never** |
| **Dynasty Nerds** | — | **NOT A SOURCE** | — | — | — | **This is a COMPETITOR** in our positioning docs, not a data source. Listed so nobody re-adds it as one. |

### Derived stores (not external sources, but they are our data and they move or don't)

| What | Where | Refreshes | Last moved |
| :-- | :-- | :-- | :-- |
| Model output (PVO runtime) | `app/data/valuation_runtime/universe_pvo_runtime.json` | LaunchAgent `dynasty-model-pvo-refresh` 09:30 | **2026-07-30 09:36** |
| Model prediction capture | `app/data/model_forward_capture.db` | with the PVO refresh | **2026-07-30 09:37** |
| League opportunity | `app/data/valuation/league_opportunity_latest.json` | **NOTHING** | **file touched 07-22, but its content is stamped 2026-07-15** — 15 days apart |
| FC snapshots (older store) | `app/data/fc_snapshots.db` | LaunchAgent `dynasty-fc-snapshot` **is installed** | **2026-06-24** — 5 weeks, while the job exists |
| Daily What-Changed report | `app/data/what_changed/` (1 file) | LaunchAgent `dynasty-what-changed-report` **is installed** | **2026-06-24** — 5 weeks, while the job exists |
| Realized-outcome scorecard | `app/data/realized_outcome/` | LaunchAgent installed, weekly | **never produced a file** (off-season no-op by design) |
| League behaviour research | `app/data/research/league_behavior/` (179 files) | **NOTHING** | **2026-07-19** |

---

## What is missing — things we do not ingest at all that the layers above would need

1. **Current data from three paid subscriptions.** PlayerProfiler and FantasyPros have historical
   data but no current feed; Footballguys has nothing. CFBD's cache and PFF's manual files are
   about two months old.
2. **Live college production.** CFBD is cache-only, so Engine A trains on a static May snapshot.
3. **Advanced NFL usage David named as free** — Next Gen Stats. Never ingested.
4. **League history beyond transactions** — drafts, standings, matchups, weekly lineups across the
   four seasons. Sleeper serves all of it; we call none of it.
5. **A live market source other than FantasyCalc.** KTC is named everywhere and ingested nowhere.
6. **Anything that would answer "is a manager still the same person"** — solved tonight inside the
   transaction chain, not available anywhere else.

## Three things the table says that are worth saying out loud

1. **We are paying for PlayerProfiler and getting nothing current.** Old caches and the v2 training
   table contain real values, but the current probe fails 874/874 rows and current v3 consumes none
   of those fields. The registry declares six PlayerProfiler columns (`breakout_age`, `speed_score`,
   `target_share` and their `source_*` twins) that the current path does not produce.
2. **Two jobs run onto content that has not moved in five weeks** — the FC-snapshot agent and the
   What-Changed agent are both installed and firing. Their outputs are dated 2026-06-24.
3. **The registry is wrong in both directions.** It lists 19 sources. Four of them (Sportradar,
   Genius Sports, Stats Perform, Rolling Insights) were never contracted and have no code. It omits
   sources the product leans on daily — general nflreadpy, Sleeper CDN, the DynastyProcess archive,
   and, until tonight, transactions.
