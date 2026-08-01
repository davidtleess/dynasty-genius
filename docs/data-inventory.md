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

## THREE INGESTED, ONE BY HAND, TWO NOT CURRENT.

**Six sources on his list. Five he pays for — PFF, CFBD, PlayerProfiler, FantasyPros, Footballguys —
plus NFL Next Gen Stats, free. CFBD, NFL Next Gen Stats and — as of 2026-07-31 — PlayerProfiler are
now ingested; PFF arrives by hand; FantasyPros is historical only; Footballguys is absent. CFBD
still reads a two-month-old cache until David authorizes the isolated refresh after tomorrow's
morning measurement.**

**What "ingested" does and does not mean.** PlayerProfiler data is in the foundation and reaches
NO model and NO surface. That is **the sequence working, not a shortfall** — David's ruling in
`05` §1 is that layers 1-2 are the foundation and *"we shouldn't be wasting cycles until we've
built this foundation."* A layer-1 adapter with no layer-3 consumer is complying with that order,
not falling short of it. It is recorded here only so that "ingested" can never be misread as
"the product got better" — this register has previously described sources as live while they
served a two-month-old cache, and that is the error being guarded against.

**Two different things get written down here, and they must not be confused:**

1. **SEQUENCE STATUS — where the work has reached.** No layer-2 consumer yet; Advanced PBP not
   ingested; FantasyPros and Footballguys unfed; CFBD still on the May cache. Every one of these
   dissolves when the work is done. They are not limits and must not be written as though they
   were. **Layer 1 is not finished, so exploring and curating would be premature by design.**
2. **DATA PROPERTIES — constraints that survive completion.** The medical archive stops at 2023
   and no amount of ingestion extends it. `yards_created_receiving` uses `NA` for both "zero" and
   "not charted" and those will still be indistinguishable in 2027. The 2025 gamelog's man/zone
   coverage columns are gone. **These are real limits, permanently**, and they bound what layer 2
   can honestly build on top of. Carry them forward.

**The order of work, per David (2026-08-01):** finish layer 1 → hypothesize and explore the full
data → then test curation in layer 2 to strengthen the models. **Exploration is its own phase**,
and it is the phase that decides *what* is worth curating — with 317 season columns, 174 gamelog
columns and 92 PBP columns in the store, curating before exploring would only be guessing at a
smaller pile.

