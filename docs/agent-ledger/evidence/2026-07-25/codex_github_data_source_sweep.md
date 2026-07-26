# Dynasty Genius GitHub / open-data source sweep

**Date:** 2026-07-25
**Mode:** research and proposal only; no ingestion, dependency change, code change, commit, or wire action
**Evidence vocabulary:** **VERIFIED** = primary repository, release, package documentation, workflow, or local locator; **ARGUED** = judgment from verified facts; **UNKNOWN** = evidence does not establish the claim, with the settling evidence named.

## Binding verdict

**VERIFIED — the highest-value result is not a new dependency.** Dynasty Genius already declares `nflreadpy` (`requirements.txt:12`) and already has a governed adapter surface (`src/dynasty_genius/adapters/nflreadpy_qb_adapter.py`). The maintained `nflverse-data` releases exposed through that package can supply:

- player game/season outcomes from 1999 onward;
- player identities, birth dates, draft facts, and season rosters;
- weekly rosters back to 2002, including reserve/PUP/retired/free-agent status;
- game-level offensive snap counts from 2012 onward;
- play-level participation from 2016 onward, including players on the play and a `route` field;
- weekly aggregate Next Gen Stats from 2016 onward;
- official weekly injury/practice reports from 2009 through 2024.

This source family can materially close four gaps established today: **no season-by-season outcome history, no player-seasons at ages 30+, no career-length/attrition panel, and no snap/route data**. It cannot honestly close current injury history after 2024, and its 2023+ participation data is postseason-only rather than an in-season feed.

**VERIFIED — DynastyProcess is the strongest newly identified historical market-adjacent source.** `dynastyprocess/data` contains weekly FantasyPros ECR, transformed 1QB/2QB player values, and rookie-pick ECR exports. Git history contains **347 revisions** of `files/values-players.csv` from 2019-04-07 through 2026-07-24. This can replace “four annual snapshots” with a weekly expert-consensus history, but it must be labeled correctly: it is **expert consensus, not completed-trade market history**.

**VERIFIED — the DynastyProcess transform is confirmed, with one boundary.** The public calculator code defaults `value_factor=235`, then computes:

`round(10500 * exp(-(235 / 10000) * ECR))`

so the default is exactly `round(10500 × exp(-0.0235 × ECR))`. Current public rows reproduce it: Ja'Marr Chase has `ecr_2qb=6.1` and `value_2qb=9098`, which is the rounded result. The public values-building workflow runs weekly on Friday and invokes private `build_pickecr.R`, `build_playerecr.R`, and `build_values.R` scripts. Therefore the formula is **VERIFIED against public calculator source and current exports**, while the complete export-generation implementation remains **UNKNOWN/private**.

**VERIFIED — public Next Gen Stats means aggregate stats, not the full tracking feed.** nflverse publishes weekly passing, rushing, and receiving NGS aggregates from 2016 onward and updates them nightly in season. Full player-tracking frames are not a general public longitudinal dataset. Big Data Bowl provides episodic competition slices under competition-specific rules; the official GitHub repository retains only one 2017 game and has no detected license.

**ARGUED — the honest acquisition order is smaller than “add every popular package.”**

1. Use the already-declared `nflreadpy` access path to snapshot selected nflverse release data.
2. Treat CC-BY-SA participation/FTN data as a separately governed source family.
3. Evaluate DynastyProcess weekly history as a second, explicitly expert-derived overlay.
4. Use manual PFF export for current-season route data if David’s subscription and PFF terms permit it.
5. Do not add R packages or stale Python wrappers merely to reach APIs the repository already calls directly.

## License discipline

### What the licenses mean here

- **MIT:** permissive code license. Keep copyright/license notice with copied substantial code. It does **not** license data returned by third-party APIs.
- **CC0-1.0:** public-domain dedication/fallback license; no attribution/share-alike requirement, though source provenance remains product law.
- **CC-BY-4.0:** reuse and adaptation permitted with attribution, license link, and change indication. No share-alike.
- **CC-BY-SA-4.0:** same attribution duties plus adaptations must be shared under the same or a compatible license when distributed. This is materially different from CC-BY and should not be mixed silently into a redistributable training corpus.
- **GPL-3.0 / GPL >=3 code:** using or modifying GPL program code and distributing the resulting program can impose corresponding-source/copyleft obligations. Merely reading exported data does not automatically make our code GPL, but `dynastyprocess/data` applies GPL-3.0 at repository level and does not publish a separate data license. Any committed copy or distributed derived dataset needs an explicit license decision.
- **No license / NOASSERTION:** GitHub visibility is not permission. Do not copy, automate, ingest, or derive from it unless the owner supplies a license or written permission.

