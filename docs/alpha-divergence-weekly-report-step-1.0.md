# Alpha Divergence Weekly Report — Step 1.0

Date: 2026-05-03

## Purpose

The report flags players where Gold internal valuation is more than 15% below Silver market consensus.

These are `Priority Shorts`: assets the market still wants more than Dynasty Genius does.

## Gold View

`gen_alpha.gold.alpha_divergence_weekly_report`

## Threshold

```text
(silver_market_value - gold_internal_valuation) / silver_market_value >= 0.15
```

## Schedule

The Databricks Asset Bundle defines `alpha_divergence_weekly_report`, scheduled for Mondays at 9:00 AM America/New_York.

## Governance

The report is read-only for MCP/Claude agents through `dg_agent_gold_readers`. It does not expose the underlying Silver market table directly.
