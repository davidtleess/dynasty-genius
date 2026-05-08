# Engine B Ignition — Step 0.6

Date: 2026-05-03

## Strategy Enforcement

The Gold layer now carries strategy-state fields that let the agent fleet distinguish verified anchors from conditional thesis assets.

- `asset_tier_status = CONDITIONAL_TIER_2` is the approved representation for prospects such as Ryan Williams after the 2027 verification audit.
- `asset_tier_basis` must explain the evidence basis for the tier. It cannot be filled with narrative hype alone.
- `gen_alpha.gold.roster_valuation_signals` converts verified age, trajectory, and market delta into trade-seeker signals.

## Liquidation Logic

The liquidation monitor is implemented as `gen_alpha.gold.great_liquidation_monitor`.

It is designed to flag sell-high veteran profiles only when the Gold row already contains verified source evidence. It does not store or infer player ages, touchdown totals, gateway variables, or other secrets.

Specific strategic watches:

- Jonathan Taylor: `position = RB` and `age_cliff_risk >= 1.0` resolves to `HIGH_LIQUIDATE` in the signal view.
- Davante Adams: the sell-high dashboard fires only when the row verifies age 33+ and contains `2025_td_outlier`.
- Tyreek Hill: the sell-high dashboard fires only when the row verifies age 32+ and contains `2025_production_outlier` or `2025_td_outlier`.

## Security Boundary

Claude/MCP agent access remains read-only through `dg_agent_gold_readers`.

Allowed:

- `SELECT` on `gen_alpha.gold.roster_valuation`
- `SELECT` on `gen_alpha.gold.roster_valuation_signals`
- `SELECT` on `gen_alpha.gold.great_liquidation_monitor`

Denied by policy:

- Write access to `gen_alpha.bronze`
- Write access to `gen_alpha.silver`
- Mutations against `gen_alpha.gold`