| # | Source | Getting it today? | Why not | What it would take | What we lose without it |
| --: | :-- | :-- | :-- | :-- | :-- |
| 1 | **collegefootballdata.com (CFBD)** | **YES — the source is live.** But we are eating from a **2-month-old cache** (810 files, last moved 2026-05-24) | Nothing is broken. The key works — the live API returned HTTP 200 tonight. The isolated raw-to-curated refresh is now built and tested, but was deliberately not executed because changing this input before tomorrow's pre-registered morning run would contaminate that measurement | **Built and runnable.** On David's word after the morning run, one explicit command fetches into a new immutable raw snapshot, validates 99%+ identity coverage and non-degraded output, and publishes a separate curated table without overwriting the May input | Every rookie is being graded on May college numbers — breakout age, dominator, target share. We are scouting the 2026 class with last spring's stats |
| 2 | **PFF** | **BY HAND ONLY** — 3 files you exported yourself, newest **2026-05-23** | The documented automated credential path is absent. A parser and real manual data exist; there is no live feed to point it at | **4–8 hours** per refresh once you export. A tested authenticated path is roughly **2–4 days**, subject to PFF's terms and subscription tier | Snaps, routes, route participation, YPRR, and grading a box score cannot show. Without them we cannot see *how* a WR or TE won, only that a target arrived |
| 3 | **PlayerProfiler** | **YES — ingested 2026-07-31 from David's own subscriber exports.** 5,476 player-seasons (36/36 position-seasons, QB/RB/WR/TE, 2017–2025, 317 columns) plus a 9,768-row medical archive 2017–2023. **No product or model consumer yet** | Nothing is broken. The old 874/874 figure came from an **unauthenticated** `admin-ajax.php` endpoint that never used David's credentials — it proved the shadow path was dead, not the subscription. The sanctioned path is the product's own export button | **Done for layer 1.** Refresh cost is David exporting again + one command. A scheduler is impossible by design (manual export); **layer 2 — a curated consumer — is the open work** | Breakout age, speed score, target share and college dominator are now IN the foundation. They are still not reaching any model, so the loss is unchanged until layer 2 lands |
| 4 | **FantasyPros** | **HISTORICAL ONLY** — 2,185 rows on four dates through DynastyProcess; no live feed | We built only a four-date archive and never built an authorized current export/feed | **1–2 days** if the paid account exposes a usable export; **3–5 days** if browser-authenticated retrieval is required | Current consensus rankings, positional ECR, and an independent draft/trade/waiver view. Today that comparison leans on FantasyCalc alone |
| 5 | **Footballguys** | **NO** | **Zero code references anywhere.** Its *thinking* is deep in us — mortality tables / expected years remaining, Superflex replacement level, seasonal value multipliers, cited across 16 strategy docs. Its *data* was never ingested | **UNVERIFIED — I cannot size this without you.** Tell us what your subscription actually lets you download (export? API? articles only?) and it becomes a real estimate | UNVERIFIED until we know what it serves. The age/replacement-level framing we already borrowed is doing real work in our valuation |
| 6 | **NFL Next Gen Stats** | **YES — raw and curated 2016–2025 aggregates captured tonight; no product/model consumer yet** | Filled tonight through the already-installed `nflreadpy.load_nextgen_stats()` path | **Built and run.** 26,723 curated rows, 100% GSIS identity coverage, immutable raw snapshots, and a repeat-run no-op. A scheduler or model/UI use remains a separate David decision | Separation, cushion, air yards, time-to-throw, expected completion, rushing efficiency, and RYOE are now in the foundation instead of being unavailable |

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

