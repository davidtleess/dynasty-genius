# Impeccable-Led Frontend Rethink - Codex Independent Lane

Date: 2026-07-06
Status: Codex design-research synthesis, uncommitted
Input: `docs/strategies/2026-07-06-fantasy-app-data-display-research-codex.md`
Scope: motivate the app rethink from fantasy-app fundamentals plus Impeccable product-register discipline

## Thesis

Dynasty Genius should stop presenting itself as a governed backend report and start presenting itself as a dynasty asset terminal.

That does not mean copying consumer fantasy-app hype. The category's useful fundamentals are structural: ranked rows, player identity, tier/drop-off visualization, focal values, position/team systems, headshots, trend deltas, league context, trade lanes, add/drop comparison, draft queues, and mobile-first scans. DG should adopt those fundamentals and translate them through its own law: model/market separation, receipts, freshness, no verdicts, and descriptive-only states.

The rethink should start with player rankings because rankings are the common barometer. Rankings define the row grammar. The row grammar then powers Daily Open, League Pulse, Trade Lab, Roster Capacity, Rookie Board, and every player card.

## What Was Missing

The failed preview was not just "not polished." It missed category fundamentals:

- No player-first row system strong enough to compete with fantasy tools.
- Too little player identity: headshots, team marks, position chips, position ranks.
- Too little focal value hierarchy: rows should have one number David can scan first.
- Too little tier/drop-off grammar: rankings need visible clusters, not only lists.
- Too little trend grammar: movement should appear as a tape of model/market changes.
- Too little league grammar: team rows, franchise equity, trade partners, roster pressure.
- Too little mobile-native thinking: fantasy usage is daily, check-in, phone-first.
- Too much backend-report language in the visible layer.

Impeccable's product-register rule applies: design serves the task. Familiar fantasy affordances are not a downgrade. They are the baseline David expects before DG's model honesty can matter.

## North-Star Screen Order

Recommended re-order for the frontend rethink:

1. **Rankings / Asset Board**
   - First surface to design because it sets the universal row system.
   - Shows all relevant players/picks with rank, identity, position rank, model percentile, xVAR/PVO focal value, market overlay, trend, tier band, caveats, and receipts.
   - Default sort basis is explicit: `model value percentile`, `xVAR`, or `market divergence`, never hidden.

2. **Daily Tape**
   - Morning view over changed rows, not a generic dashboard.
   - Summarizes model movement, market movement, freshness, new caveats, role changes, roster-pressure changes, and league events.
   - Uses the same row anatomy as Rankings, filtered to "changed since last capture."

3. **Player Inspector**
   - Right-side drawer on desktop; bottom sheet on mobile.
   - Opens from every row.
   - Displays player identity, focal numbers, source freshness, trend chart with Hard Right Edge, drivers, counter-argument, caveats, and receipts.

4. **League Equity**
   - Team rows, not cards.
   - Columns for total model value, starters, depth, picks, positional pressure, market value, capacity, and freshness.
   - Includes partner-fit evidence but no nominated targets.

5. **Trade Lab**
   - Symmetric lanes with model and market sections separated.
   - Shows total value, pieces, starters lost/gained, age/curve state, roster-capacity impact, pick context, and trend/dispersion.
   - No winner coloring. No "accept/reject." Descriptive imbalance only.

6. **Waiver / Roster Capacity**
   - Add candidate fixed above, marginal roster-cost candidates below.
   - Displays net xVAR/PVO movement, market movement, capacity pressure, slot legality, locks, deadlines, and freshness.

7. **Draft Room / Rookie Board**
   - Live-draft tool, not static prospect report.
   - Queue, picked state, player identity, draft capital, model percentile, tier/drop-off, roster context, market/ADP overlay, and caveats.

## Universal Row Anatomy

Every player/pick row should use a shared `AssetRow` grammar:

- `rank`: left edge; fixed width.
- `identity`: headshot/fallback, name, team mark, position chip, position rank.
- `primary value`: one focal number based on current sort.
- `tier/drop-off`: band divider or compact column.
- `model lane`: model-blue value/trend/range.
- `market lane`: market-amber value/trend/range when available.
- `context`: age/curve, opponent/role, roster/start %, draft capital, or slot pressure depending on surface.
- `status`: injury/stale/missing/low-coverage tokens.
- `receipt`: focusable source/provenance trigger.
- `row action`: open inspector; never an action-order button.

Rows must be stable at 32px desktop density where possible. Expanded rows can reach 48-56px only when headshots and secondary text need it. Mobile rows become two-line cells with a fixed right-side value stack.

## Visual System Direction

Use the current DG tokens, but spend them more deliberately:

- **Model blue**: DG-computed valuation lane only.
- **Market amber**: market overlay lane only.
- **Position hues**: categorical chips and tiny swatches; do not carry value judgment.
- **Team marks**: small team-color bars or dots beside team abbreviation; avoid NFL-logo dependency unless asset rights are clear.
- **Headshots**: self-hosted asset pipeline, fallback initials/silhouette. This is a parity requirement, not decoration.
- **Tier bands**: horizontal dividers, compact sticky labels, or row-group shading. Avoid side-stripe borders and card grids.
- **Trend**: small sparklines ending at the Hard Right Edge; signed deltas in neutral lane color.
- **Receipts**: visible but quiet. Every number can be inspected without making the table look like compliance paperwork.

Do not use green/red as good/bad. Do not copy DraftKings/Underdog betting-energy visual language. Do not make every section a card. Product density is allowed.

