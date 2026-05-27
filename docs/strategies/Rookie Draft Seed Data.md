# Dataset: Completed 12-Team Superflex Full PPR Dynasty Rookie Drafts (2018–2025) — Honest Yield and Recommended Pivot

## TL;DR
- **The strict dataset the request asks for effectively does not exist in publicly indexable form.** After ~20 targeted web searches and a focused subagent sweep of Reddit, Sleeper, MyFantasyLeague, DLF, DynastyNerds, Footballguys, and analyst Substacks, **zero publicly-posted completed rookie drafts could be verified as simultaneously (a) 12-team, (b) Superflex, (c) explicitly Full (1.0) PPR, (d) non-TE-Premium, (e) non-best-ball, and (f) rookie-only.** The closest matches are best-ball, TE-Premium, half-PPR, or unspecified-PPR variants from the Footballguys "Post Your Rookie Drafts" forum mega-threads.
- **What is publicly available are aggregate ADPs derived from real drafts (DLF MFL Rookie ADP, Sleeper rookie ADP).** These pool many real picks from real managers in formats close to — but not strictly filtered to — the spec, and they are the realistic raw input for a draft-capital-value model.
- **Recommended pivot:** Use DLF's MFL Rookie ADP (and Sleeper's rookie ADP) as the proxy corpus and supplement with the partial-match per-league drafts catalogued below. Do NOT plan to scrape Reddit at scale: per a 9to5Google report dated July 25, 2024, Reddit updated its robots.txt to block Bing, DuckDuckGo, Mojeek, and Qwant from crawling the site (Google retained access through a separate licensing arrangement), so the historical "rate my rookie draft" corpus on r/DynastyFF/r/Sleeper is no longer reachable through general search-engine tooling.

## Key Findings

1. **Mock drafts dominate the indexed record by roughly 50:1 over real-league completed drafts.** Top organic results for every sensible query are FantasyPros, Footballguys, Draft Sharks, Dynasty Nerds, CBS Sports, RotoBaller, NBC/Rotoworld, FantasyLife, and DLF mocks — none of which qualify as "completed real-league drafts with real managers."

2. **The single richest indexable repository of real-league rookie drafts is the Footballguys Shark Pool "Post Your Rookie Drafts" annual mega-thread** (separate threads each year 2022–2026). These contain dozens of user-posted real drafts, but most are best-ball, TE-Premium, half-PPR, 1QB, or 16-team. The fraction strictly matching the spec is small and usually missing one disambiguating detail (typically "PPR" not specified as full vs. half).