**VERIFIED caveat:** `nflreadr` says its code is MIT, while NFL data belong to their respective owners and are governed by owner terms. `nflreadpy` says most nflverse data are CC-BY-4.0, with FTN data CC-BY-SA-4.0. The central data repository itself is CC-BY-4.0. The narrow, defensible posture is to honor both the stated nflverse license and source-specific attribution/terms; the CC license does not erase third-party trademarks or rights nflverse cannot grant.

## Ranked candidates

### 1. `nflverse/nflverse-data` — **VERY HIGH**

- **Capability / data — VERIFIED:** central automated release store for play-by-play, player/team stats, rosters, weekly rosters, players, snap counts, participation, NGS, injuries, depth charts, draft picks, PFR advanced stats, FTN charting, contracts, schedules, and trades.
- **Exact license — VERIFIED:** repository data license `CC-BY-4.0`; documented exception for FTN-derived data is `CC-BY-SA-4.0`.
- **Maintenance — VERIFIED:** repository commit [`b976b422ce4b`](https://github.com/nflverse/nflverse-data/commit/b976b422ce4b0b95e96f223dadca073ba6808afe) on 2026-07-01. Release assets are the real freshness surface: schedules updated 2026-07-25; weekly rosters/players updated 2026-07-25; player/team stats updated 2026-07-10; snaps 2026-02-09; participation 2026-02-10; NGS 2026-02-28; injuries 2026-03-18.
- **Published cadence — VERIFIED:** PBP/player stats nightly after game days; rosters daily 07:00 UTC; snaps four times daily in season; NGS nightly in season; FTN charting four times daily; participation 2023+ only after postseason; injury source dead after 2024.
- **Consume — VERIFIED:** existing `nflreadpy` package, or pinned release URLs in parquet/CSV. No new dependency needed.
- **Gaps filled — VERIFIED/ARGUED:** season outcomes; age-30+ seasons; raw material for career survival/attrition; snaps; historical routes/participation; historical injuries; identity crosswalk.
- **Limits — VERIFIED:** not an immutable point-in-time archive by default; release assets are updated in place. A raw snapshot with URL, fetch time, content hash, data vintage, and license/attribution is required by our architecture.
- **Verdict:** first source to scope. The value is in selected governed datasets, not wholesale mirroring.

Relevant primary locators:

- [Repository and CC-BY-4.0 license](https://github.com/nflverse/nflverse-data)
- [Release families](https://github.com/nflverse/nflverse-data/releases)
- [Automation schedule](https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html)
- [CC-BY-4.0 license text](https://github.com/nflverse/nflverse-data/blob/main/LICENSE.md)

### 2. `nflverse/nflreadpy` — **VERY HIGH access path; LOW as new data**

- **Capability — VERIFIED:** maintained Python/Polars loader for the central releases. It exposes PBP, player stats, rosters, weekly rosters, players, snaps, NGS, FTN charting, participation, draft picks, injuries, contracts, depth charts, FantasyPros rankings, IDs, and ffopportunity data.
- **Exact license — VERIFIED:** MIT code. Data licenses remain source-specific.
- **Maintenance — VERIFIED:** latest release [`v0.1.5`](https://github.com/nflverse/nflreadpy/releases/tag/v0.1.5), 2025-11-19; latest default-branch commit [`66bb305e634b`](https://github.com/nflverse/nflreadpy/commit/66bb305e634ba815466749249d07b5c6e9268db3), 2025-11-23. nflverse still names it as the Python access path in 2026 documentation.
- **Consume — VERIFIED:** already declared at `requirements.txt:12`; existing source registry and adapters already use it.
- **Gaps filled:** none by itself; it is the least-friction route to candidate 1.
- **Verdict:** use the existing dependency and adapter law. Do not introduce a parallel downloader.

### 3. `dynastyprocess/data` — **HIGH**

- **Capability / data — VERIFIED:** weekly `db_fpecr`, `values.csv`, `values-players.csv`, `values-picks.csv`, and `db_playerids`. Current player export contains `ecr_1qb`, `ecr_2qb`, position ECR, transformed values, and scrape date. Pick export contains exact-pick 1QB/2QB ECR plus high/low models.
- **Exact license — VERIFIED:** GPL-3.0 at repository level; no separate data license was found.
- **Maintenance — VERIFIED:** latest commit [`21dd49b54cec`](https://github.com/dynastyprocess/data/commit/21dd49b54cecd6211af4a4365fc4473f0d033d34), 2026-07-24. Workflow cron `23 2 * * 5` = weekly Friday build.
- **History — VERIFIED:** 347 file revisions from 2019-04-07 through 2026-07-24 for `values-players.csv`.
- **Consume — VERIFIED:** current raw/parquet export for latest; GitHub commit blobs for point-in-time reconstruction. No package dependency required.
- **Gap filled — VERIFIED:** expands historical market-adjacent observations from four annual snapshots to weekly expert-consensus snapshots; provides an independent 2QB pick/player comparator and broad identity bridge.
- **Semantic limit — VERIFIED:** source is FantasyPros expert consensus transformed to a value scale. It is not trade-derived FantasyCalc and must never be merged under an unlabeled “market value.”
- **License limit — ARGUED:** a research-only remote snapshot is lower risk than copying transform code or committing exported/derived tables. Before durable ingestion, settle whether DynastyProcess will grant a data-specific permissive license or whether our internal-only use/attribution posture is sufficient.
- **Verdict:** highest-value new comparator, but isolate its license and semantics.

Primary locators:

- [Repository and weekly-data description](https://github.com/dynastyprocess/data)
- [Weekly values workflow](https://github.com/dynastyprocess/data/blob/master/.github/workflows/weekly-playervalues.yml)
- [Current player exports](https://github.com/dynastyprocess/data/tree/master/files)
- [Current pick export](https://raw.githubusercontent.com/dynastyprocess/data/master/files/values-picks.csv)

### 4. `ffverse/ffopportunity` — **HIGH for usage quality; MEDIUM overall**

- **Capability / data — VERIFIED:** precomputed expected fantasy points/yards/touchdowns built from nflverse PBP with XGBoost; weekly and play-level tables. Model was trained on public 2006–2020 PBP and current data releases are generated on game windows.
- **Exact license — VERIFIED:** code `GPL (>=3)`; models and expected-points data `CC-BY-SA-4.0`.
- **Maintenance — VERIFIED:** code commit [`74dcb35a112a`](https://github.com/ffverse/ffopportunity/commit/74dcb35a112a71e5349b36abe940316067ec4fec), 2025-12-11; `latest-data` assets updated through 2026-02-10. Scheduled after TNF, Sunday windows, SNF, and MNF in season.
- **Consume — VERIFIED:** existing `nflreadpy.load_ff_opportunity()` or release CSV/parquet; do not import GPL R code.
- **Gap filled — ARGUED:** adds season-by-season opportunity quality and a more stable usage target than realized touchdowns/points. It complements snaps/routes but does not replace either.
- **Obligation:** adapted/distributed datasets must preserve CC-BY-SA attribution/share-alike.
- **Verdict:** valuable secondary feature/research lane after the base longitudinal panel; keep in its own licensed dataset family.

### 5. `dynastyprocess/data-mfl_public` — **MEDIUM**

- **Capability / data — VERIFIED:** public MFL league settings, drafts, standings, weekly starters, and all public transactions for SafeLeagues 2019–2020 and Scott Fish Bowl 2016–2020. The repo documents 1,838 SafeLeagues records and league fields including dynasty/redraft, 2QB/SF, roster size, best ball, and scoring flags.
- **Exact license — VERIFIED:** CC0-1.0.
- **Maintenance — VERIFIED:** last commit [`9b8f37152036`](https://github.com/dynastyprocess/data-mfl_public/commit/9b8f37152036b44b1a5baeb35f70482b1d3369f8), 2021-07-31; stale and closed-period.
- **Consume:** parquet data release/clone or manual download; no runtime package needed.
- **Gap filled — ARGUED:** historical trade/add/drop behavior and roster-setting variation. It can help study how roster depth and SF/TEP settings affect transactions; it does not provide a player value index.
- **Verdict:** good CC0 research benchmark, not a current market feed.

### 6. `dynastyprocess/apps-calculator` — **MEDIUM as transparent benchmark code**

- **Capability — VERIFIED:** public R implementation of player/pick value transform, exact-pick and future-pick construction, league-size labeling, QB mode, rookie optimism, and future-pick factors.
- **Exact license — VERIFIED:** GPL-3.0.
- **Maintenance — VERIFIED:** latest substantive package changes 2026-04-30 (version 3.1.7); monthly heartbeat commits through [`1a33cc410a4b`](https://github.com/dynastyprocess/apps-calculator/commit/1a33cc410a4b712fb07e43b77e321d5812e958cd), 2026-07-01.
- **Consume:** read as a benchmark specification; do not copy GPL code into Dynasty Genius. Independent reimplementation would still require provenance and an exact semantic spec.
- **Gap filled:** confirms/corrects the DynastyProcess value and pick construction for benchmark interpretation.
- **Formula — VERIFIED:** default `value_factor=235`; `_calculate_value` uses `round(10500 * exp(-(value_factor/10000) * ecr))`.
- **Important correction:** `0.0235` is the default, not a mathematical constant of the platform; the UI exposes `value_factor`.
- **Verdict:** methodology reference, not a dependency.

### 7. `nflverse/ngs-data` plus `nflverse-data/nextgen_stats` — **MEDIUM-HIGH**

- **Capability — VERIFIED:** scraper/workflows for public NFL NGS weekly passing, rushing, and receiving aggregates; outputs are published in central release assets. NGS fields include receiving separation/cushion/air-yard measures, rushing efficiency/time-to-LOS/RYOE, and passing time-to-throw/completion-probability measures.
- **Exact license — VERIFIED:** `ngs-data` code MIT; central release data generally CC-BY-4.0 with attribution to NFL Next Gen Stats via nflverse.
- **Maintenance — VERIFIED:** producer commit [`5e47314baeaf`](https://github.com/nflverse/ngs-data/commit/5e47314baeaf4a1342a8a6da0007ec61486c7f12), 2026-04-30; release assets updated 2026-02-28; nightly in season.
- **Consume:** `nflreadpy.load_nextgen_stats()`; no new wrapper.
- **Gap filled — ARGUED:** better efficiency/context and historical aggregates from 2016 onward. It does **not** provide route participation for every player, snaps, or full tracking coordinates.
- **Coverage limit — VERIFIED:** NGS only publishes players above minimum attempt/target thresholds, so it is selection-biased for fringe players.
- **Verdict:** valuable enrichment after base outcomes, not the longitudinal foundation.

### 8. `nflverse/nflreadr` — **MEDIUM as documentation; LOW as dependency**

- **Capability — VERIFIED:** R loader, caching, release URL logic, and authoritative data dictionaries/schedules.
- **Exact license — VERIFIED:** MIT code.
- **Maintenance — VERIFIED:** release [`v1.5.1`](https://github.com/nflverse/nflreadr/releases/tag/v1.5.1) and commit [`9a866381a387`](https://github.com/nflverse/nflreadr/commit/9a866381a3875823468e81535f81709e07a08941), 2026-04-20.
- **Consume:** documentation/data dictionaries only; Python production should stay on existing `nflreadpy`.
- **Gap filled:** no unique data beyond candidate 1.
- **Verdict:** authoritative schema/cadence reference, redundant runtime dependency.

### 9. `nflverse/nflfastR` — **MEDIUM research; LOW immediate**

- **Capability — VERIFIED:** cleans raw NFL PBP and applies EPA/WPA/completion-probability models; can reconstruct precomputed nflverse outputs and supports raw data within roughly 15 minutes after a game.
- **Exact license — VERIFIED:** MIT code.
- **Maintenance — VERIFIED:** release [`v5.2.0`](https://github.com/nflverse/nflfastR/releases/tag/v5.2.0), 2026-02-07; commit [`0489133d85c5`](https://github.com/nflverse/nflfastR/commit/0489133d85c5f11682572d9436c4a7b371a789aa), 2026-03-25.
- **Consume:** methodology/reference or R one-off validation; normally consume precomputed central releases.
- **Gap filled:** reproducibility and custom PBP features, not a missing dataset.
- **Verdict:** popular and excellent, but adding it would not itself close today’s gaps.

### 10. `ffverse/ffscrapr` — **LOW-MEDIUM**

- **Capability — VERIFIED:** R clients for MFL, Sleeper, Fleaflicker, and ESPN with authentication, rate limiting, caching, and tidy league data.
- **Exact license — VERIFIED:** MIT code; platform/API data governed by provider terms.
- **Maintenance — VERIFIED:** version 1.4.8.20 in `DESCRIPTION`; commit [`b6990181e125`](https://github.com/ffverse/ffscrapr/commit/b6990181e125507a1b4642cea6bc9778d9acd6f3), 2024-11-01. GitHub’s latest release tag is a 2023 test tag, not a reliable current package release.
- **Consume:** R package/manual research only.
- **Gap filled:** multi-platform league data access; no new player outcomes, route, attrition, or market history.
- **Verdict:** useful ecosystem tool, but redundant for Dynasty Genius’s direct Sleeper adapter and Python stack.

### 11. `ffverse/ffhistorian` — **LOW-MEDIUM**

- **Capability — VERIFIED:** new R wrapper over ffscrapr to traverse Sleeper/ESPN/MFL/Fleaflicker league history.
- **Exact license — VERIFIED:** MIT code; upstream API terms govern data.
- **Maintenance — VERIFIED:** commit [`9464eab654fa`](https://github.com/ffverse/ffhistorian/commit/9464eab654fa4e1172c7178a3bcb67343560d57a), 2026-01-02; only five commits and no release.
- **Consume:** reference for traversal patterns, not a dependency.
- **Gap filled — ARGUED:** could help verify David’s league-history traversal, but it creates no data not available from Sleeper and does not address player career outcomes.
- **Verdict:** monitor, do not adopt now.

### 12. `ffverse/ffsimulator` — **LOW**

- **Capability — VERIFIED:** simulates fantasy league seasons from rosters, schedules, projections, and scoring.
- **Exact license — VERIFIED:** MIT code.
- **Maintenance — VERIFIED:** release [`v1.2.2`](https://github.com/ffverse/ffsimulator/releases/tag/v1.2.2), 2023-01-09; commit [`9d8bc79354ed`](https://github.com/ffverse/ffsimulator/commit/9d8bc79354ed79bd9f9ac028c3f3442b271afea5), 2024-10-03.
- **Consume:** R package for separate simulation research if ever authorized.
- **Gap filled:** none of the five current data gaps.
- **Verdict:** popular-adjacent but currently useless to this mandate.

### 13. `nflverse/nfl_data_py` — **REJECT**

- **Capability:** former Python loader for nflverse data.
- **Exact license:** MIT.
- **Maintenance — VERIFIED:** archived; final commit [`79600f3b29d5`](https://github.com/nflverse/nfl_data_py/commit/79600f3b29d524ec718abd2d545d89cbc3176c2c), 2025-09-25, explicitly says no further maintenance and directs users to nflreadpy. Last release `v0.3.3`, 2024-09-20.
- **Consume:** do not.
- **Gap filled:** none beyond existing nflreadpy.
- **Verdict:** named in older documentation, but obsolete for us.

### 14. `nflverse/nflverse-pff` — **MANUAL-EXPORT REFERENCE ONLY**

- **Capability — VERIFIED:** MIT-licensed R ingest code for PFF exports; it publishes no PFF dataset.
- **Exact license:** MIT for code; **PFF data license/terms are separate and not granted by this repo**.
- **Maintenance — VERIFIED:** five commits; latest [`6d4bac147336`](https://github.com/nflverse/nflverse-pff/commit/6d4bac14733679c5f5f14ad2f1db3477dee9f168), 2024-09-19.
- **Consume:** David-authorized manual export under his PFF access, then existing governed manual-ingest contract. Do not scrape or assume MIT applies to exported PFF data.
- **Gap filled:** current-season routes, route participation, YPRR, and richer usage if included in David’s licensed export.
- **Verdict:** manual export is the honest path for the current-season route hole.

### 15. `nfl-football-ops/Big-Data-Bowl` and Kaggle competitions — **RESEARCH-ONLY / MANUAL TERMS GATE**

- **Capability — VERIFIED:** official repo retains one 2017 game of tracking data plus schema/tutorial. Annual Kaggle competitions expose selected NGS tracking slices for particular questions and seasons.
- **Exact license:** official GitHub repo has **NOASSERTION/no license**. Kaggle competition data use competition-specific rules; notebook licenses do not license the underlying competition data.
- **Maintenance:** official repo commit [`9ad0b4b2ea36`](https://github.com/nfl-football-ops/Big-Data-Bowl/commit/9ad0b4b2ea36697e29e44e2399512cc1ce70358c), 2019-04-29. The competition continues annually, but each dataset is a separate gated artifact.
- **Consume:** manual Kaggle export only after David accepts the exact competition rules and we record the permitted use; never treat a participant’s CC-licensed notebook as a license to the NFL data.
- **Gap filled:** limited tracking-method research, not longitudinal production routes/snaps/career outcomes.
- **Verdict:** useful for research prototypes, unsuitable as the primary data floor.

### 16. `nflverse/open-source-football` — **REFERENCE ONLY UNTIL LICENSED**

- **Capability — VERIFIED:** transparent football analytics articles/code, including Ben Baldwin’s NFL draft value chart with on-field and second-contract/surplus-value constructions and a 1–256 CSV.
- **Exact license:** **NOASSERTION/no repository license found**.
- **Maintenance:** latest commit [`38b79545fee2`](https://github.com/nflverse/open-source-football/commit/38b79545fee2b83e114cbd38eba6474ce093dfd6), 2025-05-14.
- **Consume:** read methodology and independently specify a benchmark from licensed inputs; do not copy code or CSV without permission.
- **Gap filled:** draft-pick benchmark research, but it values NFL draft capital/non-QBs and is not a dynasty rookie-pick curve.
- **Verdict:** valuable idea source, legally unusable as a copied dataset today.

### 17. `nflverse/nfldata` — **USEFUL CONTENT, LICENSE BLOCKED**

- **Capability — VERIFIED:** highly maintained draft picks, draft trades, schedules, team mappings, and `draft_values.csv` with Stuart, Jimmy Johnson, and Rich Hill charts.
- **Exact license:** **NOASSERTION/no license found**.
- **Maintenance:** latest automated commit [`d61f16d971a5`](https://github.com/nflverse/nfldata/commit/d61f16d971a575a0b06316036e6516b9e2fbd6c1), 2026-07-25.
- **Consume:** do not ingest directly until an explicit license is added or nflverse confirms the central CC-BY license covers these files.
- **Gap filled:** NFL draft-pick benchmark curves and trade behavior, not dynasty rookie outcomes.
- **Verdict:** popular and current, but license uncertainty blocks use.

### 18. Sleeper Python wrappers — **REJECT AS DEPENDENCIES**

`SwapnikKatkoori/sleeper-api-wrapper`:

- MIT; latest default-branch commit [`9451b3dde5a8`](https://github.com/SwapnikKatkoori/sleeper-api-wrapper/commit/9451b3dde5a88e3d67ae84d2379caaa1941bff26), 2022-03-04.
- Stale and adds no data beyond the direct free Sleeper API.

`cameron-eth/sleeper-sdk`:

- Active commit [`a9b76e1e3c84`](https://github.com/cameron-eth/sleeper-sdk/commit/a9b76e1e3c8403f8e3caf3b12f71e071e48dc4f5), 2026-07-24, but **NOASSERTION/no license**.
- Its repository includes a KTC snapshot workflow; KeepTradeCut use is prohibited here.

**Verdict:** retain the existing direct Sleeper adapter. A wrapper would add dependency and semantic risk without expanding data coverage.

## What the nflverse streams actually solve

### Season-by-season outcomes and age 30+

**VERIFIED:**

- `load_player_stats(..., summary_level="reg")` returns player-season summaries and game/weekly data; underlying PBP/stat history starts in 1999.
- `load_rosters()` goes back to 1920 and includes birth date, experience, position, GSIS/PFR/PFF/Sleeper IDs, and status.
- `load_players()` publishes mostly immutable identity, DOB, draft year/round/pick, and cross-source IDs.

**ARGUED:** joining player-season stats to DOB gives the missing age-30+ panel immediately. It also gives Years 1, 5+, and complete veteran tails that the current prospect outcome table cannot supply.

### Career length, survival, and attrition

**VERIFIED:**

- Weekly rosters go back to 2002.
- Roster-status vocabulary includes ACT, INA, PUP, RES, RET, CUT, UFA, and related reserve/release states.
- Player stats identify actual games/seasons with production.

**ARGUED:** a season-level at-risk panel can define:

- exposure: on an NFL roster or producing in season *t*;
- event candidates: RET/CUT/UFA plus no later active roster/production;
- temporary absence: PUP/RES/INA with later return;
- censoring: last available data season or unresolved identity.

This is far more honest than treating “missing next season” as retirement. It still requires a pre-registered event definition and identity/coverage audit; nflverse does not publish a ready-made “career ended” truth label.

### Snaps and routes

**VERIFIED:**

- PFR game-level snap counts begin in 2012 and include offensive snaps and offensive percentage.
- Participation begins in 2016 and exposes `players_on_play`, offense/defense player lists, and `route`.
- Participation through 2022 is attributed to NFL NGS. From 2023 onward it is FTN, CC-BY-SA-4.0, and only published after the postseason.

**ARGUED:** historical route counts/participation can be derived by player/game/season from the play-level rows, with audit checks against offensive snaps and pass plays. It does not provide an in-season 2026 route feed. PFF manual export is the honest current-season supplement.

### Injury and IR history

**VERIFIED:**

- Injury/practice reports are available from 2009 through 2024.
- The nflverse schedule says the source died after 2024; no 2025 data and no ETA.
- Weekly rosters include PUP/RES/INA/status descriptions back to 2002.

**ARGUED:** combine official injury reports (injury type/status) through 2024 with roster-status episodes (reserve/PUP duration) for a historical panel. For 2025 onward, distinguish:

- roster-status-derived IR/PUP episodes — available;
- named injury body part/severity — unavailable unless captured from another authorized source;
- current injury feed — manual/provider-specific solution required.

No repository found supplies a maintained, permissively licensed, complete post-2024 NFL injury/IR history.

## Market-value time series

### What is genuinely available

1. **FantasyCalc:** trade-derived current/forward snapshots already captured by Dynasty Genius; no licensed GitHub repository with a historical FantasyCalc series was found.
2. **DynastyProcess:** 347 weekly historical expert-consensus revisions since 2019; values are exponential transforms of FantasyPros ECR.
3. **MFL public data:** 2016–2020 transaction records under CC0; raw behavior, not a market-value index.
4. **FantasyCalc ADP:** completed-draft behavior through the provider API, not a GitHub history.

**ARGUED:** the correct historical comparison design keeps three lanes separate:

- accepted-trade price (FantasyCalc);
- expert consensus (DynastyProcess/FantasyPros);
- observed transactions/drafts (MFL public / FantasyCalc ADP).

Calling all three “market value” would erase what each measures.

### What was not found

- No licensed, maintained GitHub history of FantasyCalc player values.
- No permitted KeepTradeCut history. KTC is prohibited and excluded even if a scraper repository exists.
- No credible permissively licensed alternative with weekly dynasty trade-derived prices.

**UNKNOWN:** FantasyCalc may maintain private historical endpoints or archives. Only provider documentation or written provider confirmation would settle that.

## NFL Next Gen Stats: public boundary

**VERIFIED public:**

- weekly player-level passing, rushing, and receiving aggregates since 2016;
- season summaries (`week == 0`);
- nightly in-season refresh through nflverse;
- selected full tracking datasets released for Big Data Bowl competitions.

**VERIFIED not public as a general open longitudinal feed:**

- full tracking coordinates for every game/season;
- unrestricted current route/tracking data through an official documented API.

**ARGUED:** use nflverse NGS aggregates automatically under the documented attribution contract. Use Big Data Bowl only as a manually accepted, competition-specific research artifact. If an NFL UI exposes a metric not in nflverse, manual export after terms review is more honest than inventing a scraper.

## Draft-pick value research

### Usable now

- **DynastyProcess pick ECR/value export:** current exact rookie-pick 1QB/2QB expert consensus, weekly; GPL repository license caveat.
- **DynastyProcess calculator code:** transparent exponential value and future-pick heuristics; GPL, reference only.
- **Our incumbent realized-outcome curve:** internal governed comparator.

### Reference-only until license clears

- **Open Source Football draft chart:** second-contract/surplus and on-field curves; no repo license.
- **nfldata draft values:** Stuart/Johnson/Hill NFL charts; no repo license.

**ARGUED:** NFL draft-pick charts are useful falsifiers for shape/monotonicity but do not answer dynasty rookie-pick value. They price NFL draft capital or team trade behavior, not a 12-team Superflex rookie slot.

## Popular but not useful

- **nflfastR:** excellent, but precomputed nflverse releases already supply its main outputs.
- **nflreadr:** authoritative docs/R loader, redundant runtime.
- **ffsimulator:** solves season simulation, not the data floor.
- **Sleeper wrappers:** no additional data; direct API already exists.
- **Big Data Bowl notebooks/repos:** modeling examples around narrow competition slices, not a longitudinal dataset.
- **recent zero-star “NFL aging curve” / “survival” repos:** no verified license, validation, or maintenance record. The licensed nflverse raw panel is a stronger foundation.

## Explicit reject / do-not-use list

- **KeepTradeCut and any KTC scraper/snapshot repository:** prohibited by standing rule.
- **`G-Sher/dynasty-daddy`:** KTC-dependent and no detected license.
- **`cameron-eth/sleeper-sdk`:** no license and includes KTC snapshot automation.
- **`nflverse/nfldata`:** no license, despite valuable/current files.
- **`nflverse/open-source-football`:** no license; methodology reading only.
- **`nflverse/nflverse-data-archives`:** quarterly redundancy but no detected license; do not assume inheritance from `nflverse-data`.
- **official Big Data Bowl GitHub data:** no detected license; manual/terms-gated only.
- **random injury, survival, or dynasty scraper repositories without a license:** not usable merely because code/data are public on GitHub.

## Where manual export is the honest path

1. **PFF current-season routes/route participation/YPRR:** David-authenticated export, if his subscription and PFF terms permit the exact use. Preserve the raw export, export timestamp, settings/filter context, source hash, and manual-review manifest. Do not scrape.
2. **Kaggle Big Data Bowl tracking slices:** manual acceptance of the exact competition rules, followed by a recorded data-use decision. Useful for bounded research only.
3. **NFL UI-only NGS metrics absent from nflverse:** manual export only after terms review; otherwise mark unavailable.
4. **Any provider whose public API omits a needed historical endpoint:** ask the provider or use a manual export; do not reverse-engineer around explicit access limits.

Manual export is **not** needed for nflverse releases, DynastyProcess public files, public MFL data, or Sleeper’s documented unauthenticated league endpoints.

## Minimum proposal worth taking forward

This is not an implementation plan. It is the smallest source portfolio that survives the sweep.

### Lane A — longitudinal NFL panel

- Source: `nflverse-data` through existing `nflreadpy`.
- Datasets: players, season-level player stats, weekly rosters, snap counts.
- Optional isolated datasets: participation/FTN (CC-BY-SA), NGS, historical injuries.
- Proof required later: season coverage, age distribution including 30+, identity join rate, attrition/censoring table, and source/license manifest.

### Lane B — market/expert history

- Source: `dynastyprocess/data` Git history.
- Dataset: weekly `values-players` and `values-picks`, stored/labeled as FantasyPros-ECR-derived.
- Proof required later: historical commit sampling, exact transform reproduction, settings/2QB field pin, identity coverage, and license decision.

### Lane C — current-season route bridge

- Source: PFF manual export, if authorized; otherwise no current route claim.
- Proof required later: terms/export provenance, schema, season/week completeness, identity join, and comparison with postseason nflverse participation when it becomes available.

### What should not be one step

**ARGUED:** do not combine base CC-BY nflverse data, CC-BY-SA FTN/ffopportunity data, GPL-repository DynastyProcess exports, and manual PFF data into one first ingestion. They have different legal obligations, freshness boundaries, and failure modes. The safe sequence is:

1. base nflverse CC-BY longitudinal panel;
2. separate share-alike participation lane;
3. separate market/expert overlay;
4. manual proprietary export lane.

That preserves the architecture’s one-adapter-per-source rule and keeps license obligations observable.

## Unknowns that must remain unknown

1. **DynastyProcess export code:** private build scripts are not public. Settle with published source or maintainer explanation.
2. **DynastyProcess data-specific license:** repo says GPL-3.0, not a separate open-data license. Settle with maintainer clarification or legal review.
3. **FantasyCalc pre-2026 history:** no public licensed GitHub archive found. Settle with provider documentation/API confirmation.
4. **Post-2024 detailed injury feed:** no maintained permissive source found. Settle with a new authorized provider/manual export.
5. **Big Data Bowl downstream rights:** dataset-specific competition rules must be read after account/rules access; notebook licenses are insufficient.
6. **PFF export rights:** settle against David’s subscription terms and the exact export type before durable ingestion.

## Evidence index

- nflverse data inventory and schedules: [nflreadr data schedule](https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html)
- player stats: [load_player_stats](https://nflreadr.nflverse.com/reference/load_player_stats.html)
- season rosters: [load_rosters](https://nflreadr.nflverse.com/reference/load_rosters.html)
- weekly rosters: [load_rosters_weekly](https://nflreadr.nflverse.com/reference/load_rosters_weekly.html)
- roster status meanings: [roster-status dictionary](https://nflreadr.nflverse.com/articles/dictionary_roster_status.html)
- players/IDs/DOB/draft fields: [load_players](https://nflreadr.nflverse.com/reference/load_players.html)
- snaps: [load_snap_counts](https://nflreadr.nflverse.com/reference/load_snap_counts.html)
- participation/routes and share-alike terms: [load_participation](https://nflreadr.nflverse.com/reference/load_participation.html)
- NGS: [load_nextgen_stats](https://nflreadr.nflverse.com/reference/load_nextgen_stats.html)
- injuries and historical floor: [load_injuries](https://nflreadr.nflverse.com/reference/load_injuries.html)
- nflreadpy functions/license/data-license note: [nflreadpy README](https://github.com/nflverse/nflreadpy)
- DynastyProcess data/cadence: [dynastyprocess/data](https://github.com/dynastyprocess/data)
- DynastyProcess transform: [apps-calculator `R/values.R`](https://github.com/dynastyprocess/apps-calculator/blob/master/R/values.R)
- MFL public data/CC0: [data-mfl_public](https://github.com/dynastyprocess/data-mfl_public)
- ffopportunity model/data: [ffopportunity](https://github.com/ffverse/ffopportunity)
- official Big Data Bowl boundary: [NFL repository](https://github.com/nfl-football-ops/Big-Data-Bowl) and [NFL Football Operations description](https://operations.nfl.com/programs-initiatives/innovation/big-data-bowl)

## Final recommendation

**ARGUED:** David’s mandate is justified, but the answer is not a dependency shopping spree. The first serious proposal should exploit the maintained, licensed data already reachable through `nflreadpy`, because that is enough to build the missing longitudinal player-season and career-risk floor. Add DynastyProcess only as a separately labeled expert-consensus history, not as “the market.” Treat current routes and post-2024 injury detail as honest manual/unknown gaps rather than filling them with unlicensed scrapers.

Nothing in this sweep changes the status of the QB rushing hypothesis: it remains **UNDER TEST**, the registered study has not run, and no result is asserted here.