**Free data we already pay nothing for and already have installed:** tonight's check verified all
eight loaders existed and had zero callers. `load_nextgen_stats` is now wired. Seven remain:
`load_ff_opportunity` · `load_ff_rankings` · `load_pfr_advstats` · `load_ftn_charting` ·
`load_contracts` · `load_injuries` · `load_depth_charts`. The raw/curated capture mechanics
generalize, but their schemas, season availability, identity keys, licenses, and football use
still require source-specific contracts.

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
| **CFBD — collegefootballdata.com** | **PAID** (David's list; exact tier UNVERIFIED) | **YES, from a stale local cache** | Current input: `app/data/cfbd_cache/` (810 files). New isolated destination is ready under `app/data/sources/cfbd_foundation/` | Raw-to-curated runner built and preflighted; **not executed and NOTHING scheduled** | Engine A college features still read the May cache | **2026-05-24** — intentionally unchanged tonight |
| **PFF** | **PAID** | **BY HAND ONLY** | `app/data/pff_exports/`: **149 distinct paid payloads / 7 report families / 2017–2025**, content-deduplicated from 307 downloads; private, gitignored, required-backup-covered | **NOTHING automatic** — David exports by hand; master inventory maps every download by SHA-256 | `scripts/build_college_features.py` reads the active NCAA receiving-summary manifest; all other newly organized families are **NOBODY yet** pending Layer-2 candidate validation | **2026-08-01** — NCAA REGPO + NFL REG baselines complete for summaries, passing pressure/depth, and receiving scheme/depth (named scope/coverage exceptions retained separately) |
| **PlayerProfiler** | **PAID** | **YES — ALL FIVE streams, layer 1 COMPLETE for this source 2026-08-01** | `app/data/playerprofiler.db` (gitignored, and **in backup `required`** on David's word): `pp_player_season` 5,476×317 · `pp_medical_history` 9,768 · `pp_roster_week` 230,394 · `pp_identity_bridge` 3,290 · `pp_gamelog_week` 44,462 · `pp_pbp_play` 280,868 · `pp_pbp_slot` 949,041 | **NOTHING automatic, and none is possible** — there is no API; David exports by hand, then one command per stream ingests | **NOBODY yet** — layer-1 substrate; the curated consumer is the open work | **2026-08-01** (player-seasons 2017–2025 · roster + gamelog 2020–2025 · medical 2017–**2023**, see the blind window) |
| **FantasyPros** | **PAID** (David's list) | **HISTORICAL ONLY** | `app/data/fc_snapshots.db`, source `dp_archive`: 2,185 rows on four dates | One manual archive load; **NOTHING current** | Backtest/trust-surface code | Local load **2026-05-30**; newest source date **2024-09-08** |
| **Footballguys** | **PAID — UNVERIFIED** (David named it 07-25; he added the URL again 22:21 tonight) | **NO** | nowhere | **NOTHING** | **NOBODY** — its *ideas* are cited in 16 strategy docs; its *data* was never ingested | **never** |
| **MyFantasyLeague (MFL)** — rookie ADP | Free public export API | **NO** (adapter exists, fixture-backed) | no production store | **NOTHING** | NOBODY outside adapter/tests | **never** |
| **RAS — ras.football** | Free | **NO** — fixture-backed only | `tests/fixtures/` | **NOTHING** | Risk-flag context | fixture, static |
| **RotoViz** | **UNVERIFIED** (likely paid) | **NO** | nowhere | **NOTHING** | **NOBODY** — declared in the registry, no fetch code exists | **never** |
| **Campus2Canton** | **UNVERIFIED** | **NO** | nowhere | **NOTHING** | **NOBODY** — declared in the registry, no fetch code exists | **never** |
| **KeepTradeCut (KTC)** | Free | **NO** | nowhere live | **NOTHING** | NOBODY — and by constitution it may never enter a model | **UNVERIFIED** |
| **NFL Next Gen Stats** | Free (David named it as public data) | **YES** | `app/data/sources/nfl_nextgen_stats/`: immutable raw Parquet plus one curated table | Manual runnable capture; **NOTHING scheduled** | Stable curated loader exists; **NOBODY in the product/model yet** | **2026-07-30 23:00 ET** — 26,723 rows, 2016–2025 |
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

1. **Current data from the remaining paid subscriptions.** FantasyPros has historical data but no
   current feed; Footballguys has nothing. CFBD's cache and PFF's manual files are about two months
   old. PlayerProfiler is now current through 2025 — but see the medical blind window below.
2. **Live college production.** CFBD is cache-only, so Engine A trains on a static May snapshot.
3. **Seven other free nflreadpy datasets remain unwired.** Next Gen Stats is now ingested; FF
   opportunity, rankings, PFR advanced stats, FTN charting, contracts, injuries, and depth charts
   still have zero callers.
4. **League history beyond transactions** — drafts, standings, matchups, weekly lineups across the
   four seasons. Sleeper serves all of it; we call none of it.
5. **A live market source other than FantasyCalc.** KTC is named everywhere and ingested nowhere.
6. **Anything that would answer "is a manager still the same person"** — solved tonight inside the
   transaction chain, not available anywhere else.

## Three things the table says that are worth saying out loud

1. **PlayerProfiler is ingested but still consumed by nothing.** The six columns the registry has
   declared since it was written (`breakout_age`, `speed_score`, `target_share` and their
   `source_*` twins) now EXIST in `pp_player_season`. No model reads them. Ingestion closed the
   layer-1 hole and closed nothing else.
   - **Identity is name-based and the numbers are stated, not implied.** PlayerProfiler's
     data-analysis export ships no id of any kind. Player-seasons resolve **98.3% canonical
     (5,385/5,476), 8 conflicts HELD, 83 unknown**. The medical stream carries PlayerProfiler's own
     `Player_ID`, but it is unusable as a join key — absent from the other export, 18 rows read
     `#N/A`, and one id maps to three different players — so both streams join on the resolved
     canonical id. Every ambiguity is held as `conflict`; nothing is guessed.
   - **The Weekly Roster Key changed the identity story.** From 2023 PlayerProfiler's
     `player_id` **is a GSIS id** — the canonical key we already use. Identity for those
     seasons is not matched, it is *given*: 110,169 of 230,394 roster rows (47.8%) are
     vendor-supplied. A further 39.9% are inferred by bridging PlayerProfiler's pre-2023
     internal ids across its 2022/2023 re-platform. The two are kept in separate
     `identity_basis` values so an inference can never be read as a fact.
   - **PlayerProfiler's internal id is NOT unique to a human, and this bit us.** It is
     initials-plus-a-number, so `AS-2100` is Andre Smith the LB *and* Andre Smith the OT;
     `AW-1812` is Andrew Wingard *and* ArDarius Washington. **13 such ids.** A first cut of
     the roster adapter keyed on the id and silently deleted one real player per collision,
     and confidently bridged 94 of them to a single canonical id. Colliding ids now carry a
     `source_id_collision` status and are never resolved. The inverse lesson is worth
     stating: **the vendor's id is more stable than the vendor's name** — Matt/Matthew
     Judon, Mike/Michael Badgley and Robby Anderson → Robbie Chosen are all one player.
   - **The Advanced Gamelog's null token changed meaning mid-archive.** 2020 writes `0`;
     2021+ writes the literal `NA` (435,537 of them in the 2021 file alone). Three column
     renames looked broken until that was accounted for. **But `NA` does not uniformly mean
     zero:** `snap_share` is `NA` only where snaps are zero, while
     `yards_created_receiving` is `NA` on 3,178 rows with no receptions *and* 3,802 rows
     that had receptions. Zero-filling the latter would invent 3,802 measurements. The
     adapter stores `NA` as NULL and publishes a measured per-column verdict — **3 columns
     safe to zero-fill, 18 never, 111 unclassified (treated as unsafe).**
   - **A second blind window: the 2025 Gamelog dropped all nine man/zone coverage columns.**
     `routes_vs_man`, `targets_vs_zone`, `separation_at_target`, `target_accuracy` and
     friends exist 2021–2024 only. Absent is not zero; an average over 2021–2025 would
     divide a four-season sum by five. Recorded in `column_availability`.
   - **Advanced PBP is three datasets, not one, and the seams cost information both times.**
     This stream names *which player filled which role* on each snap, and PlayerProfiler
     changed that vocabulary twice. 2020 charts five receiver positions and NAMES the slot
     receiver (`wr1 wr2 slot1 slot2 wr5`). **2021 did not renumber them, it DROPPED two** —
     the surviving indices are the discontinuous `receiver1`, `receiver2`, `receiver5`,
     and 2020's `slot1`/`slot2` are exactly the absent 3 and 4. **The slot receiver is
     unavailable from 2021 on.** Then 2023 removed the role entirely: `skill1..skill5` are
     anonymous, so every 2023+ slot row carries `slot_role_known = False` and any positional
     reading of them is an inference, not the vendor's word. A consumer counting receivers
     per play across these seams would read a vendor coverage change as a change in NFL
     personnel usage.
   - **THE MEDICAL BLIND WINDOW — 2024, 2025 and 2026 have NO injury data.** PlayerProfiler's
     archive stops at 2023 (David, 2026-07-31). The danger is specific: a naive join renders "no
     record" identically to "was healthy", which is not missing data but a confident wrong answer.
     The archive is **training and backtesting only — NOT decision-grade for current players.** The
     boundary is machine-readable in the status marker (`medical_blind_window`), not just prose.
2. **Two jobs run onto content that has not moved in five weeks** — the FC-snapshot agent and the
   What-Changed agent are both installed and firing. Their outputs are dated 2026-06-24.
3. **The registry is wrong in both directions.** It lists 19 sources. Four of them (Sportradar,
   Genius Sports, Stats Perform, Rolling Insights) were never contracted and have no code. It omits
   sources the product leans on daily — general nflreadpy, Sleeper CDN, the DynastyProcess archive,
   and, until tonight, transactions.