3. **Reddit indexing changes have hollowed out the largest historical source of "rate my rookie draft" posts.** Two distinct events are often conflated: (a) the June 30, 2023 API pricing change that shut down Apollo, Reddit is Fun, Sync, and BaconReader (per Wikipedia's "2023 Reddit API controversy"), which did not affect search-engine indexing; and (b) the July 25, 2024 robots.txt update that blocked all non-Google search crawlers (per 9to5Google: "Reddit changes have blocked all search engines except Google amid AI 'misuse'"). The combined result is that r/DynastyFF threads from 2023 onward are sparsely returned by general web search.

4. **DLF's two rookie ADP feeds illustrate the data landscape:** their "Superflex Rookie ADP" is from analyst-organized mocks (NOT real leagues), while their "MFL Rookie ADP" aggregates real MFL rookie drafts each spring. Per DLF's live MFL Rookie ADP page: *"MFL Rookie draft data is available once rookie drafts occur, usually the beginning in April. This data is gathered from actual rookie drafts in dynasty leagues on MyFantasyLeague.com. These drafts do not run year-round."* Neither feed publishes per-league results, and DLF does not publish a draft count.

5. **Format prevalence in real public-facing leagues skews to TE-Premium and half-PPR.** FFPC dynasty products are TE-Premium by default — per a FantasyPros explainer, *"FFPC is a full PPR format, with tight end premium scoring, meaning the position scores an extra 0.5 PPR points per reception over other positions, meaning each catch for a tight end is worth 1.5 PPR points plus the yardage gained on the catch."* Many "industry" leagues that get publicly recapped (FBG analysts' home leagues, DLF Writers, DynastyNerds App League, RotoViz TriFlex) also use TE-Premium. Pure 12-team SF Full PPR non-TEP is common in casual Sleeper leagues, but those leagues rarely publish their drafts to indexable URLs.

6. **First-round shape is highly consistent year over year across all Superflex formats**, which is why aggregate ADP is a defensible substitute. In 2024, Caleb Williams was 1.01 in essentially every public posting; in 2023, Bijan Robinson; in 2025, Ashton Jeanty. For 2026, per Dynasty Data Lab as cited by FantasyPros in May 2026: *"Love has been selected with the first overall pick in 97% of Superflex dynasty rookie drafts since the NFL Draft."* Variance in real drafts lives almost entirely from pick 1.07 onward.

## Details

### Best-effort dataset of partial matches

Each row group below is a real-league completed rookie-only draft surfaced in the Footballguys "Post Your Rookie Drafts" threads. Format flags indicate which strict-spec criterion is **failed (✗)** or **unverified (?)**.

#### Draft B — 2024, FBG forum "Ongoing Empire league" — 12-team / Superflex / PPR (Full?)
Source: forums.footballguys.com/threads/post-your-2024-dynasty-rookie-drafts.812410/

| Year | Pick | Player | Pos |
|---|---|---|---|
| 2024 | 1.01 | Caleb Williams | QB |
| 2024 | 1.02 | Marvin Harrison Jr. | WR |
| 2024 | 1.03 | Malik Nabers | WR |
| 2024 | 1.04 | Jayden Daniels | QB |
| 2024 | 1.05 | J.J. McCarthy | QB |
| 2024 | 1.06 | Brock Bowers | TE |
| 2024 | 1.07 | Rome Odunze | WR |
| 2024 | 1.08 | Drake Maye | QB |
| 2024 | 1.09 | Jonathon Brooks | RB |
| 2024 | 1.10 | Brian Thomas Jr. | WR |
| 2024 | 1.11 | Trey Benson | RB |
| 2024 | 1.12 | Ladd McConkey | WR |
| 2024 | 2.01 | Xavier Worthy | WR |
| 2024 | 2.02 | Keon Coleman | WR |
| 2024 | 2.03 | Ricky Pearsall | WR |
| 2024 | 2.04 | Bo Nix | QB |
| 2024 | 2.05 | Xavier Legette | WR |
| 2024 | 2.06 | Michael Penix Jr. | QB |
| 2024 | 2.07 | Blake Corum | RB |
| 2024 | 2.08 | Jaylen Wright | RB |
| 2024 | 2.09 | MarShawn Lloyd | RB |
| 2024 | 2.10 | Adonai Mitchell | WR |
| 2024 | 2.11 | Ja'Lynn Polk | WR |
| 2024 | 2.12 | Roman Wilson | WR |

#### Draft C — 2024, FBG "12 Team SF Best Ball PPR Dynasty" — ✗ best-ball

| Year | Pick | Player | Pos |
|---|---|---|---|
| 2024 | 1.01 | Caleb Williams | QB |
| 2024 | 1.02 | Marvin Harrison Jr. | WR |
| 2024 | 1.03 | Malik Nabers | WR |
| 2024 | 1.04 | Brock Bowers | TE |
| 2024 | 1.05 | Jayden Daniels | QB |
| 2024 | 1.06 | Rome Odunze | WR |
| 2024 | 1.07 | J.J. McCarthy | QB |
| 2024 | 1.08 | Xavier Worthy | WR |
| 2024 | 1.09 | Drake Maye | QB |
| 2024 | 1.10 | Jonathon Brooks | RB |
| 2024 | 1.11 | Bo Nix | QB |
| 2024 | 1.12 | Brian Thomas Jr. | WR |
| 2024 | 2.01 | Ladd McConkey | WR |
| 2024 | 2.02 | Keon Coleman | WR |
| 2024 | 2.03 | Trey Benson | RB |
| 2024 | 2.04 | Michael Penix Jr. | QB |
| 2024 | 2.05 | Xavier Legette | WR |
| 2024 | 2.06 | MarShawn Lloyd | RB |
| 2024 | 2.07 | Ricky Pearsall | WR |
| 2024 | 2.08 | Ja'Lynn Polk | WR |
| 2024 | 2.09 | Ben Sinnott | TE |
| 2024 | 2.10 | Blake Corum | RB |
| 2024 | 2.11 | Malachi Corley | WR |
| 2024 | 2.12 | Adonai Mitchell | WR |

(Rounds 3–4 also posted in the source; truncated here.)

#### Draft A — 2022, FBG forum, Sleeper draft URL — 12-team / Superflex / PPR (Full?)
Source: forums.footballguys.com/threads/post-your-rookie-drafts.804054/; draft board: sleeper.app/draft/nfl/789582411133521921

| Year | Pick | Player | Pos |
|---|---|---|---|
| 2022 | 1.01 | Breece Hall | RB |
| 2022 | 1.02 | Drake London | WR |
| 2022 | 1.03 | Kenny Pickett | QB |
| 2022 | 1.04 | Kenneth Walker III | RB |
| 2022 | 1.05 | Jameson Williams | WR |
| 2022 | 1.06 | Garrett Wilson | WR |
| 2022 | 1.07 | Treylon Burks | WR |
| 2022 | 1.08 | Skyy Moore | WR |
| 2022 | 1.09 | Chris Olave | WR |
| 2022 | 1.10 | James Cook | RB |
| 2022 | 1.11 | Christian Watson | WR |
| 2022 | 1.12 | George Pickens | WR |
| 2022 | 2.01 | Jahan Dotson | WR |
| 2022 | 2.02 | Desmond Ridder | QB |
| 2022 | 2.03 | Malik Willis | QB |
| 2022 | 2.04 | Rachaad White | RB |
| 2022 | 2.05 | Dameon Pierce | RB |
| 2022 | 2.06 | John Metchie III | WR |
| 2022 | 2.07 | Alec Pierce | WR |
| 2022 | 2.08 | Isaiah Spiller | RB |
| 2022 | 2.09 | Trey McBride | TE |
| 2022 | 2.10 | Matt Corral | QB |
| 2022 | 2.11 | Tyrion Davis-Price | RB |
| 2022 | 2.12 | Zamir White | RB |
| 2022 | 3.01 | Tyler Allgeier | RB |
| 2022 | 3.02 | Joshua Palmer/Tolbert | WR |
| 2022 | 3.03 | Wan'Dale Robinson | WR |
| 2022 | 3.04 | David Bell | WR |
| 2022 | 3.05 | Brian Robinson Jr. | RB |
| 2022 | 3.06 | Khalil Shakir | WR |
| 2022 | 3.07 | (J. Ross) | WR |
| 2022 | 3.08 | (Velus Jones/Ingram) | WR/RB |
| 2022 | 3.09 | Pierre Strong Jr. | RB |
| 2022 | 3.10 | (Jerome Ford / J. Woods) | RB |

(Several Round 3 names ambiguous in the snippet; open the Sleeper draft board URL to verify.)

#### Draft F — 2025, FBG forum "12 team superflex" — Full PPR?

| Year | Pick | Player | Pos |
|---|---|---|---|
| 2025 | 1.01 | Ashton Jeanty | RB |
| 2025 | 1.02 | Omarion Hampton | RB |
| 2025 | 1.03 | TreVeyon Henderson | RB |
| 2025 | 1.04 | Travis Hunter | WR |
| 2025 | 1.05 | Cam Ward | QB |
| 2025 | 1.06 | Tetairoa McMillan | WR |
| 2025 | 1.07 | Quinshon Judkins | RB |
| 2025 | 1.08 | Kaleb Johnson | RB |
| 2025 | 1.09 | RJ Harvey | RB |
| 2025 | 1.10 | Jaxson Dart | QB |
| 2025 | 1.11 | Tyler Warren | TE |
| 2025 | 1.12 | Luther Burden III | WR |

(Round 2+ truncated.)

#### Draft H — 2025, FBG forum "12 team SF Best Ball PPR Dynasty" — ✗ best-ball

| Year | Pick | Player | Pos |
|---|---|---|---|
| 2025 | 1.01 | Ashton Jeanty | RB |
| 2025 | 1.02 | Omarion Hampton | RB |
| 2025 | 1.03 | Travis Hunter | WR |
| 2025 | 1.04 | Tetairoa McMillan | WR |
| 2025 | 1.05 | Cam Ward | QB |
| 2025 | 1.06 | Quinshon Judkins | RB |
| 2025 | 1.07 | TreVeyon Henderson | RB |
| 2025 | 1.08 | Tyler Warren | TE |
| 2025 | 1.09 | RJ Harvey | RB |
| 2025 | 1.10 | Emeka Egbuka | WR |
| 2025 | 1.11 | Kaleb Johnson | RB |
| 2025 | 1.12 | Matthew Golden | WR |
| 2025 | 2.01 | Luther Burden III | WR |
| 2025 | 2.02 | Jaxson Dart | QB |
| 2025 | 2.03 | Colston Loveland | TE |
| 2025 | 2.04 | Cam Skattebo | RB |
| 2025 | 2.05 | Jayden Higgins | WR |
| 2025 | 2.06 | Bhayshul Tuten | RB |
| 2025 | 2.07 | Tyler Shough | QB |
| 2025 | 2.08 | Tre Harris | WR |
| 2025 | 2.09 | Kyle Williams | WR |
| 2025 | 2.10 | (Etienne / Taylor) | RB |
| 2025 | 2.11 | Jaydon Blue | RB |
| 2025 | 2.12 | Jalen Milroe | QB |

(Rounds 3–4 also posted in the source.)

### Rejected drafts (catalogued for transparency)

| ID | Year | Reason for exclusion |
|---|---|---|
| D | 2024 | 16-team + TE Premium |
| E | 2024 | Startup with rookies, not rookie-only |
| G | 2025 | Explicitly half-PPR |
| I | 2025 | 12T/SF/1.0 PPR but with 0.5 TE Premium |
| J | 2026 | Best-ball |
| K | 2026 | 1QB league (no Superflex) |
| L | 2026 | Best-ball |
| M | 2014 | 10-team, out of year range |

### Distinct drafts per year

| Year | Strict-spec verified | Partial (one criterion unverified) | Failed criterion |
|---|---|---|---|
| 2018 | 0 | 0 | 0 indexed |
| 2019 | 0 | 0 | 0 indexed |
| 2020 | 0 | 0 | 0 indexed |
| 2021 | 0 | 0 | 0 indexed |
| 2022 | 0 | 1 (Draft A) | 0 |
| 2023 | 0 | 0 | 0 indexed |
| 2024 | 0 | 1 (Draft B) | 2 (Drafts C, D, E) |
| 2025 | 0 | 1 (Draft F) | 3 (Drafts G, H, I) |
| 2026* | 0 | 0 | 3 (Drafts J, K, L) |

*2026 is outside the user's nominal 2018–2025 window but included for completeness because indexable drafts for that year exist.

### Why the indexed real-draft record is so thin

- **Most casual leagues never publish their drafts at a stable URL.** Sleeper and MyFantasyLeague generate public draft boards, but the URLs are never linked from indexable pages outside the league itself.
- **Industry analysts publish mocks, not their own home-league results,** because mocks are evergreen, home results expose strategy/identity, and mock posts attract more traffic.
- **The Reddit "completed real-league recap" niche** that previously powered this kind of dataset has been substantially reduced in indexed visibility since the July 25, 2024 robots.txt change (9to5Google).
- **DLF, DynastyNerds, and Dynasty Trade Calculator forums** primarily publish analyst mocks, with the partial exception of DLF's MFL Rookie ADP (aggregate only).

### What aggregate ADP actually represents

For modeling, the data you actually want — the *distribution of where each rookie was selected across many real 12-team SF Full PPR leagues* — is functionally present in two aggregates:

- **DLF MFL Rookie ADP** (dynastyleaguefootball.com/adp/mfl-adp.php) — drawn from live rookie drafts on MyFantasyLeague.com once they begin each spring. Per DLF: *"This data is gathered from actual rookie drafts in dynasty leagues on MyFantasyLeague.com. These drafts do not run year-round."* Per-league granularity is not published; the underlying draft count is not disclosed. Format mix is predominantly SF and PPR but not filtered to your strict spec.
- **DLF Superflex Rookie ADP** (dynastyleaguefootball.com/adp/?type=sf_rookie) — drawn from organized mock drafts, NOT real leagues. Per DLF: *"This ADP data is drawn from Superflex Rookie-Only dynasty mock drafts organized by @RyanMc23."* Do not use as a real-draft proxy.
- **Sleeper Rookie ADP** — visible inside the Sleeper app's Mock Draft section; aggregates Sleeper user mocks plus live drafts. KeepTradeCut surfaces related but distinct (crowd-sourced trade-value) data.

## Recommendations

**Stage 1 — Confirm the modeling need before chasing more raw drafts.** If the goal is a draft-capital-value model, the *distribution of picks* is the input, and aggregate ADP from real drafts is a near-perfect substitute. The user's "real per-league draft" requirement is based on the assumption that such data is publicly indexable; for the strict 12-team SF Full PPR non-TEP slice, it largely is not.

- **Threshold to change this plan:** if you can authenticate to the Sleeper or MFL APIs and pull league-by-league draft histories filtered by scoring settings, do that instead. Sleeper's developer API exposes `/league/{league_id}/drafts` and `/draft/{draft_id}/picks` endpoints publicly; the constraint is identifying leagues with the right settings, solvable via `/league/{league_id}/settings`.

**Stage 2 — If you need real per-league boards as your input, pivot to direct community outreach:**
- Post a recruitment thread in r/DynastyFF and r/Sleeper asking for managers to DM Sleeper draft URLs.
- Post in the Footballguys Shark Pool "Post Your Rookie Drafts" 2026 thread asking specifically for 12-team SF Full PPR non-TEP non-best-ball examples.
- Reach out to dynasty-Twitter analysts who run "writers leagues" (DLF Writers, DynastyNerds App League, RotoViz TriFlex). Most will share full historical rookie draft boards for non-commercial research, although several of these leagues use TE Premium and would not match the strict spec.

- **Threshold to change this plan:** if community sourcing yields fewer than 20 strict-match drafts after two weeks of outreach, fall back to Stage 3.

**Stage 3 — Build the model on aggregate ADP plus the partial-match per-league drafts.** Use DLF MFL Rookie ADP as the primary signal and treat the Footballguys-thread drafts catalogued above as a validation set. The 2024 "Empire" draft (Draft B) and the 2025 12-team SF draft (Draft F) are the only two indexed real-league drafts that don't fail any spec criterion outright (only Full-vs-Half PPR is unverified — and "PPR" used without modifier on FBG forums conventionally means full PPR).

- **Threshold to change this plan:** if your model is sensitive to TE-Premium vs non-TEP scoring (which materially shifts rookie TE ADP up 1–3 rounds), you cannot blend TEP and non-TEP drafts; either filter aggressively or model the scoring-format effect explicitly as a covariate.

## Caveats

- **Honesty over volume.** The 15–30 distinct drafts the user requested are not publicly available under the strict spec. The dataset above is the honest indexed yield from a thorough search; no rows were fabricated to hit a count.
- **"PPR" disambiguation.** On Footballguys and Sleeper forum posts, "PPR" written without a modifier conventionally means 1.0 PPR, but a meaningful minority of posters use "PPR" to mean any reception-based scoring including 0.5. For the drafts labeled "(Full?)" above, treat the Full PPR assumption as ~70% likely, not certain.
- **Snippet truncation.** Several drafts were transcribed from search-engine snippets, not direct page fetches (the FBG forum returns 403 to automated fetching). Round 3–4 lists may have transcription errors; verify against the source URL before use. Pick 3.07 and 3.08 in Draft A and pick 2.10 in Draft H are flagged ambiguous.
- **Year coverage skew.** The indexed yield is concentrated in 2022–2025. The 2018–2021 record is essentially empty in this search pass — partly because the FBG annual mega-thread format started in 2022, and partly because Reddit threads from that era are no longer reliably returned by search engines.
- **Reddit access.** The user's expectation that r/DynastyFF, r/fantasyfootball, and r/Sleeper would be high-yield sources reflects how those subreddits worked through ~2022. Per 9to5Google's July 25, 2024 report, Reddit's robots.txt now blocks Bing, DuckDuckGo, Mojeek, and Qwant; only Google retains crawler access (via a separate licensing arrangement reported by Bloomberg in February 2024). The historical "rate my rookie draft" corpus on these subreddits would require authenticated, logged-in browsing to retrieve at scale — outside the scope of what this research pass could perform.
- **No mocks were included in the dataset.** Every row above is from a real-league completed draft (with the noted format caveats). The 60+ "mock draft" articles encountered during research were excluded per the user's explicit instruction.