# 2026 Rookie Draft Closeout Validation

Date: 2026-05-21

## Source Checks

- Sleeper draft id: `1314363401757036544`
- League id: `1314363401744416768`
- Draft status: `complete`
- Draft shape: 3 rounds x 12 teams = 36 picks
- Generated state: `resources/draft_state.js`
- Generated state check: `current_pick_no == total_picks == 36`

## Pick Validation

- Pick 26: Kaelon Black, RB, Sleeper player id `13414`, selected by roster id `1`.
- Final pick: Demond Claiborne, RB, Sleeper player id `13347`, pick 36.
- Board recommendation check: after removing the first 25 selected players from `resources/prospect_cards.json`, Kaelon Black was the top remaining xVAR-ranked player (`xvar_class_rank` 6, `xvar` 13.4).

## Roster Audit Check

- Endpoint run: `GET /api/roster/audit`
- Result: HTTP 200, `status: active`, `engine: pvo_assembler_v1`
- Kaelon Black appeared on David's roster as player id `13414`.
- Decision-grade status remained guarded: top-level `decision_supported` was `false`.

## Product Notes

- No model features, rankings, market-derived training inputs, or decision-grade status changed.
- FantasyCalc appeared only as post-PVO market overlay in the roster audit response.
