# Fantasy App Data Display Research - Codex Independent Lane

Date: 2026-07-06
Status: independent Codex research brief, uncommitted
Scope: player rankings first, then league views, player cards, matchups, trade UIs, waivers, draft rooms, mobile
Anti-anchoring: written before reading Claude or Gemini research drafts

## Executive Read

The category teaches one blunt lesson: fantasy football UIs are row-first products. Even the richer tools are anchored by ranked rows, compact player identity, position/team metadata, one focal value, sortable context columns, freshness language, and fast filters. The best surfaces then add three things around that row: tiers to expose drop-offs, trend/market movement to show time, and a player card/inspector for evidence depth.

Dynasty Genius has been trying to look like a governed model report. The category standard looks like an asset terminal: ranks, rows, cards, league comparisons, trade lanes, add/drop workflows, draft queues, and mobile-scannable summaries. DG should keep its constitutional honesty, but the visible grammar should become fantasy-native.

## Source Notes

- KTC dynasty rankings expose a dense rankings table with controls for Superflex, PPR, TE premium, position filters, freshness copy, player/pick rows, tier, 30-day trend, and value. Source: [KeepTradeCut dynasty rankings](https://keeptradecut.com/dynasty-rankings).
- KTC trade calculator uses two trade lanes, league-setting toggles, total pieces, side totals, copy/clear actions, recent real trades, quick facts, 30-day riser/faller callouts, value dispersion, and six-month value span. Source: [KeepTradeCut trade calculator](https://keeptradecut.com/trade-calculator).
- FantasyPros rankings/cheatsheets expose the standard expert-consensus frame: scoring selector, view selector, expert picker, latest ECR, draft mode, and position tabs. Source: [FantasyPros dynasty rankings](https://www.fantasypros.com/nfl/rankings/dynasty-overall.php) and [FantasyPros consensus cheat sheets](https://www.fantasypros.com/nfl/rankings/consensus-cheatsheets.php).
- Public FantasyPros app imagery shows a Playbook dashboard with roster headshots, positional power ranks, team/league analysis, injury/news updates, and bottom navigation for Feed, Drafts, Rankings, and More. Source: [FantasyPros app screenshot page](https://mwm.ai/apps/fantasypros-fantasy-advice/1141119371).
- Sleeper markets itself around in-app chat, drafting, trade block/interest, league customization, roster/start percentages, player transaction history, FAAB/WAB, live drafts, rookie-only draft, weekly league reports, and tablet support. Source: [Sleeper fantasy football](https://sleeper.com/fantasy-football).
- Sleeper app screenshots show the Players tab split into Search, Trend, Available, Leaders, and Trade, with position chips, season-projection sorting, player rows, watchlist/star controls, and bottom chat/transaction affordances. Source: [Sleeper app redesign image result](https://sleeper.com/blog/sleepers-app-redesign-whats-new/).
- Sleeper trade-center screenshots show side-by-side league rosters with avatars, position/team labels, trade-block color panels, hearts for interest, and horizontal/vertical scrolling for roster comparison. Source: [Sleeper trading experience](https://sleeper.com/blog/welcome-to-a-whole-new-trading-experience/).
- Yahoo's 2024 redesign was framed around three mobile sections: fantasy teams, News, and Scores; The Verge reports Yahoo wanted managers to see the whole team on one screen and keep news, lineup changes, and box scores together. Source: [The Verge on Yahoo Fantasy redesign](https://www.theverge.com/2024/8/5/24206843/yahoo-fantasy-football-sports-app-redesign).
- Yahoo waiver screenshots show add/drop as a two-section workflow: add candidate on top, drop candidates below, stat columns, projections selector, lock/status icons, and a persistent Add & drop action. Source: [Yahoo waiver screenshot article](https://sports.yahoo.com/how-do-waivers-work-waiver-wire-adds-drops-210520661.html).
- NFL Fantasy rankings expose position/week filters and a simple Rank / Player / Opp / expert rank table. Projections expose search, position/week filters, paginated rows, stat-category columns, and a Points column. Sources: [NFL Fantasy rankings](https://fantasy.nfl.com/research/rankings) and [NFL Fantasy projections](https://fantasy.nfl.com/research/projections).
- NFL Fantasy home blends analysis, start/sit content, waiver wire links, videos, news, and draft entry points into one hub. Source: [NFL Fantasy home](https://fantasy.nfl.com/).
- Dynasty Nerds tools page exposes the dynasty-specific surface set: trade calculator, combine tracker, depth charts, Nerd Score, dynasty rankings, film room, data hub, rookie guide, roster rescue, mock draft sim, league analyzer, lineup optimizer, league sync, trade browser, team portfolio, rookie draft pick tracker, and custom/contender rankings. Source: [Dynasty Nerds tools](https://www.dynastynerds.com/dynasty-tools/).
- Dynasty Nerds rankings expose the plain dynasty row pattern: Rank, Player, Team, Pos, Dynasty Value. Source: [Dynasty Nerds dynasty rankings](https://www.dynastynerds.com/dynasty-rankings/).
- PFF grades explain the advanced-data pattern: each play is graded, facets split player performance into passing/rushing/receiving/blocking/rush defense/coverage, grades convert to 0-100, and PFF+ supports sorting by grade, team/position filtering, advanced stats, matchup charts, snap counts, and pre-snap position tables. Source: [PFF player grades](https://www.pff.com/grades).
- PFF draft-guide imagery shows an advanced player card: rank range, ADP, position rank chip, age/height/weight/bye, floor/median/ceiling projection line, expert mini-ranks, analyst text, player photo, and dark-card visual treatment. Source: [PFF fantasy draft guide image result](https://www.pff.com/news/fantasy-football-draft-guide-is-live-2022).
- DraftKings' NFL DFS product is salary-cap lineup creation with daily/season-long/in-game contests and private contests; its public copy emphasizes drafting within a salary cap and watching points accumulate. Source: [DraftKings fantasy football](https://www.draftkings.com/fantasy-football).
- DraftKings lineup screenshots show Create Lineup with entry fee, start time, countdown, roster-fill count, submit action, player headshots, position/name/team/matchup/time, salary, FPPG, opponent rank, and remove controls. Source: [DraftKings lineup image result](https://www.draftkings.com/fantasy-football).
- Underdog's current product page emphasizes a mobile-first sports entry flow: picks/teams, state toggles by product, Drafts/Best Ball, app download, feed-like promotional cards, and large-payout microcopy. Source: [Underdog Fantasy](https://www.underdogfantasy.com/).

## Player Rankings First: Row Anatomy

The category's standard ranking row has a stable grammar:

- Rank number: always left edge, usually the dominant ordering cue.
- Player identity: headshot or compact avatar, name, team, position, and sometimes age/bye/opponent.
- Position rank chip: QB1/RB12/WR6, sometimes more important than overall rank because managers scan positional scarcity.
- One focal value: KTC `VALUE`, Dynasty Nerds `Dynasty Value`, NFL projected points, DraftKings salary/FPPG, PFF median projection, FantasyPros ECR.
- Secondary context: age, opponent, bye, projected points, best/worst/average expert rank, injury tags, roster/start percentages, ADP, salary, or 30-day trend.
- Sort/filter controls: position chips, scoring toggles, Superflex/PPR/TEP toggles, week selectors, expert/source selectors, and search.
- Freshness/basis copy: KTC says values updated minutes ago; FantasyPros explains latest-update freshness; NFL ranks by week; PFF explains grade basis.

DG translation:

- Every rankings row should have `rank`, `PlayerIdentity`, `position rank`, `model value percentile`, `xVAR` or PVO focal number, `market overlay` if available, `trend`, and `receipt`.
- "Tier" should be a visual divider/band, not a vague badge, unless backed by the David-ratified lexicon. KTC shows why tier numbers work: they are scannable and reveal drop-offs without storytelling.
- The row should not begin with caveats. Caveats belong inline as small receipt/status tokens and expand in the inspector.
- A rank without basis is a defect. The table header must say what the ranking is sorted by.

## Tier Visualization

Observed patterns:

- KTC uses numeric tiers in the table, letting the tier read as a market segmentation column rather than prose.
- Dynasty Nerds mostly uses continuous value, which makes drop-offs visible only if the user mentally compares values.
- FantasyPros uses ECR and expert ranges; the best/worst/average pattern creates an implicit uncertainty band.
- PFF uses floor/median/ceiling inside the player card, which is stronger than a static tier when uncertainty matters.

DG translation:

- Rankings should use horizontal tier dividers or shaded row groups keyed to calibrated thresholds.
- The band label can be terse: `Tier 4`, `95-99 pct`, `straddles threshold`, `stale label suppressed`.
- Use spread bars for model-vs-market distance and value ranges; avoid green/red verdict coloring.
- Tier transitions are more important than tier names. The screen should visually answer: where is the cliff between this player and the next cluster?

## Trend Indicators

Observed patterns:

- KTC has a dedicated `30DT` and `30 DAY TREND` beside current value.
- KTC trade calculator includes 30-day riser/faller and six-month value span.
- Sleeper exposes `Trend`, `Leaders`, `Available`, and roster/start percentages.
- Yahoo and NFL place timing around weekly cadence: waiver day, matchup week, game time, projected vs actual.
- DraftKings makes time pressure visible: contest start, countdown, roster-fill count.

DG translation:

- DG should separate model movement from market movement: model-blue trend, market-amber trend, no blended color.
- The daily-open view should be a tape of changed rows, not a set of report cards.
- Trend needs both direction and basis: `market +214 since last capture`, `model unchanged`, `stale market`, `new role caveat`.
- Avoid urgency language. Time can be shown without telling David to act.

## Density

Observed patterns:

- FantasyPros and NFL use dense tables for rankings/projections.
- Yahoo explicitly redesigned around seeing a whole team on one mobile screen.
- KTC rankings show hundreds of rows with compact values, positions, ages, tiers, and trends.
- DraftKings lineup builder shows many rostered slots in a single scroll, with salary and FPPG on each row.
- Sleeper uses a dense player-list mode and a more visual card-like trade block mode.

DG translation:

- Dense is correct. A 32px row target is fantasy-native, not "too much."
- Use one dominant row value plus narrow secondary columns; push long prose into inspector/receipts.
- Mobile rows should not be mini reports. They should be two-line rows: identity + focal value line, then compact context line.
- Desktop should support a split view: rankings table left, player/league inspector right.

## Color And Position Systems

Observed patterns:

- Sleeper and Dynasty-adjacent tools use categorical color blocks/chips for positions and trade-block state.
- FantasyPros uses blue/white sports-app clarity with player headshots and colored position chips.
- DraftKings uses salary/OPRK/FPPG with rank colors, but its domain is DFS and wagering-adjacent.
- KTC's table relies more on value/tier/trend columns than heavy color.
- PFF dark-card treatment uses accent lines and high-contrast projection ranges.

DG translation:

- DG can use position hues more boldly than it has, but only as category markers.
- Model blue and market amber remain the lane axes; do not reuse them for position chips.
- No green/red verdict language. If a source uses red/green for good/bad, translate to neutral signed deltas, range bars, or lane-colored movement.
- Trade blocks and watchlists can use structural treatments: outline, fill, icon, or list placement. Hue alone is not enough.

## Headshots And Team Identity

Observed patterns:

- FantasyPros, Yahoo, ESPN screenshots, DraftKings, and PFF all use player headshots in high-frequency rows/cards.
- KTC web rankings are more text/value heavy but link player names and team abbreviations.
- Sleeper uses avatars/team icons heavily at league level and player rows with team metadata.
- Dynasty Nerds rankings page is sparse but the app/tool marketing emphasizes the app and league sync.

DG translation:

- Headshots are not decoration in this category. They are row-recognition infrastructure.
- DG should self-host Sleeper headshots or a governed equivalent, with fallback initials/silhouettes.
- Team identity should be lightweight: team abbreviation and small color mark, not NFL-brand imitation.
- Player identity should include position rank and team context in the row, because dynasty decisions are roster and league-context decisions.

## League Views

Observed patterns:

- Yahoo starts with a list of all fantasy teams and wants managers to move between team, news, and scores.
- Sleeper centers league chat, league reports, transaction history, trade block, and all-team trade comparison.
- Dynasty Nerds League Analyzer promises roster breakdowns, positional strengths, and trade partner identification.
- Public Dynasty Scout imagery shows league rankings sortable by total value/starters/PPG and filters for positions/picks.
- KTC has league power rankings and trade database adjacent to rankings.

DG translation:

- DG's league view should be a franchise-equity table, not a generic dashboard.
- Rows should be teams, columns should be model value, market value, starters, bench, picks, positional pressure, roster capacity, and freshness.
- League partner fit should be displayed as evidence rows, not target recommendations.
- The league screen should answer: where is the league imbalanced, where is David exposed, and where do model/market pictures diverge?

## Player Cards

Observed patterns:

- PFF's draft-guide card is the strongest advanced template: player image, rank/range, position chip, biographical context, ADP, floor/median/ceiling, expert mini-ranks, and analyst explanation.
- FantasyPros app card/dashboard combines player headshots with rank badges, matchup, news, and positional rank.
- Yahoo add/drop rows include player headshots, team/position, projected stats, game time, and lock/status.
- KTC player links support hover/tap info from rankings.

DG translation:

- DG needs a right-side player inspector for every player row.
- First viewport: identity, model percentile, xVAR, market value, model-market delta, age/curve state, role/freshness caveats.
- Second layer: drivers, counter-argument, projection range, source receipts, trend history, comparable cohorts.
- Do not make the card an article. It is an evidence object.

## Matchups

Observed patterns:

- ESPN/Yahoo/NFL are weekly-matchup products: opponent, rank, projection, score, game time, and injury status are always close to lineup rows.
- NFL projections expose opponent and stat projections by week.
- PFF includes head-to-head matchup charts in PFF+.
- DFS apps expose opponent rank and salary efficiency at the player-row level.

DG translation:

- Dynasty Genius is not a start/sit product first, but matchup grammar is still useful for weekly pulse and role/freshness context.
- Use matchup data as context, not a verdict. Example: `upcoming usage test`, `role monitor`, `offense context changed`.
- Do not let weekly projection dominate dynasty valuation screens.

## Trade UIs

Observed patterns:

- KTC uses symmetric Team 1 / Team 2 lanes, totals, pieces count, settings toggles, variance/future-pick adjustments, recent real trades, quick facts, trends, and dispersion.
- Sleeper trade center shows all rosters side by side, trade block flags, hearts/interest, and team avatars.
- Dynasty Nerds offers trade calculator, trade browser, league analyzer, trade partner identification, and roster rescue.
- ESPN research on trade optimization personalizes value by league rules, roster, selections, roster depth, slot count, and positional importance; team pairing can use complementary roster structures.

DG translation:

- Trade Lab should become a lane-symmetric trade workbench with visible model lane, market lane, roster-capacity context, and recent comparable market trades when available.
- Keep equality of visual weight between sides. No colored "winner" border.
- Trade UI should include why the math moves: scarcity, starters lost/gained, age/curve, picks, roster slots, market divergence.
- Suggestions to balance a trade are dangerous under current law; present candidate deltas only when David supplies the hypothesis/order.

## Waivers And Add/Drop

Observed patterns:

- Yahoo add/drop workflow keeps the add candidate fixed and lists drop candidates below, with projections, locks/status, and a persistent action.
- NFL/Sleeper waiver content is oriented around "top targets," but the app workflow is row comparisons and claims.
- Sleeper supports custom waivers, FAAB/WAB, player transaction history, available players, and roster/start percentages.

DG translation:

- DG waiver/capacity views should use a paired comparison: candidate row above, marginal roster-cost rows below.
- The key metric is not "add this player"; it is `net roster-capacity change`, `model gap`, `market gap`, `slot pressure`, `taxi/IR eligibility`, and `freshness`.
- Locks/status and claim deadlines need to be visually explicit.

## Draft Rooms

Observed patterns:

- Sleeper draft screenshots show live draft buttons, ADP, projected points, round markers, player queue, team/chat tabs, and on-clock state.
- FantasyPros Cheat Sheets app has position tabs, scoring/expert selectors, sort by ECR, headshots, bye week, ECR/best/worst/average, and draft mode.
- Dynasty Nerds offers mock draft simulator, draft assistant, rookie draft pick tracker, ADP, Nerds values, rookie guide, and film room.
- DraftKings has a different draft grammar: salary cap, roster slots, entry time, remaining count, submit action, FPPG, OPRK.

DG translation:

- Rookie Board should be a draft-room tool, not a static report.
- The core row: pick/rank, player identity, position, team/college, model percentile, draft capital, age, tier/band, market/ADP overlay, caveats, receipt.
- Use a queue/watchlist and "picked by league" state, but avoid "take now" language.
- Draft room should preserve pick context and roster need without letting need overrule the model silently.

## Mobile

Observed patterns:

- Yahoo reports fantasy is mobile-centered: its redesign aimed to combine teams, news, lineup management, and box scores; The Verge reports 85% of users used the mobile app in the prior year and over two-thirds used it daily.
- Sleeper is explicitly mobile/social: league chat, transaction alerts, players tab, trade center, and draft interactions are all phone-native.
- DraftKings and Underdog are mobile-first transaction products with large tappable rows, persistent submit/action areas, and compact line items.
- FantasyPros and Yahoo use bottom navigation; Sleeper uses tab bars and chips; ESPN classic app used top tabs.

DG translation:

- Mobile cannot be an afterthought. The first mobile screen should show the daily tape and top changed rows.
- Use bottom nav or compact surface switcher; table overflow alone is insufficient.
- The player inspector should become a bottom sheet on mobile.
- Horizontal comparison surfaces like trade/league views need segmented tabs or swipe panes, not squeezed columns.

## 101 To Advanced Pattern Ladder

1. 101: player rows with rank, identity, position/team, focal value, and filters.
2. Intermediate: tiers, trends, injury/status, freshness, and scoring/league-setting selectors.
3. Advanced: model/market separation, range/floor/median/ceiling, expert/source dispersion, league-specific value, roster-capacity effects.
4. Expert: league-wide opportunity maps, trade partner fit, historical comparable outcomes, validated insight states, and point-in-time trend receipts.

DG should not skip the 101 layer. A model-rich product still needs the same row grammar as the category.

## Risks To Avoid

- Importing action language from public tools: start/sit, buy/sell, dominate, target, verdict, uneven/favors. DG can discuss those as observed category patterns but must translate them into descriptive evidence.
- Treating public market value as truth. KTC/FantasyPros/Dynasty Nerds display market/expert consensus; DG must keep that overlay-only.
- Overusing headshots and color without receipts. Category richness should serve scan speed and recognition, not entertainment.
- Making mobile a squeezed desktop. The category's most-used experiences are mobile-native.

## Design Implication

The DG frontend reset should begin with the rankings table and player inspector. Rankings are the category's common barometer because they establish the row grammar that every other surface reuses: player card, trade lane, waiver comparison, draft room, league view, and mobile daily tape. If we get rankings right, the rest of the app can compose from the same primitives instead of inventing one-off dashboard panels.
