# Model Accuracy Dashboard — Step 0.8

Date: 2026-05-03

## Purpose

The dashboard audits when human qualitative judgment intentionally diverges from the model or market.

Primary use case: Ryan Williams is marked `CONDITIONAL_TIER_2` in Gold while mock market consensus can still represent him as `ANCHOR`. That disagreement becomes auditable instead of disappearing into narrative memory.

## Tables and Views

- Silver dependency: `gen_alpha.silver.market_consensus_values`
- Gold agent surface: `gen_alpha.gold.model_accuracy_dashboard`

Claude/MCP readers receive access only to the Gold view, not the underlying Silver market table.

## Audit Signals

- `QUAL_OVERRIDE_ACTIVE`: human re-tiering is active.
- `TIER_DISAGREEMENT`: Gold tier disagrees with market consensus tier.
- `MARKET_CONSENSUS_MISSING`: no market row exists yet.
- `ANTI_SPEED_ABORT_GOLD_INCOMPLETE`: Gold row is not decision-grade.
- `ANTI_SPEED_ABORT_MARKET_INCOMPLETE`: market row is not decision-grade.

## Ryan Williams Baseline

Mock Step 0.8 rows intentionally show:

- Gold internal tier: `CONDITIONAL_TIER_2`
- Mock Silver consensus tier: `ANCHOR`
- Dashboard result: visible tier disagreement requiring retrospective tracking.

This does not claim live market truth. It tests the governance surface until KTC/DynastyNerds ingestion is live.