## Mobile Direction

The mobile app should not be a collapsed desktop table.

Mobile pattern:

- Top: compact daily tape summary with capture freshness and surface switcher.
- Body: virtualized row list with headshots, position chips, focal values, and small model/market deltas.
- Inspector: bottom sheet with tabs: `Snapshot`, `Trend`, `Receipts`, `Context`.
- Trade: segmented lanes (`Side A`, `Side B`, `Impact`) rather than squeezed columns.
- League: team list with expandable value stacks.
- Draft: queue-first; thumb-friendly player rows; persistent current-pick context.

Yahoo and Sleeper both show that fantasy managers check constantly on phones. DG should be credible on desktop, but daily value must survive phone use.

## Impeccable Critique Checklist For The Rethink

Before any implementation, run this critique against the proposed design:

- Can a dynasty manager identify the top player, the drop-off, and the basis of the sort in five seconds?
- Does every row have a recognizable player identity?
- Is the most important value visually dominant without becoming a verdict?
- Are model and market visually separate and symmetric?
- Are position colors categorical only?
- Are stale/missing/low-coverage states visible without taking over the screen?
- Does the mobile view show useful rows, not compressed columns?
- Does every number have a receipt path?
- Does the UI avoid backend schema nouns in visible copy?
- Does the screen create a task path: scan -> inspect -> compare -> decide by David?

## Three Approaches For The Whole-Team Rethink

### Approach A - Rankings-First Rebuild

Start by designing the Asset Board and Player Inspector. Then migrate Daily Tape, League Equity, Trade Lab, Waivers, and Draft Room onto the same primitives.

Trade-off: slower to touch every surface, but the row grammar becomes coherent and reusable.

Recommendation: choose this.

### Approach B - Daily Open Rescue

Keep the current daily-open surface as the center and inject category fundamentals into it: headshots, rows, sparklines, tiers, and focal values.

Trade-off: faster visible improvement, but risks patching the failed surface instead of solving the system.

Use only if David wants a short preview loop before the larger reset.

### Approach C - Surface-by-Surface Reskin

Polish each existing surface independently.

Trade-off: fastest apparent coverage, highest long-term drift. This repeats the original mistake: good primitives without a true product grammar.

Do not choose this as the main path.

## Recommended Design Program

1. Shape the Asset Board and Player Inspector first.
2. Produce static desktop and mobile mockups before code.
3. Run Impeccable critique on those mockups.
4. Falsify against DG law: no verdicts, no hidden sort basis, no model/market blending, no color-only meaning, stale data visible.
5. Only then write a build spec and RED tests.
6. Implement in small increments: primitives, Asset Board, Daily Tape adoption, League Equity, Trade Lab, Waiver/Capacity, Draft Room.

## Concrete Surface Requirements

### Asset Board

- Row-first, virtualized if needed.
- Position tabs/chips plus all-assets view.
- Sort controls: model value, xVAR, market value, model-market delta, age/curve, trend, tier.
- Sticky tier dividers.
- Headshots and team marks.
- Right-side inspector.

### Daily Tape

- "What changed" is a filtered Asset Board.
- Sections: model movement, market movement, new caveats, league transactions, role/freshness changes.
- No prose-only blocks where a row would be better.

### League Equity

- Team rows with compact value stacks.
- Include picks explicitly, with unvalued/missing states disclosed.
- Position heat matrix can use position hues, but labels/numbers must carry meaning.

### Trade Lab

- Two or more symmetric lanes.
- Model lane and market lane visible separately.
- Context stack: starters, bench, age curve, picks, roster slots, future liquidity.
- Recent market comps only as evidence, not as recommendation.

### Waiver / Capacity

- Candidate row plus drop-cost rows.
- Marginal cost is an index, not a recommendation.
- Locks, eligibility, deadlines, stale status, and FAAB context visible.

### Draft Room

- Live board, queue, tiers, picks, ADP/market overlay, model row, roster context.
- Drafted/unavailable state clear.
- Use rookie-specific receipts: draft capital, age, production, caveats.

## Legal Translation Rules

Public fantasy apps say things DG cannot say in shipped descriptive outputs. Translate as follows:

- `Start/Sit` -> `weekly projection context`.
- `Buy/Sell` -> `market divergence`.
- `Target` -> `candidate row under selected sort`.
- `Winner/Favors` -> `side delta`.
- `Safe` -> `low variance range` only if backed by data.
- Green/red good-bad -> model-blue/market-amber signed movement or neutral severity tokens.
- "Expert says" -> source overlay with freshness.

## Success Criteria For The Next Visual Preview

The next David preview should make these true:

- First viewport has real player rows with headshots or governed fallbacks.
- It is obvious which number is the focal value and why the screen is sorted that way.
- Tier/drop-off structure is visible without reading a paragraph.
- Model and market lanes are distinct.
- At least one trend sparkline or value-span element ends at the Hard Right Edge.
- Mobile view is designed, not merely responsive.
- Receipts are accessible but not visually dominant.
- The screen feels like a dynasty asset terminal, not a compliance report.

## Codex Position For Cockpit

The team should not begin by polishing the current Daily What-Changed screen. The rebuild should begin by designing the Asset Board row system and Player Inspector, because every fantasy surface depends on that primitive. Once the row system is right, Daily Tape becomes a powerful opening surface instead of a bespoke dashboard. This is the smallest design move that changes the whole product.
