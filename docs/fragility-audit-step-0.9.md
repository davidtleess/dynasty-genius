# Roster Fragility Audit — Step 0.9

Date: 2026-05-03

## Purpose

The strategy has shifted from blind 2027 first-round pick volume to targeted acquisition. The Gold layer now needs to rank league opponents by the probability that their 2027 first lands in a premium draft slot.

## Gold View

`gen_alpha.gold.leaguemate_fragility_index`

The view ranks teams by biological debt using:

- `avg_age_cliff_risk`
- value-weighted biological debt
- count of cliff assets
- whether the manager still controls an unprotected own 2027 1st
- whether they lack 2026/2027 2nds as escape hatches
- count of incomplete rows as an Anti-Speed blocker

## Pick Tier Output

- `TIER_1_SMITH_SAYIN_ELIGIBLE_TOP_3`
- `TIER_2_MANNING_MOORE_ELIGIBLE_TOP_6`
- `TIER_3_LATE_2027_1ST`
- `LOW_FRAGILITY_CONTENDER_PICK`
- `ANTI_SPEED_ABORT_INCOMPLETE_ROSTER`

## Acquisition Action

- `ACQUIRE_2027_1ST_AGGRESSIVELY`
- `ACQUIRE_2027_1ST_SELECTIVELY`
- `REQUIRE_KICKER_FOR_LATE_1ST`
- `DO_NOT_OVERPAY_FOR_CONTENDER_1ST`
- `NO_ACTION`

## Liquidity Risk

`liquidity_risk` highlights managers who have already traded away their 2026 and/or 2027 second-round picks.

- `HIGH_NO_SECOND_ROUND_ESCAPE_HATCH`: no 2026 2nd and no 2027 2nd.
- `MEDIUM_LIMITED_ESCAPE_HATCH`: missing one of the two.
- `LOW`: still has both escape hatches.

## Anti-Speed Boundary

The view does not infer win probability or 2027 draft order from narrative. It only scores roster biological debt from Gold valuation rows. Once Sleeper live ingestion is available, owner and league metadata should be included in each Gold row's `evidence_json` so the view can group true leaguemate rosters.
