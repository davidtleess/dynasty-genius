# Engine B Ignition — Step 0.6

Date: 2026-05-03

## Strategy Enforcement

The Gold layer now carries strategy-state fields that let the agent fleet distinguish verified anchors from conditional thesis assets.

- `asset_tier_status = CONDITIONAL_TIER_2` is the approved representation for prospects such as Ryan Williams after the 2027 verification audit.
- `asset_tier_basis` must explain the evidence basis for the tier. It cannot be filled with narrative hype alone.
- `gen_alpha.gold.roster_valuation_signals` converts verified age, trajectory, and market delta into market context signals.

## Opponent Fragility Context

The opponent fragility lens is implemented as `gen_alpha.gold.opponent_fragility_lens`.

It is designed to flag veteran age-curve and market-context signals only when the Gold row already contains verified source evidence. It does not store or infer player ages, touchdown totals, gateway variables, or other secrets.

Specific strategic watches:

- Jonathan Taylor: `position = RB` and `age_cliff_risk >= 1.0` resolves to `AGE_CLIFF_HIGH` in the signal view.
- Davante Adams: the context lens emits a signal only when the row verifies age 33+ and contains `2025_td_outlier`.
- Tyreek Hill: the context lens emits a signal only when the row verifies age 32+ and contains `2025_production_outlier` or `2025_td_outlier`.

## Security Boundary

Claude/MCP agent access remains read-only through `dg_agent_gold_readers`.

Allowed:

- `SELECT` on `gen_alpha.gold.roster_valuation`
- `SELECT` on `gen_alpha.gold.roster_valuation_signals`
- `SELECT` on `gen_alpha.gold.opponent_fragility_lens`

Denied by policy:

- Write access to `gen_alpha.bronze`
- Write access to `gen_alpha.silver`
- Mutations against `gen_alpha.gold`
